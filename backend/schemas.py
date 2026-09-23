from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class GPS(BaseModel):
    lat: float
    lon: float

class Proximity(BaseModel):
    object: str
    distance_m: float
    direction: str

class Telemetry(BaseModel):
    type: str = "telemetry"
    timestamp: datetime
    machine_id: str
    machine_model: str
    operator_id: str
    engine_on: bool
    speed_kmh: float
    seatbelt_fastened: bool
    operator_seated: bool
    hydraulic_load_pct: float
    fuel_level_pct: float
    gps: GPS
    proximity: Optional[Proximity] = None

class Alert(BaseModel):
    alert_id: str
    machine_id: str
    operator_id: str
    type: str          # e.g. "seatbelt", "proximity", "idling", "unsafe_behavior"
    severity: str       # "warning" | "critical"
    message: str
    timestamp: datetime

class Incident(BaseModel):
    incident_id: str
    machine_id: str
    operator_id: str
    type: str
    severity: str
    description: str
    timestamp: datetime
    resolved: bool = False