import os
import json
from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from agents.state import RescueAgentState

# Ensure API Key configuration checks
api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
if api_key:
    os.environ["GOOGLE_API_KEY"] = api_key
    os.environ["GEMINI_API_KEY"] = api_key

# Define structured Pydantic output schema
class RescueAnalysis(BaseModel):
    analysis: str = Field(
        description="A thorough analysis and reasoning explaining why the emergency request is assigned this priority."
    )
    urgency_level: str = Field(
        description="An explanation of the urgency level (e.g. status of victims, risk level, vulnerability)."
    )
    assigned_priority: Literal['Low', 'Medium', 'High', 'Critical'] = Field(
        description="The designated priority based on request attributes."
    )

# Prompt setup
system_prompt = """You are the Rescue Agent, a critical component of SentinelAI, an automated disaster response platform.
Your responsibility is to analyze emergency requests, evaluate the urgency, and assign an appropriate priority.

You MUST prioritize requests based on the following indicators:
- **Critical**: Ongoing life-threatening situation, active medical emergency, high people count, or vulnerable individuals (like elderly) present in severe status.
- **High**: Serious situation with high potential to deteriorate quickly, medical emergencies that are currently stable but require immediate attention, or multiple people trapped/stranded.
- **Medium**: Displaced individuals, minor injuries, or groups needing assistance/shelter but not in immediate life-threatening danger.
- **Low**: Property damage only, inquiries, or minor requests for information/supplies with no injuries or direct threat to life.

Analyze the given request details carefully and return:
1. `analysis`: Detailed analysis of the request.
2. `urgency_level`: Explanation of the level of urgency.
3. `assigned_priority`: One of 'Low', 'Medium', 'High', 'Critical'.
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("user", "Emergency Request Details:\n{request_details}")
])

def rule_based_fallback(req: dict) -> dict:
    """
    Fallback heuristics for priority assignment in case LLM is unavailable or fails.
    """
    severity = req.get("severity", "low").lower()
    people_count = req.get("people_count", 1)
    elderly_present = req.get("elderly_present", False)
    medical_emergency = req.get("medical_emergency", False)
    
    fallback_note = "Rule-based fallback calculation applied."
    
    if medical_emergency:
        if severity in ("critical", "high") or elderly_present or people_count >= 5:
            assigned_priority = "Critical"
            urgency = "Life-threatening medical emergency with compounding risk factors (elderly/large group)."
        else:
            assigned_priority = "High"
            urgency = "Active medical emergency requiring rapid intervention."
    elif severity == "critical":
        assigned_priority = "Critical"
        urgency = "Severe hazard or safety risk reported."
    elif severity == "high" or elderly_present or people_count >= 5:
        assigned_priority = "High"
        urgency = "High risk scenario with vulnerable populations or large groups."
    elif severity == "medium":
        assigned_priority = "Medium"
        urgency = "Moderate risk situation requiring support."
    else:
        assigned_priority = "Low"
        urgency = "Low priority request with no immediate danger to life or safety."
        
    return {
        "analysis": f"{fallback_note} Assigned priority is: {assigned_priority}.",
        "urgency_level": urgency,
        "assigned_priority": assigned_priority
    }

def analyze_request_node(state: RescueAgentState) -> RescueAgentState:
    req = state["request"]
    
    # Try using Gemini LLM first if API key is present
    if os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"):
        try:
            llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                temperature=0.1
            )
            structured_llm = llm.with_structured_output(RescueAnalysis)
            chain = prompt | structured_llm
            
            response = chain.invoke({"request_details": json.dumps(req, indent=2)})
            
            return {
                "request": req,
                "analysis": response.analysis,
                "urgency_level": response.urgency_level,
                "assigned_priority": response.assigned_priority,
                "agent_output": {
                    "analysis": response.analysis,
                    "urgency_level": response.urgency_level,
                    "assigned_priority": response.assigned_priority
                }
            }
        except Exception as e:
            # Fallback on LLM execution failures
            fallback_res = rule_based_fallback(req)
            fallback_res["analysis"] = f"LLM error: {str(e)}. {fallback_res['analysis']}"
            return {
                "request": req,
                "analysis": fallback_res["analysis"],
                "urgency_level": fallback_res["urgency_level"],
                "assigned_priority": fallback_res["assigned_priority"],
                "agent_output": fallback_res
            }
    else:
        # If API key is missing entirely, use rule-based fallback
        fallback_res = rule_based_fallback(req)
        fallback_res["analysis"] = f"Missing API key. {fallback_res['analysis']}"
        return {
            "request": req,
            "analysis": fallback_res["analysis"],
            "urgency_level": fallback_res["urgency_level"],
            "assigned_priority": fallback_res["assigned_priority"],
            "agent_output": fallback_res
        }

# Define LangGraph StateGraph
builder = StateGraph(RescueAgentState)
builder.add_node("analyze_request", analyze_request_node)
builder.add_edge(START, "analyze_request")
builder.add_edge("analyze_request", END)

# Compile the workflow graph
rescue_agent_graph = builder.compile()

def run_rescue_agent(request_data: dict) -> dict:
    """
    Convenience entrypoint to execute the Rescue Agent workflow.
    """
    initial_state = {
        "request": request_data,
        "analysis": None,
        "urgency_level": None,
        "assigned_priority": None,
        "agent_output": None
    }
    result = rescue_agent_graph.invoke(initial_state)
    return {
        "analysis": result.get("analysis"),
        "urgency_level": result.get("urgency_level"),
        "assigned_priority": result.get("assigned_priority")
    }
