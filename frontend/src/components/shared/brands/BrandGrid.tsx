import { motion } from "framer-motion";
import { createStaggerTransition } from "@/motion";
import { BrandCard, type BrandCardModel } from "./BrandCard";

export function BrandGrid({ brands }: { brands: BrandCardModel[] }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {brands.map((brand, index) => (
        <motion.div
          key={brand.id}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={createStaggerTransition(index)}
          className="h-full"
        >
          <BrandCard brand={brand} />
        </motion.div>
      ))}
    </div>
  );
}

