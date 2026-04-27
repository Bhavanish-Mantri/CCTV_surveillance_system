/* main.js — shared utilities & live clock */

// ── Toast notifications ──
function showToast(message, type = 'info', duration = 4000) {
  let container = document.getElementById('toastContainer');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    container.id = 'toastContainer';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(120%)';
    toast.style.transition = '0.3s ease';
    setTimeout(() => toast.remove(), 350);
  }, duration);
}

// ── Live clock in top bar ──
function updateClock() {
  const now = new Date();
  const timeEl = document.getElementById('topbarTime');
  const dateEl = document.getElementById('topbarDate');
  if (timeEl) {
    timeEl.textContent = now.toLocaleTimeString('en-US', {
      hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true
    });
  }
  if (dateEl) {
    dateEl.textContent = now.toLocaleDateString('en-US', {
      weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'
    });
  }
}
updateClock();
setInterval(updateClock, 1000);

// ── System status polling ──
async function updateSystemStatus() {
  try {
    const r = await fetch('/api/processing_status');
    const d = await r.json();
    const running = d.data?.running;
    const dot  = document.getElementById('systemStatus');
    const text = document.getElementById('statusText');
    if (dot && text) {
      if (running) {
        dot.style.background = '#ff9f0a';
        dot.style.boxShadow  = '0 0 8px #ff9f0a';
        text.textContent = 'Processing…';
      } else {
        dot.style.background = '#34c759';
        dot.style.boxShadow  = '0 0 8px #34c759';
        text.textContent = 'System Ready';
      }
    }
  } catch(e) {}
}

setInterval(updateSystemStatus, 3000);
updateSystemStatus();
