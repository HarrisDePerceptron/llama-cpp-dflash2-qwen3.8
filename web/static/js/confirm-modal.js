import { openModal } from './modal.js';

function openConfirm({ title, message, confirmLabel = 'Confirm', danger = false }) {
  return new Promise((resolve) => {
    openModal({
      templateId: 'confirm-modal-template',
      variant: 'confirm',
      labelledBy: 'confirm-title',
      closeResult: false,
      initialFocus: '#confirm-cancel',
      footerActions: [
        { id: 'confirm-cancel', label: 'Cancel', variant: 'confirm-cancel', close: true, result: false },
        { id: 'confirm-ok', label: confirmLabel, variant: danger ? 'danger' : 'primary', close: true, result: true },
      ],
      onMount: ({ query }) => {
        query('#confirm-title').textContent = title;
        query('#confirm-message').textContent = message;
        const icon = query('#confirm-icon');
        icon.className = 'shrink-0 w-9 h-9 rounded-full flex items-center justify-center '
          + (danger ? 'bg-red-500/10 text-red-400' : 'bg-sky-500/10 text-sky-400');
        query('#confirm-icon-danger').classList.toggle('hidden', !danger);
        query('#confirm-icon-info').classList.toggle('hidden', danger);
      },
      onClose: resolve,
    });
  });
}

window.openConfirm = openConfirm;
