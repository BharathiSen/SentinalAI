import os
import json
import math
from typing import Literal, Dict, Any, List
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from agents.state import MedicalAgentState

# Ensure API Key configuration checks
api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
if api_key:
    os.environ["GOOGLE_API_KEY"] = api_key
    os.environ["GEMINI_API_KEY"] = api_key

# Get data path relative to agent file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOSPITALS_JSON = os.path.join(BASE_DIR, 'data', 'hospitals.json')

class MedicalNeedsAnalysis(BaseModel):
    injury_analysis: str = Field(
        description="Analysis of the potential or reported injuries and medical issues."
    )
    required_care: str = Field(
        description="Description of the required care and medical specialties needed."
    )
    required_specialties: List[Literal['emergency', 'trauma', 'icu', 'pediatrics', 'burn_unit']] = Field(
        description="A list of specific specialty tags needed."
    )
    medical_priority: Literal['Low', 'Medium', 'High', 'Critical'] = Field(
        description="The assigned medical priority based on request attributes."
    )
    recommended_action: str = Field(
        description="Immediate actions or first aid instructions before rescue arrival."
    )

# Prompt setup
system_prompt = """You are the Medical Agent, a key component of SentinelAI's emergency response system.
Your responsibility is to analyze emergency requests for potential medical injuries, determine the required medical care, and identify the required medical specialties.

You must assign a medical priority level:
- **Critical**: Severe life-threatening injuries, cardiac arrest, active heavy bleeding, unconsciousness, or multiple victims in critical condition.
- **High**: Serious injuries that require immediate attention but are currently stable (e.g., bone fractures, head trauma, moderate bleeding).
- **Medium**: Minor injuries, sprains, moderate pain, or general illness requiring standard attention.
- **Low**: No physical injuries, small cuts/abrasions, or requests for medication refills/information.

Analyze the given request details and return:
1. `injury_analysis`: Detailed analysis of potential or reported injuries.
2. `required_care`: Description of the required medical care.
3. `required_specialties`: A list of required medical specialties choosing from ['emergency', 'trauma', 'icu', 'pediatrics', 'burn_unit'].
4. `medical_priority`: One of 'Low', 'Medium', 'High', 'Critical'.
5. `recommended_action`: Recommended first-aid instructions for victims or first responders before hospital arrival.
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("user", "Emergency Request Details:\n{request_details}")
])

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates great-circle distance between two points on sphere.
    """
    R = 6371.0  # Radius of Earth in km
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

def select_suitable_hospital(request_lat: float, request_lon: float, required_specs: List[str], hospitals: List[dict]) -> dict:
    """
    Helper function to score and select the best matching hospital.
    """
    suitable_hospitals = []
    
    for h in hospitals:
        if h.get("status") == "damaged":
            continue
            
        loc = h.get("location", {})
        lat = loc.get("latitude")
        lon = loc.get("longitude")
        if lat is None or lon is None:
            continue
            
        dist = haversine_distance(request_lat, request_lon, lat, lon)
        
        # Count matching specialties
        specs = [s.lower() for s in h.get("specialities", [])]
        match_count = sum(1 for spec in required_specs if spec.lower() in specs)
        
        status = h.get("status", "operational").lower()
        beds = h.get("available_beds", 0)
        
        # Scoring algorithm:
        # Match count adds 15 points per match
        # Available beds adds 20 points
        # Operational status adds 15 points
        score = (match_count * 15)
        if beds > 0:
            score += 20
        if status == "operational":
            score += 15
            
        # Deduct score for distance (penalize 2 points per km to stay local)
        score -= dist * 2
        
        suitable_hospitals.append({
            "hospital": h,
            "distance_km": round(dist, 2),
            "match_count": match_count,
            "suitability_score": score
        })
        
    if not suitable_hospitals:
        return None
        
    suitable_hospitals.sort(key=lambda x: x["suitability_score"], reverse=True)
    return suitable_hospitals[0]

def rule_based_fallback(req: dict) -> dict:
    """
    Fallback heuristics for injury analysis in case LLM is unavailable or fails.
    """
    severity = req.get("severity", "low").lower()
    people_count = req.get("people_count", 1)
    elderly_present = req.get("elderly_present", False)
    medical_emergency = req.get("medical_emergency", False)
    
    fallback_note = "Rule-based fallback calculation applied."
    
    if medical_emergency:
        if severity in ("critical", "high") or elderly_present or people_count >= 5:
            priority = "Critical"
            required_care = "Immediate trauma/ICU life support and medical response."
            specialties = ["emergency", "trauma", "icu"]
            action = "Check airway, breathing, and circulation. Apply pressure to any bleeding. Call local paramedics immediately."
        else:
            priority = "High"
            required_care = "Urgent emergency medical care."
            specialties = ["emergency", "trauma"]
            action = "Keep victim warm and calm. Monitor vital signs and administer basic first aid until help arrives."
    else:
        if severity == "critical":
            priority = "High"
            required_care = "Emergency medical assessment for potential hazards/injuries."
            specialties = ["emergency"]
            action = "Evacuate the area immediately and check for hidden injuries or trauma."
        elif severity == "high" or elderly_present:
            priority = "Medium"
            required_care = "Secondary medical evaluation and standard emergency care."
            specialties = ["emergency"]
            action = "Provide water and shelter. Check for signs of shock or breathing difficulty."
        else:
            priority = "Low"
            required_care = "Minor/non-urgent medical review."
            specialties = ["emergency"]
            action = "Clean minor wounds, administer basic first aid, and reassure victims."
            
    if people_count >= 5:
        specialties.append("icu")
        
    return {
        "injury_analysis": f"{fallback_note} Inferred potential injuries based on severity ({severity}) and medical_emergency flag.",
        "required_care": required_care,
        "required_specialties": list(set(specialties)),
        "medical_priority": priority,
        "recommended_action": action
    }

