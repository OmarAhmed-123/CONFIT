/**
 * Social Feed Component
 * Infinite scroll feed with multiple feed types
 */

import React, { useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { RefreshCw, Home, Compass, Users, TrendingUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import { useSocialStore, FeedType, SocialPost } from '@/stores/socialStore';
import { SocialPostCard, SocialPostCardSkeleton } from './SocialPostCard';
import { apiFetch, getAuthToken } from '@/lib/api';
import { createTransition } from '@/motion';

interface SocialFeedProps {
  initialFeedType?: FeedType;
  onPostClick?: (post: SocialPost) => void;
  onUserClick?: (userId: string) => void;
  onHashtagClick?: (hashtag: string) => void;
  className?: string;
}

const FEED_CONFIGS: Record<FeedType, { icon: React.ReactNode; label: string }> = {
  home: { icon: <Home className="h-4 w-4" />, label: 'Home' },
  discover: { icon: <Compass className="h-4 w-4" />, label: 'Discover' },
  following: { icon: <Users className="h-4 w-4" />, label: 'Following' },
  trending: { icon: <TrendingUp className="h-4 w-4" />, label: 'Trending' },
};

export function SocialFeed({
  initialFeedType = 'home',
  onPostClick,
  onUserClick,
  onHashtagClick,
  className,
}: SocialFeedProps) {
  const observerTarget = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  
  const {
    feeds,
    currentFeedType,
    setFeedType,
    setFeedPosts,
    appendFeedPosts,
    setFeedLoading,
    setFeedError,
    resetFeed,
  } = useSocialStore();
  
  const currentFeed = feeds[currentFeedType];
  
  // Fetch feed posts
  const fetchPosts = useCallback(async (feedType: FeedType, skip: number = 0) => {
    const token = getAuthToken();
    if (!token) return;
    
    setFeedLoading(feedType, true);
    
    try {
      const params = new URLSearchParams({
        feed_type: feedType,
        skip: skip.toString(),
        limit: '20',
      });
      
      const response = await apiFetch(`/api/social/feed?${params}`, { token });
      
      if (!response.ok) {
        throw new Error('Failed to fetch feed');
      }
      
      const data = await response.json();
      
      if (skip === 0) {
        setFeedPosts(feedType, data.posts, data.has_more);
      } else {
        appendFeedPosts(feedType, data.posts, data.has_more);
      }
    } catch (error) {
      console.error('Failed to fetch feed:', error);
      setFeedError(feedType, 'Failed to load feed. Please try again.');
    }
  }, [setFeedPosts, appendFeedPosts, setFeedLoading, setFeedError]);
  
  // Initial fetch
  useEffect(() => {
    if (currentFeed.posts.length === 0 && !currentFeed.isLoading) {
      fetchPosts(currentFeedType, 0);
    }
  }, [currentFeedType, currentFeed.posts.length, currentFeed.isLoading, fetchPosts]);
  
  // Infinite scroll observer
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && currentFeed.hasMore && !currentFeed.isLoading) {
          fetchPosts(currentFeedType, currentFeed.posts.length);
        }
      },
      { threshold: 0.1 }
    );
    
    if (observerTarget.current) {
      observer.observe(observerTarget.current);
    }
    
    return () => observer.disconnect();
  }, [currentFeed.hasMore, currentFeed.isLoading, currentFeed.posts.length, currentFeedType, fetchPosts]);
  
  // Handle feed type change
  const handleFeedTypeChange = useCallback((type: FeedType) => {
    setFeedType(type);
    if (feeds[type].posts.length === 0) {
      fetchPosts(type, 0);
    }
  }, [setFeedType, feeds, fetchPosts]);
  
  // Handle refresh
  const handleRefresh = useCallback(async () => {
    resetFeed(currentFeedType);
    await fetchPosts(currentFeedType, 0);
  }, [currentFeedType, resetFeed, fetchPosts]);
  
  // Pull to refresh state
  const [isPulling, setIsPulling] = React.useState(false);
  const [pullDistance, setPullDistance] = React.useState(0);
  
  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    const target = e.currentTarget as HTMLDivElement;
    if (target.scrollTop === 0) {
      setIsPulling(true);
    }
  }, []);
  
  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    if (!isPulling) return;
    const distance = Math.min(e.touches[0].clientY - 100, 100);
    setPullDistance(distance);
  }, [isPulling]);
  
  const handleTouchEnd = useCallback(() => {
    if (pullDistance > 80) {
      handleRefresh();
    }
    setIsPulling(false);
    setPullDistance(0);
  }, [pullDistance, handleRefresh]);
  
  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Feed Type Tabs */}
      <div className="sticky top-0 z-10 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 border-b">
        <Tabs value={currentFeedType} onValueChange={(v) => handleFeedTypeChange(v as FeedType)}>
          <TabsList className="w-full justify-start px-4 py-2 bg-transparent h-auto">
            {Object.entries(FEED_CONFIGS).map(([type, config]) => (
              <TabsTrigger
                key={type}
                value={type}
                className="flex items-center gap-1.5 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
              >
                {config.icon}
                <span className="hidden sm:inline">{config.label}</span>
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      </div>
      
      {/* Pull to refresh indicator */}
      <motion.div
        initial={{ height: 0 }}
        animate={{ height: pullDistance }}
        className="flex items-center justify-center overflow-hidden"
      >
        <motion.div
          animate={{ rotate: pullDistance > 80 ? 360 : pullDistance * 3.6 }}
          transition={createTransition({ duration: 0.3 })}
        >
          <RefreshCw className="h-6 w-6 text-muted-foreground" />
        </motion.div>
      </motion.div>
      
      {/* Feed Content */}
      <ScrollArea
        ref={scrollRef}
        className="flex-1"
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        <div className="max-w-lg mx-auto p-4 space-y-4">
          {/* Error state */}
          {currentFeed.error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-destructive/10 text-destructive rounded-lg p-4 text-center"
            >
              <p>{currentFeed.error}</p>
              <Button variant="outline" size="sm" onClick={handleRefresh} className="mt-2">
                Try Again
              </Button>
            </motion.div>
          )}
          
          {/* Posts */}
          <AnimatePresence mode="popLayout">
            {currentFeed.posts.map((post, index) => (
              <motion.div
                key={post.id}
                layout
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.9 }}
                transition={createTransition({ delay: index * 0.05 })}
              >
                <SocialPostCard
                  post={post}
                  onCommentClick={() => onPostClick?.(post)}
                  onUserClick={onUserClick}
                  onHashtagClick={onHashtagClick}
                />
              </motion.div>
            ))}
          </AnimatePresence>
          
          {/* Loading skeletons */}
          {currentFeed.isLoading && (
            <div className="space-y-4">
              {Array.from({ length: 3 }).map((_, i) => (
                <SocialPostCardSkeleton key={i} />
              ))}
            </div>
          )}
          
          {/* Empty state */}
          {!currentFeed.isLoading && currentFeed.posts.length === 0 && !currentFeed.error && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-center py-12"
            >
              <div className="text-6xl mb-4">👗</div>
              <h3 className="text-lg font-semibold mb-2">No posts yet</h3>
              <p className="text-muted-foreground mb-4">
                {currentFeedType === 'following'
                  ? 'Follow some stylists to see their outfits here!'
                  : 'Check back soon for new outfit inspiration!'}
              </p>
              {currentFeedType === 'following' && (
                <Button onClick={() => handleFeedTypeChange('discover')}>
                  Discover Stylists
                </Button>
              )}
            </motion.div>
          )}
          
          {/* Load more trigger */}
          <div ref={observerTarget} className="h-4" />
          
          {/* End of feed */}
          {!currentFeed.hasMore && currentFeed.posts.length > 0 && (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-center text-muted-foreground py-4"
            >
              You've reached the end! ✨
            </motion.p>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
