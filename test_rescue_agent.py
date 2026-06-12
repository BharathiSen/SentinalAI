import sys
import os
import json

# Ensure parent directory is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.rescue_agent import run_rescue_agent

def main():
    print("==================================================")
    print("Starting SentinelAI Rescue Agent validation test")
    print("==================================================")
    
    # Sample 1: Critical Emergency Request
    request_critical = {
        "id": "REQ-TEST-001",
        "location": {
            "latitude": 29.743128,
            "longitude": -95.394182,
            "address": "1420 Memorial Dr, Houston, TX"
        },
        "severity": "critical",
        "people_count": 8,
        "elderly_present": True,
        "medical_emergency": True,
        "timestamp": "2026-06-12T10:12:00Z"
    }
    
    # Sample 2: Low Emergency Request
    request_low = {
        "id": "REQ-TEST-002",
        "location": {
            "latitude": 29.789123,
            "longitude": -95.345612,
            "address": "450 Heights Blvd, Houston, TX"
        },
        "severity": "low",
        "people_count": 1,
        "elderly_present": False,
        "medical_emergency": False,
        "timestamp": "2026-06-12T10:45:00Z"
    }
    
    # Test cases run
    print("\nEvaluating Request 1 (Expecting CRITICAL/HIGH priority)...")
    print(f"Input request: {json.dumps(request_critical, indent=2)}")
    res_critical = run_rescue_agent(request_critical)
    print(f"Output JSON:\n{json.dumps(res_critical, indent=2)}")
    
    print("\nEvaluating Request 2 (Expecting LOW/MEDIUM priority)...")
    print(f"Input request: {json.dumps(request_low, indent=2)}")
    res_low = run_rescue_agent(request_low)
    print(f"Output JSON:\n{json.dumps(res_low, indent=2)}")
    
    print("\n==================================================")
    print("Validation Test Complete")
    print("==================================================")

if __name__ == "__main__":
    main()
