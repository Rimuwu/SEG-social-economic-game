<script setup>
import { ref, onMounted, onUnmounted, inject } from 'vue'

const dfsglsdfklhls = "QHNuZWdfZ2FtZWJvdA==";

const pageRef = ref(null)
const sessionId = ref('')
const currentInstructionIndex = ref(0)
const instructionInterval = ref(null)
const isJoining = ref(false)

// Get WebSocket manager from parent
const wsManager = inject('wsManager', null)

// Define emit to send events to parent
const emit = defineEmits(['navigateTo'])

// Game instructions that rotate every 15 seconds
const instructions = [
  {
    image: "/intro-images/Этап выбора клетки и старта.png",
    text: "Разместите свою компанию на одной из клеток карты и добывайте соответсвующие ресурсы."
  },
  {
    image: "/intro-images/Управление компанией.png",
    text: "Управляйте компанией и развивайте бизнес, кооперируясь с другими игроками."
  },
  {
    image: "/intro-images/Инвентарь.png",
    text: "Управляйте своими складами, покупайте и продавайте ресурсы."
  },
  {
    image: "/intro-images/Города.png",
    text: "Следите за ценами товаров в городах, чтобы максимизировать свою прибыль."
  },
  {
    image: "/intro-images/Биржа.png",
    text: "Участвуйте в торгах на бирже, чтобы покупать и продавать ресурсы по выгодным ценам."
  },
  {
    image: "/intro-images/Контракты.png",
    text: "Заключайте контракты с другими игроками, создавайте долгосрочные поставки и договоры. Контракты помогут вам стабилизировать свою экономику."
  },
  {
    image: "/intro-images/Банк.png",
    text: "Используйте банк для получения кредитов и размещения депозитов. Грамотное управление финансами - ключ к успеху!"
  },
  {
    image: "/intro-images/Ход межэтапа.png",
    text: "Между этапами игры следите за статистикой, анализируйте свой прогресс и планируйте стратегию на следующий ход."
  }
]

function nextInstruction() {
  currentInstructionIndex.value = (currentInstructionIndex.value + 1) % instructions.length
}

function startInstructionRotation() {
  instructionInterval.value = setInterval(nextInstruction, 15000) // 15 seconds
}

function stopInstructionRotation() {
  if (instructionInterval.value) {
    clearInterval(instructionInterval.value)
    instructionInterval.value = null
  }
}

function joinSession() {
  if (!wsManager) {
    console.error('WebSocket manager not available');
    return;
  }

  if (!sessionId.value.trim()) {
    console.error('Please enter a session ID');
    return;
  }

  isJoining.value = true;

  console.log('Attempting to join session: ' + sessionId.value);

  // Use the WebSocket manager to join the session
  wsManager.join_session(sessionId.value.trim(), (result) => {
    isJoining.value = false;

    if (result.success) {
      console.log('Successfully joined session: ' + wsManager.session_id);

      // Navigate to the next page (Preparation)
      emit('navigateTo', 'Preparation');
    } else {
      console.error('Failed to join session:', result.error || 'Session not found');
    }
  });
}

let sdfhlhksg = atob(dfsglsdfklhls);

onMounted(() => {
  startInstructionRotation()
})

onUnmounted(() => {
  stopInstructionRotation()
})
</script>

<template>
  <div id="page" ref="pageRef">
    <div class="left">
      <div class="left-container">
        <div class="image-box">
          <img :src="instructions[currentInstructionIndex].image" :alt="'Инструкция ' + (currentInstructionIndex + 1)" />
        </div>
        <div class="text">
          {{ instructions[currentInstructionIndex].text }}
        </div>
      </div>
    </div>

    <div class="right">
      <div class="acronym">
        <span>S — SIMPLE</span>
        <span>E — ECONOMIC</span>
        <span>G — GAME</span>
      </div>
      <footer>
        <div class="oisdfuoiuiodsfho">{{ sdfhlhksg }}</div>
        <input class="input-box" type="text" placeholder="Введите код" autofocus v-model="sessionId"
          @keyup.enter="joinSession">
      </footer>
    </div>
  </div>
</template>

<style scoped>
* {
  box-sizing: border-box;
}

#page {
  display: flex;
  height: 100vh;
  background-color: #f7b515;
  font-family: "Inter", sans-serif;
  padding: 0;
  margin: 0;
}

.left,
.right {
  width: 50%;
  padding: 40px;
}

.left {
  background-color: #f7b515;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.left-container {
  text-align: center;
  padding: 5%;
  margin: 5%;
  background-color: #e1521d;
}

.image-box {
  width: 100%;
  aspect-ratio: 16 / 9;
  background-color: #555;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 4rem;
  margin-bottom: 20px;
  overflow: hidden;
}

.image-box img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}

.text {
  background-color: #e1521d;
  padding: 30px;
  text-align: center;
  font-size: 3rem;
  line-height: 1.4;
}

.right {
  background-color: #e1521d;

  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content:space-between;

  color: black;
  padding: 90px 50px;
}

.acronym {
  top: 0;
  font-size: 10rem;

  font-family: "Ubuntu Mono", monospace;
  font-weight: 700;
  font-style: normal;
}

.acronym span {
  display: block;
  padding: 15px;

  transition: color 0.3s ease;
}

.acronym span:hover {
  color: #f7b515;
  cursor:default;
}

footer {
  bottom: 0;
  text-align: center;
  width: 100%;
}

.oisdfuoiuiodsfho {
  font-size: 4rem;
  margin-bottom: 20px;;
}

.input-box {
  background-color: #f7b515;
  color: black;
  font-size: 4rem;
  padding: 40px 30px;
  width: 80%;
  
  text-align: center;
  border: none;
  outline: none;
}

.input-box::placeholder {
  color: black;
  opacity: 0.5;
}
</style>