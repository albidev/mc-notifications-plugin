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
      const result = await listNotifications(4);
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
      <div className="flex items-center justify-between border-b border-border-subtle px-3 pb-2 pt-3">
        <div className="flex items-center gap-2">
          <Bell className="h-4 w-4 text-accent" />
          <div>
            <span className="eyebrow">Inbox</span>
            <h2 className="text-sm font-semibold text-text">Notifications</h2>
          </div>
        </div>
        {unreadCount > 0 ? <Badge variant="accent">{unreadCount} unread</Badge> : <CheckCheck className="h-4 w-4 text-positive" />}
      </div>
      <div className="p-3">
        {items.length > 0 ? (
          <div className="flex flex-col gap-2">
            {items.map((item) => (
              <div key={item.id} className="flex min-w-0 items-start gap-2 rounded-lg bg-surface-sunken/35 px-2.5 py-2">
                <span aria-hidden="true" className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${severityClass[item.severity]}`} />
                <div className="min-w-0 flex-1">
                  <p className={`truncate text-sm ${item.readAt ? 'font-normal text-text-muted' : 'font-medium text-text'}`}>{item.title}</p>
                  <p className="mt-0.5 truncate text-[11px] text-text-subtle"><time dateTime={item.createdAt} title={formatDateTime(item.createdAt)}>{formatDateTime(item.createdAt)}</time> <span aria-hidden="true">·</span> {formatRelativeTime(item.createdAt)} · {item.source.kind}</p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2 py-3 text-center">
            <CheckCheck className="h-6 w-6 text-positive" />
            <p className="text-sm text-text-muted">No notifications yet.</p>
          </div>
        )}
        <Link to="/notifications" className="mt-3 flex items-center justify-end gap-1 border-t border-border-subtle pt-2 text-xs font-medium text-accent hover:text-accent/80">
          Open notification center <ChevronRight className="h-3.5 w-3.5" />
        </Link>
      </div>
    </Card>
  );
}
