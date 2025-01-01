# INGRIA FastAPI BACKEND

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import google.generativeai as genai
import os
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import logging
import psycopg2
from datetime import datetime
from typing import List, Optional
import uuid
from starlette.requests import Request

# Настройка логгера
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

# Получение API-ключа Gemini из переменной окружения
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_DB = os.getenv("POSTGRES_DB", "ingraDB")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "122887")

if not GOOGLE_API_KEY:
    print("Ошибка: Не найден API-ключ Gemini. Убедитесь, что переменная окружения GOOGLE_API_KEY установлена.")
    exit()

# Настройка API-ключа
genai.configure(api_key=GOOGLE_API_KEY)

# Выбор модели
model = genai.GenerativeModel('gemini-1.5-flash-8b')

# Инициализация FastAPI приложения
app = FastAPI(title="Gemini Media Analyzer API")

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalysisResponse(BaseModel):
    description: str

class AnalysisRecord(BaseModel):
    id: int
    timestamp: datetime
    user_id: str
    ai_response: str
    file_name: str
    file_path: str

class AnalysisListResponse(BaseModel):
    items: List[AnalysisRecord]

class AnalysisDetailsResponse(BaseModel):
    id: int
    timestamp: datetime
    user_id: str
    ai_response: str
    file_name: str
    file_path: str

class UserRecord(BaseModel):
    id: int
    session_id: str
    created_at: datetime

# Добавляем новые модели данных
class ChatMessage(BaseModel):
    content: str
    role: str = "user"

class Chat(BaseModel):
    id: Optional[int]
    user_id: str
    title: str
    created_at: datetime
    messages: List[ChatMessage]

class ChatResponse(BaseModel):
    chat_id: int
    response: str

# Обновляем класс для создания чата
class CreateChatRequest(BaseModel):
    title: Optional[str] = None
    role: str
    model_type: str  # "gemini" или "grok"

class CreateChatResponse(BaseModel):
    chat_id: int
    title: str
    created_at: datetime

# Обновляем класс для сообщений чата
class ChatMessageRequest(BaseModel):
    content: str
    role: str = "user"

class ChatMessageResponse(BaseModel):
    chat_id: int
    message_id: int
    content: str
    role: str
    timestamp: datetime

class ChatDetailsResponse(BaseModel):
    chat_id: int
    title: str
    created_at: datetime
    messages: List[ChatMessageResponse]

class ChatListResponse(BaseModel):
    chats: List[dict]

# Добавляем новые модели для работы с разными ИИ
class AIModelConfig(BaseModel):
    model_type: str  # "gemini", "grok", другие модели
    api_key: str
    endpoint: str
    system_prompt: Optional[str] = None
    temperature: float = 0
    max_tokens: Optional[int] = None

class AIMessageRequest(BaseModel):
    ai_model_config: AIModelConfig  # Изменили model_config на ai_model_config
    message: str
    chat_id: Optional[int] = None
    images: Optional[List[str]] = None  # base64 encoded images

class AIMessageResponse(BaseModel):
    response: str
    chat_id: Optional[int]
    model_type: str
    timestamp: datetime

def connect_to_db():
    """Устанавливает соединение с базой данных PostgreSQL."""
    conn = None
    try:
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
        )
        logger.info("Успешно подключено к базе данных.")
    except psycopg2.Error as e:
        logger.error(f"Ошибка подключения к базе данных: {e}")
        raise
    return conn

def create_files_directory():
    """Создает директорию /files/ если она не существует."""
    files_dir = "files"
    if not os.path.exists(files_dir):
        os.makedirs(files_dir)
        logger.info(f"Директория '{files_dir}' создана.")

def save_file(file: UploadFile, file_data:bytes) -> str:
    """Сохраняет загруженный файл в директорию /files/ и возвращает путь к файлу."""
    create_files_directory()
    file_extension = os.path.splitext(file.filename)[1]
    file_name = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join("files", file_name)
    with open(file_path, "wb") as buffer:
        buffer.write(file_data)
    logger.info(f"Файл '{file.filename}' сохранен как '{file_path}'.")
    return file_path

