import os
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from datetime import datetime, timezone, timedelta

from models import Vehicle, Location, TyrePressure, VehicleStatus, Scenario
from simulator import VEHICLES, init_vehicles, simulation_loop
from engine import incident_engine_loop, INCIDENTS
from orchestrator import orchestrator_app

app = FastAPI(title="Ops Sentinel - Fleet APIs")
init_vehicles()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    init_vehicles()
    if not os.environ.get("VERCEL"):
        try:
            asyncio.create_task(simulation_loop())
            asyncio.create_task(incident_engine_loop())
        except Exception:
            pass

@app.get("/vehicles")
async def get_all_vehicles() -> List[Vehicle]:
    if not VEHICLES:
        init_vehicles()
    return list(VEHICLES.values())

@app.get("/vehicles/{vehicle_id}")
async def get_vehicle(vehicle_id: str) -> Vehicle:
    if vehicle_id not in VEHICLES:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return VEHICLES[vehicle_id]

@app.get("/vehicles/{vehicle_id}/telemetry")
async def get_telemetry(vehicle_id: str):
    if vehicle_id not in VEHICLES:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    v = VEHICLES[vehicle_id]
    
    if v.scenario == Scenario.TELEMETRY_UNAVAILABLE:
        raise HTTPException(status_code=503, detail="Telemetry Service Unavailable")
        
    data = {
        "speed": v.speed,
        "fuel_level": v.fuel_level,
        "engine_temperature": v.engine_temperature,
        "tyre_pressure": v.tyre_pressure.dict(),
        "timestamp": v.last_updated.isoformat()
    }
    if vehicle_id in CUSTOM_CARGO_MAP:
        c_info = CUSTOM_CARGO_MAP[vehicle_id]
        if c_info.get("driver_status"):
            data["driver_status"] = c_info["driver_status"]
        if c_info.get("judge_notes"):
            data["judge_notes"] = c_info["judge_notes"]
    
    if v.scenario == Scenario.MISSING_EVIDENCE:
        del data["engine_temperature"]
        del data["tyre_pressure"]
        
    return data

@app.get("/vehicles/{vehicle_id}/maintenance")
async def get_maintenance(vehicle_id: str):
    v = VEHICLES.get(vehicle_id)
    if not v:
        raise HTTPException(status_code=404, detail="Vehicle not found")
        
    if v.scenario == Scenario.MAINTENANCE_TIMEOUT:
        await asyncio.sleep(2.0)
        raise HTTPException(status_code=504, detail="Maintenance API Gateway Timeout")
        
    if vehicle_id in CUSTOM_CARGO_MAP:
        cm = CUSTOM_CARGO_MAP[vehicle_id]
        response = {
            "last_service_date": cm.get("last_service_date", "2026-08-15"),
            "open_work_orders": cm.get("open_work_orders", 0),
            "maintenance_risk": "HIGH" if cm.get("open_work_orders", 0) >= 2 else "LOW"
        }
    else:
        response = {
            "last_service_date": "2026-07-15",
            "open_work_orders": 1 if v.scenario in [Scenario.ENGINE_OVERHEAT, Scenario.CRITICAL_SAFETY] else 0,
            "maintenance_risk": "MEDIUM" if v.scenario in [Scenario.ENGINE_OVERHEAT, Scenario.CRITICAL_SAFETY] else "LOW"
        }
    
    if v.scenario == Scenario.STALE_MAINTENANCE:
        stale_time = datetime.now(timezone.utc) - timedelta(hours=400)
        response["last_synced"] = stale_time.isoformat()
    else:
        response["last_synced"] = v.last_updated.isoformat()
        
    return response


def clean_input_str(s: str) -> str:
    if not s:
        return ""
    return s.replace("\r\n", " ").replace("\n", " ").replace("\r", " ").replace('"', "'").replace("\\", "/").strip()

CUSTOM_CARGO_MAP = {}

class AddVehicleRequest(BaseModel):
    vehicle_id: str
    driver: str = "Judge Evaluation"
    destination: str = "Goa"
    cargo: str = "High-Value Freight"
    priority: str = "HIGH"
    route_conditions: str = "Clear Highway"
    engine_temperature: float = 85.0
    speed: float = 70.0
    fuel_level: float = 85.0
    tyre_pressure_fl: float = 32.0
    tyre_pressure_fr: float = 32.0
    tyre_pressure_rl: float = 32.0
    tyre_pressure_rr: float = 32.0
    driver_status: str = "Shift ends in 30 minutes"
    open_work_orders: int = 0
    last_service_date: str = "2026-08-15"
    judge_notes: str = ""
    scenario: str = "NORMAL"

