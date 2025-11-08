<script setup>
import { inject } from 'vue'

const emit = defineEmits(['leave', 'showAbout'])
const wsManager = inject('wsManager', null)

const handleLeave = () => {
    // Leave session and clear stored session
    if (wsManager) {
        wsManager.leaveSession()
    }

    // Emit event to parent to navigate to Introduction
    emit('leave')
}

const handleAbout = () => {
    // Emit event to parent to show About page
    emit('showAbout')
}
</script>

<template>
    <div class="navigation-buttons">
        <button class="nav-button leave-button" @click="handleAbout">
            <img src="/about.svg" alt="О нас">
            О нас
        </button>
        
        <button class="nav-button leave-button" @click="handleLeave">
            <img src="/leave.svg" alt="Выйти">
            Выйти
        </button>
    </div>
</template>

<style scoped>
.navigation-buttons {
    position: fixed;
    bottom: 20px;
    right: 20px;
    display: flex;
    flex-direction: row;
    gap: 15px;
}

.nav-button {
    display: flex;
    align-items: center;
    
    background-color: rgba(51, 51, 51, 0.8);
    color: white;

    border: none;
    border-radius: 8px;

    padding: 12px 16px;
    font-size: 1.6rem;
    font-weight: 600;
    font-family: "Inter", sans-serif;

    cursor: pointer;
    transition: background-color 0.3s ease;
    backdrop-filter: blur(4px);
}

.nav-button:hover {
    background-color: rgba(85, 85, 85, 0.9);
}

.nav-button img {
    padding-right: 8px;
    width: 16px;
    height: 16px;
}

.about-button {
    background-color: #333;
}

.about-button:hover {
    background-color: rgba(46, 106, 0, 0.9);
}

.leave-button {
    background-color: rgba(51, 51, 51, 0.8);
}

.leave-button:hover {
    background-color: rgba(85, 85, 85, 0.9);
}
</style>