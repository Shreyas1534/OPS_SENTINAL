import yaml
from schemas import RiskLevel, EvidenceQuality

with open("policy.yaml", "r") as f:
    POLICY = yaml.safe_load(f)

def enforce_policy(state: dict) -> dict:
    """
    Deterministic Policy Engine.
    Enforces rules and returns human-readable block reasons describing the exact hazard.
    """
    human_approval_required = False
    block_reasons = []

    # 1. Safety & Telemetry Risk
    safety = state.get("safety", {})
    safety_risk = safety.get("finding", RiskLevel.UNKNOWN.value)
    if safety_risk in [RiskLevel.CRITICAL.value, RiskLevel.HIGH.value]:
        human_approval_required = True
        ev = safety.get("evidence", "")
        if isinstance(ev, dict) or isinstance(ev, list):
            import json
            ev_str = json.dumps(ev)
        else:
            ev_str = str(ev)
            
        if "drunk" in ev_str.lower() or "alcohol" in ev_str.lower():
            block_reasons.append("🚨 SAFETY HAZARD: Driver intoxication reported in vehicle telemetry.")
        elif "kill" in ev_str.lower() or "threat" in ev_str.lower() or "attack" in ev_str.lower():
            block_reasons.append("🚨 SAFETY HAZARD: Hostile driver behavior or threat of violence detected.")
        elif "10" in ev_str or "11" in ev_str or "temp" in ev_str.lower():
            block_reasons.append(f"🔥 THERMAL HAZARD: Engine temperature exceeds safe limits ({safety_risk} Risk).")
        elif "tyre" in ev_str.lower() or "psi" in ev_str.lower():
            block_reasons.append(f"🛞 TYRE HAZARD: Abnormal tyre pressure detected ({safety_risk} Risk).")
        else:
            block_reasons.append(f"🛡️ SAFETY RISK ({safety_risk}): Telemetry breached policy thresholds.")

    # 2. Adversarial Red Team Audit Challenge
    adversarial = state.get("adversarial", {})
    if adversarial.get("challenge_successful", False):
        human_approval_required = True
        flaw = adversarial.get("flaw_description", "").strip()
        if flaw:
            block_reasons.append(f"🔺 RED TEAM CHALLENGE: {flaw}")
        else:
            block_reasons.append("🔺 RED TEAM CHALLENGE: Adversarial audit identified unaddressed risk factors.")

    # 3. Critic Conflicts & Scope Violations
    critic = state.get("critic", {})
    if critic.get("scope_violation_detected", False):
        human_approval_required = True
        block_reasons.append("⚖️ SCOPE VIOLATION: Operations domain contained unverified safety claims.")
    if critic.get("has_conflict", False):
        human_approval_required = True
        block_reasons.append("⚖️ CONFLICT DETECTED: Contradiction found between Safety and Operations findings.")
    if critic.get("requires_more_evidence", False):
        human_approval_required = True
        block_reasons.append("📄 DATA GAP: Critical sensor or operational evidence is missing or corrupted.")

    # 4. Stale Maintenance Records
    for agent_key in ["safety", "maintenance", "operations"]:
        quality = state.get(agent_key, {}).get("evidence_quality", EvidenceQuality.MISSING.value)
        if quality == EvidenceQuality.STALE.value:
            human_approval_required = True
            block_reasons.append(f"🔧 STALE RECORDS: {agent_key.capitalize()} data is outdated (>14 days un-synced).")

    # 5. Max Iterations Exceeded
    if state.get("iteration", 0) >= POLICY['orchestration']['max_iterations']:
        human_approval_required = True
        block_reasons.append("⏳ TIMEOUT: Max agent debate iterations reached without resolution.")

    return {
        "human_approval_required": human_approval_required,
        "block_reasons": block_reasons if block_reasons else ["Routine human review required before dispatch."]
    }
