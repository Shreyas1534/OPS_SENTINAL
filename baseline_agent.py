import os
import httpx
from dotenv import load_dotenv
from groq import Groq
import instructor
from schemas import FinalDecision

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
client = instructor.from_groq(Groq(api_key=api_key))
MODEL = "openai/gpt-oss-120b"

def run_baseline(vehicle_id: str) -> FinalDecision:
    # 1. Fetch all data like a standard single agent
    try:
        t = httpx.get(f"http://127.0.0.1:8000/vehicles/{vehicle_id}/telemetry").json()
    except Exception as e:
        t = {"error": str(e)}
    try:
        m = httpx.get(f"http://127.0.0.1:8000/vehicles/{vehicle_id}/maintenance").json()
    except Exception as e:
        m = {"error": str(e)}
    try:
        o = httpx.get(f"http://127.0.0.1:8000/vehicles/{vehicle_id}/route").json()
    except Exception as e:
        o = {"error": str(e)}

    system_prompt = """You are an AI assistant. Make a final operational recommendation based on the following vehicle data.
    CRITICAL: Output the exact JSON schema."""
    
    return client.chat.completions.create(
        model=MODEL,
        response_model=FinalDecision,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": f"Telemetry: {t}\nMaintenance: {m}\nRoute: {o}"}],
        max_retries=2
    )
