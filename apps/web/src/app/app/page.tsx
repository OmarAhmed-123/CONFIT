"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "@/components/session/SessionProvider";
import { motion, AnimatePresence } from "framer-motion";
import { Check, LogOut, User, Mail, Shield, ChevronRight } from "lucide-react";

export default function ProtectedHome() {
  const { state, logout } = useSession();
  const router = useRouter();
  const [showContinueAs, setShowContinueAs] = useState(true);

  useEffect(() => {
    if (state.status === "unauthenticated") router.replace("/login");
  }, [state.status, router]);

  // Hide "Continue as" popup after 5 seconds
  useEffect(() => {
    if (state.status === "authenticated") {
      const timer = setTimeout(() => setShowContinueAs(false), 5000);
      return () => clearTimeout(timer);
    }
  }, [state.status]);

  if (state.status !== "authenticated") {
    return (
      <div className="flex flex-1 items-center justify-center bg-neutral-950 text-white">
        <div className="rounded-2xl border border-white/10 bg-white/5 px-6 py-5">Loading session…</div>
      </div>
    );
  }

  const user = state.user;
  const initials = user.name?.split(" ").map(n => n[0]).join("").toUpperCase() || "U";

  return (
    <div className="flex flex-1 items-center justify-center bg-neutral-950 px-6 py-16 text-white relative">
      {/* "Continue as" Popup - Modern UX */}
      <AnimatePresence>
        {showContinueAs && (
          <motion.div
            initial={{ opacity: 0, y: -20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.98 }}
            className="absolute top-6 right-6 z-50"
          >
            <div className="rounded-2xl border border-white/20 bg-white/10 p-4 backdrop-blur-xl shadow-2xl max-w-xs">
              <div className="flex items-center gap-3">
                {user.pictureUrl ? (
                  <img 
                    src={user.pictureUrl} 
                    alt={user.name || "User"} 
                    className="h-12 w-12 rounded-full border-2 border-white/30 object-cover"
                  />
                ) : (
                  <div className="h-12 w-12 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-lg font-semibold border-2 border-white/30">
                    {initials}
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 text-xs text-green-400 mb-0.5">
                    <Check className="h-3 w-3" />
                    <span>Signed in</span>
                  </div>
                  <p className="font-medium text-white truncate">{user.name || "User"}</p>
                  <p className="text-xs text-white/60 truncate">{user.primaryEmail || ""}</p>
                </div>
                <button
                  onClick={() => setShowContinueAs(false)}
                  className="text-white/40 hover:text-white/80 p-1"
                  aria-label="Dismiss notification"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Welcome Card */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-xl rounded-3xl border border-white/10 bg-white/5 p-8 backdrop-blur"
      >
        <div className="flex items-start justify-between gap-6">
          <div className="flex items-center gap-4">
            {user.pictureUrl ? (
              <img 
                src={user.pictureUrl} 
                alt={user.name || "User"} 
                className="h-16 w-16 rounded-full border-2 border-white/20 object-cover"
              />
            ) : (
              <div className="h-16 w-16 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-2xl font-semibold border-2 border-white/20">
                {initials}
              </div>
            )}
            <div>
              <h1 className="text-2xl font-semibold tracking-tight">
                Welcome{user.name ? `, ${user.name.split(" ")[0]}` : ""}
              </h1>
              <div className="flex items-center gap-2 mt-1 text-sm text-white/60">
                <Mail className="h-3.5 w-3.5" />
                <span>{user.primaryEmail || "No email"}</span>
              </div>
            </div>
          </div>
          <button
            onClick={() => void logout()}
            className="flex items-center gap-2 rounded-xl bg-white/10 hover:bg-white/20 px-4 py-2 text-sm font-medium text-white transition-colors"
          >
            <LogOut className="h-4 w-4" />
            Log out
          </button>
        </div>
        
        <div className="mt-6 pt-6 border-t border-white/10">
          <div className="flex items-center gap-2 text-sm text-white/70">
            <Shield className="h-4 w-4 text-green-400" />
            <span>Your session is secured with short-lived access tokens + rotating refresh.</span>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

