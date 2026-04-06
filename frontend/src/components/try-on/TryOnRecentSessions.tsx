import { motion, AnimatePresence } from 'framer-motion';
import { History, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { TryOnLocalSessionEntry } from '@/lib/tryOnLocalSessions';
import { clearTryOnSessions } from '@/lib/tryOnLocalSessions';

interface TryOnRecentSessionsProps {
  sessions: TryOnLocalSessionEntry[];
  onRefresh: () => void;
}

export function TryOnRecentSessions({ sessions, onRefresh }: TryOnRecentSessionsProps) {
  if (sessions.length === 0) return null;

  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="mt-10 rounded-2xl border border-border/80 bg-card/40 p-4 backdrop-blur-md md:p-6"
    >
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <History className="h-4 w-4 text-muted-foreground" aria-hidden />
          <h2 className="text-sm font-semibold tracking-tight md:text-base">Recent on this device</h2>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="gap-1 text-muted-foreground"
          onClick={() => {
            clearTryOnSessions();
            onRefresh();
          }}
        >
          <Trash2 className="h-3.5 w-3.5" />
          Clear
        </Button>
      </div>
      <div className="flex gap-3 overflow-x-auto pb-1">
        <AnimatePresence mode="popLayout">
          {sessions.map((s) => (
            <motion.div
              key={s.id}
              layout
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.96 }}
              className="w-[100px] shrink-0"
            >
              <div className="overflow-hidden rounded-xl border border-border bg-muted/30">
                {s.thumbDataUrl ? (
                  <img
                    src={s.thumbDataUrl}
                    alt=""
                    className="aspect-[3/4] w-full object-cover"
                  />
                ) : (
                  <div className="aspect-[3/4] w-full bg-muted" />
                )}
              </div>
              <p className="mt-1 line-clamp-2 text-[10px] text-muted-foreground leading-tight">
                {s.productName}
              </p>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
      <p className="mt-3 text-[11px] text-muted-foreground">
        Stored locally in your browser — not sent to external analytics. Use a real Supabase project
        when you need cloud sync.
      </p>
    </motion.section>
  );
}
