/**
 * Session Utilities
 * Server-side session access and authentication helpers
 */

import { getServerSession } from 'next-auth';
import { authOptions } from './auth.config';

/**
 * Get the current session on the server side
 */
export async function getAuthSession() {
  return getServerSession(authOptions);
}

/**
 * Require authentication - throws if not authenticated
 */
export async function requireAuth() {
  const session = await getAuthSession();
  
  if (!session?.accessToken) {
    throw new Error('Authentication required');
  }
  
  return session;
}

/**
 * Get access token for API calls
 */
export async function getAccessToken(): Promise<string | null> {
  const session = await getAuthSession();
  return session?.accessToken || null;
}
