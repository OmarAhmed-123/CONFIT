import { ProductCard } from "@/components/product/ProductCard";
import { InteractiveCard, ScrollReveal } from "@/components/experience/interactive";
import type { Product } from "@/types";

type Props = {
  product: Product;
  index: number;
  viewMode: "grid" | "list";
};

export function DiscoverCard({ product, index, viewMode }: Props) {
  return (
    <ScrollReveal>
      <InteractiveCard className="h-full">
        <ProductCard product={product} index={index} viewMode={viewMode} />
      </InteractiveCard>
    </ScrollReveal>
  );
}

