import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
    LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
    PORT = 5000
    DEBUG = True
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///stock_bot.db')