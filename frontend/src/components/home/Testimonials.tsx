import { motion } from 'framer-motion';
import { Quote } from 'lucide-react';
import { createTransition } from '@/motion';

const testimonials = [
  {
    id: 1,
    quote: "CONFIT transformed how I shop. The virtual try-on is incredibly accurate — I haven't returned a single item since using it.",
    author: "Sarah M.",
    role: "Fashion Enthusiast",
    avatar: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&h=100&fit=crop",
  },
  {
    id: 2,
    quote: "The AI stylist understands my taste better than I do. It creates outfits I never would have thought of but absolutely love.",
    author: "James L.",
    role: "Creative Director",
    avatar: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&h=100&fit=crop",
  },
  {
    id: 3,
    quote: "Finally, a shopping experience that respects my time and budget. The outfit builder is genius.",
    author: "Emily R.",
    role: "Marketing Executive",
    avatar: "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=100&h=100&fit=crop",
  },
];

export function Testimonials() {
  return (
    <section className="py-16 md:py-24 bg-primary text-primary-foreground overflow-hidden">
      <div className="container">
        <div className="text-center mb-12">
          <h2 className="heading-section mb-4">Worn with Confidence</h2>
          <p className="text-primary-foreground/70 max-w-xl mx-auto">
            Join thousands who've discovered their style with CONFIT.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-8">
          {testimonials.map((testimonial, index) => (
            <motion.div
              key={testimonial.id}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={createTransition({ duration: 0.5, delay: index * 0.1 })}
              className="relative"
            >
              <div className="bg-charcoal-light/30 backdrop-blur-sm rounded-xl p-8 h-full border border-primary-foreground/10">
                <Quote className="h-8 w-8 text-accent mb-6 opacity-60" />
                <blockquote className="text-lg text-primary-foreground/90 mb-6 leading-relaxed">
                  "{testimonial.quote}"
                </blockquote>
                <div className="flex items-center gap-4">
                  <img
                    src={testimonial.avatar}
                    alt={testimonial.author}
                    className="w-12 h-12 rounded-full object-cover"
                  />
                  <div>
                    <p className="font-medium text-primary-foreground">
                      {testimonial.author}
                    </p>
                    <p className="text-sm text-primary-foreground/60">
                      {testimonial.role}
                    </p>
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
