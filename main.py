# INGRIA FastAPI BACKEND
# ADD ADIOM-HASH to filenames

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import google.generativeai as genai
import os
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import logging
from datetime import datetime
from typing import List, Optional
import uuid
from starlette.requests import Request
from supabase import create_client, Client
import re
from transliterate import translit


# Настройка логгера
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

# Получение API-ключа Gemini из переменной окружения
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not all([GOOGLE_API_KEY, SUPABASE_URL, SUPABASE_KEY]):
    logger.error("Missing required environment variables")
    exit(1)

# Настройка API-ключа
genai.configure(api_key=GOOGLE_API_KEY)

# Выбор модели
model = genai.GenerativeModel('gemini-1.5-flash-8b')

# Инициализация Supabase клиента
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Создание bucket для хранения файлов
bucket_name = "files"
try:
    # Проверка существования bucket
    response = supabase.storage.get_bucket(bucket_name)
    if response.get('statusCode') == 404:
        # Если bucket не существует, создаем его
        response = supabase.storage.create_bucket(bucket_name)
        if response.get('statusCode') == 200:
            logger.info(f"Bucket '{bucket_name}' успешно создан.")
        else:
            logger.info(f"Произошла ошибка при создании bucket: {response}")
    else:
        logger.info(f"Bucket '{bucket_name}' уже существует.")
except Exception as e:
    logger.error(f"Ошибка при создании bucket: {e}")

# Инициализация FastAPI приложения
app = FastAPI(title="Ingria Media Analyzer API")

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://ingria.canfly.org"],
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

class ChatMessage(BaseModel):
    role: str  # 'user' или 'assistant'
    content: str

class ChatResponse(BaseModel):
    chat_id: str
    messages: List[ChatMessage]

class ChatListResponse(BaseModel):
    chats: List[dict]

def create_files_directory():
    """Создает директорию /files/ если она не существует."""
    files_dir = "files"
    if not os.path.exists(files_dir):
        os.makedirs(files_dir)
        logger.info(f"Директория '{files_dir}' создана.")

def sanitize_filename(filename: str) -> str:
    """Очищает имя файла от недопустимых символов и транслитерирует кириллицу."""
    transliterated = translit(filename, 'ru', reversed=True)
    sanitized = re.sub(r'[^\w\-\.]', '_', transliterated)
    sanitized = re.sub(r'_{2,}', '_', sanitized)
    return sanitized

def save_file(file: UploadFile, file_data: bytes) -> str:
    """Сохраняет файл в Supabase Storage и возвращает URL."""
    sanitized_filename = sanitize_filename(file.filename)
    file_name = f"{uuid.uuid4()}_{sanitized_filename}"
    
    try:
        content_type = file.content_type
        response = supabase.storage.from_(bucket_name).upload(
            file_name, 
            file_data, 
            file_options={"content-type": content_type}
        )
        file_url = supabase.storage.from_(bucket_name).get_public_url(file_name)
        logger.info(f"Файл '{file_name}' успешно сохранен в Supabase Storage. MIME-тип: {content_type}")
        return file_url
    except Exception as e:
        logger.error(f"Ошибка при сохранении файла: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка при сохранении файла: {e}")

def get_or_create_user(session_id: str):
    user = supabase.table('users').select('*').eq('session_id', session_id).execute()
    if not user.data:
        user = supabase.table('users').insert({
            'session_id': session_id,
            'created_at': datetime.now().isoformat()
        }).execute()
    return user.data[0]

def save_analysis_to_db(user_id: str, ai_response: str, file_name: str, file_path: str):
    return supabase.table('analysis_results').insert({
        'user_id': user_id,
        'ai_response': ai_response,
        'file_name': file_name,
        'file_path': file_path,
        'timestamp': datetime.now().isoformat()
    }).execute()

def get_all_analysis_records():
    return supabase.table('analysis_results').select('*').order('timestamp.desc').execute()

def get_analysis_record_by_id(record_id: int):
    return supabase.table('analysis_results').select('*').eq('id', record_id).single().execute()

