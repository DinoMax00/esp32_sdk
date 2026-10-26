import { displayState } from './state.mjs';

const connection = document.getElementById('connection');
const label = document.getElementById('label');
const title = document.getElementById('title');
const detail = document.getElementById('detail');
const fullscreen = document.getElementById('fullscreen');
const theme = document.querySelector('meta[name="theme-color"]');

const copy = {
  clear: ['开发板已连接', '未接触', '安全', '铁环与铁丝已分开'],
  touch: ['开发板已连接', '已接触', '碰到啦！', '移开铁环后，屏幕恢复绿色'],
  offline: ['开发板未连接', '检测已暂停', '等待连接', '请检查 USB 连接，连接恢复后会自动继续'],
};

function render(state) {
  // Avoid repeatedly announcing unchanged heartbeat messages to screen readers.
  if (document.body.dataset.state === state && connection.textContent === copy[state][0]) return;
  document.body.dataset.state = state;
  [connection.textContent, label.textContent, title.textContent, detail.textContent] = copy[state];
  theme.content = state === 'touch' ? '#e53136' : '#35dc83';
}

const events = new EventSource('/events');
events.onmessage = (event) => {
  try { render(displayState(JSON.parse(event.data))); }
  catch { render('offline'); }
};
events.onerror = () => render('offline');
window.addEventListener('pagehide', () => events.close());

async function toggleFullscreen() {
  try {
    if (document.fullscreenElement) await document.exitFullscreen();
    else if (document.documentElement.requestFullscreen) await document.documentElement.requestFullscreen();
    else fullscreen.textContent = '请使用浏览器全屏';
  } catch { fullscreen.textContent = '请使用浏览器全屏'; }
}
fullscreen.addEventListener('click', toggleFullscreen);
document.addEventListener('fullscreenchange', () => {
  fullscreen.textContent = document.fullscreenElement ? '退出全屏 ↙' : '进入全屏 ↗';
});
document.addEventListener('keydown', (event) => {
  if (event.key.toLowerCase() === 'f' && !event.metaKey && !event.ctrlKey && !event.altKey) {
    event.preventDefault();
    toggleFullscreen();
  }
});
