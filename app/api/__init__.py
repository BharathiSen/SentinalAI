from flask import Blueprint
from app.api.emergencies import emergencies_bp
from app.api.hospitals import hospitals_bp
from app.api.shelters import shelters_bp

api_bp = Blueprint('api', __name__)

# Register sub-blueprints with their respective prefixes
api_bp.register_blueprint(emergencies_bp, url_prefix='/emergencies')
api_bp.register_blueprint(hospitals_bp, url_prefix='/hospitals')
api_bp.register_blueprint(shelters_bp, url_prefix='/shelters')
