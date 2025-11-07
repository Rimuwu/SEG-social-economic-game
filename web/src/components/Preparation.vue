<script setup>
import './mapScripts.js'
import Map from './Map.vue'
import LeaveButton from './LeaveButton.vue'
import { onMounted, onUnmounted, ref, inject, reactive, watch, computed } from 'vue'

const emit = defineEmits(['navigateTo'])

/**
 * Ref to the root page container for animation and event handling.
 * @type {import('vue').Ref<HTMLElement>}
 */
const pageRef = ref(null)
/**
 * Injected WebSocketManager instance for session and company data.
 * @type {WebSocketManager}
 */
const wsManager = inject('wsManager', null)

/**
 * Handle leave button click
 */
const handleLeave = () => {
  emit('navigateTo', 'Introduction')
}

/**
 * Reactive state for the list of companies displayed in the columns.
 */
const companiesState = reactive({ list: [] })

const prepState = ref(0)
let color_scheme = [
  ["#12488E", "#C67D1D"],
  ["#7EBE25", "#0C9273"],
]

/**
 * Pagination state for companies slider
 */
const currentPage = ref(0)
const itemsPerPage = 10
let autoSlideInterval = null

/**
 * Handles updates to the companies list from polling events.
 * @param {CustomEvent} e
 */
function handleCompaniesUpdated(e) {
  if (e && e.detail && Array.isArray(e.detail.companies)) {
    companiesState.list = e.detail.companies
  }
}

function stateChange() {
  console.log("stateChange called, new state: " + prepState.value)
  if (prepState.value == 0) {
    document.documentElement.style.setProperty("--color-1", color_scheme[0][0])
    document.documentElement.style.setProperty("--color-2", color_scheme[0][1])
  } else if (prepState.value == 1) {
    document.documentElement.style.setProperty("--color-1", color_scheme[1][0])
    document.documentElement.style.setProperty("--color-2", color_scheme[1][1])
  }
}

/**
 * Navigate to previous page
 */
const goToPreviousPage = () => {
  if (currentPage.value > 0) {
    currentPage.value--;
  } else {
    currentPage.value = totalPages.value - 1; // Go to last page
  }
  resetAutoSlide();
};

/**
 * Navigate to next page
 */
const goToNextPage = () => {
  if (currentPage.value < totalPages.value - 1) {
    currentPage.value++;
  } else {
    currentPage.value = 0; // Go to first page
  }
  resetAutoSlide();
};

/**
 * Start automatic sliding every 10 seconds
 */
const startAutoSlide = () => {
  if (shouldShowPagination.value) {
    autoSlideInterval = setInterval(() => {
      goToNextPage();
    }, 10000);
  }
};

/**
 * Stop and restart automatic sliding
 */
const resetAutoSlide = () => {
  if (autoSlideInterval) {
    clearInterval(autoSlideInterval);
  }
  startAutoSlide();
};

/**
 * Total number of companies with content
 */
const totalCompanies = computed(() => {
  if (!wsManager || !wsManager.gameState) return 0;
  
  let count = 0;
  for (let i = 0; i < 50; i++) { // Check up to 50 companies
    const companyName = wsManager.gameState.getCompanyNameByIndex(i) || '';
    const usernames = wsManager.gameState.stringUsernamesByCompanyIndex(i) || '';
    if (companyName.trim() !== '' || usernames.trim() !== '') {
      count = i + 1;
    }
  }
  return count;
});

/**
 * Total number of pages needed for pagination
 */
const totalPages = computed(() => {
  return Math.ceil(totalCompanies.value / itemsPerPage);
});

/**
 * Companies to display on current page
 */
const currentPageCompanies = computed(() => {
  const startIndex = currentPage.value * itemsPerPage;
  const companies = [];
  
  for (let i = 0; i < itemsPerPage; i++) {
    const globalIndex = startIndex + i;
    if (globalIndex < totalCompanies.value) {
      const companyName = wsManager?.gameState?.getCompanyNameByIndex(globalIndex) || '';
      const usernames = wsManager?.gameState?.stringUsernamesByCompanyIndex(globalIndex) || '';
      companies.push({
        index: globalIndex,
        name: companyName,
        users: usernames,
        hasContent: companyName.trim() !== '' || usernames.trim() !== ''
      });
    }
  }
  
  return companies;
});

/**
 * Should show pagination controls
 */
const shouldShowPagination = computed(() => {
  return totalPages.value > 1;
});

