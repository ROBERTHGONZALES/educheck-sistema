export const CONTACT_EMAIL = (import.meta.env.VITE_CONTACT_EMAIL ?? '').trim();

export const demoMailto = CONTACT_EMAIL
  ? `mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent('Solicitud de demostración de EduCheck')}`
  : '';
