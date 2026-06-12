from flask import Blueprint, jsonify, request, current_app
from app.utils.data_loader import load_json_data

shelters_bp = Blueprint('shelters', __name__)

@shelters_bp.route('', methods=['GET'])
def get_shelters():
    """
    Retrieve all shelters with optional filtering.
    
    Query Params:
    - status: 'open', 'full', or 'closed'
    - amenity: 'food', 'water', 'power_generators', 'medical_station', 'pets_allowed', 'wifi'
    """
    file_path = current_app.config['SHELTERS_JSON']
    data = load_json_data(file_path)
    
    status = request.args.get('status')
    if status:
        data = [item for item in data if item.get('status') == status.lower()]
        
    amenity = request.args.get('amenity')
    if amenity:
        amen_lower = amenity.lower()
        data = [item for item in data if amen_lower in [a.lower() for a in item.get('amenities', [])]]
        
    return jsonify(data)
