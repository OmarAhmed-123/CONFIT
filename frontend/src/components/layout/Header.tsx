import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ShoppingBag, Search, Menu, X, User, Heart, Crown, LogIn } from 'lucide-react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useCart } from '@/context/CartContext';
import { useWishlist } from '@/context/WishlistContext';
import { useAuth } from '@/context/AuthContext';
import { useGender } from '@/context/GenderContext';
import { cn } from "@/lib/utils";

export const Header = () => {
  const pathname = usePathname();
  const [isScrolled, setIsScrolled] = useState(false);
  const { getCartCount } = useCart();
  const { getWishlistCount } = useWishlist();
  const { user, signOut } = useAuth();
  const { selectedGender, setGender } = useGender();
  const [isSearchOpen, setIsSearchOpen] = useState(false);

  // Handle scroll effect
  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const cartCount = getCartCount();
  const wishlistCount = getWishlistCount();
  /** Lovable-style try-on studio: logo + icon rail only, solid dark bar */
  const isTryOnStudio = pathname === '/try-on';

  const navLinks = [
    { name: 'Discover', path: '/discover' },
    { name: 'Brands', path: '/brands' },
    { name: 'Influencers', path: '/influencers' },
    { name: 'Stylist', path: '/stylist' },
    { name: 'Try-On', path: '/try-on' },
    { name: 'Wardrobe', path: '/wardrobe' },
    { name: 'Digital Twin', path: '/digital-twin' },
    { name: 'Social', path: '/social' },
    { name: 'Growth', path: '/growth' },
    { name: 'Resale', path: '/resale' },
    { name: 'Dashboard', path: '/brand-dashboard' },
    { name: 'Smart Mirror', path: '/smart-mirror' },
    { name: 'Challenges', path: '/challenges' },
  ];

  return (
    <header
      className={cn(
        "fixed top-0 left-0 right-0 z-50 transition-all duration-300 border-b border-transparent",
        isTryOnStudio &&
          "border-b border-white/[0.06] bg-[hsl(220_22%_6%)] py-3 shadow-none backdrop-blur-none",
        !isTryOnStudio &&
          (isScrolled
            ? "bg-white/80 dark:bg-black/80 backdrop-blur-md shadow-sm border-border/40 py-2"
            : "bg-transparent py-4")
      )}
    >
      <div className="container px-4 md:px-6 mx-auto flex items-center justify-between">

        {/* Logo & Mobile Menu */}
        <div className="flex items-center gap-4">
          <Sheet>
            <SheetTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className={cn(
                  "text-foreground hover:bg-white/5",
                  isTryOnStudio ? "flex text-white/90" : "lg:hidden"
                )}
              >
                <Menu className="h-6 w-6" />
                <span className="sr-only">Toggle menu</span>
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-[300px] sm:w-[400px]">
              <div className="flex flex-col gap-6 py-6">
                <Link href="/" className="text-2xl font-playfair font-bold">CONFIT</Link>
                <nav className="flex flex-col gap-4">
                  {navLinks.map((link) => (
                    <Link
                      key={link.path}
                      href={link.path}
                      className={cn(
                        "text-lg font-medium transition-colors hover:text-primary",
                        pathname === link.path ? "text-primary" : "text-muted-foreground"
                      )}
                    >
                      {link.name}
                    </Link>
                  ))}
                </nav>
              </div>
            </SheetContent>
          </Sheet>

          <Link
            href="/"
            className={cn(
              "group flex items-center gap-2.5",
              isTryOnStudio && "gap-2"
            )}
          >
            {isTryOnStudio ? (
              <>
                <Crown
                  className="h-[1.15rem] w-[1.15rem] shrink-0 text-[hsl(45_74%_52%)]"
                  strokeWidth={1.75}
                  aria-hidden
                />
                <span className="font-playfair text-xl font-bold tracking-[0.12em] text-white sm:text-[1.35rem]">
                  CONFIT
                </span>
              </>
            ) : (
              <>
                <div className="rounded-lg bg-primary p-1.5 text-primary-foreground transition-transform group-hover:scale-110">
                  <span className="font-playfair text-lg font-bold tracking-wider">C</span>
                </div>
                <span className="hidden font-playfair text-xl font-bold tracking-tight sm:inline-block">
                  CONFIT
                </span>
              </>
            )}
          </Link>
        </div>

        {/* Desktop Navigation */}
        <nav
          className={cn(
            "hidden items-center gap-8 lg:flex",
            isTryOnStudio && "lg:hidden"
          )}
        >
          {navLinks.map((link) => (
            <Link
              key={link.path}
              href={link.path}
              className={cn(
                "text-sm font-medium transition-colors hover:text-primary relative group",
                pathname === link.path ? "text-primary" : "text-muted-foreground"
              )}
            >
              {link.name}
              <span className={cn(
                "absolute -bottom-1 left-0 w-full h-0.5 bg-primary scale-x-0 group-hover:scale-x-100 transition-transform origin-left",
                pathname === link.path && "scale-x-100"
              )} />
            </Link>
          ))}
        </nav>

        {/* Actions */}
        <div
          className={cn(
            "flex items-center gap-1 sm:gap-2",
            isTryOnStudio && "gap-1.5 sm:gap-2"
          )}
        >

          {/* Gender Switcher (Desktop) */}
          <div
            className={cn(
              "mr-2 hidden items-center rounded-full border border-border/50 bg-muted/50 p-1 md:flex",
              isTryOnStudio && "hidden"
            )}
          >
            <button
              onClick={() => setGender('women')}
              className={cn(
                "px-3 py-1 rounded-full text-xs font-medium transition-all",
                selectedGender === 'women' ? "bg-white shadow-sm text-foreground" : "text-muted-foreground hover:text-foreground"
              )}
            >
              Women
            </button>
            <button
              onClick={() => setGender('men')}
              className={cn(
                "px-3 py-1 rounded-full text-xs font-medium transition-all",
                selectedGender === 'men' ? "bg-white shadow-sm text-foreground" : "text-muted-foreground hover:text-foreground"
              )}
            >
              Men
            </button>
          </div>

          <Button
            variant="ghost"
            size="icon"
            className={cn(
              isTryOnStudio ? "flex" : "hidden sm:flex",
              isTryOnStudio && "text-white/85 hover:bg-white/10 hover:text-white"
            )}
            onClick={() => setIsSearchOpen(!isSearchOpen)}
          >
            <Search className="h-5 w-5" />
          </Button>

          <Link href="/wishlist">
            <Button
              variant="ghost"
              size="icon"
              className={cn("relative", isTryOnStudio && "text-white/85 hover:bg-white/10 hover:text-white")}
            >
              <Heart className="h-5 w-5" />
              {wishlistCount > 0 && (
                <span className="absolute top-1 right-1 h-2 w-2 rounded-full bg-red-500 animate-pulse" />
              )}
            </Button>
          </Link>

          <Link href="/cart">
            <Button
              variant="ghost"
              size="icon"
              className={cn("relative", isTryOnStudio && "text-white/85 hover:bg-white/10 hover:text-white")}
            >
              <ShoppingBag className="h-5 w-5" />
              {cartCount > 0 && (
                <span className="absolute -top-1 -right-1 h-5 w-5 rounded-full bg-primary text-[10px] font-bold text-primary-foreground flex items-center justify-center border-2 border-background">
                  {cartCount}
                </span>
              )}
            </Button>
          </Link>

          {user ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className={cn(
                    "rounded-full",
                    isTryOnStudio && "text-white/85 hover:bg-white/10 hover:text-white"
                  )}
                >
                  {user.avatar_url || user.avatar ? (
                    <img src={user.avatar_url || user.avatar} alt={user.name} className="h-8 w-8 rounded-full object-cover" />
                  ) : (
                    <User className="h-5 w-5" />
                  )}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56 glass-panel">
                <DropdownMenuLabel>
                  <div className="flex flex-col space-y-1">
                    <p className="text-sm font-medium leading-none">{user.name}</p>
                    <p className="text-xs leading-none text-muted-foreground">{user.email}</p>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <Link href="/profile">Profile & Orders</Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link href="/wardrobe">My Wardrobe</Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link href="/digital-twin">Digital Twin</Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link href="/social">Social Styling</Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link href="/resale">Resale Marketplace</Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link href="/smart-mirror">Smart Mirror</Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link href="/challenges">Style Challenges</Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link href="/influencers">Creator Marketplace</Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link href="/brand-dashboard">Brand Dashboard (Demo)</Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={signOut} className="text-red-500 focus:text-red-500">
                  Log out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : isTryOnStudio ? (
            <Button
              variant="ghost"
              size="icon"
              className="ml-0.5 text-white/85 hover:bg-white/10 hover:text-white"
              asChild
            >
              <Link href="/login" aria-label="Sign in">
                <LogIn className="h-5 w-5" />
              </Link>
            </Button>
          ) : (
            <Button variant="default" size="sm" asChild className="ml-2 rounded-full px-6">
              <Link href="/login">Sign In</Link>
            </Button>
          )}
        </div>
      </div>

      {/* Expandable Search Bar */}
      {isSearchOpen && (
        <div className="absolute top-full left-0 right-0 bg-background/95 backdrop-blur-md border-b border-border p-4 animate-fade-in-up">
          <div className="container mx-auto max-w-2xl relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search products, brands, or styles..."
              className="pl-10 h-10 rounded-full border-muted-foreground/20"
              autoFocus
            />
            <Button
              variant="ghost"
              size="icon"
              className="absolute right-2 top-1/2 -translate-y-1/2 h-6 w-6"
              onClick={() => setIsSearchOpen(false)}
            >
              <X className="h-3 w-3" />
            </Button>
          </div>
        </div>
      )}
    </header>
  );
};
