import { motion } from 'framer-motion';
import { MapPin, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';

type Props = {
  customerName: string;
  productName: string;
  pickupLocationName: string;
  pickupTime: string;
  orderId: string;
  createdAt?: string | null;
  read: boolean;
  onMarkRead?: () => void;
};

const ease = [0.2, 0.8, 0.2, 1] as const;

export function PickupNotificationCard(props: Props) {
  const {
    customerName,
    productName,
    pickupLocationName,
    pickupTime,
    orderId,
    read,
    onMarkRead,
  } = props;

  return (
    <motion.button
      type="button"
      onClick={onMarkRead}
      initial={{ x: 28, opacity: 0 }}
      animate={{
        x: 0,
        opacity: 1,
        boxShadow: read
          ? '0 1px 2px rgba(0,0,0,0.06)'
          : [
              '0 1px 2px rgba(0,0,0,0.06)',
              '0 8px 30px rgba(0,0,0,0.14)',
              '0 1px 2px rgba(0,0,0,0.06)',
            ],
      }}
      transition={{
        // Slide-in spec: 220ms, soft spring feel.
        x: { type: 'spring', stiffness: 260, damping: 26 },
        opacity: { duration: 0.22, ease },
        // Pulse highlight for new/unread (1s).
        boxShadow: read ? { duration: 0.22, ease } : { duration: 1.0, ease },
      }}
      whileHover={{ scale: 1.01 }}
      className={cn(
        'w-full text-left rounded-xl border border-border bg-card p-4 shadow-sm',
        'transition-[box-shadow,background-color] duration-200',
        read ? 'bg-muted/30' : 'bg-card',
        'hover:shadow-md'
      )}
      style={{ transitionDuration: '180ms' }}
    >
      <div className="flex items-start gap-3">
        {/* Avatar placeholder */}
        <div className="h-10 w-10 rounded-full bg-muted flex items-center justify-center shrink-0">
          <span className="text-xs font-semibold text-muted-foreground">
            {customerName?.split(' ').slice(0, 2).map((s) => s[0]).join('').toUpperCase() || 'C'}
          </span>
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <div className="text-sm font-semibold truncate">
                {customerName}
                <span className="text-muted-foreground font-normal"> • </span>
                <span className="text-muted-foreground font-mono">#{orderId}</span>
              </div>
              <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                <span className="inline-flex items-center gap-1">
                  <MapPin className="h-3.5 w-3.5" />
                  <span className="truncate max-w-[22rem]">{pickupLocationName}</span>
                </span>
                <span className="inline-flex items-center gap-1">
                  <Clock className="h-3.5 w-3.5" />
                  <span className="truncate">{pickupTime}</span>
                </span>
              </div>
            </div>

            <motion.span
              initial={{ scale: 1 }}
              animate={read ? { scale: 1 } : { scale: [1, 1.08, 1] }}
              transition={read ? { duration: 0.2, ease: 'easeOut' } : { duration: 0.42, ease: 'easeOut' }}
              className={cn(
                'inline-flex items-center rounded-full px-2 py-1 text-[11px] font-medium',
                'border',
                read
                  ? 'bg-muted/40 text-muted-foreground border-border'
                  : 'bg-accent/10 text-accent border-accent/30'
              )}
            >
              Pickup Scheduled
            </motion.span>
          </div>

              <div className="mt-2 text-xs font-medium text-muted-foreground truncate">
                Product: <span className="text-foreground/90">{productName}</span>
              </div>

          <div className="mt-3 text-sm text-foreground/90 leading-relaxed">
            Customer <span className="font-medium">{customerName}</span> will pick up order{' '}
            <span className="font-mono">#{orderId}</span> from{' '}
            <span className="font-medium">{pickupLocationName}</span> at{' '}
            <span className="font-medium">{pickupTime}</span>.
          </div>
        </div>
      </div>
    </motion.button>
  );
}

