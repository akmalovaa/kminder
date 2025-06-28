#!/usr/bin/python
import logging
import requests
import hashlib
import argparse


logging.basicConfig(level=logging.INFO, format="INFO - %(message)s")


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--appId",
        dest="appId",
        help="application identifier my.starline.ru",
        default="",
        required=True,
    )
    parser.add_argument(
        "-s",
        "--appSecret",
        dest="appSecret",
        help="account secret my.starline.ru",
        default="",
        required=True,
    )
    parser.add_argument(
        "-l",
        "--login",
        dest="login",
        help="user account login",
        default="",
        required=True,
    )
    parser.add_argument(
        "-p",
        "--password",
        dest="password",
        help="user account password",
        default="",
        required=True,
    )
    args = parser.parse_args()
    logging.debug(
        "appId: {}, appSecret: {}, login: {}, password: {}".format(
            args.appId, args.appSecret, args.login, args.password
        )
    )
    return args


def get_app_code(app_id, app_secret):
    """
    Получение кода приложения для дальнейшего получения токена.
    Идентификатор приложения и пароль выдаются на сайте my.starline.ru раздел разработчикам
    Срок годности кода приложения 1 час.
    :param app_id: Идентификатор приложения
    :param app_secret: Пароль приложения
    :return: Код, необходимый для получения токена приложения
    """
    url = "https://id.starline.ru/apiV3/application/getCode/"
    logging.debug("execute request: {}".format(url))

    payload = {
        "appId": app_id,
        "secret": hashlib.md5(app_secret.encode("utf-8")).hexdigest(),
    }
    response = requests.get(url, params=payload)
    response_data = response.json()
    logging.debug(f"payload : {payload}")
    logging.debug(f"response info: {response}")
    logging.debug(f"response data: {response_data}")
    if int(response_data["state"]) == 1:
        app_code = response_data["desc"]["code"]
        logging.debug(f"Application code: {app_code}")
        return app_code
    raise Exception(response_data)


def get_app_token(app_id, app_secret, app_code):
    """
    Получение токена приложения для дальнейшей авторизации.
    Время жизни токена приложения - 4 часа.
    Идентификатор приложения и пароль можно получить на my.starline.ru.
    :param app_id: Идентификатор приложения
    :param app_secret: Пароль приложения
    :param app_code: Код приложения
    :return: Токен приложения
    """
    url = "https://id.starline.ru/apiV3/application/getToken/"
    logging.debug(f"execute request: {url}")
    payload = {
        "appId": app_id,
        "secret": hashlib.md5((app_secret + app_code).encode("utf-8")).hexdigest(),
    }
    response = requests.get(url, params=payload)
    response_data = response.json()
    logging.debug(f"payload: {payload}")
    logging.debug(f"response info: {response}")
    logging.debug(f"response data: {response_data}")
    if int(response_data["state"]) == 1:
        app_token = response_data["desc"]["token"]
        logging.debug(f"Application token: {app_token}")
        return app_token
    raise Exception(response_data)


def get_slid_token(app_token, user_login, user_password):
    """
     Аутентификация пользователя по логину и паролю.
     Неверные данные авторизации или слишком частое выполнение запроса авторизации с одного
     ip-адреса может привести к запросу капчи.
     Для того, чтобы сервер SLID корректно обрабатывал клиентский IP,
     необходимо проксировать его в параметре user_ip.
     В противном случае все запросы авторизации будут фиксироваться для IP-адреса сервера приложения,
     что приведет к частому требованию капчи.
    :param sid_url: URL StarLineID сервера
    :param app_token: Токен приложения
    :param user_login: Логин пользователя
    :param user_password: Пароль пользователя
    :return: Токен, необходимый для работы с данными пользователя. Данный токен потребуется для авторизации
     на StarLine API сервере. Время жизни токена - 1 год.
    """
    url = "https://id.starline.ru/apiV3/user/login/"
    logging.debug(f"execute request: {url}")
    payload = {"token": app_token}
    data = {}
    data["login"] = user_login
    data["pass"] = hashlib.sha1(user_password.encode("utf-8")).hexdigest()
    # data["user_ip"] = "1.1.1.1"
    # data["captchaSid"] = "rke3TMQbdnyjd"
    # data["captchaImg"] = "T2SyOH"
    response = requests.post(url, params=payload, data=data)
    response_data = response.json()
    logging.debug(f"payload : {payload}")
    logging.debug(f"response info: {response}")
    logging.debug(f"response data: {response_data}")
    if int(response_data["state"]) == 1:
        slid_token = response_data["desc"]["user_token"]
        logging.debug(f"SLID token: {slid_token}")
        return slid_token
    raise Exception(response_data)


def main():
    args = get_args()
    app_code = get_app_code(args.appId, args.appSecret)
    app_token = get_app_token(args.appId, args.appSecret, app_code)
    slid_token = get_slid_token(app_token, args.login, args.password)
    logging.info(f"SLID TOKEN: {slid_token}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error(e)
