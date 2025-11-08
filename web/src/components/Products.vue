<script setup>
import { ref, inject, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  title: {
    type: String,
    default: 'ПРОДУКТЫ'
  }
})

const wsManager = inject('wsManager', null)

// Используем прямые ссылки на GameState для сохранения данных между переходами этапов
const priceChanges = computed(() => {
  if (!wsManager?.gameState?.state?.priceChanges) {
    // Инициализируем, если еще не существует
    if (wsManager?.gameState?.state) {
      wsManager.gameState.state.priceChanges = []
    }
  }
  return wsManager?.gameState?.state?.priceChanges || []
})

const currentPrices = computed(() => {
  if (!wsManager?.gameState?.state?.currentPrices) {
    // Инициализируем, если еще не существует
    if (wsManager?.gameState?.state) {
      wsManager.gameState.state.currentPrices = {}
    }
  }
  return wsManager?.gameState?.state?.currentPrices || {}
})

// Инициализируем текущие цены
const initializePrices = async () => {
  if (!wsManager || !wsManager.gameState?.state?.session?.id) return
  
  console.log('[Products.vue] Initializing current prices')
  
  wsManager.get_all_item_prices((response) => {
    let pricesData
    if (response && response.success && response.data) {
      pricesData = response.data
    } else if (response && typeof response === 'object' && !response.success) {
      pricesData = response
    }
    
    if (pricesData && typeof pricesData === 'object') {
      // Сохраняем текущие цены без добавления в список изменений
      const prices = currentPrices.value
      Object.entries(pricesData).forEach(([itemId, priceData]) => {
        const price = typeof priceData === 'object' ? (priceData.current_price || priceData.price || 0) : priceData
        prices[itemId] = price
      })
      
      console.log('[Products.vue] Initial prices loaded:', Object.keys(prices).length)
    }
  })
}

// Обработчик обновления цены одного товара
const handlePriceUpdate = (data) => {
  const { item_id, price, session_id } = data
  
  // Проверяем, что это обновление для нашей сессии
  if (session_id !== wsManager?.gameState?.state?.session?.id) return

  const prices = currentPrices.value
  const changes = priceChanges.value
  const oldPrice = prices[item_id]
  
  // Проверяем, что цена действительно изменилась
  if (oldPrice !== undefined && oldPrice !== price) {
    const productName = wsManager.gameState?.getResourceName ? wsManager.gameState.getResourceName(item_id) : item_id
    const trend = price > oldPrice ? 'up' : 'down'
    
    // Добавляем изменение как новую запись
    const priceChange = {
      id: `${item_id}-${Date.now()}-${Math.random()}`, // Уникальный ID для каждого изменения
      itemId: item_id,
      name: productName,
      oldPrice: oldPrice,
      newPrice: price,
      trend: trend,
      timestamp: Date.now()
    }
    
    // Добавляем в начало списка (новые изменения сверху)
    changes.unshift(priceChange)
    
    // Ограничиваем количество записей (показываем только последние 5 изменений)
    if (changes.length > 5) {
      changes.splice(5) // Удаляем все элементы после 5-го
    }
    
    console.log(`[Products.vue] Price change detected: ${productName} ${oldPrice} -> ${price} (${trend})`)
  }
  
  // Обновляем текущую цену
  prices[item_id] = price
}

// Computed для отображаемых изменений цен  
const displayedPriceChanges = computed(() => {
  return priceChanges.value
})

// Обработчик WebSocket broadcast событий
const handleBroadcastEvent = (event) => {
  const { type, data } = event.detail
  console.log('[Products.vue] Broadcast event received:', type, data)
  
  if (type === 'api-item_price_updated' && data) {
    handlePriceUpdate(data)
  }
}

// Интервал для периодического обновления
let priceUpdateInterval = null

onMounted(() => {
  console.log('[Products.vue] Component mounted')
  console.log('[Products.vue] wsManager available:', !!wsManager)
  
  // Инициализируем цены
  setTimeout(() => {
    initializePrices()
  }, 1000)
  
  // Подписываемся на WebSocket broadcast события
  console.log('[Products.vue] Subscribing to WebSocket broadcasts')
  window.addEventListener('ws-broadcast', handleBroadcastEvent)
  
  // Запускаем периодическое обновление каждые 5 секунд
  priceUpdateInterval = setInterval(() => {
    initializePrices()
  }, 5000)
})

