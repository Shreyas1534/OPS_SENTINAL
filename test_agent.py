import httpx
import time
from agents import run_safety_agent

def main():
    vehicle_id = "TRUCK-1005"
    
    print(f"--- Setting scenario for {vehicle_id} to ENGINE_OVERHEAT ---")
    httpx.post(
        f"http://127.0.0.1:8000/vehicles/{vehicle_id}/scenario",
        json={"scenario": "ENGINE_OVERHEAT"}
    )
    
    print("Waiting 5 seconds for simulator to increase temperature...")
    time.sleep(5)
    
    print("--- Running Safety Agent ---")
    assessment = run_safety_agent(vehicle_id)
    
    print("\n[Safety Agent Result]")
    print(assessment.model_dump_json(indent=2))

if __name__ == "__main__":
    main()
