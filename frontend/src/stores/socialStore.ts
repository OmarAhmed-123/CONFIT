/**
 * CONFIT Social Feed Store
 * Zustand store for managing social feed state
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

// ── Types ─────────────────────────────────────────────────────────────────────

export interface SocialUser {
  id: string;
  name: string;
  avatar_url: string | null;
  style_preference?: string | null;
  followers_count?: number;
  following_count?: number;
  is_following?: boolean;
  is_followed_by?: boolean;
}

export interface SocialPostStats {
  like_count: number;
  comment_count: number;
  share_count: number;
  save_count: number;
  view_count: number;
  engagement_rate: number;
  trending_score: number;
}

export interface SocialPost {
  id: string;
  user: SocialUser;
  outfit_id: string | null;
  caption: string | null;
  hashtags: string[];
  image_urls: string[];
  video_url: string | null;
  post_type: 'outfit' | 'lookbook' | 'story';
  visibility: string;
  location: string | null;
  tags: string[];
  is_featured: boolean;
  created_at: string;
  stats: SocialPostStats | null;
  is_liked: boolean;
  is_saved: boolean;
  _score?: number;
}

export interface SocialComment {
  id: string;
  user: SocialUser;
  post_id: string;
  parent_id: string | null;
  content: string;
  mentions: string[];
  is_edited: boolean;
  like_count: number;
  is_liked: boolean;
  reply_count: number;
  created_at: string;
  updated_at: string | null;
}

export interface SocialStory {
  id: string;
  media_url: string;
  media_type: 'image' | 'video';
  caption: string | null;
  view_count: number;
  is_viewed: boolean;
  created_at: string;
  expires_at: string;
}

export interface SocialStoryGroup {
  user: SocialUser;
  stories: SocialStory[];
  has_unseen: boolean;
}

export interface SocialHashtag {
  tag: string;
  post_count: number;
  trending_score: number;
}

export type FeedType = 'home' | 'discover' | 'following' | 'trending';

export interface FeedState {
  posts: SocialPost[];
  hasMore: boolean;
  feedType: FeedType;
  isLoading: boolean;
  error: string | null;
  lastUpdated: string | null;
}

const createInitialFeedState = (type: FeedType): FeedState => ({
  posts: [],
  hasMore: true,
  feedType: type,
  isLoading: false,
  error: null,
  lastUpdated: null,
});

// ── Store State ───────────────────────────────────────────────────────────────

export interface SocialState {
  // Feed
  feeds: Record<FeedType, FeedState>;
  currentFeedType: FeedType;
  
  // Stories
  stories: SocialStoryGroup[];
  storiesLoading: boolean;
  
  // Current post detail
  currentPost: SocialPost | null;
  currentPostComments: SocialComment[];
  commentsLoading: boolean;
  commentsHasMore: boolean;
  
  // User profiles
  userProfiles: Record<string, SocialUser>;
  
  // Trending
  trendingHashtags: SocialHashtag[];
  popularStylists: SocialUser[];
  
  // Saved posts
  savedPosts: SocialPost[];
  savedPostsLoading: boolean;
  
  // Suggestions
  suggestedUsers: SocialUser[];
  
  // UI State
  isCreatingPost: boolean;
  isUploading: boolean;
  activeStoryUserId: string | null;
  activeStoryIndex: number;
  
  // Actions - Feed
  setFeedType: (type: FeedType) => void;
  setFeedPosts: (type: FeedType, posts: SocialPost[], hasMore: boolean) => void;
  appendFeedPosts: (type: FeedType, posts: SocialPost[], hasMore: boolean) => void;
  prependFeedPost: (type: FeedType, post: SocialPost) => void;
  setFeedLoading: (type: FeedType, loading: boolean) => void;
  setFeedError: (type: FeedType, error: string | null) => void;
  resetFeed: (type: FeedType) => void;
  
  // Actions - Post engagement
  likePost: (postId: string) => void;
  unlikePost: (postId: string) => void;
  savePost: (postId: string) => void;
  unsavePost: (postId: string) => void;
  updatePostStats: (postId: string, stats: Partial<SocialPostStats>) => void;
  
  // Actions - Comments
  setCurrentPost: (post: SocialPost | null) => void;
  setComments: (comments: SocialComment[], hasMore: boolean) => void;
  appendComments: (comments: SocialComment[], hasMore: boolean) => void;
  addComment: (comment: SocialComment) => void;
  removeComment: (commentId: string) => void;
  likeComment: (commentId: string) => void;
  unlikeComment: (commentId: string) => void;
  setCommentsLoading: (loading: boolean) => void;
  
  // Actions - Stories
  setStories: (stories: SocialStoryGroup[]) => void;
  markStoryViewed: (storyId: string) => void;
  setActiveStory: (userId: string | null, index?: number) => void;
  nextStory: () => void;
  prevStory: () => void;
  setStoriesLoading: (loading: boolean) => void;
  
  // Actions - User profiles
  setUserProfile: (userId: string, user: SocialUser) => void;
  followUser: (userId: string) => void;
  unfollowUser: (userId: string) => void;
  
  // Actions - Trending
  setTrendingHashtags: (hashtags: SocialHashtag[]) => void;
  setPopularStylists: (stylists: SocialUser[]) => void;
  
  // Actions - Saved
  setSavedPosts: (posts: SocialPost[]) => void;
  setSavedPostsLoading: (loading: boolean) => void;
  
  // Actions - Suggestions
  setSuggestedUsers: (users: SocialUser[]) => void;
  
  // Actions - UI
  setCreatingPost: (creating: boolean) => void;
  setUploading: (uploading: boolean) => void;
  
  // Actions - Reset
  reset: () => void;
}

// ── Initial State ─────────────────────────────────────────────────────────────

const initialState = {
  feeds: {
    home: createInitialFeedState('home'),
    discover: createInitialFeedState('discover'),
    following: createInitialFeedState('following'),
    trending: createInitialFeedState('trending'),
  } as Record<FeedType, FeedState>,
  currentFeedType: 'home' as FeedType,
  stories: [],
  storiesLoading: false,
  currentPost: null,
  currentPostComments: [],
  commentsLoading: false,
  commentsHasMore: true,
  userProfiles: {},
  trendingHashtags: [],
  popularStylists: [],
  savedPosts: [],
  savedPostsLoading: false,
  suggestedUsers: [],
  isCreatingPost: false,
  isUploading: false,
  activeStoryUserId: null,
  activeStoryIndex: 0,
};

// ── Store ─────────────────────────────────────────────────────────────────────

export const useSocialStore = create<SocialState>()(
  persist(
    (set, get) => ({
      ...initialState,
      
      // ── Feed Actions ───────────────────────────────────────────────────────
      
      setFeedType: (type) => set({ currentFeedType: type }),
      
      setFeedPosts: (type, posts, hasMore) =>
        set((state) => ({
          feeds: {
            ...state.feeds,
            [type]: {
              ...state.feeds[type],
              posts,
              hasMore,
              isLoading: false,
              error: null,
              lastUpdated: new Date().toISOString(),
            },
          },
        })),
      
      appendFeedPosts: (type, posts, hasMore) =>
        set((state) => ({
          feeds: {
            ...state.feeds,
            [type]: {
              ...state.feeds[type],
              posts: [...state.feeds[type].posts, ...posts],
              hasMore,
              isLoading: false,
            },
          },
        })),
      
      prependFeedPost: (type, post) =>
        set((state) => ({
          feeds: {
            ...state.feeds,
            [type]: {
              ...state.feeds[type],
              posts: [post, ...state.feeds[type].posts],
            },
          },
        })),
      
      setFeedLoading: (type, loading) =>
        set((state) => ({
          feeds: {
            ...state.feeds,
            [type]: { ...state.feeds[type], isLoading: loading },
          },
        })),
      
      setFeedError: (type, error) =>
        set((state) => ({
          feeds: {
            ...state.feeds,
            [type]: { ...state.feeds[type], error, isLoading: false },
          },
        })),
      
      resetFeed: (type) =>
        set((state) => ({
          feeds: {
            ...state.feeds,
            [type]: createInitialFeedState(type),
          },
        })),
      
      // ── Post Engagement Actions ─────────────────────────────────────────────
      
      likePost: (postId) =>
        set((state) => {
          const feeds = { ...state.feeds };
          const currentFeedType = state.currentFeedType;
          
          // Update in all feeds
          Object.keys(feeds).forEach((feedType) => {
            const feed = feeds[feedType as FeedType];
            const postIndex = feed.posts.findIndex((p) => p.id === postId);
            if (postIndex !== -1) {
              const posts = [...feed.posts];
              posts[postIndex] = {
                ...posts[postIndex],
                is_liked: true,
                stats: posts[postIndex].stats
                  ? {
                      ...posts[postIndex].stats!,
                      like_count: posts[postIndex].stats!.like_count + 1,
                    }
                  : null,
              };
              feeds[feedType as FeedType] = { ...feed, posts };
            }
          });
          
          // Update current post if viewing
          let currentPost = state.currentPost;
          if (currentPost && currentPost.id === postId) {
            currentPost = {
              ...currentPost,
              is_liked: true,
              stats: currentPost.stats
                ? { ...currentPost.stats, like_count: currentPost.stats.like_count + 1 }
                : null,
            };
          }
          
          return { feeds, currentPost };
        }),
      
      unlikePost: (postId) =>
        set((state) => {
          const feeds = { ...state.feeds };
          
          Object.keys(feeds).forEach((feedType) => {
            const feed = feeds[feedType as FeedType];
            const postIndex = feed.posts.findIndex((p) => p.id === postId);
            if (postIndex !== -1) {
              const posts = [...feed.posts];
              posts[postIndex] = {
                ...posts[postIndex],
                is_liked: false,
                stats: posts[postIndex].stats
                  ? {
                      ...posts[postIndex].stats!,
                      like_count: Math.max(0, posts[postIndex].stats!.like_count - 1),
                    }
                  : null,
              };
              feeds[feedType as FeedType] = { ...feed, posts };
            }
          });
          
          let currentPost = state.currentPost;
          if (currentPost && currentPost.id === postId) {
            currentPost = {
              ...currentPost,
              is_liked: false,
              stats: currentPost.stats
                ? { ...currentPost.stats, like_count: Math.max(0, currentPost.stats.like_count - 1) }
                : null,
            };
          }
          
          return { feeds, currentPost };
        }),
      
      savePost: (postId) =>
        set((state) => {
          const feeds = { ...state.feeds };
          
          Object.keys(feeds).forEach((feedType) => {
            const feed = feeds[feedType as FeedType];
            const postIndex = feed.posts.findIndex((p) => p.id === postId);
            if (postIndex !== -1) {
              const posts = [...feed.posts];
              posts[postIndex] = {
                ...posts[postIndex],
                is_saved: true,
                stats: posts[postIndex].stats
                  ? {
                      ...posts[postIndex].stats!,
                      save_count: posts[postIndex].stats!.save_count + 1,
                    }
                  : null,
              };
              feeds[feedType as FeedType] = { ...feed, posts };
            }
          });
          
          let currentPost = state.currentPost;
          if (currentPost && currentPost.id === postId) {
            currentPost = {
              ...currentPost,
              is_saved: true,
              stats: currentPost.stats
                ? { ...currentPost.stats, save_count: currentPost.stats.save_count + 1 }
                : null,
            };
          }
          
          return { feeds, currentPost };
        }),
      
      unsavePost: (postId) =>
        set((state) => {
          const feeds = { ...state.feeds };
          
          Object.keys(feeds).forEach((feedType) => {
            const feed = feeds[feedType as FeedType];
            const postIndex = feed.posts.findIndex((p) => p.id === postId);
            if (postIndex !== -1) {
              const posts = [...feed.posts];
              posts[postIndex] = {
                ...posts[postIndex],
                is_saved: false,
                stats: posts[postIndex].stats
                  ? {
                      ...posts[postIndex].stats!,
                      save_count: Math.max(0, posts[postIndex].stats!.save_count - 1),
                    }
                  : null,
              };
              feeds[feedType as FeedType] = { ...feed, posts };
            }
          });
          
          let currentPost = state.currentPost;
          if (currentPost && currentPost.id === postId) {
            currentPost = {
              ...currentPost,
              is_saved: false,
              stats: currentPost.stats
                ? { ...currentPost.stats, save_count: Math.max(0, currentPost.stats.save_count - 1) }
                : null,
            };
          }
          
          // Remove from saved posts
          const savedPosts = state.savedPosts.filter((p) => p.id !== postId);
          
          return { feeds, currentPost, savedPosts };
        }),
      
      updatePostStats: (postId, stats) =>
        set((state) => {
          const feeds = { ...state.feeds };
          
          Object.keys(feeds).forEach((feedType) => {
            const feed = feeds[feedType as FeedType];
            const postIndex = feed.posts.findIndex((p) => p.id === postId);
            if (postIndex !== -1) {
              const posts = [...feed.posts];
              posts[postIndex] = {
                ...posts[postIndex],
                stats: posts[postIndex].stats
                  ? { ...posts[postIndex].stats!, ...stats }
                  : null,
              };
              feeds[feedType as FeedType] = { ...feed, posts };
            }
          });
          
          return { feeds };
        }),
      
      // ── Comment Actions ─────────────────────────────────────────────────────
      
      setCurrentPost: (post) => set({ currentPost: post, currentPostComments: [] }),
      
      setComments: (comments, hasMore) =>
        set({
          currentPostComments: comments,
          commentsHasMore: hasMore,
          commentsLoading: false,
        }),
      
      appendComments: (comments, hasMore) =>
        set((state) => ({
          currentPostComments: [...state.currentPostComments, ...comments],
          commentsHasMore: hasMore,
          commentsLoading: false,
        })),
      
      addComment: (comment) =>
        set((state) => ({
          currentPostComments: [comment, ...state.currentPostComments],
        })),
      
      removeComment: (commentId) =>
        set((state) => ({
          currentPostComments: state.currentPostComments.filter((c) => c.id !== commentId),
        })),
      
      likeComment: (commentId) =>
        set((state) => ({
          currentPostComments: state.currentPostComments.map((c) =>
            c.id === commentId
              ? { ...c, is_liked: true, like_count: c.like_count + 1 }
              : c
          ),
        })),
      
      unlikeComment: (commentId) =>
        set((state) => ({
          currentPostComments: state.currentPostComments.map((c) =>
            c.id === commentId
              ? { ...c, is_liked: false, like_count: Math.max(0, c.like_count - 1) }
              : c
          ),
        })),
      
      setCommentsLoading: (loading) => set({ commentsLoading: loading }),
      
      // ── Story Actions ───────────────────────────────────────────────────────
      
      setStories: (stories) =>
        set({ stories, storiesLoading: false }),
      
      markStoryViewed: (storyId) =>
        set((state) => ({
          stories: state.stories.map((group) => ({
            ...group,
            stories: group.stories.map((story) =>
              story.id === storyId ? { ...story, is_viewed: true } : story
            ),
            has_unseen: group.stories.some((s) => s.id !== storyId && !s.is_viewed),
          })),
        })),
      
      setActiveStory: (userId, index = 0) =>
        set({ activeStoryUserId: userId, activeStoryIndex: index }),
      
      nextStory: () =>
        set((state) => {
          const group = state.stories.find((g) => g.user.id === state.activeStoryUserId);
          if (!group) return { activeStoryUserId: null, activeStoryIndex: 0 };
          
          const nextIndex = state.activeStoryIndex + 1;
          if (nextIndex >= group.stories.length) {
            // Move to next user's stories
            const currentGroupIndex = state.stories.findIndex(
              (g) => g.user.id === state.activeStoryUserId
            );
            const nextGroup = state.stories[currentGroupIndex + 1];
            if (nextGroup) {
              return { activeStoryUserId: nextGroup.user.id, activeStoryIndex: 0 };
            }
            return { activeStoryUserId: null, activeStoryIndex: 0 };
          }
          
          return { activeStoryIndex: nextIndex };
        }),
      
      prevStory: () =>
        set((state) => {
          if (state.activeStoryIndex > 0) {
            return { activeStoryIndex: state.activeStoryIndex - 1 };
          }
          
          // Move to previous user's stories
          const currentGroupIndex = state.stories.findIndex(
            (g) => g.user.id === state.activeStoryUserId
          );
          const prevGroup = state.stories[currentGroupIndex - 1];
          if (prevGroup) {
            return {
              activeStoryUserId: prevGroup.user.id,
              activeStoryIndex: prevGroup.stories.length - 1,
            };
          }
          
          return state;
        }),
      
      setStoriesLoading: (loading) => set({ storiesLoading: loading }),
      
      // ── User Profile Actions ────────────────────────────────────────────────
      
      setUserProfile: (userId, user) =>
        set((state) => ({
          userProfiles: { ...state.userProfiles, [userId]: user },
        })),
      
      followUser: (userId) =>
        set((state) => {
          const userProfiles = { ...state.userProfiles };
          if (userProfiles[userId]) {
            userProfiles[userId] = {
              ...userProfiles[userId],
              is_following: true,
              followers_count: (userProfiles[userId].followers_count || 0) + 1,
            };
          }
          
          // Update in popular stylists
          const popularStylists = state.popularStylists.map((s) =>
            s.id === userId
              ? { ...s, is_following: true, followers_count: (s.followers_count || 0) + 1 }
              : s
          );
          
          // Update in suggested users
          const suggestedUsers = state.suggestedUsers.map((s) =>
            s.id === userId
              ? { ...s, is_following: true, followers_count: (s.followers_count || 0) + 1 }
              : s
          );
          
          // Update in posts
          const feeds = { ...state.feeds };
          Object.keys(feeds).forEach((feedType) => {
            const feed = feeds[feedType as FeedType];
            feeds[feedType as FeedType] = {
              ...feed,
              posts: feed.posts.map((p) =>
                p.user.id === userId
                  ? { ...p, user: { ...p.user, is_following: true } }
                  : p
              ),
            };
          });
          
          return { userProfiles, popularStylists, suggestedUsers, feeds };
        }),
      
      unfollowUser: (userId) =>
        set((state) => {
          const userProfiles = { ...state.userProfiles };
          if (userProfiles[userId]) {
            userProfiles[userId] = {
              ...userProfiles[userId],
              is_following: false,
              followers_count: Math.max(0, (userProfiles[userId].followers_count || 1) - 1),
            };
          }
          
          const popularStylists = state.popularStylists.map((s) =>
            s.id === userId
              ? { ...s, is_following: false, followers_count: Math.max(0, (s.followers_count || 1) - 1) }
              : s
          );
          
          const suggestedUsers = state.suggestedUsers.filter((s) => s.id !== userId);
          
          const feeds = { ...state.feeds };
          Object.keys(feeds).forEach((feedType) => {
            const feed = feeds[feedType as FeedType];
            feeds[feedType as FeedType] = {
              ...feed,
              posts: feed.posts.map((p) =>
                p.user.id === userId
                  ? { ...p, user: { ...p.user, is_following: false } }
                  : p
              ),
            };
          });
          
          return { userProfiles, popularStylists, suggestedUsers, feeds };
        }),
      
      // ── Trending Actions ────────────────────────────────────────────────────
      
      setTrendingHashtags: (hashtags) => set({ trendingHashtags: hashtags }),
      
      setPopularStylists: (stylists) => set({ popularStylists: stylists }),
      
      // ── Saved Actions ────────────────────────────────────────────────────────
      
      setSavedPosts: (posts) => set({ savedPosts: posts, savedPostsLoading: false }),
      
      setSavedPostsLoading: (loading) => set({ savedPostsLoading: loading }),
      
      // ── Suggestions Actions ─────────────────────────────────────────────────
      
      setSuggestedUsers: (users) => set({ suggestedUsers: users }),
      
      // ── UI Actions ──────────────────────────────────────────────────────────
      
      setCreatingPost: (creating) => set({ isCreatingPost: creating }),
      
      setUploading: (uploading) => set({ isUploading: uploading }),
      
      // ── Reset ───────────────────────────────────────────────────────────────
      
      reset: () => set(initialState),
    }),
    {
      name: 'confit-social',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        currentFeedType: state.currentFeedType,
        trendingHashtags: state.trendingHashtags,
      }),
    }
  )
);

// ── Selectors ─────────────────────────────────────────────────────────────────

export const selectCurrentFeed = (state: SocialState) => state.feeds[state.currentFeedType];

export const selectFeedPosts = (feedType: FeedType) => (state: SocialState) =>
  state.feeds[feedType].posts;

export const selectIsPostLiked = (postId: string) => (state: SocialState) => {
  const feed = state.feeds[state.currentFeedType];
  const post = feed.posts.find((p) => p.id === postId);
  return post?.is_liked ?? false;
};

export const selectIsPostSaved = (postId: string) => (state: SocialState) => {
  const feed = state.feeds[state.currentFeedType];
  const post = feed.posts.find((p) => p.id === postId);
  return post?.is_saved ?? false;
};

export const selectActiveStory = (state: SocialState) => {
  if (!state.activeStoryUserId) return null;
  const group = state.stories.find((g) => g.user.id === state.activeStoryUserId);
  if (!group) return null;
  return group.stories[state.activeStoryIndex] || null;
};

export const selectActiveStoryGroup = (state: SocialState) => {
  if (!state.activeStoryUserId) return null;
  return state.stories.find((g) => g.user.id === state.activeStoryUserId) || null;
};
