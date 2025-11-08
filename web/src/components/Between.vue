<script setup>
import Map from './Map.vue'
import NavigationButtons from './NavigationButtons.vue'
import Products from './Products.vue'
import { onMounted, onUnmounted, ref, inject, computed } from 'vue'

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

// Computed properties for time and turn display
const timeToNextStage = computed(() => {
  // Access the reactive state directly for proper reactivity
  const time = wsManager?.gameState?.state?.timeToNextStage
  if (time === null || time === undefined) return '--:--'
  const minutes = Math.floor(time / 60)
  const seconds = time % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
})

const turnInfo = computed(() => {
  const step = wsManager?.gameState?.state?.session?.step || 0
  const maxSteps = wsManager?.gameState?.state?.session?.max_steps || 0
  return `${step}/${maxSteps}`
})

// Products are now handled by the Products component

// Leaders computed property
const leaders = computed(() => {
  // Try to get session ID from session object
  let sessionId = wsManager?.gameState?.state?.session?.id
  
  // If no session ID, try to get all companies and use the first company's session_id
  const allCompanies = wsManager?.gameState?.state?.companies || []
  
  console.log('[Between.vue] Leaders - Session ID from session:', sessionId)
  console.log('[Between.vue] Leaders - All companies:', allCompanies)
  console.log('[Between.vue] Leaders - All companies count:', allCompanies.length)
  
  // If sessionId is null but we have companies, use the first company's session_id
  if (!sessionId && allCompanies.length > 0) {
    sessionId = allCompanies[0].session_id
    console.log('[Between.vue] Leaders - Using session_id from first company:', sessionId)
  }
  
  if (!sessionId) {
    console.log('[Between.vue] Leaders - No sessionId found anywhere')
    return { capital: null, reputation: null, economic: null }
  }
  
  const companies = wsManager?.gameState?.getCompaniesBySession(sessionId) || []
  console.log('[Between.vue] Leaders - Filtered companies:', companies)
  console.log('[Between.vue] Leaders - Filtered companies count:', companies.length)
  
  if (companies.length === 0) {
    console.log('[Between.vue] Leaders - No companies found for session:', sessionId)
    // Try using all companies as fallback
    if (allCompanies.length > 0) {
      console.log('[Between.vue] Leaders - Using all companies as fallback')
      const byCapital = [...allCompanies].sort((a, b) => (b.balance || 0) - (a.balance || 0))[0]
      const byReputation = [...allCompanies].sort((a, b) => (b.reputation || 0) - (a.reputation || 0))[0]
      const byEconomic = [...allCompanies].sort((a, b) => (b.economic_power || 0) - (a.economic_power || 0))[0]
      
      console.log('[Between.vue] Leaders - byCapital (fallback):', byCapital)
      console.log('[Between.vue] Leaders - byReputation (fallback):', byReputation)
      console.log('[Between.vue] Leaders - byEconomic (fallback):', byEconomic)
      
      return {
        capital: byCapital,
        reputation: byReputation,
        economic: byEconomic
      }
    }
    return { capital: null, reputation: null, economic: null }
  }
  
  // Find top companies
  const byCapital = [...companies].sort((a, b) => (b.balance || 0) - (a.balance || 0))[0]
  const byReputation = [...companies].sort((a, b) => (b.reputation || 0) - (a.reputation || 0))[0]
  const byEconomic = [...companies].sort((a, b) => (b.economic_power || 0) - (a.economic_power || 0))[0]
  
  console.log('[Between.vue] Leaders - byCapital:', byCapital)
  console.log('[Between.vue] Leaders - byReputation:', byReputation)
  console.log('[Between.vue] Leaders - byEconomic:', byEconomic)
  
  const result = {
    capital: byCapital,
    reputation: byReputation,
    economic: byEconomic
  }
  
  console.log('[Between.vue] Leaders - result:', result)
  
  return result
})

// Helper to format numbers with thousand separators
const formatNumber = (num) => {
  return num?.toLocaleString('ru-RU') || '0'
}

// Event computed property
const currentEvent = computed(() => {
  if (!wsManager?.gameState?.state) {
    return null
  }
  
  const eventData = wsManager.gameState.state.event
  console.log('[Between.vue] Current event from state:', eventData)
  
  // Проверяем, не завернуто ли событие в дополнительный объект
  if (eventData && eventData.event) {
    console.log('[Between.vue] Event is wrapped, extracting inner event:', eventData.event)
    return eventData.event
  }
  
  // Возвращаем событие как есть
  return eventData
})

