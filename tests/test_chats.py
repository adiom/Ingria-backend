import pytest
from fastapi.testclient import TestClient

def test_create_chat(client):
    """Тест создания нового чата"""
    response = client.post(
        "/chats",
        json={"title": "Test Chat"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["title"] == "Test Chat"

def test_get_chats_list(client):
    """Тест получения списка чатов"""
    response = client.get("/chats")
    assert response.status_code == 200
    data = response.json()
    assert "chats" in data
    assert isinstance(data["chats"], list)

def test_get_chat_by_id(client):
    """Тест получения конкретного чата по ID"""
    # Сначала создаем чат
    create_response = client.post(
        "/chats",
        json={"title": "Test Chat"}
    )
    chat_id = create_response.json()["id"]
    
    # Получаем созданный чат
    response = client.get(f"/chats/{chat_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == chat_id