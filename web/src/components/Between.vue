<script setup>
import Map from './Map.vue'
import LeaveButton from './LeaveButton.vue'
import Products from './Products.vue'
import { onMounted, onUnmounted, ref, inject, computed } from 'vue'

const emit = defineEmits(['navigateTo'])

const pageRef = ref(null)
const wsManager = inject('wsManager', null)

// Handle leave button click
const handleLeave = () => {
  emit('navigateTo', 'Introduction')
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
  console.log('[Between.vue] === EVENT DEBUG START ===')
  console.log('[Between.vue] wsManager exists:', !!wsManager)
  console.log('[Between.vue] gameState exists:', !!wsManager?.gameState)
  console.log('[Between.vue] state exists:', !!wsManager?.gameState?.state)
  
  // Access the reactive state directly for proper reactivity
  const event = wsManager?.gameState?.state?.event
  console.log('[Between.vue] Raw event object:', event)
  console.log('[Between.vue] Event type:', typeof event)
  
  if (event) {
    console.log('[Between.vue] Event properties:')
    console.log('[Between.vue] - id:', event.id)
    console.log('[Between.vue] - name:', event.name)
    console.log('[Between.vue] - description:', event.description)
    console.log('[Between.vue] - is_active:', event.is_active)
    console.log('[Between.vue] - starts_next_turn:', event.starts_next_turn)
    console.log('[Between.vue] - predictable:', event.predictable)
    console.log('[Between.vue] - start_step:', event.start_step)
    console.log('[Between.vue] - end_step:', event.end_step)
    console.log('[Between.vue] - All event keys:', Object.keys(event))
  } else {
    console.log('[Between.vue] Event is null/undefined')
  }
  
  // Check the condition
  const hasId = event && event.id
  console.log('[Between.vue] Has ID check:', hasId)
  console.log('[Between.vue] Final result:', hasId ? event : null)
  console.log('[Between.vue] === EVENT DEBUG END ===')
  
  // Return event only if it has an ID (meaning it exists)
  return hasId ? event : null
})

// Helper to get event status text
const eventStatusText = computed(() => {
  const event = currentEvent.value
  console.log('[Between.vue] === EVENT STATUS DEBUG START ===')
  console.log('[Between.vue] Event for status:', event)
  
  if (!event || !event.id) {
    console.log('[Between.vue] No event or no ID, returning null')
    return null
  }
  
  console.log('[Between.vue] Event status check:')
  console.log('[Between.vue] - is_active:', event.is_active)
  console.log('[Between.vue] - starts_next_turn:', event.starts_next_turn)
  console.log('[Between.vue] - predictable:', event.predictable)
  
  let statusText = null
  
  if (event.is_active) {
    statusText = 'Действует сейчас'
    console.log('[Between.vue] Status: Active')
  } else if (event.starts_next_turn) {
    statusText = 'Начнётся на следующем ходу'
    console.log('[Between.vue] Status: Starts next turn')
  } else if (event.predictable) {
    const currentStep = wsManager?.gameState?.state?.session?.step
    const stepsUntil = event.start_step - currentStep
    console.log('[Between.vue] Predictable event - current step:', currentStep, 'start step:', event.start_step, 'steps until:', stepsUntil)
    console.log('[Between.vue] Event end_step:', event.end_step)
    
    if (stepsUntil <= 0) {
      // Событие уже началось, показываем когда закончится
      const stepsUntilEnd = event.end_step ? (event.end_step - currentStep) : null
      console.log('[Between.vue] Steps until end:', stepsUntilEnd)
      
      if (stepsUntilEnd && stepsUntilEnd > 0) {
        statusText = `Закончится через ${stepsUntilEnd} ход${stepsUntilEnd === 1 ? '' : stepsUntilEnd < 5 ? 'а' : 'ов'}`
      } else {
        statusText = 'Заканчивается в этом ходу'
      }
    } else {
      // Событие ещё не началось
      statusText = `Начнётся через ${stepsUntil} ход${stepsUntil === 1 ? '' : stepsUntil < 5 ? 'а' : 'ов'}`
    }
    console.log('[Between.vue] Status: Predictable -', statusText)
  } else {
    console.log('[Between.vue] No status matched')
  }
  
  console.log('[Between.vue] Final status text:', statusText)
  console.log('[Between.vue] === EVENT STATUS DEBUG END ===')
  
  return statusText
})

