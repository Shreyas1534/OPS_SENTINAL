import asyncio
import random
from datetime import datetime, timezone
from models import Vehicle, Location, TyrePressure, VehicleStatus, Scenario

VEHICLES = {}

TRUCK_PROFILES = {
    "TRUCK-1001": {"route": "Pune to Mumbai",      "driver": "R. Kadam",     "scenario": Scenario.NORMAL,              "temp_range": (82, 94),  "speed_range": (55, 85),  "fuel_start": 72},
    "TRUCK-1002": {"route": "Pune to Bengaluru",    "driver": "S. Patil",     "scenario": Scenario.ENGINE_OVERHEAT,     "temp_range": (100, 112), "speed_range": (40, 65),  "fuel_start": 45},
    "TRUCK-1003": {"route": "Pune to Nashik",       "driver": "A. Verma",     "scenario": Scenario.TYRE_PRESSURE_DROP,  "temp_range": (78, 88),  "speed_range": (60, 80),  "fuel_start": 88},
    "TRUCK-1004": {"route": "Pune to Hyderabad",    "driver": "N. Deshmukh",  "scenario": Scenario.STALE_MAINTENANCE,   "temp_range": (85, 96),  "speed_range": (45, 70),  "fuel_start": 31},
    "TRUCK-1005": {"route": "Pune to Delhi",        "driver": "V. Singh",     "scenario": Scenario.NORMAL,              "temp_range": (80, 90),  "speed_range": (65, 95),  "fuel_start": 62},
    "TRUCK-1006": {"route": "Pune to Kolkata",      "driver": "M. Das",       "scenario": Scenario.CRITICAL_SAFETY,     "temp_range": (110, 118), "speed_range": (30, 50),  "fuel_start": 19},
    "TRUCK-1007": {"route": "Pune to Chennai",      "driver": "K. Reddy",     "scenario": Scenario.NORMAL,              "temp_range": (76, 86),  "speed_range": (70, 90),  "fuel_start": 81},
    "TRUCK-1008": {"route": "Pune to Ahmedabad",    "driver": "J. Patel",     "scenario": Scenario.NORMAL,              "temp_range": (83, 91),  "speed_range": (50, 75),  "fuel_start": 55},
    "TRUCK-1009": {"route": "Pune to Jaipur",       "driver": "R. Sharma",    "scenario": Scenario.MISSING_EVIDENCE,    "temp_range": (88, 98),  "speed_range": (55, 80),  "fuel_start": 40},
    "TRUCK-1010": {"route": "Pune to Lucknow",      "driver": "P. Yadav",     "scenario": Scenario.NORMAL,              "temp_range": (79, 87),  "speed_range": (60, 85),  "fuel_start": 67},
}

def init_vehicles():
    base_lat = 18.5204
    base_lng = 73.8567
    
    for i in range(1, 11):
        vid = f"TRUCK-{1000 + i}"
        profile = TRUCK_PROFILES[vid]
        
        temp_lo, temp_hi = profile["temp_range"]
        spd_lo, spd_hi = profile["speed_range"]
        
        VEHICLES[vid] = Vehicle(
            vehicle_id=vid,
            location=Location(lat=base_lat + random.uniform(-0.1, 0.1), lng=base_lng + random.uniform(-0.1, 0.1)),
            speed=random.uniform(spd_lo, spd_hi),
            fuel_level=profile["fuel_start"] + random.uniform(-5, 5),
            engine_temperature=random.uniform(temp_lo, temp_hi),
            tyre_pressure=TyrePressure(
                front_left=random.uniform(30, 34),
                front_right=random.uniform(30, 34),
                rear_left=random.uniform(30, 34),
                rear_right=random.uniform(30, 34),
            ),
            status=VehicleStatus.ACTIVE,
            scenario=profile["scenario"],
            last_updated=datetime.now(timezone.utc)
        )

async def simulation_loop():
    while True:
        now = datetime.now(timezone.utc)
        for vid, v in VEHICLES.items():
            profile = TRUCK_PROFILES.get(vid, {})
            if profile.get("is_custom", False) or vid.startswith("TRUCK-JUDGE"):
                v.last_updated = now
                continue
            spd_lo, spd_hi = profile["speed_range"]
            temp_lo, temp_hi = profile["temp_range"]
            
            # Speed fluctuates noticeably 
            v.speed += random.uniform(-4.0, 4.0)
            v.speed = max(spd_lo * 0.8, min(spd_hi * 1.1, v.speed))
            
            # Fuel slowly drains
            v.fuel_level = max(5.0, v.fuel_level - random.uniform(0.01, 0.05))
            
            # All tyres fluctuate slightly
            v.tyre_pressure.front_right += random.uniform(-0.15, 0.15)
            v.tyre_pressure.front_right = max(29.0, min(35.0, v.tyre_pressure.front_right))
            v.tyre_pressure.rear_left += random.uniform(-0.15, 0.15)
            v.tyre_pressure.rear_left = max(29.0, min(35.0, v.tyre_pressure.rear_left))
            v.tyre_pressure.rear_right += random.uniform(-0.15, 0.15)
            v.tyre_pressure.rear_right = max(29.0, min(35.0, v.tyre_pressure.rear_right))
            
            # Scenario-specific behavior
            if v.scenario in [Scenario.NORMAL, Scenario.STALE_MAINTENANCE, Scenario.MAINTENANCE_TIMEOUT, Scenario.MISSING_EVIDENCE]:
                v.engine_temperature += random.uniform(-1.5, 1.5)
                v.engine_temperature = max(temp_lo, min(temp_hi, v.engine_temperature))
                v.tyre_pressure.front_left += random.uniform(-0.15, 0.15)
                v.tyre_pressure.front_left = max(29.0, min(35.0, v.tyre_pressure.front_left))
                
            elif v.scenario == Scenario.ENGINE_OVERHEAT:
                v.engine_temperature += random.uniform(0.3, 1.5)
                v.engine_temperature = max(temp_lo, min(temp_hi, v.engine_temperature))
                v.tyre_pressure.front_left += random.uniform(-0.15, 0.15)
                v.tyre_pressure.front_left = max(29.0, min(35.0, v.tyre_pressure.front_left))
                
            elif v.scenario == Scenario.CRITICAL_SAFETY:
                v.engine_temperature = max(temp_lo, min(temp_hi, v.engine_temperature + random.uniform(0.5, 2.0)))
                v.tyre_pressure.front_left += random.uniform(-0.15, 0.15)
                v.tyre_pressure.front_left = max(29.0, min(35.0, v.tyre_pressure.front_left))
                
            elif v.scenario == Scenario.TYRE_PRESSURE_DROP:
                v.engine_temperature += random.uniform(-1.5, 1.5)
                v.engine_temperature = max(temp_lo, min(temp_hi, v.engine_temperature))
                v.tyre_pressure.front_left = max(16.0, v.tyre_pressure.front_left - random.uniform(0.3, 0.8))
            
            v.location.lat += random.uniform(-0.001, 0.001)
            v.location.lng += random.uniform(-0.001, 0.001)
            
            v.last_updated = now
            
        await asyncio.sleep(2)
