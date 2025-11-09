<script setup>
import { ref, reactive, provide, watch, computed } from 'vue'

/**
 * Shared map state for singleton Map component.
 * Provided to child components for tile data access.
 */
const mapState = reactive({
  tiles: Array.from({ length: 49 }, (_, i) => ({
    id: `t-${i}`,
    label: String.fromCharCode(65 + (i % 7)) + (Math.floor(i / 7) + 1)
  }))
})
provide('mapState', mapState)

// Import all main page components
import Introduction from './components/Introduction.vue'
import Preparation from './components/Preparation.vue'
import Game from './components/Game.vue'
import Between from './components/Between.vue'
import Endgame from './components/Endgame.vue'
import About from './components/About.vue'
import AdminPanel from './components/AdminPanel.vue'

import { WebSocketManager } from './ws'

/**
 * Tracks the current view/page being displayed.
 * @type {import('vue').Ref<string>}
 */
const currentView = ref('Introduction')
/**
 * Controls visibility of the admin panel overlay.
 * @type {import('vue').Ref<boolean>}
 */
const showAdmin = ref(false)

/**
 * Controls the transition animation state
 * @type {import('vue').Ref<boolean>}
 */
const isTransitioning = ref(false)

/**
 * Changes the current view/page with transition animation.
 * @param {string} view - The view name to show.
 */
function handleShow(view) {
  isTransitioning.value = true
  
  // Wait for animation to reach middle (screen covered), then change view
  setTimeout(() => {
    currentView.value = view
  }, 400) // Half of the 800ms animation
  
  // Reset transitioning state after animation completes
  setTimeout(() => {
    isTransitioning.value = false
  }, 800)
}

/**
 * Map session stage to view component name
 * @param {string} stage - Session stage from API
 * @returns {string} - Component name
 */
function stageToView(stage) {
  switch (stage) {
    case 'FreeUserConnect':
    case 'CellSelect':
      return 'Preparation'
    case 'Game':
      return 'Game'
    case 'ChangeTurn':
      return 'Between'
    case 'End':
      return 'Endgame'
    default:
      return currentView.value // Keep current view if unknown stage
  }
}

/**
 * Shows the admin panel when mouse is in the top-left corner.
 * @param {MouseEvent} e
 */
function handleMouseMove(e) {
  if (e.clientX < 32 && e.clientY < 32) {
    showAdmin.value = true
  }
}

/**
 * Hides the admin panel overlay.
 */
function handleAdminLeave() {
  showAdmin.value = false
}

/**
 * Determine WebSocket URL based on current page location
 * @returns {string} WebSocket URL
 */
function getWebSocketUrl() {
  const hostname = window.location.hostname
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'

  // Use the same hostname as the web page with port 81
  return `${protocol}//${hostname}:81/ws/connect`
}

/**
 * WebSocketManager instance for global WebSocket communication.
 * Provided to child components and exposed globally.
 * @type {WebSocketManager}
 */
let wsManager = null
const wsUrl = getWebSocketUrl()
console.log(`🔌 Connecting to WebSocket: ${wsUrl}`)
wsManager = new WebSocketManager(wsUrl)
wsManager.connect()
globalThis.wsManager = wsManager

/**
 * Watch for session stage changes and automatically navigate to appropriate view
 * Only triggers if user is actually in a session (session.id exists)
 */
watch(
  () => wsManager.gameState?.state?.session?.stage,
  (newStage, oldStage) => {
    // Only auto-navigate if we have a valid session ID
    const sessionId = wsManager.gameState?.state?.session?.id
    if (newStage && newStage !== oldStage && sessionId) {
      const targetView = stageToView(newStage)
      if (targetView !== currentView.value && targetView !== 'Introduction') {
        console.log(`🎮 Stage changed: ${oldStage} → ${newStage}, navigating to ${targetView}`)
        handleShow(targetView)
      }
    }
  },
  { immediate: false }
)

/**
 * Globally available function to refresh the map from session data.
 */
globalThis.refreshMap = () => {
  if (wsManager && wsManager.map) {
    wsManager.refreshMap()
    console.log('Global map refresh called')
  } else {
    console.error('No map data available for global refresh')
  }
}

// ==================== DEBUG FUNCTIONS ====================
// These functions are available in DevTools console for debugging

