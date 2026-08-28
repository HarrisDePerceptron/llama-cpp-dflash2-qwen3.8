import { API, refresh } from './core.js';
import { openModal } from './modal.js';

let configContext = null;

function openServerConfig() {
  configContext = openModal({
    templateId: 'srv-config-modal-template',
    variant: 'config',
    title: 'Server configuration',
    initialFocus: '#srv-config-body input',
    footerActions: [
      { label: 'Cancel', variant: 'secondary', close: true },
      { id: 'srv-config-save', label: 'Save & Restart', onClick: saveServerConfig },
    ],
    onClose: () => { configContext = null; },
  });
}

function closeServerConfig() {
  if (configContext) configContext.close();
}

async function saveServerConfig(actionContext = configContext) {
  const context = actionContext?.query ? actionContext : configContext;
  if (!context) return;
  const inputs = context.query('#srv-config-body').querySelectorAll('[data-idx]');
  const params = [];
  inputs.forEach((el) => {
    if (el.dataset.flag) {
      if (el.checked) params.push({ name: el.dataset.name, value: '', is_flag: true });
    } else {
      params.push({ name: el.dataset.name, value: el.value, is_flag: false });
    }
  });

  const btn = actionContext?.button || context.query('#srv-config-save');
  btn.disabled = true;
  btn.textContent = 'Saving…';
  try {
    await API.saveServerParams(params);
    await API.restartServer();
    context.close();
    refresh();
  } catch (error) {
    alert(error.message);
  } finally {
    if (btn.isConnected) {
      btn.disabled = false;
      btn.textContent = 'Save & Restart';
    }
  }
}

window.openServerConfig = openServerConfig;
window.closeServerConfig = closeServerConfig;
window.saveServerConfig = saveServerConfig;
