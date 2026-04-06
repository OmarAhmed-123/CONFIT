/**
 * CONFIT — useChallengesViewModel
 * Handles daily quest loading, leaderboard, and challenge submission.
 * Used by: StyleChallenges page.
 */

import { useState, useCallback, useEffect } from 'react';
import { apiFetch } from '@/lib/api';
import { getAuthToken } from '@/lib/auth';
import { useToast } from '@/hooks/use-toast';

export interface Quest {
    id: string;
    title: string;
    description: string;
    type: string;
    reward_points: number;
    reward_badge: string | null;
    icon: string;
    constraint_json: Record<string, unknown>;
    is_active: boolean;
    expires_at: string | null;
    created_at: string;
}

export interface LeaderboardEntry {
    id: string;
    total_points: number;
    confidence_score: number;
    level: number;
    badges: string[];
    current_streak: number;
    longest_streak: number;
    updated_at: string;
    created_at: string;
}

export function useChallengesViewModel() {
    const { toast } = useToast();
    const token = getAuthToken();

    const [quest, setQuest] = useState<Quest | null>(null);
    const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isSubmitting, setIsSubmitting] = useState(false);

    const load = useCallback(async () => {
        setIsLoading(true);
        try {
            const qRes = await apiFetch('/api/challenges/quests');
            if (!qRes.ok) return;
            const quests: Quest[] = await qRes.json();
            if (quests.length > 0) {
                setQuest(quests[0]); // Use first active quest
            }

            const lbRes = await apiFetch('/api/challenges/leaderboard');
            if (lbRes.ok) {
                const data: LeaderboardEntry[] = await lbRes.json();
                setLeaderboard(data);
            }
        } catch {
            // silent — no quest available or error
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        load();
    }, [load]);

    const submit = useCallback(async () => {
        if (!quest) return;
        const currentToken = getAuthToken();
        if (!currentToken) {
            toast({ title: 'Sign in required', description: 'Please log in to submit a challenge.', variant: 'destructive' });
            return;
        }
        setIsSubmitting(true);
        try {
            const res = await apiFetch(`/api/challenges/quests/${quest.id}/complete`, {
                method: 'POST',
                token: currentToken,
                body: JSON.stringify({ points_earned: quest.reward_points }),
            });

            if (!res.ok) throw new Error('Submission failed');

            const data = await res.json();
            toast({ title: 'Quest completed!', description: `Earned ${data.points_earned} points!` });

            // Refresh data
            load();
        } catch {
            toast({ title: 'Completion failed', description: 'Please try again.', variant: 'destructive' });
        } finally {
            setIsSubmitting(false);
        }
    }, [quest, toast, load]);

    return {
        quest,
        leaderboard,
        isLoading,
        isSubmitting,
        submit,
        refresh: load,
    };
}
