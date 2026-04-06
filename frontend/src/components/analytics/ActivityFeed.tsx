/**
 * CONFIT — Activity Feed
 * ========================
 * Scrollable real-time event log with channel/recipient filters.
 * Color-coded event type badges.
 */

import { useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Activity,
  Send,
  CheckCircle2,
  Eye,
  MousePointerClick,
  X,
  Filter,
  Mail,
  Bell,
  MessageSquare,
  Users,
  Store,
} from 'lucide-react';
import type {
  ActivityFeedItem,
  AnalyticsChannel,
  AnalyticsRecipientType,
  NotificationEventType,
} from '@/types/notificationAnalyticsTypes';

interface ActivityFeedProps {
  items: ActivityFeedItem[];
}

const EVENT_CONFIG: Record<NotificationEventType, {
  label: string;
  icon: typeof Send;
  color: string;
  bg: string;
}> = {
  sent: { label: 'Sent', icon: Send, color: 'text-blue-400', bg: 'bg-blue-500/10' },
  delivered: { label: 'Delivered', icon: CheckCircle2, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
  read: { label: 'Read', icon: Eye, color: 'text-purple-400', bg: 'bg-purple-500/10' },
  clicked: { label: 'Clicked', icon: MousePointerClick, color: 'text-amber-400', bg: 'bg-amber-500/10' },
  dismissed: { label: 'Dismissed', icon: X, color: 'text-gray-400', bg: 'bg-gray-500/10' },
};

const CHANNEL_ICONS: Record<AnalyticsChannel, typeof Bell> = {
  in_app: MessageSquare,
  email: Mail,
  push: Bell,
  toast: Bell,
};

function formatTimeAgo(timestamp: string): string {
  const diff = Date.now() - new Date(timestamp).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function ActivityFeed({ items }: ActivityFeedProps) {
  const [channelFilter, setChannelFilter] = useState<AnalyticsChannel | 'all'>('all');
  const [recipientFilter, setRecipientFilter] = useState<AnalyticsRecipientType | 'all'>('all');
  const [showFilters, setShowFilters] = useState(false);

  const filteredItems = useMemo(() => {
    let result = items;
    if (channelFilter !== 'all') {
      result = result.filter((i) => i.channel === channelFilter);
    }
    if (recipientFilter !== 'all') {
      result = result.filter((i) => i.recipient_type === recipientFilter);
    }
    return result.slice(0, 50);
  }, [items, channelFilter, recipientFilter]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.3 }}
      className="rounded-2xl border border-white/[0.06] bg-white/[0.02] backdrop-blur-xl p-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-emerald-400" />
          <h3 className="text-lg font-semibold text-foreground font-sans">
            Real-Time Activity
          </h3>
          <span className="text-xs text-muted-foreground">
            ({filteredItems.length} events)
          </span>
        </div>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
            showFilters ? 'bg-white/[0.08] text-foreground' : 'text-muted-foreground hover:text-foreground bg-white/[0.04]'
          }`}
        >
          <Filter className="h-3.5 w-3.5" />
          Filters
        </button>
      </div>

      {/* Filters */}
      <AnimatePresence>
        {showFilters && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden mb-4"
          >
            <div className="flex flex-wrap gap-3 pb-4 border-b border-white/[0.06]">
              <div>
                <label className="text-[10px] text-muted-foreground uppercase tracking-wider block mb-1">
                  Channel
                </label>
                <div className="flex gap-1">
                  {(['all', 'in_app', 'email', 'push'] as const).map((ch) => (
                    <button
                      key={ch}
                      onClick={() => setChannelFilter(ch)}
                      className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all ${
                        channelFilter === ch ? 'bg-white/[0.1] text-foreground' : 'text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      {ch === 'all' ? 'All' : ch === 'in_app' ? 'In-App' : ch.charAt(0).toUpperCase() + ch.slice(1)}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-[10px] text-muted-foreground uppercase tracking-wider block mb-1">
                  Recipient
                </label>
                <div className="flex gap-1">
                  {(['all', 'customer', 'owner'] as const).map((rt) => (
                    <button
                      key={rt}
                      onClick={() => setRecipientFilter(rt)}
                      className={`flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium transition-all ${
                        recipientFilter === rt ? 'bg-white/[0.1] text-foreground' : 'text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      {rt === 'customer' && <Users className="h-3 w-3" />}
                      {rt === 'owner' && <Store className="h-3 w-3" />}
                      {rt === 'all' ? 'All' : rt.charAt(0).toUpperCase() + rt.slice(1)}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Feed List */}
      <div className="max-h-[400px] overflow-y-auto space-y-1 pr-1">
        {filteredItems.map((item, i) => {
          const config = EVENT_CONFIG[item.event_type];
          const EventIcon = config.icon;
          const ChannelIcon = CHANNEL_ICONS[item.channel];

          return (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.2, delay: Math.min(i * 0.02, 0.5) }}
              className="flex items-center gap-3 py-2.5 px-3 rounded-lg hover:bg-white/[0.02] transition-colors"
            >
              {/* Event icon */}
              <div className={`h-7 w-7 rounded-lg ${config.bg} flex items-center justify-center flex-shrink-0`}>
                <EventIcon className={`h-3.5 w-3.5 ${config.color}`} />
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-foreground font-medium truncate">
                    {item.notification_title}
                  </span>
                  <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${config.bg} ${config.color}`}>
                    {config.label}
                  </span>
                </div>
                <div className="flex items-center gap-2 mt-0.5 text-xs text-muted-foreground">
                  <ChannelIcon className="h-3 w-3" />
                  <span>{item.channel === 'in_app' ? 'In-App' : item.channel.charAt(0).toUpperCase() + item.channel.slice(1)}</span>
                  <span className="text-muted-foreground/40">·</span>
                  <span className="flex items-center gap-1">
                    {item.recipient_type === 'customer' ? <Users className="h-3 w-3" /> : <Store className="h-3 w-3" />}
                    {item.recipient_id}
                  </span>
                </div>
              </div>

              {/* Timestamp */}
              <span className="text-xs text-muted-foreground whitespace-nowrap flex-shrink-0">
                {formatTimeAgo(item.timestamp)}
              </span>
            </motion.div>
          );
        })}

        {filteredItems.length === 0 && (
          <div className="text-center py-8 text-muted-foreground text-sm">
            No events match the current filters.
          </div>
        )}
      </div>
    </motion.div>
  );
}
