# Используем более легкий базовый образ
FROM node:21-alpine

# Устанавливаем зависимости для работы с изображениями
RUN apk add --no-cache python3 make g++

# Создаем директорию для логов
RUN mkdir -p /usr/src/app/chat_logs && chmod 777 /usr/src/app/chat_logs

# Устанавливаем рабочую директорию
WORKDIR /usr/src/app

# Копируем файлы package.json
COPY package*.json ./

# Устанавливаем зависимости (заменяем ci на install)
RUN npm install --omit=dev

# Копируем исходный код приложения
COPY . .

# Создаем неroot пользователя
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser

# Указываем порты, если необходимо
EXPOSE 3000

# Запускаем приложение
CMD ["node", "grok.js"]
