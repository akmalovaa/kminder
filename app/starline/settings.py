import pydantic_settings


class Settings(pydantic_settings.BaseSettings):
    log_level: str = "INFO"
    starline_slid_token: str = "yourtoken:4200042"


settings: Settings = Settings()
