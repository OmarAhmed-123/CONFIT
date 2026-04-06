"use client";

import { motion } from "framer-motion";

const providers = [
  { id: "google", label: "Continue with Google" },
  { id: "facebook", label: "Continue with Facebook" },
  { id: "instagram", label: "Continue with Instagram" },
  { id: "x", label: "Continue with X" },
  { id: "tiktok", label: "Continue with TikTok" }
] as const;

export function SocialLoginButtons() {
  return (
    <div className="grid gap-3">
      {providers.map((p, idx) => (
        <motion.a
          key={p.id}
          href={`/auth/${p.id}`}
          initial={{ opacity: 0, y: 20, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ delay: idx * 0.08, type: "spring", stiffness: 520, damping: 38 }}
          whileHover={{ scale: 1.02, boxShadow: "0 12px 32px rgba(0,0,0,0.12)" }}
          whileTap={{ scale: 0.97 }}
          className="rounded-2xl border border-black/10 bg-white px-4 py-3 text-sm font-medium text-black shadow-sm"
        >
          {p.label}
        </motion.a>
      ))}
    </div>
  );
}

