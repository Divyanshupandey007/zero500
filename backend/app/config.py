from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME:str= "Zero500"
    APP_VERSION:str="0.2.0"
    DEBUG:bool=True

    #Gemini Configuration
    GEMINI_API_KEY:str=""
    GEMINI_MODEL:str="gemini-3.1-flash-lite"

    class Config:
        env_file=".env"
        extra="ignore"

settings=Settings()