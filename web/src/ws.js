import { GameState } from './GameState.js';

/**
 * WebSocketManager - Manages WebSocket connections and game state
 * 
 * Features:
 * - Automatic reconnection on connection loss (every 5 seconds)
 * - Session persistence with localStorage (auto-rejoin on page refresh)
 * - Session rejoin happens AFTER WebSocket connection is established
 */
export class WebSocketManager {
  constructor(url, consoleObj) {
    this.url = url;
    this.socket = null;
    this.console = consoleObj;
    
    // Initialize GameState
    this.gameState = new GameState();
    
    this.pendingCallbacks = new Map();
    this._pollInterval = null;
    
    // Auto-reconnection settings
    this.reconnectInterval = null;
    this.reconnectDelay = 1000; // 5 seconds
    this.isManualDisconnect = false;
    
    // Session persistence key
    this.SESSION_STORAGE_KEY = 'seg_session_id';
    
    // Request optimization
    this.pendingRequests = new Set(); // Track pending requests to avoid duplicates
    this.debouncedRequests = new Map(); // Map of request type -> timeout ID
    this.DEBOUNCE_DELAY = 2000; // 1 second debounce for broadcast-triggered requests
    
    // Request metrics tracking
    this.requestMetrics = {
      total: 0,
      byType: {},
      bySource: {
        polling: 0,
        broadcast: 0,
        manual: 0
      },
      debounced: 0,
      startTime: Date.now()
    };
  }

  // Expose game state for Vue components
  get state() {
    return this.gameState.getState();
  }

  // Convenience getters for backward compatibility
  get session_id() {
    return this.gameState.state.session.id;
  }

  get map() {
    return this.gameState.getMapData();
  }

  get companies() {
    return this.gameState.state.companies;
  }

  get users() {
    return this.gameState.state.users;
  }
  
  /**
   * Get stored session ID from localStorage
   * @returns {string|null}
   */
  getStoredSessionId() {
    try {
      return localStorage.getItem(this.SESSION_STORAGE_KEY);
    } catch (error) {
      console.error('[WS] Error getting stored session ID:', error);
      return null;
    }
  }

  get_id() {
    return `web_${Date.now()}`;
  }

  connect() {
    const client_id = this.get_id();
    const wsUrl = `${this.url}?client_id=${client_id}`;
    
    this.gameState.setConnecting(true);
    this.isManualDisconnect = false;
    
    // Clear any existing reconnect interval
    if (this.reconnectInterval) {
      clearInterval(this.reconnectInterval);
      this.reconnectInterval = null;
    }
    
    this.socket = new WebSocket(wsUrl);
    
    this.socket.onopen = () => {
      console.log('[WS] Connected to server');
      this.gameState.setConnected(true);
      this.gameState.setError(null);
      
      // Try to rejoin stored session after connection is established
      this.attemptSessionRejoin();
    };
    
    this.socket.onmessage = (event) => this.onmessage(event);

    this.socket.onclose = () => {
      console.log('[WS] Disconnected from server');
      this.gameState.setConnected(false);
      this.gameState.setConnecting(false);
      
      // Attempt to reconnect if not manually disconnected
      if (!this.isManualDisconnect) {
        this.scheduleReconnect();
      }
    };
    
    this.socket.onerror = (error) => {
      console.error('[WS] WebSocket error:', error);
      this.gameState.setError('WebSocket connection error');
      this.gameState.setConnected(false);
      this.gameState.setConnecting(false);
    };
  }
  
  /**
   * Schedule automatic reconnection attempt
   */
  scheduleReconnect() {
    if (this.reconnectInterval) {
      return; // Already scheduled
    }
    
    console.log(`[WS] Will attempt to reconnect in ${this.reconnectDelay / 1000} seconds...`);
    
    this.reconnectInterval = setInterval(() => {
      if (!this.gameState.state.connected && !this.isManualDisconnect) {
        console.log('[WS] Attempting to reconnect...');
        this.connect();
      } else {
        // Stop trying if connected
        clearInterval(this.reconnectInterval);
        this.reconnectInterval = null;
      }
    }, this.reconnectDelay);
  }
  
  /**
   * Attempt to rejoin a previously stored session
   */
  attemptSessionRejoin() {
    try {
      const storedSessionId = localStorage.getItem(this.SESSION_STORAGE_KEY);
      
      if (storedSessionId) {
        console.log(`[WS] Found stored session: ${storedSessionId}, attempting to rejoin...`);
        
        // Join the stored session
        this.join_session(storedSessionId, (response) => {
          if (response.success) {
            console.log('[WS] Successfully rejoined stored session');
            // Initialize all game data after successful reconnection
            this.initializeSession();
          } else {
            console.log('[WS] Failed to rejoin stored session, clearing it');
            localStorage.removeItem(this.SESSION_STORAGE_KEY);
          }
        });
      } else {
        console.log('[WS] No stored session found');
      }
    } catch (error) {
      console.error('[WS] Error attempting session rejoin:', error);
    }
  }
  
  /**
   * Store session ID in localStorage
   */
  storeSessionId(sessionId) {
    try {
      if (sessionId) {
        localStorage.setItem(this.SESSION_STORAGE_KEY, sessionId);
        console.log(`[WS] Session ${sessionId} stored for auto-rejoin`);
      }
    } catch (error) {
      console.error('[WS] Error storing session ID:', error);
    }
  }
  
  /**
   * Clear stored session ID
   */
  clearStoredSession() {
    try {
      localStorage.removeItem(this.SESSION_STORAGE_KEY);
      console.log('[WS] Stored session cleared');
    } catch (error) {
      console.error('[WS] Error clearing stored session:', error);
    }
  }

  /**
   * Track a request being sent
   * @param {string} requestType - Type of request (e.g., 'get-companies')
   * @param {string} source - Source of request: 'polling', 'broadcast', 'manual'
   */
  trackRequest(requestType, source = 'manual') {
    this.requestMetrics.total++;
    
    if (!this.requestMetrics.byType[requestType]) {
      this.requestMetrics.byType[requestType] = 0;
    }
    this.requestMetrics.byType[requestType]++;
    
    if (this.requestMetrics.bySource[source] !== undefined) {
      this.requestMetrics.bySource[source]++;
    }
  }

  /**
   * Get request metrics (callable from console: wsManager.getRequestStats())
   * @returns {Object} Request statistics
   */
  getRequestStats() {
    const elapsed = (Date.now() - this.requestMetrics.startTime) / 1000; // seconds
    const perMinute = (this.requestMetrics.total / elapsed) * 60;
    
    const stats = {
      total: this.requestMetrics.total,
      elapsed_seconds: Math.round(elapsed),
      requests_per_minute: Math.round(perMinute * 10) / 10,
      by_source: { ...this.requestMetrics.bySource },
      by_type: { ...this.requestMetrics.byType },
      debounced_count: this.requestMetrics.debounced
    };
    
    // Sort by type from most to least requests
    const sortedByType = Object.entries(stats.by_type)
      .sort((a, b) => b[1] - a[1])
      .reduce((obj, [key, value]) => {
        obj[key] = value;
        return obj;
      }, {});
    
    stats.by_type = sortedByType;
    
    console.log('=== WebSocket Request Statistics ===');
    console.log(`Total Requests: ${stats.total}`);
    console.log(`Elapsed Time: ${stats.elapsed_seconds}s`);
    console.log(`Rate: ${stats.requests_per_minute} requests/minute`);
    console.log(`Debounced: ${stats.debounced_count}`);
    console.log('\nBy Source:');
    console.table(stats.by_source);
    console.log('\nBy Type (Top 10):');
    const top10 = Object.entries(sortedByType).slice(0, 10);
    console.table(Object.fromEntries(top10));
    console.log('\nFull data returned as object');
    
    return stats;
  }