/**
 * Lifecycle hook: runs on component mount.
 * Sets up entrance animation, exit event listener, and starts company polling.
 */
onMounted(() => {
  // Watch for changes in prepState and call stateChange
  watch(prepState, () => {
    stateChange()
  })

  // Watch for changes in total companies to restart auto slide
  watch(totalPages, () => {
    resetAutoSlide()
  })

  if (wsManager) {
    window.addEventListener('companies-updated', handleCompaniesUpdated)
    wsManager.fetchAllGameData();
    wsManager.startPolling(5000)
  }

  window.preparationState = prepState;
  
  // Start auto slide when component mounts
  startAutoSlide();
})

/**
 * Lifecycle hook: runs on component unmount.
 * Cleans up event listeners and stops company polling.
 */
onUnmounted(() => {
  if (wsManager) {
    wsManager.stopPolling()
    window.removeEventListener('companies-updated', handleCompaniesUpdated)
  }
  
  // Clear auto slide interval
  if (autoSlideInterval) {
    clearInterval(autoSlideInterval);
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
        <span>@sneg_gamebot</span>
        <span>/</span>
        <span>{{ wsManager.session_id }}</span>
      </div>
      <Map class="map" />
    </div>
    <div class="right">
      <div class="grid-container">
        <div class="grid">
          <div 
            v-for="company in currentPageCompanies" 
            :key="`${currentPage}-${company.index}`" 
            class="item" 
            v-show="company.hasContent"
          >
            <p class="title">{{ company.name }}</p>  
            <p class="users">{{ company.users }}</p>
          </div>
        </div>
        
        <!-- Pagination controls -->
        <div class="pagination" v-if="shouldShowPagination">
          <button class="nav-arrow left-arrow" @click="goToPreviousPage" :disabled="totalPages <= 1">
            ←
          </button>
          
          <div class="page-indicators">
            <span 
              v-for="page in totalPages" 
              :key="page" 
              class="page-dot" 
              :class="{ active: page - 1 === currentPage }"
              @click="currentPage = page - 1; resetAutoSlide();"
            ></span>
          </div>
          
          <button class="nav-arrow right-arrow" @click="goToNextPage" :disabled="totalPages <= 1">
            →
          </button>
        </div>
      </div>
    </div>
    
    <!-- Leave Button -->
    <LeaveButton @leave="handleLeave" />
  </div>
</template>

<style scoped>
* {
  --color-1: #12488E;
  --color-2: #C67D1D;
}

#page {
  display: flex;
  height: 100vh;
  background-color: var(--color-2);
  font-family: "Inter", sans-serif;
  padding: 0;
  margin: 0;
}

.left,
.right {
  width: 50%;
  padding: 40px;
  transition: background-color 1s ease-in-out;
}


.left {
  background-color: var(--color-1);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.right {
  background-color: var(--color-2);
  color: black;
  padding: 90px 50px;
}

.grid-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
}

.grid {
  flex: 1;
  display: grid;
  padding: 0; 
  margin: 0;
  width: 100%;
  justify-items: stretch;
  align-items: center;
  align-content: space-between;
  justify-content: space-between;
  grid-template-columns: 47.5% 47.5%;
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px 0;
  gap: 20px;
}

.nav-arrow {
  background: white;
  border: 2px solid var(--color-1);
  border-radius: 50%;
  width: 50px;
  height: 50px;
  font-size: 24px;
  font-weight: bold;
  color: var(--color-1);
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.nav-arrow:hover:not(:disabled) {
  background: var(--color-1);
  color: white;
  transform: scale(1.1);
}

.nav-arrow:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.page-indicators {
  display: flex;
  gap: 10px;
}

.page-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  transition: all 0.3s ease;
}

.page-dot.active {
  background: white;
  transform: scale(1.3);
}

.page-dot:hover {
  background: rgba(255, 255, 255, 0.8);
}

.item {
  background: white;
  padding: 10px;

  font-family: "Ubuntu Mono", monospace;

  text-align: center;
}

.title {
  font-size: 2.5rem;
  margin: 0;
  text-transform: uppercase;
  margin-bottom: 20px;
}

.users {
  text-transform: lowercase;
  font-size: 2rem;
  margin: 0;
  opacity: 0.75;
}

.footer {
  width: 90%;

  background: var(--color-2);
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;

  font-family: "Ubuntu Mono", monospace;
  font-weight: normal;
  font-size: 4rem;

  color: white;
}

.footer span {
  margin: 25px;
}

.map {
  width: 90%;
  margin: 0; padding: 0;
}
</style>