/**
 * Get the current game state for debugging
 * Usage in console: getGameState()
 */
globalThis.getGameState = () => {
  if (!wsManager || !wsManager.gameState) {
    console.error('❌ GameState not available')
    return null
  }
  const state = wsManager.gameState.toJSON()
  console.log('🎮 Current Game State:')
  console.table({
    'Session ID': state.session.id || 'None',
    'Stage': state.session.stage || 'None',
    'Step': `${state.session.step}/${state.session.max_steps}`,
    'Connected': state.connected ? '✅' : '❌',
    'Companies': state.companies.length,
    'Users': state.users.length,
    'Factories': state.factories.length,
    'Exchanges': state.exchanges.length,
    'Map Loaded': state.map.loaded ? '✅' : '❌'
  })
  return state
}

/**
 * Helper function to download a file
 */
function downloadFile(content, fileName, contentType) {
    var a = document.createElement("a");
    var file = new Blob([content], {type: contentType});
    a.href = URL.createObjectURL(file);
    a.download = fileName;
    a.click();
}

/**
 * Get detailed game state as JSON
 * Usage: getGameStateJSON()
 */
globalThis.saveGameState = () => {
  if (!wsManager || !wsManager.gameState) {
    console.error('❌ GameState not available')
    return null
  }
  let timestamp = new Date();
  const formatedTime = `${timestamp.getHours()}.${timestamp.getMinutes()}.${timestamp.getSeconds()}`
  downloadFile(JSON.stringify(wsManager.gameState.toJSON()), formatedTime + "_gameState.json", "text/plain")
}

/**
 * Log current game state to console
 * Usage: logGameState()
 */
globalThis.logGameState = () => {
  if (!wsManager || !wsManager.gameState) {
    console.error('❌ GameState not available')
    return
  }
  wsManager.gameState.logState()
}

/**
 * Get all companies
 * Usage: getCompanies()
 */
globalThis.getCompanies = () => {
  if (!wsManager) return []
  console.table(wsManager.gameState.state.companies)
  return wsManager.gameState.state.companies
}

/**
 * Get all users
 * Usage: getUsers()
 */
globalThis.getUsers = () => {
  if (!wsManager) return []
  console.table(wsManager.gameState.state.users)
  return wsManager.gameState.state.users
}

/**
 * Get session info
 * Usage: getSession()
 */
globalThis.getSession = () => {
  if (!wsManager) return null
  const session = wsManager.gameState.state.session
  console.log('📍 Session Info:', session)
  return session
}

/**
 * Get map data
 * Usage: getMap()
 */
globalThis.getMap = () => {
  if (!wsManager) return null
  const map = wsManager.gameState.getMapData()
  console.log('🗺️ Map Data:', {
    size: map.size,
    cellCount: map.cells.length,
    loaded: map.loaded,
    pattern: map.pattern
  })
  return map
}

/**
 * Get exchange offers
 * Usage: getExchanges()
 */
globalThis.getExchanges = () => {
  if (!wsManager) return []
  console.table(wsManager.gameState.state.exchanges)
  return wsManager.gameState.state.exchanges
}

/**
 * Get factories
 * Usage: getFactories()
 */
globalThis.getFactories = () => {
  if (!wsManager) return []
  console.table(wsManager.gameState.state.factories)
  return wsManager.gameState.state.factories
}

/**
 * Get winners (if game ended)
 * Usage: getWinners()
 */
globalThis.getWinners = () => {
  if (!wsManager) return null
  const winners = wsManager.gameState.getWinners()
  console.log('🏆 Winners:', winners)
  return winners
}

/**
 * Get current user info
 * Usage: getCurrentUser()
 */
globalThis.getCurrentUser = () => {
  if (!wsManager) return null
  const user = wsManager.gameState.state.currentUser
  console.log('👤 Current User:', user)
  return user
}

/**
 * Refresh all game data
 * Usage: refreshGameData()
 */
globalThis.refreshGameData = () => {
  if (!wsManager) {
    console.error('❌ WebSocket manager not available')
    return
  }
  console.log('🔄 Refreshing all game data...')
  wsManager.fetchAllGameData()
}

/**
 * Get stored session ID
 * Usage: getStoredSession()
 */
