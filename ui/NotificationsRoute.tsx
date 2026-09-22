import { Bell, Check, CheckCheck, ExternalLink, RefreshCw, Search, X } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkBreaks from 'remark-breaks';
import remarkGfm from 'remark-gfm';
import { useCallback, useEffect, useState, type CSSProperties } from 'react';
import { Link } from 'react-router-dom';
import { Badge, Button, Card } from './primitives';
import { formatDateTime, formatRelativeTime } from './format';
import { listNotifications, markAllNotificationsRead, markNotificationRead } from './endpoints';
import type { NotificationItem, NotificationList, NotificationSeverity } from './types';

const severityVariant: Record<NotificationSeverity, 'default' | 'positive' | 'warning' | 'negative' | 'accent'> = {
  info: 'accent',
  success: 'positive',
  warning: 'warning',
  error: 'negative',
  action: 'accent',
};

function isCronDelivery(item: NotificationItem): boolean {
  return item.payload?.kind === 'cron-delivery' || item.payload?.kind === 'cron-report' || item.type === 'cron.delivery';
}

function isCronEvent(item: NotificationItem): boolean {
  return item.payload?.kind === 'cron-event' || item.type === 'cron.event';
}

function MarkdownDocument({ content }: { content: string }) {
  return (
    <div className="chat-markdown min-w-0 text-sm leading-7 text-text">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkBreaks]}
        components={{
          a: ({ node: _node, ...props }) => (
            <a {...props} target="_blank" rel="noopener noreferrer" />
          ),
          table: ({ node: _node, ...props }) => (
            <div className="chat-table-scroll">
              <table {...props} />
            </div>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

function NotificationDetailModal({ item, onClose }: { item: NotificationItem; onClose: () => void }) {
  const isDelivery = isCronDelivery(item);
  const isEvent = isCronEvent(item);
  const [isMobile, setIsMobile] = useState(() => typeof window !== 'undefined' && window.innerWidth < 640);

  useEffect(() => {
    const onResize = () => setIsMobile(window.innerWidth < 640);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  const dialogStyle: CSSProperties = isMobile
    ? { width: '100%', height: '100%', resize: 'none' }
    : {
        width: 'min(92vw, 1040px)',
        height: '82vh',
        minWidth: 360,
        minHeight: 480,
        maxWidth: 1100,
        maxHeight: '92vh',
        resize: 'both',
      };
  return (
    <div className="fixed inset-0 z-[100] flex h-full w-full items-center justify-center bg-black/75 p-0 sm:p-4" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="notification-detail-title"
        style={dialogStyle}
        className="relative flex h-full w-full max-w-none flex-col overflow-hidden border border-border bg-surface shadow-2xl sm:rounded-2xl"
      >
        <header className="flex shrink-0 items-start justify-between gap-4 border-b border-border-subtle bg-surface-raised px-4 py-4 sm:px-6 sm:py-5">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={severityVariant[item.severity]}>{item.severity}</Badge>
              <Badge variant="default">{item.source.kind}</Badge>
              {isDelivery ? <Badge variant="accent">Markdown report</Badge> : null}
              {isEvent ? <Badge variant="accent">Cron event</Badge> : null}
            </div>
            <h2 id="notification-detail-title" className="mt-3 break-words text-lg font-semibold tracking-tight text-text sm:text-2xl">{item.title}</h2>
            <p className="mt-1 text-xs text-text-subtle">{formatDateTime(item.createdAt)}{item.profile ? ` · ${item.profile}` : ''}{item.source.id ? ` · ${item.source.id}` : ''}</p>
          </div>
          <button type="button" onClick={onClose} className="shrink-0 rounded-xl p-2 text-text-muted transition-colors hover:bg-surface-sunken hover:text-text" aria-label="Close notification detail" title="Close">
            <X className="h-5 w-5" />
          </button>
        </header>
        <div className="min-h-0 flex-1 overflow-y-auto overscroll-y-contain scroll-py-8 px-4 py-8 sm:px-8 sm:py-10">
          <MarkdownDocument content={item.body || '*No report content.*'} />
        </div>
        <footer className="flex shrink-0 items-center justify-between gap-3 border-t border-border-subtle bg-surface-raised px-4 py-3 sm:px-6">
          <span className="truncate text-[11px] text-text-subtle">{isDelivery ? 'Cron report' : isEvent ? 'Cron event' : 'Mission Control notification'}</span>
          <Button variant="secondary" onClick={onClose}>Close</Button>
        </footer>
      </section>
    </div>
  );
}

export function NotificationsRoute() {
  const PAGE_SIZE = 50;
  const [data, setData] = useState<NotificationList>({ items: [], unreadCount: 0, readCount: 0, allCount: 0, total: 0, hasMore: false, nextOffset: null });
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<NotificationItem | null>(null);
  const [filter, setFilter] = useState<'all' | 'unread' | 'read'>('all');
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');

  const listOptions = filter === 'all' ? { search } : { read: filter, search };
  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const result = await listNotifications(PAGE_SIZE, 0, listOptions);
      setData(result);
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not load notifications.');
    } finally {
      setLoading(false);
    }
  }, [listOptions.read, listOptions.search]);

  useEffect(() => { void refresh(); }, [refresh]);

  useEffect(() => {
    const timer = window.setTimeout(() => setSearch(searchInput), 250);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  const loadMore = useCallback(async () => {
    if (loadingMore || !data.hasMore) return;
    setLoadingMore(true);
    try {
      const result = await listNotifications(PAGE_SIZE, data.nextOffset ?? data.items.length, listOptions);
      setData((current) => ({
        ...result,
        items: [...current.items, ...result.items],
      }));
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not load more notifications.');
    } finally {
      setLoadingMore(false);
    }
  }, [data.hasMore, data.items.length, data.nextOffset, listOptions.read, listOptions.search, loadingMore]);

  useEffect(() => {
    if (!selected) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setSelected(null);
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [selected]);

  const markRead = async (item: NotificationItem) => {
    if (item.readAt) return;
    try {
      const result = await markNotificationRead(item.id);
      setData((current) => ({
        ...current,
        unreadCount: Math.max(0, current.unreadCount - 1),
        readCount: current.readCount + 1,
        total: filter === 'unread' ? Math.max(0, current.total - 1) : current.total,
        items: filter === 'unread'
          ? current.items.filter((candidate: NotificationItem) => candidate.id !== item.id)
          : current.items.map((candidate: NotificationItem) => candidate.id === item.id ? result.notification : candidate),
      }));
      setSelected((current) => current?.id === item.id ? result.notification : current);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not mark notification as read.');
    }
  };

  const openNotification = async (item: NotificationItem) => {
    setSelected(item);
    if (!item.readAt) await markRead(item);
  };

  const markAllRead = async () => {
    try {
      await markAllNotificationsRead();
      setData((current) => ({
        ...current,
        unreadCount: 0,
        readCount: current.allCount,
        total: filter === 'unread' ? 0 : current.total,
        items: filter === 'unread' ? [] : current.items.map((item: NotificationItem) => ({ ...item, readAt: item.readAt || new Date().toISOString() })),
      }));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not mark notifications as read.');
    }
  };

  const visibleItems = data.items;

  const filterLabel = filter === 'all' ? 'all notifications' : filter === 'read' ? 'read notifications' : 'unread notifications';

  return (
    <div className="route-page-scroll h-full overflow-y-auto p-4 sm:p-6">
      <div className="mx-auto flex max-w-4xl flex-col gap-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <span className="eyebrow">Inbox</span>
            <h1 className="mt-1 flex items-center gap-2 text-2xl font-semibold text-text"><Bell className="h-6 w-6 text-accent" /> Notifications</h1>
            <p className="mt-1 text-sm text-text-muted">Persistent events from cron jobs, agents, and Mission Control integrations.</p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" icon={<RefreshCw className="h-3.5 w-3.5" />} onClick={() => void refresh()} disabled={loading}>Refresh</Button>
            <Button variant="secondary" icon={<CheckCheck className="h-3.5 w-3.5" />} onClick={() => void markAllRead()} disabled={data.unreadCount === 0}>Mark all read</Button>
          </div>
        </div>

        <div className="flex flex-col gap-3 rounded-xl border border-border bg-surface-raised p-2 shadow-sm sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap items-center gap-1" role="tablist" aria-label="Notification filter">
            {(['all', 'unread', 'read'] as const).map((option) => {
              const count = option === 'all' ? data.allCount : option === 'unread' ? data.unreadCount : data.readCount;
              const label = option === 'all' ? 'All' : option === 'unread' ? 'Unread' : 'Read';
              return (
                <button
                  key={option}
                  type="button"
                  role="tab"
                  aria-selected={filter === option}
                  onClick={() => setFilter(option)}
                  className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${filter === option ? 'bg-accent text-white shadow-sm' : 'text-text-muted hover:bg-surface-sunken hover:text-text'}`}
                >
                  {label} <span className={filter === option ? 'text-white/75' : 'text-text-subtle'}>{count}</span>
                </button>
              );
            })}
          </div>
          <label className="relative min-w-0 flex-1 sm:max-w-xs">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-subtle" />
            <input
              type="search"
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="Search notifications…"
              aria-label="Search notifications"
              className="h-9 w-full rounded-lg border border-border bg-surface px-9 text-sm text-text outline-none placeholder:text-text-subtle focus:border-accent/60 focus:ring-2 focus:ring-accent/15"
            />
          </label>
        </div>

        {error ? <Card padding="sm"><p className="text-sm text-negative">{error}</p></Card> : null}
        {loading && data.items.length === 0 ? <Card padding="md"><p className="text-sm text-text-muted">Loading notifications…</p></Card> : null}
        {!loading && data.total === 0 && !search && filter === 'all' ? <Card padding="lg"><div className="flex flex-col items-center gap-2 text-center"><Check className="h-8 w-8 text-positive" /><p className="font-medium text-text">You’re all caught up.</p><p className="text-sm text-text-muted">New cron and agent events will appear here.</p></div></Card> : null}
        {!loading && data.total === 0 && (Boolean(search) || filter !== 'all') ? <Card padding="lg"><div className="flex flex-col items-center gap-2 text-center"><Search className="h-8 w-8 text-text-subtle" /><p className="font-medium text-text">No matches in {filterLabel}.</p><p className="text-sm text-text-muted">Try another search or switch the filter.</p></div></Card> : null}

        <div className="flex flex-col gap-2">
          {visibleItems.map((item) => {
            const delivery = isCronDelivery(item);
            const event = isCronEvent(item);
            const preview = delivery
              ? item.body.replace(/\s+/g, ' ').trim().slice(0, 280)
              : item.body;
            return (
              <Card
                key={item.id}
                padding="sm"
                className={`cursor-pointer transition-colors hover:border-accent/40 hover:bg-surface-sunken/35 ${item.readAt ? 'opacity-75' : ''}`}
                role="button"
                tabIndex={0}
                onClick={() => void openNotification(item)}
                onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); void openNotification(item); } }}
              >
                <div className="flex items-start gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      {!item.readAt ? <span aria-label="Unread" className="h-2 w-2 rounded-full bg-accent" /> : null}
                      <h2 className="font-medium text-text">{item.title}</h2>
                      <Badge variant={severityVariant[item.severity]}>{item.severity}</Badge>
                      <Badge variant="default">{item.source.kind}</Badge>
                      {delivery ? <Badge variant="accent">report</Badge> : null}
                      {event ? <Badge variant="accent">event</Badge> : null}
                    </div>
                    {preview ? <p className={`mt-2 ${delivery ? 'line-clamp-2 font-mono text-[11px] leading-5' : 'line-clamp-2 text-sm'} text-text-muted`}>{preview}</p> : null}
                    <p className="mt-2 text-xs text-text-subtle"><time dateTime={item.createdAt} title={formatDateTime(item.createdAt)}>{formatDateTime(item.createdAt)}</time> <span aria-hidden="true">·</span> {formatRelativeTime(item.createdAt)}{item.profile ? ` · ${item.profile}` : ''}{item.source.id ? ` · ${item.source.id}` : ''} · Tap to open</p>
                  </div>
                  <div className="flex shrink-0 items-center gap-1">
                    {item.deepLink ? <Link to={item.deepLink} onClick={(event) => event.stopPropagation()} className="rounded p-2 text-text-muted hover:bg-surface-sunken hover:text-accent" aria-label="Open source" title="Open source"><ExternalLink className="h-4 w-4" /></Link> : null}
                    {!item.readAt ? <button type="button" className="rounded p-2 text-text-muted hover:bg-surface-sunken hover:text-accent" aria-label="Mark as read" title="Mark as read" onClick={(event) => { event.stopPropagation(); void markRead(item); }}><Check className="h-4 w-4" /></button> : null}
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
        {data.total > 0 ? (
          <div className="flex flex-col items-center gap-2 border-t border-border-subtle pt-4 sm:flex-row sm:justify-between">
            <p className="text-xs text-text-subtle">Showing {data.items.length} of {data.total}</p>
            {data.hasMore ? <Button variant="secondary" onClick={() => void loadMore()} disabled={loadingMore}>{loadingMore ? 'Loading…' : 'Load more'}</Button> : <span className="text-xs text-text-subtle">All loaded</span>}
          </div>
        ) : null}
      </div>
      {selected ? <NotificationDetailModal item={selected} onClose={() => setSelected(null)} /> : null}
    </div>
  );
}
