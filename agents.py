import json
import os
import httpx
import yaml
from datetime import datetime, timezone
from dotenv import load_dotenv
from groq import Groq
import instructor
from schemas import AgentAssessment, CriticAssessment, AdversarialChallenge, FinalDecision

load_dotenv()

def get_client():
    api_key = os.getenv("GROQ_API_KEY")
    try:
        return instructor.from_groq(Groq(api_key=api_key), mode=instructor.Mode.JSON)
    except Exception as e:
        print("Failed to initialize Groq client:", e)
        return None

MODEL = "openai/gpt-oss-20b"

# Load Policy
policy_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "policy.yaml")
with open(policy_path, "r") as f:
    POLICY = yaml.safe_load(f)

def run_safety_agent(vehicle_id: str) -> AgentAssessment:
    try:
        from simulator import VEHICLES, init_vehicles
        from main import CUSTOM_CARGO_MAP
        if not VEHICLES: init_vehicles()
        v = VEHICLES.get(vehicle_id)
        if v:
            data = {
                "speed": v.speed,
                "fuel_level": v.fuel_level,
                "engine_temperature": v.engine_temperature,
                "tyre_pressure": v.tyre_pressure.dict(),
                "timestamp": v.last_updated.isoformat()
            }
            if vehicle_id in CUSTOM_CARGO_MAP:
                c_info = CUSTOM_CARGO_MAP[vehicle_id]
                if c_info.get("driver_status"): data["driver_status"] = c_info["driver_status"]
                if c_info.get("judge_notes"): data["judge_notes"] = c_info["judge_notes"]
        else:
            data = {"error": "Vehicle not found"}
    except Exception as e:
        data = {"error": str(e)}

    system_prompt = f"""You are the Safety Agent. 
    SCOPE: Evaluate telemetry (engine_temperature, tyre_pressure, speed).
    POLICY: 
    - CRITICAL SAFETY HAZARD: If driver_status or judge_notes mentions driver intoxication (drunk/alcohol/drinking), severe fatigue, OR threats of violence/hostility/harm (e.g. 'kill', 'attack', 'threat', 'harm', aggressive driver behavior), finding MUST be CRITICAL safety risk!
    - Engine temp > {POLICY['safety']['engine_temperature']['warning_max']} is HIGH risk, > {POLICY['safety']['engine_temperature']['critical_min']} is CRITICAL.
    - Tyre pressure < {POLICY['safety']['tyre_pressure']['warning_min']} (25 PSI) is HIGH risk, or < 20 PSI is CRITICAL.
    - Tyre pressure > {POLICY['safety']['tyre_pressure']['normal_max']} (35 PSI) is HIGH risk (over-inflation hazard), or > 45 PSI is CRITICAL.
    - Otherwise, it is LOW risk.
    
    The user will provide the JSON data. You must extract the exact values into the `evidence` list.
    Set `finding` to LOW, HIGH, or CRITICAL.
    Set `evidence_quality` to CURRENT.
    Set `missing_evidence` to an empty list [].
    """
    try:
        c = get_client()
        if not c: raise ValueError('Groq client uninitialized')
        return c.chat.completions.create(
            model=MODEL,
            response_model=AgentAssessment,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": f"Data: {json.dumps(data)}"}],
            max_retries=2
        )
    except Exception as e:
        return AgentAssessment(
            finding="UNKNOWN",
            confidence=0.0,
            evidence=f"LLM API Failure: {str(e)}",
            evidence_quality="UNKNOWN",
            missing_evidence=["LLM API Failure"]
        )

