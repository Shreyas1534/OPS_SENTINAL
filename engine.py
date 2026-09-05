import asyncio
from datetime import datetime
from models import Incident
from simulator import VEHICLES

INCIDENTS = {}

async def incident_engine_loop():
    while True:
        for vid, v in VEHICLES.items():
            if any(inc.vehicle_id == vid and inc.status == "OPEN" for inc in INCIDENTS.values()):
                continue
                
            if v.engine_temperature > 100 and v.tyre_pressure.front_left < 25:
                inc_id = f"INC-{vid.split('-')[1]}"
                INCIDENTS[inc_id] = Incident(
                    incident_id=inc_id,
                    vehicle_id=vid,
                    type="CRITICAL_SAFETY_ANOMALY",
                    severity="HIGH",
                    timestamp=datetime.now(),
                    status="OPEN"
                )
            elif v.engine_temperature > 100:
                inc_id = f"INC-{vid.split('-')[1]}"
                INCIDENTS[inc_id] = Incident(
                    incident_id=inc_id,
                    vehicle_id=vid,
                    type="ENGINE_OVERHEAT",
                    severity="HIGH",
                    timestamp=datetime.now(),
                    status="OPEN"
                )
            elif v.tyre_pressure.front_left < 25:
                inc_id = f"INC-{vid.split('-')[1]}"
                INCIDENTS[inc_id] = Incident(
                    incident_id=inc_id,
                    vehicle_id=vid,
                    type="TYRE_PRESSURE_CRITICAL",
                    severity="HIGH",
                    timestamp=datetime.now(),
                    status="OPEN"
                )
                
        await asyncio.sleep(2)
