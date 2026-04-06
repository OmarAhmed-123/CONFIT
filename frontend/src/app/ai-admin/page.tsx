/**
 * /ai-admin — AI Cost Admin Dashboard
 * Admin-only page for monitoring AI service costs, budgets, and kill-switch.
 */

'use client';

import dynamic from 'next/dynamic';

const AIAdminDashboard = dynamic(
  () => import('@/pages/AIAdminDashboard').then((m) => m.default),
  {
    ssr: false,
    loading: () => (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="animate-spin h-8 w-8 border-4 border-accent border-t-transparent rounded-full" />
      </div>
    ),
  }
);

export default function AIAdminRoutePage() {
  return <AIAdminDashboard />;
}
