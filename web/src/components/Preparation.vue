<script setup>
import './mapScripts.js'
import Map from './Map.vue'
import { onMounted, onUnmounted, ref, inject, reactive, watch, computed } from 'vue'

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
 * Reactive state for the list of companies displayed in the columns.
 */
const companiesState = reactive({ list: [] })

const prepState = ref(0)
let color_scheme = [
  ["#12488E", "#C67D1D"],
  ["#7EBE25", "#0C9273"],
]

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
  if (state == 0) {
    document.documentElement.style.setProperty("--color-1", color_scheme[0][0])
    document.documentElement.style.setProperty("--color-2", color_scheme[0][1])
  } else if (state == 1) {
    document.documentElement.style.setProperty("--color-1", color_scheme[1][0])
    document.documentElement.style.setProperty("--color-2", color_scheme[1][1])
  }
}

/**
 * Computed array to track visibility of each item reactively
 * @returns {Array<boolean>} - Array of visibility states for each company
 */
const itemVisibility = computed(() => {
  // If wsManager or gameState is not ready, return all false
  if (!wsManager || !wsManager.gameState) return Array(10).fill(false);
  
  // Access the reactive state to ensure reactivity
  const companies = wsManager.gameState.state.companies;
  const users = wsManager.gameState.state.users;
  
  return Array.from({ length: 10 }, (_, index) => {
    const companyName = wsManager.gameState.getCompanyNameByIndex(index) || '';
    const usernames = wsManager.gameState.stringUsernamesByCompanyIndex(index) || '';
    const hasContent = companyName.trim() !== '' || usernames.trim() !== '';
    // console.log(`Item ${index}: company="${companyName}", users="${usernames}", visible=${hasContent}`);
    return hasContent;
  });
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

  if (wsManager) {
    window.addEventListener('companies-updated', handleCompaniesUpdated)
    wsManager.fetchAllGameData();
    wsManager.startPolling(5000)
  }

  window.preparationState = prepState;

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
      <div class="grid">
        <div v-for="n in 10" :key="n" class="item" v-show="itemVisibility[n - 1]" :data-visible="itemVisibility[n - 1]">
          <p class="title">{{ wsManager.gameState.getCompanyNameByIndex(n - 1) }}</p>  
          <p class="users">{{ wsManager.gameState.stringUsernamesByCompanyIndex(n - 1) }}</p>
          <!-- <p style="font-size: 10px; color: red;">Debug: visible={{ itemVisibility[n - 1] }}</p> -->
        </div>
      </div>
    </div>
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
