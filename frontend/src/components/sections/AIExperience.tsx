import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from 'next/navigation';
import { AnimatePresence, motion } from "framer-motion";
import {
  Sparkles,
  Wand2,
  Camera,
  RefreshCw,
  Pause,
  Play,
  ArrowRight,
} from "lucide-react";
import { useGender } from "@/context/GenderContext";
import { apiUrl } from "@/lib/api";
import { getProductsByCategory, featuredOutfits } from "@/services/mockData";
import type { Product } from "@/types";

import { ChatUI, type ChatMessage } from "@/components/ai/ChatUI";
import type { OutfitBuild, OutfitItemPosition } from "@/components/ai/OutfitCard";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

function parseBudgetMax(text: string): number | null {
  const t = text.toLowerCase();

  // Common patterns: "under $150", "below 150", "budget 150", "max $120"
  const patterns: RegExp[] = [
    /under\s*\$?\s*([\d,]+)/i,
    /below\s*\$?\s*([\d,]+)/i,
    /max\s*\$?\s*([\d,]+)/i,
    /budget\s*\$?\s*([\d,]+)/i,
    /<=\s*\$?\s*([\d,]+)/i,
    /\$?\s*([\d,]+)\s*(?:usd|dollars)?\s*(?:or less)?/i,
  ];

  for (const p of patterns) {
    const m = t.match(p);
    if (m?.[1]) {
      const raw = String(m[1]).replace(/,/g, "");
      const n = Number(raw);
      if (Number.isFinite(n) && n > 0) return n;
    }
  }
  return null;
}

function parseOccasionHint(text: string): string | undefined {
  const t = text.toLowerCase();
  const map: Array<[string, string[]]> = [
    ["wedding", ["wedding", "bride", "groom", "marriage", "ceremony", "nuptial"]],
    ["work", ["work", "office", "business", "meeting", "interview", "professional", "corporate"]],
    ["party", ["party", "club", "night out", "birthday", "celebration", "celebrate"]],
    ["date", ["date", "dinner date", "romantic", "anniversary", "first date"]],
    ["casual", ["casual", "everyday", "weekend", "relaxed", "lounge", "shopping"]],
    ["active", ["gym", "workout", "exercise", "run", "running", "sport", "athletic"]],
    ["formal", ["formal", "gala", "black tie", "red carpet", "ceremony"]],
  ];

  for (const [occasion, keywords] of map) {
    if (keywords.some((k) => t.includes(k))) return occasion;
  }
  return undefined;
}

function parseStyleHint(text: string): string | undefined {
  const t = text.toLowerCase();
  const map: Array<[string, string[]]> = [
    ["classic", ["classic", "timeless", "elegant", "traditional"]],
    ["modern", ["modern", "contemporary", "trendy", "current"]],
    ["minimalist", ["minimalist", "minimal", "clean", "capsule"]],
    ["bohemian", ["bohemian", "boho", "flowy", "free-spirited"]],
    ["streetwear", ["streetwear", "street", "urban", "sneaker"]],
    ["edgy", ["edgy", "rock", "punk", "alternative", "bold"]],
  ];

  for (const [style, keywords] of map) {
    if (keywords.some((k) => t.includes(k))) return style;
  }
  return undefined;
}

function parseBudgetLevelHint(budgetMax: number | null, text: string): string | undefined {
  if (budgetMax != null) {
    if (budgetMax <= 100) return "budget";
    if (budgetMax <= 300) return "moderate";
    if (budgetMax <= 500) return "premium";
    return "luxury";
  }

  const t = text.toLowerCase();
  if (/(luxury|designer|high-?end|expensive)/i.test(t)) return "luxury";
  if (/(premium|investment|quality)/i.test(t)) return "premium";
  if (/(moderate|mid-?range|affordable)/i.test(t)) return "moderate";
  if (/(budget|cheap|inexpensive)/i.test(t)) return "budget";
  return undefined;
}

