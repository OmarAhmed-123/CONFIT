import { motion } from 'framer-motion';
import { MainLayout } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Leaf, Store, Tag } from 'lucide-react';
import { useResaleViewModel } from '@/viewmodels/useResaleViewModel';
import { createTransition } from '@/motion';

export default function ResalePage() {
  const {
    tab,
    listings,
    impact,
    search,
    isBuying,
    isLoading,
    setTab,
    setSearch,
    buy
  } = useResaleViewModel();

  return (
    <MainLayout>
      <div className="container py-8">
        <div className="max-w-6xl mx-auto space-y-8">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="inline-flex items-center gap-2 bg-accent/10 text-accent px-4 py-2 rounded-full mb-3">
                <Leaf className="h-4 w-4" />
                <span className="text-sm font-medium">Circular Fashion</span>
              </div>
              <h1 className="heading-section">Wardrobe Monetization</h1>
              <p className="text-muted-foreground max-w-2xl">
                List items from your wardrobe in one click, shop second‑hand, and track your eco impact.
              </p>
            </div>

            <div className="inline-flex rounded-full border border-border bg-card p-1">
              <button
                type="button"
                onClick={() => setTab('market')}
                className={`px-5 py-2 text-sm rounded-full transition-colors ${tab === 'market' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground'}`}
              >
                Marketplace
              </button>
              <button
                type="button"
                onClick={() => setTab('seller')}
                className={`px-5 py-2 text-sm rounded-full transition-colors ${tab === 'seller' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground'}`}
              >
                Seller Dashboard
              </button>
            </div>
          </div>

          {tab === 'seller' && (
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="grid md:grid-cols-3 gap-4">
              <div className="bg-card border border-border rounded-xl p-5">
                <p className="text-sm text-muted-foreground mb-1">CO₂ saved</p>
                <p className="text-2xl font-bold">{impact?.co2_saved_kg ?? 0} kg</p>
              </div>
              <div className="bg-card border border-border rounded-xl p-5">
                <p className="text-sm text-muted-foreground mb-1">Water saved</p>
                <p className="text-2xl font-bold">{impact?.water_saved_l ?? 0} L</p>
              </div>
              <div className="bg-card border border-border rounded-xl p-5">
                <p className="text-sm text-muted-foreground mb-1">Tip</p>
                <p className="text-sm">{impact?.message ?? 'List items from Wardrobe → Resell to increase impact.'}</p>
              </div>
            </motion.div>
          )}

          <div className="flex flex-col md:flex-row gap-4 items-center">
            <div className="relative flex-1 w-full">
              <Store className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search listings..."
                className="pl-12 h-12"
              />
            </div>
            <Button variant="outline" asChild>
              <a href="/wardrobe">List from Wardrobe</a>
            </Button>
          </div>

          {isLoading ? (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {[1, 2, 3].map(i => (
                <div key={i} className="bg-card border border-border rounded-xl aspect-[3/4] animate-pulse" />
              ))}
            </div>
          ) : listings.length === 0 ? (
            <div className="bg-card border border-border rounded-xl p-10 text-center">
              <p className="text-muted-foreground">No listings found.</p>
            </div>
          ) : (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {listings.map((l, idx) => (
                <motion.article
                  key={l.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={createTransition({ delay: Math.min(idx * 0.03, 0.2) })}
                  className="bg-card border border-border rounded-xl overflow-hidden"
                >
                  <div className="aspect-[3/4] bg-muted overflow-hidden">
                    <img
                      src={l.item_image_url || 'https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=400&h=500&fit=crop'}
                      alt={l.item_name || 'Listing'}
                      className="w-full h-full object-cover transition-transform duration-500 hover:scale-105"
                      loading="lazy"
                    />
                  </div>
                  <div className="p-4 space-y-3">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold">{l.item_name || 'Wardrobe item'}</p>
                        <p className="text-xs text-muted-foreground">{l.item_brand || 'Seller listing'}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-bold">{l.currency} {l.price.toFixed(0)}</p>
                        <p className="text-xs text-muted-foreground">{l.status}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <Tag className="h-3 w-3" />
                      <span>{l.item_category || 'fashion'}</span>
                      {l.item_color && <span>• {l.item_color}</span>}
                    </div>
                    <div className="flex items-center justify-between gap-2">
                      {tab === 'market' ? (
                        <Button
                          variant="hero"
                          size="sm"
                          className="flex-1"
                          onClick={() => buy(l.id)}
                          disabled={isBuying === l.id}
                        >
                          {isBuying === l.id ? 'Processing...' : 'Buy (Demo)'}
                        </Button>
                      ) : (
                        <Button variant="secondary" size="sm" className="flex-1" disabled>
                          Your Listing
                        </Button>
                      )}

                      <Button variant="outline" size="sm" onClick={() => navigator.clipboard?.writeText(l.id)}>
                        Copy ID
                      </Button>
                    </div>
                  </div>
                </motion.article>
              ))}
            </div>
          )}
        </div>
      </div>
    </MainLayout>
  );
}
