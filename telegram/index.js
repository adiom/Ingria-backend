// INGRIA TELEGRAM NODEJS

require('dotenv').config();
const TelegramBot = require('node-telegram-bot-api');
const axios = require('axios');
const FormData = require('form-data');
const fs = require('node:fs/promises');
const path = require('node:path');

// Получение токена Telegram бота и URL бэкенда из переменных окружения
const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const BACKEND_API_URL = process.env.BACKEND_API_URL || 'http://localhost:81/analyze';

if (!TELEGRAM_BOT_TOKEN) {
    console.error('Ошибка: Не найден токен Telegram бота. Убедитесь, что переменная окружения TELEGRAM_BOT_TOKEN установлена.');
    process.exit(1);
}

// Создаем экземпляр бота
const bot = new TelegramBot(TELEGRAM_BOT_TOKEN, { polling: true });

// Обработка команды /start
bot.onText(/\/start/, (msg) => {
    bot.sendMessage(msg.chat.id, 'Привет! Отправь мне фотографию или голосовое сообщение, и я их проанализирую.');
});

// Обработка команды /help
bot.onText(/\/help/, (msg) => {
    bot.sendMessage(msg.chat.id, 'Просто отправь мне фотографию или голосовое сообщение, и я скажу, что на них вижу/слышу.');
});

// Функция для обрезки длинного текста
function truncateText(text, maxLength) {
    if (text.length > maxLength) {
        return text.substring(0, maxLength - 3) + '...';
    }
    return text;
}

// Обработка полученных сообщений
bot.on('message', async (msg) => {
    console.log('Получено сообщение:', msg); // Добавлено логирование


    const chatId = msg.chat.id;
    const MAX_CAPTION_LENGTH = 1000; // Пример ограничения длины подписи

    if (msg.photo) {
        try {
            const fileId = msg.photo[msg.photo.length - 1].file_id;
            const fileInfo = await bot.getFile(fileId);
            const fileUrl = `https://api.telegram.org/file/bot${TELEGRAM_BOT_TOKEN}/${fileInfo.file_path}`;

            const imageResponse = await axios({
                method: 'get',
                url: fileUrl,
                responseType: 'arraybuffer',
            });

            const formData = new FormData();
            const imageName = `telegram_image_${msg.message_id}.jpg`;
            formData.append('file', Buffer.from(imageResponse.data), {
                filename: imageName,
                contentType: 'image/jpeg',
            });

            const backendResponse = await axios.post(BACKEND_API_URL, formData, {
                headers: formData.getHeaders(),
            });

            const truncatedDescription = truncateText(backendResponse.data.description, MAX_CAPTION_LENGTH - ("\n\n@Ingria_AI_bot Ingria AI".length));

            const tempFilePath = path.join(__dirname, imageName);
            await fs.writeFile(tempFilePath, Buffer.from(imageResponse.data));

            await bot.sendPhoto(chatId, tempFilePath, {
                caption: `${truncatedDescription} \n\n@Ingria_AI_bot Ingria AI`,
            });

            await fs.unlink(tempFilePath);

        } catch (error) {
            console.error('Ошибка при обработке изображения:', error);
            bot.sendMessage(chatId, 'Произошла ошибка при обработке изображения. Попробуйте позже.');
        }
    } else if (msg.voice) {
        try {
            const fileId = msg.voice.file_id;
            const fileInfo = await bot.getFile(fileId);
            const fileUrl = `https://api.telegram.org/file/bot${TELEGRAM_BOT_TOKEN}/${fileInfo.file_path}`;

            const audioResponse = await axios({
                method: 'get',
                url: fileUrl,
                responseType: 'arraybuffer',
            });

            const formData = new FormData();
            const audioName = `telegram_audio_${msg.message_id}.ogg`;
            formData.append('file', Buffer.from(audioResponse.data), {
                filename: audioName,
                contentType: 'audio/ogg',
            });

            const backendResponse = await axios.post(BACKEND_API_URL, formData, {
                headers: formData.getHeaders(),
            });

            const truncatedDescription = truncateText(backendResponse.data.description, MAX_CAPTION_LENGTH - ("\n\n🎈 @Ingria_AI_bot Ingria AI".length));

            const tempFilePath = path.join(__dirname, audioName);
            await fs.writeFile(tempFilePath, Buffer.from(audioResponse.data));

            await bot.sendVoice(chatId, tempFilePath, {
                caption: `${truncatedDescription} \n\n🎈 @Ingria_AI_bot Ingria AI`,
            });

            await fs.unlink(tempFilePath);

        } catch (error) {
            console.error('Ошибка при обработке аудио:', error);
            bot.sendMessage(chatId, 'Произошла ошибка при обработке аудио. Попробуйте позже.');
        }
    }  else if (msg.text) {
        console.log(`Получено текстовое сообщение от ${msg.from.username || msg.from.first_name}: ${msg.text}`);
        // Здесь можно добавить обработку других текстовых сообщений, если нужно
    }
});

console.log('Бот запущен и ожидает сообщения...');