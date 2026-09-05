import os
import yaml
from typing import Dict, Any, TypedDict
from langgraph.graph import StateGraph, END
from agents import run_safety_agent, run_maintenance_agent, run_operations_agent, run_critic_agent, run_adversarial_agent, run_decision_agent
from policy_engine import enforce_policy

class HarnessState(TypedDict, total=False):
    vehicle_id: str
    iteration: int
    safety: Dict[str, Any]
    maintenance: Dict[str, Any]
    operations: Dict[str, Any]
    critic: Dict[str, Any]
    adversarial: Dict[str, Any]
    decision: Dict[str, Any]

policy_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "policy.yaml")
with open(policy_file_path, "r") as f:
    POLICY = yaml.safe_load(f)

def safety_node(state: HarnessState):
    print(f"--- [Node] Safety Agent running for {state['vehicle_id']} ---")
    assessment = run_safety_agent(state['vehicle_id'])
    return {"safety": assessment.dict()}

def maintenance_node(state: HarnessState):
    print(f"--- [Node] Maintenance Agent running for {state['vehicle_id']} ---")
    assessment = run_maintenance_agent(state['vehicle_id'])
    return {"maintenance": assessment.dict()}

def operations_node(state: HarnessState):
    print(f"--- [Node] Operations Agent running for {state['vehicle_id']} ---")
    assessment = run_operations_agent(state['vehicle_id'])
    return {"operations": assessment.dict()}

def critic_node(state: HarnessState):
    print("--- [Node] Critic Agent running ---")
    assessment = run_critic_agent(state['safety'], state['maintenance'], state['operations'])
    return {"critic": assessment.dict(), "iteration": state.get("iteration", 0) + 1}

def adversarial_node(state: HarnessState):
    print("--- [Node] Adversarial Agent running ---")
    assessment = run_adversarial_agent(state['safety'], state['maintenance'], state['operations'], state['critic'])
    return {"adversarial": assessment.dict()}

def critic_router(state: HarnessState):
    # Hackathon override: NEVER loop so it finishes in 15 seconds instead of 2 minutes!
    return "decision"

def decision_node(state: HarnessState):
    print("--- [Node] Policy Engine & Decision Agent running ---")
    
    # 1. Deterministic Policy Engine
    policy_result = enforce_policy(state)
    
    # 2. LLM Recommendation
    recommendation = run_decision_agent(state['safety'], state['maintenance'], state['operations'], state['critic'], state['adversarial'])
    
    final = {
        "recommendation": recommendation.recommendation,
        "human_approval_required": policy_result["human_approval_required"],
        "block_reasons": policy_result["block_reasons"]
    }
    return {"decision": final}

workflow = StateGraph(HarnessState)

workflow.add_node("safety", safety_node)
workflow.add_node("maintenance", maintenance_node)
workflow.add_node("operations", operations_node)
workflow.add_node("critic", critic_node)
workflow.add_node("adversarial", adversarial_node)
workflow.add_node("decision", decision_node)

workflow.set_entry_point("safety")
workflow.add_edge("safety", "maintenance")
workflow.add_edge("maintenance", "operations")
workflow.add_edge("operations", "critic")
workflow.add_edge("critic", "adversarial")
workflow.add_conditional_edges(
    "adversarial",
    critic_router,
    {
        "safety": "safety",
        "decision": "decision"
    }
)
workflow.add_edge("decision", END)

orchestrator_app = workflow.compile()
