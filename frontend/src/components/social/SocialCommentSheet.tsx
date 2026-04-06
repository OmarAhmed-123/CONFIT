/**
 * Social Comment Sheet Component
 * Bottom sheet for viewing and adding comments
 */

import React, { useEffect, useState, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Heart, MoreHorizontal, AtSign, Smile } from 'lucide-react';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import { useSocialStore, SocialComment, SocialPost } from '@/stores/socialStore';
import { apiFetch, getAuthToken } from '@/lib/api';

interface SocialCommentSheetProps {
  post: SocialPost | null;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  trigger?: React.ReactNode;
}

export function SocialCommentSheet({
  post,
  open,
  onOpenChange,
  trigger,
}: SocialCommentSheetProps) {
  const [commentText, setCommentText] = useState('');
  const [replyTo, setReplyTo] = useState<SocialComment | null>(null);
  const observerTarget = useRef<HTMLDivElement>(null);
  
  const {
    currentPostComments,
    commentsLoading,
    commentsHasMore,
    setCurrentPost,
    setComments,
    appendComments,
    addComment,
    likeComment,
    unlikeComment,
    setCommentsLoading,
  } = useSocialStore();
  
  // Fetch comments when post changes
  useEffect(() => {
    if (post && open) {
      fetchComments(post.id, 0);
    } else if (!open) {
      setCommentText('');
      setReplyTo(null);
    }
  }, [post?.id, open]);
  
  const fetchComments = async (postId: string, skip: number) => {
    const token = getAuthToken();
    if (!token) return;
    
    setCommentsLoading(true);
    
    try {
      const params = new URLSearchParams({
        skip: skip.toString(),
        limit: '20',
        sort: 'newest',
      });
      
      const response = await apiFetch(`/api/social/posts/${postId}/comments?${params}`, { token });
      
      if (response.ok) {
        const data = await response.json();
        if (skip === 0) {
          setComments(data, data.length === 20);
        } else {
          appendComments(data, data.length === 20);
        }
      }
    } catch (error) {
      console.error('Failed to fetch comments:', error);
    } finally {
      setCommentsLoading(false);
    }
  };
  
  // Infinite scroll
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && commentsHasMore && !commentsLoading && post) {
          fetchComments(post.id, currentPostComments.length);
        }
      },
      { threshold: 0.1 }
    );
    
    if (observerTarget.current) {
      observer.observe(observerTarget.current);
    }
    
    return () => observer.disconnect();
  }, [commentsHasMore, commentsLoading, post?.id, currentPostComments.length]);
  
  const handleSubmitComment = useCallback(async () => {
    if (!commentText.trim() || !post) return;
    
    const token = getAuthToken();
    if (!token) return;
    
    try {
      const response = await apiFetch(`/api/social/posts/${post.id}/comments`, {
        token,
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: commentText.trim(),
          parent_id: replyTo?.id,
        }),
      });
      
      if (response.ok) {
        const newComment = await response.json();
        addComment(newComment);
        setCommentText('');
        setReplyTo(null);
      }
    } catch (error) {
      console.error('Failed to post comment:', error);
    }
  }, [commentText, post?.id, replyTo?.id, addComment]);
  
  const handleLikeComment = useCallback(
    async (comment: SocialComment) => {
      const token = getAuthToken();
      if (!token) return;
      
      try {
        if (comment.is_liked) {
          await apiFetch(`/api/social/comments/${comment.id}/like`, {
            token,
            method: 'DELETE',
          });
          unlikeComment(comment.id);
        } else {
          await apiFetch(`/api/social/comments/${comment.id}/like`, {
            token,
            method: 'POST',
          });
          likeComment(comment.id);
        }
      } catch (error) {
        console.error('Failed to toggle like:', error);
      }
    },
    [likeComment, unlikeComment]
  );
  
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      {trigger && <SheetTrigger asChild>{trigger}</SheetTrigger>}
      <SheetContent side="bottom" className="h-[80vh] max-h-[800px] flex flex-col p-0">
        <SheetHeader className="px-4 py-3 border-b">
          <SheetTitle className="text-left">
            Comments {post?.stats?.comment_count ? `(${post.stats.comment_count})` : ''}
          </SheetTitle>
        </SheetHeader>
        
        {/* Comments list */}
        <ScrollArea className="flex-1 px-4">
          <div className="py-4 space-y-4">
            {currentPostComments.map((comment) => (
              <CommentItem
                key={comment.id}
                comment={comment}
                onLike={() => handleLikeComment(comment)}
                onReply={() => setReplyTo(comment)}
              />
            ))}
            
            {commentsLoading && (
              <div className="space-y-4">
                {Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className="flex gap-3 animate-pulse">
                    <div className="h-10 w-10 rounded-full bg-muted" />
                    <div className="flex-1 space-y-2">
                      <div className="h-4 w-24 bg-muted rounded" />
                      <div className="h-4 w-full bg-muted rounded" />
                    </div>
                  </div>
                ))}
              </div>
            )}
            
            {!commentsLoading && currentPostComments.length === 0 && (
              <div className="text-center py-8 text-muted-foreground">
                <p>No comments yet. Be the first to comment!</p>
              </div>
            )}
            
            <div ref={observerTarget} className="h-4" />
          </div>
        </ScrollArea>
        
        {/* Reply indicator */}
        <AnimatePresence>
          {replyTo && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="border-t px-4 py-2 bg-muted/50 flex items-center justify-between"
            >
              <span className="text-sm text-muted-foreground">
                Replying to <span className="font-medium text-foreground">{replyTo.user.name}</span>
              </span>
              <Button variant="ghost" size="sm" onClick={() => setReplyTo(null)}>
                Cancel
              </Button>
            </motion.div>
          )}
        </AnimatePresence>
        
        {/* Comment input */}
        <div className="border-t px-4 py-3 flex items-center gap-3">
          <Avatar className="h-8 w-8">
            <AvatarFallback>U</AvatarFallback>
          </Avatar>
          
          <div className="flex-1 flex items-center gap-2">
            <Input
              value={commentText}
              onChange={(e) => setCommentText(e.target.value)}
              placeholder={replyTo ? `Reply to ${replyTo.user.name}...` : 'Add a comment...'}
              className="flex-1"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmitComment();
                }
              }}
            />
            <Button
              size="icon"
              variant="ghost"
              disabled={!commentText.trim()}
              onClick={handleSubmitComment}
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}

