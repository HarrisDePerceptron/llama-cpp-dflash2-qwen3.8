async function req(path, opts) {
  const r = await fetch(path, opts);
  let body = null;
  try {
    body = await r.json();
  } catch {
    /* non-JSON */
  }
  if (!r.ok) throw new Error((body && body.detail) || r.statusText);
  return body;
}

export const API = {
  req,
  get: (p) => req(p),
  post: (p, body) =>
    req(p, body != null
      ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }
      : { method: 'POST' }),
  state: () => req('/api/state'),
  logs: (n = 200) => req(`/api/logs?lines=${n}`),
  job: (name) => req(`/api/jobs/${name}`),
  jobStop: (name) => req(`/api/jobs/${name}/stop`, { method: 'POST' }),
  service: (action) => req(`/api/service/${action}`, { method: 'POST' }),
  setup: () => req('/api/setup', { method: 'POST' }),
  uninstall: () => req('/api/service/uninstall', { method: 'POST' }),
  opencodeSetup: () => req('/api/opencode-setup', { method: 'POST' }),
  saveServerParams: (params) => req('/api/server/params', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ params }) }),
  restartServer: () => req('/api/server/restart', { method: 'POST' }),
};
