<template>
  <div class="container mx-auto p-4">
    <header class="text-center my-5">
      <h1 class="text-3xl font-bold text-gray-800">Canfly Ingria</h1>
      <p class="lead text-gray-600 mt-2">Загрузите изображение для анализа с помощью Ingria.</p>
      <NuxtLink to="/analysis" class="text-blue-500 hover:underline hover:text-blue-700 mt-2 block">
        Просмотреть сохраненные анализы
      </NuxtLink>
    </header>

    <section class="upload-section mb-5">
       <div class="flex justify-center">
        <ImageUploader @image-selected="onImageSelected" />
      </div>
    </section>

    <section v-if="analysisResult" class="analysis-section mt-8">
      <h2 class="text-xl font-semibold mb-2">Результат анализа:</h2>
      <div class="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded relative" role="alert">
        {{ analysisResult }}
      </div>
    </section>

    <section v-if="errorMessage" class="error-section mt-8">
       <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert" v-html="errorMessage">
       </div>
    </section>

    <section v-if="isLoading" class="loading-section text-center mt-8">
      <div class="animate-spin inline-block w-8 h-8 border-t-2 border-blue-500 border-solid rounded-full" role="status">
          <span class="visually-hidden">Загрузка...</span>
        </div>
      <p class="mt-2">Идет анализ изображения...</p>
    </section>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import axios from 'axios';
import 'bootstrap-icons/font/bootstrap-icons.css';

const selectedImageFile = ref(null);
const analysisResult = ref(null);
const errorMessage = ref(null);
const isLoading = ref(false);

const onImageSelected = (file) => {
  selectedImageFile.value = file;
  analysisResult.value = null;
  errorMessage.value = null;
  if (file) {
    analyzeImage();
  }
};

const analyzeImage = async () => {
  if (!selectedImageFile.value) return;

  isLoading.value = true;
  errorMessage.value = null;

  const formData = new FormData();
  formData.append('file', selectedImageFile.value);

  try {
    const response = await axios.post('http://localhost:81/analyze', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    analysisResult.value = response.data.description;
  } catch (error) {
    console.error('Ошибка анализа:', error);
    if (error.response) {
      errorMessage.value = `Ошибка анализа: ${error.response.status} - ${error.response.statusText}`;
      if (error.response.data) {
        errorMessage.value += `<br>Детали: ${JSON.stringify(error.response.data)}`;
      }
    } else if (error.request) {
      errorMessage.value = 'Ошибка анализа: Не удалось получить ответ от сервера.';
    } else {
      errorMessage.value = 'Ошибка анализа: ' + error.message;
    }
  } finally {
    isLoading.value = false;
  }
};
</script>

<style scoped>
/* Удалите старые стили, так как мы теперь используем Tailwind CSS */
</style>