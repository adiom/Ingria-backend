import pytest
from fastapi.testclient import TestClient
from datetime import datetime
import os
from ..main import app, connect_to_db

client = TestClient(app)

# Фикстуры для тестов
@pytest.fixture
def test_db():
    """Создает тестовую базу данных и необходимые таблицы"""
    conn = connect_to_db()
    cursor = conn.cursor()
    
    # Создаем тестовые таблицы
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            session_id TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS chats (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            title TEXT,
            model_type TEXT NOT NULL DEFAULT 'gemini',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS chat_messages (
            id SERIAL PRIMARY KEY,
            chat_id INTEGER REFERENCES chats(id),
            role TEXT,
            content TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    
    yield conn
    
    # Очищаем тестовые данные
    cursor.execute("""
        DELETE FROM chat_messages;
        DELETE FROM chats;
        DELETE FROM users;
    """)
    conn.commit()
    conn.close()

@pytest.fixture
def test_user(test_db):
    """Создает тестового пользователя"""
    cursor = test_db.cursor()
    session_id = "test_session_id"
    cursor.execute(
        "INSERT INTO users (session_id, created_at) VALUES (%s, %s) RETURNING id;",
        (session_id, datetime.now())
    )
    user_id = cursor.fetchone()[0]
    test_db.commit()
    return {"id": user_id, "session_id": session_id}

@pytest.fixture
def test_chat(test_db, test_user):
    """Создает тестовый чат"""
    cursor = test_db.cursor()
    cursor.execute(
        "INSERT INTO chats (user_id, title) VALUES (%s, %s) RETURNING id;",
        (test_user["id"], "Test Chat")
    )
    chat_id = cursor.fetchone()[0]
    test_db.commit()
    return chat_id

# Тесты API эндпоинтов
def test_create_chat(test_user):
    """Тест создания нового чата"""
    response = client.post(
        "/chat/new",
        json={
            "title": "New Test Chat",
            "role": "test assistant",
            "model_type": "gemini"
        },
        cookies={"session_id": test_user["session_id"]}
    )
    assert response.status_code == 200
    data = response.json()
    assert "chat_id" in data
    assert data["title"] == "New Test Chat"

def test_send_message(test_chat):
    """Тест отправки сообщения в чат"""
    response = client.post(
        f"/chat/{test_chat}/message",
        json={
            "content": "Test message",
            "role": "user"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["content"] != ""
    assert data["role"] == "assistant"

def test_get_chat_details(test_chat, test_user):
    """Тест получения деталей чата"""
    response = client.get(f"/chat/{test_chat}")
    assert response.status_code == 200
    data = response.json()
    assert data["chat_id"] == test_chat
    assert "messages" in data

def test_get_chats_list(test_user):
    """Тест получения списка чатов"""
    response = client.get(
        "/chats",
        cookies={"session_id": test_user["session_id"]}
    )
    assert response.status_code == 200
    data = response.json()
    assert "chats" in data

def test_ai_chat():
    """Тест универсального эндпоинта для общения с ИИ"""
    response = client.post(
        "/ai/chat",
        json={
            "ai_model_config": {
                "model_type": "gemini",
                "api_key": "test_key",
                "endpoint": "test_endpoint",
                "system_prompt": "You are a helpful assistant"
            },
            "message": "Hello",
            "chat_id": None
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data

# Тесты обработки файлов
def test_analyze_image():
    """Тест анализа изображения"""
    # Создаем тестовое изображение
    image_path = "test_image.jpg"
    with open(image_path, "wb") as f:
        f.write(b"fake image content")
    
    with open(image_path, "rb") as f:
        response = client.post(
            "/analyze",
            files={"file": ("test_image.jpg", f, "image/jpeg")}
        )
    
    os.remove(image_path)
    assert response.status_code == 200
    data = response.json()
    assert "description" in data

# Тесты обработки ошибок
def test_chat_not_found():
    """Тест обработки несуществующего чата"""
    response = client.get("/chat/99999")
    assert response.status_code == 404

def test_invalid_message():
    """Тест отправки некорректного сообщения"""
    response = client.post(
        "/chat/1/message",
        json={"invalid": "data"}
    )
    assert response.status_code == 422

def test_invalid_ai_config():
    """Тест некорректной конфигурации ИИ"""
    response = client.post(
        "/ai/chat",
        json={
            "ai_model_config": {
                "model_type": "invalid_model",
                "api_key": "test_key",
                "endpoint": "test_endpoint"
            },
            "message": "Hello"
        }
    )
    assert response.status_code == 500
