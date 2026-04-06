/**
 * CONFIT — useSocialViewModel
 * Encapsulates social feed, lookbooks, post creation, and voting logic.
 * Used by: Social page.
 */

import { useState, useCallback, useEffect } from 'react';
import { apiUrl, apiFetch } from '@/lib/api';
import { getAuthToken } from '@/lib/auth';
import { useToast } from '@/hooks/use-toast';

export type Visibility = 'private' | 'link' | 'public';
export type VoteValue = 'hot' | 'cold';

export interface SocialPostData {
    id: string;
    owner_user_id: string;
    image_url: string;
    caption?: string | null;
    visibility: Visibility;
    created_at: string;
    hot_count: number;
    cold_count: number;
    user_vote?: VoteValue | null;
}

export interface LookbookData {
    id: string;
    stylist_user_id: string;
    title: string;
    description?: string | null;
    items: { product_id: string; note?: string | null }[];
    commission_rate: number;
    visibility: 'public' | 'private';
    created_at: string;
}

export function useSocialViewModel() {
    const { toast } = useToast();
    const token = getAuthToken(); // Note: token might change, but typically we read it once or use a context. 
    // For simple VM, getting it in function body or useEffect is okay.

    const [posts, setPosts] = useState<SocialPostData[]>([]);
    const [lookbooks, setLookbooks] = useState<LookbookData[]>([]);
    const [isLoadingFeed, setIsLoadingFeed] = useState(true);
    const [isLoadingLookbooks, setIsLoadingLookbooks] = useState(true);
    const [isPosting, setIsPosting] = useState(false);

    // ── Fetching ───────────────────────────────────────────────────
    const fetchFeed = useCallback(async () => {
        setIsLoadingFeed(true);
        const currentToken = getAuthToken();
        try {
            const res = await apiFetch('/api/social/feed?visibility=public&limit=30', { token: currentToken });
            if (res.ok) {
                const data = await res.json();
                setPosts(Array.isArray(data) ? data : data?.posts ?? []);
            }
        } catch {
            // ignore
        } finally {
            setIsLoadingFeed(false);
        }
    }, []);

    const fetchLookbooks = useCallback(async () => {
        setIsLoadingLookbooks(true);
        try {
            const res = await apiFetch('/api/social/lookbooks?visibility=public&limit=50');
            if (res.ok) {
                const data = await res.json();
                setLookbooks(Array.isArray(data) ? data : []);
            }
        } catch {
            // ignore
        } finally {
            setIsLoadingLookbooks(false);
        }
    }, []);

    useEffect(() => {
        fetchFeed();
        fetchLookbooks();
    }, [fetchFeed, fetchLookbooks]);


    // ── Actions ────────────────────────────────────────────────────
    const vote = useCallback(async (postId: string, value: VoteValue) => {
        const currentToken = getAuthToken();
        if (!currentToken) {
            toast({ title: 'Sign in required', description: 'Please sign in to vote.', variant: 'destructive' });
            return;
        }

        // Optimistic Update
        setPosts(prev => prev.map(p => {
            if (p.id !== postId) return p;

            // Logic to adjust counts based on previous vote
            // If same vote: toggle off? Or just ignore? Assuming toggle off or re-vote.
            // Let's assume sending the same vote again doesn't toggle off for now, or backend handles it.
            // Simplified optimistic: increment target, decrement old if exists.

            // Actually, correct optimistic logic depends on backend behavior (toggle vs replace).
            // For now, we will wait for server response for the count, 
            // BUT we can update 'user_vote' immediately to show UI feedback.
            return { ...p, user_vote: value };
        }));

        try {
            const res = await apiFetch(`/api/social/posts/${postId}/vote`, {
                method: 'POST',
                token: currentToken,
                body: JSON.stringify({ value }),
            });

            if (res.ok) {
                const updated: SocialPostData = await res.json();
                setPosts(prev => prev.map(p => p.id === postId ? updated : p));
                toast({ title: value === 'hot' ? '🔥 Hot!' : '🧊 Cold!', duration: 1500 });
            } else {
                throw new Error('Vote failed');
            }
        } catch {
            toast({ title: 'Vote failed', variant: 'destructive' });
            fetchFeed(); // Revert on error
        }
    }, [fetchFeed, toast]);

    const createPost = useCallback(async (imageUrl: string, caption: string, visibility: Visibility): Promise<boolean> => {
        const currentToken = getAuthToken();
        if (!currentToken) {
            toast({ title: 'Sign in required', description: 'Please sign in to share a look.', variant: 'destructive' });
            return false;
        }

        if (!imageUrl.trim()) {
            toast({ title: 'Image required', description: 'Please provide an image.', variant: 'destructive' });
            return false;
        }

        setIsPosting(true);
        try {
            const res = await apiFetch('/api/social/posts', {
                method: 'POST',
                token: currentToken,
                body: JSON.stringify({
                    image_url: imageUrl.trim(),
                    caption: caption.trim() || undefined,
                    visibility,
                }),
            });

            if (res.ok) {
                const created: SocialPostData = await res.json();
                setPosts(prev => [created, ...prev]);
                toast({ title: 'Look shared!', description: 'Your post is now live.' });
                return true;
            } else {
                throw new Error('Post failed');
            }
        } catch {
            toast({ title: 'Failed to share look', variant: 'destructive' });
            return false;
        } finally {
            setIsPosting(false);
        }
    }, [toast]);

    return {
        posts,
        lookbooks,
        isLoadingFeed,
        isLoadingLookbooks,
        isPosting,
        vote,
        createPost,
        refreshFeed: fetchFeed,
        refreshLookbooks: fetchLookbooks,
    };
}