def run_maintenance_agent(vehicle_id: str) -> AgentAssessment:
    try:
        from simulator import VEHICLES, init_vehicles
        from main import CUSTOM_CARGO_MAP
        if not VEHICLES: init_vehicles()
        c_info = CUSTOM_CARGO_MAP.get(vehicle_id, {})
        data = {
            "last_service_date": c_info.get("last_service_date", "2026-08-01"),
            "open_work_orders": c_info.get("open_work_orders", 0),
            "last_synced": datetime.now(timezone.utc).isoformat(),
            "status": "OK"
        }
    except Exception as e:
        data = {"error": str(e)}
        
    current_time = datetime.now(timezone.utc).isoformat()
    
    system_prompt = f"""You are the Maintenance Agent.
    SCOPE: Evaluate service history, work orders, and data freshness.
    POLICY:
    - If `last_synced` is older than {POLICY['maintenance']['stale_data_threshold_hours']} hours from {current_time}, evidence_quality MUST be STALE.
    - If open work orders > {POLICY['maintenance']['max_open_work_orders']}, risk is HIGH.
    - Otherwise, risk is LOW.
    
    The user will provide the JSON data. You must extract the exact values into the `evidence` list.
    Set `finding` to LOW or HIGH.
    Set `evidence_quality` to CURRENT or STALE.
    Set `missing_evidence` to an empty list [].
    """
    try:
        c = get_client()
        if not c: raise ValueError('Groq client uninitialized')
        return c.chat.completions.create(
            model=MODEL,
            response_model=AgentAssessment,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": f"Data: {json.dumps(data)}"}],
            max_retries=2
        )
    except Exception as e:
        return AgentAssessment(
            finding="UNKNOWN",
            confidence=0.0,
            evidence=f"LLM API Failure: {str(e)}",
            evidence_quality="UNKNOWN",
            missing_evidence=["LLM API Failure"]
        )

