import type { Metadata } from 'next';
import { Inter, Playfair_Display } from 'next/font/google';
import { Providers } from '@/components/providers';
import '@/index.css';

const inter = Inter({
  variable: '--font-sans',
  subsets: ['latin'],
});

const playfair = Playfair_Display({
  variable: '--font-display',
  subsets: ['latin'],
});

export const metadata: Metadata = {
  title: {
    default: 'CONFIT — Your Personal Fashion Platform',
    template: '%s | CONFIT',
  },
  description: 'Discover, style, and shop fashion with AI-powered recommendations and virtual try-on.',
  keywords: ['fashion', 'AI stylist', 'virtual try-on', 'wardrobe', 'outfits'],
  authors: [{ name: 'CONFIT' }],
  creator: 'CONFIT',
  metadataBase: new URL(process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'),
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: '/',
    siteName: 'CONFIT',
    title: 'CONFIT — Your Personal Fashion Platform',
    description: 'Discover, style, and shop fashion with AI-powered recommendations and virtual try-on.',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'CONFIT',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'CONFIT — Your Personal Fashion Platform',
    description: 'Discover, style, and shop fashion with AI-powered recommendations and virtual try-on.',
    images: ['/og-image.png'],
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} ${playfair.variable}`}>
      <body className="min-h-screen flex flex-col antialiased">
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  );
}