  /**
   * Reset request metrics (callable from console: wsManager.resetRequestStats())
   */
  resetRequestStats() {
    this.requestMetrics = {
      total: 0,
      byType: {},
      bySource: {
        polling: 0,
        broadcast: 0,
        manual: 0
      },
      debounced: 0,
      startTime: Date.now()
    };
    console.log('[WS] Request metrics reset');
  }

  /**
   * Print live request rate (callable from console: wsManager.printRequestRate())
   */
  printRequestRate() {
    const elapsed = (Date.now() - this.requestMetrics.startTime) / 1000;
    const perMinute = (this.requestMetrics.total / elapsed) * 60;
    
    console.log(`[WS] Current rate: ${Math.round(perMinute * 10) / 10} requests/minute (${this.requestMetrics.total} total)`);
    return perMinute;
  }

  /**
   * Start monitoring request rate (callable from console: wsManager.startMonitoring(intervalSeconds))
   * @param {number} intervalSeconds - How often to print stats (default: 30)
   * @returns {number} - Interval ID (use clearInterval(id) to stop)
   */
  startMonitoring(intervalSeconds = 30) {
    if (this._monitoringInterval) {
      console.log('[WS] Monitoring already running, stopping old one');
      clearInterval(this._monitoringInterval);
    }
    
    console.log(`[WS] Starting request monitoring (every ${intervalSeconds}s)`);
    this.resetRequestStats();
    
    this._monitoringInterval = setInterval(() => {
      this.printRequestRate();
    }, intervalSeconds * 1000);
    
    return this._monitoringInterval;
  }

  /**
   * Stop monitoring request rate (callable from console: wsManager.stopMonitoring())
   */
  stopMonitoring() {
    if (this._monitoringInterval) {
      clearInterval(this._monitoringInterval);
      this._monitoringInterval = null;
      console.log('[WS] Request monitoring stopped');
      this.getRequestStats(); // Print final stats
    } else {
      console.log('[WS] No monitoring running');
    }
  }

