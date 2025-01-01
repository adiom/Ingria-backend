<template>
  <div class="container mx-auto p-4">
    <h1 class="text-2xl font-bold mb-4">Сохраненные анализы</h1>
    <div v-if="isLoading" class="text-center">Загрузка...</div>
    <div v-else-if="errorMessage" class="text-red-500">{{ errorMessage }}</div>
    <div v-else class="overflow-x-auto">
      <table class="min-w-full border border-gray-200 shadow-md rounded">
        <thead class="bg-gray-50">
          <tr>
            <th class="py-2 px-4 border-b">ID</th>
            <th class="py-2 px-4 border-b">Время</th>
            <th class="py-2 px-4 border-b">Имя файла</th>
            <th class="py-2 px-4 border-b">Действия</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="analysis in analyses" :key="analysis.id" class="hover:bg-gray-100">
            <td class="py-2 px-4 border-b">{{ analysis.id }}</td>
            <td class="py-2 px-4 border-b">{{ formatDate(analysis.timestamp) }}</td>
            <td class="py-2 px-4 border-b">{{ analysis.file_name }}</td>
            <td class="py-2 px-4 border-b">
              <NuxtLink :to="`/analysis/${analysis.id}`" class="text-blue-500 hover:underline">
                Подробнее
              </NuxtLink>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import axios from 'axios';

const analyses = ref([]);
const isLoading = ref(true);
const errorMessage = ref(null);

onMounted(async () => {
  try {
    const response = await axios.get('http://localhost:81/analysis');
    analyses.value = response.data.items; // Изменено для доступа к массиву items
  } catch (error) {
    console.error('Ошибка получения списка анализов:', error);
    errorMessage.value = 'Не удалось загрузить список анализов.';
  } finally {
    isLoading.value = false;
  }
});

function formatDate(dateString) {
  const date = new Date(dateString);
  if (isNaN(date)) {
    return 'Invalid Date';
  }

  return date.toLocaleString();
}

</script>