def get_user_by_session_id(conn, session_id: str) -> Optional[UserRecord]:
    """Получает пользователя по session_id или создает нового, если не существует."""
    cursor = conn.cursor()
    try:
        query = "SELECT id, session_id, created_at FROM users WHERE session_id = %s;"
        cursor.execute(query, (session_id,))
        record = cursor.fetchone()
        if record:
            return UserRecord(id=record[0], session_id=record[1], created_at=record[2])
        else:
            # Создаем нового пользователя
            query = "INSERT INTO users (session_id, created_at) VALUES (%s, %s) RETURNING id, session_id, created_at;"
            cursor.execute(query, (session_id, datetime.now()))
            new_user_data = cursor.fetchone()
            conn.commit()
            return UserRecord(id=new_user_data[0], session_id=new_user_data[1], created_at=new_user_data[2])
    except psycopg2.Error as e:
        logger.error(f"Ошибка при получении или создании пользователя: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()

def save_analysis_to_db(conn, user_id, ai_response, file_name, file_path):
    """Сохраняет результаты анализа в базе данных."""
    cursor = conn.cursor()
    try:
        query = """
            INSERT INTO analysis_results (timestamp, user_id, ai_response, file_name, file_path)
            VALUES (%s, %s, %s, %s, %s);
        """
        cursor.execute(query, (datetime.now(), user_id, ai_response, file_name, file_path))
        conn.commit()
        logger.info(f"Данные анализа для файла '{file_name}' успешно сохранены в базе данных.")
    except psycopg2.Error as e:
        logger.error(f"Ошибка сохранения данных в базе данных: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()

def get_all_analysis_records(conn) -> List[AnalysisRecord]:
    """Получает все записи анализа из базы данных."""
    cursor = conn.cursor()
    try:
        query = """
            SELECT ar.id, ar.timestamp, u.session_id, ar.ai_response, ar.file_name, ar.file_path
            FROM analysis_results ar
            JOIN users u ON ar.user_id = u.id
            ORDER BY ar.timestamp DESC;
        """
        cursor.execute(query)
        results = cursor.fetchall()
        records = [
            AnalysisRecord(
                id=row[0],
                timestamp=row[1],
                user_id=row[2],
                ai_response=row[3],
                file_name=row[4],
                file_path=row[5]
            )
            for row in results
        ]
        return records
    except psycopg2.Error as e:
        logger.error(f"Ошибка при получении записей анализа из базы данных: {e}")
        raise
    finally:
        cursor.close()

def get_analysis_record_by_id(conn, record_id: int) -> Optional[AnalysisDetailsResponse]:
    """Получает запись анализа по ID из базы данных."""
    cursor = conn.cursor()
    try:
        query = """
            SELECT ar.id, ar.timestamp, u.session_id, ar.ai_response, ar.file_name, ar.file_path
            FROM analysis_results ar
            JOIN users u ON ar.user_id = u.id
            WHERE ar.id = %s;
        """
        cursor.execute(query, (record_id,))
        record = cursor.fetchone()
        if record:
            return AnalysisDetailsResponse(
                id=record[0],
                timestamp=record[1],
                user_id=record[2],
                ai_response=record[3],
                file_name=record[4],
                file_path = record[5]
            )
        else:
            return None
    except psycopg2.Error as e:
        logger.error(f"Ошибка при получении записи анализа из базы данных: {e}")
        raise
    finally:
        cursor.close()

def create_chat_tables(conn):
    """Создает таблицы для чатов и сообщений."""
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                title TEXT,
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
    except Exception as e:
        logger.error(f"Ошибка создания таблиц чата: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()

def get_chat_history(conn, chat_id: int) -> List[dict]:
    """Получает историю сообщений чата."""
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT role, content FROM chat_messages 
            WHERE chat_id = %s 
            ORDER BY timestamp ASC
        """, (chat_id,))
        messages = cursor.fetchall()
        return [{"role": msg[0], "content": msg[1]} for msg in messages]
    finally:
        cursor.close()

def save_chat_message(conn, chat_id: int, role: str, content: str):
    """Сохраняет сообщение в истории чата."""
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO chat_messages (chat_id, role, content)
            VALUES (%s, %s, %s)
        """, (chat_id, role, content))
        conn.commit()
    finally:
        cursor.close()

# Добавляем таблицу для хранения настроек моделей
def create_ai_models_table(conn):
    """Создает таблицу для хранения конфигураций ИИ-моделей."""
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_models_config (
                id SERIAL PRIMARY KEY,
                model_type TEXT NOT NULL,
                api_key TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                system_prompt TEXT,
                temperature FLOAT DEFAULT 0,
                max_tokens INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
    except Exception as e:
        logger.error(f"Ошибка создания таблицы конфигураций ИИ: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()

async def process_image(image_data: str) -> dict:
    """Обрабатывает изображение для отправки в ИИ-модель."""
    if image_data.startswith('data:image'):
        return {
            "type": "image_url",
            "image_url": {
                "url": image_data
            }
        }
    return {
        "type": "image_url",
        "image_url": {
            "url": f"data:image/jpeg;base64,{image_data}"
        }
    }

async def send_to_ai_model(model_config: AIModelConfig, messages: List[dict], images: List[str] = None) -> str:
    """Отправляет запрос к выбранной ИИ-модели."""
    try:
        if model_config.model_type == "gemini":
            # Используем существующую модель Gemini
            response = model.generate_content([msg["content"] for msg in messages])
            return response.text
            
        elif model_config.model_type == "grok":
            # Формируем запрос для Grok API
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {model_config.api_key}'
            }
            
            # Подготовка контента с изображениями
            if images:
                processed_images = [await process_image(img) for img in images]
                content = [
                    {"type": "text", "text": messages[-1]["content"]},
                    *processed_images
                ]
            else:
                content = messages[-1]["content"]

            data = {
                "messages": [
                    *[{"role": msg["role"], "content": msg["content"]} for msg in messages[:-1]],
                    {"role": messages[-1]["role"], "content": content}
                ],
                "model": "grok-2-vision-1212",
                "stream": False,
                "temperature": model_config.temperature
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    model_config.endpoint,
                    headers=headers,
                    json=data
                )
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
        
        else:
            raise ValueError(f"Неподдерживаемый тип модели: {model_config.model_type}")
            
    except Exception as e:
        logger.error(f"Ошибка при отправке запроса к ИИ-модели: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_media(request: Request, file: UploadFile = File(...)):
    logger.info(f"Получен запрос к /analyze с файлом: {file.filename}, тип: {file.content_type}")
    """
    Анализирует загруженное изображение или аудиофайл с помощью Gemini и возвращает текстовое описание.
    Поддерживаемые типы файлов: изображения (jpeg, png, webp), аудио (ogg).
    """
    if not file:
        logger.warning("Файл не был загружен.")
        raise HTTPException(status_code=400, detail="Необходимо загрузить файл.")

    allowed_mime_types = ["image/jpeg", "image/png", "image/webp", "audio/ogg", "audio/wav", "audio/m4a", "audio/x-m4a"]
    if file.content_type not in allowed_mime_types:
        logger.warning(f"Неподдерживаемый тип файла: {file.content_type}")
        raise HTTPException(status_code=400, detail=f"Неподдерживаемый тип файла. Разрешены: {', '.join(allowed_mime_types)}")

    try:
        file_data = await file.read() # Читаем файл сейчас
        logger.info(f"Размер загруженного файла: {len(file_data)} байт")

        file_path = save_file(file, file_data) #  Сохраняем файл

        contents = []
        if file.content_type.startswith("image/"):
            prompt_text = "Ты в роли нейрохирурга! Изучи детально представленные файлы и скажи всё что ты можешь сказать"
            contents = [
                prompt_text,
                {"mime_type": file.content_type, "data": file_data}
            ]
        elif file.content_type.startswith("audio/"):
            prompt_text = "Преобразуй аудио в текст и переведи на английский язык. Отправь и распознанный текст и перевод!"
            contents = [
                prompt_text,
                {"mime_type": file.content_type, "data": file_data}
            ]
        else:
            # Этого блока по идее не должно достигаться, так как проверка mime_type выше
            logger.error(f"Неизвестный тип файла после проверки: {file.content_type}")
            raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера при обработке типа файла.")

        response = model.generate_content(contents)
        logger.info(f"Успешный ответ от Gemini: {response.text[:50]}...") # Логируем начало ответа

        # Сохранение в базу данных
        try:
            conn = connect_to_db()
            session_id = request.cookies.get("session_id", str(uuid.uuid4()))
            user = get_user_by_session_id(conn, session_id)
            save_analysis_to_db(conn, user.id, response.text, file.filename, file_path)
        except Exception as db_error:
            logger.error(f"Ошибка при сохранении в базу данных: {db_error}")
        finally:
            if conn:
                conn.close()

        return {"description": response.text}
    except Exception as e:
        logger.error(f"Произошла ошибка при анализе файла: {e}")
        raise HTTPException(status_code=500, detail=f"Произошла ошибка при анализе файла: {e}")

@app.post("/chat/new", response_model=CreateChatResponse, 
          summary="Создать новый чат",
          description="Создает новый чат для текущего пользователя с заданной ролью и ИИ-моделью")
async def create_new_chat(
    request: Request,
    chat_data: CreateChatRequest
):
    """
    Создает новый чат для пользователя с заданной ролью и ИИ-моделью.
    
    Args:
        chat_data: Данные для создания чата (название, роль, тип модели)
        
    Returns:
        CreateChatResponse: Информация о созданном чате
    """
    try:
        conn = connect_to_db()
        session_id = request.cookies.get("session_id", str(uuid.uuid4()))
        user = get_user_by_session_id(conn, session_id)
        
        title = chat_data.title if chat_data else f"Чат {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO chats (user_id, title)
            VALUES (%s, %s)
            RETURNING id, title, created_at
        """, (user.id, title))
        
        chat_id, title, created_at = cursor.fetchone()
        conn.commit()
        
        # Сохраняем начальный контекст чата
        cursor.execute("""
            INSERT INTO chat_messages (chat_id, role, content)
            VALUES (%s, %s, %s)
        """, (chat_id, "system", chat_data.role))
        conn.commit()
        
        return CreateChatResponse(
            chat_id=chat_id,
            title=title,
            created_at=created_at
        )
    finally:
        if conn:
            conn.close()

@app.post("/chat/{chat_id}/message", response_model=ChatMessageResponse,
          summary="Отправить сообщение в чат",
          description="Отправляет сообщение в чат и получает ответ от модели ИИ")
async def send_chat_message(
    chat_id: int,
    message: ChatMessageRequest
):
    """
    Отправляет сообщение в чат и получает ответ от модели.
    
    Args:
        chat_id: ID чата
        message: Сообщение для отправки
        
    Returns:
        ChatMessageResponse: Ответ модели
    """
    try:
        conn = connect_to_db()
        
        # Получаем историю чата
        chat_history = get_chat_history(conn, chat_id)
        
        # Добавляем новое сообщение пользователя
        save_chat_message(conn, chat_id, "user", message.content)
        
        # Формируем контекст для модели
        context = [
            {"role": "system", "content": "Ты полезный ассистент, который отвечает на русском языке."}
        ] + chat_history + [{"role": "user", "content": message.content}]
        
        # Получаем ответ от модели
        response = model.generate_content([msg["content"] for msg in context])
        
        # Сохраняем ответ модели
        save_chat_message(conn, chat_id, "assistant", response.text)
        
        return ChatMessageResponse(
            chat_id=chat_id,
            message_id=uuid.uuid4().int,
            content=response.text,
            role="assistant",
            timestamp=datetime.now()
        )
    finally:
        if conn:
            conn.close()

@app.get("/chats", response_model=ChatListResponse,
         summary="Получить список чатов",
         description="Возвращает список всех чатов пользователя")
async def get_user_chats(request: Request):
    """
    Получает список чатов пользователя.
    
    Returns:
        ChatListResponse: Список чатов пользователя
    """
    try:
        conn = connect_to_db()
        session_id = request.cookies.get("session_id", str(uuid.uuid4()))
        user = get_user_by_session_id(conn, session_id)
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, created_at 
            FROM chats 
            ORDER BY created_at DESC
        """, (user.id,))
        
        chats = cursor.fetchall()
        return {
            "chats": [
                {
                    "id": chat[0],
                    "title": chat[1],
                    "created_at": chat[2]
                }
                for chat in chats
            ]
        }
    finally:
        if conn:
            conn.close()

@app.get("/chat/{chat_id}", response_model=ChatDetailsResponse)
async def get_chat_details(chat_id: int):
    """Получает детали чата и историю сообщений."""
    try:
        conn = connect_to_db()
        cursor = conn.cursor()
        
        # Получаем информацию о чате
        cursor.execute("""
            SELECT title, created_at 
            FROM chats 
            WHERE id = %s
        """, (chat_id,))
        
        chat_info = cursor.fetchone()
        if not chat_info:
            raise HTTPException(status_code=404, detail="Чат не найден")
            
        # Получаем сообщения чата
        cursor.execute("""
            SELECT id, role, content, timestamp
            FROM chat_messages 
            WHERE chat_id = %s 
            ORDER BY timestamp ASC
        """, (chat_id,))
        
        messages = [
            ChatMessageResponse(
                chat_id=chat_id,
                message_id=msg[0],
                role=msg[1],
                content=msg[2],
                timestamp=msg[3]
            )
            for msg in cursor.fetchall()
        ]
        
        return ChatDetailsResponse(
            chat_id=chat_id,
            title=chat_info[0],
            created_at=chat_info[1],
            messages=messages
        )
    except Exception as e:
        logger.error(f"Ошибка при получении деталей чата: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

@app.get("/analysis", response_model=AnalysisListResponse)
def get_analysis_list():
    """Возвращает список всех записей анализа."""
    try:
        conn = connect_to_db()
        records = get_all_analysis_records(conn)
        return AnalysisListResponse(items=records)
    except Exception as e:
        logger.error(f"Ошибка при получении списка записей анализа: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при получении списка записей анализа")
    finally:
        if conn:
            conn.close()

@app.get("/analysis/{record_id}", response_model=AnalysisDetailsResponse)
def get_analysis_details(record_id: int):
    """Возвращает детальную информацию о конкретной записи анализа по ID."""
    try:
        conn = connect_to_db()
        record = get_analysis_record_by_id(conn, record_id)
        if record:
            return record
        else:
            raise HTTPException(status_code=404, detail="Запись не найдена")
    except Exception as e:
        logger.error(f"Ошибка при получении детальной информации о записи анализа: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при получении детальной информации о записи анализа")
    finally:
        if conn:
            conn.close()

@app.post("/ai/chat", response_model=AIMessageResponse)
async def chat_with_ai(request: AIMessageRequest):
    """
    Универсальный endpoint для общения с разными ИИ-моделями.
    
    Args:
        request: Запрос с конфигурацией модели и сообщением
        
    Returns:
        AIMessageResponse: Ответ от ИИ-модели
    """
    try:
        conn = connect_to_db()
        
        # Получаем историю чата, если указан chat_id
        messages = []
        if request.chat_id:
            messages = get_chat_history(conn, request.chat_id)
        
        # Добавляем системный промпт, если он есть
        if request.ai_model_config.system_prompt:  # Изменили здесь
            messages.insert(0, {
                "role": "system",
                "content": request.ai_model_config.system_prompt
            })
        
        # Добавляем текущее сообщение
        messages.append({
            "role": "user",
            "content": request.message
        })
        
        # Получаем ответ от модели
        response_text = await send_to_ai_model(
            request.ai_model_config,  # Изменили здесь
            messages,
            request.images
        )
        
        # Сохраняем сообщение и ответ в БД, если указан chat_id
        if request.chat_id:
            save_chat_message(conn, request.chat_id, "user", request.message)
            save_chat_message(conn, request.chat_id, "assistant", response_text)
        
        return AIMessageResponse(
            response=response_text,
            chat_id=request.chat_id,
            model_type=request.ai_model_config.model_type,  # Изменили здесь
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Ошибка в чате с ИИ: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

@app.on_event("startup")
async def startup_event():
    """Создаем необходимые таблицы при запуске приложения."""
    conn = connect_to_db()
    try:
        cursor = conn.cursor()
        
        # Создаем таблицу пользователей, если её нет
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                session_id TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Создаем таблицы для чатов
        cursor.execute("""
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
        logger.info("База данных успешно инициализирована")
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=81)