from flask import Blueprint, jsonify, request, current_app
from app.utils.data_loader import load_json_data

emergencies_bp = Blueprint('emergencies', __name__)

@emergencies_bp.route('', methods=['GET'])
def get_emergencies():
    """
    Retrieve all emergency requests with optional filtering.
    
    Query Params:
    - severity: 'critical', 'high', 'medium', or 'low'
    - medical: 'true' or 'false'
    """
    file_path = current_app.config['EMERGENCIES_JSON']
    data = load_json_data(file_path)
    
    severity = request.args.get('severity')
    if severity:
        data = [item for item in data if item.get('severity') == severity.lower()]
        
    medical = request.args.get('medical')
    if medical is not None:
        is_medical = medical.lower() in ('true', '1', 'yes')
        data = [item for item in data if item.get('medical_emergency') == is_medical]
        
    return jsonify(data)

@emergencies_bp.route('/analyze', methods=['POST'])
def analyze_emergency():
    """
    Analyze an emergency request using the Rescue Agent.
    
    Expects:
    JSON request body containing emergency details (severity, people_count, medical_emergency, etc.)
    
    Returns:
    JSON response containing the analysis, urgency level, and assigned priority.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No request data provided"}), 400
        
    try:
        from agents.rescue_agent import run_rescue_agent
        result = run_rescue_agent(data)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            "error": "Failed to analyze request",
            "message": str(e)
        }), 500

