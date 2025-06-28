import logging
import requests
import json
from pathlib import Path


logging.basicConfig(level=logging.INFO, format="INFO - %(message)s")


class StarLineAPI:
    def __init__(self, slid_token: str):
        self.slid_token = slid_token
        self.slnet_token = None
        self.user_id = None
        self.device_id = None

    def authenticate(self):
        """
        Получить slnet_token и user_id по slid_token
        Ручка /auth.slid может потребовать каптчу при частых обращениях
        """
        url = "https://developer.starline.ru/json/v2/auth.slid"
        logging.debug(f"execute request: {url}")
        data = {"slid_token": self.slid_token}
        try:
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()
            response_data = response.json()
            slnet_token = response.cookies.get("slnet")
            user_id = response_data.get("user_id")
            if not slnet_token or not user_id:
                raise Exception("Failed to get slnet_token or user_id")
            self.slnet_token = slnet_token
            self.user_id = user_id
            logging.debug("StarLine authentication was successful")
        except Exception as e:
            logging.error(f"StarLine auth error: {e}", exc_info=True)
            raise

    def fetch_user_data(self):
        """
        Получить данные по устройствам пользователя, автоматически обновляя slnet_token при необходимости
        Ответ содержит полное состояние устройств
        """
        if not self.slnet_token or not self.user_id:
            self.authenticate()
        url = f"https://developer.starline.ru/json/v3/user/{self.user_id}/data"
        headers = {"Cookie": f"slnet={self.slnet_token}"}
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 401:
                logging.debug("slnet_token expired, re-authenticating...")
                self.authenticate()
                headers = {"Cookie": f"slnet={self.slnet_token}"}
                response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            logging.debug("User data has been successfully received")
            return response.json()
        except Exception as e:
            logging.error(f"Error fetch user data StarLine: {e}", exc_info=True)
            raise

    def save_data_to_file(self):
        """
        Получает данные пользователя через fetch_user_data() и сохраняет их в starline_data.json
        """
        try:
            data = self.fetch_user_data()
            file_path = Path(__file__).parent.parent / "starline_data.json"
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logging.debug("starline_data.json been updated successfully")
            return True
        except Exception as e:
            logging.error(f"Error save data - starline_data.json: {e}", exc_info=True)
            return False