onUnmounted(() => {
  // Отписываемся от событий при размонтировании
  console.log('[Products.vue] Unsubscribing from WebSocket broadcasts')
  window.removeEventListener('ws-broadcast', handleBroadcastEvent)
  
  // Останавливаем интервал
  if (priceUpdateInterval) {
    clearInterval(priceUpdateInterval)
  }
})

// Форматирование цены с разделителями
const formatPrice = (price) => {
  return price?.toLocaleString('ru-RU') || '0'
}

// Функция для тестирования (удалить в продакшене)
const testPriceChange = () => {
  const prices = currentPrices.value
  if (Object.keys(prices).length === 0) {
    console.log('[Products.vue] No prices loaded yet for testing')
    return
  }
  
  // Берем случайный товар и меняем его цену
  const items = Object.keys(prices)
  const randomItem = items[Math.floor(Math.random() * items.length)]
  const currentPrice = prices[randomItem]
  const newPrice = currentPrice + (Math.random() > 0.5 ? 10 : -10)
  
  console.log('[Products.vue] Testing price change for', randomItem, currentPrice, '->', newPrice)
  
  handlePriceUpdate({
    item_id: randomItem,
    price: newPrice,
    session_id: wsManager?.gameState?.state?.session?.id
  })
}

// Глобальная функция для тестирования из консоли браузера
if (typeof window !== 'undefined') {
  window.testPriceChange = testPriceChange
}
</script>

<template>
  <div class="products-container">
    <p class="title">{{ title }}</p>
    <div class="content">
      <div v-if="displayedPriceChanges.length > 0" class="products-list">
        <div 
          v-for="change in displayedPriceChanges" 
          :key="change.id" 
          class="product-item"
          :class="{ 'trend-up': change.trend === 'up', 'trend-down': change.trend === 'down' }"
        >
          <div class="product-info">
            <div class="product-name">{{ change.name }}</div>
            <div class="product-price">{{ formatPrice(change.newPrice) }} монет</div>
          </div>
          <div class="trend-indicator">
            <img 
              v-if="change.trend === 'up'" 
              src="/arrow-up.svg" 
              alt="Цена выросла"
              class="trend-icon"
            >
            <img 
              v-else-if="change.trend === 'down'" 
              src="/arrow-down.svg" 
              alt="Цена упала"
              class="trend-icon"
            >
          </div>
        </div>
      </div>
      <div v-else class="no-products">
        Нет событий
      </div>
    </div>
  </div>
</template>

<style scoped>
.products-container {
  width: 100%;
  height: 100%;
}

.title {
  font-size: 4rem;
  margin: 0;
  margin-bottom: 20px;
  text-transform: uppercase;
  color: white;
  text-align: center;
}

.content {
  font-size: 2rem;
  color: white;
  font-weight: 400;
}

.products-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.product-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-radius: 4px;
  transition: all 0.3s ease;
}

.product-item.trend-up {
  background-color: #3D8C00 ;
}

.product-item.trend-down {
  background-color: #D32F2F;
}

.product-item:not(.trend-up):not(.trend-down) {
  background-color: #3D8C00 ;
}

.product-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.product-name {
  font-size: 1.8rem;
  font-weight: 600;
  line-height: 1.2;
}

.product-price {
  font-size: 1.4rem;
  opacity: 0.9;
  line-height: 1.2;
}

.trend-indicator {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  margin-left: 10px;
}

.trend-icon {
  width: 20px;
  height: 20px;
  filter: brightness(0) invert(1); /* Делает иконку белой */
}

.no-products {
  text-align: center;
  padding: 20px;
  opacity: 0.7;
  font-style: italic;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .title {
    font-size: 3rem;
  }
  
  .product-name {
    font-size: 1.6rem;
  }
  
  .product-price {
    font-size: 1.2rem;
  }
}
</style>