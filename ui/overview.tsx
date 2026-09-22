import { Bell, CheckCheck, ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useCallback, useEffect, useState } from 'react';
import { Badge, Card } from './primitives';
import { formatDateTime, formatRelativeTime } from './format';
import { listNotifications } from './endpoints';
import type { NotificationItem, NotificationSeverity } from './types';

const severityClass: Record<NotificationSeverity, string> = {
  info: 'bg-accent',
  success: 'bg-positive',
  warning: 'bg-warning',
  error: 'bg-negative',
  action: 'bg-accent',
};

export function NotificationsOverview() {
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);

  const refresh = useCallback(async () => {
    try {
      const result = await listNotifications(3);
      setItems(result.items);
      setUnreadCount(result.unreadCount);
    } catch {
      // The overview must stay usable if an optional plugin backend is down.
    }
  }, []);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 30_000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  return (
    <Card padding="none">
      <div className="flex items-center justify-between border-b border-border-subtle px-3 py-2.5">
        <div className="flex min-w-0 items-center gap-2">
          <Bell className="h-4 w-4 shrink-0 text-accent" />
          <div className="min-w-0">
            <span className="eyebrow">Inbox</span>
            <h2 className="truncate text-sm font-semibold text-text">Notifications</h2>
          </div>
        </div>
        {unreadCount > 0 ? (
          <Badge className="shrink-0 text-[11px]" variant="accent">{unreadCount} unread</Badge>
        ) : (
          <CheckCheck aria-label="All notifications read" className="h-4 w-4 shrink-0 text-positive" title="All notifications read" />
        )}
      </div>
      <div>
        {items.length > 0 ? (
          <div className="flex flex-col gap-2 px-3">
            {items.map((item) => (
              <div key={item.id} className="rounded-lg bg-surface-sunken/35 px-2.5 py-2">
                <div className="flex min-w-0 items-center gap-2 text-sm">
                  <span aria-hidden="true" className={`h-2 w-2 shrink-0 rounded-full ${severityClass[item.severity]}`} />
                  <span className={`min-w-0 flex-1 truncate font-medium ${item.readAt ? 'text-text-muted' : 'text-text'}`}>{item.title}</span>
                  <time className="shrink-0 text-xs text-text-muted" dateTime={item.createdAt} title={formatDateTime(item.createdAt)}>{formatRelativeTime(item.createdAt)}</time>
                </div>
                <div className="mt-1 flex min-w-0 flex-wrap items-center gap-x-1.5 gap-y-0.5 text-[11px] text-text-subtle">
                  <span>{item.source.kind}</span>
                  <span aria-hidden="true">·</span>
                  <span>{item.profile || item.severity}</span>
                  <span className="sr-only"> · {formatDateTime(item.createdAt)}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="flex items-center justify-center gap-2 px-3 py-5 text-center">
            <CheckCheck className="h-4 w-4 text-positive" />
            <p className="text-sm text-text-muted">No notifications yet.</p>
          </div>
        )}
        <Link to="/notifications" className="flex items-center justify-end gap-1 border-t border-border-subtle px-3 py-2 text-xs font-medium text-accent hover:text-accent/80">
          Open notification center <ChevronRight className="h-3.5 w-3.5" />
        </Link>
      </div>
    </Card>
  );
}