function hashStringToSeed(input: string) {
  let h = 2166136261;
  for (let i = 0; i < input.length; i += 1) {
    h ^= input.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function mulberry32(seed: number) {
  return function rng() {
    let t = (seed += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function formatDollars(value: number) {
  try {
    return value.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
  } catch {
    return `$${Math.round(value)}`;
  }
}

function extractColorKeywords(text: string): string[] {
  const t = text.toLowerCase();
  const keywords = ["black", "white", "navy", "gold", "champagne", "beige", "burgundy", "red", "blue", "green", "olive", "silver", "cream", "camel"];
  return keywords.filter((k) => t.includes(k));
}

function pickFromList<T>(list: T[], rng: () => number) {
  if (list.length === 0) throw new Error("pickFromList on empty list");
  const idx = Math.floor(rng() * list.length);
  return list[idx] ?? list[0];
}

function pickProductForPosition({
  category,
  gender,
  rng,
  preferredColorKeywords,
}: {
  category: "tops" | "bottoms" | "shoes" | "accessories" | "bags" | "outerwear" | "dresses";
  gender: "men" | "women" | "unisex";
  rng: () => number;
  preferredColorKeywords: string[];
}): Product {
  const candidates = getProductsByCategory(category as any).filter(
    (p) => p.gender === "unisex" || p.gender === gender
  );

  if (preferredColorKeywords.length > 0) {
    const byColor = candidates.filter((p) =>
      (p.colors || []).some((c) => preferredColorKeywords.some((k) => c.toLowerCase().includes(k)))
    );
    if (byColor.length > 0) {
      return pickFromList(byColor, rng);
    }
  }

  return pickFromList(candidates.length > 0 ? candidates : getProductsByCategory(category as any), rng);
}

function deriveStyleExplanation({
  top,
  bottom,
  shoes,
  accessory,
  promptText,
}: {
  top: Product;
  bottom: Product;
  shoes: Product;
  accessory: Product;
  promptText: string;
}) {
  const topColor = top.colors?.[0] ?? "";
  const bottomColor = bottom.colors?.[0] ?? "";
  const shoesColor = shoes.colors?.[0] ?? "";
  const accessoryColor = accessory.colors?.[0] ?? "";
  const keywords = extractColorKeywords(promptText);

  const mentions = (s: string) => s && keywords.some((k) => s.toLowerCase().includes(k));
  const contrastPair = (a: string, b: string) => {
    const aa = a.toLowerCase();
    const bb = b.toLowerCase();
    const hasBlackWhite = (aa.includes("black") && bb.includes("white")) || (aa.includes("white") && bb.includes("black"));
    const hasNavyBlack = (aa.includes("navy") && bb.includes("black")) || (aa.includes("black") && bb.includes("navy"));
    return hasBlackWhite || hasNavyBlack;
  };

  if (topColor && bottomColor) {
    if (contrastPair(topColor, bottomColor)) {
      return `This works because of color harmony: ${topColor} contrast against ${bottomColor} creates confidence and clean visual focus.`;
    }
    if (mentions(topColor) && mentions(bottomColor)) {
      return `This works because of color harmony: your requested palette (${topColor} + ${bottomColor}) stays cohesive, while ${accessoryColor || "the accent"} adds a polished finishing note.`;
    }
  }

  return `This works because of color harmony: a balanced foundation with ${shoesColor || "cohesive footwear"} grounding the look, then ${accessoryColor || "a refined accent"} elevating it.`;
}

function computeRemaining(priceEstimate: number, budgetMax: number | null) {
  if (budgetMax == null) return null;
  return budgetMax - priceEstimate;
}

function buildOutfitFromSeed({
  id,
  name,
  styleScore,
  confidence,
  budgetMax,
  promptText,
  gender,
  rngSeed,
}: {
  id: string;
  name: string;
  styleScore: number;
  confidence: number;
  budgetMax: number | null;
  promptText: string;
  gender: "men" | "women" | "unisex";
  rngSeed: number;
}): OutfitBuild {
  const rng = mulberry32(rngSeed);
  const preferredColorKeywords = extractColorKeywords(promptText);

  // Prompt-aware category swaps (lightweight)
  const wantsDress = promptText.toLowerCase().includes("dress");
  const wantsOuterwear = promptText.toLowerCase().includes("coat") || promptText.toLowerCase().includes("jacket") || promptText.toLowerCase().includes("blazer");

  const topCategory = wantsOuterwear ? "outerwear" : "tops";
  const bottomCategory = wantsDress ? "dresses" : "bottoms";
  const shoesCategory: "shoes" = "shoes";
  const accessoryCategory: "accessories" | "bags" = promptText.toLowerCase().includes("bag") ? "bags" : "accessories";

  const topProduct = pickProductForPosition({
    category: topCategory as any,
    gender,
    rng,
    preferredColorKeywords,
  });
  const bottomProduct = pickProductForPosition({
    category: bottomCategory as any,
    gender,
    rng,
    preferredColorKeywords,
  });
  const shoesProduct = pickProductForPosition({
    category: shoesCategory as any,
    gender,
    rng,
    preferredColorKeywords,
  });
  const accessoryProduct = pickProductForPosition({
    category: accessoryCategory as any,
    gender,
    rng,
    preferredColorKeywords,
  });

  const priceEstimate = (topProduct.price || 0) + (bottomProduct.price || 0) + (shoesProduct.price || 0) + (accessoryProduct.price || 0);
  const remaining = computeRemaining(priceEstimate, budgetMax);

  const image = topProduct.images?.[0] || bottomProduct.images?.[0] || shoesProduct.images?.[0] || accessoryProduct.images?.[0] || "";

  const styleExplanation = deriveStyleExplanation({
    top: topProduct,
    bottom: bottomProduct,
    shoes: shoesProduct,
    accessory: accessoryProduct,
    promptText,
  });

  return {
    id,
    name,
    confidence,
    styleScore,
    image,
    priceEstimate,
    budgetMax,
    remaining,
    styleExplanation,
    items: {
      top: { position: "top", product: topProduct },
      bottom: { position: "bottom", product: bottomProduct },
      shoes: { position: "shoes", product: shoesProduct },
      accessory: { position: "accessory", product: accessoryProduct },
    },
  };
}

function buildLocalOutfits({
  promptText,
  budgetMax,
  gender,
}: {
  promptText: string;
  budgetMax: number | null;
  gender: "men" | "women" | "unisex";
}): OutfitBuild[] {
  const base = featuredOutfits ?? [];
  const seed = hashStringToSeed(`${promptText}::${budgetMax ?? "none"}::${gender}`);
  const rng = mulberry32(seed);

  const templates = [
    base[0] as any,
    base[1] as any,
    base[2] as any,
    base[3] as any,
  ];

  return templates.map((t, idx) =>
    buildOutfitFromSeed({
      id: `local-${seed}-${idx}`,
      name: t?.name || ["Velvet Confidence", "City Elegance", "Soft Power", "Gala Glow"][idx]!,
      styleScore: Number(t?.styleScore ?? Math.round(86 + rng() * 10)),
      confidence: Number(Math.round(82 + rng() * 15)),
      budgetMax,
      promptText,
      gender,
      rngSeed: Math.floor(seed + rng() * 1_000_000 + idx * 999),
    })
  );
}

export function AIExperience({
  prefillNonce,
  prefillPrompt,
}: {
  prefillNonce: number;
  prefillPrompt: string | null;
}) {
  const { selectedGender } = useGender();
  const router = useRouter();

  const chips = useMemo(
    () => [
      "I need an outfit for a wedding under $150",
      "Build me a work look that feels premium",
      "Make this outfit party-ready—bold but flattering",
      "I want modern, minimal, and confident styling",
    ],
    []
  );

  const welcomeMessage: ChatMessage = useMemo(
    () => ({
      id: "welcome",
      role: "assistant",
      content:
        "Hi—I'm your CONFIT AI Stylist. Tell me your occasion, vibe, and budget. I’ll generate outfit builds you can try, edit, and trust.",
    }),
    []
  );

  const [messages, setMessages] = useState<ChatMessage[]>([welcomeMessage]);
  const [inputValue, setInputValue] = useState("");
  const [isThinking, setIsThinking] = useState(false);
  const [latestOutfits, setLatestOutfits] = useState<OutfitBuild[]>([]);
  const [budgetMax, setBudgetMax] = useState<number | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);

  const assistantIdRef = useRef<string | null>(null);
  const latestGenerationToken = useRef(0);
  const fallbackTimerRef = useRef<number | null>(null);

  const [tryOnOpen, setTryOnOpen] = useState(false);
  const [tryOnOutfit, setTryOnOutfit] = useState<OutfitBuild | null>(null);
  const [tryOnFocus, setTryOnFocus] = useState<OutfitItemPosition | null>(null);

  const [replaceOpen, setReplaceOpen] = useState(false);
  const [replaceOutfit, setReplaceOutfit] = useState<OutfitBuild | null>(null);
  const [replacePosition, setReplacePosition] = useState<OutfitItemPosition>("accessory");
  const [replacePrompt, setReplacePrompt] = useState("");

  const openTryOn = useCallback((outfitId: string, focus?: OutfitItemPosition | null) => {
    const outfit = latestOutfits.find((o) => o.id === outfitId) || null;
    setTryOnOutfit(outfit);
    setTryOnFocus(focus ?? null);
    setTryOnOpen(true);
  }, [latestOutfits]);

  const openReplace = useCallback((outfitId: string, position: OutfitItemPosition) => {
    const outfit = latestOutfits.find((o) => o.id === outfitId) || null;
    if (!outfit) return;
    setReplaceOutfit(outfit);
    setReplacePosition(position);
    setReplacePrompt(`Replace my ${position} in a way that keeps the same confidence, but feels even more “me”.`);
    setReplaceOpen(true);
  }, [latestOutfits]);

  const rebuildOutfitsFromPrompt = useCallback(
    (promptText: string, budget: number | null, gender: "men" | "women" | "unisex") => {
      const next = buildLocalOutfits({
        promptText,
        budgetMax: budget,
        gender,
      });
      setLatestOutfits(next);
      return next;
    },
    []
  );

  const updateAssistantMessage = useCallback((assistantId: string, content: string) => {
    setMessages((prev) => prev.map((m) => (m.id === assistantId ? { ...m, content } : m)));
  }, []);

  const handleSend = useCallback(
    async (text: string) => {
      const promptText = text.trim();
      if (!promptText) return;

      latestGenerationToken.current += 1;
      const token = latestGenerationToken.current;

      // Budget tracking (live)
      const parsedBudgetMax = parseBudgetMax(promptText);
      setBudgetMax(parsedBudgetMax);

      const occasionHint = parseOccasionHint(promptText);
      const stylePreferenceHint = parseStyleHint(promptText);
      const budgetLevelHint = parseBudgetLevelHint(parsedBudgetMax, promptText);

      setIsThinking(true);
      setLatestOutfits([]);
      setInputValue("");

      const userMsg: ChatMessage = {
        id: `user-${Date.now()}-${Math.random().toString(16).slice(2)}`,
        role: "user",
        content: promptText,
      };

      const assistantId = `assistant-${Date.now()}-${Math.random().toString(16).slice(2)}`;
      assistantIdRef.current = assistantId;

      const assistantPlaceholder: ChatMessage = {
        id: assistantId,
        role: "assistant",
        content: "Thinking… Let me build something you can wear with confidence.",
      };

      setMessages((prev) => [...prev, userMsg, assistantPlaceholder]);

      // Fallback after ~1.4s so the user never waits too long.
      if (fallbackTimerRef.current) window.clearTimeout(fallbackTimerRef.current);
      fallbackTimerRef.current = window.setTimeout(() => {
        if (latestGenerationToken.current !== token) return;

        const next = rebuildOutfitsFromPrompt(promptText, parsedBudgetMax, selectedGender);
        updateAssistantMessage(
          assistantId,
          `I built 4 premium outfit builds for “${promptText.slice(0, 64)}”. This works because of color harmony—tap Try On when you want the fit.`
        );
        setIsThinking(false);
      }, 1400);

      try {
        const controller = new AbortController();
        const res = await fetch(apiUrl("/api/stylist/chat"), {
          method: "POST",
          headers: { "Content-Type": "application/json", Accept: "application/json" },
          body: JSON.stringify({
            message: promptText,
            session_id: sessionId ?? undefined,
            occasion: occasionHint ?? undefined,
            budget: budgetLevelHint ?? undefined,
            style_preference: stylePreferenceHint ?? undefined,
            gender: selectedGender,
          }),
          signal: controller.signal,
        });

        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = (await res.json()) as {
          content?: string;
          outfitSuggestions?: Array<{ id: string; name: string; price: number; styleScore: number; image: string }>;
          sessionId?: string;
        };

        if (latestGenerationToken.current !== token) return;

        if (data?.sessionId) setSessionId(data.sessionId);

        const suggested = data?.outfitSuggestions?.length ? data.outfitSuggestions : null;
        const localFallback = suggested
          ? suggested.map((s, idx) =>
              buildOutfitFromSeed({
                id: s.id ?? `api-${token}-${idx}`,
                name: s.name ?? `CONFIT Look ${idx + 1}`,
                styleScore: Number(s.styleScore ?? 88),
                confidence: Number(Math.round(82 + idx * 2)),
                budgetMax: parsedBudgetMax,
                promptText,
                gender: selectedGender,
                rngSeed: hashStringToSeed(`${s.id ?? idx}-${promptText}-${selectedGender}`),
              })
            )
          : buildLocalOutfits({
              promptText,
              budgetMax: parsedBudgetMax,
              gender: selectedGender,
            });

        setLatestOutfits(localFallback);
        const content = data?.content
          ? data.content
          : `I refined your build with confidence cues. This works because of color harmony—tap Replace items if you want it sharper.`;

        updateAssistantMessage(assistantId, content);
        setIsThinking(false);
      } catch {
        // Keep fallback result; no-op.
        if (latestGenerationToken.current === token) {
          updateAssistantMessage(
            assistantId,
            "I couldn’t reach the server, but I still assembled a premium, budget-aware set of looks. Try On and adjust—confidence stays intact."
          );
        }
      } finally {
        if (latestGenerationToken.current === token) setIsThinking(false);
      }
    },
    [rebuildOutfitsFromPrompt, selectedGender, updateAssistantMessage, sessionId]
  );

  useEffect(() => {
    return () => {
      if (fallbackTimerRef.current) window.clearTimeout(fallbackTimerRef.current);
    };
  }, []);

  // Prefill prompt from homepage interactions
  const appliedPrefillNonce = useRef<number>(0);
  useEffect(() => {
    if (!prefillPrompt) return;
    if (prefillNonce <= 0) return;
    if (appliedPrefillNonce.current === prefillNonce) return;
    appliedPrefillNonce.current = prefillNonce;

    void handleSend(prefillPrompt);
  }, [handleSend, prefillNonce, prefillPrompt]);

  // Live AI demo (autoplay)
  const demoPrompt = "I need an outfit for a wedding under $150";
  const demoBudget = parseBudgetMax(demoPrompt);
  const [demoPlaying, setDemoPlaying] = useState(true);
  const [demoPhase, setDemoPhase] = useState<0 | 1 | 2>(0);
  const demoOutfits = useMemo(
    () =>
      buildLocalOutfits({
        promptText: demoPrompt,
        budgetMax: demoBudget,
        gender: selectedGender,
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [selectedGender]
  );

  useEffect(() => {
    if (!demoPlaying) return;

    const t0 = window.setTimeout(() => setDemoPhase(0), 0);
    const cycle = window.setInterval(() => {
      setDemoPhase(1);
      window.setTimeout(() => setDemoPhase(2), 900);
      window.setTimeout(() => setDemoPhase(0), 2600);
    }, 3600);

    return () => {
      window.clearTimeout(t0);
      window.clearInterval(cycle);
    };
  }, [demoPlaying]);

  const handleReplaceApply = useCallback(() => {
    if (!replaceOutfit) return;
    const nextPrompt = replacePrompt.trim();

    const position = replacePosition;
    const currentItems = replaceOutfit.items;

    // Replace algorithm: pick a new product in the same category, keep budget-awareness.
    const rngSeed = hashStringToSeed(`${replaceOutfit.id}-${position}-${nextPrompt}-${Date.now()}`);
    const rng = mulberry32(rngSeed);
    const gender = selectedGender;
    const preferredColorKeywords = extractColorKeywords(nextPrompt || replaceOutfit.name);

    const categoryMap: Record<OutfitItemPosition, "tops" | "bottoms" | "shoes" | "accessories" | "bags" | "outerwear" | "dresses"> = {
      top: "tops",
      bottom: "bottoms",
      shoes: "shoes",
      accessory: "accessories",
    };

    const category = categoryMap[position];
    const nextProduct = pickProductForPosition({
      category,
      gender,
      rng,
      preferredColorKeywords,
    });

    const updated: OutfitBuild = {
      ...replaceOutfit,
      items: {
        ...replaceOutfit.items,
        [position]: { position, product: nextProduct },
      },
    };

    const nextPrice =
      updated.items.top.product.price +
      updated.items.bottom.product.price +
      updated.items.shoes.product.price +
      updated.items.accessory.product.price;

    const remaining = computeRemaining(nextPrice, updated.budgetMax ?? null);
    const image = updated.items.top.product.images?.[0] || updated.image;

    updated.priceEstimate = nextPrice;
    updated.remaining = remaining;
    updated.image = image;
    updated.styleExplanation = deriveStyleExplanation({
      top: updated.items.top.product,
      bottom: updated.items.bottom.product,
      shoes: updated.items.shoes.product,
      accessory: updated.items.accessory.product,
      promptText: replacePrompt || updated.name,
    });

    setLatestOutfits((prev) => prev.map((o) => (o.id === updated.id ? updated : o)));
    setReplaceOpen(false);

    const assistantId = `assistant-replace-${Date.now()}`;
    setMessages((prev) => [
      ...prev,
      {
        id: assistantId,
        role: "assistant",
        content:
          `Done. I replaced your ${position} to sharpen the silhouette while keeping the same confidence cues. Want a tighter budget or more contrast?`,
      },
    ]);
  }, [replaceOutfit, replacePosition, replacePrompt, selectedGender]);

  const selectedTryOnImage = useMemo(() => {
    if (!tryOnOutfit) return null;
    if (tryOnFocus) {
      const p = tryOnOutfit.items[tryOnFocus]?.product;
      return p?.images?.[0] ?? tryOnOutfit.image;
    }
    return tryOnOutfit.image;
  }, [tryOnFocus, tryOnOutfit]);

  const viewProduct = useCallback(
    (productId: string) => {
      setTryOnOpen(false);
      router.push(`/product/${productId}`);
    },
    [router]
  );

  return (
    <section className="py-14 md:py-20 bg-background">
      <div className="container px-4 md:px-6">
        <div className="flex flex-col lg:flex-row items-start lg:items-stretch gap-6 md:gap-10">
          {/* Live AI demo */}
          <motion.div
            className="lg:w-[420px] w-full"
            initial={{ opacity: 0, y: 18 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.25 }}
            transition={{ duration: 0.45, ease: "easeInOut" }}
          >
            <div className="mb-6">
              <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-card/20 backdrop-blur-md px-4 py-2 text-sm font-medium text-foreground">
                <Wand2 className="h-4 w-4 text-accent" />
                <span>Live AI Demo</span>
                <span className="text-muted-foreground">·</span>
                <span className="text-muted-foreground">Prompt → Outfit</span>
              </div>
              <h2 className="mt-4 heading-section">Watch confidence assemble</h2>
              <p className="mt-3 text-body text-muted-foreground">
                Every output is budget-aware and grounded in style logic you can understand.
              </p>
            </div>

            <div className="glass-panel rounded-3xl border-white/10 overflow-hidden">
              <div className="p-4 border-b border-white/10 bg-card/10 flex items-center justify-between gap-3">
                <Badge variant="outline" className="border-white/10 bg-card/20">
                  {demoPhase === 0 ? "Prompt" : demoPhase === 1 ? "Thinking" : "Transformation"}
                </Badge>
                <Button
                  variant="ghost"
                  size="sm"
                  className="rounded-full hover:bg-white/5"
                  onClick={() => setDemoPlaying((v) => !v)}
                >
                  {demoPlaying ? <Pause className="h-4 w-4 mr-2" /> : <Play className="h-4 w-4 mr-2" />}
                  {demoPlaying ? "Pause" : "Play"}
                </Button>
              </div>

              <div className="p-4 space-y-4">
                <AnimatePresence mode="wait">
                  {demoPhase === 0 && (
                    <motion.div
                      key="demo-prompt"
                      initial={{ opacity: 0, y: 10, filter: "blur(8px)" }}
                      animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                      exit={{ opacity: 0, y: -10 }}
                      transition={{ duration: 0.35, ease: "easeInOut" }}
                    >
                      <div className="rounded-2xl border border-white/10 bg-background/30 p-4">
                        <p className="text-xs font-semibold text-muted-foreground">Your prompt</p>
                        <p className="mt-2 text-sm text-foreground font-semibold leading-relaxed">
                          {demoPrompt}
                        </p>
                        {demoBudget != null && (
                          <p className="mt-2 text-xs text-muted-foreground">
                            Budget max: <span className="text-foreground font-semibold">{formatDollars(demoBudget)}</span>
                          </p>
                        )}
                      </div>
                    </motion.div>
                  )}

                  {demoPhase === 1 && (
                    <motion.div
                      key="demo-thinking"
                      initial={{ opacity: 0, y: 10, filter: "blur(8px)" }}
                      animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                      exit={{ opacity: 0, y: -10 }}
                      transition={{ duration: 0.35, ease: "easeInOut" }}
                    >
                      <div className="rounded-2xl border border-white/10 bg-card/20 p-4">
                        <div className="flex items-center gap-2 text-sm font-semibold">
                          <Sparkles className="h-4 w-4 text-accent" />
                          Thinking with style logic
                        </div>
                        <div className="mt-4 space-y-3">
                          <div className="h-3 w-full rounded-full bg-white/10 overflow-hidden">
                            <div className="h-full w-full animate-shimmer bg-[linear-gradient(90deg,transparent,rgba(255,255,255,0.25),transparent)]" />
                          </div>
                          <div className="h-3 w-5/6 rounded-full bg-white/10 overflow-hidden">
                            <div className="h-full w-full animate-shimmer bg-[linear-gradient(90deg,transparent,rgba(255,255,255,0.25),transparent)]" />
                          </div>
                          <div className="h-3 w-3/5 rounded-full bg-white/10 overflow-hidden">
                            <div className="h-full w-full animate-shimmer bg-[linear-gradient(90deg,transparent,rgba(255,255,255,0.25),transparent)]" />
                          </div>
                        </div>
                        <p className="mt-4 text-xs text-muted-foreground">
                          Checking budget, harmonizing colors, and assembling confident pieces.
                        </p>
                      </div>
                    </motion.div>
                  )}

                  {demoPhase === 2 && (
                    <motion.div
                      key="demo-transform"
                      initial={{ opacity: 0, y: 10, filter: "blur(10px)" }}
                      animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                      exit={{ opacity: 0, y: -10 }}
                      transition={{ duration: 0.45, ease: "easeInOut" }}
                    >
                      <div className="space-y-3">
                        <div className="flex items-center justify-between gap-3">
                          <p className="text-xs font-semibold text-muted-foreground">Transformation</p>
                          <Badge variant="outline" className="border-white/10 bg-card/20">
                            Ready to Try On
                          </Badge>
                        </div>
                        <div className="space-y-3">
                          {demoOutfits.slice(0, 1).map((o) => (
                            <div key={o.id} className="rounded-2xl overflow-hidden border border-white/10 bg-card/10">
                              <div className="aspect-[16/10]">
                                <img src={o.image} alt={o.name} className="w-full h-full object-cover" loading="lazy" />
                              </div>
                              <div className="p-4">
                                <p className="text-sm font-semibold">{o.name}</p>
                                <p className="mt-1 text-xs text-muted-foreground">
                                  {o.styleScore}% match · {formatDollars(o.priceEstimate)}
                                </p>
                                <p className="mt-2 text-xs text-muted-foreground">
                                  {o.styleExplanation}
                                </p>
                              </div>
                            </div>
                          ))}
                        </div>
                        <Button
                          className="w-full rounded-full bg-gradient-to-r from-violet-500 to-blue-500 text-white hover:from-violet-400 hover:to-blue-400 h-11"
                          onClick={() => handleSend(demoPrompt)}
                        >
                          Try this build
                          <ArrowRight className="ml-2 h-5 w-5" />
                        </Button>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>
          </motion.div>

          {/* Chat + outputs */}
          <div className="flex-1 w-full">
            <ChatUI
              messages={messages}
              isThinking={isThinking}
              inputValue={inputValue}
              onChangeInput={setInputValue}
              onSend={(v) => void handleSend(v)}
              onPickChip={(chip) => void handleSend(chip)}
              chips={chips}
              latestOutfits={latestOutfits}
              onTryOn={(outfitId, focus) => openTryOn(outfitId, focus ?? undefined)}
              onReplaceItem={(outfitId, position) => openReplace(outfitId, position)}
              onViewProduct={viewProduct}
              budgetMax={budgetMax}
            />

            <div className="mt-5 md:mt-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-2xl glass-panel border border-white/10 flex items-center justify-center animate-glow-pulse">
                  <Camera className="h-5 w-5 text-accent" />
                </div>
                <div>
                  <p className="text-sm font-semibold tracking-tight">Try on, then refine</p>
                  <p className="mt-1 text-xs text-muted-foreground">Replace items without losing the vibe.</p>
                </div>
              </div>

              <div className="flex gap-2">
                <Button
                  variant="outline"
                  className="rounded-full border-white/10 bg-card/20 hover:bg-card/30"
                  onClick={() => {
                    setMessages([welcomeMessage]);
                    setLatestOutfits([]);
                    setInputValue("");
                    setBudgetMax(null);
                    setIsThinking(false);
                  }}
                >
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Reset
                </Button>
                <Button
                  className="rounded-full bg-gradient-to-r from-violet-500 to-blue-500 text-white hover:from-violet-400 hover:to-blue-400 shadow-lg h-10"
                  onClick={() => handleSend("I need an outfit for a wedding under $150")}
                >
                  Build a look
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
        </div>

        {/* Replace Modal */}
        <Dialog open={replaceOpen} onOpenChange={setReplaceOpen}>
          <DialogContent className="max-w-2xl rounded-3xl border-white/10 bg-background">
            <DialogHeader>
              <DialogTitle className="font-display">Replace your {replacePosition}</DialogTitle>
              <DialogDescription>
                Give the stylist clear instructions. We’ll keep the confidence and harmonize the result.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-3">
              <div className="rounded-2xl border border-border/60 bg-card/20 p-4">
                <p className="text-xs font-semibold text-muted-foreground">Current build</p>
                <p className="mt-2 text-sm font-semibold">{replaceOutfit?.name ?? ""}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Estimated total:{" "}
                  <span className="text-foreground font-semibold">
                    {replaceOutfit ? formatDollars(replaceOutfit.priceEstimate) : ""}
                  </span>
                </p>
              </div>

              <Textarea
                value={replacePrompt}
                onChange={(e) => setReplacePrompt(e.target.value)}
                className="min-h-[140px] rounded-2xl border-white/10 bg-card/20 focus-visible:ring-accent/40"
              />

              <div className="text-xs text-muted-foreground">
                Example: “Replace shoes with something more elevated in a darker tone, keep it wedding-ready.”
              </div>
            </div>

            <DialogFooter className="gap-2 sm:gap-0">
              <Button variant="outline" className="rounded-full border-border/70" onClick={() => setReplaceOpen(false)}>
                Cancel
              </Button>
              <Button
                className="rounded-full bg-gradient-to-r from-violet-500 to-blue-500 text-white hover:from-violet-400 hover:to-blue-400"
                onClick={handleReplaceApply}
                disabled={!replacePrompt.trim()}
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Replace item
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Try On Modal */}
        <Dialog open={tryOnOpen} onOpenChange={setTryOnOpen}>
          <DialogContent className="max-w-3xl rounded-3xl border-white/10 bg-background">
            <DialogHeader>
              <DialogTitle className="font-display">Try On Preview</DialogTitle>
              <DialogDescription>
                {tryOnOutfit ? (
                  <>
                    {tryOnFocus ? (
                      <>
                        Previewing your <span className="font-semibold">{tryOnFocus}</span> within{" "}
                        <span className="font-semibold">{tryOnOutfit.name}</span>.
                      </>
                    ) : (
                      <>Previewing <span className="font-semibold">{tryOnOutfit.name}</span>.</>
                    )}
                  </>
                ) : (
                  "Preview your look."
                )}
              </DialogDescription>
            </DialogHeader>

            <div className="rounded-2xl overflow-hidden border border-border/60 bg-card/20">
              <div className="aspect-[16/10]">
                {selectedTryOnImage ? (
                  <img src={selectedTryOnImage} alt="Try on preview" className="w-full h-full object-cover" loading="lazy" />
                ) : null}
              </div>
            </div>

            <DialogFooter className="gap-2 sm:gap-0">
              <Button variant="outline" className="rounded-full border-border/70" onClick={() => setTryOnOpen(false)}>
                Close
              </Button>
              <Button
                className="rounded-full bg-gradient-to-r from-violet-500 to-blue-500 text-white hover:from-violet-400 hover:to-blue-400"
                onClick={() => {
                  setTryOnOpen(false);
                  router.push("/try-on");
                }}
              >
                <Camera className="h-4 w-4 mr-2" />
                Open Try-On Studio
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </section>
  );
}

