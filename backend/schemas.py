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
    # Hour 5-7 additions. Optional + default None so telemetry produced by
    # the Hour 1-3 simulator (before this field existed) still validates.
    relative_velocity_mps: Optional[float] = None
    worker_x_m: Optional[float] = None
    worker_y_m: Optional[float] = None

class Telemetry(BaseModel):
    type: str = "telemetry"
    timestamp: datetime
    machine_id: str
    machine_model: str
    operator_id: str
    engine_on: bool
    speed_kmh: float
    seatbelt_fastened: bool
    operating_hours: float=0.0
    machine_state: str = "idle"
    operator_seated: bool
    hydraulic_load_pct: float
    fuel_level_pct: float
    gps: GPS
    proximity: Optional[Proximity] = None

class Alert(BaseModel):
    type: str = "alert"
    alert_id: str
    timestamp: datetime
    category: str      # seatbelt | proximity | idling | unsafe_behavior | overwork | weather | sos
    severity: str      # info | warning | critical
    message: str
    speak: bool = False
    machine_id: str
    operator_id: str
    active: bool = True

class Incident(BaseModel):
    incident_id: str
    machine_id: str
    operator_id: str
    type: str
    severity: str
    description: str
    timestamp: datetime
    resolved: bool = False