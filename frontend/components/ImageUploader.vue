<template>
  <div
    class="drop-area"
    @dragover.prevent="handleDragOver"
    @drop.prevent="handleDrop"
    :class="{ 'is-dragging': isDragging }"
  >
    <div v-if="!selectedImage">
      <i class="bi bi-cloud-arrow-up icon"></i>
      <p>Перетащите изображение сюда или <label for="image-upload">выберите файл</label></p>
      <input type="file" id="image-upload" accept="image/*" @change="onFileChange" class="d-none">
    </div>
    <div v-else class="preview-container">
      <img :src="selectedImage" alt="Предварительный просмотр" class="img-fluid preview">
      <button class="btn btn-danger btn-sm mt-2" @click="clearImage">Удалить</button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const emit = defineEmits(['image-selected']);

const isDragging = ref(false);
const selectedImage = ref(null);

const handleDragOver = () => {
  isDragging.value = true;
};

const handleDrop = (event) => {
  isDragging.value = false;
  const files = event.dataTransfer.files;
  if (files.length > 0) {
    handleFile(files[0]);
  }
};

const onFileChange = (event) => {
  const files = event.target.files;
  if (files.length > 0) {
    handleFile(files[0]);
  }
};

const handleFile = (file) => {
  const reader = new FileReader();
  reader.onload = (e) => {
    selectedImage.value = e.target.result;
    emit('image-selected', file);
  };
  reader.readAsDataURL(file);
};

const clearImage = () => {
  selectedImage.value = null;
  emit('image-selected', null);
};
</script>

<style scoped>
.drop-area {
  border: 2px dashed #ccc;
  border-radius: 10px;
  padding: 40px;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.3s ease;
}

.drop-area.is-dragging {
  border-color: #007bff;
  background-color: #f8f9fa;
}

.drop-area .icon {
  font-size: 3rem;
  color: #6c757d;
  margin-bottom: 10px;
}

.drop-area p {
  color: #6c757d;
}

.preview-container {
  margin-top: 20px;
}

.preview {
  max-height: 200px;
  border-radius: 5px;
}
</style>