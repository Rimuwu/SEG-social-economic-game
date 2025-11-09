<script setup>
import NavigationButtons from './NavigationButtons.vue'
import { ref, onMounted, inject, computed } from 'vue'

const emit = defineEmits(['navigateTo'])

const pageRef = ref(null)
const wsManager = inject('wsManager', null)

// Handle navigation
const handleLeave = () => {
  emit('navigateTo', 'Introduction')
}

const handleAbout = () => {
  emit('navigateTo', 'About')
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

// Computed properties for statistics
const statisticsBalance = computed(() => {
  return wsManager?.gameState?.getStatisticsBalance() || {}
})

const statisticsReputation = computed(() => {
  return wsManager?.gameState?.getStatisticsReputation() || {}
})

const statisticsEconomicPower = computed(() => {
  return wsManager?.gameState?.getStatisticsEconomicPower() || {}
})

const companyNames = computed(() => {
  return wsManager?.gameState?.getStatisticsCompanyNames() || []
})

// Get top 3 most sold products (mock data for now - will be populated with real data)
const topProducts = computed(() => {
  // TODO: Get real data from API/GameState
  return [
    { name: 'Товар 1', amount: 1500 },
    { name: 'Товар 2', amount: 1200 },
    { name: 'Товар 3', amount: 980 }
  ]
})

onMounted(() => {
  // Fetch statistics for the ended game
  if (wsManager) {
    console.log('[Endgame] Mounted, current winners:', winners.value)
    console.log('[Endgame] Fetching statistics for session:', wsManager.gameState.state.session.id)
    
    // Fetch all statistics for this session
    wsManager.get_session_statistics((response) => {
      if (response.success) {
        console.log('[Endgame] Statistics fetched successfully')
        console.log('[Endgame] Balance stats:', wsManager.gameState.getStatisticsBalance())
        console.log('[Endgame] Reputation stats:', wsManager.gameState.getStatisticsReputation())
        console.log('[Endgame] Economic Power stats:', wsManager.gameState.getStatisticsEconomicPower())
      } else {
        console.error('[Endgame] Failed to fetch statistics:', response.error)
      }
    })
  }
})

</script>

<template>
  <div id="page" ref="pageRef">
    
    <div id="column-left">
      <!-- Graph placeholder -->
      <div id="graph-container">
        <p class="placeholder-text">График будет здесь</p>
      </div>

      <!-- Top 3 products row -->
      <div id="products-row">
        <div v-for="(product, index) in topProducts" :key="index" class="product-item">
          <p class="product-name">{{ product.name }}</p>
          <p class="product-amount">Продано {{ formatNumber(product.amount) }} раз</p>
        </div>
      </div>
    </div>

    <div id="column-right">
      <p id="title">Победители</p>
      
      <div id="by-money" class="winner-element">
        <p class="winner-title">по капиталу</p>
        <p class="winner-name" v-if="winners.capital">{{ winners.capital.name }}</p>
        <p class="winner-name" v-else>—</p>
        <p class="winner-value" v-if="winners.capital">{{ formatNumber(winners.capital.balance) }}</p>
      </div>
      
      <div id="by-rep" class="winner-element">
        <p class="winner-title">по репутации</p>
        <p class="winner-name" v-if="winners.reputation">{{ winners.reputation.name }}</p>
        <p class="winner-name" v-else>—</p>
        <p class="winner-value" v-if="winners.reputation">{{ winners.reputation.reputation }}</p>
      </div>
      
      <div id="by-level" class="winner-element">
        <p class="winner-title">по экономическому уровню</p>
        <p class="winner-name" v-if="winners.economic">{{ winners.economic.name }}</p>
        <p class="winner-name" v-else>—</p>
        <p class="winner-value" v-if="winners.economic">{{ winners.economic.economic_power }}</p>
      </div>
    </div>
    
    <!-- Navigation Buttons -->
    <NavigationButtons @leave="handleLeave" @showAbout="handleAbout" />
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
  height: 95%;
  display: flex;
  flex-direction: column;
  background: #0C9273;
  padding: 40px;
  gap: 20px;
}

#column-right {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: space-evenly;
  padding: 40px;

  background: #0C6892;

  color: white;
  gap: 36px;
}

/* Graph container */
#graph-container {
  flex: 9;
  background: #0C6892;
  display: flex;
  align-items: center;
  justify-content: center;
}

.placeholder-text {
  color: white;
  font-size: 4rem;
  opacity: 0.6;
  margin: 0;
}

/* Products row */
#products-row {
  flex: 1;
  display: flex;
  gap: 20px;
  justify-content: space-between;
  padding: 20px 0;
}

.product-item {
  flex: 1;
  background: #0C6892;
  padding: 20px;
  text-align: center;
  color: white;
}

.product-name {
  font-size: 3rem;
  font-weight: bold;
  margin: 0 0 10px 0;
  font-family: "Ubuntu Mono", monospace;
  text-transform: uppercase;
}

.product-amount {
  font-size: 3.5rem;
  margin: 0;
  opacity: 0.9;
}

/* Winners section */
#title {
  color: white;
  font-size: 6rem;
  margin: 0;
  text-align: center;
}

.winner-element {
  margin: 0;
  padding: 20px;
  color: white;
  text-align: center;
  background: #0C9273;
  width: 100%;
}

.winner-title {
  font-family: "Ubuntu Mono", monospace;
  font-size: 3rem;
  text-transform: uppercase;
  margin: 0 0 10px 0;
}

.winner-name {
  font-size: 4.5rem;
  font-weight: bold;
  margin: 10px 0;
}

.winner-value {
  font-size: 3rem;
  opacity: 0.8;
  margin: 10px 0;
  font-family: "Ubuntu Mono", monospace;
}
</style>
