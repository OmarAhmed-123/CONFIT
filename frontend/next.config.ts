import path from 'path';
import type { NextConfig } from 'next';

const enableWebpackConfig = process.env.CONFIT_ENABLE_WEBPACK_CONFIG === 'true';

const nextConfig: NextConfig = {
  reactStrictMode: true,
  allowedDevOrigins: ['169.254.157.9'],
  outputFileTracingRoot: path.join(__dirname, '..'),
  poweredByHeader: false,
  compress: true,
  productionBrowserSourceMaps: false,
  experimental: {
    // Increase memory limit for large pages
    largePageDataBytes: 128 * 1024 * 1024, // 128MB
    optimizePackageImports: [
      'lucide-react',
      'framer-motion',
      'recharts',
      '@radix-ui/react-icons',
    ],
    // Webpack build worker for faster builds
    webpackBuildWorker: true,
  },
  eslint: {
    // Large Vite→Next migration: re-enable strict lint in CI after cleanup.
    ignoreDuringBuilds: true,
  },
  typescript: {
    // Incremental cleanup: `npx tsc --noEmit` in frontend/ until this can be removed.
    ignoreBuildErrors: true,
  },
  ...(enableWebpackConfig
    ? {
        // Optional production bundle optimization. Disabled by default so Turbopack dev stays clean.
        webpack: (config: any, { isServer }: { isServer: boolean }) => {
          if (!isServer) {
            config.optimization = {
              ...config.optimization,
              splitChunks: {
                chunks: 'all',
                cacheGroups: {
                  vendor: {
                    test: /[\\/]node_modules[\\/](react|react-dom|next)[\\/]/,
                    name: 'vendor-core',
                    priority: 40,
                    enforce: true,
                  },
                  ui: {
                    test: /[\\/]node_modules[\\/](@radix-ui|framer-motion|lucide-react)[\\/]/,
                    name: 'vendor-ui',
                    priority: 30,
                    enforce: true,
                  },
                  ml: {
                    test: /[\\/]node_modules[\\/](@tensorflow|@mediapipe|tfjs)[\\/]/,
                    name: 'vendor-ml',
                    priority: 20,
                    enforce: true,
                  },
                  dataviz: {
                    test: /[\\/]node_modules[\\/](recharts|jspdf|lottie-react)[\\/]/,
                    name: 'vendor-dataviz',
                    priority: 10,
                    enforce: true,
                  },
                },
              },
            };
          }
          return config;
        },
      }
    : {}),
  /**
   * Proxy `/api/*` to FastAPI backend.
   * NextAuth reserved paths are handled by App Router route at /api/auth/[...nextauth].
   * Backend auth endpoints (login, register, me, refresh, logout) are proxied.
   */
  async rewrites() {
    const backend = (process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:8000').replace(
      /\/$/,
      ''
    );
    // NextAuth reserved paths that should NOT be proxied to backend
    const nextAuthPaths = [
      'session', 'signin', 'signout', 'callback', 'csrf', 'providers',
      'error', 'verify-request', '_log', 'new-user'
    ];
    const nextAuthPattern = nextAuthPaths.join('|');
    
    return {
      // Proxy backend auth endpoints (exclude NextAuth reserved paths)
      beforeFiles: [
        {
          source: `/api/auth/:path((?!${nextAuthPattern}).*)*`,
          destination: `${backend}/api/auth/:path*`,
        },
      ],
      // Fallback for all other API routes
      fallback: [{ source: '/api/:path*', destination: `${backend}/api/:path*` }],
    };
  },
  images: {
    remotePatterns: [
      { hostname: 'localhost' },
      { hostname: '127.0.0.1' },
      { hostname: '*.stripe.com' },
      { hostname: 'images.unsplash.com' },
      { hostname: 'via.placeholder.com' },
    ],
  },
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          { key: 'X-XSS-Protection', value: '1; mode=block' },
        ],
      },
    ];
  },
  env: {
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL,
    NEXT_PUBLIC_AUTH_ORIGIN: process.env.NEXT_PUBLIC_AUTH_ORIGIN,
    NEXT_PUBLIC_APP_URL: process.env.NEXT_PUBLIC_APP_URL,
    NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY: process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY,
    NEXT_PUBLIC_GOOGLE_CLIENT_ID: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID,
    NEXT_PUBLIC_SUPABASE_URL: process.env.NEXT_PUBLIC_SUPABASE_URL,
    NEXT_PUBLIC_SUPABASE_ANON_KEY: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
  },
};

export default nextConfig;
