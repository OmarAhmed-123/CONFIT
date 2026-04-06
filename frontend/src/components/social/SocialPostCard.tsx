/**
 * Social Post Card Component
 * Instagram-style card with engagement buttons and animations
 */

import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Heart, MessageCircle, Share2, Bookmark, MoreHorizontal, MapPin } from 'lucide-react';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { useSocialStore, SocialPost } from '@/stores/socialStore';
import { formatDistanceToNow } from '@/lib/utils';
import { createTransition } from '@/motion';

interface SocialPostCardProps {
  post: SocialPost;
  onCommentClick?: () => void;
  onUserClick?: (userId: string) => void;
  onHashtagClick?: (hashtag: string) => void;
  showStats?: boolean;
}

export function SocialPostCard({
  post,
  onCommentClick,
  onUserClick,
  onHashtagClick,
  showStats = true,
}: SocialPostCardProps) {
  const [isImageLoaded, setIsImageLoaded] = useState(false);
  const [showHeart, setShowHeart] = useState(false);
  const [currentImageIndex, setCurrentImageIndex] = useState(0);
  
  const { likePost, unlikePost, savePost, unsavePost } = useSocialStore();
  
  const handleLike = useCallback(() => {
    if (post.is_liked) {
      unlikePost(post.id);
    } else {
      likePost(post.id);
      // Show heart animation
      setShowHeart(true);
      setTimeout(() => setShowHeart(false), 800);
    }
  }, [post.id, post.is_liked, likePost, unlikePost]);
  
  const handleSave = useCallback(() => {
    if (post.is_saved) {
      unsavePost(post.id);
    } else {
      savePost(post.id);
    }
  }, [post.id, post.is_saved, savePost, unsavePost]);
  
  const handleDoubleTap = useCallback(() => {
    if (!post.is_liked) {
      likePost(post.id);
      setShowHeart(true);
      setTimeout(() => setShowHeart(false), 800);
    }
  }, [post.id, post.is_liked, likePost]);
  
  const handleShare = useCallback(async () => {
    try {
      if (navigator.share) {
        await navigator.share({
          title: 'Check out this outfit!',
          url: window.location.href,
        });
      }
    } catch (error) {
      console.error('Share failed:', error);
    }
  }, []);
  
  const handlePrevImage = useCallback(() => {
    setCurrentImageIndex((prev) => Math.max(0, prev - 1));
  }, []);
  
  const handleNextImage = useCallback(() => {
    setCurrentImageIndex((prev) => Math.min(post.image_urls.length - 1, prev + 1));
  }, [post.image_urls.length]);
  
  const renderHashtags = useCallback((text: string) => {
    const parts = text.split(/(\s+)/);
    return parts.map((part, index) => {
      if (part.startsWith('#')) {
        return (
          <button
            key={index}
            onClick={() => onHashtagClick?.(part.slice(1))}
            className="text-primary hover:underline font-medium"
          >
            {part}
          </button>
        );
      }
      return part;
    });
  }, [onHashtagClick]);
  
  return (
    <article className="bg-card rounded-xl overflow-hidden shadow-sm border border-border/50">
      {/* Header */}
      <header className="flex items-center justify-between p-3">
        <button
          onClick={() => onUserClick?.(post.user.id)}
          className="flex items-center gap-3 hover:opacity-80 transition-opacity"
        >
          <Avatar className="h-10 w-10 ring-2 ring-background">
            <AvatarImage src={post.user.avatar_url || undefined} alt={post.user.name} />
            <AvatarFallback>{post.user.name.slice(0, 2).toUpperCase()}</AvatarFallback>
          </Avatar>
          <div className="flex flex-col items-start">
            <span className="font-semibold text-sm">{post.user.name}</span>
            {post.location && (
              <span className="text-xs text-muted-foreground flex items-center gap-1">
                <MapPin className="h-3 w-3" />
                {post.location}
              </span>
            )}
          </div>
        </button>
        
        <Button variant="ghost" size="icon" className="h-8 w-8">
          <MoreHorizontal className="h-4 w-4" />
        </Button>
      </header>
      
      {/* Image Carousel */}
      <div
        className="relative aspect-[4/5] bg-muted overflow-hidden"
        onDoubleClick={handleDoubleTap}
      >
        {/* Loading skeleton */}
        {!isImageLoaded && (
          <div className="absolute inset-0 bg-muted animate-pulse" />
        )}
        
        {/* Main image */}
        <img
          src={post.image_urls[currentImageIndex]}
          alt={post.caption || 'Outfit post'}
          className={cn(
            'w-full h-full object-cover transition-opacity duration-300',
            isImageLoaded ? 'opacity-100' : 'opacity-0'
          )}
          onLoad={() => setIsImageLoaded(true)}
        />
        
        {/* Double-tap heart animation */}
        <AnimatePresence>
          {showHeart && (
            <motion.div
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 1.5, opacity: 0 }}
              transition={createTransition({ duration: 0.4 })}
              className="absolute inset-0 flex items-center justify-center pointer-events-none"
            >
              <Heart className="h-24 w-24 text-white fill-white drop-shadow-lg" />
            </motion.div>
          )}
        </AnimatePresence>
        
        {/* Image navigation dots */}
        {post.image_urls.length > 1 && (
          <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex gap-1.5">
            {post.image_urls.map((_, index) => (
              <button
                key={index}
                onClick={() => setCurrentImageIndex(index)}
                className={cn(
                  'w-1.5 h-1.5 rounded-full transition-all',
                  index === currentImageIndex
                    ? 'bg-white w-4'
                    : 'bg-white/50 hover:bg-white/70'
                )}
                title={`Go to image ${index + 1}`}
                aria-label={`Go to image ${index + 1}`}
              />
            ))}
          </div>
        )}
        
        {/* Swipe areas for navigation */}
        {post.image_urls.length > 1 && (
          <>
            <button
              onClick={handlePrevImage}
              className="absolute left-0 top-0 bottom-0 w-1/3 cursor-w-resize"
              disabled={currentImageIndex === 0}
              title="Previous image"
              aria-label="Previous image"
            />
            <button
              onClick={handleNextImage}
              className="absolute right-0 top-0 bottom-0 w-1/3 cursor-e-resize"
              disabled={currentImageIndex === post.image_urls.length - 1}
              title="Next image"
              aria-label="Next image"
            />
          </>
        )}
        
        {/* Featured badge */}
        {post.is_featured && (
          <div className="absolute top-3 right-3">
            <Badge variant="secondary" className="bg-primary/90 text-primary-foreground">
              Featured
            </Badge>
          </div>
        )}
      </div>
      
      {/* Engagement Actions */}
      <div className="p-3">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-1">
            {/* Like button */}
            <motion.button
              whileTap={{ scale: 0.9 }}
              onClick={handleLike}
              className="p-2 rounded-full hover:bg-muted transition-colors"
            >
              <motion.div
                animate={post.is_liked ? { scale: [1, 1.2, 1] } : {}}
                transition={createTransition({ duration: 0.3 })}
              >
                <Heart
                  className={cn(
                    'h-6 w-6 transition-colors',
                    post.is_liked
                      ? 'text-red-500 fill-red-500'
                      : 'text-foreground'
                  )}
                />
              </motion.div>
            </motion.button>
            
            {/* Comment button */}
            <motion.button
              whileTap={{ scale: 0.9 }}
              onClick={onCommentClick}
              className="p-2 rounded-full hover:bg-muted transition-colors"
            >
              <MessageCircle className="h-6 w-6" />
            </motion.button>
            
            {/* Share button */}
            <motion.button
              whileTap={{ scale: 0.9 }}
              onClick={handleShare}
              className="p-2 rounded-full hover:bg-muted transition-colors"
            >
              <Share2 className="h-6 w-6" />
            </motion.button>
          </div>
          
          {/* Save button */}
          <motion.button
            whileTap={{ scale: 0.9 }}
            onClick={handleSave}
            className="p-2 rounded-full hover:bg-muted transition-colors"
          >
            <Bookmark
              className={cn(
                'h-6 w-6 transition-colors',
                post.is_saved ? 'fill-foreground' : ''
              )}
            />
          </motion.button>
        </div>
        
        {/* Stats */}
        {showStats && post.stats && (
          <div className="mb-2">
            {post.stats.like_count > 0 && (
              <p className="text-sm font-semibold">
                {post.stats.like_count.toLocaleString()} likes
              </p>
            )}
          </div>
        )}
        
        {/* Caption */}
        {post.caption && (
          <p className="text-sm leading-relaxed">
            <button
              onClick={() => onUserClick?.(post.user.id)}
              className="font-semibold hover:underline"
            >
              {post.user.name}
            </button>{' '}
            <span className="whitespace-pre-wrap">
              {renderHashtags(post.caption)}
            </span>
          </p>
        )}
        
        {/* Hashtags */}
        {post.hashtags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {post.hashtags.slice(0, 5).map((tag) => (
              <button
                key={tag}
                onClick={() => onHashtagClick?.(tag)}
                className="text-xs text-primary hover:underline"
              >
                #{tag}
              </button>
            ))}
            {post.hashtags.length > 5 && (
              <span className="text-xs text-muted-foreground">
                +{post.hashtags.length - 5} more
              </span>
            )}
          </div>
        )}
        
        {/* Comment count */}
        {post.stats && post.stats.comment_count > 0 && (
          <button
            onClick={onCommentClick}
            className="text-sm text-muted-foreground mt-1 hover:text-foreground transition-colors"
          >
            View all {post.stats.comment_count} comments
          </button>
        )}
        
        {/* Timestamp */}
        <time className="text-xs text-muted-foreground mt-2 block">
          {formatDistanceToNow(new Date(post.created_at))} ago
        </time>
      </div>
    </article>
  );
}

// Skeleton component for loading state
export function SocialPostCardSkeleton() {
  return (
    <article className="bg-card rounded-xl overflow-hidden shadow-sm border border-border/50 animate-pulse">
      {/* Header skeleton */}
      <header className="flex items-center justify-between p-3">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-full bg-muted" />
          <div className="space-y-2">
            <div className="h-4 w-24 bg-muted rounded" />
            <div className="h-3 w-16 bg-muted rounded" />
          </div>
        </div>
      </header>
      
      {/* Image skeleton */}
      <div className="aspect-[4/5] bg-muted" />
      
      {/* Actions skeleton */}
      <div className="p-3 space-y-3">
        <div className="flex justify-between">
          <div className="flex gap-1">
            <div className="h-10 w-10 rounded-full bg-muted" />
            <div className="h-10 w-10 rounded-full bg-muted" />
            <div className="h-10 w-10 rounded-full bg-muted" />
          </div>
          <div className="h-10 w-10 rounded-full bg-muted" />
        </div>
        <div className="h-4 w-20 bg-muted rounded" />
        <div className="space-y-2">
          <div className="h-4 w-full bg-muted rounded" />
          <div className="h-4 w-3/4 bg-muted rounded" />
        </div>
      </div>
    </article>
  );
}
