<script setup>
import NavigationButtons from './NavigationButtons.vue'
import { ref, onMounted, inject, computed, nextTick, watch } from 'vue'
import { Chart, registerables } from 'chart.js'

// Register Chart.js components
Chart.register(...registerables)

const emit = defineEmits(['navigateTo'])

const pageRef = ref(null)
const wsManager = inject('wsManager', null)
const chartCanvas = ref(null)
let chartInstance = null

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

// Watch winners for changes
watch(winners, (newWinners, oldWinners) => {
  console.log('[Endgame] Winners changed!', { old: oldWinners, new: newWinners })
}, { deep: true })

// Helper to format numbers with thousand separators
const formatNumber = (num) => {
  return num?.toLocaleString('ru-RU') || '0'
}

// Computed properties for statistics
const allStatistics = computed(() => {
  return wsManager?.gameState?.getStatistics() || []
})

const companyIds = computed(() => {
  return wsManager?.gameState?.getStatisticsCompanyIds() || []
})

// Get top 3 most sold products
const topProducts = computed(() => {
  if (!wsManager) {
    console.warn('[Endgame topProducts] No wsManager')
    return []
  }
  
  const mostSold = wsManager.gameState.getMostSoldProducts()
  console.log('[Endgame topProducts] Most sold products:', mostSold.length)
  
  if (mostSold.length === 0) {
    console.warn('[Endgame topProducts] No products with popularity data')
    return []
  }
  
  // Get top 3 and format with localized resource names
  const top3 = mostSold.slice(0, 3).map(item => {
    const localizedName = wsManager.gameState.getResourceName(item.id)
    console.log(`[Endgame topProducts] ${item.id} -> ${localizedName}, popularity: ${item.popularity}`)
    
    return {
      name: localizedName,
      amount: item.popularity
    }
  })
  
  console.log('[Endgame topProducts] Final top 3:', top3)
  return top3
})

// Chart type state
const currentChartType = ref('balance')

// Function to switch chart type
const switchChart = (type) => {
  currentChartType.value = type
  createChart()
}

// Generic function to create chart
const createChart = () => {
  if (!chartCanvas.value) return

  // Destroy existing chart if it exists
  if (chartInstance) {
    chartInstance.destroy()
  }

  const ctx = chartCanvas.value.getContext('2d')

  // Get real statistics data
  const statistics = allStatistics.value
  console.log('[Endgame] Creating chart with statistics:', statistics)

  // Generate colors for each company
  const colors = [
    'rgb(255, 99, 132)',   // Red
    'rgb(54, 162, 235)',   // Blue
    'rgb(75, 192, 192)',   // Green
    'rgb(255, 159, 64)',   // Orange
    'rgb(153, 102, 255)',  // Purple
    'rgb(255, 205, 86)',   // Yellow
  ]

  // Determine which data to use based on chart type
  let dataKey, chartTitle
  switch (currentChartType.value) {
    case 'balance':
      dataKey = 'balance'
      chartTitle = 'Прогресс баланса компаний'
      break
    case 'reputation':
      dataKey = 'reputation'
      chartTitle = 'Прогресс репутации компаний'
      break
    case 'economic_power':
      dataKey = 'economic_power'
      chartTitle = 'Прогресс экономической мощи компаний'
      break
    default:
      dataKey = 'balance'
      chartTitle = 'Прогресс баланса компаний'
  }

  // Create datasets from real data
  const datasets = statistics.map((companyStat, index) => {
    // Get company name
    const company = wsManager?.gameState?.getCompanyById(companyStat.company_id)
    const companyName = company ? company.name : `Компания ${companyStat.company_id}`
    
    return {
      label: companyName,
      data: companyStat[dataKey],
      borderColor: colors[index % colors.length],
      backgroundColor: colors[index % colors.length].replace('rgb', 'rgba').replace(')', ', 0.1)'),
      borderWidth: 3,
      tension: 0.5,
      pointRadius: 4,
      pointHoverRadius: 6
    }
  })

  // Determine the number of steps from the data
  const maxSteps = statistics.length > 0 ? statistics[0][dataKey].length : 15

  chartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: Array.from({ length: maxSteps }, (_, i) => `Ход ${i + 1}`),
      datasets: datasets
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'top',
          labels: {
            color: 'white',
            font: {
              size: 36
            },
            padding: 30
          }
        },
        title: {
          display: true,
          text: chartTitle,
          color: 'white',
          font: {
            size: 40,
            weight: 'bold'
          },
          padding: 40
        },
        tooltip: {
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          titleFont: {
            size: 28
          },
          bodyFont: {
            size: 26
          },
          padding: 24,
          callbacks: {
            label: function(context) {
              return `${context.dataset.label}: ${context.parsed.y.toLocaleString('ru-RU')}`
            }
          }
        }
      },
      scales: {
        x: {
          ticks: {
            color: 'white',
            font: {
              size: 32
            }
          },
          grid: {
            color: 'rgba(255, 255, 255, 0.1)'
          }
        },
        y: {
          ticks: {
            color: 'white',
            font: {
              size: 32
            },
            callback: function(value) {
              return value.toLocaleString('ru-RU')
            }
          },
          grid: {
            color: 'rgba(255, 255, 255, 0.2)'
          }
        }
      }
    }
  })
}

