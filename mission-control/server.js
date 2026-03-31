const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const { exec } = require('child_process');
const path = require('path');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

const PORT = 8080;
const HOME = process.env.HOME || '/data/data/com.termux/files/home';

// Serve static files
app.use(express.static(path.join(__dirname, 'public')));
app.use(express.json());

// Helper to run shell commands
function runCommand(cmd, timeout = 30000) {
  return new Promise((resolve, reject) => {
    exec(cmd, { timeout, cwd: HOME }, (error, stdout, stderr) => {
      if (error) {
        reject({ error: error.message, stderr });
      } else {
        resolve(stdout.trim());
      }
    });
  });
}

// ============== REST API ==============

// Get system status
app.get('/api/status', async (req, res) => {
  try {
    const battery = await runCommand('bash ~/phone_control.sh battery 2>/dev/null || echo "N/A"');
    const felixStatus = await runCommand('bash ~/.openclaw/workspace/felix status 2>/dev/null || echo "stopped"');
    const uptime = await runCommand('uptime -p 2>/dev/null || uptime');
    
    res.json({
      battery,
      felix: felixStatus,
      uptime,
      timestamp: new Date().toISOString()
    });
  } catch (e) {
    res.status(500).json({ error: e.error || e.message });
  }
});

// Get IG positions
app.get('/api/positions', async (req, res) => {
  try {
    const output = await runCommand('bash ~/.trading/ig_api.sh positions 2>&1');
    try {
      const data = JSON.parse(output);
      res.json(data);
    } catch {
      res.json({ raw: output, error: 'Parse error' });
    }
  } catch (e) {
    res.status(500).json({ error: e.error || e.message, raw: e.stderr });
  }
});

// Get account info
app.get('/api/account', async (req, res) => {
  try {
    const output = await runCommand('bash ~/.trading/ig_api.sh account 2>&1');
    try {
      const data = JSON.parse(output);
      res.json(data);
    } catch {
      res.json({ raw: output });
    }
  } catch (e) {
    res.status(500).json({ error: e.error || e.message });
  }
});

// Get working orders (pending limits)
app.get('/api/workingorders', async (req, res) => {
  try {
    const output = await runCommand('bash ~/.trading/ig_api.sh workingorders 2>&1');
    try {
      const data = JSON.parse(output);
      res.json(data);
    } catch {
      res.json({ raw: output });
    }
  } catch (e) {
    res.status(500).json({ error: e.error || e.message });
  }
});

// Get recent logs
app.get('/api/logs/:type?', async (req, res) => {
  const type = req.params.type || 'felix';
  let cmd;
  
  switch(type) {
    case 'trades':
      cmd = 'tail -50 ~/.trading/data/trades.jsonl 2>/dev/null || echo "No trades"';
      break;
    case 'signals':
      cmd = 'tail -50 ~/.trading/data/signals.jsonl 2>/dev/null || echo "No signals"';
      break;
    case 'errors':
      cmd = 'tail -50 ~/.trading/data/rejections.jsonl 2>/dev/null || echo "No errors"';
      break;
    default:
      cmd = 'tail -50 ~/.trading/logs/felix.log 2>/dev/null || echo "No logs"';
  }
  
  try {
    const output = await runCommand(cmd);
    res.json({ logs: output.split('\n').filter(l => l.trim()) });
  } catch (e) {
    res.status(500).json({ error: e.error || e.message });
  }
});

// Open position
app.post('/api/trade', async (req, res) => {
  const { epic, direction, size, orderType = 'MARKET', level } = req.body;
  
  if (!epic || !direction || !size) {
    return res.status(400).json({ error: 'Missing required fields: epic, direction, size' });
  }
  
  let cmd;
  if (orderType === 'LIMIT' && level) {
    cmd = `bash ~/.trading/ig_api.sh order ${epic} ${direction} ${size} LIMIT ${level}`;
  } else {
    cmd = `bash ~/.trading/ig_api.sh order ${epic} ${direction} ${size}`;
  }
  
  try {
    const output = await runCommand(cmd, 60000);
    try {
      const data = JSON.parse(output);
      res.json({ success: true, data });
    } catch {
      res.json({ success: true, raw: output });
    }
    // Broadcast update to all clients
    broadcast({ type: 'trade_executed', epic, direction, size, timestamp: Date.now() });
  } catch (e) {
    res.status(500).json({ error: e.error || e.message, raw: e.stderr });
  }
});

