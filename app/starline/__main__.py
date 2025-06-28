import logging
import yaml
import re

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Form
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager

from pathlib import Path
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler


import uvicorn

from starline.settings import settings
from starline.starline_api import StarLineAPI
from starline.starline_data import get_odb_mileage, get_status, get_update_timestamp


LOG_FORMAT = "%(asctime)s %(levelname)s: %(message)s"
DATE_FORMAT = "%d-%m-%Y %H:%M:%S"
BASE_DIR = Path(__file__).parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
SERVICES_YAML_PATH = Path(__file__).parent.parent / "services.yaml"

for handler in logging.getLogger().handlers:
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))


def fetch_starline_info():
    logging.debug("Fetching data from StarLine API")
    try:
        api = StarLineAPI(settings.starline_slid_token)
        save_result = api.save_data_to_file()
        if save_result:
            logging.debug("Success - starline api save_data_to_file")
        else:
            logging.warning("Failed - starline api save_data_to_file")
    except Exception as e:
        logging.error(f"Error save data from StarLine API: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    fetch_starline_info()
    scheduler = BackgroundScheduler()
    scheduler.add_job(fetch_starline_info, "interval", minutes=2)
    scheduler.start()
    logging.debug("Background OBD fetch scheduler started")
    yield
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def load_services_yaml() -> dict:
    """
    Загружает services.yaml и возвращает словарь сервисов.
    В случае ошибки возвращает пустой словарь и пишет ошибку в лог.
    """
    try:
        with open(SERVICES_YAML_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            raise ValueError("services.yaml должен содержать словарь")
        return data
    except Exception as e:
        logging.error(f"Ошибка при чтении services.yaml: {e}", exc_info=True)
        return {}


def get_services(mileage: int) -> list:
    """
    Возвращает список сервисов с полями:
      - description: название сервиса
      - latest_action_km: пробег последнего обслуживания
      - range_km: регламент обслуживания
      - remain_km: остаток расчет по формуле (range_km - (mileage - latest_action_km))
    :param mileage: текущий пробег автомобиля
    :return: список словарей с данными по сервисам
    """
    data = load_services_yaml()
    result = []
    for service in data.values():
        if not isinstance(service, dict):
            continue
        desc = service.get("description")
        latest_action_km = service.get("latest_action_km")
        range_km = service.get("range_km")
        if (
            desc is not None
            and isinstance(latest_action_km, int)
            and isinstance(range_km, int)
            and isinstance(mileage, int)
        ):
            remain_km = range_km - (mileage - latest_action_km)
            result.append(
                {
                    "description": desc,
                    "latest_action_km": latest_action_km,
                    "range_km": range_km,
                    "remain_km": remain_km,
                }
            )
    return result


def update_service_action(service_name: str, mileage: int):
    """
    Обновляет latest_action_km если в истории обслуживания выбран уже созданный сервис
    """
    data = load_services_yaml()
    updated = False
    for service in data.values():
        if isinstance(service, dict) and service.get("description") == service_name:
            service["latest_action_km"] = mileage
            updated = True
    if updated:
        try:
            with open(SERVICES_YAML_PATH, "w", encoding="utf-8") as f:
                yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
            logging.info(f"Service '{service_name}' successfully updated")
        except Exception as e:
            logging.error(f"Recording error services.yaml: {e}", exc_info=True)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    mileage = int(get_odb_mileage())
    services = get_services(mileage)
    logging.debug(f"services: {services}")
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "mileage": mileage,
            "status": get_status(),
            "update_ts": get_update_timestamp(),
            "services": services,
        },
    )


@app.get("/history", response_class=HTMLResponse)
async def history(request: Request):
    mileage = get_odb_mileage()
    services = get_services(mileage)
    service_names = [s["description"] for s in services]
    history_path = Path(__file__).parent.parent / "services_history.yaml"
    if history_path.exists():
        with open(history_path, "r", encoding="utf-8") as f:
            history_data = yaml.safe_load(f) or []
    else:
        history_data = []
    current_date = datetime.now().strftime("%d.%m.%Y")
    return templates.TemplateResponse(
        "history.html",
        {
            "request": request,
            "history": history_data,
            "current_date": current_date,
            "mileage": mileage,
            "service_names": service_names,
        },
    )


@app.post("/history/add")
async def add_history_entry(
    request: Request,
    date: str = Form(...),
    mileage: int = Form(...),
    service: str = Form(...),
    description: str = Form(""),
    cost: int = Form(...),
):
    if not re.match(r"^\d{2}\.\d{2}\.\d{4}$", date):
        return RedirectResponse("/history", status_code=303)
    if not (0 <= mileage <= 2000000):
        return RedirectResponse("/history", status_code=303)
    if not (0 <= cost <= 2000000):
        return RedirectResponse("/history", status_code=303)
    if len(description) > 500:
        description = description[:500]
    if len(service) > 100:
        service = service[:100]

    new_entry = {
        "date": date,
        "mileage": mileage,
        "service": service,
        "description": description,
        "cost": cost,
    }
    history_path = Path(__file__).parent.parent / "services_history.yaml"
    if history_path.exists():
        with open(history_path, "r", encoding="utf-8") as f:
            history_data = yaml.safe_load(f) or []
    else:
        history_data = []
    history_data.append(new_entry)
    with open(history_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(history_data, f, allow_unicode=True, sort_keys=False)
    update_service_action(service, mileage)
    return RedirectResponse("/history", status_code=303)


if __name__ == "__main__":
    logging.info("APP start ✅, listening on port 8001")
    uvicorn.run(app, host="0.0.0.0", port=8001, log_config=None)
