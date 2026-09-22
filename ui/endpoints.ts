import type { NotificationItem, NotificationList } from './types';

const API_BASE = '/api/local';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = typeof window !== 'undefined' ? window.localStorage.getItem('mission-control-token') || '' : '';
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      Accept: 'application/json',
      ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers || {}),
    },
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || payload.error || `Request failed (${response.status})`);
  return payload as T;
}

export type NotificationListOptions = {
  read?: 'read' | 'unread';
  search?: string;
};

export function listNotifications(limit = 50, offset = 0, options: NotificationListOptions = {}): Promise<NotificationList> {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  if (options.read) params.set('read', options.read);
  if (options.search?.trim()) params.set('q', options.search.trim());
  return request<NotificationList>(`/notifications?${params.toString()}`);
}

export function markNotificationRead(id: string): Promise<{ success: boolean; notification: NotificationItem }> {
  return request('/notifications/read', {
    method: 'POST',
    body: JSON.stringify({ id }),
  });
}

export function markAllNotificationsRead(): Promise<{ success: boolean; markedRead: number }> {
  return request('/notifications/read-all', {
    method: 'POST',
    body: JSON.stringify({}),
  });
}
