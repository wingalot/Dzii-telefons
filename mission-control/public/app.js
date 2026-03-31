// Mission Control Frontend
const WS_URL = `ws://${window.location.host}`;
const API_URL = '';

let ws = null;
let reconnectInterval = null;
let currentLogType = 'felix';

// DOM Elements
const wsStatus = document.getElementById('ws-status');
const felixStatus = document.getElementById('felix-status');
const battery = document.getElementById('battery');
const clock = document.getElementById('clock');

// Initialize
function init() {
    connectWebSocket();
    initTabs();
    initForms();
    initButtons();
    initLogControls();
    updateClock();
    setInterval(updateClock, 1000);
    
    // Initial data load
    loadAllData();
    
    // Periodic refresh (every 10 seconds)
    setInterval(loadAllData, 10000);
}

// WebSocket
function connectWebSocket() {
    ws = new WebSocket(WS_URL);
    
    ws.onopen = () => {
        console.log('WS connected');
        wsStatus.textContent = '● Online';
        wsStatus.classList.remove('disconnected');
        wsStatus.classList.add('connected');
        
        if (reconnectInterval) {
            clearInterval(reconnectInterval);
            reconnectInterval = null;
        }
    };
    
    ws.onclose = () => {
        console.log('WS disconnected');
        wsStatus.textContent = '● Offline';
        wsStatus.classList.remove('connected');
        wsStatus.classList.add('disconnected');
        
        // Reconnect after 3 seconds
        if (!reconnectInterval) {
            reconnectInterval = setInterval(connectWebSocket, 3000);
        }
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };
    
    ws.onerror = (err) => {
        console.error('WS error:', err);
    };
}

function handleWebSocketMessage(data) {
    switch(data.type) {
        case 'connected':
            console.log('Connected to server');
            break;
            
        case 'positions_update':
            updatePositions(data.data);
            break;
            
        case 'account_update':
            updateAccount(data.data);
            break;
            
        case 'trade_executed':
            showNotification('Trade executed', `Order placed for ${data.epic}`);
            loadPositions();
            break;
            
        case 'position_closed':
            showNotification('Position closed', `Closed ${data.epic}`);
            loadPositions();
            break;
            
        case 'order_cancelled':
            showNotification('Order cancelled', `Order ${data.dealId} cancelled`);
            loadWorkingOrders();
            break;
            
        case 'felix_action':
            showNotification('Felix', `Action: ${data.action}`);
            loadStatus();
            break;
    }
}

