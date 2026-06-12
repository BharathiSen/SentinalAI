import json
import os
from flask import current_app

def load_json_data(file_path):
    """
    Safely reads JSON data from the specified file path.
    Returns parsed list/dict or empty list if the file is missing or invalid.
    """
    if not os.path.exists(file_path):
        current_app.logger.error(f"Data file not found: {file_path}")
        return []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        current_app.logger.error(f"Error decoding JSON from {file_path}: {str(e)}")
        return []
    except Exception as e:
        current_app.logger.error(f"Unexpected error reading {file_path}: {str(e)}")
        return []