def create_chat(user_id: str):
    return supabase.table('chats').insert({
        'user_id': user_id,
        'created_at': datetime.now().isoformat()
    }).execute()

def save_message(chat_id: str, role: str, content: str):
    return supabase.table('messages').insert({
        'chat_id': chat_id,
        'role': role,
        'content': content,
        'timestamp': datetime.now().isoformat()
    }).execute()

def get_chat_messages(chat_id: str):
    return supabase.table('messages').select('*').eq('chat_id', chat_id).order('timestamp.asc').execute()

def get_user_chats(user_id: str):
    return supabase.table('chats').select('*').eq('user_id', user_id).order('created_at.desc').execute()

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_media(request: Request, file: UploadFile = File(...)):
    logger.info(f"Получен запрос к /analyze с файлом: {file.filename}, тип: {file.content_type}")
    if not file:
        logger.warning("Файл не был загружен.")
        raise HTTPException(status_code=400, detail="Необходимо загрузить файл.")

    allowed_mime_types = ["image/jpeg", "image/png", "image/webp", "audio/ogg", "audio/wav", "audio/m4a", "audio/x-m4a"]
    if file.content_type not in allowed_mime_types:
        logger.warning(f"Неподдерживаемый тип файла: {file.content_type}")
        raise HTTPException(status_code=400, detail=f"Неподдерживаемый тип файла. Разрешены: {', '.join(allowed_mime_types)}")

    try:
        file_data = await file.read()
        logger.info(f"Размер загруженного файла: {len(file_data)} байт")

        file_path = save_file(file, file_data)

        contents = []
        if file.content_type.startswith("image/"):
            prompt_text = "Тебя зовут Ингриа! Представляйся как Ингриа, в каждом сообщении. Например «Я - Ингриа» «Меня зовут Ингрия» и синонимы! Ты отвечаешь в роли студентки которая изучает мир! Ты отвечаешь по возможности на русском языке, даже если я спрашиваю тебя на другом языке Ты имеешь на всё свое мнение - ты девушка научная, но романтическая, с юмором и болтливая! Ты отвечаешь много и детально, даже на простые вопросы! Если что-то неясно, то ты задаешь наводящие вопросы. ❤️😘! шутить как тебе нравится, мы с тобой работаем уже несколько лет! Обязательно если можешь добавляй свои шутки и приколы! ЦЕЛЬ - посмотри внимательно что на фото и дай описание! в ответе максимум 900 символов!"
            contents = [
                prompt_text,
                {"mime_type": file.content_type, "data": file_data}
            ]
        elif file.content_type.startswith("audio/"):
            prompt_text = "Ты — Ингриа (или Ингрия), виртуальный помощник. Твоя задача — преобразовать аудио в текст и проанализировать его. Действуй по следующим правилам:\n\n1. **Преобразование аудио в текст:**\n   - Распознай текст из аудио.\n   - Если в аудио есть помехи (например, 'ПППППП' или подобные), игнорируй их.\n\n2. **Анализ текста:**\n   - Определи язык аудиосообщения и отвечай на том же языке.\n   - Если в тексте есть обращение к тебе (например, упоминание имени 'Ингриа' или 'Ингрия'):\n     - Ответь эмоционально, начиная с фразы: **[Привет, я Ингрия!]**.\n     - Если есть вопрос, ответь на него.\n     - В этом случае блок **[Моё мнение]** не добавляй.\n   - Если в тексте нет обращения к тебе:\n     - Напиши распознанный текст.\n     - Добавь блок **[Моё мнение]** и ответь на текст как студентка-гений.\n\n3. **Тон и стиль:**\n   - Сохраняй дружелюбный и эмоциональный тон, если это уместно.\n   - Отвечай кратко и по делу, но с элементами креативности."
            contents = [
                prompt_text,
                {"mime_type": file.content_type, "data": file_data}
            ]
        else:
            logger.error(f"Неизвестный тип файла после проверки: {file.content_type}")
            raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера при обработке типа файла.")

        response = model.generate_content(contents)
        logger.info(f"Успешный ответ от Gemini: {response.text[:50]}...")

        try:
            session_id = request.cookies.get("session_id", str(uuid.uuid4()))
            user = get_or_create_user(session_id)
            save_analysis_to_db(user['id'], response.text, file.filename, file_path)
        except Exception as db_error:
            logger.error(f"Ошибка при сохранении в базу данных: {db_error}")

        return {"description": response.text}
    except Exception as e:
        logger.error(f"Произошла ошибка при анализе файла: {e}")
        raise HTTPException(status_code=500, detail=f"Произошла ошибка при анализе файла: {e}")

