import { GameState } from './GameState.js';

export class WebSocketManager {
  constructor(url, consoleObj) {
    this.url = url;
    this.socket = null;
    this.console = consoleObj;
    
    // Initialize GameState
    this.gameState = new GameState();
    
    this.pendingCallbacks = new Map();
    this._pollInterval = null;
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

  get_id() {
    return `web_${Date.now()}`;
  }

  connect() {
    const client_id = this.get_id();
    const wsUrl = `${this.url}?client_id=${client_id}`;
    
    this.gameState.setConnecting(true);
    this.socket = new WebSocket(wsUrl);
    
    this.socket.onopen = () => {
      console.log('[WS] Connected to server');
      this.gameState.setConnected(true);
      this.gameState.setError(null);
    };
    
    this.socket.onmessage = (event) => this.onmessage(event);

    this.socket.onclose = () => {
      console.log('[WS] Disconnected from server');
      this.gameState.setConnected(false);
      this.gameState.setConnecting(false);
    };
    
    this.socket.onerror = (error) => {
      console.error('[WS] WebSocket error:', error);
      this.gameState.setError('WebSocket connection error');
      this.gameState.setConnected(false);
      this.gameState.setConnecting(false);
    };
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

  get_session(callback = null) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      const error = "WebSocket is not connected";
      this.gameState.setError(error);
      if (callback) callback({ success: false, error });
      return null;
    }

    const request_id = `get_session_${Date.now()}_${Math.random()
      .toString(36)
      .substr(2, 9)}`;
    if (callback && typeof callback === "function") {
      this.pendingCallbacks.set(request_id, callback);
    }
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

    const request_id = `get_session_event_${Date.now()}_${Math.random()
      .toString(36)
      .substr(2, 9)}`;
    if (callback && typeof callback === "function") {
      this.pendingCallbacks.set(request_id, callback);
    }
    this.socket.send(
      JSON.stringify({
        type: "get-session-event",
        session_id: this.gameState.state.session.id,
        request_id: request_id,
      })
    );
    return request_id;
  }

  get_companies(callback = null) {
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
    this.socket.send(
      JSON.stringify({
        type: "get-companies",
        session_id: this.gameState.state.session.id || undefined,
        request_id: request_id,
      })
    );
    return request_id;
  }

