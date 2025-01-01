import { defineStore } from 'pinia'

interface Chat {
  id: number
  title: string
  last_message?: string
  created_at: string
}

interface Message {
  id: number
  chat_id: number
  content: string
  role: 'user' | 'assistant'
  created_at: string
}

export const useChatStore = defineStore('chat', {
  state: () => ({
    chats: [] as Chat[],
    currentChat: null as Chat | null,
    messages: [] as Message[],
    loading: false,
    error: null as string | null
  }),

  actions: {
    // Загрузка списка чатов
    async loadChats() {
      this.loading = true
      try {
        const response = await fetch('http://localhost:81/chats')
        const data = await response.json()
        this.chats = data.chats
      } catch (err) {
        this.error = 'Ошибка загрузки чатов'
        console.error(err)
      } finally {
        this.loading = false
      }
    },

    // Создание нового чата
    async createChat(title: string, role: string, model_type: string) {
      try {
        const response = await fetch('http://localhost:81/chat/new', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ title, role, model_type })
        })
        const newChat = await response.json()
        this.chats.push(newChat)
        return newChat
      } catch (err) {
        this.error = 'Ошибка создания чата'
        console.error(err)
      }
    },

    // Загрузка сообщений чата
    async loadMessages(chatId: number) {
      this.loading = true
      try {
        const response = await fetch(`http://localhost:81/chat/${chatId}`)
        const data = await response.json()
        this.messages = data.messages
      } catch (err) {
        this.error = 'Ошибка загрузки сообщений'
        console.error(err)
      } finally {
        this.loading = false
      }
    },

    // Отправка сообщения
    async sendMessage(chatId: number, content: string) {
      try {
        const response = await fetch(`http://localhost:81/chat/${chatId}/message`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ content })
        })
        const newMessage = await response.json()
        this.messages.push(newMessage)
        return newMessage
      } catch (err) {
        this.error = 'Ошибка отправки сообщения'
        console.error(err)
      }
    },

    // Удаление чата
    async deleteChat(chatId: number) {
      try {
        await fetch(`http://localhost:81/chat/${chatId}`, {
          method: 'DELETE'
        })
        this.chats = this.chats.filter(chat => chat.id !== chatId)
      } catch (err) {
        this.error = 'Ошибка удаления чата'
        console.error(err)
      }
    }
  }
})