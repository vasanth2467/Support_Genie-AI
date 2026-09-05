from typing import Optional
from pydantic import BaseModel

class AccountModel(BaseModel):
    account_id: str
    customer_id: str
    plan_name: str
    category: str
    monthly_rate: float
    balance_due: float
    billing_cycle_day: int
    status: str
    data_limit_gb: float
    data_used_gb: float
    roaming_enabled: bool

class LineTelemetryModel(BaseModel):
    account_id: str
    modem_online: bool
    optical_rx_power_dbm: float
    optical_los_alarm: bool
    router_ip: Optional[str] = None
    area_outage_detected: bool
    area_outage_eta: Optional[str] = None
    last_reboot_timestamp: Optional[str] = None

class CustomerDetailModel(BaseModel):
    customer_id: str
    full_name: str
    email: str
    phone: str
    address: str
    verification_status: str
    account: Optional[AccountModel] = None
    telemetry: Optional[LineTelemetryModel] = None
    demo_tag: Optional[str] = None