def analyze_medical_needs_node(state: MedicalAgentState) -> MedicalAgentState:
    req = state["request"]
    
    # Try using Gemini LLM first if API key is present
    if os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"):
        try:
            llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                temperature=0.1
            )
            structured_llm = llm.with_structured_output(MedicalNeedsAnalysis)
            chain = prompt | structured_llm
            
            response = chain.invoke({"request_details": json.dumps(req, indent=2)})
            
            return {
                "request": req,
                "injury_analysis": response.injury_analysis,
                "required_care": response.required_care,
                "required_specialties": response.required_specialties,
                "medical_priority": response.medical_priority,
                "recommended_action": response.recommended_action,
                "hospital_recommendation": None,
                "agent_output": None
            }
        except Exception as e:
            fallback_res = rule_based_fallback(req)
            fallback_res["injury_analysis"] = f"LLM error: {str(e)}. {fallback_res['injury_analysis']}"
            return {
                "request": req,
                "injury_analysis": fallback_res["injury_analysis"],
                "required_care": fallback_res["required_care"],
                "required_specialties": fallback_res["required_specialties"],
                "medical_priority": fallback_res["medical_priority"],
                "recommended_action": fallback_res["recommended_action"],
                "hospital_recommendation": None,
                "agent_output": None
            }
    else:
        fallback_res = rule_based_fallback(req)
        fallback_res["injury_analysis"] = f"Missing API key. {fallback_res['injury_analysis']}"
        return {
            "request": req,
            "injury_analysis": fallback_res["injury_analysis"],
            "required_care": fallback_res["required_care"],
            "required_specialties": fallback_res["required_specialties"],
            "medical_priority": fallback_res["medical_priority"],
            "recommended_action": fallback_res["recommended_action"],
            "hospital_recommendation": None,
            "agent_output": None
        }

def recommend_hospital_node(state: MedicalAgentState) -> MedicalAgentState:
    req = state["request"]
    required_specs = state.get("required_specialties") or ["emergency"]
    
    # Get location
    loc = req.get("location", {})
    if isinstance(loc, dict):
        lat = loc.get("latitude") or req.get("latitude")
        lon = loc.get("longitude") or req.get("longitude")
    else:
        lat = req.get("latitude")
        lon = req.get("longitude")
        
    # Default location if missing
    if lat is None or lon is None:
        lat = 29.7604
        lon = -95.3698
        
    # Load hospitals
    hospitals = []
    try:
        with open(HOSPITALS_JSON, 'r', encoding='utf-8') as f:
            hospitals = json.load(f)
    except Exception as e:
        print(f"Error loading hospitals: {e}")
        
    best_h = select_suitable_hospital(lat, lon, required_specs, hospitals)
    
    recommendation = None
    if best_h:
        h = best_h["hospital"]
        recommendation = {
            "id": h.get("id"),
            "name": h.get("name"),
            "address": h.get("location", {}).get("address"),
            "distance_km": best_h["distance_km"],
            "available_beds": h.get("available_beds"),
            "specialities": h.get("specialities", [])
        }
    else:
        recommendation = {
            "name": "No suitable hospital found",
            "address": "N/A",
            "distance_km": 0.0,
            "available_beds": 0,
            "specialities": []
        }
        
    agent_output = {
        "hospital_recommendation": recommendation,
        "medical_priority": state.get("medical_priority"),
        "recommended_action": state.get("recommended_action"),
        "injury_analysis": state.get("injury_analysis"),
        "required_care": state.get("required_care")
    }
    
    return {
        "hospital_recommendation": recommendation,
        "agent_output": agent_output
    }

# Define LangGraph StateGraph for Medical Agent
builder = StateGraph(MedicalAgentState)
builder.add_node("analyze_medical_needs", analyze_medical_needs_node)
builder.add_node("recommend_hospital", recommend_hospital_node)

builder.add_edge(START, "analyze_medical_needs")
builder.add_edge("analyze_medical_needs", "recommend_hospital")
builder.add_edge("recommend_hospital", END)

# Compile workflow graph
medical_agent_graph = builder.compile()

def run_medical_agent(request_data: dict) -> dict:
    """
    Convenience entrypoint to execute the Medical Agent workflow.
    """
    initial_state = {
        "request": request_data,
        "injury_analysis": None,
        "required_care": None,
        "required_specialties": None,
        "medical_priority": None,
        "recommended_action": None,
        "hospital_recommendation": None,
        "agent_output": None
    }
    result = medical_agent_graph.invoke(initial_state)
    return result.get("agent_output") or {}