// Helper to get event status text
const eventStatusText = computed(() => {
  const event = currentEvent.value
  console.log('[Between.vue] eventStatusText - event:', event)
  
  if (!event) {
    console.log('[Between.vue] eventStatusText - no event')
    return null
  }
  
  console.log('[Between.vue] eventStatusText - checking status:', {
    is_active: event.is_active,
    starts_next_turn: event.starts_next_turn,
    predictable: event.predictable,
    start_step: event.start_step
  })
  
  // Отображаем статус как есть, без сложной логики
  if (event.is_active) {
    return 'Действует сейчас'
  } else if (event.starts_next_turn) {
    return 'Начнётся на следующем ходу'
  } else if (event.predictable && event.start_step !== undefined) {
    const currentStep = wsManager?.gameState?.state?.session?.step || 0
    const stepsUntil = event.start_step - currentStep
    
    console.log('[Between.vue] eventStatusText - predictable event, currentStep:', currentStep, 'stepsUntil:', stepsUntil)
    
    if (stepsUntil <= 0) {
      const stepsUntilEnd = event.end_step ? (event.end_step - currentStep) : null
      if (stepsUntilEnd && stepsUntilEnd > 0) {
        return `Закончится через ${stepsUntilEnd} ход${stepsUntilEnd === 1 ? '' : stepsUntilEnd < 5 ? 'а' : 'ов'}`
      } else {
        return 'Заканчивается в этом ходу'
      }
    } else {
      return `Начнётся через ${stepsUntil} ход${stepsUntil === 1 ? '' : stepsUntil < 5 ? 'а' : 'ов'}`
    }
  }
  
  console.log('[Between.vue] eventStatusText - no status match')
  return null
})

// Function to refresh event data
const refreshEventData = () => {
  if (wsManager && wsManager.get_session_event) {
    console.log('[Between.vue] Refreshing event data...')
    wsManager.get_session_event((response) => {
      console.log('[Between.vue] Event refresh response:', response)
      
      if (response && response.success) {
        const eventData = response.data
        console.log('[Between.vue] Event data received:', eventData)
        
        // Напрямую записываем данные события без проверок
        if (wsManager.gameState && wsManager.gameState.state) {
          console.log('[Between.vue] Setting event in state:', eventData)
          wsManager.gameState.state.event = eventData
        } else {
          console.error('[Between.vue] GameState or state not available')
        }
      } else {
        console.log('[Between.vue] Event request failed or no success:', response)
      }
    })
  } else {
    console.log('[Between.vue] WebSocket manager or get_session_event not available')
  }
}

// Интервал для периодической проверки событий
let eventCheckInterval = null

onMounted(() => {
  console.log('[Between.vue] Component mounted - checking initial state')
  console.log('[Between.vue] wsManager on mount:', !!wsManager)
  console.log('[Between.vue] gameState on mount:', !!wsManager?.gameState)
  console.log('[Between.vue] state on mount:', !!wsManager?.gameState?.state)
  console.log('[Between.vue] event on mount:', wsManager?.gameState?.state?.event)
  
  // Log the entire gameState structure for debugging
  if (wsManager?.gameState?.state) {
    console.log('[Between.vue] Full state keys:', Object.keys(wsManager.gameState.state))
  }

  // Запрашиваем актуальное событие при загрузке межэтапа
  refreshEventData()

  // Добавляем интервал для периодической проверки событий каждые 10 секунд
  eventCheckInterval = setInterval(() => {
    console.log('[Between.vue] Periodic event check...')
    refreshEventData()
  }, 10000) // 10 секунд
})

// Очистка интервала при размонтировании компонента
onUnmounted(() => {
  if (eventCheckInterval) {
    clearInterval(eventCheckInterval)
    eventCheckInterval = null
  }
})


</script>


