from typing import TypedDict, Optional, Dict, Any

class RescueAgentState(TypedDict):
    """
    State representing the data flow in the Rescue Agent graph.
    """
    # The input emergency request data
    request: Dict[str, Any]
    
    # Analysis outputs filled by the agent
    analysis: Optional[str]          # Detail justification/reasoning
    urgency_level: Optional[str]     # Description of the urgency level determined
    assigned_priority: Optional[str] # One of: 'Low', 'Medium', 'High', 'Critical'
    
    # Full parsed JSON dictionary result
    agent_output: Optional[Dict[str, Any]]
