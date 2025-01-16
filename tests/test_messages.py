import pytest

def test_send_message(client):
    """Тест отправки сообщения в чат"""
    # Создаем тестовый чат
    chat_response = client.post(
        "/chats",
        json={"title": "Test Chat"}
    )
    chat_id = chat_response.json()["id"]
    
    # Отправляем сообщение
    message = "Test message"
    response = client.post(
        f"/chats/{chat_id}/messages",
        json={"content": message}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == message
    assert data["chat_id"] == chat_id

def test_get_chat_messages(client):
    """Тест получения сообщений чата"""
    # Создаем чат и отправляем сообщение
    chat_response = client.post(
        "/chats",
        json={"title": "Test Chat"}
    )
    chat_id = chat_response.json()["id"]
    
    client.post(
        f"/chats/{chat_id}/messages",
        json={"content": "Message 1"}
    )
    
    # Получаем сообщения
    response = client.get(f"/chats/{chat_id}/messages")
    assert response.status_code == 200
    data = response.json()
    assert "messages" in data
    assert len(data["messages"]) > 0