// Function to refresh event data
const refreshEventData = () => {
  if (wsManager && wsManager.get_session_event) {
    console.log('[Between.vue] Refreshing event data...')
    wsManager.get_session_event((response) => {
      console.log('[Between.vue] Event refresh response:', response)
      
      if (response && response.success) {
        const eventData = response.data
        
        if (eventData && eventData.id) {
          console.log('[Between.vue] Valid event received - updating state:', eventData)
          wsManager.gameState.updateEvent(eventData)
        } else {
          console.log('[Between.vue] Empty/null event data - event has ended, clearing from state')
          wsManager.gameState.clearEvent()
        }
      } else {
        console.log('[Between.vue] Event request failed:', response)
      }
    })
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

  // Добавляем интервал для периодической проверки событий каждые 30 секунд
  eventCheckInterval = setInterval(() => {
    console.log('[Between.vue] Periodic event check...')
    refreshEventData()
  }, 30000) // 30 секунд
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
              <p class="name">ПО КАПИТАЛУ</p>
              <p class="desc" v-if="leaders.capital">{{ leaders.capital.name }} ({{ formatNumber(leaders.capital.balance) }})</p>
              <p class="desc" v-else>—</p>
            </section>
            <section>
              <p class="name">ПО РЕПУТАЦИИ</p>
              <p class="desc" v-if="leaders.reputation">{{ leaders.reputation.name }} ({{ leaders.reputation.reputation }})</p>
              <p class="desc" v-else>—</p>
            </section>
            <section>
              <p class="name">ПО ЭКОНОМИЧЕСКОМУ УРОВНЮ</p>
              <p class="desc" v-if="leaders.economic">{{ leaders.economic.name }} ({{ leaders.economic.economic_power }})</p>
              <p class="desc" v-else>—</p>
            </section>
          </div>
        </div>
      </div>

      <!-- Events section moved below grid -->
      <div class="events">

        <div v-if="currentEvent && currentEvent.id" class="event-content">
          <div class="event-name">{{ currentEvent.name }}</div>
          <div class="event-status" v-if="eventStatusText">{{ eventStatusText }}</div>
          <div class="event-description">{{ currentEvent.description }}</div>
        </div>
        <span v-else>Нет событий</span>
      </div>

    </div>
    
    <!-- Leave Button -->
    <LeaveButton @leave="handleLeave" />
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
}

.grid {
  margin: auto;
  display: flex;
  flex-direction: row;
  gap: 5%;
  padding: 0;
  margin: 0;

  width: 100%;

  justify-items: stretch;
  align-items: stretch;
  align-content: stretch;
  justify-content: space-between;
  margin-bottom: 40px;
}

.grid-item {
  width: 100%;
  height: 100%;
  /* background: #0f0; */
}

.content {
  font-size: 2.25rem;
  color: white;
  font-weight: 400;
}

.title {
  font-size: 4rem;
  margin: 0;
  margin-bottom: 10px;
  text-transform: uppercase;
  margin-bottom: 20px;
  color: white;
  text-align: center;
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
  padding: 5px 10px;
}

.content {
  font-family: "Ubuntu Mono", monospace;
  text-align: center;
}

.name {
  font-size: 3rem;
  text-transform: uppercase;
  margin: 0;
}

.desc {
  opacity: 80%;
  margin: 0;

}

.events {
  font-size: 5rem;
  text-transform: uppercase;

  text-align: center;
  justify-content: center;

  padding: 40px 0;

  background-color: #3D8C00;

  color: white;
  font-family: "Ubuntu Mono", monospace;
}

.event-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.event-name {
  font-size: 5rem;
  font-weight: bold;
}

.event-status {
  font-size: 2.5rem;
  opacity: 0.8;
  font-style: italic;
}

.event-description {
  font-size: 3rem;
  opacity: 0.9;
  margin-top: 10px;
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
