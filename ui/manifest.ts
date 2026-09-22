import type { MCPluginManifest } from '../../core/plugins/types';

export const notificationsManifest: MCPluginManifest = {
  id: 'notifications',
  name: 'Notifications',
  description: 'Persistent Mission Control notification inbox and delivery events',
  version: '0.1.0',
  enabled: true,
  routePath: '/notifications',
  navItem: { to: '/notifications', label: 'Notifications', icon: 'Bell', order: 55 },
  surfaces: {
    overview: { enabled: true, order: 20, className: 'widget-notifications' },
    attention: { enabled: true, order: 20 },
  },
  endpoints: [
    { method: 'GET', path: '/notifications', handler: 'listNotifications' },
    { method: 'POST', path: '/notifications/publish', handler: 'publishNotification' },
    { method: 'POST', path: '/notifications/read', handler: 'markNotificationRead' },
    { method: 'POST', path: '/notifications/read-all', handler: 'markAllNotificationsRead' },
  ],
};
