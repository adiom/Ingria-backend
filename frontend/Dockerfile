FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install  # Явно устанавливаем зависимости

COPY . .

EXPOSE 3000

CMD ["npx", "nuxt", "dev", "--host", "0.0.0.0"]