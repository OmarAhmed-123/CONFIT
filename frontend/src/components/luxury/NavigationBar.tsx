/**
 * NavigationBar - Premium dark luxury navigation
 * Features: Glass effect, gold accents, smooth animations
 */

import { forwardRef, HTMLAttributes } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Crown, Home, Search, ShoppingBag, User, Sparkles } from 'lucide-react';
import { transitionFast, transitionLuxury } from '@/motion';

export interface NavigationBarProps extends HTMLAttributes<HTMLElement> {
  variant?: 'default' | 'glass' | 'minimal';
}

const navItems = [
  { path: '/', label: 'Home', icon: Home },
  { path: '/discover', label: 'Discover', icon: Search },
  { path: '/outfits', label: 'Outfits', icon: Sparkles },
  { path: '/cart', label: 'Cart', icon: ShoppingBag },
  { path: '/profile', label: 'Profile', icon: User },
];

export const NavigationBar = forwardRef<HTMLElement, NavigationBarProps>(
  ({ className, variant = 'glass', ...props }, ref) => {
    const pathname = usePathname();

    const variantStyles = {
      default: 'bg-[#0B0F1A] border-white/10',
      glass: 'bg-black/40 backdrop-blur-xl border-white/[0.06]',
      minimal: 'bg-transparent border-transparent',
    };

    return (
      <nav
        ref={ref}
        className={cn(
          'fixed bottom-0 left-0 right-0 z-40',
          'border-t',
          variantStyles[variant],
          className
        )}
        {...props}
      >
        <div className="max-w-lg mx-auto px-4">
          <div className="flex items-center justify-around py-2">
            {navItems.map((item) => {
              const isActive = pathname === item.path;
              const Icon = item.icon;

              return (
                <Link
                  key={item.path}
                  href={item.path}
                  className={cn(
                    'relative flex flex-col items-center gap-1 px-4 py-2',
                    'transition-colors duration-200',
                    isActive ? 'text-[#D4AF37]' : 'text-[#A0A3A8] hover:text-[#F5F5F5]'
                  )}
                >
                  <motion.div
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.95 }}
                    transition={transitionFast}
                  >
                    <Icon className="w-5 h-5" />
                  </motion.div>
                  <span className="text-[10px] font-medium tracking-wide">
                    {item.label}
                  </span>
                  
                  {/* Active indicator */}
                  <AnimatePresence>
                    {isActive && (
                      <motion.div
                        initial={{ scale: 0, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        exit={{ scale: 0, opacity: 0 }}
                        transition={transitionFast}
                        className="absolute -top-1 left-1/2 -translate-x-1/2 w-1 h-1 rounded-full bg-[#D4AF37]"
                      />
                    )}
                  </AnimatePresence>
                </Link>
              );
            })}
          </div>
        </div>
      </nav>
    );
  }
);

NavigationBar.displayName = 'NavigationBar';

// ═══════════════════════════════════════════════════════════════
// TOP NAVIGATION BAR
// ═══════════════════════════════════════════════════════════════

export interface TopNavigationBarProps extends HTMLAttributes<HTMLElement> {
  showLogo?: boolean;
  transparent?: boolean;
  actions?: React.ReactNode;
}

export const TopNavigationBar = forwardRef<HTMLElement, TopNavigationBarProps>(
  ({ className, showLogo = true, transparent = false, actions, ...props }, ref) => {
    return (
      <header
        ref={ref}
        className={cn(
          'fixed top-0 left-0 right-0 z-40',
          'border-b',
          transparent 
            ? 'bg-transparent border-transparent' 
            : 'bg-black/40 backdrop-blur-xl border-white/[0.06]',
          className
        )}
        {...props}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            {showLogo && (
              <Link href="/" className="flex items-center gap-2 group">
                <motion.div
                  whileHover={{ scale: 1.05 }}
                  transition={transitionFast}
                  className="flex items-center gap-2"
                >
                  <div className="relative w-8 h-8">
                    <Crown className="w-6 h-6 text-[#D4AF37]" />
                    <div className="absolute inset-0 bg-[#D4AF37]/20 blur-lg rounded-full" />
                  </div>
                  <span className="font-display text-xl font-bold tracking-tight text-[#F5F5F5]">
                    CONFIT
                  </span>
                </motion.div>
              </Link>
            )}

            {/* Actions */}
            <div className="flex items-center gap-4">
              {actions}
            </div>
          </div>
        </div>
      </header>
    );
  }
);

TopNavigationBar.displayName = 'TopNavigationBar';

// ═══════════════════════════════════════════════════════════════
// NAVIGATION LINK
// ═══════════════════════════════════════════════════════════════

export interface NavLinkProps extends HTMLAttributes<HTMLAnchorElement> {
  to: string;
  active?: boolean;
}

export const NavLink = forwardRef<HTMLAnchorElement, NavLinkProps>(
  ({ className, to, active, children, ...props }, ref) => {
    return (
      <Link
        ref={ref}
        href={to}
        className={cn(
          'relative px-4 py-2 text-sm font-medium',
          'transition-colors duration-200',
          active 
            ? 'text-[#D4AF37]' 
            : 'text-[#A0A3A8] hover:text-[#F5F5F5]',
          className
        )}
        {...props}
      >
        <motion.span
          whileHover={{ y: -1 }}
          transition={transitionFast}
        >
          {children}
        </motion.span>
        
        {/* Active underline */}
        {active && (
          <motion.div
            layoutId="nav-underline"
            className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#D4AF37]"
            initial={false}
            transition={transitionLuxury}
          />
        )}
      </Link>
    );
  }
);

NavLink.displayName = 'NavLink';

export default NavigationBar;
