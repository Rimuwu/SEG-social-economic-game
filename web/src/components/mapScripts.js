/**
 * Map tile and grid configuration for the game map.
 * Provides tile definitions, types, styles, and tile mutation logic.
 */
import { ref, onMounted, nextTick } from 'vue'
/**
 * Number of rows in the map grid.
 * @type {number}
 */
const rows = 7
/**
 * Number of columns in the map grid.
 * @type {number}
 */
const cols = 7
/**
 * Total number of tiles in the grid.
 * @type {number}
 */
const total = rows * cols
/**
 * Letters used for tile labeling.
 * @type {string}
 */
const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
/**
 * Array of tile objects for the grid.
 * @type {Array<{id: string, label: string}>}
 */
const tiles = Array.from({ length: total }, (_, i) => ({
  id: `t-${i}`,
  label: letters[Math.floor(i / cols)] + ((i % cols) + 1),
}))
/**
 * References to tile DOM elements.
 * @type {import('vue').Ref<Array<HTMLElement>>}
 */
const tileRefs = ref([])
/**
 * Enum for tile types.
 * @type {Object}
 */
const TileTypes = {
  MOUNTAINS: 0,
  WATER: 1,
  FOREST: 2,
  FIELD: 3,
  CITY: 4,
  BANK: 5,
  COMPANY: 6,
}
/**
 * Mapping of tile types to their color styles.
 * @type {Object}
 */
const tileStyles = {
  [TileTypes.MOUNTAINS]: { color: "#4E4E4E", fontColor: "#ff"},
  [TileTypes.WATER]: { color: "#00AAFF", fontColor: "#000"},
  [TileTypes.FOREST]: { color: "#3E8B03", fontColor: "#fff"},
  [TileTypes.FIELD]: { color: "#81D905", fontColor: "#000"},
  [TileTypes.CITY]: { color: "#FFBB00", fontColor: "#000"},
  [TileTypes.BANK]: { color: "#FF4400", fontColor: "#000"},
  [TileTypes.COMPANY]: { color: "#A100FF", fontColor: "#fff"},
}
/**
 * Sets the tile's color and label in the grid.
 * @param {number} row - Row index (0-based)
 * @param {number} col - Column index (0-based)
 * @param {number} tileType - Tile type enum value
 * @param {string} text - Text label for the tile
 * @param {string} font_size - Optional font size for the label
 */
function setTile(row, col, tileType, text) {
  if (row < 0 || row >= rows || col < 0 || col >= cols) return
  const idx = row * cols + col
  const tile = tileRefs.value[idx]
  if (!tile) return
  if (tileType !== undefined && tileType !== null) {
    tile.style.backgroundColor = tileStyles[tileType].color
    tile.style.color = tileStyles[tileType].fontColor
  }
  
  // Remove any previous special classes
  tile.classList.remove('company-tile')
  
  // Handle icon display for CITY and BANK tiles
  if (tileType === TileTypes.CITY || tileType === TileTypes.BANK) {
    // Clear existing content
    tile.innerHTML = ''
    
    // Create image element
    const img = document.createElement('img')
    img.src = tileType === TileTypes.CITY ? '/city.svg' : '/bank.svg'
    img.alt = tileType === TileTypes.CITY ? 'City' : 'Bank'
    img.style.width = '60%'
    img.style.height = '60%'
    img.style.objectFit = 'contain'
    img.style.filter = 'brightness(0)' // Make icon black/dark
    
    tile.appendChild(img)
  } else if (text !== undefined) {
    // For other tiles with custom text (like companies)
    tile.textContent = text
    
    // If this is a company tile, add the company-tile class for special styling
    if (tileType === TileTypes.COMPANY) {
      tile.classList.add('company-tile')
    }
  }
  // Otherwise, keep the default coordinate label
}
export { tiles, tileRefs, TileTypes, tileStyles, setTile, rows, cols }