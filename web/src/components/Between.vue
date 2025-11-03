<script setup>
import Map from './Map.vue'
import { onMounted, ref, inject, computed } from 'vue'

const pageRef = ref(null)
const wsManager = inject('wsManager', null)

// Computed properties for time and turn display
const timeToNextStage = computed(() => {
  return wsManager?.gameState?.getFormattedTimeToNextStage() || '--:--'
})

const turnInfo = computed(() => {
  const step = wsManager?.gameState?.state?.session?.step || 0
  const maxSteps = wsManager?.gameState?.state?.session?.max_steps || 0
  return `${step}/${maxSteps}`
})

// Store randomly selected product IDs
const randomProductIds = ref([])

// Products computed property
const products = computed(() => {
  if (!wsManager || !wsManager.gameState) return []
  
  const prices = wsManager.gameState.state.itemPrices || {}
  const allIds = Object.keys(prices)
  
  // If we don't have random IDs yet, or if products changed significantly, pick new ones
  if (randomProductIds.value.length === 0 || randomProductIds.value.length > allIds.length) {
    const shuffled = [...allIds].sort(() => Math.random() - 0.5)
    randomProductIds.value = shuffled.slice(0, Math.min(10, allIds.length))
  }
  
  // Map the selected IDs to product objects with localized names
  return randomProductIds.value
    .filter(itemId => prices[itemId] !== undefined) // Ensure item still exists
    .map(itemId => {
      const price = prices[itemId]
      // Get localized name from GameState
      const localizedName = wsManager.gameState.getResourceName(itemId) || itemId
      
      console.log(`[Between.vue] Product: ${itemId} -> ${localizedName}, Price: ${price}`)
      
      return {
        id: itemId,
        name: localizedName,
        price: price
      }
    })
})

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
  const event = wsManager?.gameState?.getEvent() || null
  console.log('[Between.vue] Current event:', event)
  return event
})

// Helper to get event status text
const eventStatusText = computed(() => {
  const event = currentEvent.value
  if (!event || !event.id) return null
  
  if (event.is_active) {
    return 'Действует сейчас'
  } else if (event.starts_next_turn) {
    return 'Начнётся на следующем ходу'
  } else if (event.predictable) {
  const stepsUntil = event.start_step - wsManager?.gameState?.state?.session?.step
    return `Начнётся через ${stepsUntil} ход${stepsUntil === 1 ? '' : stepsUntil < 5 ? 'а' : 'ов'}`
  }
  return null
})

onMounted(() => {
  // Component mounted
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
      <Map class="map" />
      <div class="footer">
        <div>До конца этапа {{ timeToNextStage }}</div>
        <div>{{ turnInfo }}</div>
      </div>
    </div>
    <div class="right">
      <div class="grid">

        <div class="products grid-item">
          <p class="title">ТОВАРЫ</p>
          <div class="content">
            <section v-for="product in products" :key="product.id">
              <p class="name">{{ product.name }} — {{ product.price }}</p>
            </section>
            <section v-if="products.length === 0">
              <p class="desc">Цены на товары загружаются...</p>
            </section>
          </div>
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

      <div class="events">
        <div v-if="currentEvent && currentEvent.id" class="event-content">
          <div class="event-name">{{ currentEvent.name }}</div>
          <div class="event-status" v-if="eventStatusText">{{ eventStatusText }}</div>
          <div class="event-description">{{ currentEvent.description }}</div>
        </div>
        <span v-else>Нет событий</span>
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

.products .content,
.leaders .content {
  display: flex;
  flex-direction: column;
  gap: 36px;
}

.products .content {
  gap: 10px;
}

.products section,
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

.products .name {
  font-size: 2rem;
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

  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;

  font-weight: normal;
  font-size: 4rem;

  gap: 5%;

  color: white;
}

.footer div {
  background: #0C6792;
  padding: 25px 50px;
}

.map {
  width: 90%;
  margin: 0;
  padding: 0;
}
</style>
