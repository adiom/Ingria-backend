import pytest
import os
from dotenv import load_dotenv

@pytest.fixture(autouse=True)
def setup_test_env():
    """Настраивает тестовое окружение"""
    load_dotenv()
    # Устанавливаем тестовые переменные окружения
    os.environ["POSTGRES_DB"] = "test_ingraDB"
    os.environ["GOOGLE_API_KEY"] = "test_key"
    yield