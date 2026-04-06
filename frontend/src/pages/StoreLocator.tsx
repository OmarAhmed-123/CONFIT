import { useState, useMemo, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useSearchParams } from 'next/navigation';
import {
    MapPin, Search, Phone, Clock, Navigation2, Store, Truck, RotateCcw, Camera, Filter, ChevronDown, CheckCircle2, X, MessageCircle, Radio
} from 'lucide-react';
import { MainLayout } from '@/components/layout/MainLayout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface StoreService {
    id: string;
    name: string;
    icon: React.ElementType;
}

interface StoreLocation {
    id: string;
    name: string;
    address: string;
    city: string;
    state: string;
    zip_code: string;
    postal_code?: string; // Backend uses postal_code
    phone: string;
    hours: Record<string, string> | { day: string; open: string; close: string }[];
    services: string[];
    distance: number;
    coordinates?: { lat: number; lng: number };
    location?: { lat: number; lng: number };
    featured?: boolean;
    is_live?: boolean;
    live_viewers?: number;
    current_showcase?: string;
    whatsapp_number?: string;
    response_time_minutes?: number;
}

const STORE_SERVICES: StoreService[] = [
    { id: 'bopis', name: 'Buy Online, Pick Up', icon: Store },
    { id: 'tryon', name: 'Virtual Try-On Booth', icon: Camera },
    { id: 'returns', name: 'Easy Returns', icon: RotateCcw },
    { id: 'shipping', name: 'Ship from Store', icon: Truck },
];

// Store data fetched from API
// const MOCK_STORES removed in favor of state

function getStoreHours(
    hours: StoreLocation['hours']
): Array<{ day: string; open: string; close: string }> {
    if (Array.isArray(hours)) {
        return hours;
    }

    return Object.entries(hours || {}).map(([day, value]) => {
        const [open = 'Closed', close = 'Closed'] = String(value).split('-').map((item) => item.trim());
        return { day, open, close };
    });
}

function getWhatsAppLink(store: StoreLocation): string | null {
    const rawNumber = (store.whatsapp_number || store.phone || '').replace(/\D/g, '');
    if (!rawNumber) return null;

    const message = encodeURIComponent(
        `Hi ${store.name}, I am browsing CONFIT and would like help with sizing, availability, or booking a store visit.`
    );
    return `https://wa.me/${rawNumber}?text=${message}`;
}


