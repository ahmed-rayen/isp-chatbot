from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    nvidia_api_key: str
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_model: str = "meta/llama-3.1-8b-instruct"

    class Config:
        env_file = ".env"

settings = Settings()