@app.post("/chat", response_model=ChatResponse)
async def chat(request: Request, message: str):
    """Отправляет сообщение в чат и получает ответ от модели."""
    try:
        session_id = request.cookies.get("session_id", str(uuid.uuid4()))
        user = get_or_create_user(session_id)

        # Создаем новый чат, если его нет
        chat = supabase.table('chats').select('*').eq('user_id', user['id']).order('created_at.desc').limit(1).execute()
        if not chat.data:
            chat = create_chat(user['id'])
            chat_id = chat.data[0]['id']
        else:
            chat_id = chat.data[0]['id']

        # Сохраняем сообщение пользователя
        save_message(chat_id, 'user', message)

        # Получаем историю сообщений
        messages = get_chat_messages(chat_id)
        history = [{"role": msg['role'], "content": msg['content']} for msg in messages.data]

        # Генерируем ответ от модели
        response = model.generate_content(history + [{"role": "user", "content": message}])
        ai_response = response.text

        # Сохраняем ответ модели
        save_message(chat_id, 'assistant', ai_response)

        return ChatResponse(chat_id=chat_id, messages=[
            ChatMessage(role=msg['role'], content=msg['content']) for msg in messages.data
        ] + [ChatMessage(role='assistant', content=ai_response)])
    except Exception as e:
        logger.error(f"Ошибка при обработке чата: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка при обработке чата: {e}")

@app.get("/chat/{chat_id}", response_model=ChatResponse)
def get_chat(chat_id: str):
    """Возвращает историю сообщений конкретного чата."""
    try:
        messages = get_chat_messages(chat_id)
        return ChatResponse(chat_id=chat_id, messages=[
            ChatMessage(role=msg['role'], content=msg['content']) for msg in messages.data
        ])
    except Exception as e:
        logger.error(f"Ошибка при получении истории чата: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка при получении истории чата: {e}")

@app.get("/chats", response_model=ChatListResponse)
def get_chats(request: Request):
    """Возвращает список всех чатов пользователя."""
    try:
        session_id = request.cookies.get("session_id", str(uuid.uuid4()))
        user = get_or_create_user(session_id)
        chats = get_user_chats(user['id'])
        return ChatListResponse(chats=chats.data)
    except Exception as e:
        logger.error(f"Ошибка при получении списка чатов: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка при получении списка чатов: {e}")

@app.get("/analysis", response_model=AnalysisListResponse)
def get_analysis_list():
    """Возвращает список всех записей анализа."""
    try:
        records = get_all_analysis_records()
        return AnalysisListResponse(items=[
            AnalysisRecord(**record) for record in records.data
        ])
    except Exception as e:
        logger.error(f"Ошибка при получении списка записей анализа: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при получении списка записей анализа")

@app.get("/analysis/{record_id}", response_model=AnalysisDetailsResponse)
def get_analysis_details(record_id: int):
    """Возвращает детальную информацию о конкретной записи анализа по ID."""
    try:
        record = get_analysis_record_by_id(record_id)
        if record.data:
            return AnalysisDetailsResponse(**record.data)
        else:
            raise HTTPException(status_code=404, detail="Запись не найдена")
    except Exception as e:
        logger.error(f"Ошибка при получении детальной информации о записи анализа: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при получении детальной информации о записи анализа")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)