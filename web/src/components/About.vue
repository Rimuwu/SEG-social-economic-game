<script setup>
import { onMounted } from 'vue'

const emit = defineEmits(['navigateTo'])

// Get AUTHORS from environment, with fallback
const AUTHORS = import.meta.env.VITE_AUTHORS || 'SEG Development Team';

// Handle navigation back
const handleBack = () => {
  emit('navigateTo', 'Introduction')
}

onMounted(() => {
  const authorsElement = document.getElementById("authors")
  if (authorsElement) {
    authorsElement.innerHTML = AUTHORS.split("/").join("<br/>");
  }
})
</script>

<template>
  <div id="page">
    <div class="left">
      <div class="qr-section">
        <h2>@MIREA_ESPORTS</h2>
        <div class="qr-placeholder">
          <img src="/qr.svg" alt="QR Code" class="qr-image">
        </div>
        <p class="qr-text">
          ХОТИТЕ СЫГРАТЬ ЕЩЁ?<br>
          СЛЕДИТЕ ЗА НОВОСТЯМИ!
        </p>
      </div>
    </div>
    
    <div class="right">
      <div class="info-section">
        <div class="thank-you">
          <h1>Спасибо за игру!</h1>
          <p>
            Игра создана и<br>
            разработана по<br>
            авторской идее и без<br>
            использования<br>
            потусторонних сил.
          </p>
        </div>
        
        <div class="creators">
          <h2>Создатели</h2>
          <div id="authors" class="authors-list"></div>
        </div>
        
        <button class="back-button" @click="handleBack">
          Выйти →
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
#page {
  display: flex;
  height: 100vh;
  background-color: #3D8C00;
  font-family: "Inter", sans-serif;
  padding: 0;
  margin: 0;
}

.left, .right {
  width: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.left {
  background-color: #0C9273;
  width: 60%;
}

.right {
  background-color: #1976D2;
  width: 40%;
}

.thank-you {
  width: 100%;
}

.creators {
  width: 100%;
}

.qr-section {
  text-align: center;
  color: white;
}

.qr-section h2 {
  font-size: 4rem;
  margin-bottom: 40px;
  font-weight: bold;
}

.qr-placeholder {
  margin: 40px 0;
  display: flex;
  justify-content: center;
}

.qr-image {
  width: 450px;
  height: 450px;
  filter: brightness(0) invert(1);
}

.qr-text {
  font-size: 2.5rem;
  font-weight: bold;
  line-height: 1.4;
  margin-top: 40px;
}

.info-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 40px;
  color: white;
  width: 100%;
  max-width: 500px;
}

.thank-you h1 {
  font-size: 4rem;
  margin-bottom: 20px;
  background-color: #0C9273;
  padding: 40px 60px;
  border-radius: 12px;
  text-align: center;
  width: 100%;
  box-sizing: border-box;
}

.thank-you p {
  font-size: 2.2rem;
  line-height: 1.5;
  text-align: center;
  background-color: #0C9273;
  padding: 40px 60px;
  border-radius: 12px;
  width: 100%;
  box-sizing: border-box;
  margin: 0;
}

.creators h2 {
  font-size: 3rem;
  margin-bottom: 20px;
  text-align: center;
  background-color: #0C9273;
  padding: 30px 50px;
  border-radius: 12px;
  width: 100%;
  box-sizing: border-box;
}

.authors-list {
  font-size: 2.5rem;
  line-height: 1.6;
  text-align: center;
  background-color: #0C9273;
  padding: 40px 60px;
  border-radius: 12px;
  width: 100%;
  box-sizing: border-box;
}

.back-button {
  background-color: #0C9273;
  color: white;
  border: none;
  border-radius: 12px;
  padding: 20px 50px;
  font-size: 2.5rem;
  font-weight: 600;
  font-family: "Inter", sans-serif;
  cursor: pointer;
  transition: background-color 0.3s ease;
  width: 100%;
  box-sizing: border-box;
}

.back-button:hover {
  background-color: #0A7A62;
}
</style>