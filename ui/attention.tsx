import { Bell, ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useEffect, useRef, useState } from 'react';
import { Badge } from './primitives';
import { listNotifications } from './endpoints';
import { createSingleFlightPoller } from './single-flight-poller';

export function NotificationsAttention({ onActiveChange }: { onActiveChange: (count: number) => void }) {
  const [count, setCount] = useState(0);
  // Hosts may pass a fresh callback every render; keep it out of the polling
  // effect so a re-render never restarts the poll (and never adds a request).
  const onActiveChangeRef = useRef(onActiveChange);
  useEffect(() => {
    onActiveChangeRef.current = onActiveChange;
  }, [onActiveChange]);

  useEffect(() => {
    const poller = createSingleFlightPoller({
      intervalMs: 30_000,
      load: (signal) => listNotifications(1, 0, { actionable: true }, { signal }),
      onResult: (result) => {
        setCount(result.unreadCount);
        onActiveChangeRef.current(result.unreadCount);
      },
      onError: () => {
        setCount(0);
        onActiveChangeRef.current(0);
      },
    });
    poller.start();
    return () => poller.stop();
  }, []);

  if (count === 0) return null;
  return (
    <div className="flex items-center gap-2">
      <Bell className="mt-0.5 h-4 w-4 shrink-0 text-warning" />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-text">Action needed</p>
        <p className="mt-0.5 text-xs text-text-muted">Errors, warnings, and notifications waiting for your input.</p>
      </div>
      <Badge variant="warning">{count}</Badge>
      <Link to="/notifications" className="text-text-muted hover:text-accent" aria-label="Open notifications" title="Open notifications">
        <ChevronRight className="h-4 w-4" />
      </Link>
    </div>
  );
}
