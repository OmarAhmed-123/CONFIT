import React, { useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Sparkles, Bot, User } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { OutfitCard, type OutfitBuild } from "./OutfitCard";
import { trackBehaviorSignal } from "@/services/telemetry";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

export function ChatUI({
  messages,
  isThinking,
  inputValue,
  onChangeInput,
  onSend,
  onPickChip,
  chips,
  latestOutfits,
  onTryOn,
  onReplaceItem,
  onViewProduct,
  budgetMax,
  className,
}: {
  messages: ChatMessage[];
  isThinking: boolean;
  inputValue: string;
  onChangeInput: (v: string) => void;
  onSend: (text: string) => void;
  onPickChip: (chip: string) => void;
  chips: string[];
  latestOutfits: OutfitBuild[];
  onTryOn: (outfitId: string, focus?: any) => void;
  onReplaceItem: (outfitId: string, position: any) => void;
  onViewProduct: (productId: string) => void;
  budgetMax?: number | null;
  className?: string;
}) {
  const [activeOutfitIndex, setActiveOutfitIndex] = useState(0);

  // Reset stack position when new outfits arrive.
  const latestOutfitKey = useMemo(
    () => latestOutfits.map((o) => o.id).join("|"),
    [latestOutfits]
  );

  useEffect(() => {
    setActiveOutfitIndex(0);
  }, [latestOutfitKey]);

  const activeOutfit = latestOutfits[activeOutfitIndex] ?? null;

  const onSendWithTelemetry = (text: string) => {
    void trackBehaviorSignal(
      "stylist_chat",
      "conversation",
      "default",
      {
        message_length: text.trim().length,
        budget_max: budgetMax ?? undefined,
        variant: "ai_stylist_chat",
      }
    );
    onSend(text);
  };

  const onPickChipWithTelemetry = (chip: string) => {
    void trackBehaviorSignal(
      "stylist_chat",
      "conversation",
      "default",
      {
        message_length: chip.trim().length,
        budget_max: budgetMax ?? undefined,
        variant: "ai_stylist_chat_chip",
      }
    );
    onPickChip(chip);
  };

  const onTryOnWithTelemetry = (outfitId: string, focus?: any) => {
    void trackBehaviorSignal(
      "try_on",
      "outfit",
      outfitId,
      {
        focus: focus ?? null,
        source: "ai_chat_outfit_card",
      }
    );
    onTryOn(outfitId, focus);
  };

  const onReplaceItemWithTelemetry = (outfitId: string, position: any) => {
    void trackBehaviorSignal(
      "outfit_edit",
      "outfit",
      outfitId,
      {
        position: position ?? null,
        source: "ai_chat_outfit_card",
      }
    );
    onReplaceItem(outfitId, position);
  };

  const onViewProductWithTelemetry = (productId: string) => {
    void trackBehaviorSignal(
      "quick_view",
      "product",
      productId,
      {
        source: "ai_chat_outfit_card",
      }
    );
    onViewProduct(productId);
  };

  const remainingLabel = useMemo(() => {
    if (budgetMax == null) return null;
    return `Budget set: $${Math.round(budgetMax)}`;
  }, [budgetMax]);

  return (
    <Card
      className={cn("glass-card rounded-3xl border-white/10 overflow-hidden", className)}
    >
      <CardContent className="p-0">
        <div className="px-5 pt-5 pb-3">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full border border-border/60 bg-card/20 backdrop-blur-md px-4 py-2 text-sm font-medium text-foreground">
                <Sparkles className="h-4 w-4 text-accent" />
                <span>AI Stylist</span>
                <span className="text-muted-foreground">·</span>
                <span className="text-muted-foreground">Confidence, Styled</span>
              </div>
              {remainingLabel && (
                <div className="mt-3 text-xs text-muted-foreground">
                  <span className="font-semibold text-foreground">{remainingLabel}</span>
                  {" · "}
                  <span>We’ll keep choices aligned.</span>
                </div>
              )}
            </div>

            <div className="hidden md:flex items-center gap-2">
              <Badge variant="outline" className="border-white/10 bg-card/20">
                {isThinking ? "Thinking" : "Ready"}
              </Badge>
            </div>
          </div>

          {messages.length <= 1 && chips.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-2">
              {chips.map((chip) => (
                <Button
                  key={chip}
                  type="button"
                  variant="outline"
                  size="sm"
                  className="rounded-full border-white/10 bg-card/20 hover:bg-card/30"
                  onClick={() => onPickChipWithTelemetry(chip)}
                  disabled={isThinking}
                >
                  {chip}
                </Button>
              ))}
            </div>
          )}
        </div>

        <div className="px-5 pb-5">
          <div className="max-h-[420px] overflow-y-auto no-scrollbar pr-2 space-y-4">
            <AnimatePresence mode="popLayout">
              {messages.map((m) => (
                <motion.div
                  key={m.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.25, ease: "easeInOut" }}
                  className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}
                >
                  <div
                    className={cn(
                      "max-w-[90%] rounded-2xl px-4 py-3 border",
                      m.role === "user"
                        ? "bg-gradient-to-r from-violet-500/20 to-blue-500/10 border-white/10"
                        : "bg-card/30 border-border/60 backdrop-blur-sm"
                    )}
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <span className={cn("w-7 h-7 rounded-full flex items-center justify-center", m.role === "user" ? "bg-gradient-to-r from-violet-500 to-blue-500 text-white" : "bg-muted text-foreground")}>
                        {m.role === "user" ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4 text-accent" />}
                      </span>
                      <span className="text-xs font-semibold text-muted-foreground">
                        {m.role === "user" ? "You" : "Stylist"}
                      </span>
                    </div>
                    <p className="text-sm leading-relaxed whitespace-pre-wrap">{m.content}</p>
                  </div>
                </motion.div>
              ))}

              {isThinking && (
                <motion.div
                  key="thinking"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="flex justify-start"
                >
                  <div className="max-w-[90%] rounded-2xl px-4 py-3 border bg-card/30 border-border/60 backdrop-blur-sm">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="w-7 h-7 rounded-full flex items-center justify-center bg-muted text-foreground">
                        <Bot className="h-4 w-4 text-accent" />
                      </span>
                      <span className="text-xs font-semibold text-muted-foreground">Stylist</span>
                    </div>
                    <div className="space-y-3">
                      <div className="h-3 w-44 rounded-full bg-white/10 overflow-hidden">
                        <div className="h-full w-full animate-shimmer bg-[linear-gradient(90deg,transparent,rgba(255,255,255,0.25),transparent)]" />
                      </div>
                      <div className="flex gap-2">
                        {[0, 1, 2].map((i) => (
                          <span
                            key={i}
                            className="w-2 h-2 rounded-full bg-accent/80 animate-bounce"
                            style={{ animationDelay: `${i * 0.1}s` }}
                          />
                        ))}
                      </div>
                      <p className="text-xs text-muted-foreground">Building options with color harmony…</p>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {latestOutfits.length > 0 && activeOutfit && (
              <div className="pt-2">
                <div className="flex items-center justify-between mb-3 px-1">
                  <div className="text-xs text-muted-foreground">Swipe to explore</div>
                  <div className="text-xs text-muted-foreground">
                    {activeOutfitIndex + 1}/{Math.min(latestOutfits.length, 4)}
                  </div>
                </div>

                <div className="relative">
                  <div className="absolute inset-0 -z-10 opacity-35 blur-[0px]">
                    {latestOutfits[activeOutfitIndex + 1] ? (
                      <OutfitCard
                        outfit={latestOutfits[activeOutfitIndex + 1]}
                      onTryOn={onTryOnWithTelemetry}
                      onReplaceItem={onReplaceItemWithTelemetry}
                      onViewProduct={onViewProductWithTelemetry}
                        className="scale-[0.985] opacity-70 pointer-events-none"
                      />
                    ) : null}
                  </div>

                  <AnimatePresence mode="wait">
                    <motion.div
                      key={activeOutfit.id}
                      drag="x"
                      dragConstraints={{ left: -120, right: 120 }}
                      onDragEnd={(_, info) => {
                        const dx = info.offset.x;
                        const threshold = 85;
                        if (Math.abs(dx) < threshold) return;
                        const currentId = activeOutfit?.id;
                        if (currentId) {
                          void trackBehaviorSignal("scroll_past", "outfit_stack", currentId, {
                            direction: dx < 0 ? "next" : "prev",
                            source: "ai_chat_outfit_swipe",
                          });
                        }
                        if (dx < 0) {
                          setActiveOutfitIndex((v) => Math.min(Math.min(latestOutfits.length, 4) - 1, v + 1));
                        } else {
                          setActiveOutfitIndex((v) => Math.max(0, v - 1));
                        }
                      }}
                      initial={{ opacity: 0, y: 10, filter: "blur(8px)", scale: 0.985 }}
                      animate={{ opacity: 1, y: 0, filter: "blur(0px)", scale: 1 }}
                      exit={{ opacity: 0, y: -8, filter: "blur(8px)", scale: 0.99 }}
                      transition={{ duration: 0.28, ease: "easeInOut" }}
                      whileTap={{ scale: 0.99 }}
                    >
                      <OutfitCard
                        outfit={activeOutfit}
                        onTryOn={onTryOnWithTelemetry}
                        onReplaceItem={onReplaceItemWithTelemetry}
                        onViewProduct={onViewProductWithTelemetry}
                      />
                    </motion.div>
                  </AnimatePresence>

                  <div className="mt-3 flex items-center justify-center gap-2">
                    {Array.from({ length: Math.min(latestOutfits.length, 4) }).map((_, i) => {
                      const isActive = i === activeOutfitIndex;
                      return (
                        <button
                          key={i}
                          type="button"
                          aria-label={`Outfit ${i + 1}`}
                          onClick={() => setActiveOutfitIndex(i)}
                          className={[
                            "h-1.5 w-8 rounded-full transition",
                            isActive ? "bg-accent/90" : "bg-white/10 hover:bg-white/15",
                          ].join(" ")}
                        />
                      );
                    })}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="border-t border-border/60 bg-card/10 px-5 py-4">
          <div className="flex gap-3 items-end">
            <div className="flex-1 relative">
              <Textarea
                value={inputValue}
                onChange={(e) => onChangeInput(e.target.value)}
                placeholder="I need a wedding outfit under $150"
                disabled={isThinking}
                className="min-h-[44px] max-h-[120px] pr-12 rounded-2xl border-white/10 bg-background/30 focus-visible:ring-accent/40"
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    void onSendWithTelemetry(inputValue);
                  }
                }}
              />

              <div className="absolute right-3 bottom-3">
                <span className="text-[11px] text-muted-foreground hidden sm:inline">
                  Enter · Send
                </span>
              </div>
            </div>

            <motion.div whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.98 }}>
              <Button
                size="lg"
                className="rounded-full h-11 bg-gradient-to-r from-violet-500 to-blue-500 text-white hover:from-violet-400 hover:to-blue-400 shadow-lg disabled:opacity-60"
                disabled={isThinking || !inputValue.trim()}
                onClick={() => void onSendWithTelemetry(inputValue)}
              >
                <Send className="h-4 w-4 mr-2" />
                Send
              </Button>
            </motion.div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

