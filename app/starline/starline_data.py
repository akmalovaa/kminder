"""
Модуль для работы с локальным файлом starline_data.json.
Используйте эти функции для получения информации без прямого обращения к API StarLine.
"""

import json
from pathlib import Path
from datetime import datetime

DATA_PATH = Path(__file__).parent.parent / "starline_data.json"


def _load_data():
    if DATA_PATH.exists():
        try:
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def get_status():
    data = _load_data()
    codestring = data.get("codestring")
    if codestring == "OK":
        return "🟢"
    return "🔴"


def get_update_timestamp():
    data = _load_data()
    devices = data.get("user_data", {}).get("devices", [])
    if devices:
        ts = devices[0].get("activity_ts")
        if ts:
            # Преобразуем timestamp в строку нужного формата
            return datetime.fromtimestamp(ts).strftime("%d.%m.%Y %H:%M:%S")
    return None


def get_odb_mileage():
    data = _load_data()
    # Пример: return data.get("user_data", {}).get("devices", [{}])[0].get("obd", {}).get("mileage")
    devices = data.get("user_data", {}).get("devices", [])
    if devices and "obd" in devices[0]:
        return devices[0]["obd"].get("mileage")
    return None
