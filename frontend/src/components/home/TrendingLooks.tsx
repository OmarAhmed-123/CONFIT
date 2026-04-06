import { motion } from 'framer-motion';
import Link from 'next/link';
import { ArrowRight, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { featuredOutfits } from '@/services/mockData';
import { createTransition } from '@/motion';

export function TrendingLooks() {
    return (
        <section className="py-16 md:py-24 bg-background">
            <div className="container">
                <div className="flex flex-col md:flex-row justify-between items-end gap-6 mb-12">
                    <div className="max-w-2xl">
                        <div className="inline-flex items-center gap-2 bg-accent/10 text-accent px-3 py-1 rounded-full text-xs font-medium mb-3">
                            <Sparkles className="h-3 w-3" />
                            <span>Trending Now</span>
                        </div>
                        <h2 className="heading-section mb-4">Curated Looks for You</h2>
                        <p className="text-muted-foreground">
                            Discover complete outfits styled by our AI, tailored to current trends and your preferences.
                        </p>
                    </div>
                    <Button variant="link" asChild className="hidden md:inline-flex">
                        <Link href="/discover">
                            View All Trends
                            <ArrowRight className="h-4 w-4 ml-2" />
                        </Link>
                    </Button>
                </div>

                <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
                    {featuredOutfits.map((outfit, index) => (
                        <motion.div
                            key={outfit.id}
                            initial={{ opacity: 0, y: 20 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true }}
                            transition={createTransition({ duration: 0.5, delay: index * 0.1 })}
                            className="group cursor-pointer"
                        >
                            <div className="relative aspect-[4/5] overflow-hidden rounded-xl mb-4 bg-muted">
                                {/* Main Look Image */}
                                <img
                                    src={`https://images.unsplash.com/photo-${['1515886657613-9f3515b0c78f', '1483985988355-763728e1935b', '1539008835657-9e8e9680c956', '1550614000-4b9519879354'][index % 4]}?w=500&h=625&fit=crop`}
                                    alt={outfit.name}
                                    className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
                                />

                                {/* Overlay Gradient */}
                                <div className="absolute inset-0 bg-gradient-to-t from-charcoal/80 via-transparent to-transparent opacity-60 group-hover:opacity-80 transition-opacity" />

                                {/* Content Overlay */}
                                <div className="absolute bottom-0 left-0 right-0 p-6 text-white transform translate-y-4 group-hover:translate-y-0 transition-transform duration-300">
                                    <p className="text-xs font-medium text-accent mb-1 uppercase tracking-wider">
                                        {outfit.occasion}
                                    </p>
                                    <h3 className="font-display font-semibold text-lg leading-tight mb-2">
                                        {outfit.name}
                                    </h3>
                                    <div className="flex items-center justify-between opacity-0 group-hover:opacity-100 transition-opacity duration-300 delay-100">
                                        <span className="font-medium">${outfit.totalPrice}</span>
                                        <span className="text-xs bg-white/20 backdrop-blur px-2 py-1 rounded">
                                            {outfit.styleScore}% Match
                                        </span>
                                    </div>
                                </div>

                                {/* Quick Action */}
                                <div className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                                    <Button variant="gold" size="sm" className="shadow-lg">
                                        Shop Look
                                    </Button>
                                </div>
                            </div>
                        </motion.div>
                    ))}
                </div>

                <div className="mt-8 text-center md:hidden">
                    <Button variant="outline" className="w-full" asChild>
                        <Link href="/discover">View All Trends</Link>
                    </Button>
                </div>
            </div>
        </section>
    );
}
