import { API } from './api.js';

const LLM = window.__LLM__;
const $ = (id) => document.getElementById(id);
const BTN_BASE = LLM.btnBase;
const BTN = LLM.btnClasses;

const fmtGB = (mb) => mb == null ? '—' : (mb / 1024).toFixed(1) + ' GB';
const fmtBytes = (b) => b >= 2 ** 30 ? (b / 2 ** 30).toFixed(1) + ' GB' : b >= 2 ** 20 ? (b / 2 ** 20).toFixed(0) + ' MB' : (b / 2 ** 10).toFixed(0) + ' KB';
const pct = (part, total) => total > 0 ? Math.max(0, Math.min(100, (part / total) * 100)) : 0;
const stripAnsi = (s) => s.replace(/\x1b\[[0-9;]*m/g, '');

function setBtn(el, variant, label = null, disabled = false) {
  el.className = BTN_BASE + ' ' + BTN[variant];
  if (label != null) el.textContent = label;
  el.disabled = disabled;
}

// ── state ────────────────────────────────────────────────────────────
let svcDetail = '';
let svcState = 'idle';
let setupRunning = false;
let uninstallRunning = false;
let ready = false;
let logsPinned = true;
let logModal = null;
let confirmResolve = null;

// ── render fns (value-only) ──────────────────────────────────────────
function renderStatusPill(svc, srv) {
  const el = $('status-pill');
  let cls, text;
  if (svc.active === 'active' && srv.up) { cls = 'bg-emerald-500/10 text-emerald-400 ring-emerald-500/20'; text = 'all systems go'; }
  else if (svc.active === 'active' || srv.up) { cls = 'bg-amber-500/10 text-amber-400 ring-amber-500/20'; text = 'degraded'; }
  else { cls = 'bg-red-500/10 text-red-400 ring-red-500/20'; text = 'down'; }
  el.className = 'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ring-1 ring-inset ' + cls;
  $('status-pill-text').textContent = text;
}

function renderService(s) {
  const on = s.active === 'active';
  $('svc-dot').className = 'w-2 h-2 rounded-full shrink-0 ' + (on ? 'bg-emerald-500' : 'bg-zinc-600');
  $('svc-state').textContent = s.installed ? `${s.active} (${s.enabled})` : 'unit not installed';
  setBtn($('svc-toggle'), on ? 'secondary' : 'primary', on ? 'Stop' : 'Start', svcState === 'running');
}

function renderInstallToggle() {
  if (setupRunning) setBtn($('install-toggle'), 'danger-ghost', 'Stop install');
  else if (uninstallRunning) setBtn($('install-toggle'), 'danger-ghost', 'Uninstalling…', true);
  else if (ready) setBtn($('install-toggle'), 'danger-ghost', 'Uninstall');
  else setBtn($('install-toggle'), 'primary', 'Install');
}

function renderSystem(s) {
  $('sys-cpu').textContent = `${s.cpu_percent}%`;
  $('sys-cpu-bar').style.width = s.cpu_percent + '%';
  $('sys-load').textContent = s.load_avg ? `load ${s.load_avg.map((x) => x.toFixed(2)).join('  ')}` : '';
  $('sys-mem').textContent = `${s.mem_used_gb} / ${s.mem_total_gb} GB`;
  $('sys-mem-bar').style.width = s.mem_percent + '%';
  $('sys-swap').textContent = `${s.swap_used_gb} / ${s.swap_total_gb} GB`;
}

function renderGpus(gpus) {
  const cards = document.querySelectorAll('[data-gpu-card]');
  if ((gpus || []).length !== cards.length) { location.reload(); return; }
  (gpus || []).forEach((g) => {
    const i = g.index;
    const model = g.model_mem_mb || 0;
    const other = Math.max(0, (g.mem_used_mb || 0) - model);
    const util = g.util_percent != null ? g.util_percent : 0;
    $('gpu-' + i + '-meta').textContent = [g.temp_c != null ? g.temp_c + '°C' : '', g.power_w != null ? g.power_w.toFixed(0) + ' W' : ''].filter(Boolean).join(' · ');
    $('gpu-' + i + '-util-bar').style.width = util + '%';
    $('gpu-' + i + '-util-val').textContent = g.util_percent != null ? g.util_percent + '%' : '—';
    $('gpu-' + i + '-vram-model').style.width = pct(model, g.mem_total_mb) + '%';
    $('gpu-' + i + '-vram-other').style.width = pct(other, g.mem_total_mb) + '%';
    $('gpu-' + i + '-vram-val').textContent = (g.mem_used_mb / 1024).toFixed(1) + ' / ' + (g.mem_total_mb / 1024).toFixed(1) + ' GB';
    $('gpu-' + i + '-model-gb').textContent = fmtGB(model);
    $('gpu-' + i + '-other-gb').textContent = fmtGB(other);
    $('gpu-' + i + '-free-gb').textContent = fmtGB(Math.max(0, g.mem_total_mb - (g.mem_used_mb || 0)));
  });
}

function renderServer(s) {
  $('srv-dot').className = 'w-2 h-2 rounded-full ' + (s.up ? 'bg-emerald-500' : 'bg-zinc-600');
  $('srv-state').textContent = s.up ? 'up' : 'down';
  const c = s.configured || {};
  $('srv-url').textContent = s.url;
  $('srv-model').textContent = c.model || '—';
  $('srv-draft').textContent = c.draft || '—';
  $('srv-ctx').textContent = c.ctx_size ? `${c.ctx_size} / ${c.ngl ?? '—'}` : '—';
  $('srv-models').classList.toggle('hidden', !s.up);
  $('srv-down').classList.toggle('hidden', s.up);
}

function renderWeights(w) {
  const models = (w && w.models) || [];
  const cards = document.querySelectorAll('[data-wt-card]');
  const renderedFiles = document.querySelectorAll('.wt-file-size').length;
  const stateFiles = models.reduce((a, m) => a + ((m.files || []).length), 0);
  if (models.length !== cards.length || renderedFiles !== stateFiles) { location.reload(); return; }
  const total = models.reduce((a, m) => a + (m.total_bytes || 0), 0);
  $('wt-total').textContent = total ? fmtBytes(total) : '';
  models.forEach((m, i) => {
    $('wt-' + i + '-summary').textContent = m.found ? m.files.length + ' files · ' + fmtBytes(m.total_bytes) : 'not found';
    let j = 0;
    document.querySelectorAll('#wt-' + i + '-files .wt-file-size').forEach((el) => { el.textContent = fmtBytes(m.files[j++].size_bytes); });
  });
}

function renderSpeed(s) {
  const fmt = (v) => v != null ? v.toFixed(1) : '—';
  $('spd-prompt').textContent = fmt(s.prompt_tps);
  $('spd-predict').textContent = fmt(s.predict_tps);
  $('spd-prompt-avg').textContent = s.prompt_tps_avg != null ? s.prompt_tps_avg.toFixed(1) + ' t/s' : '—';
  $('spd-predict-avg').textContent = s.predict_tps_avg != null ? s.predict_tps_avg.toFixed(1) + ' t/s' : '—';
  const badge = $('spd-live-badge');
  if (s.live) { badge.textContent = 'live'; badge.className = 'ml-auto text-[10px] font-mono text-emerald-500'; }
  else { badge.textContent = ''; badge.className = 'ml-auto text-[10px] font-mono text-zinc-600'; }
}

function renderAgents(a) {
  $('ag-oc').textContent = a.opencode_installed ? (a.opencode_version || 'installed') : 'not installed';
  $('ag-provider').textContent = a.provider_configured ? 'configured' : 'not configured';
}

function renderInstance(i) {
  $('instance').textContent = `${i.path} [${i.mode}]`;
}

async function refresh() {
  try {
    const s = await API.state();
    renderInstance(s.instance);
    renderService(s.service);
    renderSystem(s.system);
    renderGpus(s.gpus);
    renderServer(s.server);
    renderWeights(s.weights);
    renderSpeed(s.speed);
    renderAgents(s.agents);
    renderStatusPill(s.service, s.server);
    ready = s.instance.built && s.service.installed;
    const [setupJob, uninstallJob] = await Promise.all([API.job('setup'), API.job('uninstall')]);
    setupRunning = setupJob.state === 'running';
    uninstallRunning = uninstallJob.state === 'running';
    renderInstallToggle();
    const logs = await API.logs(200);
    const el = $('logs');
    el.textContent = logs.lines.join('\n');
    if (logsPinned) el.scrollTop = el.scrollHeight;
    if (logModal) pollLogModal();
  } catch (e) { /* transient */ }
}

// ── Server config modal ──────────────────────────────────────────────
function openServerConfig() {
  const modal = $('srv-config-modal');
  modal.classList.remove('hidden');
  modal.classList.add('flex');
}

function closeServerConfig() {
  const modal = $('srv-config-modal');
  modal.classList.add('hidden');
  modal.classList.remove('flex');
}

async function saveServerConfig() {
  const inputs = $('srv-config-body').querySelectorAll('[data-idx]');
  const params = [];
  inputs.forEach((el) => {
    if (el.dataset.flag) {
      if (el.checked) params.push({ name: el.dataset.name, value: '', is_flag: true });
    } else {
      params.push({ name: el.dataset.name, value: el.value, is_flag: false });
    }
  });
  const btn = $('srv-config-save');
  btn.disabled = true;
  btn.textContent = 'Saving…';
  try {
    await API.saveServerParams(params);
    await API.restartServer();
    closeServerConfig();
    refresh();
  } catch (e) {
    alert(e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Save & Restart';
  }
}

// ── Reusable confirmation modal ──────────────────────────────────────
function openConfirm({ title, message, confirmLabel = 'Confirm', danger = false }) {
  return new Promise((resolve) => {
    confirmResolve = resolve;
    $('confirm-title').textContent = title;
    $('confirm-message').textContent = message;
    setBtn($('confirm-ok'), danger ? 'danger' : 'primary', confirmLabel);
    const icon = $('confirm-icon');
    icon.className = 'shrink-0 w-9 h-9 rounded-full flex items-center justify-center ' + (danger ? 'bg-red-500/10 text-red-400' : 'bg-sky-500/10 text-sky-400');
    $('confirm-icon-danger').classList.toggle('hidden', !danger);
    $('confirm-icon-info').classList.toggle('hidden', danger);
    const modal = $('confirm-modal');
    modal.classList.remove('hidden');
    modal.classList.add('flex');
    $('confirm-cancel').focus();
  });
}

function closeConfirm(result) {
  const modal = $('confirm-modal');
  modal.classList.add('hidden');
  modal.classList.remove('flex');
  const resolve = confirmResolve;
  confirmResolve = null;
  if (resolve) resolve(result);
}

// ── Reusable terminal log modal ──────────────────────────────────────
const logBadgeStyles = {
  running: 'bg-amber-500/10 text-amber-400 ring-amber-500/20',
  done: 'bg-emerald-500/10 text-emerald-400 ring-emerald-500/20',
  error: 'bg-red-500/10 text-red-400 ring-red-500/20',
  stopped: 'bg-sky-500/10 text-sky-400 ring-sky-500/20',
};

function setLogModalBadge(state) {
  const badge = $('log-modal-badge');
  if (!state || state === 'idle') { badge.classList.add('hidden'); return; }
  badge.textContent = state;
  badge.className = 'px-2 py-0.5 rounded-full text-[10px] font-mono ring-1 ring-inset ' + (logBadgeStyles[state] || 'bg-zinc-800/60 text-zinc-400 ring-zinc-700/60');
}

function openLogModal({ title, load, stopUrl = null }) {
  logModal = { load, stopUrl, follow: true, last: '' };
  $('log-modal-title').textContent = title;
  $('log-modal-body').textContent = '';
  setLogModalBadge(null);
  const modal = $('log-modal');
  modal.classList.remove('hidden');
  modal.classList.add('flex');
  pollLogModal();
}

function closeLogModal() {
  logModal = null;
  const modal = $('log-modal');
  modal.classList.add('hidden');
  modal.classList.remove('flex');
}

async function pollLogModal() {
  if (!logModal) return;
  try {
    const snap = await logModal.load();
    if (!logModal) return;
    const out = stripAnsi((snap.output || []).join('\n'));
    const body = $('log-modal-body');
    const pinned = body.scrollHeight - body.scrollTop - body.clientHeight < 40;
    body.textContent = out;
    if (logModal.follow && (pinned || out !== logModal.last)) body.scrollTop = body.scrollHeight;
    logModal.last = out;
    setLogModalBadge(snap.state);
    $('log-modal-stop').classList.toggle('hidden', !(logModal.stopUrl && snap.state === 'running'));
  } catch (e) { /* transient */ }
}

function openJobModal(which) {
  const titles = { setup: 'Install', opencode: 'Configure opencode', uninstall: 'Uninstall' };
  const stopUrl = which === 'uninstall' ? null : '/api/jobs/' + which + '/stop';
  openLogModal({ title: titles[which], load: () => API.job(which), stopUrl });
}

// ── actions (exposed to inline onclick) ──────────────────────────────
function svcToggle() {
  if (svcState === 'running') return;
  svcAction($('svc-toggle').textContent === 'Start' ? 'start' : 'stop');
}

async function svcAction(action) {
  svcState = 'running';
  svcDetail = '';
  openLogModal({
    title: `Service ${action}`,
    load: async () => ({ state: svcState, output: (svcDetail || '').split('\n') }),
  });
  try {
    const r = await API.service(action);
    svcDetail = r.detail || (r.ok ? 'ok' : 'failed');
    svcState = r.ok ? 'done' : 'error';
  } catch (e) {
    svcDetail = String(e.message || e);
    svcState = 'error';
  }
}

async function installToggle() {
  if (setupRunning) {
    await API.jobStop('setup');
    return;
  }
  if (uninstallRunning) return;
  if (ready) {
    const ok = await openConfirm({
      title: 'Uninstall the stack?',
      message: `- stops and removes the ${LLM.unit} systemd service
- kills any running llama-server process for this instance
- deletes llama.cpp/ (the build)
- removes the llama-server provider from opencode
(the opencode binary is kept)`,
      confirmLabel: 'Uninstall',
      danger: true,
    });
    if (!ok) return;
    await API.uninstall();
    openJobModal('uninstall');
    return;
  }
  await API.setup();
  openJobModal('setup');
}

async function opencodeSetup() {
  await API.opencodeSetup();
  openJobModal('opencode');
}

async function stopLogModalJob() {
  if (!logModal || !logModal.stopUrl) return;
  const btn = $('log-modal-stop');
  btn.disabled = true;
  await API.post(logModal.stopUrl);
  btn.disabled = false;
  pollLogModal();
}

function copyLogModal() {
  const text = $('log-modal-body').textContent;
  if (!text) return;
  navigator.clipboard.writeText(text).then(() => {
    const btn = $('log-modal-copy');
    btn.title = 'Copied';
    setTimeout(() => { btn.title = 'Copy logs'; }, 1500);
  });
}

// ── event wiring ─────────────────────────────────────────────────────
$('logs').addEventListener('scroll', () => {
  const el = $('logs');
  logsPinned = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
});

$('srv-config-modal').addEventListener('click', (e) => {
  if (e.target === $('srv-config-modal')) closeServerConfig();
});

$('confirm-cancel').addEventListener('click', () => closeConfirm(false));
$('confirm-ok').addEventListener('click', () => closeConfirm(true));
$('confirm-modal').addEventListener('click', (e) => {
  if (e.target === $('confirm-modal')) closeConfirm(false);
});

$('log-modal-body').addEventListener('scroll', () => {
  if (!logModal) return;
  const el = $('log-modal-body');
  logModal.follow = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
});

$('log-modal').addEventListener('click', (e) => {
  if (e.target === $('log-modal')) closeLogModal();
});

document.addEventListener('keydown', (e) => {
  if (e.key !== 'Escape') return;
  if (confirmResolve) closeConfirm(false);
  else if (logModal) closeLogModal();
});

// ── expose to inline onclick ─────────────────────────────────────────
window.svcToggle = svcToggle;
window.installToggle = installToggle;
window.opencodeSetup = opencodeSetup;
window.openServerConfig = openServerConfig;
window.closeServerConfig = closeServerConfig;
window.saveServerConfig = saveServerConfig;
window.stopLogModalJob = stopLogModalJob;
window.copyLogModal = copyLogModal;
window.closeLogModal = closeLogModal;

refresh();
setInterval(refresh, 2000);
