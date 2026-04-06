/**
 * Social User Card Component
 * User profile card for follow suggestions and user lists
 */

import React, { useCallback } from 'react';
import { motion } from 'framer-motion';
import { UserPlus, UserCheck, MoreHorizontal } from 'lucide-react';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { useSocialStore, SocialUser } from '@/stores/socialStore';
import { apiFetch, getAuthToken } from '@/lib/api';

interface SocialUserCardProps {
  user: SocialUser;
  variant?: 'default' | 'compact' | 'list';
  showStats?: boolean;
  showFollowButton?: boolean;
  onUserClick?: (userId: string) => void;
  className?: string;
}

export function SocialUserCard({
  user,
  variant = 'default',
  showStats = true,
  showFollowButton = true,
  onUserClick,
  className,
}: SocialUserCardProps) {
  const { followUser, unfollowUser } = useSocialStore();
  
  const handleFollowToggle = useCallback(
    async (e: React.MouseEvent) => {
      e.stopPropagation();
      
      const token = getAuthToken();
      if (!token) return;
      
      try {
        if (user.is_following) {
          await apiFetch(`/api/social/follow/${user.id}`, {
            token,
            method: 'DELETE',
          });
          unfollowUser(user.id);
        } else {
          await apiFetch('/api/social/follow', {
            token,
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: user.id }),
          });
          followUser(user.id);
        }
      } catch (error) {
        console.error('Failed to toggle follow:', error);
      }
    },
    [user.id, user.is_following, followUser, unfollowUser]
  );
  
  if (variant === 'compact') {
    return (
      <div
        className={cn('flex items-center gap-3 p-2 rounded-lg hover:bg-muted/50 transition-colors cursor-pointer', className)}
        onClick={() => onUserClick?.(user.id)}
      >
        <Avatar className="h-10 w-10">
          <AvatarImage src={user.avatar_url || undefined} />
          <AvatarFallback>{user.name.slice(0, 2).toUpperCase()}</AvatarFallback>
        </Avatar>
        
        <div className="flex-1 min-w-0">
          <p className="font-medium text-sm truncate">{user.name}</p>
          {user.style_preference && (
            <p className="text-xs text-muted-foreground truncate">{user.style_preference}</p>
          )}
        </div>
        
        {showFollowButton && (
          <Button
            size="sm"
            variant={user.is_following ? 'secondary' : 'default'}
            onClick={handleFollowToggle}
            className="flex-shrink-0"
          >
            {user.is_following ? (
              <>
                <UserCheck className="h-4 w-4 mr-1" />
                Following
              </>
            ) : (
              <>
                <UserPlus className="h-4 w-4 mr-1" />
                Follow
              </>
            )}
          </Button>
        )}
      </div>
    );
  }
  
  if (variant === 'list') {
    return (
      <motion.div
        whileHover={{ scale: 1.01 }}
        className={cn('flex items-center gap-4 p-4 rounded-xl bg-card border hover:shadow-md transition-shadow cursor-pointer', className)}
        onClick={() => onUserClick?.(user.id)}
      >
        <Avatar className="h-14 w-14">
          <AvatarImage src={user.avatar_url || undefined} />
          <AvatarFallback>{user.name.slice(0, 2).toUpperCase()}</AvatarFallback>
        </Avatar>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <p className="font-semibold truncate">{user.name}</p>
            {user.is_followed_by && (
              <Badge variant="outline" className="text-xs">
                Follows you
              </Badge>
            )}
          </div>
          
          {showStats && (
            <div className="flex items-center gap-3 text-sm text-muted-foreground mt-1">
              {user.followers_count !== undefined && (
                <span>{user.followers_count.toLocaleString()} followers</span>
              )}
              {user.style_preference && (
                <span className="truncate">{user.style_preference}</span>
              )}
            </div>
          )}
        </div>
        
        {showFollowButton && (
          <Button
            size="default"
            variant={user.is_following ? 'secondary' : 'default'}
            onClick={handleFollowToggle}
            className="flex-shrink-0"
          >
            {user.is_following ? (
              <>
                <UserCheck className="h-4 w-4 mr-2" />
                Following
              </>
            ) : (
              <>
                <UserPlus className="h-4 w-4 mr-2" />
                Follow
              </>
            )}
          </Button>
        )}
      </motion.div>
    );
  }
  
  // Default card variant
  return (
    <motion.div
      whileHover={{ y: -4 }}
      className={cn('bg-card rounded-xl border overflow-hidden hover:shadow-lg transition-shadow cursor-pointer', className)}
      onClick={() => onUserClick?.(user.id)}
    >
      {/* Cover image placeholder */}
      <div className="h-20 bg-gradient-to-br from-primary/20 to-primary/5" />
      
      {/* Content */}
      <div className="p-4 pt-0">
        <Avatar className="h-16 w-16 border-4 border-background -mt-8">
          <AvatarImage src={user.avatar_url || undefined} />
          <AvatarFallback className="text-lg">{user.name.slice(0, 2).toUpperCase()}</AvatarFallback>
        </Avatar>
        
        <div className="mt-3">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold">{user.name}</h3>
              {user.style_preference && (
                <p className="text-sm text-muted-foreground">{user.style_preference}</p>
              )}
            </div>
            
            {showFollowButton && (
              <Button
                size="sm"
                variant={user.is_following ? 'secondary' : 'default'}
                onClick={handleFollowToggle}
              >
                {user.is_following ? (
                  <UserCheck className="h-4 w-4" />
                ) : (
                  <UserPlus className="h-4 w-4" />
                )}
              </Button>
            )}
          </div>
          
          {showStats && (
            <div className="flex items-center gap-4 mt-3 text-sm text-muted-foreground">
              <div className="text-center">
                <p className="font-semibold text-foreground">{user.followers_count?.toLocaleString() || 0}</p>
                <p className="text-xs">Followers</p>
              </div>
              <div className="text-center">
                <p className="font-semibold text-foreground">{user.following_count?.toLocaleString() || 0}</p>
                <p className="text-xs">Following</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

// Skeleton component
export function SocialUserCardSkeleton({ variant = 'default' }: { variant?: 'default' | 'compact' | 'list' }) {
  if (variant === 'compact') {
    return (
      <div className="flex items-center gap-3 p-2 animate-pulse">
        <div className="h-10 w-10 rounded-full bg-muted" />
        <div className="flex-1 space-y-2">
          <div className="h-4 w-24 bg-muted rounded" />
          <div className="h-3 w-16 bg-muted rounded" />
        </div>
      </div>
    );
  }
  
  if (variant === 'list') {
    return (
      <div className="flex items-center gap-4 p-4 rounded-xl bg-card border animate-pulse">
        <div className="h-14 w-14 rounded-full bg-muted" />
        <div className="flex-1 space-y-2">
          <div className="h-4 w-32 bg-muted rounded" />
          <div className="h-3 w-48 bg-muted rounded" />
        </div>
      </div>
    );
  }
  
  return (
    <div className="bg-card rounded-xl border overflow-hidden animate-pulse">
      <div className="h-20 bg-muted" />
      <div className="p-4 pt-0">
        <div className="h-16 w-16 rounded-full bg-muted -mt-8 border-4 border-background" />
        <div className="mt-3 space-y-3">
          <div className="h-4 w-24 bg-muted rounded" />
          <div className="h-3 w-32 bg-muted rounded" />
          <div className="flex gap-4">
            <div className="h-8 w-16 bg-muted rounded" />
            <div className="h-8 w-16 bg-muted rounded" />
          </div>
        </div>
      </div>
    </div>
  );
}
