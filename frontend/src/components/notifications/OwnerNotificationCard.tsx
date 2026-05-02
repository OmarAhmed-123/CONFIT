import { Bell } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface OwnerNotificationCardProps {
  notification: any;
  onMarkRead?: () => void;
  onDelete?: () => void;
}

export function OwnerNotificationCard({
  notification,
  onMarkRead,
  onDelete,
}: OwnerNotificationCardProps) {
  const title = notification?.title || notification?.data?.title || 'Notification';
  const message = notification?.message || notification?.data?.message || notification?.body || '';
  const read = Boolean(notification?.read_status || notification?.read);

  return (
    <div className={cn('rounded-lg border p-3 bg-card', !read && 'border-accent/50 bg-accent/5')}>
      <div className="flex items-start gap-3">
        <Bell className="h-4 w-4 mt-1 text-accent" />
        <div className="min-w-0 flex-1">
          <p className="font-medium text-sm">{title}</p>
          {message && <p className="text-xs text-muted-foreground mt-1">{message}</p>}
          <div className="flex gap-2 mt-3">
            {!read && onMarkRead && (
              <Button size="sm" variant="outline" onClick={onMarkRead}>
                Mark read
              </Button>
            )}
            {onDelete && (
              <Button size="sm" variant="ghost" onClick={onDelete}>
                Delete
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
