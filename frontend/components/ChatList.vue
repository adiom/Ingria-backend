<!--
  Component: ChatList
  Path: /frontend/components/ChatList.vue
  Description: Компонент для отображения списка чатов
-->
<template>
  <div class="container mx-auto p-4">
    <div class="flex justify-between mb-4">
      <h1 class="text-2xl">Чаты</h1>
      <NuxtLink to="/chats/new" class="btn btn-primary">
        Новый чат
      </NuxtLink>
    </div>
    
    <div class="grid gap-4">
      <div v-for="chat in chats" :key="chat.id" 
           class="p-4 border rounded hover:bg-gray-50">
        <NuxtLink :to="`/chats/${chat.id}`">
          <h3>{{ chat.title }}</h3>
          <p class="text-sm text-gray-500">
            {{ chat.last_message || 'Нет сообщений' }}
          </p>
        </NuxtLink>
      </div>
    </div>
  </div>
</template>

<script setup>
const chatStore = useChatStore()

onMounted(() => {
  chatStore.loadChats()
})

const chats = computed(() => chatStore.chats)
</script>