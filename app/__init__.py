import os
from flask import Flask, jsonify
from flask_cors import CORS
from app.config import config_by_name
from app.api import api_bp

def create_app(config_name=None):
    if not config_name:
        config_name = os.environ.get('FLASK_ENV', 'development')
        
    app = Flask(__name__)
    
    # Load configuration
    config_obj = config_by_name.get(config_name, config_by_name['default'])
    app.config.from_object(config_obj)
    
    # Enable CORS for all routes to support cross-origin frontend apps (e.g. Next.js)
    CORS(app, resources={r"/*": {"origins": "*"}})
    
    # Register blueprints at root to match requested endpoints (e.g. /emergencies)
    app.register_blueprint(api_bp, url_prefix='')
    
    # Health check route
    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({
            "status": "healthy",
            "service": "SentinelAI API",
            "environment": config_name
        }), 200

    # Error handling
    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        return jsonify({"error": "Internal server error"}), 500
        
    return app
