import { Globe, ShoppingBag } from "lucide-react";
import Link from 'next/link';
import { Badge } from "@/components/ui/badge";
import { HoverRevealCard, TiltCard } from "@/components/experience/interactive";

export type BrandCardModel = {
  id: string;
  name: string;
  description: string;
  type: string;
  origin: string;
  productCount: number;
};

export function BrandCard({ brand }: { brand: BrandCardModel }) {
  return (
    <TiltCard className="h-full">
      <HoverRevealCard
        className="h-full p-6"
        reveal={
          <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/35 to-transparent p-5 flex items-end rounded-2xl">
            <p className="text-sm text-white/90 leading-relaxed">{brand.description}</p>
          </div>
        }
      >
        <div className="flex justify-between items-start mb-4">
          <div className="w-12 h-12 bg-foreground text-background rounded-full flex items-center justify-center font-serif text-xl font-bold">
            {brand.name.substring(0, 1)}
          </div>
          <Badge variant="outline" className="bg-background">
            {brand.type}
          </Badge>
        </div>

        <h3 className="text-xl font-bold mb-2 group-hover:text-accent transition-colors">{brand.name}</h3>
        <p className="text-sm text-muted-foreground mb-4 line-clamp-2 h-10">{brand.description}</p>

        <div className="flex items-center gap-4 text-xs text-muted-foreground mb-6">
          <span className="flex items-center gap-1">
            <Globe className="h-3 w-3" /> {brand.origin}
          </span>
          <span className="flex items-center gap-1">
            <ShoppingBag className="h-3 w-3" /> {brand.productCount} Products
          </span>
        </div>

        <Link
          href={`/discover?brand=${brand.name}`}
          className="block w-full py-2.5 text-center bg-muted hover:bg-accent hover:text-white rounded-lg font-medium transition-colors text-sm"
        >
          View Collection
        </Link>
      </HoverRevealCard>
    </TiltCard>
  );
}