@app.post("/vehicles/add")
async def add_custom_vehicle(req: AddVehicleRequest):
    min_tyre = min(req.tyre_pressure_fl, req.tyre_pressure_fr, req.tyre_pressure_rl, req.tyre_pressure_rr)
    if req.engine_temperature > 105 or (req.engine_temperature > 100 and min_tyre < 25):
        sc = Scenario.CRITICAL_SAFETY
    elif req.engine_temperature > 100:
        sc = Scenario.ENGINE_OVERHEAT
    elif min_tyre < 25:
        sc = Scenario.TYRE_PRESSURE_DROP
    else:
        sc = Scenario.NORMAL
        
    vid = req.vehicle_id.upper().strip()
    if not vid.startswith("TRUCK-"):
        vid = f"TRUCK-{vid}"

    from simulator import TRUCK_PROFILES
    TRUCK_PROFILES[vid] = {
        "route": f"Pune to {req.destination}",
        "driver": req.driver,
        "scenario": sc,
        "temp_range": (max(50.0, req.engine_temperature - 2), req.engine_temperature + 2),
        "speed_range": (max(0.0, req.speed - 4), req.speed + 4),
        "fuel_start": req.fuel_level,
        "is_custom": True
    }

    CUSTOM_CARGO_MAP[vid] = {
        "dest": clean_input_str(req.destination),
        "cargo": clean_input_str(req.cargo),
        "priority": req.priority,
        "cond": clean_input_str(req.route_conditions),
        "driver": clean_input_str(req.driver),
        "driver_status": clean_input_str(req.driver_status),
        "open_work_orders": req.open_work_orders,
        "last_service_date": req.last_service_date,
        "judge_notes": clean_input_str(req.judge_notes),
        "is_custom": True
    }

    VEHICLES[vid] = Vehicle(
        vehicle_id=vid,
        location=Location(lat=18.5204, lng=73.8567),
        speed=req.speed,
        fuel_level=req.fuel_level,
        engine_temperature=req.engine_temperature,
        tyre_pressure=TyrePressure(
            front_left=req.tyre_pressure_fl,
            front_right=req.tyre_pressure_fr,
            rear_left=req.tyre_pressure_rl,
            rear_right=req.tyre_pressure_rr
        ),
        status=VehicleStatus.ACTIVE,
        scenario=sc,
        last_updated=datetime.now(timezone.utc)
    )

    return {"message": f"Vehicle {vid} created successfully", "vehicle_id": vid}


@app.get("/vehicles/{vehicle_id}/route")
async def get_route(vehicle_id: str):
    v = VEHICLES.get(vehicle_id)
    if not v:
        raise HTTPException(status_code=404, detail="Vehicle not found")
        
    if v.scenario == Scenario.GPS_UNAVAILABLE:
        raise HTTPException(status_code=503, detail="Route Service Unavailable")
        
    # Dynamic cargo data
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
    
    if vehicle_id in CUSTOM_CARGO_MAP:
        info = CUSTOM_CARGO_MAP[vehicle_id]
    else:
        info = cargo_map.get(vehicle_id, {"dest": "Unknown", "cargo": "General Cargo", "priority": "LOW", "cond": "Unknown"})
        
    return {
        "destination": info["dest"],
        "estimated_arrival": "17:30",
        "cargo": info["cargo"],
        "route_conditions": info["cond"],
        "driver_status": info.get("driver_status", "Shift ends in 30 minutes"),
        "judge_notes": info.get("judge_notes", ""),
        "priority": info["priority"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/incidents")
async def get_all_incidents():
    return list(INCIDENTS.values())

class ScenarioRequest(BaseModel):
    scenario: Scenario

@app.post("/vehicles/{vehicle_id}/scenario")
async def set_scenario(vehicle_id: str, req: ScenarioRequest):
    if vehicle_id not in VEHICLES:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    VEHICLES[vehicle_id].scenario = req.scenario
    return {"message": f"Scenario for {vehicle_id} set to {req.scenario.value}"}

@app.post("/incidents/{vehicle_id}/investigate")
def trigger_investigation(vehicle_id: str):
    if vehicle_id not in VEHICLES:
        raise HTTPException(status_code=404, detail="Vehicle not found")
        
    initial_state = {
        "vehicle_id": vehicle_id,
        "safety": None,
        "maintenance": None,
        "operations": None,
        "critic": None,
        "adversarial": None,
        "decision": None,
        "iteration": 0
    }
    
    final_state = orchestrator_app.invoke(initial_state)
    return final_state

@app.get("/")
def read_root():
    return FileResponse(os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html"))