  get_users(callback = null) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      const error = "WebSocket is not connected";
      this.gameState.setError(error);
      if (callback) callback({ success: false, error });
      return null;
    }
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

  get_factories(company_id, callback = null) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      const error = "WebSocket is not connected";
      this.gameState.setError(error);
      if (callback) callback({ success: false, error });
      return null;
    }
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

  get_exchanges(callback = null) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      const error = "WebSocket is not connected";
      this.gameState.setError(error);
      if (callback) callback({ success: false, error });
      return null;
    }
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

  get_all_item_prices(callback = null) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      const error = "WebSocket is not connected";
      this.gameState.setError(error);
      if (callback) callback({ success: false, error });
      return null;
    }
    const request_id = `get_all_item_prices_${Date.now()}_${Math.random()
      .toString(36)
      .substr(2, 9)}`;
    if (callback && typeof callback === "function") {
      this.pendingCallbacks.set(request_id, callback);
    }
    this.socket.send(
      JSON.stringify({
        type: "get-all-item-prices",
        session_id: this.gameState.state.session.id || undefined,
        request_id: request_id,
      })
    );
    return request_id;
  }

  get_cities(callback = null) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      const error = "WebSocket is not connected";
      this.gameState.setError(error);
      if (callback) callback({ success: false, error });
      return null;
    }
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

  get_city(cityId, callback = null) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      const error = "WebSocket is not connected";
      this.gameState.setError(error);
      if (callback) callback({ success: false, error });
      return null;
    }
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

  get_contracts(callback = null) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      const error = "WebSocket is not connected";
      this.gameState.setError(error);
      if (callback) callback({ success: false, error });
      return null;
    }
    const request_id = `get_contracts_${Date.now()}_${Math.random()
      .toString(36)
      .substr(2, 9)}`;
    if (callback && typeof callback === "function") {
      this.pendingCallbacks.set(request_id, callback);
    }
    this.socket.send(
      JSON.stringify({
        type: "get-contracts",
        session_id: this.gameState.state.session.id || undefined,
        request_id: request_id,
      })
    );
    return request_id;
  }

  get_contract(contractId, callback = null) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      const error = "WebSocket is not connected";
      this.gameState.setError(error);
      if (callback) callback({ success: false, error });
      return null;
    }
    const request_id = `get_contract_${Date.now()}_${Math.random()
      .toString(36)
      .substr(2, 9)}`;
    if (callback && typeof callback === "function") {
      this.pendingCallbacks.set(request_id, callback);
    }
    this.socket.send(
      JSON.stringify({
        type: "get-contract",
        id: contractId,
        request_id: request_id,
      })
    );
    return request_id;
  }

  get_time_to_next_stage(callback = null) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      const error = "WebSocket is not connected";
      this.gameState.setError(error);
      if (callback) callback({ success: false, error });
      return null;
    }
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

  startPolling(intervalMs = 5000) {
    this.stopPolling();
    
    // Initial comprehensive fetch
    this.fetchAllGameData();
    
    this._pollInterval = setInterval(() => {
      this.fetchAllGameData();
    }, intervalMs);
    
    console.log('[WS] Polling started');
  }

  /**
   * Fetch all necessary game data in the correct order
   */
  fetchAllGameData() {
    // 1. Session state and map (includes time_to_next_stage)
    this.get_session();
    
    // 2. Explicitly fetch time to ensure it's always fresh
    this.get_time_to_next_stage();
    
    // 3. Event data
    this.get_session_event();
    
    // 4. Companies and their users
    this.get_companies();
    this.get_users();
    
    // 5. Cities
    this.get_cities();
    
    // 6. Contracts
    this.get_contracts();
    
    // 7. Exchange data
    this.get_exchanges();
    
    // 8. Item prices
    this.get_all_item_prices();
    
    // Note: Factories are fetched per company when needed
    // Events, contracts, winners are handled via broadcasts
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
      } else if (message.request_id.startsWith("get_contracts_")) {
        this.handleContractsResponse(message);
      } else if (message.request_id.startsWith("get_contract_")) {
        this.handleContractResponse(message);
      } else if (message.request_id.startsWith("get_time_")) {
        this.handleTimeResponse(message);
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
      // Update game state with session data
      this.gameState.updateSession(message.data);
      
      // Update time to next stage if provided in session data
      if (message.data.time_to_next_stage !== undefined) {
        this.gameState.updateTimeToNextStage(message.data.time_to_next_stage);
      }
      
      // Load map if available
      if (message.data.cells && message.data.map_size) {
        this.loadMapToDOM();
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
    
    if (message.data && message.data.event !== undefined) {
      // Check if event has data
      const eventData = message.data.event;
      
      if (eventData && Object.keys(eventData).length > 0) {
        // Update event in game state
        console.log('[WS] Updating event:', eventData);
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
    
    if (message.data && message.data.prices) {
      // Update game state with prices object
      this.gameState.updateItemPrices(message.data.prices);
      
      if (callback) callback({ success: true, data: message.data.prices });
    } else {
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

  handleContractsResponse(message) {
    const requestId = message.request_id;
    const callback = this.pendingCallbacks.get(requestId);
    
    if (message.data) {
      let contractsData = [];
      
      if (Array.isArray(message.data)) {
        contractsData = message.data;
      } else if (Array.isArray(message.data.contracts)) {
        contractsData = message.data.contracts;
      }
      
      // Update game state
      this.gameState.updateContracts(contractsData);
      
      if (callback) callback({ success: true, data: contractsData });
    } else {
      if (callback) callback({ success: false, error: "No contracts data" });
    }
    
    if (callback) this.pendingCallbacks.delete(requestId);
  }

  handleContractResponse(message) {
    const requestId = message.request_id;
    const callback = this.pendingCallbacks.get(requestId);
    
    if (message.data) {
      // Update this specific contract in the contracts array
      const contractData = message.data;
      const existingIndex = this.gameState.state.contracts.findIndex(
        c => c.id === contractData.id
      );
      
      if (existingIndex >= 0) {
        this.gameState.state.contracts[existingIndex] = contractData;
      } else {
        this.gameState.state.contracts.push(contractData);
      }
      
      if (callback) callback({ success: true, data: contractData });
    } else {
      if (callback) callback({ success: false, error: message.error || "No contract data" });
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
    
    // Handle different broadcast types
    switch (message.type) {
      case 'api-create_company':
      case 'api-company_deleted':
      case 'api-user_added_to_company':
      case 'api-user_left_company':
      case 'api-company_set_position':
        // Refresh companies
        this.get_companies();
        break;
      
      case 'api-company_improvement_upgraded':
        // Add upgrade to recent upgrades list
        if (message.data) {
          this.gameState.addUpgrade(message.data);
        }
        // Refresh companies
        this.get_companies();
        break;
        
      case 'api-create_user':
      case 'api-update_user':
      case 'api-user_deleted':
        // Refresh users
        this.get_users();
        break;
        
      case 'api-update_session_stage':
        // Refresh session (includes time_to_next_stage)
        this.get_session();
        
        // Refresh event data (might have changed)
        this.get_session_event();

        // If stage changed, reload map
        if (message.data && message.data.new_stage) {
          this.loadMapToDOM();
        }
        break;
        
      case 'api-session_deleted':
        // Clear session if it's the current one
        if (message.data && message.data.session_id === this.gameState.state.session.id) {
          this.leaveSession();
        }
        break;
        
      case 'api-game_ended':
        // Handle game end with winners
        if (message.data && message.data.winners) {
          this.gameState.updateWinners(message.data.winners);
        }
        // Refresh session to get End stage
        this.get_session();
        break;
        
      case 'api-factory-start-complectation':
        // Refresh factories if we have a company
        if (this.gameState.hasCompany) {
          this.get_factories(this.gameState.state.currentUser.company_id);
        }
        break;
        
      case 'api-exchange_offer_created':
      case 'api-exchange_offer_updated':
      case 'api-exchange_offer_cancelled':
      case 'api-exchange_trade_completed':
        // Refresh exchanges
        this.get_exchanges();
        // Also refresh companies to update balances
        this.get_companies();
        break;
        
      case 'api-city-create':
      case 'api-city-delete':
        // Refresh cities list
        this.get_cities();
        break;
        
      case 'api-city-update-demands':
        // Update specific city demands
        if (message.data && message.data.city_id) {
          this.get_city(message.data.city_id);
        } else {
          this.get_cities();
        }
        break;
        
      case 'api-city-trade':
        // Refresh cities and companies after trade
        this.get_cities();
        this.get_companies();
        break;
        
      case 'api-contract_created':
      case 'api-contract_accepted':
      case 'api-contract_declined':
      case 'api-contract_cancelled':
      case 'api-contract_deleted':
        // Refresh contracts and companies
        this.get_contracts();
        this.get_companies();
        break;
      
      case 'api-event_generated':
        // Refresh event data when a new event is generated
        this.get_session_event();
        break;
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
        for (const company of companies) {
          if (company.cell_position) {
            // Parse cell_position format "x.y"
            const [colStr, rowStr] = company.cell_position.split('.');
            const col = parseInt(colStr, 10);
            const row = parseInt(rowStr, 10);
            
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
    this.stopPolling();
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
    console.log('[WS] Left session');
  }
}