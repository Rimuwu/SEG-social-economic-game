<script setup>
import LeaveButton from './LeaveButton.vue'
import { ref, onMounted, inject, computed } from 'vue'

const emit = defineEmits(['navigateTo'])

const pageRef = ref(null)
const wsManager = inject('wsManager', null)

// Handle leave button click
const handleLeave = () => {
  emit('navigateTo', 'Introduction')
}

// Get AUTHORS from environment, with fallback
const AUTHORS = import.meta.env.VITE_AUTHORS || 'SEG Development Team';

// Computed property for winners
const winners = computed(() => {
  return wsManager?.gameState?.getWinners() || {
    capital: null,
    reputation: null,
    economic: null
  }
})

// Helper to format numbers with thousand separators
const formatNumber = (num) => {
  return num?.toLocaleString('ru-RU') || '0'
}

onMounted(() => {
  const authorsElement = document.getElementById("authors")
  if (authorsElement) {
    authorsElement.innerHTML = AUTHORS.split("/").join("<br/>");
  }
  
  // Fetch current game state to get winners
  if (wsManager) {
    console.log('[Endgame] Mounted, current winners:', winners.value)
  }
})

</script>

<template>
  <div id="page" ref="pageRef">
    
    <div id="column-left">
      <p id="title">Победители</p>
      <div id="by-money" class="element">
        <p class="title">по капиталу</p>
        <p class="name" v-if="winners.capital">{{ winners.capital.name }}</p>
        <p class="name" v-else>—</p>
        <p class="value" v-if="winners.capital">{{ formatNumber(winners.capital.balance) }}</p>
      </div>
      <div id="by-rep" class="element">
        <p class="title">по репутации</p>
        <p class="name" v-if="winners.reputation">{{ winners.reputation.name }}</p>
        <p class="name" v-else>—</p>
        <p class="value" v-if="winners.reputation">Репутация: {{ winners.reputation.reputation }}</p>
      </div>
      <div id="by-level" class="element">
        <p class="title">по экономическому уровню</p>
        <p class="name" v-if="winners.economic">{{ winners.economic.name }}</p>
        <p class="name" v-else>—</p>
        <p class="value" v-if="winners.economic">Эконом. мощь: {{ winners.economic.economic_power }}</p>
      </div>
    </div>

    <div id="column-right">
      <p>
        Спасибо за игру в SEG.<br/><br/>
        Игра создана и разработана по авторской идеи и без использования потусторонних сил.<br/><br/>
        Создатели:<br/>
        <span id="authors"></span>
      </p>
    </div>
    
    <!-- Leave Button -->
    <LeaveButton @leave="handleLeave" />
  </div>

</template>

<style scoped>
#page {
  display: flex;
  align-items: stretch;

  margin: 0;
  padding: 0;

  width: 100%;
  height: 100vh;

  background: #0C9273;
}

#column-left {
  flex: 2;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  background: #0C9273;
  gap: 36px;
}

#column-right {
  flex: 1;
  display: flex;
  flex-direction: column;

  background: #0C6892;

  font-size: 4rem;
  color: white;
  text-align: center;
  justify-content: center;
  line-height: 1.5;
}

#title {
  color: white;
  font-size: 6rem;
  margin: 0;
}

.element {
  margin: 0;
  padding: 10px;
  color: white;
  text-align: center;
  background: #0C6892;
  width: 90%;
}

.title {
  font-family: "Ubuntu Mono", monospace;
  font-size: 4rem;
  text-transform: uppercase;
}
.name {
  font-size: 5rem;
  margin: 5px 0;
}
.value {
  font-size: 3rem;
  opacity: 0.8;
  margin: 5px 0;
  font-family: "Ubuntu Mono", monospace;
}
</style>