globalThis.getStoredSession = () => {
  if (!wsManager) return null
  const storedId = wsManager.getStoredSessionId()
  console.log('💾 Stored session ID:', storedId)
  return storedId
}

/**
 * Clear stored session
 * Usage: clearStoredSession()
 */
globalThis.clearStoredSession = () => {
  if (!wsManager) return
  wsManager.clearStoredSession()
  console.log('🗑️ Stored session cleared')
}

/**
 * Manually trigger reconnection
 * Usage: reconnect()
 */
globalThis.reconnect = () => {
  if (!wsManager) return
  console.log('🔄 Manually triggering reconnection...')
  wsManager.connect()
}

/**
 * Get current view name
 * Usage: getCurrentView()
 */
globalThis.getCurrentView = () => {
  console.log('👁️ Current view:', currentView.value)
  return currentView.value
}

/**
 * Switch to a specific view
 * Usage: showView('About')
 */
globalThis.showView = (viewName) => {
  console.log(`🎬 Switching to view: ${viewName}`)
  handleShow(viewName)
}

/**
 * Show available debug commands
 * Usage: debugHelp()
 */
globalThis.debugHelp = () => {
  console.log(`
🎮 Available Debug Commands:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 State Access:
  getGameState()      - Get formatted game state overview
  getGameStateJSON()  - Get raw game state as JSON
  logGameState()      - Log detailed state to console

🎯 Specific Data:
  getSession()        - Get session information
  getCompanies()      - Get all companies (table format)
  getUsers()          - Get all users (table format)
  getMap()            - Get map data
  getExchanges()      - Get exchange offers
  getFactories()      - Get factories
  getWinners()        - Get game winners (if ended)
  getCurrentUser()    - Get current user info

🔧 Actions:
  refreshGameData()   - Refresh all game data from server
  refreshMap()        - Refresh map display
  getStoredSession()  - Get stored session ID from localStorage
  clearStoredSession()- Clear stored session ID
  reconnect()         - Manually trigger WebSocket reconnection

🎬 View Control:
  getCurrentView()    - Get current view name
  showView(name)      - Switch to a specific view (Introduction, Preparation, Game, Between, Endgame)

💡 Direct Access:
  wsManager           - WebSocketManager instance
  wsManager.gameState - GameState instance
  wsManager.state     - Reactive state object

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  `)
}

// Log available debug commands on load
console.log('🎮 Game loaded! Type debugHelp() for available commands.')

provide('wsManager', wsManager)
</script>

<template>
  <!--
    Root application container.
    Handles mouse movement for admin panel reveal and hosts all main page components.
  -->
  <div @mousemove="handleMouseMove" style="position: relative; min-height: 100vh; overflow: hidden;">
    <!-- Admin panel overlay, shown when mouse is in top-left corner -->
    <AdminPanel v-if="showAdmin" @show="handleShow" @mouseleave="handleAdminLeave"
      style="position: fixed; left: 0; top: 0; width: 320px; z-index: 1000;" />


      <component :is="currentView === 'Introduction' ? Introduction :
          currentView === 'Preparation' ? Preparation :
            currentView === 'Between' ? Between :
              currentView === 'Endgame' ? Endgame :
                currentView === 'About' ? About :
                Game
        " :key="currentView" @navigateTo="handleShow" />

    <!-- Black transition overlay -->
    <div class="transition-overlay" :class="{ 'transitioning': isTransitioning }"></div>
  </div>
</template>

<style scoped>
/*
  Black rectangle sliding transition overlay.
*/
.transition-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background-color: #1E1E1E;
  z-index: 999;
  transform: translateY(-100%);
  pointer-events: none;
}

/*
  Page transition styles with sliding black rectangle effect.
  The overlay slides down from top, covers the screen, then slides down to bottom.
*/
.page-leave-active {
  transition-delay: 0s;
}

.page-enter-active {
  transition-delay: 0.4s;
}

/* Animation for the black overlay */
@keyframes slideDown {
  0% {
    transform: translateY(-100%);
  }
  50% {
    transform: translateY(0);
  }
  100% {
    transform: translateY(100%);
  }
}

.transitioning {
  animation: slideDown 0.8s ease-in-out;
}
</style>
