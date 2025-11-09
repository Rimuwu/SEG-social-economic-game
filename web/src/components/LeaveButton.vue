<script setup>
import { inject } from 'vue'

const emit = defineEmits(['leave'])
const wsManager = inject('wsManager', null)

const handleLeave = () => {
    // Leave session and clear stored session
    if (wsManager) {
        wsManager.leaveSession()
    }

    // Emit event to parent to navigate to Introduction
    emit('leave')
}
</script>

<template>
    <button class="leave-button" @click="handleLeave">
        <img src="/leave.svg"></img>
        выйти
    </button>
</template>

<style scoped>
img {
    padding-right: 8px;
}

.leave-button {
    display: flex;
    align-items: center;
    
    
    position: fixed;
    bottom: 20px;
    right: 20px;

    background-color: #333;
    color: white;

    border: none;
    border-radius: 8px;

    padding: 12px 16px;
    font-size: 1.6rem;
    font-weight: 600;
    font-family: "Inter", sans-serif;

    cursor: pointer;

    z-index: 500;
    transition: all 0.2s ease;
}

.leave-button:hover {
    background-color: #b71c1c;
}
</style>
