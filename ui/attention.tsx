import { Bell, ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useCallback, useEffect, useState } from 'react';
import { Badge } from './primitives';
import { listNotifications } from './endpoints';

export function NotificationsAttention({ onActiveChange }: { onActiveChange: (count: number) => void }) {
  const [count, setCount] = useState(0);
  const refresh = useCallback(async () => {
    try {
      const result = await listNotifications(1);
      setCount(result.unreadCount);
      onActiveChange(result.unreadCount);
    } catch {
      setCount(0);
      onActiveChange(0);
    }
  }, [onActiveChange]);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 30_000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  if (count === 0) return null;
  return (
    <div className="flex items-center gap-2">
      <Bell className="mt-0.5 h-4 w-4 shrink-0 text-warning" />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-text">Unread notifications</p>
        <p className="mt-0.5 text-xs text-text-muted">The inbox has items waiting for review.</p>
      </div>
      <Badge variant="warning">{count}</Badge>
      <Link to="/notifications" className="text-text-muted hover:text-accent" aria-label="Open notifications" title="Open notifications">
        <ChevronRight className="h-4 w-4" />
      </Link>
    </div>
  );
}
