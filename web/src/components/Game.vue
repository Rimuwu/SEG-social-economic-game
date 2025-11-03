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

// Computed properties for cities
const city1 = computed(() => {
  return wsManager?.gameState?.getCityById(1) || null
})

const city2 = computed(() => {
  return wsManager?.gameState?.getCityById(2) || null
})

const city3 = computed(() => {
  return wsManager?.gameState?.getCityById(3) || null
})

const city4 = computed(() => {
  return wsManager?.gameState?.getCityById(4) || null
})

// Helper function to format city demands
const formatCityDemands = (city) => {
  console.log('[Game.vue] formatCityDemands called for city:', city);
  
  if (!city || !city.demands) {
    console.log('[Game.vue] No city or no demands:', { city: !!city, demands: !!city?.demands });
    return []
  }
  
  console.log('[Game.vue] City demands object:', city.demands);
  
  // Filter demands with amount > 0 and get only 2
  const formatted = Object.entries(city.demands)
    .filter(([_, demand]) => demand.amount > 0)
    .slice(0, 2)
    .map(([resourceId, demand]) => ({
      resourceId,
      amount: demand.amount,
      price: demand.price
    }));
  
  console.log('[Game.vue] Formatted demands:', formatted);
  return formatted;
}

// Computed property for exchanges (latest 4, newest first)
const latestExchanges = computed(() => {
  const exchanges = wsManager?.gameState?.state?.exchanges || []
  const sessionExchanges = exchanges.filter(e => 
    e.session_id === wsManager?.gameState?.state?.session?.id
  )
  // Get the last 4 exchanges (most recent) and reverse to show newest first
  return sessionExchanges.slice(-4).reverse()
})

// Helper function to get company name by ID
const getCompanyName = (companyId) => {
  const company = wsManager?.gameState?.getCompanyById(companyId)
  return company?.name || `Компания ${companyId}`
}

// Helper function to format exchange text (matching the existing format)
const formatExchangeText = (exchange) => {
  const companyName = getCompanyName(exchange.company_id)
  const resourceName = wsManager?.gameState?.getResourceName(exchange.sell_resource)
  
  if (exchange.offer_type === 'money') {
    return `${companyName} выставила на продажу ${resourceName}`
  } else if (exchange.offer_type === 'barter') {
    const barterResourceName = wsManager?.gameState?.getResourceName(exchange.barter_resource)
    return `${companyName} меняет ${resourceName} на ${barterResourceName}`
  }
  return `${companyName} выставила на продажу ${resourceName}`
}

// Computed property for contracts (latest 2, newest first)
const latestContracts = computed(() => {
  const contracts = wsManager?.gameState?.state?.contracts || []
  const sessionContracts = contracts.filter(c => 
    c.session_id === wsManager?.gameState?.state?.session?.id
  )
  // Show pending contracts first (not yet accepted)
  const pendingContracts = sessionContracts.filter(c => !c.accepted)
  // Get the last 2 contracts (most recent) and reverse to show newest first
  return pendingContracts.slice(-2).reverse()
})

// Helper function to format contract text (matching the existing format)
const formatContractText = (contract) => {
  const customerName = getCompanyName(contract.customer_company_id)
  const resourceName = wsManager?.gameState?.getResourceName(contract.resource)
  
  if (contract.supplier_company_id === 0) {
    // Free contract
    return `${customerName} создала свободный контракт на ${resourceName} на ${contract.duration_turns} ходов`
  } else {
    // Direct contract
    const supplierName = getCompanyName(contract.supplier_company_id)
    return `${customerName} создала контракт с ${supplierName} на ${resourceName} на ${contract.duration_turns} ходов`
  }
}

// Computed property for recent upgrades (latest 4)
const recentUpgrades = computed(() => {
  return wsManager?.gameState?.getRecentUpgrades(4) || []
})

// Helper function to format upgrade text
const formatUpgradeText = (upgrade) => {
  const companyName = upgrade.companyName || getCompanyName(upgrade.companyId)
  const improvementName = wsManager?.gameState?.getImprovementName(upgrade.improvementType)
  return `${companyName} улучшила ${improvementName} до уровня ${upgrade.level}`
}