onMounted(async () => {
  // Stop polling when on Endgame page (game has ended, no need to fetch updates)
  if (wsManager) {
    console.log('[Endgame] Stopping polling - game has ended')
    wsManager.stopPolling()
  }
  
  // Fetch statistics and leaders for the ended game
  if (wsManager) {
    console.log('[Endgame] Mounted, current winners:', winners.value)
    console.log('[Endgame] WebSocket connected:', wsManager.gameState.state.connected)
    
    // Wait for WebSocket connection if not connected yet
    if (!wsManager.gameState.state.connected) {
      console.log('[Endgame] Waiting for WebSocket connection...')
      const connected = await wsManager.waitForConnection(10000)
      
      if (!connected) {
        console.error('[Endgame] Failed to establish WebSocket connection')
        return
      }
      
      console.log('[Endgame] WebSocket connection established')
    }
    
    // Check if we have a session ID
    if (!wsManager.gameState.state.session.id) {
      console.error('[Endgame] No session ID available')
      return
    }
    
    console.log('[Endgame] Fetching data for session:', wsManager.gameState.state.session.id)
    
    // Fetch leaders/winners
    wsManager.get_session_leaders((response) => {
      if (response.success) {
        console.log('[Endgame] Leaders fetched successfully:', response.data)
      } else {
        console.error('[Endgame] Failed to fetch leaders:', response.error)
      }
    })
    
    // Fetch item prices (for most sold products)
    wsManager.get_all_item_prices((response) => {
      if (response.success) {
        console.log('[Endgame] Item prices fetched successfully')
        console.log('[Endgame] Most sold products:', wsManager.gameState.getMostSoldProducts())
      } else {
        console.error('[Endgame] Failed to fetch item prices:', response.error)
      }
    })
    
    // Fetch all statistics for this session
    wsManager.get_session_statistics((response) => {
      if (response.success) {
        console.log('[Endgame] Statistics fetched successfully')
        console.log('[Endgame] All stats:', wsManager.gameState.getStatistics())
        
        // Create chart with real data
        nextTick(() => {
          createChart()
        })
      } else {
        console.error('[Endgame] Failed to fetch statistics:', response.error)
        // Create chart anyway
        nextTick(() => {
          createChart()
        })
      }
    })
  } else {
    // No wsManager, create chart
    nextTick(() => {
      createChart()
    })
  }
})

</script>

<template>
  <div id="page" ref="pageRef">
    
    <div id="column-left">
      <!-- Chart container -->
      <div id="graph-container">
        <canvas ref="chartCanvas"></canvas>
        
        <!-- Chart type switcher buttons -->
        <div class="chart-switcher">
          <button 
            @click="switchChart('balance')" 
            :class="{ active: currentChartType === 'balance' }"
            class="chart-btn"
            title="Баланс">
            Баланс
          </button>
          <button 
            @click="switchChart('reputation')" 
            :class="{ active: currentChartType === 'reputation' }"
            class="chart-btn"
            title="Репутация">
            Репутация
          </button>
          <button 
            @click="switchChart('economic_power')" 
            :class="{ active: currentChartType === 'economic_power' }"
            class="chart-btn"
            title="Экономическая мощь">
            Эконом. уровень
          </button>
        </div>
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
  padding: 20px 20px 90px 20px;
  position: relative;
}

/* Chart switcher buttons */
.chart-switcher {
  position: absolute;
  bottom: 16px;
  right: 16px;
  display: flex;
  gap: 16px;
  z-index: 10;
}

.chart-btn {
  background: rgba(51, 51, 51, 1);
  border: none;
  padding: 10px;
  color: white;
  font-size: 3rem;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.3s ease;
  font-family: "Ubuntu Mono", monospace;
}

.chart-btn:hover {
  transform: scale(1.05);
}

.chart-btn.active {
  background: rgba(71, 71, 71, 1);
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
