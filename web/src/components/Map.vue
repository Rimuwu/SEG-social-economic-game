<template>
    <div class="map-wrapper">
        <div id="map" ref="mapRoot">
            <div v-for="(tile, idx) in tiles" :key="tile.id" class="tile" :data-index="idx" ref="tileRefs">
                {{ tile.label }}
            </div>
        </div>
    </div>
</template>

<script setup>
import { tiles, tileRefs, TileTypes, tileStyles, setTile, rows, cols } from './mapScripts.js'
import { onMounted, onUnmounted, nextTick, inject, watch, ref } from 'vue'

// Get WebSocket manager from parent
const wsManager = inject('wsManager', null)

onMounted(async () => {
    // await nextTick()
    // Make functions globally available
    window.setTile = setTile
    window.TileTypes = TileTypes

    // Load map from WebSocket data if available
    if (wsManager && wsManager.map) {
        wsManager.loadMapToDOM()
    } else {
        // Fallback to default static setup if no session data
        setTile(1, 1, TileTypes.CITY, "ГОРОД А")
        setTile(5, 1, TileTypes.CITY, "ГОРОД В")
        setTile(1, 5, TileTypes.CITY, "ГОРОД Б")
        setTile(5, 5, TileTypes.CITY, "ГОРОД Г")
        setTile(3, 3, TileTypes.BANK, "ЦЕНТР. БАНК")
        
        console.log('Map loaded with default static data')
    }
})

onUnmounted(() => {
    // Cleanup global functions
    if (window.setTile) delete window.setTile
    if (window.TileTypes) delete window.TileTypes
})

// Watch for session changes and reload map
if (wsManager) {
    watch(() => wsManager.session_id, (newSessionId) => {
        if (newSessionId && wsManager.map) {
            wsManager.loadMapToDOM()
        }
    })
}
</script>

<style scoped>
.map-wrapper {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;

    overflow: hidden;
}

#map {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    grid-template-rows: repeat(7, 1fr);
    background: white;
    /* gap: 4px; */
    padding: 15px;

    box-sizing: border-box;
    overflow: hidden;
    
    aspect-ratio: 1/1;
    width: 80vh;
    max-width: 80vw;
    height: 80vh;
    max-height: 80vw;

    gap: 0;
}

.tile {
    /* Force fixed dimensions */
    width: 100%;
    height: 100%;
    min-width: 0;
    min-height: 0;
    aspect-ratio: 1/1;

    box-shadow: inset 0 0 0 2px rgba(1,1,1,0.5);
    
    display: flex;
    align-items: center;
    justify-content: center;
    background: #f3f4f6;
    user-select: none;
    cursor: pointer;
    font-weight: 600;
    margin: 0;
    padding: 4px;
    box-sizing: border-box;

    /* Responsive font size based on container */
    font-size: clamp(0.6rem, 1.2vw, 1.2rem);
    line-height: 1.1;
    
    /* Text handling for overflow */
    word-wrap: break-word;
    word-break: break-word;
    hyphens: auto;
    text-align: center;
    overflow: hidden;
    text-overflow: ellipsis;
    
    /* Smooth transitions */
    transition: background-color 1s ease, font-size 0.3s ease;

    font-size: 3rem;
    font-family: "Ubuntu Mono", monospace;
}

/* Company tiles need smaller text and ellipsis for overflow */
.tile.company-tile {
    font-size: 2.5rem;
    white-space: wrap;
    overflow: hidden;
    text-overflow: ellipsis;
    padding: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    line-height: normal;
}
</style>
