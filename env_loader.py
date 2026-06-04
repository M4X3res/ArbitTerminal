"""Загрузка конфигурации из .env файла"""
import os
from pathlib import Path


def load_env():
    """Загрузка переменных окружения из .env файла"""
    env_path = Path(__file__).parent / '.env'
    
    if not env_path.exists():
        print("⚠️  .env файл не найден. Используйте .env.example как шаблон.")
        return
    
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()


def get_api_keys(exchange: str):
    """Получение API ключей для биржи"""
    load_env()
    
    key = os.getenv(f'{exchange.upper()}_API_KEY')
    secret = os.getenv(f'{exchange.upper()}_API_SECRET')
    
    return key, secret
