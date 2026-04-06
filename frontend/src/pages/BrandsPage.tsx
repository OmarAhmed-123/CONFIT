import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Search } from 'lucide-react';
import { MainLayout } from '@/components/layout/MainLayout';
import { Input } from '@/components/ui/input';
import { createStaggerTransition } from '@/motion';
import { AnimatedSection, HoverRevealCard, ScrollReveal, TiltCard } from '@/components/experience/interactive';
import { BrandGrid } from '@/components/shared';

interface Brand {
    id: string;
    name: string;
    description: string;
    type: 'Luxury' | 'Streetwear' | 'Sustainable' | 'Local' | 'Fast Fashion';
    origin: string;
    productCount: number;
    logo?: string;
}

// Extended mock data or fetch from backend
const MOCK_BRANDS: Brand[] = [
    { id: 'brand-gucci', name: 'Gucci', description: 'Innovative, progressive, wholly modern.', type: 'Luxury', origin: 'Italy', productCount: 156 },
    { id: 'brand-nike', name: 'Nike', description: 'Just Do It. Innovation and inspiration for every athlete.', type: 'Streetwear', origin: 'USA', productCount: 342 },
    { id: 'brand-zara', name: 'Zara', description: 'Latest trends in clothing for women, men & kids.', type: 'Fast Fashion', origin: 'Spain', productCount: 890 },
    { id: 'brand-patagonia', name: 'Patagonia', description: 'Build the best product, cause no unnecessary harm.', type: 'Sustainable', origin: 'USA', productCount: 120 },
    { id: 'brand-confit', name: 'CONFIT Essentials', description: 'Premium basics for the modern wardrobe.', type: 'Local', origin: 'Egypt', productCount: 45 },
    { id: 'brand-supreme', name: 'Supreme', description: 'New York skateboarding shop and clothing brand.', type: 'Streetwear', origin: 'USA', productCount: 85 },
    { id: 'brand-chanel', name: 'Chanel', description: 'Ultimate luxury and timeless style.', type: 'Luxury', origin: 'France', productCount: 98 },
    { id: 'brand-off-white', name: 'Off-White', description: 'Defining the grey area between black and white.', type: 'Streetwear', origin: 'Italy', productCount: 110 },
    { id: 'brand-h-m', name: 'H&M', description: 'Fashion and quality at the best price.', type: 'Fast Fashion', origin: 'Sweden', productCount: 650 },
    { id: 'brand-cairo-cotton', name: 'Cairo Cotton Co.', description: 'The finest Egyptian cotton essentials.', type: 'Local', origin: 'Egypt', productCount: 30 },
];

export default function BrandsPage() {
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedType, setSelectedType] = useState<string | null>(null);
    const [brands, setBrands] = useState<Brand[]>(MOCK_BRANDS);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        // Show mock data immediately, then try to fetch from API
        const fetchBrands = async () => {
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 2000);
                
                const { apiUrl } = await import('@/lib/api');
                const response = await fetch(apiUrl('/api/brands'), { signal: controller.signal });
                clearTimeout(timeoutId);
                
                if (response.ok) {
                    const data: unknown = await response.json();
                    if (!Array.isArray(data)) return;

                    type ApiBrandRow = {
                        id?: string;
                        name?: string;
                        description?: string;
                        logo?: string;
                        productCount?: number;
                    };

                    const mapped: Brand[] = data
                        .map((row) => {
                            if (!row || typeof row !== "object") return null;
                            const r = row as ApiBrandRow;
                            const name = typeof r.name === "string" ? r.name : "";
                            if (!name) return null;

                            return {
                                id: r.id ?? `brand-${name.toLowerCase().replace(/\s+/g, "-")}`,
                                name,
                                description: typeof r.description === "string" ? r.description : "",
                                type: determineBrandType(name) as Brand["type"],
                                origin: "Global",
                                productCount: typeof r.productCount === "number" ? r.productCount : 0,
                                logo: typeof r.logo === "string" ? r.logo : undefined,
                            };
                        })
                        .filter((x): x is Brand => Boolean(x));

                    if (mapped.length > 0) setBrands(mapped);
                }
            } catch (error) {
                if (error instanceof Error && error.name !== 'AbortError') {
                    console.warn('Error fetching brands, using mock data:', error);
                }
                // Keep MOCK_BRANDS already set
            }
        };

        fetchBrands();
    }, []);

    const filteredBrands = brands.filter(brand => {
        const matchesSearch = brand.name.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesType = selectedType ? brand.type === selectedType : true;
        return matchesSearch && matchesType;
    });

    const types = ['Luxury', 'Streetwear', 'Sustainable', 'Local', 'Fast Fashion'];

    function determineBrandType(name: string): string {
        const lower = name.toLowerCase();
        if (['gucci', 'prada', 'versace', 'chanel', 'dior'].some(b => lower.includes(b))) return 'Luxury';
        if (['supreme', 'nike', 'adidas', 'off-white'].some(b => lower.includes(b))) return 'Streetwear';
        if (['patagonia', 'reformation', 'everlane'].some(b => lower.includes(b))) return 'Sustainable';
        if (['zara', 'h&m', 'uniqlo'].some(b => lower.includes(b))) return 'Fast Fashion';
        return 'Local'; // Default to Local/Boutique for others
    }

    return (
        <MainLayout>
            <div className="container py-8">
                {/* Header */}
                <ScrollReveal className="text-center max-w-2xl mx-auto mb-12">
                    <h1 className="heading-hero mb-4">Our Brands</h1>
                    <p className="text-muted-foreground">
                        Discover a curated collection of world-class international designers and unique local labels.
                        From high-end luxury to sustainable essentials.
                    </p>
                </ScrollReveal>

                {/* Filters */}
                <div className="flex flex-col md:flex-row gap-4 mb-8 items-center justify-between">
                    <div className="relative w-full md:w-96">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                        <Input
                            placeholder="Search brands..."
                            className="pl-10"
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                        />
                    </div>
                    <div className="flex flex-wrap gap-2">
                        <button
                            onClick={() => setSelectedType(null)}
                            className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${!selectedType ? 'bg-foreground text-background' : 'bg-muted hover:bg-muted/80'}`}
                        >
                            All
                        </button>
                        {types.map(type => (
                            <button
                                key={type}
                                onClick={() => setSelectedType(type)}
                                className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${selectedType === type ? 'bg-foreground text-background' : 'bg-muted hover:bg-muted/80'}`}
                            >
                                {type}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Grid */}
                <AnimatedSection
                    className="mt-2"
                    title="Luxury Brand Showcase"
                    subtitle="Curated labels with seamless discovery, cinematic micro-interactions, and editorial rhythm."
                >
                <BrandGrid brands={filteredBrands} />
                </AnimatedSection>

                {filteredBrands.length === 0 && (
                    <div className="text-center py-20">
                        <p className="text-muted-foreground">No brands found matching your criteria.</p>
                        <button
                            onClick={() => { setSearchTerm(''); setSelectedType(null); }}
                            className="text-accent hover:underline mt-2"
                        >
                            Clear filters
                        </button>
                    </div>
                )}
            </div>
        </MainLayout>
    );
}
