<template>
  <div class="flex gap-3 p-4" :class="messageClass">
    <div class="flex-shrink-0">
      <div class="w-8 h-8 rounded-full" :class="avatarClass">
        {{ isUser ? 'You' : 'AI' }}
      </div>
    </div>
    <div class="flex-grow">
      <p>{{ message }}</p>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  message: {
    type: String,
    required: true
  },
  isUser: {
    type: Boolean,
    default: false
  }
})

const messageClass = computed(() => props.isUser ? 'bg-gray-50' : '')
const avatarClass = computed(() => props.isUser ? 'bg-blue-500 text-white' : 'bg-green-500 text-white')
</script>