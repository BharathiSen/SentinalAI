from flask import Blueprint, jsonify, request, current_app
from app.utils.data_loader import load_json_data

hospitals_bp = Blueprint('hospitals', __name__)

@hospitals_bp.route('', methods=['GET'])
def get_hospitals():
    """
    Retrieve all hospitals with optional filtering.
    
    Query Params:
    - status: 'operational', 'critical', or 'damaged'
    - speciality: 'emergency', 'trauma', 'icu', 'pediatrics', 'burn_unit'
    """
    file_path = current_app.config['HOSPITALS_JSON']
    data = load_json_data(file_path)
    
    status = request.args.get('status')
    if status:
        data = [item for item in data if item.get('status') == status.lower()]
        
    speciality = request.args.get('speciality')
    if speciality:
        spec_lower = speciality.lower()
        data = [item for item in data if spec_lower in [s.lower() for s in item.get('specialities', [])]]
        
    return jsonify(data)
