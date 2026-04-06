/**
 * Social Stories Component
 * Instagram-style story highlights with swipe navigation
 */

import React, { useEffect, useCallback, useState } from 'react';
import { motion, AnimatePresence, PanInfo } from 'framer-motion';
import { ChevronLeft, ChevronRight, X, Pause, Play } from 'lucide-react';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';
import { useSocialStore, SocialStoryGroup, SocialStory } from '@/stores/socialStore';
import { apiFetch, getAuthToken } from '@/lib/api';

interface SocialStoriesProps {
  className?: string;
}

export function SocialStoriesBar({ className }: SocialStoriesProps) {
  const { stories, setStories, setStoriesLoading, setActiveStory } = useSocialStore();
  
  useEffect(() => {
    const fetchStories = async () => {
      const token = getAuthToken();
      if (!token) return;
      
      setStoriesLoading(true);
      
      try {
        const response = await apiFetch('/api/social/stories?limit=20', { token });
        if (response.ok) {
          const data = await response.json();
          setStories(data);
        }
      } catch (error) {
        console.error('Failed to fetch stories:', error);
      }
    };
    
    fetchStories();
  }, [setStories, setStoriesLoading]);
  
  if (stories.length === 0) return null;
  
  return (
    <div className={cn('flex gap-4 overflow-x-auto py-4 px-4 scrollbar-hide', className)}>
      {stories.map((group, index) => (
        <StoryAvatar
          key={group.user.id}
          group={group}
          onClick={() => setActiveStory(group.user.id, 0)}
        />
      ))}
    </div>
  );
}

interface StoryAvatarProps {
  group: SocialStoryGroup;
  onClick: () => void;
}

function StoryAvatar({ group, onClick }: StoryAvatarProps) {
  const hasUnseen = group.has_unseen;
  
  return (
    <button
      onClick={onClick}
      className="flex flex-col items-center gap-1.5 flex-shrink-0 group"
    >
      <div
        className={cn(
          'p-0.5 rounded-full transition-all',
          hasUnseen
            ? 'bg-gradient-to-tr from-pink-500 via-red-500 to-yellow-500'
            : 'bg-muted'
        )}
      >
        <Avatar className="h-16 w-16 border-2 border-background group-hover:scale-105 transition-transform">
          <AvatarImage src={group.user.avatar_url || undefined} alt={group.user.name} />
          <AvatarFallback>{group.user.name.slice(0, 2).toUpperCase()}</AvatarFallback>
        </Avatar>
      </div>
      <span className="text-xs text-muted-foreground truncate max-w-[72px]">
        {group.user.name.split(' ')[0]}
      </span>
    </button>
  );
}

// Full-screen story viewer
interface StoryViewerProps {
  isOpen: boolean;
  onClose: () => void;
}

