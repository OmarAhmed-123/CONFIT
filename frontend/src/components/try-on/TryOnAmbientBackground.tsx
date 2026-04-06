import { motion } from 'framer-motion';

/** Soft animated mesh — Apple-like calm motion + CONFIT gold accents */
export function TryOnAmbientBackground() {
  return (
    <div
      className="pointer-events-none absolute inset-0 overflow-hidden"
      aria-hidden
    >
      <div className="absolute inset-0 bg-gradient-to-b from-background via-background/95 to-muted/30" />
      <motion.div
        className="absolute -left-[20%] top-[10%] h-[min(520px,50vh)] w-[min(520px,70vw)] rounded-full bg-accent/12 blur-3xl"
        animate={{ x: [0, 24, 0], y: [0, -18, 0], opacity: [0.45, 0.65, 0.45] }}
        transition={{ duration: 14, repeat: Infinity, ease: 'easeInOut' }}
      />
      <motion.div
        className="absolute -right-[15%] bottom-[5%] h-[min(480px,45vh)] w-[min(480px,65vw)] rounded-full bg-primary/10 blur-3xl"
        animate={{ x: [0, -20, 0], y: [0, 22, 0], opacity: [0.35, 0.55, 0.35] }}
        transition={{ duration: 18, repeat: Infinity, ease: 'easeInOut' }}
      />
      <motion.div
        className="absolute left-1/2 top-1/3 h-px w-[120%] -translate-x-1/2 rotate-[12deg] bg-gradient-to-r from-transparent via-border/60 to-transparent"
        animate={{ opacity: [0.2, 0.45, 0.2] }}
        transition={{ duration: 8, repeat: Infinity }}
      />
    </div>
  );
}
