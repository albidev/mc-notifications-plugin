export type NotificationSeverity = 'info' | 'success' | 'warning' | 'error' | 'action';

export type NotificationItem = {
  id: string;
  dedupeKey: string;
  type: string;
  severity: NotificationSeverity;
  title: string;
  body: string;
  source: { kind: string; id: string | null };
  profile: string | null;
  createdAt: string;
  readAt: string | null;
  archivedAt: string | null;
  deepLink: string | null;
  payload: Record<string, unknown>;
};

export type NotificationList = {
  items: NotificationItem[];
  unreadCount: number;
  readCount: number;
  allCount: number;
  actionableCount: number;
  total: number;
  hasMore: boolean;
  nextOffset: number | null;
};

export type NotificationSession =
  | { available: true; sessionId: string; profile: string; title: string | null; messageCount: number }
  | { available: false; reason: string };