// API Calls
async function apiGet(endpoint) {
    try {
        const res = await fetch(`${API_URL}/api${endpoint}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    } catch (e) {
        console.error('API error:', e);
        return { error: e.message };
    }
}

async function apiPost(endpoint, body) {
    try {
        const res = await fetch(`${API_URL}/api${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    } catch (e) {
        console.error('API error:', e);
        return { error: e.message };
    }
}

// Data Loading
async function loadAllData() {
    await Promise.all([
        loadStatus(),
        loadPositions(),
        loadAccount(),
        loadWorkingOrders(),
        loadSignals(),
        loadLogs()
    ]);
}

async function loadStatus() {
    const data = await apiGet('/status');
    if (data.error) return;
    
    felixStatus.textContent = `Felix: ${data.felix || 'unknown'}`;
    battery.textContent = data.battery || 'Batt: --';
    document.getElementById('uptime').textContent = data.uptime || '--';
}

async function loadPositions() {
    const data = await apiGet('/positions');
    updatePositions(data);
}

function updatePositions(data) {
    const container = document.getElementById('positions-list');
    const closeContainer = document.getElementById('close-positions');
    const countEl = document.getElementById('pos-count');
    
    if (data.error || !data.positions) {
        container.innerHTML = `<div class="empty">${data.error || 'No positions'}</div>`;
        closeContainer.innerHTML = `<div class="empty">No positions</div>`;
        countEl.textContent = '0';
        updatePnL([]);
        return;
    }
    
    const positions = data.positions;
    countEl.textContent = positions.length;
    
    if (positions.length === 0) {
        container.innerHTML = `<div class="empty">No open positions</div>`;
        closeContainer.innerHTML = `<div class="empty">No positions to close</div>`;
        updatePnL([]);
        return;
    }
    
    let html = '';
    let closeHtml = '';
    let totalPL = 0;
    
    positions.forEach(pos => {
        const isBuy = pos.direction === 'BUY';
        const pl = parseFloat(pos.upl || 0);
        totalPL += pl;
        const plClass = pl >= 0 ? 'positive' : 'negative';
        const plSign = pl >= 0 ? '+' : '';
        
        html += `
            <div class="position ${isBuy ? 'buy' : 'sell'}">
                <div class="position-pair">${pos.market?.instrumentName || pos.epic}</div>
                <span class="position-dir ${isBuy ? 'buy' : 'sell'}">${pos.direction}</span>
                <span class="position-size">${pos.size} lots</span>
                <span class="position-pl ${plClass}">${plSign}${pl.toFixed(2)}</span>
                <span>@ ${pos.level || 'unknown'}</span>
            </div>
        `;
        
        closeHtml += `
            <div class="close-item">
                <div class="close-item-info">
                    <span><strong>${pos.market?.instrumentName || pos.epic}</strong></span>
                    <span class="position-dir ${isBuy ? 'buy' : 'sell'}">${pos.direction}</span>
                    <span>${pos.size} lots</span>
                </div>
                <button class="btn btn-danger btn-close-pos" 
                        data-epic="${pos.epic}" 
                        data-dir="${isBuy ? 'SELL' : 'BUY'}" 
                        data-size="${pos.size}"
                        onclick="closePosition('${pos.epic}', '${isBuy ? 'SELL' : 'BUY'}', ${pos.size})">
                    Close
                </button>
            </div>
        `;
    });
    
    container.innerHTML = html;
    closeContainer.innerHTML = closeHtml;
    updatePnL(positions, totalPL);
}

function updatePnL(positions, totalPL) {
    const container = document.getElementById('pnl-summary');
    
    if (positions.length === 0) {
        container.innerHTML = `<div class="empty">No open positions</div>`;
        return;
    }
    
    const plClass = totalPL >= 0 ? 'positive' : 'negative';
    const plSign = totalPL >= 0 ? '+' : '';
    
    container.innerHTML = `
        <div class="pnl-item">
            <span>Total Unrealized P&L</span>
            <span class="pnl-value ${plClass}">${plSign}${totalPL.toFixed(2)}</span>
        </div>
        <div class="pnl-item">
            <span>Open Positions</span>
            <span class="pnl-value">${positions.length}</span>
        </div>
    `;
}

async function loadAccount() {
    const data = await apiGet('/account');
    updateAccount(data);
}

function updateAccount(data) {
    const container = document.getElementById('account-info');
    
    if (data.error || !data.accounts) {
        container.innerHTML = `<div class="empty">Account data unavailable</div>`;
        return;
    }
    
    const acc = data.accounts[0] || {};
    const balance = parseFloat(acc.balance || 0);
    const available = parseFloat(acc.available || 0);
    const pnl = parseFloat(acc.profitLoss || 0);
    
    container.innerHTML = `
        <div class="account-item">
            <label>Balance</label>
            <value>${balance.toFixed(2)}</value>
        </div>
        <div class="account-item">
            <label>Available</label>
            <value>${available.toFixed(2)}</value>
        </div>
        <div class="account-item">
            <label>P&L</label>
            <value class="${pnl >= 0 ? 'positive' : 'negative'}">${pnl >= 0 ? '+' : ''}${pnl.toFixed(2)}</value>
        </div>
        <div class="account-item">
            <label>Margin Used</label>
            <value>${((balance - available) / balance * 100).toFixed(1)}%</value>
        </div>
    `;
}

async function loadWorkingOrders() {
    const data = await apiGet('/workingorders');
    const container = document.getElementById('working-orders');
    
    if (data.error || !data.workingOrders) {
        container.innerHTML = `<div class="empty">${data.error || 'No pending orders'}</div>`;
        return;
    }
    
    const orders = data.workingOrders;
    
    if (orders.length === 0) {
        container.innerHTML = `<div class="empty">No pending orders</div>`;
        return;
    }
    
    let html = '';
    orders.forEach(order => {
        html += `
            <div class="order">
                <span class="order-epic">${order.epic}</span>
                <span class="position-dir ${order.direction === 'BUY' ? 'buy' : 'sell'}">${order.direction}</span>
                <span class="order-type">${order.orderType}</span>
                <span class="order-level">@ ${order.level}</span>
                <span>${order.size} lots</span>
                <button class="btn btn-danger" onclick="cancelOrder('${order.dealId}')">Cancel</button>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

async function loadSignals() {
    const data = await apiGet('/logs/signals');
    const container = document.getElementById('signals-list');
    
    if (data.error || !data.logs) {
        container.innerHTML = `<div class="empty">No signals</div>`;
        return;
    }
    
    const logs = data.logs.slice(-5).reverse();
    
    if (logs.length === 0) {
        container.innerHTML = `<div class="empty">No recent signals</div>`;
        return;
    }
    
    container.innerHTML = logs.map(log => {
        try {
            const s = JSON.parse(log);
            return `<div class="list-item">${s.pair || s.symbol || 'Unknown'} ${s.direction || ''} @ ${s.price || 'market'}</div>`;
        } catch {
            return `<div class="list-item">${log}</div>`;
        }
    }).join('');
}

async function loadLogs() {
    const data = await apiGet(`/logs/${currentLogType}`);
    const container = document.getElementById('log-content');
    
    if (data.error || !data.logs) {
        container.textContent = data.error || 'No logs';
        return;
    }
    
    container.textContent = data.logs.join('\n') || 'No logs';
    container.scrollTop = container.scrollHeight;
}

// Actions
async function closePosition(epic, direction, size) {
    if (!confirm(`Close ${epic} ${direction} ${size} lots?`)) return;
    
    const result = await apiPost('/close', { epic, direction, size });
    showResult('trade-result', result);
    loadPositions();
}

async function cancelOrder(dealId) {
    if (!confirm(`Cancel order ${dealId}?`)) return;
    
    const result = await apiPost('/cancel-order', { dealId });
    if (result.success) {
        showNotification('Success', 'Order cancelled');
    } else {
        showNotification('Error', result.error || 'Failed to cancel');
    }
    loadWorkingOrders();
}

// UI Helpers
function initTabs() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            btn.classList.add('active');
            document.getElementById(btn.dataset.tab).classList.add('active');
        });
    });
}

function initForms() {
    // Trade form
    const tradeForm = document.getElementById('trade-form');
    
    // Direction buttons
    document.querySelectorAll('.dir-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.dir-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById('trade-dir').value = btn.dataset.dir;
        });
    });
    
    // Order type toggle
    document.getElementById('trade-type').addEventListener('change', (e) => {
        const limitGroup = document.querySelector('.limit-price');
        limitGroup.style.display = e.target.value === 'LIMIT' ? 'block' : 'none';
    });
    
    // Submit
    tradeForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const epic = document.getElementById('trade-pair').value;
        const direction = document.getElementById('trade-dir').value;
        const size = parseFloat(document.getElementById('trade-size').value);
        const orderType = document.getElementById('trade-type').value;
        const level = document.getElementById('trade-price').value;
        
        if (!direction) {
            showResult('trade-result', { error: 'Select BUY or SELL' });
            return;
        }
        
        const result = await apiPost('/trade', { 
            epic, direction, size, orderType, 
            ...(orderType === 'LIMIT' && level ? { level: parseFloat(level) } : {})
        });
        
        showResult('trade-result', result);
        if (result.success) {
            tradeForm.reset();
            document.querySelectorAll('.dir-btn').forEach(b => b.classList.remove('active'));
            loadPositions();
            loadWorkingOrders();
        }
    });
}

function initButtons() {
    document.getElementById('felix-start').addEventListener('click', () => felixAction('start'));
    document.getElementById('felix-stop').addEventListener('click', () => felixAction('stop'));
    document.getElementById('felix-restart').addEventListener('click', () => felixAction('restart'));
    document.getElementById('felix-status').addEventListener('click', () => felixAction('status'));
}

function initLogControls() {
    document.querySelectorAll('.log-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.log-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentLogType = btn.dataset.log;
            loadLogs();
        });
    });
}

async function felixAction(action) {
    const output = document.getElementById('felix-output');
    output.textContent = 'Executing...';
    
    const result = await apiPost(`/felix/${action}`, {});
    output.textContent = result.output || result.error || 'Done';
    
    loadStatus();
}

function showResult(id, result) {
    const el = document.getElementById(id);
    if (result.error) {
        el.innerHTML = `<div class="result error">Error: ${result.error}</div>`;
    } else if (result.success) {
        el.innerHTML = `<div class="result success">Success! ${result.data?.dealStatus || 'Order placed'}</div>`;
    }
    setTimeout(() => el.innerHTML = '', 5000);
}

function showNotification(title, message) {
    if ('Notification' in window && Notification.permission === 'granted') {
        new Notification(title, { body: message });
    }
    console.log(`[${title}] ${message}`);
}

function updateClock() {
    const now = new Date();
    clock.textContent = now.toLocaleTimeString('lv-LV');
}

// Request notification permission
if ('Notification' in window) {
    Notification.requestPermission();
}

// Start
init();
