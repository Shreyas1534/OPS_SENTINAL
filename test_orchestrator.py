import httpx
import time
import json

def main():
    vehicle_id = "TRUCK-1005"
    
    print(f"--- Setting scenario for {vehicle_id} to NORMAL ---")
    httpx.post(
        f"http://127.0.0.1:8000/vehicles/{vehicle_id}/scenario",
        json={"scenario": "NORMAL"}
    )
    
    print("Triggering the Multi-Agent Orchestrator (LangGraph)...")
    print("This will run Safety, Maintenance, and Operations agents, followed by the Critic and Decision nodes.")
    print("Because we set NORMAL, the Maintenance API will return an old timestamp.")
    
    response = httpx.post(f"http://127.0.0.1:8000/incidents/{vehicle_id}/investigate", timeout=120.0)
    
    print("\n--- [Final Graph State] ---")
    print(json.dumps(response.json(), indent=2))

if __name__ == "__main__":
    main()