// Close position
app.post('/api/close', async (req, res) => {
  const { epic, direction, size } = req.body;
  
  if (!epic || !direction || !size) {
    return res.status(400).json({ error: 'Missing required fields' });
  }
  
  const cmd = `bash ~/.trading/ig_api.sh close ${epic} ${direction} ${size}`;
  
  try {
    const output = await runCommand(cmd, 60000);
    try {
      const data = JSON.parse(output);
      res.json({ success: true, data });
    } catch {
      res.json({ success: true, raw: output });
    }
    broadcast({ type: 'position_closed', epic, direction, size, timestamp: Date.now() });
  } catch (e) {
    res.status(500).json({ error: e.error || e.message, raw: e.stderr });
  }
});

// Cancel working order
app.post('/api/cancel-order', async (req, res) => {
  const { dealId } = req.body;
  
  if (!dealId) {
    return res.status(400).json({ error: 'Missing dealId' });
  }
  
  const cmd = `bash ~/.trading/ig_api.sh cancel-order ${dealId}`;
  
  try {
    const output = await runCommand(cmd, 30000);
    res.json({ success: true, raw: output });
    broadcast({ type: 'order_cancelled', dealId, timestamp: Date.now() });
  } catch (e) {
    res.status(500).json({ error: e.error || e.message });
  }
});

// Felix control
app.post('/api/felix/:action', async (req, res) => {
  const action = req.params.action;
  let cmd;
  
  switch(action) {
    case 'start':
      cmd = 'bash ~/.openclaw/workspace/felix start';
      break;
    case 'stop':
      cmd = 'bash ~/.openclaw/workspace/felix stop';
      break;
    case 'restart':
      cmd = 'bash ~/.openclaw/workspace/felix restart';
      break;
    case 'status':
      cmd = 'bash ~/.openclaw/workspace/felix status';
      break;
    default:
      return res.status(400).json({ error: 'Unknown action' });
  }
  
  try {
    const output = await runCommand(cmd, 10000);
    res.json({ success: true, action, output });
    broadcast({ type: 'felix_action', action, timestamp: Date.now() });
  } catch (e) {
    res.status(500).json({ error: e.error || e.message });
  }
});

// ============== WEBSOCKET ==============

const clients = new Set();

function broadcast(data) {
  const msg = JSON.stringify(data);
  clients.forEach(ws => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(msg);
    }
  });
}

wss.on('connection', (ws) => {
  clients.add(ws);
  console.log('Client connected, total:', clients.size);
  
  ws.send(JSON.stringify({ type: 'connected', timestamp: Date.now() }));
  
  ws.on('close', () => {
    clients.delete(ws);
    console.log('Client disconnected, total:', clients.size);
  });
  
  ws.on('message', async (message) => {
    try {
      const data = JSON.parse(message);
      
      if (data.type === 'ping') {
        ws.send(JSON.stringify({ type: 'pong' }));
      }
      
      if (data.type === 'request_update') {
        // Client requests specific update
        const positions = await runCommand('bash ~/.trading/ig_api.sh positions 2>&1').catch(() => '{}');
        ws.send(JSON.stringify({ type: 'positions_update', data: positions }));
      }
    } catch (e) {
      console.error('WS message error:', e);
    }
  });
});

// Background data broadcaster (every 5 seconds)
let lastPositions = '';
setInterval(async () => {
  try {
    const positions = await runCommand('bash ~/.trading/ig_api.sh positions 2>&1').catch(() => null);
    if (positions && positions !== lastPositions) {
      lastPositions = positions;
      broadcast({ type: 'positions_update', data: positions, timestamp: Date.now() });
    }
    
    // Also broadcast account update
    const account = await runCommand('bash ~/.trading/ig_api.sh account 2>&1').catch(() => null);
    if (account) {
      broadcast({ type: 'account_update', data: account, timestamp: Date.now() });
    }
  } catch (e) {
    // Silent fail
  }
}, 5000);

// ============== START ==============

server.listen(PORT, '0.0.0.0', () => {
  console.log(`🚀 Mission Control running on http://0.0.0.0:${PORT}`);
  console.log(`📱 Access from local network at http://<phone-ip>:${PORT}`);
});
