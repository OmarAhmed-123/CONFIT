import { DiscoverCard } from "./DiscoverCard";
import type { Product } from "@/types";

type Props = {
  products: Product[];
  viewMode: "grid" | "list";
};

export function ProductGrid({ products, viewMode }: Props) {
  return (
    <div
      className={
        viewMode === "grid"
          ? "grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 md:gap-6"
          : "flex flex-col gap-4"
      }
    >
      {products.map((product, index) => (
        <DiscoverCard key={product.id} product={product} index={index} viewMode={viewMode} />
      ))}
    </div>
  );
}

