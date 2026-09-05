from enum import Enum
from pydantic import BaseModel
from datetime import datetime

class Location(BaseModel):
    lat: float
    lng: float

class TyrePressure(BaseModel):
    front_left: float
    front_right: float
    rear_left: float
    rear_right: float

class VehicleStatus(str, Enum):
    ACTIVE = "ACTIVE"
    IN_MAINTENANCE = "IN_MAINTENANCE"
    OUT_OF_SERVICE = "OUT_OF_SERVICE"

class Scenario(str, Enum):
    NORMAL = "NORMAL"
    ENGINE_OVERHEAT = "ENGINE_OVERHEAT"
    TYRE_PRESSURE_DROP = "TYRE_PRESSURE_DROP"
    STALE_MAINTENANCE = "STALE_MAINTENANCE"
    MAINTENANCE_TIMEOUT = "MAINTENANCE_TIMEOUT"
    TELEMETRY_UNAVAILABLE = "TELEMETRY_UNAVAILABLE"
    GPS_UNAVAILABLE = "GPS_UNAVAILABLE"
    CONFLICTING_AGENTS = "CONFLICTING_AGENTS"
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    MALFORMED_OUTPUT = "MALFORMED_OUTPUT"
    UNKNOWN_INCIDENT = "UNKNOWN_INCIDENT"
    CRITICAL_SAFETY = "CRITICAL_SAFETY"
    DUPLICATE_INCIDENT = "DUPLICATE_INCIDENT"
    CONTRADICTORY_HISTORY = "CONTRADICTORY_HISTORY"
    AGENT_SCOPE_VIOLATION = "AGENT_SCOPE_VIOLATION"

class Vehicle(BaseModel):
    vehicle_id: str
    location: Location
    speed: float
    fuel_level: float
    engine_temperature: float
    tyre_pressure: TyrePressure
    status: VehicleStatus
    scenario: Scenario
    last_updated: datetime

class Incident(BaseModel):
    incident_id: str
    vehicle_id: str
    type: str
    severity: str
    timestamp: datetime
    status: str