  join_session(session_id, callback = null) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      const error = "WebSocket is not connected";
      this.gameState.setError(error);
      if (callback) {
        callback({ success: false, error: error });
      }
      return null;
    }

    const request_id = `join_session_${Date.now()}_${Math.random()
      .toString(36)
      .substr(2, 9)}`;
    if (callback && typeof callback === "function") {
      this.pendingCallbacks.set(request_id, callback);
    }

    this.state.session.id = session_id;
    console.log(`[WS] Joining session ${session_id}`);
    
    // Store session ID for auto-rejoin
    this.storeSessionId(session_id);

    this.socket.send(
      JSON.stringify({
        type: "get-session",
        session_id: session_id,
        request_id: request_id,
      })
    );

    return request_id;
  }

  check_session(session_id, callback = null) {
    const request_id = `check_session_${Date.now()}_${Math.random()
      .toString(36)
      .substr(2, 9)}`;
    if (callback && typeof callback === "function") {
      this.pendingCallbacks.set(request_id, callback);
    }

    this.socket.send(
      JSON.stringify({
        type: "get-session",
        session_id: session_id,
        request_id: request_id,
      })
    );

    return request_id;
  }

  get_sessions(callback = null) {
    const request_id = `get_sessions_${Date.now()}_${Math.random()
      .toString(36)
      .substr(2, 9)}`;
    if (callback && typeof callback === "function") {
      this.pendingCallbacks.set(request_id, callback);
    }
    this.socket.send(
      JSON.stringify({
        type: "get-sessions",
        request_id: request_id,
      })
    );
    return request_id;
  }

  get_session(callback = null, source = 'manual') {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      const error = "WebSocket is not connected";
      this.gameState.setError(error);
      if (callback) callback({ success: false, error });
      return null;
    }

    // Check if we have a session ID
    if (!this.gameState.state.session.id) {
      console.warn('[WS] No session ID available, skipping session fetch');
      if (callback) callback({ success: false, error: "No session ID" });
      return null;
    }

    const request_id = `get_session_${Date.now()}_${Math.random()
      .toString(36)
      .substr(2, 9)}`;
    if (callback && typeof callback === "function") {
      this.pendingCallbacks.set(request_id, callback);
    }

    this.trackRequest('get-session', source);

    this.socket.send(
      JSON.stringify({
        type: "get-session",
        session_id: this.gameState.state.session.id,
        request_id: request_id,
      })
    );
    return request_id;
  }

  get_session_event(callback = null) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      const error = "WebSocket is not connected";
      this.gameState.setError(error);
      if (callback) callback({ success: false, error });
      return null;
    }

    // Check if we have a session ID
    if (!this.gameState.state.session.id) {
      console.warn('[WS] No session ID available, skipping event fetch');
      if (callback) callback({ success: false, error: "No session ID" });
      return null;
    }

    const request_id = `get_session_event_${Date.now()}_${Math.random()
      .toString(36)
      .substr(2, 9)}`;
    if (callback && typeof callback === "function") {
      this.pendingCallbacks.set(request_id, callback);
    }
    
    this.trackRequest('get-session-event', 'manual');
    
    this.socket.send(
      JSON.stringify({
        type: "get-session-event",
        session_id: this.gameState.state.session.id,
        request_id: request_id,
      })
    );
    return request_id;
  }

  get_companies(callback = null, source = 'manual') {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      const error = "WebSocket is not connected";
      this.gameState.setError(error);
      if (callback) callback({ success: false, error });
      return null;
    }
    const request_id = `get_companies_${Date.now()}_${Math.random()
      .toString(36)
      .substr(2, 9)}`;
    if (callback && typeof callback === "function") {
      this.pendingCallbacks.set(request_id, callback);
    }
    
    this.trackRequest('get-companies', source);
    
    this.socket.send(
      JSON.stringify({
        type: "get-companies",
        session_id: this.gameState.state.session.id || undefined,
        request_id: request_id,
      })
    );
    return request_id;
  }

  get_users(callback = null, source = 'manual') {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      const error = "WebSocket is not connected";
      this.gameState.setError(error);
      if (callback) callback({ success: false, error });
      return null;
    }
    
    this.trackRequest('get-users', source);
    
    const request_id = `get_users_${Date.now()}_${Math.random()
      .toString(36)
      .substr(2, 9)}`;
    if (callback && typeof callback === "function") {
      this.pendingCallbacks.set(request_id, callback);
    }
    this.socket.send(
      JSON.stringify({
        type: "get-users",
        session_id: this.gameState.state.session.id || undefined,
        request_id: request_id,
      })
    );
    return request_id;
  }

  get_factories(company_id, callback = null, source = 'manual') {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      const error = "WebSocket is not connected";
      this.gameState.setError(error);
      if (callback) callback({ success: false, error });
      return null;
    }
    
    this.trackRequest('get-factories', source);
    
    const request_id = `get_factories_${Date.now()}_${Math.random()
      .toString(36)
      .substr(2, 9)}`;
    if (callback && typeof callback === "function") {
      this.pendingCallbacks.set(request_id, callback);
    }
    this.socket.send(
      JSON.stringify({
        type: "get-factories",
        company_id: company_id,
        request_id: request_id,
      })
    );
    return request_id;
  }

  get_exchanges(callback = null, source = 'manual') {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      const error = "WebSocket is not connected";
      this.gameState.setError(error);
      if (callback) callback({ success: false, error });
      return null;
    }
    
    this.trackRequest('get-exchanges', source);
    
    const request_id = `get_exchanges_${Date.now()}_${Math.random()
      .toString(36)
      .substr(2, 9)}`;
    if (callback && typeof callback === "function") {
      this.pendingCallbacks.set(request_id, callback);
    }
    this.socket.send(
      JSON.stringify({
        type: "get-exchanges",
        session_id: this.gameState.state.session.id || undefined,
        request_id: request_id,
      })
    );
    return request_id;
  }

  get_all_item_prices(callback = null, source = 'manual') {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      const error = "WebSocket is not connected";
      this.gameState.setError(error);
      if (callback) callback({ success: false, error });
      return null;
    }
    
    this.trackRequest('get-items-price', source);
    
    const request_id = `get_all_item_prices_${Date.now()}_${Math.random()
      .toString(36)
      .substr(2, 9)}`;
    if (callback && typeof callback === "function") {
      this.pendingCallbacks.set(request_id, callback);
    }
    
    console.log('[WS] Fetching item prices with popularity data');
    
    this.socket.send(
      JSON.stringify({
        type: "get-items-price",
        session_id: this.gameState.state.session.id || undefined,
        request_id: request_id,
      })
    );
    return request_id;
  }

  get_cities(callback = null, source = 'manual') {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      const error = "WebSocket is not connected";
      this.gameState.setError(error);
      if (callback) callback({ success: false, error });
      return null;
    }
    
    this.trackRequest('get-cities', source);
    
    const request_id = `get_cities_${Date.now()}_${Math.random()
      .toString(36)
      .substr(2, 9)}`;
    if (callback && typeof callback === "function") {
      this.pendingCallbacks.set(request_id, callback);
    }
    this.socket.send(
      JSON.stringify({
        type: "get-cities",
        session_id: this.gameState.state.session.id || undefined,
        request_id: request_id,
      })
    );
    return request_id;
  }

  get_city(cityId, callback = null, source = 'manual') {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      const error = "WebSocket is not connected";
      this.gameState.setError(error);
      if (callback) callback({ success: false, error });
      return null;
    }
    
    this.trackRequest('get-city', source);
    
    const request_id = `get_city_${Date.now()}_${Math.random()
      .toString(36)
      .substr(2, 9)}`;
    if (callback && typeof callback === "function") {
      this.pendingCallbacks.set(request_id, callback);
    }
    this.socket.send(
      JSON.stringify({
        type: "get-city",
        id: cityId,
        request_id: request_id,
      })
    );
    return request_id;
  }

  get_city_demands(cityId, callback = null) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      const error = "WebSocket is not connected";
      this.gameState.setError(error);
      if (callback) callback({ success: false, error });
      return null;
    }
    const request_id = `get_city_demands_${Date.now()}_${Math.random()
      .toString(36)
      .substr(2, 9)}`;
    if (callback && typeof callback === "function") {
      this.pendingCallbacks.set(request_id, callback);
    }
    this.socket.send(
      JSON.stringify({
        type: "get-city-demands",
        city_id: cityId,
        request_id: request_id,
      })
    );
    return request_id;
  }

  sell_to_city(cityId, companyId, resourceId, amount, password, callback = null) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      const error = "WebSocket is not connected";
      this.gameState.setError(error);
      if (callback) callback({ success: false, error });
      return null;
    }
    const request_id = `sell_to_city_${Date.now()}_${Math.random()
      .toString(36)
      .substr(2, 9)}`;
    if (callback && typeof callback === "function") {
      this.pendingCallbacks.set(request_id, callback);
    }
    this.socket.send(
      JSON.stringify({
        type: "sell-to-city",
        city_id: cityId,
        company_id: companyId,
        resource_id: resourceId,
        amount: amount,
        password: password,
        request_id: request_id,
      })
    );
    return request_id;
  }

  get_time_to_next_stage(callback = null, source = 'manual') {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      const error = "WebSocket is not connected";
      this.gameState.setError(error);
      if (callback) callback({ success: false, error });
      return null;
    }
    
    // Check if we have a session ID before trying to fetch time
    if (!this.gameState.state.session.id) {
      console.warn('[WS] No session ID available, skipping time fetch');
      if (callback) callback({ success: false, error: "No session ID" });
      return null;
    }
    
    this.trackRequest('get-session-time-to-next-stage', source);
    
    const request_id = `get_time_${Date.now()}_${Math.random()
      .toString(36)
      .substr(2, 9)}`;
    if (callback && typeof callback === "function") {
      this.pendingCallbacks.set(request_id, callback);
    }
    
    console.log('[WS] Sending get-session-time-to-next-stage request');
    
    this.socket.send(
      JSON.stringify({
        type: "get-session-time-to-next-stage",
        session_id: this.gameState.state.session.id,
        request_id: request_id,
      })
    );
    return request_id;
  }

  get_session_statistics(callback = null, source = 'manual') {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      const error = "WebSocket is not connected";
      this.gameState.setError(error);
      if (callback) callback({ success: false, error });
      return null;
    }
    
    this.trackRequest('get-all-session-statistics', source);
    
    const request_id = `get_statistics_${Date.now()}_${Math.random()
      .toString(36)
      .substr(2, 9)}`;
    
    if (callback && typeof callback === "function") {
      this.pendingCallbacks.set(request_id, callback);
    }
    
    console.log('[WS] Sending get-all-session-statistics request');
    
    this.socket.send(
      JSON.stringify({
        type: "get-all-session-statistics",
        session_id: this.gameState.state.session.id,
        request_id: request_id,
      })
    );
    return request_id;
  }

  get_session_leaders(callback = null) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      const error = "WebSocket is not connected";
      this.gameState.setError(error);
      if (callback) callback({ success: false, error });
      return null;
    }
    
    const request_id = `get_leaders_${Date.now()}_${Math.random()
      .toString(36)
      .substr(2, 9)}`;
    
    if (callback && typeof callback === "function") {
      this.pendingCallbacks.set(request_id, callback);
    }
    
    console.log('[WS] Sending get-session-leaders request');
    
    this.socket.send(
      JSON.stringify({
        type: "get-session-leaders",
        session_id: this.gameState.state.session.id,
        request_id: request_id,
      })
    );
    return request_id;
  }

  /**
   * Debounce a request - delays execution and resets timer on repeated calls
   * @param {string} requestKey - Unique key for this request type
   * @param {Function} requestFn - Function to call after debounce
   * @param {number} delay - Delay in milliseconds (default: DEBOUNCE_DELAY)
   * @param {string} source - Source of request (default: 'broadcast')
   */
  debounceRequest(requestKey, requestFn, delay = this.DEBOUNCE_DELAY, source = 'broadcast') {
    // Clear existing timer for this request type
    if (this.debouncedRequests.has(requestKey)) {
      clearTimeout(this.debouncedRequests.get(requestKey));
      this.requestMetrics.debounced++; // Count debounced requests
    }
    
    // Set new timer
    const timeoutId = setTimeout(() => {
      this.debouncedRequests.delete(requestKey);
      requestFn(source); // Pass source to request function
    }, delay);
    
    this.debouncedRequests.set(requestKey, timeoutId);
  }

  /**
   * Check if a request is already pending to avoid duplicates
   * @param {string} requestType - Type of request
   * @returns {boolean} - True if request is already pending
   */
  isRequestPending(requestType) {
    return this.pendingRequests.has(requestType);
  }

  /**
   * Mark request as pending
   * @param {string} requestType - Type of request
   */
  markRequestPending(requestType) {
    this.pendingRequests.add(requestType);
  }

  /**
   * Mark request as completed
   * @param {string} requestType - Type of request
   */
  markRequestComplete(requestType) {
    this.pendingRequests.delete(requestType);
  }

  /**
   * Get polling interval based on game stage
   * @returns {number} Interval in milliseconds
   */
  getPollingInterval() {
    const stage = this.gameState.state.session.stage;
    
    switch (stage) {
      case 'Setup':
      case 'Lobby':
        return 10000; // 10 seconds - less critical
      case 'Between':
        return 7000; // 7 seconds - moderate
      case 'Active':
        return 5000; // 5 seconds - most critical
      case 'End':
        return 0; // No polling
      default:
        return 5000; // Default to 5 seconds
    }
  }

  startPolling(intervalMs = null) {
    this.stopPolling();
    
    // Use stage-based interval if not specified
    const interval = intervalMs !== null ? intervalMs : this.getPollingInterval();
    
    if (interval === 0) {
      console.log('[WS] Polling disabled for current stage');
      return;
    }
    
    // Initial comprehensive fetch
    this.fetchAllGameData();
    
    this._pollInterval = setInterval(() => {
      this.fetchAllGameData();
    }, interval);
    
    console.log(`[WS] Polling started with ${interval}ms interval`);
  }

  /**
   * Restart polling with updated interval based on current stage
   */
  restartPolling() {
    const interval = this.getPollingInterval();
    if (interval > 0) {
      this.startPolling(interval);
    } else {
      this.stopPolling();
    }
  }

  /**
   * Fetch all necessary game data in the correct order
   */
  fetchAllGameData() {
    // Don't fetch data if game has ended
    if (this.gameState.state.session.stage === 'End') {
      console.log('[WS] Game has ended, skipping data fetch');
      return;
    }
    
    // 1. Session state and map (includes time_to_next_stage)
    this.get_session(null, 'polling');
    
    // 2. Explicitly fetch time to ensure it's always fresh
    this.get_time_to_next_stage(null, 'polling');
    
    // 3. Event data
    this.get_session_event(null, 'polling');
    
    // 4. Companies and their users
    this.get_companies(null, 'polling');
    this.get_users(null, 'polling');
    
    // 5. Cities
    this.get_cities(null, 'polling');
    
    // 6. Exchange data
    this.get_exchanges(null, 'polling');
    
    // 7. Item prices
    this.get_all_item_prices(null, 'polling');
    
    // Note: Factories are fetched per company when needed
    // Events are handled via broadcasts
  }

  /**
   * Fetch frequently updated data (without cities)
   */
  fetchFrequentData() {
    // Don't fetch data if game has ended
    if (this.gameState.state.session.stage === 'End') {
      console.log('[WS] Game has ended, skipping frequent data fetch');
      return;
    }
    
    // 1. Session state and time
    this.get_session();
    this.get_time_to_next_stage();
    
    // 2. Event data
    this.get_session_event();
    
    // 3. Companies and users (can change frequently)
    this.get_companies();
    this.get_users();
    
    // 4. Exchanges (active data)
    this.get_exchanges();
    
    // 5. Item prices
    this.get_all_item_prices();
    
    // Cities are fetched separately less frequently
  }

  stopPolling() {
    if (this._pollInterval) {
      clearInterval(this._pollInterval);
      this._pollInterval = null;
      console.log('[WS] Polling stopped');
    }
  }

  ping() {
    const request_id = `ping_${Date.now()}_${Math.random()
      .toString(36)
      .substr(2, 9)}`;
    this.socket.send(JSON.stringify({ type: "ping", request_id: request_id }));
    return request_id;
  }

  onmessage(event) {
    const message = JSON.parse(event.data);

    if (message.type === "response" && message.request_id) {
      if (
        message.request_id.startsWith("check_session_") ||
        message.request_id.startsWith("join_session_") ||
        message.request_id.startsWith("get_session_")
      ) {
        this.handleSessionResponse(message);
      } else if (message.request_id.startsWith("get_session_event_")) {
        this.handleEventResponse(message);
      } else if (message.request_id.startsWith("get_companies_")) {
        this.handleCompaniesResponse(message);
      } else if (message.request_id.startsWith("get_company_")) {
        this.handleSingleCompanyResponse(message);
      } else if (message.request_id.startsWith("get_users_")) {
        this.handleUsersResponse(message);
      } else if (message.request_id.startsWith("get_factories_")) {
        this.handleFactoriesResponse(message);
      } else if (message.request_id.startsWith("get_exchanges_")) {
        this.handleExchangesResponse(message);
      } else if (message.request_id.startsWith("get_all_item_prices_")) {
        this.handleItemPricesResponse(message);
      } else if (message.request_id.startsWith("get_cities_")) {
        this.handleCitiesResponse(message);
      } else if (message.request_id.startsWith("get_city_demands_")) {
        this.handleCityDemandsResponse(message);
      } else if (message.request_id.startsWith("get_city_")) {
        this.handleCityResponse(message);
      } else if (message.request_id.startsWith("sell_to_city_")) {
        this.handleSellToCityResponse(message);
      } else if (message.request_id.startsWith("get_time_")) {
        this.handleTimeResponse(message);
      } else if (message.request_id.startsWith("get_statistics_")) {
        this.handleStatisticsResponse(message);
      } else if (message.request_id.startsWith("get_leaders_")) {
        this.handleLeadersResponse(message);
      } else if (message.request_id.startsWith("get_sessions_")) {
        this.handleSessionsListResponse(message);
      } else if (message.request_id.startsWith("get_improvement_info_")) {
        this.handleImprovementInfoResponse(message);
      } else if (message.request_id.startsWith("get_company_cell_info_")) {
        this.handleCellInfoResponse(message);
      } else {
        // Generic handler for other responses
        this.handleGenericResponse(message);
      }
    } else if (message.type && message.type.startsWith("api-")) {
      this.handleBroadcast(message);
    } else if (message.type === "error") {
      this.gameState.setError(message.message || 'Unknown error');
      console.error('[WS] Server error:', message.message);
    } else if (message.type === "pong") {
      console.log('[WS] Pong received');
    }
    
    return message;
  }

  handleSessionResponse(message) {
    const requestId = message.request_id;
    const callback = this.pendingCallbacks.get(requestId);
    
    if (message.data) {
      console.log('[WS] Session response received. time_to_next_stage:', message.data.time_to_next_stage);
      
      // Update game state with session data
      this.gameState.updateSession(message.data);
      
      // Update time to next stage if provided in session data
      if (message.data.time_to_next_stage !== undefined) {
        console.log('[WS] Updating time from session response:', message.data.time_to_next_stage);
        this.gameState.updateTimeToNextStage(message.data.time_to_next_stage);
      } else {
        console.warn('[WS] Session response missing time_to_next_stage field');
      }
      
      // Load map if available
      if (message.data.cells && message.data.map_size) {
        this.loadMapToDOM();
      }

      // Initialize session data after joining/connecting
      if (requestId.startsWith('join_session_')) {
        console.log('[WS] Session joined successfully, initializing game data...');
        this.initializeSession();
      }

      if (callback) {
        callback({ success: true, data: message.data });
      }
    } else {
      if (callback) {
        callback({ success: false, error: "Session not found" });
      }
      this.gameState.setError("Session not found");
    }

    if (callback) {
      this.pendingCallbacks.delete(requestId);
    }
  }  handleSessionsListResponse(message) {
    const requestId = message.request_id;
    const callback = this.pendingCallbacks.get(requestId);
    
    if (callback) {
      if (message.data) {
        callback({ success: true, data: message.data });
      } else {
        callback({ success: false, error: "No sessions data" });
      }
      this.pendingCallbacks.delete(requestId);
    }
  }

  handleEventResponse(message) {
    const requestId = message.request_id;
    const callback = this.pendingCallbacks.get(requestId);
    
    console.log('[WS] Event response received:', message);
    console.log('[WS] Event response - data exists:', !!message.data);
    console.log('[WS] Event response - event property exists:', message.data && 'event' in message.data);
    console.log('[WS] Event response - event value:', message.data?.event);
    
    if (message.data && message.data.event !== undefined) {
      // Check if event has data
      const eventData = message.data.event;
      
      if (eventData && eventData.id && Object.keys(eventData).length > 0) {
        // Update event in game state
        console.log('[WS] Updating event with ID:', eventData.id, eventData);
        this.gameState.updateEvent(eventData);
        
        if (callback) {
          callback({ success: true, data: eventData });
        }
      } else {
        // Empty event object - clear it
        console.log('[WS] Empty event data, clearing event');
        this.gameState.clearEvent();
        
        if (callback) {
          callback({ success: true, data: null });
        }
      }
    } else {
      // No event data - clear it
      console.log('[WS] No event data in response, clearing event');
      this.gameState.clearEvent();
      
      if (callback) {
        callback({ success: true, data: null });
      }
    }

    if (callback) {
      this.pendingCallbacks.delete(requestId);
    }
  }

  handleCompaniesResponse(message) {
    const requestId = message.request_id;
    const callback = this.pendingCallbacks.get(requestId);
    
    if (message.data) {
      let companiesData = [];
      
      if (Array.isArray(message.data)) {
        companiesData = message.data;
      } else if (Array.isArray(message.data.companies)) {
        companiesData = message.data.companies;
      }
      
      // Update game state
      this.gameState.updateCompanies(companiesData);
      
      // Update map to reflect any position changes
      setTimeout(() => {
        console.log('[WS] Updating map after companies data received');
        this.loadMapToDOM();
      }, 100);
      
      if (callback) callback({ success: true, data: companiesData });
    } else {
      if (callback) callback({ success: false, error: "No companies data" });
    }
    
    if (callback) this.pendingCallbacks.delete(requestId);
    
    // Dispatch custom event for components
    window.dispatchEvent(
      new CustomEvent("companies-updated", {
        detail: { companies: this.gameState.state.companies },
      })
    );
  }

  handleUsersResponse(message) {
    const requestId = message.request_id;
    const callback = this.pendingCallbacks.get(requestId);
    
    if (message.data) {
      let usersData = [];
      
      if (Array.isArray(message.data)) {
        usersData = message.data;
      } else if (Array.isArray(message.data.users)) {
        usersData = message.data.users;
      }
      
      // Update game state
      this.gameState.updateUsers(usersData);
      
      if (callback) callback({ success: true, data: usersData });
    } else {
      if (callback) callback({ success: false, error: "No users data" });
    }
    
    if (callback) this.pendingCallbacks.delete(requestId);
  }

  handleFactoriesResponse(message) {
    const requestId = message.request_id;
    const callback = this.pendingCallbacks.get(requestId);
    
    if (message.data) {
      let factoriesData = [];
      
      if (Array.isArray(message.data)) {
        factoriesData = message.data;
      } else if (Array.isArray(message.data.factories)) {
        factoriesData = message.data.factories;
      }
      
      // Update game state
      this.gameState.updateFactories(factoriesData);
      
      if (callback) callback({ success: true, data: factoriesData });
    } else {
      if (callback) callback({ success: false, error: "No factories data" });
    }
    
    if (callback) this.pendingCallbacks.delete(requestId);
  }

  handleExchangesResponse(message) {
    const requestId = message.request_id;
    const callback = this.pendingCallbacks.get(requestId);
    
    if (message.data) {
      let exchangesData = [];
      
      if (Array.isArray(message.data)) {
        exchangesData = message.data;
      } else if (Array.isArray(message.data.exchanges)) {
        exchangesData = message.data.exchanges;
      }
      
      // Update game state
      this.gameState.updateExchanges(exchangesData);
      
      if (callback) callback({ success: true, data: exchangesData });
    } else {
      if (callback) callback({ success: false, error: "No exchanges data" });
    }
    
    if (callback) this.pendingCallbacks.delete(requestId);
  }

  handleItemPricesResponse(message) {
    const requestId = message.request_id;
    const callback = this.pendingCallbacks.get(requestId);
    
    // Handle both formats: array directly or wrapped in prices object
    let pricesData = null;
    
    if (Array.isArray(message.data)) {
      // New format: array of full item price objects with popularity
      pricesData = message.data;
      console.log('[WS] Received item prices array:', pricesData.length, 'items');
    } else if (message.data && message.data.prices) {
      // Old format: prices object
      pricesData = message.data.prices;
      console.log('[WS] Received item prices object');
    }
    
    if (pricesData) {
      // Update game state with prices
      this.gameState.updateItemPrices(pricesData);
      
      if (callback) callback({ success: true, data: pricesData });
    } else {
      console.warn('[WS] No item prices data in response');
      if (callback) callback({ success: false, error: "No item prices data" });
    }
    
    if (callback) this.pendingCallbacks.delete(requestId);
  }

  handleCitiesResponse(message) {
    const requestId = message.request_id;
    const callback = this.pendingCallbacks.get(requestId);
    
    if (message.data) {
      let citiesData = [];
      
      if (Array.isArray(message.data)) {
        citiesData = message.data;
      } else if (Array.isArray(message.data.cities)) {
        citiesData = message.data.cities;
      }
      
      // Update game state
      this.gameState.updateCities(citiesData);
      
      if (callback) callback({ success: true, data: citiesData });
    } else {
      if (callback) callback({ success: false, error: "No cities data" });
    }
    
    if (callback) this.pendingCallbacks.delete(requestId);
  }

  handleCityResponse(message) {
    const requestId = message.request_id;
    const callback = this.pendingCallbacks.get(requestId);
    
    if (message.data) {
      // Update this specific city in the cities array
      const cityData = message.data;
      const existingIndex = this.gameState.state.cities.findIndex(
        c => c.id === cityData.id
      );
      
      if (existingIndex >= 0) {
        this.gameState.state.cities[existingIndex] = cityData;
      } else {
        this.gameState.state.cities.push(cityData);
      }
      
      if (callback) callback({ success: true, data: cityData });
    } else {
      if (callback) callback({ success: false, error: message.error || "No city data" });
    }
    
    if (callback) this.pendingCallbacks.delete(requestId);
  }

  handleCityDemandsResponse(message) {
    const requestId = message.request_id;
    const callback = this.pendingCallbacks.get(requestId);
    
    if (message.data) {
      // Update the city's demands in the cities array
      const cityId = message.data.city_id;
      const existingCity = this.gameState.state.cities.find(c => c.id === cityId);
      
      if (existingCity) {
        existingCity.demands = message.data.demands;
        existingCity.branch = message.data.branch;
      }
      
      if (callback) callback({ success: true, data: message.data });
    } else {
      if (callback) callback({ success: false, error: message.error || "No city demands data" });
    }
    
    if (callback) this.pendingCallbacks.delete(requestId);
  }

  handleSellToCityResponse(message) {
    const requestId = message.request_id;
    const callback = this.pendingCallbacks.get(requestId);
    
    if (message.data) {
      // Refresh relevant data after successful trade
      if (message.data.success) {
        this.get_companies();
        this.get_cities();
      }
      
      if (callback) callback({ success: true, data: message.data });
    } else {
      if (callback) callback({ success: false, error: message.error || "Trade failed" });
    }
    
    if (callback) this.pendingCallbacks.delete(requestId);
  }

  handleTimeResponse(message) {
    const requestId = message.request_id;
    const callback = this.pendingCallbacks.get(requestId);
    console.log('[WS] Time response received:', message);
    
    if (message.data && message.data.time_to_next_stage !== undefined) {
      this.gameState.updateTimeToNextStage(message.data.time_to_next_stage);
      console.log('[WS] Time updated:', message.data.time_to_next_stage);
      
      // Also update session step if provided
      if (message.data.step !== undefined) {
        this.gameState.state.session.step = message.data.step;
      }
      if (message.data.max_steps !== undefined) {
        this.gameState.state.session.max_steps = message.data.max_steps;
      }
      if (message.data.stage_now !== undefined) {
        this.gameState.state.session.stage = message.data.stage_now;
      }
      
      if (callback) callback({ success: true, data: message.data });
    } else {
      if (callback) callback({ success: false, error: "No time data" });
    }
    
    if (callback) this.pendingCallbacks.delete(requestId);
  }

  handleSingleCompanyResponse(message) {
    const requestId = message.request_id;
    const callback = this.pendingCallbacks.get(requestId);
    
    if (message.data) {
      // Update this specific company in the companies array
      const companyData = message.data;
      const existingIndex = this.gameState.state.companies.findIndex(
        c => c.id === companyData.id
      );
      
      if (existingIndex >= 0) {
        this.gameState.state.companies[existingIndex] = companyData;
      } else {
        this.gameState.state.companies.push(companyData);
      }
      
      if (callback) callback({ success: true, data: companyData });
    } else {
      if (callback) callback({ success: false, error: "No company data" });
    }
    
    if (callback) this.pendingCallbacks.delete(requestId);
  }

  handleStatisticsResponse(message) {
    const requestId = message.request_id;
    const callback = this.pendingCallbacks.get(requestId);
    
    console.log('[WS] Statistics response received:', message);
    
    if (message.data && Array.isArray(message.data)) {
      this.gameState.updateStatistics(message.data);
      
      if (callback) {
        callback({ success: true, data: message.data });
      }
    } else {
      console.warn('[WS] Invalid statistics data in response');
      
      if (callback) {
        callback({ success: false, error: "Invalid statistics data" });
      }
    }
    
    if (callback) {
      this.pendingCallbacks.delete(requestId);
    }
  }

  handleLeadersResponse(message) {
    const requestId = message.request_id;
    const callback = this.pendingCallbacks.get(requestId);
    
    console.log('[WS] Leaders response received:', message);
    console.log('[WS] Leaders data structure:', {
      capital: message.data?.capital,
      reputation: message.data?.reputation,
      economic: message.data?.economic
    });
    
    if (message.data) {
      // Update winners in game state
      this.gameState.updateWinners({
        capital: message.data.capital,
        reputation: message.data.reputation,
        economic: message.data.economic
      });
      
      console.log('[WS] Winners updated, current state:', this.gameState.getWinners());
      
      if (callback) {
        callback({ success: true, data: message.data });
      }
    } else {
      console.warn('[WS] Invalid leaders data in response');
      
      if (callback) {
        callback({ success: false, error: "Invalid leaders data" });
      }
    }
    
    if (callback) {
      this.pendingCallbacks.delete(requestId);
    }
  }

  handleImprovementInfoResponse(message) {
    const requestId = message.request_id;
    const callback = this.pendingCallbacks.get(requestId);
    
    if (message.data) {
      // Store improvement info separately or update company data
      console.log('[WS] Improvement info received:', message.data);
      
      if (callback) callback({ success: true, data: message.data });
    } else {
      if (callback) callback({ success: false, error: "No improvement data" });
    }
    
    if (callback) this.pendingCallbacks.delete(requestId);
  }

  handleCellInfoResponse(message) {
    const requestId = message.request_id;
    const callback = this.pendingCallbacks.get(requestId);
    
    if (message.data) {
      // Store cell info separately or update company data
      console.log('[WS] Cell info received:', message.data);
      
      if (callback) callback({ success: true, data: message.data });
    } else {
      if (callback) callback({ success: false, error: "No cell data" });
    }
    
    if (callback) this.pendingCallbacks.delete(requestId);
  }

  handleGenericResponse(message) {
    const requestId = message.request_id;
    const callback = this.pendingCallbacks.get(requestId);
    
    if (callback) {
      if (message.data !== undefined) {
        callback({ success: true, data: message.data });
      } else {
        callback({ success: false, error: "No data in response" });
      }
      this.pendingCallbacks.delete(requestId);
    } else {
      console.log('[WS] Response received with no callback:', message);
    }
  }

  handleBroadcast(message) {
    console.log('[WS] Broadcast received:', message.type, message.data);
    
    // DEBUGGING: Log all event-related broadcasts
    if (message.type.includes('event') || (message.data && message.data.event !== undefined)) {
      console.log('[WS] EVENT BROADCAST DETECTED:', message.type, message.data);
    }
    
    // Handle different broadcast types with debouncing
    switch (message.type) {
      case 'api-create_company':
      case 'api-company_deleted':
      case 'api-user_added_to_company':
      case 'api-user_left_company':
        // Debounced refresh companies
        this.debounceRequest('companies', () => this.get_companies(null, 'broadcast'), 1000, 'broadcast');
        break;

      case 'api-company_set_position':
        // Log position change details
        console.log('[WS] Company position changed:', message.data);
        // Debounced refresh companies - this will trigger map update
        this.debounceRequest('companies', () => this.get_companies(null, 'broadcast'), 1000, 'broadcast');
        break;

      case 'api-company_improvement_upgraded':
        // Add upgrade to recent upgrades list
        if (message.data) {
          this.gameState.addUpgrade(message.data);
        }
        // Debounced refresh companies
        this.debounceRequest('companies', () => this.get_companies(null, 'broadcast'), 1000, 'broadcast');
        break;
        
      case 'api-create_user':
      case 'api-update_user':
      case 'api-user_deleted':
        // Debounced refresh users
        this.debounceRequest('users', () => this.get_users(null, 'broadcast'), 1000, 'broadcast');
        break;
        
      case 'api-update_session_stage':
        console.log('[WS] Stage update broadcast received');
        
        // Check if game has ended - no need to fetch data anymore
        if (message.data && message.data.new_stage === 'End') {
          console.log('[WS] Game ended, stopping data fetching');
          this.stopPolling();
          break;
        }
        
        // Immediate refresh for critical stage changes (no debounce, but mark as broadcast)
        this.get_session(null, 'broadcast');
        this.get_time_to_next_stage(null, 'broadcast');
        this.get_session_event(null, 'broadcast');

        // If stage changed, reload map
        if (message.data && message.data.new_stage) {
          this.loadMapToDOM();
          // Restart polling with new interval based on stage
          this.restartPolling();
        }
        break;
        
      case 'api-session_deleted':
        // Clear session if it's the current one (immediate, no debounce)
        if (message.data && message.data.session_id === this.gameState.state.session.id) {
          this.leaveSession();
        }
        break;
        
      case 'api-game_ended':
        console.log('[WS] Game ended broadcast received');
        // Handle game end with winners
        if (message.data && message.data.winners) {
          this.gameState.updateWinners(message.data.winners);
        }
        // Stop polling for ended game
        this.stopPolling();
        // Immediate refresh (no debounce for game end, but mark as broadcast)
        this.get_session(null, 'broadcast');
        this.get_session_statistics(null, 'broadcast');
        break;
        
      case 'api-factory-start-complectation':
        // Debounced refresh factories if we have a company
        if (this.gameState.hasCompany) {
          this.debounceRequest('factories', () => {
            this.get_factories(this.gameState.state.currentUser.company_id, null, 'broadcast');
          }, 1000, 'broadcast');
        }
        break;
        
      case 'api-exchange_offer_created':
        // Add to recent activity
        if (message.data && message.data.offer) {
          this.gameState.addExchangeActivity({
            type: 'offer_created',
            company_id: message.data.offer.company_id,
            sell_resource: message.data.offer.sell_resource,
            sell_amount_per_trade: message.data.offer.sell_amount_per_trade,
            offer_type: message.data.offer.offer_type,
            price: message.data.offer.price,
            barter_resource: message.data.offer.barter_resource,
            barter_amount: message.data.offer.barter_amount
          });
        }
        // Debounced refresh exchanges
        this.debounceRequest('exchanges', () => this.get_exchanges(null, 'broadcast'), 1000, 'broadcast');
        break;
        
      case 'api-exchange_offer_updated':
      case 'api-exchange_offer_cancelled':
        // Debounced refresh exchanges
        this.debounceRequest('exchanges', () => this.get_exchanges(null, 'broadcast'), 1000, 'broadcast');
        break;
        
      case 'api-exchange_trade_completed':
        // Add to recent activity
        if (message.data) {
          this.gameState.addExchangeActivity({
            type: 'trade_completed',
            seller_id: message.data.seller_id,
            buyer_id: message.data.buyer_id,
            sell_resource: message.data.sell_resource,
            sell_amount: message.data.sell_amount,
            offer_type: message.data.offer_type,
            price: message.data.price,
            barter_resource: message.data.barter_resource,
            barter_amount: message.data.barter_amount
          });
        }
        // Debounced refresh exchanges and companies (batched together)
        this.debounceRequest('exchanges', () => this.get_exchanges(null, 'broadcast'), 1000, 'broadcast');
        this.debounceRequest('companies', () => this.get_companies(null, 'broadcast'), 1000, 'broadcast');
        break;
        
      case 'api-city-create':
      case 'api-city-delete':
        // Debounced refresh cities list
        this.debounceRequest('cities', () => this.get_cities(null, 'broadcast'), 1000, 'broadcast');
        break;
        
      case 'api-city-update-demands':
        // Debounced update specific city demands
        if (message.data && message.data.city_id) {
          this.debounceRequest(`city_${message.data.city_id}`, () => {
            this.get_city(message.data.city_id, null, 'broadcast');
          }, 1000, 'broadcast');
        } else {
          this.debounceRequest('cities', () => this.get_cities(null, 'broadcast'), 1000, 'broadcast');
        }
        break;
        
      case 'api-city-trade':
        // Track product sales from city trades
        if (message.data && message.data.resource_id && message.data.amount) {
          const resource = message.data.resource_id;
          const amount = message.data.amount;
          
          if (!this.gameState.state.productSales[resource]) {
            this.gameState.state.productSales[resource] = 0;
          }
          this.gameState.state.productSales[resource] += amount;
          
          console.log('[WS] City trade tracked:', resource, 'amount:', amount, 'total:', this.gameState.state.productSales[resource]);
        }
        
        // Debounced refresh cities and companies after trade
        this.debounceRequest('cities', () => this.get_cities(null, 'broadcast'), 1000, 'broadcast');
        this.debounceRequest('companies', () => this.get_companies(null, 'broadcast'), 1000, 'broadcast');
        break;
        
      case 'api-item_price_updated':
        console.log('[WS] Item price updated broadcast received:', message.data);
        // Update item prices in game state if needed
        if (message.data && message.data.item_id && message.data.price !== undefined) {
          this.gameState.updateItemPrice(message.data.item_id, message.data.price);
        }
        // Debounced refresh all item prices to stay in sync
        this.debounceRequest('item_prices', () => this.get_all_item_prices(null, 'broadcast'), 1000, 'broadcast');
        break;
      
      case 'api-event_generated':
      case 'api-event_started':
      case 'api-event_ended':
      case 'api-event_updated':
      case 'event_update':
        console.log('[WS] EVENT BROADCAST: Refreshing event data for type:', message.type);
        
        // If broadcast contains event data directly, use it
        if (message.data && message.data.event !== undefined) {
          console.log('[WS] Event data found in broadcast:', message.data.event);
          if (message.data.event && Object.keys(message.data.event).length > 0) {
            this.gameState.updateEvent(message.data.event);
          } else {
            this.gameState.clearEvent();
          }
        } else {
          // Otherwise refresh event data from server
          this.get_session_event();
        }
        break;
    }
    
    // Check if any broadcast message contains event data
    if (message.data && message.data.event !== undefined && 
        !['api-event_generated', 'api-event_started', 'api-event_ended', 'api-event_updated', 'event_update'].includes(message.type)) {
      console.log('[WS] UNEXPECTED EVENT DATA in broadcast type:', message.type, message.data.event);
      if (message.data.event && Object.keys(message.data.event).length > 0) {
        this.gameState.updateEvent(message.data.event);
      } else {
        this.gameState.clearEvent();
      }
    }
    
    // Dispatch custom event for components that need raw broadcast data
    window.dispatchEvent(
      new CustomEvent('ws-broadcast', {
        detail: { type: message.type, data: message.data }
      })
    );
  }

  loadMapToDOM() {
    const mapData = this.gameState.getMapData();
    
    if (!mapData.loaded || !mapData.cells || mapData.cells.length === 0) {
      return false;
    }

    if (
      typeof window.setTile === "function" &&
      typeof window.TileTypes === "object"
    ) {
      const { cells, size } = mapData;

      const mapElement = document.getElementById("map");
      if (mapElement && size.cols !== 7) {
        mapElement.style.gridTemplateColumns = `repeat(${size.cols}, 1fr)`;
        mapElement.style.gridTemplateRows = `repeat(${size.rows}, 1fr)`;
      }

      console.log('[WS] LoadMapToDOM: Redrawing entire map with', cells.length, 'cells');

      // First, load the base terrain (don't pass text to keep default labels)
      for (let i = 0; i < cells.length && i < size.rows * size.cols; i++) {
        const row = Math.floor(i / size.cols);
        const col = i % size.cols;
        const cellType = this.gameState.getCellType(cells[i]);
        // Don't pass text parameter to keep the default coordinate labels
        window.setTile(row, col, cellType);
      }

      // Then, overlay company tiles on their positions
      const sessionId = this.gameState.state.session.id;
      if (sessionId) {
        const companies = this.gameState.getCompaniesBySession(sessionId);
        console.log('[WS] LoadMapToDOM: Placing', companies.length, 'companies on map');
        
        for (const company of companies) {
          if (company.cell_position) {
            // Parse cell_position format "x.y"
            const [colStr, rowStr] = company.cell_position.split('.');
            const col = parseInt(colStr, 10);
            const row = parseInt(rowStr, 10);
            
            console.log('[WS] LoadMapToDOM: Placing company', company.name, 'at position', row, col);
            
            // Set company tile with company name
            if (row >= 0 && row < size.rows && col >= 0 && col < size.cols) {
              window.setTile(row, col, window.TileTypes.COMPANY, company.name);
            }
          }
        }
      }

      return true;
    } else {
      // Retry after a delay if setTile is not available yet
      setTimeout(() => this.loadMapToDOM(), 500);
      return false;
    }
  }

  refreshMap() {
    this.get_session();
  }

  // ==================== COMPANY-SPECIFIC DATA METHODS ====================

  /**
   * Get company cell information
   * @param {number} companyId - Company ID
   * @param {Function} callback - Callback function
   * @returns {string} Request ID
   */
  get_company_cell_info(companyId, callback = null) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      const error = "WebSocket is not connected";
      this.gameState.setError(error);
      if (callback) callback({ success: false, error });
      return null;
    }
    const request_id = `get_company_cell_info_${Date.now()}_${Math.random()
      .toString(36)
      .substr(2, 9)}`;
    if (callback && typeof callback === "function") {
      this.pendingCallbacks.set(request_id, callback);
    }
    this.socket.send(
      JSON.stringify({
        type: "get-company-cell-info",
        company_id: companyId,
        request_id: request_id,
      })
    );
    return request_id;
  }

  /**
   * Get company improvement information
   * @param {number} companyId - Company ID
   * @param {Function} callback - Callback function
   * @returns {string} Request ID
   */
  get_company_improvement_info(companyId, callback = null) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      const error = "WebSocket is not connected";
      this.gameState.setError(error);
      if (callback) callback({ success: false, error });
      return null;
    }
    const request_id = `get_improvement_info_${Date.now()}_${Math.random()
      .toString(36)
      .substr(2, 9)}`;
    if (callback && typeof callback === "function") {
      this.pendingCallbacks.set(request_id, callback);
    }
    this.socket.send(
      JSON.stringify({
        type: "get-company-improvement-info",
        company_id: companyId,
        request_id: request_id,
      })
    );
    return request_id;
  }

  /**
   * Get single company details
   * @param {number} companyId - Company ID
   * @param {Function} callback - Callback function
   * @returns {string} Request ID
   */
  get_company(companyId, callback = null) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      const error = "WebSocket is not connected";
      this.gameState.setError(error);
      if (callback) callback({ success: false, error });
      return null;
    }
    const request_id = `get_company_${Date.now()}_${Math.random()
      .toString(36)
      .substr(2, 9)}`;
    if (callback && typeof callback === "function") {
      this.pendingCallbacks.set(request_id, callback);
    }
    this.socket.send(
      JSON.stringify({
        type: "get-company",
        company_id: companyId,
        request_id: request_id,
      })
    );
    return request_id;
  }

  /**
   * Fetch all data for current user's company (comprehensive)
   * Includes: company details, factories, improvement info, cell info
   */
  fetchCurrentCompanyData() {
    if (!this.gameState.hasCompany) {
      console.warn('[WS] Cannot fetch company data: user has no company');
      return;
    }

    const companyId = this.gameState.state.currentUser.company_id;
    
    // Fetch all company-related data
    this.get_company(companyId);
    this.get_factories(companyId);
    this.get_company_improvement_info(companyId);
    this.get_company_cell_info(companyId);
    
    console.log('[WS] Fetching comprehensive company data for company:', companyId);
  }

  // ==================== UTILITY METHODS ====================

  /**
   * Initialize session after joining - fetches all necessary data
   */
  initializeSession() {
    console.log('[WS] Initializing session data...');
    
    // Start with session and map
    this.get_session((response) => {
      if (response.success) {
        // Load map to DOM after session data is loaded
        setTimeout(() => this.loadMapToDOM(), 100);
      }
    });
    
    // Fetch all game state
    this.fetchAllGameData();
    
    // If user has a company, fetch company-specific data
    if (this.gameState.hasCompany) {
      this.fetchCurrentCompanyData();
    }
    
    // Start polling for updates
    this.startPolling();
  }

  // Clean disconnect
  disconnect() {
    this.isManualDisconnect = true;
    this.stopPolling();
    
    // Clear reconnection interval
    if (this.reconnectInterval) {
      clearInterval(this.reconnectInterval);
      this.reconnectInterval = null;
    }
    
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    this.gameState.setConnected(false);
    console.log('[WS] Disconnected');
  }

  // Leave current session
  leaveSession() {
    this.stopPolling();
    this.gameState.clearSession();
    
    // Clear stored session when explicitly leaving
    this.clearStoredSession();
    
    console.log('[WS] Left session');
  }
}