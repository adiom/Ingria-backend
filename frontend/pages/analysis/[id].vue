<template>
  <div class="container mx-auto p-4">
    <NuxtLink to="/analysis" class="text-blue-500 hover:underline mb-4 block">
      <i class="bi bi-arrow-left"></i> Вернуться к списку
    </NuxtLink>
    <h1 class="text-2xl font-bold mb-4">Детали анализа</h1>
    <div v-if="isLoading" class="text-center">Загрузка...</div>
    <div v-else-if="errorMessage" class="text-red-500">{{ errorMessage }}</div>
    <div v-else class="bg-white shadow-md rounded p-4">
      <p><strong>ID:</strong> {{ analysis.id }}</p>
      <p><strong>Время:</strong> {{ new Date(analysis.timestamp).toLocaleString() }}</p>
      <p><strong>User ID:</strong> {{ analysis.user_id }}</p>
      <p><strong>Имя файла:</strong> {{ analysis.file_name }}</p>
      <p><strong>Описание от Gemini:</strong></p>
      <div class="border rounded p-2 whitespace-pre-line">{{ analysis.ai_response }}</div>
      <p class="mt-4"><strong>Содержимое файла:</strong></p>
      <div class="border rounded p-2 overflow-auto">
        <pre>{{ analysis.file_content }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import axios from 'axios';
import { useRoute } from 'nuxt/app';

const route = useRoute();
const analysis = ref(null);
const isLoading = ref(true);
const errorMessage = ref(null);

onMounted(async () => {
  const analysisId = route.params.id;
  try {
    const response = await axios.get(`http://localhost:81/analysis/${analysisId}`);
    analysis.value = response.data;
  } catch (error) {
    console.error('Ошибка получения деталей анализа:', error);
    errorMessage.value = 'Не удалось загрузить детали анализа.';
  } finally {
    isLoading.value = false;
  }
});
</script>