import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MapPin, Clock, Phone, ChevronRight, Check, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { mockStores, type Store } from '@/services/orderData';
import { cn } from '@/lib/utils';
import { createTransition } from '@/motion';

interface StoreLocatorProps {
    productName?: string;
    isOpen: boolean;
    onClose: () => void;
    onSelectStore?: (store: Store) => void;
}

export function StoreLocator({ productName, isOpen, onClose, onSelectStore }: StoreLocatorProps) {
    const [selectedStore, setSelectedStore] = useState<Store | null>(null);

    const handleSelectStore = (store: Store) => {
        if (store.hasStock) {
            setSelectedStore(store);
            onSelectStore?.(store);
        }
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    {/* Backdrop */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="fixed inset-0 bg-charcoal/60 backdrop-blur-sm z-50"
                    />

                    {/* Modal */}
                    <motion.div
                        initial={{ opacity: 0, y: '100%' }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: '100%' }}
                        transition={createTransition({ type: 'spring', damping: 25 })}
                        className="fixed left-0 right-0 bottom-0 md:left-1/2 md:top-1/2 md:-translate-x-1/2 md:-translate-y-1/2 md:bottom-auto w-full md:max-w-lg max-h-[85vh] md:max-h-[80vh] overflow-hidden bg-card border border-border md:rounded-2xl rounded-t-2xl shadow-xl z-50"
                    >
                        {/* Header */}
                        <div className="sticky top-0 bg-card border-b border-border p-4 md:p-6 flex items-center justify-between">
                            <div>
                                <h2 className="text-lg font-display font-semibold">Find In Store</h2>
                                {productName && (
                                    <p className="text-sm text-muted-foreground line-clamp-1">{productName}</p>
                                )}
                            </div>
                            <button
                                onClick={onClose}
                                className="w-8 h-8 rounded-full hover:bg-muted flex items-center justify-center transition-colors"
                            >
                                <X className="h-5 w-5" />
                            </button>
                        </div>

                        {/* Store List */}
                        <div className="overflow-y-auto max-h-[60vh]">
                            <div className="p-4 md:p-6 space-y-3">
                                {mockStores.map((store) => (
                                    <button
                                        key={store.id}
                                        onClick={() => handleSelectStore(store)}
                                        disabled={!store.hasStock}
                                        className={cn(
                                            "w-full text-left p-4 rounded-xl border transition-all",
                                            store.hasStock
                                                ? "border-border hover:border-accent hover:bg-muted/50 cursor-pointer"
                                                : "border-border/50 opacity-60 cursor-not-allowed",
                                            selectedStore?.id === store.id && "border-accent bg-accent/5 ring-2 ring-accent/20"
                                        )}
                                    >
                                        <div className="flex items-start justify-between gap-3">
                                            <div className="flex-1">
                                                <div className="flex items-center gap-2">
                                                    <h3 className="font-semibold">{store.name}</h3>
                                                    {selectedStore?.id === store.id && (
                                                        <Check className="h-4 w-4 text-accent" />
                                                    )}
                                                </div>
                                                <p className="text-sm text-muted-foreground mt-1">
                                                    {store.address}, {store.city}, {store.state} {store.zipCode}
                                                </p>
                                                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-xs text-muted-foreground">
                                                    <span className="flex items-center gap-1">
                                                        <MapPin className="h-3 w-3" />
                                                        {store.distance} mi away
                                                    </span>
                                                    <span className="flex items-center gap-1">
                                                        <Phone className="h-3 w-3" />
                                                        {store.phone}
                                                    </span>
                                                </div>
                                            </div>
                                            <div className="text-right shrink-0">
                                                <span className={cn(
                                                    "inline-block px-2 py-1 rounded-md text-xs font-medium",
                                                    store.hasStock
                                                        ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400"
                                                        : "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400"
                                                )}>
                                                    {store.hasStock ? 'In Stock' : 'Out of Stock'}
                                                </span>
                                                {store.hasStock && store.pickupTime && (
                                                    <p className="text-xs text-muted-foreground mt-1 flex items-center justify-end gap-1">
                                                        <Clock className="h-3 w-3" />
                                                        {store.pickupTime}
                                                    </p>
                                                )}
                                            </div>
                                        </div>
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Footer */}
                        <div className="sticky bottom-0 bg-card border-t border-border p-4 md:p-6">
                            <Button
                                variant="hero"
                                size="lg"
                                className="w-full"
                                disabled={!selectedStore}
                                onClick={() => {
                                    if (selectedStore) {
                                        onClose();
                                    }
                                }}
                            >
                                {selectedStore ? (
                                    <>
                                        Reserve at {selectedStore.name}
                                        <ChevronRight className="h-4 w-4 ml-2" />
                                    </>
                                ) : (
                                    'Select a Store'
                                )}
                            </Button>
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}
