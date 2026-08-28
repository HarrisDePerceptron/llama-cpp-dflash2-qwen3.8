import { API } from './api.js';

export { API };

const LLM = window.__LLM__;

export const $ = (id) => document.getElementById(id);
export const BTN_BASE = LLM.btnBase;
export const BTN = LLM.btnClasses;

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
