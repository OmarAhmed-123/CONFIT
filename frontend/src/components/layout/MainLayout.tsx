import { ReactNode } from 'react';
import { PrimaryNav } from '@/components/navigation';
import { Footer } from './Footer';
import { cn } from '@/lib/utils';

interface MainLayoutProps {
  children: ReactNode;
  className?: string;
  hideFooter?: boolean;
  fullWidth?: boolean;
}

export function MainLayout({ 
  children, 
  className, 
  hideFooter = false,
  fullWidth = false 
}: MainLayoutProps) {
  return (
    <div className="min-h-screen flex flex-col">
      <PrimaryNav />
      <main className={cn(
        "flex-1",
        !fullWidth && "pt-16 md:pt-20",
        className
      )}>
        {children}
      </main>
      {!hideFooter && <Footer />}
    </div>
  );
}
