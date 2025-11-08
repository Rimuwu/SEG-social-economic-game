<script setup>
import Map from './Map.vue'
import LeaveButton from './LeaveButton.vue'
import Products from './Products.vue'
import { onMounted, ref, inject, computed } from 'vue'

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

// Computed properties for cities - get first 4 cities from the array
const allCities = computed(() => {
  const cities = wsManager?.gameState?.state?.cities || []
  console.log('[Game.vue] All cities:', cities)
  return cities
})

const city1 = computed(() => {
  const cities = allCities.value
  const city = cities.length > 0 ? cities[0] : null
  console.log('[Game.vue] City 1 (first city):', city)
  return city
})

const city2 = computed(() => {
  const cities = allCities.value
  const city = cities.length > 1 ? cities[1] : null
  console.log('[Game.vue] City 2 (second city):', city)
  return city
})

const city3 = computed(() => {
  const cities = allCities.value
  const city = cities.length > 2 ? cities[2] : null
  console.log('[Game.vue] City 3 (third city):', city)
  return city
})

const city4 = computed(() => {
  const cities = allCities.value
  const city = cities.length > 3 ? cities[3] : null
  console.log('[Game.vue] City 4 (fourth city):', city)
  return city
})

// Helper function to format city demands
const formatCityDemands = (city) => {
  console.log('[Game.vue] formatCityDemands called for city:', city);
  
  if (!city || !city.demands) {
    console.log('[Game.vue] No city or no demands:', { city: !!city, demands: !!city?.demands });
    return []
  }
  
  console.log('[Game.vue] City demands object:', city.demands);
  
  // Show all demands for debugging (remove amount > 0 filter temporarily)
  const allDemands = Object.entries(city.demands)
    .map(([resourceId, demand]) => ({
      resourceId,
      amount: demand.amount || 0,
      price: demand.price || 0
    }));
  
  console.log('[Game.vue] All demands:', allDemands);
  
  // Filter demands with amount > 0 and get only 2
  const formatted = allDemands
    .filter(demand => demand.amount > 0)
    .slice(0, 2);
  
  console.log('[Game.vue] Filtered demands (amount > 0):', formatted);
  return formatted;
}

// Computed property for exchanges (latest 3 activities, newest first)
const latestExchanges = computed(() => {
  // Use the recent activity list instead of the offers list
  return wsManager?.gameState?.getRecentExchangeActivity(3) || []
})

// Helper function to get company name by ID
const getCompanyName = (companyId) => {
  const company = wsManager?.gameState?.getCompanyById(companyId)
  return company?.name || `Компания ${companyId}`
}

// Helper function to format exchange text based on activity type
const formatExchangeText = (activity) => {
  if (activity.type === 'offer_created') {
    const companyName = activity.companyName || getCompanyName(activity.companyId)
    const resourceName = wsManager?.gameState?.getResourceName(activity.resource)
    
    if (activity.offerType === 'money') {
      return `Компания ${companyName} выставила на продажу продукт ${resourceName}`
    } else if (activity.offerType === 'barter') {
      const barterResourceName = wsManager?.gameState?.getResourceName(activity.barterResource)
      return `Компания ${companyName} предлагает бартер товара ${resourceName} на ${barterResourceName}`
    }
    return `Компания ${companyName} выставила на продажу продукт ${resourceName}`
  } else if (activity.type === 'trade_completed') {
    const sellerName = activity.companyName || getCompanyName(activity.companyId)
    const buyerName = activity.buyerName || getCompanyName(activity.buyerId)
    const resourceName = wsManager?.gameState?.getResourceName(activity.resource)
    
    if (activity.offerType === 'money') {
      return `Компания ${buyerName} выкупила продукт ${resourceName} у компании ${sellerName}`
    } else if (activity.offerType === 'barter') {
      const barterResourceName = wsManager?.gameState?.getResourceName(activity.barterResource)
      return `Компания ${buyerName} обменяла ${barterResourceName} на ${resourceName} с компанией ${sellerName}`
    }
    return `Компания ${buyerName} купила продукт ${resourceName} у компании ${sellerName}`
  }
  return ''
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
  // Access the reactive state directly for proper reactivity
  const event = wsManager?.gameState?.state?.event
  console.log('[Game.vue] Current event:', event)
  // Return event only if it has an ID (meaning it exists)
  return event && event.id ? event : null
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
  console.log('[Game.vue] Component mounted')
  console.log('[Game.vue] wsManager:', !!wsManager)
  console.log('[Game.vue] gameState:', !!wsManager?.gameState)
  console.log('[Game.vue] cities array:', wsManager?.gameState?.state?.cities)
  
  // Watch for cities changes
  if (wsManager?.gameState) {
    console.log('[Game.vue] Setting up cities watcher')
    const stopWatcher = wsManager.gameState.state.cities && typeof wsManager.gameState.state.cities === 'object' 
      ? () => {} // Already reactive
      : () => {}
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
        
        <div class="cities grid-item">
          <p class="title">ГОРОДА ({{ allCities.length }})</p>
          <div class="content">
            <span>
              <!-- City 1 -->
              <template v-if="city1">
                {{ city1.name }} (↖)<br/>
                <template v-for="demand in formatCityDemands(city1)" :key="demand.resourceId">
                  &nbsp;&nbsp;• {{ wsManager.gameState.getResourceName(demand.resourceId) }}<br/>
                  &nbsp;&nbsp;&nbsp;&nbsp;[{{ demand.amount }} шт.]<br/>
                </template>
                <br/>
              </template>
              
              <!-- City 2 -->
              <template v-if="city2">
                {{ city2.name }} (↙)<br/>
                <template v-for="demand in formatCityDemands(city2)" :key="demand.resourceId">
                  &nbsp;&nbsp;• {{ wsManager.gameState.getResourceName(demand.resourceId) }}<br/>
                  &nbsp;&nbsp;&nbsp;&nbsp;[{{ demand.amount }} шт.]<br/>
                </template>
              </template>
            </span>

            <span>
              <!-- City 3 -->
              <template v-if="city3">
                {{ city3.name }} (↗)<br/>
                <template v-for="demand in formatCityDemands(city3)" :key="demand.resourceId">
                  &nbsp;&nbsp;• {{ wsManager.gameState.getResourceName(demand.resourceId) }}<br/>
                  &nbsp;&nbsp;&nbsp;&nbsp;[{{ demand.amount }} шт.]<br/>
                </template>
                <br/>
              </template>
              
              <!-- City 4 -->
              <template v-if="city4">
                {{ city4.name }} (↘)<br/>
                <template v-for="demand in formatCityDemands(city4)" :key="demand.resourceId">
                  &nbsp;&nbsp;• {{ wsManager.gameState.getResourceName(demand.resourceId) }}<br/>
                  &nbsp;&nbsp;&nbsp;&nbsp;[{{ demand.amount }} шт.]<br/>
                </template>
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
        <div class="products grid-item">
          <Products title="ПРОДУКТЫ" />
        </div>

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
  background: #3D8C00 ;
}

.stock .content, .upgrades .content {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.stock span, .upgrades span {
  background: #3D8C00 ;
  padding: 5px 10px;
}

.products {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.events {
  font-size: 5rem;
  text-transform: uppercase;

  text-align: center;
  justify-content: center;

  padding: 40px 0;
  margin-top: 40px;

  background-color: #3D8C00 ;

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
  margin: 0; padding: 0;
}
</style>
