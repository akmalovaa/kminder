from typing import Optional
from pydantic import BaseModel


class OBDData(BaseModel):
    fuel_litres: Optional[float]
    fuel_percent: Optional[int]
    mileage: Optional[int]
    ts: Optional[int]
    dist_to_empty: Optional[int]
    fuel_ts: Optional[int]
    mileage_ts: Optional[int]
    fuel_reserve_ts: Optional[int]


class CommonData(BaseModel):
    gps_lvl: Optional[int]
    gsm_lvl: Optional[int]
    ctemp: Optional[int]
    etemp: Optional[int]
    mayak_temp: Optional[float]
    ts: Optional[int]
    reg_date: Optional[int]
    heater_liquid_temp: Optional[float]
    heater_air_temp: Optional[float]
    motohours_reset_ts: Optional[int]
    battery: Optional[float]
    battery_type: Optional[str]


class BalanceData(BaseModel):
    key: Optional[str]
    value: Optional[int]
    state: Optional[int]
    operator: Optional[str]
    currency: Optional[str]
    url_payment: Optional[str]
    number: Optional[str]
    slot: Optional[int]
    ts: Optional[int]
