import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-sentinel-ai')
    BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    
    # Dataset paths
    EMERGENCIES_JSON = os.path.join(DATA_DIR, 'emergency_requests.json')
    HOSPITALS_JSON = os.path.join(DATA_DIR, 'hospitals.json')
    SHELTERS_JSON = os.path.join(DATA_DIR, 'shelters.json')
    RESCUE_TEAMS_JSON = os.path.join(DATA_DIR, 'rescue_teams.json')
    FLOOD_ZONES_JSON = os.path.join(DATA_DIR, 'flood_zones.json')

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
