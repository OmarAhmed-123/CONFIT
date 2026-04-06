import { Button } from "@/components/ui/button";
import Link from 'next/link';
import { ArrowRight, Sparkles } from "lucide-react";
import { motion } from "framer-motion";
import { createTransition } from '@/motion';

export const HeroSection = () => {
  return (
    <section className="relative min-h-[90vh] flex items-center justify-center overflow-hidden bg-[#F8F9FA] dark:bg-black/95">
      {/* Abstract Background Elements */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-[-10%] right-[-5%] w-[50vw] h-[50vw] bg-purple-200/30 rounded-full blur-3xl animate-float" />
        <div className="absolute bottom-[-10%] left-[-10%] w-[60vw] h-[60vw] bg-blue-200/30 rounded-full blur-3xl animate-float delay-1000" />
        <div className="absolute top-[20%] left-[15%] w-[20vw] h-[20vw] bg-pink-200/20 rounded-full blur-3xl animate-float delay-2000" />
      </div>

      <div className="container px-4 md:px-6 relative z-10 grid lg:grid-cols-2 gap-12 items-center">

        {/* Text Content */}
        <motion.div
          initial={{ opacity: 0, x: -50 }}
          animate={{ opacity: 1, x: 0 }}
          transition={createTransition({ duration: 0.8, ease: "easeOut" })}
          className="space-y-8 text-center lg:text-left"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/5 border border-primary/10 text-primary/80 text-sm font-medium">
            <Sparkles className="w-4 h-4 text-amber-500" />
            <span>Personal Styling</span>
          </div>

          <h1 className="text-5xl md:text-7xl font-bold tracking-tight leading-[1.1]">
            Wear Your <br />
            <span className="text-gradient-gold">Confidence</span>
          </h1>

          <p className="text-xl text-muted-foreground leading-relaxed max-w-xl mx-auto lg:mx-0">
            Discover a fashion experience tailored to your unique style.
            Virtual try-on, AI styling, and premium collections in one seamless journey.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center lg:justify-start">
            <Button size="lg" className="rounded-full px-8 h-12 text-base shadow-lg hover:shadow-primary/25 transition-all" asChild>
              <Link href="/discover">
                Start Exploring
                <ArrowRight className="ml-2 w-5 h-5" />
              </Link>
            </Button>
            <Button size="lg" variant="outline" className="rounded-full px-8 h-12 text-base glass-card border-2" asChild>
              <Link href="/stylist">
                Meet Your AI Stylist
              </Link>
            </Button>
          </div>

          {/* Trust Indicators */}
          <div className="pt-8 flex items-center justify-center lg:justify-start gap-8 text-sm text-muted-foreground/60">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-foreground">500+</span> Brands
            </div>
            <div className="w-1 h-1 bg-current rounded-full" />
            <div className="flex items-center gap-2">
              <span className="font-semibold text-foreground">10k+</span> Outfits Created
            </div>
          </div>
        </motion.div>

        {/* Visual Content - 3D/Image Composition */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={createTransition({ duration: 0.8, delay: 0.2 })}
          className="relative h-[500px] hidden lg:block"
        >
          {/* Main Hero Image */}
          <div className="relative z-20 h-full w-full rounded-[2rem] overflow-hidden shadow-2xl glass-panel p-2">
            <div className="h-full w-full rounded-[1.5rem] overflow-hidden relative">
              <img
                src="https://images.unsplash.com/photo-1483985988355-763728e1935b?w=800&q=80"
                alt="Fashion Model"
                className="object-cover w-full h-full hover:scale-105 transition-transform duration-700"
              />

              {/* Floating UI Cards */}
              <motion.div
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={createTransition({ delay: 0.6 })}
                className="absolute bottom-6 left-6 right-6 glass-panel rounded-xl p-4 flex items-center gap-4"
              >
                <div className="w-12 h-12 rounded-full bg-black flex items-center justify-center text-white font-bold">
                  C
                </div>
                <div>
                  <p className="text-sm font-medium">Outfit Match Score</p>
                  <div className="flex items-center gap-2">
                    <div className="h-2 w-32 bg-gray-200 rounded-full overflow-hidden">
                      <div className="h-full bg-green-500 w-[92%]" />
                    </div>
                    <span className="text-xs font-bold text-green-600">92%</span>
                  </div>
                </div>
              </motion.div>
            </div>
          </div>

          {/* Decorative Backdrops */}
          <div className="absolute top-10 -right-10 w-full h-full border-2 border-dashed border-primary/20 rounded-[2rem] z-0" />
          <div className="absolute -bottom-10 -left-10 w-full h-full border-2 border-primary/10 rounded-[2rem] z-0" />
        </motion.div>
      </div>
    </section>
  );
};
