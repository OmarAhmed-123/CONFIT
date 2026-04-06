import { motion } from 'framer-motion';
import Link from 'next/link';
import { occasions } from '@/services/mockData';
import { createTransition } from '@/motion';

export function OccasionShortcuts() {
  return (
    <section className="py-16 md:py-24 bg-secondary">
      <div className="container">
        <div className="text-center mb-12">
          <h2 className="heading-section mb-4">What's the Occasion?</h2>
          <p className="text-muted-foreground max-w-xl mx-auto">
            Tell us where you're going, and we'll curate the perfect look for you.
          </p>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 md:gap-6">
          {occasions.map((occasion, index) => (
            <motion.div
              key={occasion.id}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={createTransition({ duration: 0.4, delay: index * 0.05 })}
            >
              <Link
                href={`/stylist?occasion=${occasion.id}`}
                className="group card-interactive p-6 md:p-8 flex flex-col items-center text-center"
              >
                <span className="text-4xl md:text-5xl mb-4 group-hover:scale-110 transition-transform duration-300">
                  {occasion.icon}
                </span>
                <span className="font-medium text-foreground group-hover:text-accent transition-colors">
                  {occasion.label}
                </span>
              </Link>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