export function StoryViewer({ isOpen, onClose }: StoryViewerProps) {
  const {
    stories,
    activeStoryUserId,
    activeStoryIndex,
    setActiveStory,
    nextStory,
    prevStory,
    markStoryViewed,
  } = useSocialStore();
  
  const [isPaused, setIsPaused] = useState(false);
  const [progress, setProgress] = useState(0);
  
  const activeGroup = stories.find((g) => g.user.id === activeStoryUserId);
  const activeStory = activeGroup?.stories[activeStoryIndex];
  
  // Auto-progress story
  useEffect(() => {
    if (!isOpen || isPaused || !activeStory) return;
    
    const duration = activeStory.media_type === 'video' ? 15000 : 5000;
    const interval = 50;
    const increment = (interval / duration) * 100;
    
    const timer = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          // Mark as viewed and move to next
          markStoryViewed(activeStory.id);
          nextStory();
          return 0;
        }
        return prev + increment;
      });
    }, interval);
    
    return () => clearInterval(timer);
  }, [isOpen, isPaused, activeStory, activeStoryIndex, markStoryViewed, nextStory]);
  
  // Reset progress on story change
  useEffect(() => {
    setProgress(0);
  }, [activeStoryIndex, activeStoryUserId]);
  
  // Handle keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;
      
      switch (e.key) {
        case 'ArrowLeft':
          prevStory();
          break;
        case 'ArrowRight':
          if (activeStory) {
            markStoryViewed(activeStory.id);
          }
          nextStory();
          break;
        case 'Escape':
          onClose();
          break;
        case ' ':
          setIsPaused((p) => !p);
          break;
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, activeStory, markStoryViewed, nextStory, prevStory, onClose]);
  
  // Handle swipe gestures
  const handleDragEnd = useCallback(
    (_: unknown, info: PanInfo) => {
      if (Math.abs(info.offset.x) > 100) {
        if (info.offset.x > 0) {
          prevStory();
        } else {
          if (activeStory) {
            markStoryViewed(activeStory.id);
          }
          nextStory();
        }
      }
    },
    [activeStory, markStoryViewed, nextStory, prevStory]
  );
  
  if (!activeGroup || !activeStory) return null;
  
  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 bg-black"
        >
          {/* Progress bars */}
          <div className="absolute top-4 left-4 right-4 flex gap-1 z-10">
            {activeGroup.stories.map((story, index) => (
              <Progress
                key={story.id}
                value={
                  index < activeStoryIndex
                    ? 100
                    : index === activeStoryIndex
                    ? progress
                    : 0
                }
                className="h-0.5 bg-white/20"
              />
            ))}
          </div>
          
          {/* Header */}
          <header className="absolute top-8 left-4 right-4 flex items-center justify-between z-10">
            <div className="flex items-center gap-3">
              <Avatar className="h-8 w-8 ring-2 ring-white/50">
                <AvatarImage src={activeGroup.user.avatar_url || undefined} />
                <AvatarFallback>{activeGroup.user.name.slice(0, 2).toUpperCase()}</AvatarFallback>
              </Avatar>
              <span className="text-white font-medium text-sm">{activeGroup.user.name}</span>
              <span className="text-white/70 text-xs">
                {getTimeAgo(activeStory.created_at)}
              </span>
            </div>
            
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setIsPaused((p) => !p)}
                className="text-white hover:bg-white/20"
              >
                {isPaused ? <Play className="h-5 w-5" /> : <Pause className="h-5 w-5" />}
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={onClose}
                className="text-white hover:bg-white/20"
              >
                <X className="h-5 w-5" />
              </Button>
            </div>
          </header>
          
          {/* Story content */}
          <motion.div
            drag="x"
            dragConstraints={{ left: 0, right: 0 }}
            dragElastic={0.2}
            onDragEnd={handleDragEnd}
            className="absolute inset-0 flex items-center justify-center"
          >
            {activeStory.media_type === 'video' ? (
              <video
                src={activeStory.media_url}
                className="max-h-full max-w-full object-contain"
                autoPlay
                playsInline
                muted
              />
            ) : (
              <img
                src={activeStory.media_url}
                alt={activeStory.caption || 'Story'}
                className="max-h-full max-w-full object-contain"
              />
            )}
            
            {/* Caption */}
            {activeStory.caption && (
              <div className="absolute bottom-20 left-4 right-4 text-center">
                <p className="text-white text-sm bg-black/30 backdrop-blur-sm rounded-lg px-4 py-2">
                  {activeStory.caption}
                </p>
              </div>
            )}
          </motion.div>
          
          {/* Navigation areas */}
          <button
            onClick={prevStory}
            className="absolute left-0 top-0 bottom-0 w-1/3 cursor-w-resize"
            title="Previous story"
            aria-label="Previous story"
          />
          <button
            onClick={() => {
              markStoryViewed(activeStory.id);
              nextStory();
            }}
            className="absolute right-0 top-0 bottom-0 w-1/3 cursor-e-resize"
            title="Next story"
            aria-label="Next story"
          />
          
          {/* Navigation arrows (for desktop) */}
          <div className="hidden md:flex absolute left-4 top-1/2 -translate-y-1/2">
            <Button
              variant="ghost"
              size="icon"
              onClick={prevStory}
              className="text-white/50 hover:text-white hover:bg-white/20 h-12 w-12"
              disabled={activeStoryIndex === 0}
            >
              <ChevronLeft className="h-8 w-8" />
            </Button>
          </div>
          <div className="hidden md:flex absolute right-4 top-1/2 -translate-y-1/2">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => {
                markStoryViewed(activeStory.id);
                nextStory();
              }}
              className="text-white/50 hover:text-white hover:bg-white/20 h-12 w-12"
              disabled={activeStoryIndex === activeGroup.stories.length - 1}
            >
              <ChevronRight className="h-8 w-8" />
            </Button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// Helper function
function getTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const hours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));
  
  if (hours < 1) return 'Just now';
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}