function StoreCard({ store, isSelected, onSelect }: { store: StoreLocation; isSelected: boolean; onSelect: () => void }) {
    const isOpen = true; // Mock: always open for demo

    const handleGetDirections = () => {
        const url = `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(
            `${store.address}, ${store.city}, ${store.state} ${store.zip_code}`
        )}`;
        window.open(url, '_blank');
    };

    const handleWhatsApp = () => {
        const link = getWhatsAppLink(store);
        if (link) {
            window.open(link, '_blank', 'noopener,noreferrer');
        }
    };

    const handleWatchLive = () => {
        window.location.href = `/try-on-live?store=${encodeURIComponent(store.name)}`;
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className={cn(
                "relative bg-card border rounded-xl p-5 cursor-pointer transition-all",
                isSelected ? "border-accent ring-2 ring-accent/20" : "border-border hover:border-muted-foreground"
            )}
            onClick={onSelect}
        >
            {store.featured && (
                <Badge className="absolute -top-2 left-4 bg-accent text-accent-foreground">Flagship</Badge>
            )}

            <div className="flex justify-between items-start mb-3">
                <div>
                    <h3 className="font-semibold text-lg">{store.name}</h3>
                    <p className="text-sm text-muted-foreground">{store.address}</p>
                    <p className="text-sm text-muted-foreground">{store.city}, {store.state} {store.zip_code}</p>
                </div>
                <div className="text-right space-y-1">
                    <span className="block text-sm font-medium text-accent">{store.distance.toFixed(1)} mi</span>
                    {store.is_live && (
                        <Badge className="bg-rose-500 text-white hover:bg-rose-500">
                            <Radio className="h-3 w-3 mr-1" />
                            Live now
                        </Badge>
                    )}
                </div>
            </div>

            <div className="flex items-center gap-4 text-sm mb-4">
                <div className="flex items-center gap-1.5">
                    <Phone className="h-4 w-4 text-muted-foreground" />
                    <span>{store.phone}</span>
                </div>
                <div className="flex items-center gap-1.5">
                    <Clock className="h-4 w-4 text-muted-foreground" />
                    <span className={isOpen ? 'text-green-600' : 'text-red-500'}>
                        {isOpen ? 'Open Now' : 'Closed'}
                    </span>
                </div>
            </div>

            {store.is_live && (
                <div className="mb-4 rounded-xl border border-rose-500/20 bg-rose-500/5 p-3">
                    <div className="flex items-center justify-between gap-3">
                        <div>
                            <p className="text-sm font-medium">Store live stream is active</p>
                            <p className="text-xs text-muted-foreground">
                                {store.current_showcase || 'Live styling and new arrivals'}
                            </p>
                        </div>
                        <div className="text-right">
                            <p className="text-sm font-semibold text-rose-600">{store.live_viewers || 0}</p>
                            <p className="text-[11px] text-muted-foreground">watching</p>
                        </div>
                    </div>
                </div>
            )}

            <div className="flex flex-wrap gap-2 mb-4">
                {store.services.map((serviceId) => {
                    const service = STORE_SERVICES.find(s => s.id === serviceId);
                    if (!service) return null;
                    return (
                        <span key={serviceId} className="flex items-center gap-1 text-xs px-2 py-1 bg-muted rounded-full">
                            <service.icon className="h-3 w-3" />
                            {service.name}
                        </span>
                    );
                })}
            </div>

            <div className="grid gap-2 sm:grid-cols-2">
                <Button variant="hero" size="sm" className="w-full" onClick={(e) => { e.stopPropagation(); handleGetDirections(); }}>
                    <Navigation2 className="h-4 w-4 mr-2" />
                    Get Directions
                </Button>
                <Button variant="outline" size="sm" className="w-full" onClick={(e) => { e.stopPropagation(); handleWhatsApp(); }}>
                    <MessageCircle className="h-4 w-4 mr-2" />
                    WhatsApp
                </Button>
                <Button variant="outline" size="sm" className="w-full" onClick={(e) => { e.stopPropagation(); window.location.href = `tel:${store.phone}`; }}>
                    <Phone className="h-4 w-4 mr-2" />
                    Call
                </Button>
                {store.is_live && (
                    <Button variant="outline" size="sm" className="w-full border-rose-500/30 text-rose-600 hover:bg-rose-500/10" onClick={(e) => { e.stopPropagation(); handleWatchLive(); }}>
                        <Radio className="h-4 w-4 mr-2" />
                        Watch Live
                    </Button>
                )}
            </div>
        </motion.div>
    );
}

