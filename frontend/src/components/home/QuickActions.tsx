import { motion } from 'framer-motion';
import Link from 'next/link';
import { ArrowRight, Sparkles, Camera, Layers, Shirt, Dna } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { createTransition } from '@/motion';

const quickActions = [
  {
    id: 'style-me',
    icon: Sparkles,
    title: 'Style Me',
    description: 'Get AI-powered outfit recommendations tailored to your style and occasion.',
    href: '/stylist',
    color: 'bg-accent/10 text-accent',
  },
  {
    id: 'try-on',
    icon: Camera,
    title: 'Virtual Try-On',
    description: 'See how clothes look on you before you buy with our AR technology.',
    href: '/try-on',
    color: 'bg-champagne/10 text-champagne-dark',
  },
  {
    id: 'build-outfit',
    icon: Layers,
    title: 'Build Outfit',
    description: 'Mix and match pieces across brands to create your perfect look.',
    href: '/outfits',
    color: 'bg-charcoal/5 text-charcoal',
  },
  {
    id: 'wardrobe',
    icon: Shirt,
    title: 'My Wardrobe',
    description: 'Digitize your closet and get smart suggestions using what you own.',
    href: '/wardrobe',
    color: 'bg-muted text-muted-foreground',
  },
  {
    id: 'fashion-os',
    icon: Dna,
    title: 'Fashion OS',
    description: 'Identity layer: Style DNA, daily outfit, closet intelligence, and DNA-aware stylist.',
    href: '/fashion-os',
    color: 'bg-violet-500/10 text-violet-700 dark:text-violet-300',
  },
];

export function QuickActions() {
  return (
    <section className="py-16 md:py-24">
      <div className="container">
        <div className="text-center mb-12">
          <h2 className="heading-section mb-4">Your Style Journey</h2>
          <p className="text-muted-foreground max-w-xl mx-auto">
            Powerful tools to transform how you discover, try, and wear fashion.
          </p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6">
          {quickActions.map((action, index) => {
            const Icon = action.icon;
            return (
              <motion.div
                key={action.id}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={createTransition({ duration: 0.4, delay: index * 0.1 })}
              >
                <Link
                  href={action.href}
                  className="group card-interactive h-full p-6 flex flex-col"
                >
                  <div className={`w-12 h-12 rounded-lg ${action.color} flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300`}>
                    <Icon className="h-6 w-6" />
                  </div>
                  <h3 className="heading-card mb-2 group-hover:text-accent transition-colors">
                    {action.title}
                  </h3>
                  <p className="text-body-sm text-muted-foreground flex-1">
                    {action.description}
                  </p>
                  <div className="mt-4 flex items-center text-sm font-medium text-accent opacity-0 group-hover:opacity-100 transition-opacity">
                    Get Started
                    <ArrowRight className="h-4 w-4 ml-1 group-hover:translate-x-1 transition-transform" />
                  </div>
                </Link>
              </motion.div>
            );
          })}
        </div>

        <div className="mt-12 text-center">
          <Button variant="elegant" size="lg" asChild>
            <Link href="/discover">
              Explore All Features
              <ArrowRight className="h-4 w-4 ml-2" />
            </Link>
          </Button>
        </div>
      </div>
    </section>
  );
}
