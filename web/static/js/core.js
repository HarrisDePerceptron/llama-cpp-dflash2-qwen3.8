import { API } from './api.js';

export { API };

export const $ = (id) => document.getElementById(id);
export const BTN_BASE = 'inline-flex items-center justify-center gap-1.5 whitespace-nowrap transition cursor-pointer';
export const BTN = {
  'primary': 'px-3.5 py-1.5 text-sm font-semibold rounded-lg gemini-gradient-135 text-zinc-950 hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed',
  'secondary': 'px-3.5 py-1.5 text-sm font-medium rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 disabled:opacity-50 disabled:cursor-not-allowed',
  'danger': 'px-3.5 py-1.5 text-sm font-semibold rounded-lg bg-red-600 hover:bg-red-500 text-white disabled:opacity-50 disabled:cursor-not-allowed',
  'danger-ghost': 'px-3.5 py-1.5 text-sm font-medium rounded-lg text-red-400 ring-1 ring-inset ring-red-500/30 hover:bg-red-500/10 disabled:opacity-50 disabled:cursor-not-allowed',
  'ghost': 'px-3 py-1.5 rounded-lg text-sm text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors',
  'icon': 'p-1.5 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 disabled:opacity-50 disabled:cursor-not-allowed',
};

export const fmtGB = (mb) => mb == null ? '—' : (mb / 1024).toFixed(1) + ' GB';
export const fmtBytes = (b) => b >= 2 ** 30 ? (b / 2 ** 30).toFixed(1) + ' GB' : b >= 2 ** 20 ? (b / 2 ** 20).toFixed(0) + ' MB' : (b / 2 ** 10).toFixed(0) + ' KB';
export const pct = (part, total) => total > 0 ? Math.max(0, Math.min(100, (part / total) * 100)) : 0;
export const stripAnsi = (s) => s.replace(/\x1b\[[0-9;]*m/g, '');

export function setBtn(el, variant, label = null, disabled = false) {
  el.className = BTN_BASE + ' ' + BTN[variant];
  if (label != null) el.textContent = label;
  el.disabled = disabled;
}

const renderers = [];
const ticks = [];
export function register(fn) { renderers.push(fn); }
export function registerTick(fn) { ticks.push(fn); }

export let lastCtx = null;

export async function refresh() {
  try {
    const s = await API.state();
    const [setupJob, uninstallJob] = await Promise.all([API.job('setup'), API.job('uninstall')]);
    const logs = await API.logs(200);
    const ctx = {
      ...s,
      jobs: { setup: setupJob, uninstall: uninstallJob },
      ready: s.instance.built && s.service.installed,
      logs: logs.lines,
    };
    lastCtx = ctx;
    for (const fn of renderers) fn(ctx);
    for (const fn of ticks) fn(ctx);
  } catch (e) { /* transient */ }
}

export function boot() {
  refresh();
  setInterval(refresh, 2000);
}
