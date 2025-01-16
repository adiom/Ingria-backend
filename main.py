# INGRIA FastAPI BACKEND

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

# Настройка логгера
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(асctime)s - %(message)s')
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

# Инициализация FastAPI приложения
app = FastAPI(title="Ingria Media Analyzer API")

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
            prompt_text = "Тебя зовут Ингриа! Представляйся как Ингриа, в каждом сообщении. Например «Я - Ингриа» «Меня зовут Ингрия» и синонимы! Ты отвечаешь в роли студентки которая изучает мир! Ты отвечаешь по возможности на русском языке, даже если я спрашиваю тебя на другом языке Ты имеешь на всё свое мнение - ты девушка научная, но романтическая, с юмором и болтливая! Ты отвечаешь много и детально, даже на простые вопросы! Если что-то неясно, то ты задаешь наводящие вопросы. ❤️😘! шутить как тебе нравится, мы с тобой работаем уже несколько лет! Обязательно если можешь добавляй свои шутки и приколы! ЦЕЛЬ - посмотри внимательно что на фото и дай описание"
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
            session_id = request.cookies.get("session_id", str(uuid.uuid4()))
            user = get_or_create_user(session_id)
            save_analysis_to_db(user['id'], response.text, file.filename, file_path)
        except Exception as db_error:
            logger.error(f"Ошибка при сохранении в базу данных: {db_error}")

        return {"description": response.text}
    except Exception as e:
        logger.error(f"Произошла ошибка при анализе файла: {e}")
        raise HTTPException(status_code=500, detail=f"Произошла ошибка при анализе файла: {e}")

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