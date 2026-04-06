/**
 * NextAuth.js Configuration
 * Handles Google and Apple OAuth with backend token validation
 */

import type { NextAuthOptions } from 'next-auth';
import GoogleProvider from 'next-auth/providers/google';
import AppleProvider from 'next-auth/providers/apple';
import CredentialsProvider from 'next-auth/providers/credentials';
import { JWT } from 'next-auth/jwt';

// In development, use empty string to leverage Next.js rewrites (proxy to backend)
// In production, use the explicit backend URL
const isDev = process.env.NODE_ENV === 'development';
const API_BASE_URL = isDev ? '' : (process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8001');

const googleClientId =
  process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || process.env.GOOGLE_CLIENT_ID || '';
const googleClientSecret = process.env.GOOGLE_CLIENT_SECRET || '';
const appleClientId =
  process.env.NEXT_PUBLIC_APPLE_CLIENT_ID || process.env.APPLE_CLIENT_ID || '';
const appleClientSecret = process.env.APPLE_CLIENT_SECRET || '';

const providers: NextAuthOptions['providers'] = [];

if (googleClientId && googleClientSecret) {
  providers.push(
    GoogleProvider({
      clientId: googleClientId,
      clientSecret: googleClientSecret,
      authorization: {
        params: {
          prompt: 'consent',
          access_type: 'offline',
          scope: 'openid email profile',
        },
      },
    })
  );
} else if ((googleClientId || googleClientSecret) && process.env.NODE_ENV !== 'production') {
  console.warn(
    '[auth] Google OAuth is partially configured. Set NEXT_PUBLIC_GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.'
  );
}

if (appleClientId && appleClientSecret) {
  providers.push(
    AppleProvider({
      clientId: appleClientId,
      clientSecret: appleClientSecret,
      authorization: {
        params: {
          scope: 'name email',
          response_mode: 'form_post',
        },
      },
    })
  );
} else if ((appleClientId || appleClientSecret) && process.env.NODE_ENV !== 'production') {
  console.warn(
    '[auth] Apple Sign-In is partially configured. Set NEXT_PUBLIC_APPLE_CLIENT_ID and APPLE_CLIENT_SECRET.'
  );
}

// Extend NextAuth types
declare module 'next-auth' {
  interface Session {
    accessToken: string;
    refreshToken: string;
    user: {
      id: string;
      email: string;
      name: string;
      image?: string;
      roles?: string[];
    };
  }
}

declare module 'next-auth/jwt' {
  interface JWT {
    accessToken: string;
    refreshToken: string;
    userId: string;
    roles?: string[];
  }
}

export const authOptions: NextAuthOptions = {
  providers: [
    ...providers,
    // Credentials Provider (for email/password login)
    CredentialsProvider({
      name: 'Email & Password',
      credentials: {
        email: { label: 'Email', type: 'email' },
        password: { label: 'Password', type: 'password' },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) {
          throw new Error('Email and password required');
        }

        try {
          const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              email: credentials.email,
              password: credentials.password,
            }),
          });

          if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Invalid credentials');
          }

          const data = await response.json();

          return {
            id: data.user?.id || '',
            email: data.user?.email || credentials.email,
            name: data.user?.name || '',
            image: data.user?.avatar_url,
            accessToken: data.access_token,
            refreshToken: data.refresh_token,
          };
        } catch (error) {
          if (error instanceof Error) {
            throw error;
          }
          throw new Error('Authentication failed');
        }
      },
    }),
  ],

  callbacks: {
    // JWT callback - store tokens in JWT
    async jwt({ token, account, user }) {
      // Initial sign in
      if (account && user) {
        // For OAuth providers, exchange tokens with backend
        if (account.provider === 'google' || account.provider === 'apple') {
          try {
            const response = await fetch(`${API_BASE_URL}/api/auth/oauth/callback`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                provider: account.provider,
                access_token: account.access_token,
                id_token: account.id_token,
                code: account.code,
              }),
            });

            if (response.ok) {
              const data = await response.json();
              token.accessToken = data.access_token;
              token.refreshToken = data.refresh_token;
              token.userId = data.user?.id;
              token.roles = data.user?.roles || ['user'];
            } else {
              // If backend validation fails, use provider token temporarily
              token.accessToken = account.access_token || '';
              token.refreshToken = account.refresh_token || '';
              token.userId = user.id;
              token.roles = ['user'];
            }
          } catch (error) {
            console.error('OAuth backend validation failed:', error);
            // Fallback to provider tokens
            token.accessToken = account.access_token || '';
            token.refreshToken = account.refresh_token || '';
            token.userId = user.id;
            token.roles = ['user'];
          }
        } else {
          // Credentials provider - tokens already set
          token.accessToken = (user as any).accessToken || '';
          token.refreshToken = (user as any).refreshToken || '';
          token.userId = user.id;
          token.roles = (user as any).roles || ['user'];
        }

        return token;
      }

      // Return previous token if still valid
      if (token.accessToken) {
        return token;
      }

      // Token expired - attempt refresh
      try {
        const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: token.refreshToken }),
        });

        if (response.ok) {
          const data = await response.json();
          token.accessToken = data.access_token;
          token.refreshToken = data.refresh_token;
          return token;
        }
      } catch (error) {
        console.error('Token refresh failed:', error);
      }

      // Refresh failed - sign out
      return { ...token, accessToken: '', refreshToken: '' };
    },

    // Session callback - expose tokens to client (minimal payload)
    async session({ session, token }) {
      if (token.accessToken) {
        session.accessToken = token.accessToken;
        session.refreshToken = token.refreshToken;
        if (session.user) {
          session.user.id = token.userId || '';
          session.user.roles = token.roles as string[] || ['user'];
        }
      }
      return session;
    },

    // SignIn callback - validate user
    async signIn({ user, account, profile }) {
      // For OAuth providers, allow sign in
      if (account?.provider === 'google' || account?.provider === 'apple') {
        return true;
      }

      // For credentials, user is already validated
      return !!user;
    },
  },

  pages: {
    signIn: '/login',
    signOut: '/logout',
    error: '/auth/error',
    newUser: '/register',
  },

  session: {
    strategy: 'jwt',
    maxAge: 24 * 60 * 60, // 24 hours
  },

  cookies: {
    sessionToken: {
      name: `confit.session-token`,
      options: {
        httpOnly: true,
        sameSite: 'lax',
        path: '/',
        secure: process.env.NODE_ENV === 'production',
      },
    },
    csrfToken: {
      name: `confit.csrf-token`,
      options: {
        httpOnly: true,
        sameSite: 'lax',
        path: '/',
        secure: process.env.NODE_ENV === 'production',
      },
    },
  },

  debug: process.env.NEXTAUTH_DEBUG === 'true',
};