def run_operations_agent(vehicle_id: str) -> AgentAssessment:
    try:
        from simulator import VEHICLES, init_vehicles
        from main import CUSTOM_CARGO_MAP
        if not VEHICLES: init_vehicles()
        cargo_map = {
            "TRUCK-1001": {"dest": "Mumbai", "cargo": "Auto Parts", "priority": "LOW", "cond": "Clear highway"},
            "TRUCK-1002": {"dest": "Bengaluru", "cargo": "Industrial Machinery", "priority": "MEDIUM", "cond": "Heavy rain on NH48"},
            "TRUCK-1003": {"dest": "Nashik", "cargo": "Electronics", "priority": "HIGH", "cond": "Clear, light traffic"},
            "TRUCK-1004": {"dest": "Hyderabad", "cargo": "Perishables", "priority": "HIGH", "cond": "Heavy traffic, construction"},
            "TRUCK-1005": {"dest": "Delhi", "cargo": "Vaccines (Expires in 4 hours)", "priority": "HIGH", "cond": "Massive traffic jam on Route 66"},
            "TRUCK-1006": {"dest": "Kolkata", "cargo": "Chemicals", "priority": "CRITICAL", "cond": "Moderate traffic"},
            "TRUCK-1007": {"dest": "Chennai", "cargo": "Textiles", "priority": "LOW", "cond": "Clear"},
            "TRUCK-1008": {"dest": "Ahmedabad", "cargo": "Furniture", "priority": "LOW", "cond": "Clear"},
            "TRUCK-1009": {"dest": "Jaipur", "cargo": "Medical Supplies", "priority": "HIGH", "cond": "Clear"},
            "TRUCK-1010": {"dest": "Lucknow", "cargo": "Steel Pipes", "priority": "MEDIUM", "cond": "Slow moving traffic"}
        }
        info = CUSTOM_CARGO_MAP.get(vehicle_id, cargo_map.get(vehicle_id, {"dest": "Unknown", "cargo": "General Cargo", "priority": "LOW", "cond": "Unknown"}))
        data = {
            "destination": info["dest"],
            "estimated_arrival": "17:30",
            "cargo": info["cargo"],
            "route_conditions": info["cond"],
            "driver_status": info.get("driver_status", "Shift ends in 30 minutes"),
            "judge_notes": info.get("judge_notes", ""),
            "priority": info["priority"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        data = {"error": str(e)}

    system_prompt = """You are the Operations Agent.
    SCOPE: Evaluate delivery priority, route conditions, cargo type, and impact of stopping the vehicle.
    POLICY: 
    - If driver_status or judge_notes mentions driver intoxication (drunk/alcohol) or sleep deprivation/fatigue, finding MUST be HIGH risk due to severe driver impairment!
    - If cargo is expiring soon (like vaccines) or driver shift is ending, stopping the vehicle is a massive risk. In these cases, finding MUST be HIGH.
    - Otherwise, finding is LOW.
    
    The user will provide the JSON data. You must extract the exact values into the `evidence` list.
    Set `finding` to LOW or HIGH.
    Set `evidence_quality` to CURRENT.
    Set `missing_evidence` to an empty list [].
    """
    try:
        c = get_client()
        if not c: raise ValueError('Groq client uninitialized')
        return c.chat.completions.create(
            model=MODEL,
            response_model=AgentAssessment,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": f"Data: {json.dumps(data)}"}],
            max_retries=2
        )
    except Exception as e:
        return AgentAssessment(
            finding="UNKNOWN",
            confidence=0.0,
            evidence=f"LLM API Failure: {str(e)}",
            evidence_quality="UNKNOWN",
            missing_evidence=["LLM API Failure"]
        )

def run_critic_agent(safety: dict, maintenance: dict, operations: dict) -> CriticAssessment:
    system_prompt = """You are the Critic Agent.
    Your responsibilities are:
    1. DRIVER IMPAIRMENT CHECK: If any evidence mentions driver drunkenness, intoxication, or multi-day sleep deprivation, and Safety or Operations did NOT report CRITICAL/HIGH risk, flag `has_conflict` = True and explicitly state driver impairment was ignored!
    2. Conflict Detection: Identify if Safety says LOW while Operations or Maintenance says HIGH/CRITICAL (or vice versa)! Flag `has_conflict` = True.
    3. Evidence Sufficiency: Identify if critical required fields are in `missing_evidence`.
    4. Evidence Freshness: Identify if any domain reported `evidence_quality` as STALE.
    5. Scope Violation: Ensure Operations didn't make safety claims without Safety Agent evaluating them.
    
    If ANY of the above are true, flag `requires_more_evidence` or `has_conflict` or `scope_violation_detected` as True.
    CRITICAL: Output the JSON schema.
    """
    user_prompt = f"Safety: {safety}\nMaintenance: {maintenance}\nOperations: {operations}"
    try:
        c = get_client()
        if not c: raise ValueError('Groq client uninitialized')
        return c.chat.completions.create(
            model=MODEL,
            response_model=CriticAssessment,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            max_retries=2
        )
    except Exception as e:
        return CriticAssessment(
            has_conflict=False,
            scope_violation_detected=False,
            requires_more_evidence=False,
            reasoning=f"LLM API Failure: {str(e)}"
        )

def run_adversarial_agent(safety: dict, maintenance: dict, operations: dict, critic: dict) -> AdversarialChallenge:
    system_prompt = """You are the Adversarial Agent (Red Team).
    You audit the other agents for logical flaws, scope violations, or ignored evidence.
    
    CRITICAL: If any evidence mentions driver drunkenness, alcohol, or sleep deprivation, and the vehicle was cleared or rated LOW risk by Safety, YOU MUST RAISE A CHALLENGE highlighting: "CRITICAL DRIVER IMPAIRMENT HAZARD: Vehicle cannot be dispatched with a drunk or sleep-deprived driver."
    
    If you find a clear, dangerous flaw or contradiction, set `challenge_successful` to True and describe the flaw.
    HOWEVER, if the data is normal (e.g. engine temp < 95, tyre pressure > 28, fuel > 15), and the agents correctly reported LOW risk, you MUST set `challenge_successful` to False. 
    DO NOT invent flaws about normal operating values (e.g. do not claim 77C is overheating, do not claim 30 PSI is low).
    CRITICAL: Output the JSON schema.
    """
    user_prompt = f"Safety: {safety}\nMaintenance: {maintenance}\nOperations: {operations}\nCritic: {critic}"
    try:
        c = get_client()
        if not c: raise ValueError('Groq client uninitialized')
        return c.chat.completions.create(
            model=MODEL,
            response_model=AdversarialChallenge,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            max_retries=2
        )
    except Exception as e:
        return AdversarialChallenge(
            challenge_successful=False,
            flaw_description=f"LLM API Failure: {str(e)}"
        )

def run_decision_agent(safety: dict, maintenance: dict, operations: dict, critic: dict, adversarial: dict) -> FinalDecision:
    system_prompt = """You are the Final Decision Agent.
    Based on all evidence, the Critic's review, and the Adversarial Agent's challenge, make a final operational recommendation.
    (Note: The Policy Engine will strictly enforce whether human approval is required, you just need to provide the recommendation string.)
    CRITICAL: Output the JSON schema.
    """
    user_prompt = f"Safety: {safety}\nMaint: {maintenance}\nOps: {operations}\nCritic: {critic}\nAdversarial: {adversarial}"
    try:
        c = get_client()
        if not c: raise ValueError('Groq client uninitialized')
        return c.chat.completions.create(
            model=MODEL,
            response_model=FinalDecision,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            max_retries=2
        )
    except Exception as e:
        return FinalDecision(
            recommendation=f"LLM API Failure: {str(e)}",
            human_approval_required=True
        )
