/**
 * NextAuth API Route Handler
 * Handles all authentication requests
 * 
 * Note: Moved to /api/nextauth to avoid intercepting backend /api/auth/* routes
 */

import NextAuth from 'next-auth';
import { authOptions } from '@/lib/auth/auth.config';

const handler = NextAuth(authOptions);

export { handler as GET, handler as POST };
