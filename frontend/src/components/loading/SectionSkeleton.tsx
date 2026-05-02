'use client';

import { motion } from 'framer-motion';

export function SectionSkeleton() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="w-full py-16"
    >
      <div className="container mx-auto px-4">
        {/* Section header shimmer */}
        <div className="mb-8 max-w-2xl space-y-3">
          <div className="h-8 w-48 rounded-lg bg-gradient-to-r from-white/5 via-white/10 to-white/5 animate-shimmer" />
          <div className="h-4 w-96 rounded-lg bg-gradient-to-r from-white/5 via-white/10 to-white/5 animate-shimmer" />
        </div>

        {/* Content grid shimmer */}
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="space-y-3 rounded-xl border border-white/5 p-3"
            >
              <div className="aspect-[3/4] w-full rounded-lg bg-gradient-to-r from-white/5 via-white/10 to-white/5 animate-shimmer" />
              <div className="space-y-2">
                <div className="h-4 w-3/4 rounded bg-gradient-to-r from-white/5 via-white/10 to-white/5 animate-shimmer" />
                <div className="h-3 w-1/2 rounded bg-gradient-to-r from-white/5 via-white/10 to-white/5 animate-shimmer" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}
