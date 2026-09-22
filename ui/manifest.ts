import type { MCPluginManifest } from '../../core/plugins/types';

export const notificationsManifest: MCPluginManifest = {
  id: 'notifications',
  name: 'Notifications',
  description: 'Persistent Mission Control notification inbox and delivery events',
  version: '0.2.0',
  enabled: true,
  routePath: '/notifications',
  navItem: {
    to: '/notifications',
    label: 'Notifications',
    icon: 'Bell',
    order: 55,
    indicator: {
      endpoint: '/notifications/status',
      pollMs: 30_000,
      tones: ['neutral', 'info', 'success', 'warning', 'error'],
    },
  },
  surfaces: {
    overview: { enabled: true, order: 20, className: 'widget-notifications' },
    attention: { enabled: true, order: 20 },
  },
  endpoints: [
    { method: 'GET', path: '/notifications', handler: 'listNotifications' },
    { method: 'GET', path: '/notifications/status', handler: 'notificationStatus' },
    { method: 'POST', path: '/notifications/publish', handler: 'publishNotification' },
    { method: 'POST', path: '/notifications/read', handler: 'markNotificationRead' },
    { method: 'POST', path: '/notifications/read-all', handler: 'markAllNotificationsRead' },
    { method: 'GET', path: '/notifications/deliveries', handler: 'listDeliveries' },
    { method: 'POST', path: '/notifications/deliveries/queue', handler: 'queueDelivery' },
    { method: 'POST', path: '/notifications/deliveries/claim', handler: 'claimDeliveries' },
    { method: 'POST', path: '/notifications/deliveries/complete', handler: 'completeDelivery' },
    { method: 'POST', path: '/notifications/deliveries/fail', handler: 'failDelivery' },
  ],
};