// Event computed property
const currentEvent = computed(() => {
  const event = wsManager?.gameState?.getEvent() || null
  console.log('[Game.vue] Current event:', event)
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
        
        <div class="cities grid-item">
          <p class="title">ГОРОДА</p>
          <div class="content">
            <span>
              <!-- City 1 -->
              <template v-if="city1">
                {{ city1.name }}<br/>
                <template v-for="demand in formatCityDemands(city1)" :key="demand.resourceId">
                  &nbsp;&nbsp;• {{ wsManager.gameState.getResourceName(demand.resourceId) }}<br/>
                </template>
              </template>
              <template v-else>
                Город 1<br/>
              </template>
              <br/>
              
              <!-- City 2 -->
              <template v-if="city2">
                {{ city2.name }}<br/>
                <template v-for="demand in formatCityDemands(city2)" :key="demand.resourceId">
                  &nbsp;&nbsp;• {{ wsManager.gameState.getResourceName(demand.resourceId) }}<br/>
                </template>
              </template>
              <template v-else>
                Город 2<br/>
              </template>
            </span>

            <span>
              <!-- City 3 -->
              <template v-if="city3">
                {{ city3.name }}<br/>
                <template v-for="demand in formatCityDemands(city3)" :key="demand.resourceId">
                  &nbsp;&nbsp;• {{ wsManager.gameState.getResourceName(demand.resourceId) }}<br/>
                </template>
              </template>
              <template v-else>
                Город 3<br/>
              </template>
              <br/>
              
              <!-- City 4 -->
              <template v-if="city4">
                {{ city4.name }}<br/>
                <template v-for="demand in formatCityDemands(city4)" :key="demand.resourceId">
                  &nbsp;&nbsp;• {{ wsManager.gameState.getResourceName(demand.resourceId) }}<br/>
                </template>
              </template>
              <template v-else>
                Город 4<br/>
              </template>
            </span>
          </div>
        </div>

        <div class="stock grid-item">
          <p class="title">БИРЖА</p>
          <div class="content">
            <template v-if="latestExchanges.length > 0">
              <span v-for="exchange in latestExchanges" :key="exchange.id">
                {{ formatExchangeText(exchange) }}
              </span>
            </template>
            <template v-else>
              <span>Никаких операций за последнее время не происходило</span>
            </template>
          </div>
        </div>
        <div class="upgrades grid-item">
          <p class="title">УЛУЧШЕНИЯ</p>
          <div class="content">
            <template v-if="recentUpgrades.length > 0">
              <span v-for="upgrade in recentUpgrades" :key="upgrade.id">
                {{ formatUpgradeText(upgrade) }}
              </span>
            </template>
            <template v-else>
              <span>Никаких улучшений за последнее время не происходило</span>
            </template>
          </div>
        </div>
        <div class="contracts grid-item">
          <p class="title">КОНТРАКТЫ</p>
          <div class="content">
            <template v-if="latestContracts.length > 0">
              <span v-for="contract in latestContracts" :key="contract.id">
                {{ formatContractText(contract) }}
              </span>
            </template>
            <template v-else>
              <span>На данный момент контракты отсутсвуют</span>
            </template>
          </div>
        </div>

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
  display: grid;
  padding: 0; margin: 0;

  width: 100%;
  height: 100%;

  justify-items: stretch;
  align-items: center;
  align-content: space-between;
  justify-content: space-between;

  grid-template-columns: 47.5% 47.5%;
  grid-template-rows: 47.5% 47.5%;
}

.grid-item {
  width: 100%; height: 100%;
  /* background: #0f0; */
}

.content {
  font-size: 2rem;
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

.cities .content {
  padding: 5px 10px;

  width: 100%;
  display: flex;
  flex-direction: row;
  justify-content: space-between;
  text-align: left;
  line-height: 1.5;
  background: #3D8C00;
}

.stock .content, .upgrades .content, .contracts .content {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.stock span, .upgrades span, .contracts span {
  background: #3D8C00;
  padding: 5px 10px;
}

.events {
  font-size: 5rem;
  text-transform: uppercase;

  text-align: center;
  justify-content: center;

  padding: 40px 0;
  margin-top: 40px;

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
  margin: 0; padding: 0;
}
</style>
