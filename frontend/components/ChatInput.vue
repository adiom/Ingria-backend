<template>
    <div class="chat-input">
        <input 
            v-model="message" 
            @keyup.enter="sendMessage" 
            type="text" 
            placeholder="Type your message here..." 
        />
        <button @click="sendMessage">Send</button>
    </div>
</template>

<script>
export default {
    data() {
        return {
            message: ''
        };
    },
    methods: {
        sendMessage() {
            if (this.message.trim() !== '') {
                this.$emit('send-message', this.message);
                this.message = '';
            }
        }
    }
};
</script>

<style scoped>
.chat-input {
    display: flex;
    align-items: center;
}

.chat-input input {
    flex: 1;
    padding: 10px;
    margin-right: 10px;
}

.chat-input button {
    padding: 10px 20px;
}
</style>