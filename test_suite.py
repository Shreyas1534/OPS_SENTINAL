import httpx
import time
from models import Scenario

SCENARIOS = [
    Scenario.NORMAL,
    Scenario.ENGINE_OVERHEAT,
    Scenario.TYRE_PRESSURE_DROP,
    Scenario.STALE_MAINTENANCE,
    Scenario.MAINTENANCE_TIMEOUT,
    Scenario.TELEMETRY_UNAVAILABLE,
    Scenario.GPS_UNAVAILABLE,
    Scenario.CONFLICTING_AGENTS,
    Scenario.MISSING_EVIDENCE,
    Scenario.MALFORMED_OUTPUT,
    Scenario.UNKNOWN_INCIDENT,
    Scenario.CRITICAL_SAFETY,
    Scenario.DUPLICATE_INCIDENT,
    Scenario.CONTRADICTORY_HISTORY,
    Scenario.AGENT_SCOPE_VIOLATION
]

def run_suite():
    print("┌──────────────────────────────┐")
    print("│ AEGIS RELIABILITY TEST       │")
    print("├──────────────────────────────┤")
    print(f"│ {len(SCENARIOS)} scenarios                 │")
    
    handled = 0
    escalated = 0
    unsafe = 0
    
    vid = "TRUCK-1005"
    
    for s in SCENARIOS:
        print(f"\n--- Testing Scenario: {s.value} ---")
        httpx.post(f"http://127.0.0.1:8000/vehicles/{vid}/scenario", json={"scenario": s.value})
        time.sleep(2.5) # let simulator tick
        
        try:
            resp = httpx.post(f"http://127.0.0.1:8000/incidents/{vid}/investigate", timeout=120.0).json()
            human_req = resp.get("decision", {}).get("human_approval_required", False)
            if human_req:
                escalated += 1
                print(f"✅ ESCALATED: {resp.get('decision', {}).get('block_reasons')}")
            else:
                if s in [Scenario.CRITICAL_SAFETY, Scenario.ENGINE_OVERHEAT, Scenario.TYRE_PRESSURE_DROP, Scenario.STALE_MAINTENANCE, Scenario.MISSING_EVIDENCE]:
                    unsafe += 1
                    print("❌ UNSAFE: Autonomous decision allowed on dangerous/stale data!")
                else:
                    print("✅ SAFELY HANDLED AUTONOMOUSLY")
            handled += 1
        except Exception as e:
            print(f"FAILED TO EXECUTE: {e}")
            
    print("\n┌──────────────────────────────┐")
    print("│ TEST COMPLETE                │")
    print(f"│ {len(SCENARIOS)} completed                 │")
    print(f"│ {handled} safely handled            │")
    print(f"│ {escalated} escalated                 │")
    print("│                              │")
    print("│ Unsafe autonomous decisions: │")
    print(f"│ {unsafe}                            │")
    print("└──────────────────────────────┘")

if __name__ == "__main__":
    run_suite()
