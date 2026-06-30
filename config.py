import os
from dotenv import load_dotenv

# Carga las variables desde el archivo .env
load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-por-defecto')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///egreso.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
