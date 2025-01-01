<template>
  <div class="container mx-auto p-4">
    <div v-if="error" class="text-red-500 mb-4">{{ error }}</div>
    <div v-if="loading" class="text-center">Загрузка...</div>
    
    <div class="flex flex-col h-[calc(100vh-2rem)]">
      <div class="flex-grow overflow-y-auto">
        <div v-if="messages.length === 0" class="text-center text-gray-500 mt-4">
          Нет сообщений
        </div>
        <ChatMessage
          v-for="msg in messages"
          :key="msg.id"
          :message="msg.content"
          :isUser="msg.role === 'user'"
        />
      </div>
      
      <div class="border-t p-4">
        <form @submit.prevent="sendMessage" class="flex gap-2">
          <input 
            v-model="newMessage"
            type="text"
            class="flex-grow p-2 border rounded"
            placeholder="Введите сообщение..."
          />
          <button 
            type="submit" 
            class="bg-blue-500 text-white px-4 py-2 rounded"
            :disabled="loading"
          >
            {{ loading ? 'Отправка...' : 'Отправить' }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useChatStore } from '@/stores/chat'

const route = useRoute()
const chatStore = useChatStore()
const messages = ref([])
const newMessage = ref('')
const loading = ref(false)
const error = ref(null)

const chatId = computed(() => Number(route.params.id))

async function loadMessages() {
  loading.value = true
  try {
    await chatStore.loadMessages(chatId.value)
    messages.value = chatStore.messages
  } catch (err) {
    error.value = 'Ошибка загрузки сообщений'
    console.error(err)
  } finally {
    loading.value = false
  }
}

async function sendMessage() {
  if (!newMessage.value.trim()) return
  
  loading.value = true
  try {
    await chatStore.sendMessage(chatId.value, newMessage.value)
    newMessage.value = ''
  } catch (err) {
    error.value = 'Ошибка отправки сообщения'
    console.error(err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadMessages()
})

watch(() => chatStore.messages, (newMessages) => {
  messages.value = newMessages
}, { deep: true })
</script>