export default function StoreLocator() {
    const searchParams = useSearchParams();
    const initialSearch = searchParams?.get('search')?.trim() || '';
    const [searchQuery, setSearchQuery] = useState(initialSearch);
    const [selectedStore, setSelectedStore] = useState<string | null>(null);
    const [activeFilters, setActiveFilters] = useState<string[]>([]);
    const [showFilters, setShowFilters] = useState(false);
    const [stores, setStores] = useState<StoreLocation[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        // Show empty state immediately, then try to fetch
        const fetchStores = async () => {
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 2000);
                
                const { apiUrl } = await import('@/lib/api');
                const res = await fetch(apiUrl('/api/stores'), { signal: controller.signal });
                clearTimeout(timeoutId);
                
                if (res.ok) {
                    const data = await res.json();
                    const mapped = (Array.isArray(data) ? data : []).map((s: any) => ({
                        ...s,
                        zip_code: s.postal_code || s.zip_code || '',
                        coordinates: s.location || s.coordinates || { lat: 0, lng: 0 },
                        distance: s.distance_km ? s.distance_km * 0.621371 : (s.distance || 0), // Convert km to miles
                        is_live: Boolean(s.is_live ?? (s.live_status === 'live')),
                        live_viewers: Number(s.live_viewers ?? 48),
                        current_showcase: s.current_showcase || 'New arrivals, live demos, and pickup support',
                        whatsapp_number: s.whatsapp_number || s.phone || '',
                        response_time_minutes: Number(s.response_time_minutes ?? 5),
                    }));
                    setStores(mapped);
                    setError(null);
                }
            } catch (e) {
                if (e instanceof Error && e.name !== 'AbortError') {
                    console.warn("Failed to fetch stores", e);
                    setError('Unable to load stores');
                }
                // Keep empty array if fetch fails
            }
        };
        fetchStores();
    }, []);

    const filteredStores = useMemo(() => {
        return stores.filter(store => {
            const matchesSearch = searchQuery === '' ||
                store.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                store.city.toLowerCase().includes(searchQuery.toLowerCase()) ||
                (store.zip_code || store.postal_code || '').includes(searchQuery);

            const matchesFilters = activeFilters.length === 0 ||
                activeFilters.every(filter => store.services.includes(filter));

            return matchesSearch && matchesFilters;
        }).sort((a, b) => a.distance - b.distance);
    }, [stores, searchQuery, activeFilters]);

    const toggleFilter = (filterId: string) => {
        setActiveFilters(prev =>
            prev.includes(filterId) ? prev.filter(f => f !== filterId) : [...prev, filterId]
        );
    };

    return (
        <MainLayout>
            <div className="container py-8">
                <div className="max-w-6xl mx-auto">
                    {/* Header */}
                    <div className="text-center mb-8">
                        <h1 className="text-3xl md:text-4xl font-display font-semibold mb-3">Find a Store</h1>
                        <p className="text-muted-foreground max-w-xl mx-auto">
                            Visit us in person for personalized styling, virtual try-on experiences, and easy pickup of your online orders.
                        </p>
                    </div>

                    {/* Search & Filters */}
                    <div className="bg-card border border-border rounded-xl p-4 mb-6">
                        <div className="flex flex-col md:flex-row gap-4">
                            <div className="relative flex-1">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                                <Input
                                    placeholder="Search by city, state, or ZIP code..."
                                    className="pl-10 h-12"
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                />
                            </div>
                            <Button
                                variant="outline"
                                className="h-12 gap-2"
                                onClick={() => setShowFilters(!showFilters)}
                            >
                                <Filter className="h-4 w-4" />
                                Filter
                                {activeFilters.length > 0 && (
                                    <Badge variant="secondary" className="ml-1">{activeFilters.length}</Badge>
                                )}
                                <ChevronDown className={cn("h-4 w-4 transition-transform", showFilters && "rotate-180")} />
                            </Button>
                        </div>

                        {/* Filter Options */}
                        {showFilters && (
                            <motion.div
                                initial={{ height: 0, opacity: 0 }}
                                animate={{ height: 'auto', opacity: 1 }}
                                exit={{ height: 0, opacity: 0 }}
                                className="mt-4 pt-4 border-t border-border"
                            >
                                <p className="text-sm font-medium mb-3">Filter by Services:</p>
                                <div className="flex flex-wrap gap-2">
                                    {STORE_SERVICES.map((service) => (
                                        <button
                                            key={service.id}
                                            onClick={() => toggleFilter(service.id)}
                                            className={cn(
                                                "flex items-center gap-2 px-3 py-2 rounded-lg border text-sm transition-all",
                                                activeFilters.includes(service.id)
                                                    ? "border-accent bg-accent/10 text-accent"
                                                    : "border-border hover:border-muted-foreground"
                                            )}
                                        >
                                            <service.icon className="h-4 w-4" />
                                            {service.name}
                                            {activeFilters.includes(service.id) && <CheckCircle2 className="h-4 w-4" />}
                                        </button>
                                    ))}
                                    {activeFilters.length > 0 && (
                                        <button
                                            onClick={() => setActiveFilters([])}
                                            className="flex items-center gap-1 px-3 py-2 text-sm text-muted-foreground hover:text-foreground"
                                        >
                                            <X className="h-4 w-4" />
                                            Clear All
                                        </button>
                                    )}
                                </div>
                            </motion.div>
                        )}
                    </div>

                    {/* Results Count */}
                    <div className="flex items-center justify-between mb-4">
                        {error ? (
                            <p className="text-sm text-destructive">{error}</p>
                        ) : (
                            <p className="text-sm text-muted-foreground">
                                {filteredStores.length} store{filteredStores.length !== 1 ? 's' : ''} found
                            </p>
                        )}
                        <p className="text-sm text-muted-foreground">
                            Sorted by distance
                        </p>
                    </div>

                    {/* Store Grid */}
                    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {filteredStores.map((store) => (
                            <StoreCard
                                key={store.id}
                                store={store}
                                isSelected={selectedStore === store.id}
                                onSelect={() => setSelectedStore(store.id === selectedStore ? null : store.id)}
                            />
                        ))}
                    </div>

                    {filteredStores.length === 0 && (
                        <div className="text-center py-16">
                            <MapPin className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                            <h3 className="text-lg font-semibold mb-2">No stores found</h3>
                            <p className="text-muted-foreground mb-4">
                                Try adjusting your search or filters to find a store near you.
                            </p>
                            <Button variant="outline" onClick={() => { setSearchQuery(''); setActiveFilters([]); }}>
                                Clear Search
                            </Button>
                        </div>
                    )}

                    {/* Store Details Panel */}
                    {selectedStore && (
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="fixed bottom-0 left-0 right-0 bg-card border-t border-border p-6 shadow-lg z-40 md:relative md:mt-6 md:rounded-xl md:border md:shadow-none"
                        >
                            {(() => {
                                const store = stores.find(s => s.id === selectedStore);
                                if (!store) return null;
                                return (
                                    <div className="max-w-4xl mx-auto">
                                        <div className="flex items-start justify-between mb-4">
                                            <div>
                                                <h3 className="text-xl font-semibold">{store.name}</h3>
                                                <p className="text-muted-foreground">{store.address}, {store.city}, {store.state} {store.zip_code}</p>
                                            </div>
                                            <Button variant="ghost" size="icon" onClick={() => setSelectedStore(null)}>
                                                <X className="h-5 w-5" />
                                            </Button>
                                        </div>
                                        <div className="grid md:grid-cols-2 gap-6">
                                            <div>
                                                <h4 className="font-medium mb-2 flex items-center gap-2">
                                                    <Clock className="h-4 w-4" /> Store Hours
                                                </h4>
                                                <div className="space-y-1 text-sm">
                                                    {getStoreHours(store.hours).map((h, i) => (
                                                        <div key={i} className="flex justify-between">
                                                            <span className="text-muted-foreground">{h.day}</span>
                                                            <span>{h.open} - {h.close}</span>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                            <div>
                                                <h4 className="font-medium mb-2 flex items-center gap-2">
                                                    <Store className="h-4 w-4" /> Available Services
                                                </h4>
                                                <div className="flex flex-wrap gap-2">
                                                    {store.services.map((serviceId) => {
                                                        const service = STORE_SERVICES.find(s => s.id === serviceId);
                                                        if (!service) return null;
                                                        return (
                                                            <Badge key={serviceId} variant="secondary" className="gap-1">
                                                                <service.icon className="h-3 w-3" />
                                                                {service.name}
                                                            </Badge>
                                                        );
                                                    })}
                                                </div>
                                                <div className="mt-4 space-y-2 text-sm">
                                                    {store.is_live && (
                                                        <div className="rounded-lg border border-rose-500/20 bg-rose-500/5 p-3">
                                                            <div className="flex items-center justify-between gap-3">
                                                                <div>
                                                                    <p className="font-medium">Live right now</p>
                                                                    <p className="text-muted-foreground">{store.current_showcase}</p>
                                                                </div>
                                                                <span className="text-rose-600 font-semibold">
                                                                    {store.live_viewers || 0} viewers
                                                                </span>
                                                            </div>
                                                        </div>
                                                    )}
                                                    <div className="flex flex-wrap gap-2">
                                                        <Button size="sm" variant="outline" onClick={() => {
                                                            const link = getWhatsAppLink(store);
                                                            if (link) window.open(link, '_blank', 'noopener,noreferrer');
                                                        }}>
                                                            <MessageCircle className="h-4 w-4 mr-2" />
                                                            WhatsApp
                                                        </Button>
                                                        <Button size="sm" variant="outline" onClick={() => { window.location.href = `tel:${store.phone}`; }}>
                                                            <Phone className="h-4 w-4 mr-2" />
                                                            Call Store
                                                        </Button>
                                                        {store.is_live && (
                                                            <Button size="sm" variant="outline" className="border-rose-500/30 text-rose-600 hover:bg-rose-500/10" onClick={() => {
                                                                window.location.href = `/try-on-live?store=${encodeURIComponent(store.name)}`;
                                                            }}>
                                                                <Radio className="h-4 w-4 mr-2" />
                                                                Watch Live
                                                            </Button>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                );
                            })()}
                        </motion.div>
                    )}
                </div>
            </div>
        </MainLayout>
    );
}
