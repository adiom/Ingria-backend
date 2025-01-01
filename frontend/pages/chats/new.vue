<template>
  <div class="container mx-auto p-4">
    <h1 class="text-2xl mb-4">Новый чат</h1>
    
    <form @submit.prevent="createChat" class="max-w-md">
      <input 
        v-model="title"
        type="text"
        placeholder="Название чата"
        class="w-full p-2 border rounded mb-4"
      />
      
      <button type="submit" class="btn btn-primary">
        Создать
      </button>
    </form>
  </div>
</template>

<script setup>
const router = useRouter()
const chatStore = useChatStore()
const title = ref('')

async function createChat() {
  await chatStore.createChat(title.value, "grok", "kolobok")
  router.push('/chats')
}
</script>