interface CommentItemProps {
  comment: SocialComment;
  onLike: () => void;
  onReply: () => void;
}

function CommentItem({ comment, onLike, onReply }: CommentItemProps) {
  return (
    <div className="flex gap-3">
      <Avatar className="h-10 w-10 flex-shrink-0">
        <AvatarImage src={comment.user.avatar_url || undefined} />
        <AvatarFallback>{comment.user.name.slice(0, 2).toUpperCase()}</AvatarFallback>
      </Avatar>
      
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <div>
            <span className="font-semibold text-sm">{comment.user.name}</span>
            <span className="text-muted-foreground text-xs ml-2">
              {getTimeAgo(comment.created_at)}
            </span>
          </div>
          <Button variant="ghost" size="icon" className="h-6 w-6">
            <MoreHorizontal className="h-3 w-3" />
          </Button>
        </div>
        
        <p className="text-sm mt-1 break-words">{comment.content}</p>
        
        <div className="flex items-center gap-4 mt-2">
          <button
            onClick={onLike}
            className={cn(
              'text-xs font-medium flex items-center gap-1 transition-colors',
              comment.is_liked ? 'text-red-500' : 'text-muted-foreground hover:text-foreground'
            )}
          >
            <Heart
              className={cn('h-3 w-3', comment.is_liked && 'fill-current')}
            />
            {comment.like_count > 0 && comment.like_count}
          </button>
          
          <button
            onClick={onReply}
            className="text-xs text-muted-foreground hover:text-foreground font-medium"
          >
            Reply
          </button>
          
          {comment.reply_count > 0 && (
            <span className="text-xs text-muted-foreground">
              {comment.reply_count} {comment.reply_count === 1 ? 'reply' : 'replies'}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

function getTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);
  
  if (seconds < 60) return 'Just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;
  if (seconds < 604800) return `${Math.floor(seconds / 86400)}d`;
  return date.toLocaleDateString();
}
