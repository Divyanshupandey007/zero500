from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME:str= "Zero500"
    APP_VERSION:str="0.2.0"
    DEBUG:bool=True

    #Gemini Configuration
    GEMINI_API_KEY:str=""
    GEMINI_MODEL:str="gemini-3.5-flash"
    DATABASE_URL: str = ""

    #Embedding configuration
    EMBEDDING_MODEL:str="gemini-embedding-001"
    EMBEDDING_DIMENSIONS:int=768

    class Config:
        env_file=".env"
        extra="ignore"

settings=Settings()