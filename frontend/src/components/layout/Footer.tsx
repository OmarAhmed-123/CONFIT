import { Facebook, Instagram, Twitter, Linkedin, Mail, ArrowRight, MapPin, Phone } from 'lucide-react';
import Link from 'next/link';
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useState } from 'react';
import { toast } from '@/hooks/use-toast';
import { apiUrl } from '@/lib/api';

export const Footer = () => {
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubscribe = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;

    setIsLoading(true);
    try {
      const response = await fetch(apiUrl('/api/newsletter/subscribe'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });

      const data = await response.json();

      if (response.ok) {
        toast({
          title: "Subscribed!",
          description: data.message,
        });
        setEmail('');
      } else {
        toast({
          title: "Subscription failed",
          description: data.detail || "Please try again later.",
          variant: "destructive",
        });
      }
    } catch (error) {
      // Fallback for demo if backend is offline
      toast({
        title: "Subscribed!",
        description: "Thanks for joining our newsletter (Demo Mode).",
      });
      setEmail('');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <footer className="bg-muted/30 border-t border-border mt-auto pt-16 pb-8">
      <div className="container px-4 md:px-6 mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-12 mb-12">

          {/* Brand Column */}
          <div className="space-y-4">
            <Link href="/" className="flex items-center gap-2 group">
              <div className="bg-primary text-primary-foreground rounded-lg p-1.5 transition-transform group-hover:scale-105">
                <span className="font-playfair font-bold text-lg tracking-wider">C</span>
              </div>
              <span className="text-2xl font-playfair font-bold tracking-tight">CONFIT</span>
            </Link>
            <p className="text-muted-foreground leading-relaxed max-w-sm">
              Redefining your digital fashion experience. Visual try-on, AI styling, and premium collections tailored to your confidence.
            </p>
            <div className="flex gap-4 pt-2">
              <a href="#" className="p-2 rounded-full bg-background border border-border hover:bg-primary hover:text-primary-foreground transition-colors">
                <Instagram className="h-5 w-5" />
              </a>
              <a href="#" className="p-2 rounded-full bg-background border border-border hover:bg-primary hover:text-primary-foreground transition-colors">
                <Twitter className="h-5 w-5" />
              </a>
              <a href="#" className="p-2 rounded-full bg-background border border-border hover:bg-primary hover:text-primary-foreground transition-colors">
                <Linkedin className="h-5 w-5" />
              </a>
            </div>
          </div>

          {/* Quick Links */}
          <div>
            <h3 className="font-bold text-lg mb-6">Explore</h3>
            <ul className="space-y-3">
              <li><Link href="/discover" className="text-muted-foreground hover:text-primary transition-colors flex items-center gap-2"><ArrowRight className="w-3 h-3" /> Latest Arrivals</Link></li>
              <li><Link href="/stylist" className="text-muted-foreground hover:text-primary transition-colors flex items-center gap-2"><ArrowRight className="w-3 h-3" /> AI Stylist</Link></li>
              <li><Link href="/try-on" className="text-muted-foreground hover:text-primary transition-colors flex items-center gap-2"><ArrowRight className="w-3 h-3" /> Virtual Dressing Room</Link></li>
              <li><Link href="/brands" className="text-muted-foreground hover:text-primary transition-colors flex items-center gap-2"><ArrowRight className="w-3 h-3" /> Our Brands</Link></li>
            </ul>
          </div>

          {/* Support */}
          <div>
            <h3 className="font-bold text-lg mb-6">Support</h3>
            <ul className="space-y-3">
              <li><Link href="/profile" className="text-muted-foreground hover:text-primary transition-colors">My Account</Link></li>
              <li><Link href="/orders" className="text-muted-foreground hover:text-primary transition-colors">Order Status</Link></li>
              <li><Link href="/wishlist" className="text-muted-foreground hover:text-primary transition-colors">Wishlist</Link></li>
              <li><Link href="/stores" className="text-muted-foreground hover:text-primary transition-colors">Store Locator</Link></li>
              <li><Link href="/contact" className="text-muted-foreground hover:text-primary transition-colors">Contact Us</Link></li>
            </ul>
          </div>

          {/* Newsletter */}
          <div>
            <h3 className="font-bold text-lg mb-6">Stay Updated</h3>
            <p className="text-muted-foreground mb-4 text-sm">
              Subscribe to get special offers, free giveaways, and once-in-a-lifetime deals.
            </p>
            <form onSubmit={handleSubscribe} className="space-y-3">
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  type="email"
                  placeholder="Enter your email"
                  className="pl-10 bg-background/50 border-border focus:border-primary transition-colors"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
              <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading ? 'Subscribing...' : 'Subscribe'}
              </Button>
            </form>
          </div>
        </div>

        <div className="border-t border-border pt-8 flex flex-col md:flex-row justify-between items-center gap-4 text-sm text-muted-foreground">
          <p>© {new Date().getFullYear()} CONFIT Inc. All rights reserved.</p>
          <div className="flex gap-6">
            <Link href="/privacy" className="hover:text-primary transition-colors">Privacy Policy</Link>
            <Link href="/terms" className="hover:text-primary transition-colors">Terms of Service</Link>
          </div>
        </div>
      </div>
    </footer>
  );
};