<template>
  <!--
    Preparation page layout.
    Left column: title, map, session key.
    Right columns: alternating company slots (left/right).
  -->
  <div id="page" ref="pageRef">
    <div class="left">
      <div class="footer">
        <div>До конца этапа {{ timeToNextStage }}</div>
        <div>{{ turnInfo }}</div>
      </div>
      <Map class="map" />
    </div>
    <div class="right">
      <div class="grid">

        <div class="products grid-item">
          <Products title="ПРОДУКТЫ" />
        </div>

        <div class="leaders grid-item">
          <p class="title">ЛИДЕРЫ</p>
          <div class="content">
            <section>
              <p class="name">КАПИТАЛ</p>
              <p class="desc" v-if="leaders.capital">{{ leaders.capital.name }} ({{ formatNumber(leaders.capital.balance) }})</p>
              <p class="desc" v-else>—</p>
            </section>
            <section>
              <p class="name">РЕПУТАЦИЯ</p>
              <p class="desc" v-if="leaders.reputation">{{ leaders.reputation.name }} ({{ leaders.reputation.reputation }})</p>
              <p class="desc" v-else>—</p>
            </section>
            <section>
              <p class="name">ЭКОНОМИЧЕСКИЙ УРОВЕНЬ</p>
              <p class="desc" v-if="leaders.economic">{{ leaders.economic.name }} ({{ leaders.economic.economic_power }})</p>
              <p class="desc" v-else>—</p>
            </section>
          </div>
        </div>
      </div>

      <!-- Events section -->
      <div v-if="currentEvent" class="event-block">
        <div class="event-header">СОБЫТИЕ</div>
        <div class="event-title">{{ currentEvent.name }}</div>
        <div class="event-description">{{ currentEvent.description }}</div>
      </div>
      
      <div v-else class="no-events-block">
        Нет событий
      </div>

    </div>
    
    <!-- Navigation Buttons -->
    <NavigationButtons @leave="handleLeave" @showAbout="handleAbout" />
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

.left,
.right {
  width: 50%;
  padding: 40px;
}


.left {
  background-color: #3D8C00;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.right {
  background-color: #0C6892;
  color: black;
  padding: 90px 50px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  height: 100vh;
  box-sizing: border-box;
}

.grid {
  display: flex;
  flex-direction: row;
  gap: 5%;
  width: 100%;
  justify-content: space-between;
  align-items: stretch;
  flex: 1;
  margin-bottom: 40px;
}

.grid-item {
  width: 47.5%;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
}

.content {
  font-size: 2.25rem;
  color: white;
  font-weight: 400;
}

.title {
  font-size: 4rem;
  margin: 0;
  margin-bottom: 20px;
  text-transform: uppercase;
  color: white;
  text-align: center;
  font-family: "Ubuntu Mono", monospace;
}

.leaders .content {
  display: flex;
  flex-direction: column;
  gap: 36px;
}

.products {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.leaders section {
  background: #3D8C00;
  padding: 15px 20px;
  border-radius: 8px;
  margin-bottom: 15px;
}

.content {
  font-family: "Ubuntu Mono", monospace;
  text-align: center;
}

.name {
  font-size: 2.2rem;
  text-transform: uppercase;
  margin: 0;
  margin-bottom: 8px;
  font-weight: bold;
}

.desc {
  opacity: 90%;
  margin: 0;
  font-size: 1.8rem;
  line-height: 1.3;
}

.event-block {
  background-color: #3D8C00;
  border-radius: 12px;
  padding: 0;
  flex-shrink: 0;
  color: white;
  font-family: "Ubuntu Mono", monospace;
  margin-top: 20px;
  overflow: hidden;
}

.event-header {
  background-color: rgba(0, 0, 0, 0.2);
  padding: 8px 15px;
  font-size: 1.4rem;
  text-transform: uppercase;
  font-weight: bold;
  text-align: left;
  margin: 0;
}

.event-title {
  padding: 20px 25px 10px 25px;
  font-size: 2.5rem;
  font-weight: bold;
  text-transform: uppercase;
  text-align: center;
  margin: 0;
}

.event-description {
  padding: 0 25px 25px 25px;
  font-size: 1.8rem;
  line-height: 1.4;
  text-align: center;
  margin: 0;
}

.no-events-block {
  background-color: #3D8C00;
  border-radius: 12px;
  padding: 40px 20px;
  flex-shrink: 0;
  color: white;
  font-family: "Ubuntu Mono", monospace;
  font-size: 3rem;
  text-align: center;
  margin-top: 20px;
}

.footer {
  width: 90%;

  background: #0C6792;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;

  font-family: "Ubuntu Mono", monospace;
  font-weight: normal;
  font-size: 4rem;

  color: white;
}

.footer div {
  margin: 25px;
}

.map {
  width: 90%;
  margin: 0;
  padding: 0;
}
</style>
