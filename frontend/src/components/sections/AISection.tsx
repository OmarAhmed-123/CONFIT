import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from "framer-motion";
import {
  Bot,
  User,
  Send,
  Sparkles,
  Mic,
  MicOff,
  RefreshCw,
  Eye,
  Edit3,
  ArrowLeftRight,
  Loader2,
} from "lucide-react";
import { createTransition } from "@/motion";
import { useGender } from "@/context/GenderContext";
import { apiUrl } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import type { OutfitSuggestion } from "@/types";
import { featuredOutfits } from "@/services/mockData";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

type StyleTip = { title: string; description: string };

type ChatResponse = {
  content: string;
  sessionId?: string | null;
  outfitSuggestions?: OutfitSuggestion[];
  styleTips?: StyleTip[];
};

function TypingDots() {
  return (
    <div className="flex items-center gap-1">
      {[0, 1, 2].map((i) => (
        <motion.span
          // eslint-disable-next-line react/no-array-index-key
          key={i}
          className="w-2 h-2 rounded-full bg-accent/80"
          initial={{ opacity: 0.6, y: 0 }}
          animate={{ opacity: [0.4, 1, 0.55], y: [0, -4, 0] }}
          transition={{ duration: 0.6, delay: i * 0.12, repeat: Infinity, ease: "easeInOut" }}
        />
      ))}
    </div>
  );
}

function buildFallbackOutfits(): OutfitSuggestion[] {
  const base = featuredOutfits ?? [];
  const heroImages = [
    "https://images.unsplash.com/photo-1520975916090-3105956dac38?w=900&h=1125&fit=crop&q=80",
    "https://images.unsplash.com/photo-1483985988355-763728e1935b?w=900&h=1125&fit=crop&q=80",
    "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=900&h=1125&fit=crop&q=80",
    "https://images.unsplash.com/photo-1539008835657-9e8e9680c956?w=900&h=1125&fit=crop&q=80",
    "https://images.unsplash.com/photo-1550614000-4b9519879354?w=900&h=1125&fit=crop&q=80",
  ];

  const fallback: OutfitSuggestion[] = [];
  for (let i = 0; i < 4; i += 1) {
    const f = base[i] as any;
    fallback.push({
      id: `fallback-outfit-${i}`,
      name: f?.name || ["Velvet Confidence", "Modern Gala", "Soft Power", "City Elegance"][i]!,
      price: Number(f?.totalPrice ?? 220 + i * 90),
      styleScore: Number(f?.styleScore ?? 86 + i * 2),
      image: heroImages[i % heroImages.length]!,
    });
  }

  return fallback;
}

function formatDollars(value: number) {
  try {
    return value.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
  } catch {
    return `$${Math.round(value)}`;
  }
}

export function AISection({
  prefillNonce,
  prefillPrompt,
}: {
  prefillNonce: number;
  prefillPrompt: string | null;
}) {
  const { selectedGender } = useGender();
  const router = useRouter();

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "Hi—I'm your CONFIT AI Stylist. Tell me your occasion, vibe, and budget. I'll build options you can feel confident about.",
    },
  ]);

  const [inputValue, setInputValue] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);

  const [latestOutfits, setLatestOutfits] = useState<OutfitSuggestion[]>([]);
  const [latestStyleTips, setLatestStyleTips] = useState<StyleTip[]>([]);

  const [tryOnOpen, setTryOnOpen] = useState(false);
  const [tryOnOutfit, setTryOnOutfit] = useState<OutfitSuggestion | null>(null);

  const [editOpen, setEditOpen] = useState(false);
  const [editOutfit, setEditOutfit] = useState<OutfitSuggestion | null>(null);
  const [editPrompt, setEditPrompt] = useState("");

  const [replaceOpen, setReplaceOpen] = useState(false);
  const [replaceOutfit, setReplaceOutfit] = useState<OutfitSuggestion | null>(null);
  const [replacePrompt, setReplacePrompt] = useState("");

  const chatEndRef = useRef<HTMLDivElement | null>(null);
  const lastAppliedPrefillNonce = useRef<number>(0);

  const promptChips = useMemo(
    () => [
      "I need an outfit for a wedding under $150",
      "Build a work look that feels confident and comfortable",
      "Make this outfit party-ready—bold but flattering",
      "Find my style: modern, minimal, and premium",
    ],
    []
  );

  const canSend = useMemo(() => inputValue.trim().length > 0 && !isGenerating, [inputValue, isGenerating]);

  const scrollToEnd = useCallback(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, []);

  useEffect(() => {
    scrollToEnd();
  }, [messages, isGenerating, scrollToEnd]);

  const openTryOn = useCallback((outfit: OutfitSuggestion) => {
    setTryOnOutfit(outfit);
    setTryOnOpen(true);
  }, []);

  const openEdit = useCallback((outfit: OutfitSuggestion) => {
    setEditOutfit(outfit);
    setEditPrompt(`Keep the essence of "${outfit.name}", but refine this outfit by:`);
    setEditOpen(true);
  }, []);

  const openReplace = useCallback((outfit: OutfitSuggestion) => {
    setReplaceOutfit(outfit);
    setReplacePrompt(`Replace items in "${outfit.name}" with:`);
    setReplaceOpen(true);
  }, []);

  const generateWithApi = useCallback(
    async (messageText: string) => {
      setIsGenerating(true);
      setLatestOutfits([]);
      setLatestStyleTips([]);

      const userMessage: Message = {
        id: `user-${Date.now()}`,
        role: "user",
        content: messageText.trim(),
      };
      setMessages((prev) => [...prev, userMessage]);

      try {
        const res = await fetch(apiUrl("/api/stylist/chat"), {
          method: "POST",
          headers: { "Content-Type": "application/json", Accept: "application/json" },
          body: JSON.stringify({
            message: messageText.trim(),
            session_id: sessionId,
            gender: selectedGender,
          }),
        });

        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }

        const data = (await res.json()) as ChatResponse;
        const assistantMessage: Message = {
          id: `assistant-${Date.now()}`,
          role: "assistant",
          content: data?.content || "I built you a confident set of looks—tap Try On to see the fit.",
        };

        setSessionId(data?.sessionId ?? sessionId);
        setMessages((prev) => [...prev, assistantMessage]);
        setLatestOutfits(data?.outfitSuggestions?.length ? data.outfitSuggestions : buildFallbackOutfits());
        setLatestStyleTips(data?.styleTips?.length ? (data.styleTips as StyleTip[]) : []);
      } catch {
        const assistantMessage: Message = {
          id: `assistant-${Date.now()}`,
          role: "assistant",
          content:
            "Stylist mode: I couldn't reach the server right now, but I still assembled a premium set of outfits for your prompt. Try again when you can—I'll refine the suggestions.",
        };

        setMessages((prev) => [...prev, assistantMessage]);
        setLatestOutfits(buildFallbackOutfits());
        setLatestStyleTips([
          { title: "Confidence fit", description: "Choose one statement piece and keep the silhouette clean." },
          { title: "Occasion-aware", description: "Your look adapts to the moment—daylight, lighting, and vibe." },
        ]);
      } finally {
        setIsGenerating(false);
      }
    },
    [sessionId, selectedGender]
  );

  const sendMessage = useCallback(async () => {
    if (!canSend) return;
    const text = inputValue;
    setInputValue("");
    await generateWithApi(text);
  }, [canSend, generateWithApi, inputValue]);

  useEffect(() => {
    if (!prefillPrompt) return;
    if (prefillNonce <= 0) return;
    if (lastAppliedPrefillNonce.current === prefillNonce) return;
    lastAppliedPrefillNonce.current = prefillNonce;

    // Generate immediately for minimal friction.
    void generateWithApi(prefillPrompt);
  }, [generateWithApi, prefillNonce, prefillPrompt]);

  // Voice input (best-effort) — gracefully degrades if unsupported.
  const [voiceOn, setVoiceOn] = useState(false);
  const recognitionRef = useRef<any>(null);

  const startVoice = useCallback(() => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    const recognition = new SpeechRecognition();
    recognitionRef.current = recognition;
    recognition.lang = "en-US";
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    setVoiceOn(true);

    recognition.onresult = (event: any) => {
      const transcript = Array.from(event.results)
        .map((r: any) => r[0]?.transcript)
        .join(" ");
      setInputValue(transcript.trim());
    };

    recognition.onerror = () => {
      setVoiceOn(false);
    };

    recognition.onend = () => {
      setVoiceOn(false);
    };

    recognition.start();
  }, []);

  const stopVoice = useCallback(() => {
    try {
      recognitionRef.current?.stop?.();
    } catch {
      // ignore
    } finally {
      setVoiceOn(false);
    }
  }, []);

  const stage = useMemo(() => {
    if (isGenerating) return 2;
    if (latestOutfits.length > 0) return 3;
    return 1;
  }, [isGenerating, latestOutfits.length]);

  return (
    <section id="confit-ai-experience" className="py-14 md:py-20 bg-background">
      <div className="container px-4 md:px-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 md:gap-10 items-start">
          {/* Left: Conversational UI */}
          <div>
            <motion.div
              initial={{ opacity: 0, y: 18 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.25 }}
              transition={createTransition({ duration: 0.35 })}
              className="mb-6"
            >
              <div className="flex items-center justify-between gap-4">
                <div>
                  <div className="inline-flex items-center gap-2 rounded-full border border-border/60 bg-card/20 backdrop-blur-md px-4 py-2 text-sm font-medium">
                    <Sparkles className="h-4 w-4 text-accent" />
                    <span>AI Experience</span>
                    <span className="text-muted-foreground">·</span>
                    <span className="text-muted-foreground">Chat + Try-On</span>
                  </div>
                  <h2 className="mt-4 heading-section">Your AI Stylist</h2>
                  <p className="mt-3 text-body text-muted-foreground max-w-xl">
                    Describe your moment. We'll generate outfits, then let you Try On, Edit, or Replace items—until it feels right.
                  </p>
                </div>

                <Button
                  variant="ghost"
                  size="sm"
                  className="hidden md:inline-flex rounded-full"
                  onClick={() => {
                    setMessages([
                      {
                        id: "welcome",
                        role: "assistant",
                        content:
                          "Hi—I'm your CONFIT AI Stylist. Tell me your occasion, vibe, and budget. I'll build options you can feel confident about.",
                      },
                    ]);
                    setLatestOutfits([]);
                    setLatestStyleTips([]);
                    setSessionId(null);
                  }}
                >
                  <RefreshCw className="h-4 w-4" />
                  Reset
                </Button>
              </div>
            </motion.div>

            <Card className="glass-card rounded-3xl border-white/10 overflow-hidden">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between gap-3">
                  <CardTitle className="text-lg font-semibold flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full bg-accent animate-pulse" />
                    CONFIT Stylist
                  </CardTitle>
                  <div className="flex items-center gap-2">
                    {voiceOn ? (
                      <Badge variant="outline" className="border-accent/40 text-accent">
                        Voice On
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="border-border/60 text-muted-foreground">
                        {selectedGender === "women" ? "Women" : "Men"} mode
                      </Badge>
                    )}
                  </div>
                </div>
                <p className="text-sm text-muted-foreground mt-2">
                  Example: <span className="text-foreground font-semibold">“I need an outfit for a wedding under $150”</span>
                </p>
              </CardHeader>

              <CardContent className="p-0">
                <div className="px-4 pb-4 pt-0">
                  {messages.length <= 1 && latestOutfits.length === 0 && (
                    <div className="flex flex-wrap gap-2 pt-1">
                      {promptChips.map((chip) => (
                        <Button
                          key={chip}
                          variant="outline"
                          size="sm"
                          className="rounded-full border-border/70 bg-card/20 hover:bg-card/40"
                          disabled={isGenerating}
                          onClick={() => {
                            setInputValue(chip);
                            void generateWithApi(chip);
                          }}
                        >
                          {chip}
                        </Button>
                      ))}
                    </div>
                  )}
                </div>

                <div className="px-4">
                  <div className="max-h-[360px] overflow-y-auto no-scrollbar pr-2">
                    <div className="space-y-4 py-2">
                      {messages.map((m) => (
                        <motion.div
                          key={m.id}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={createTransition({ duration: 0.3 })}
                          className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
                        >
                          <div
                            className={`flex items-start gap-3 max-w-[90%] ${
                              m.role === "user" ? "flex-row-reverse" : "flex-row"
                            }`}
                          >
                            <div
                              className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                                m.role === "user"
                                  ? "bg-gradient-to-r from-violet-500 to-blue-500 text-white"
                                  : "bg-muted border border-border/50"
                              }`}
                            >
                              {m.role === "user" ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4 text-accent" />}
                            </div>

                            <div
                              className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                                m.role === "user"
                                  ? "bg-white/10 border border-white/10 text-foreground"
                                  : "bg-card/50 border border-border/60 text-foreground"
                              }`}
                            >
                              {m.content}
                            </div>
                          </div>
                        </motion.div>
                      ))}

                      <AnimatePresence>
                        {isGenerating && (
                          <motion.div
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            className="flex justify-start"
                          >
                            <div className="flex items-start gap-3 max-w-[90%]">
                              <div className="w-8 h-8 rounded-full flex items-center justify-center bg-muted border border-border/50">
                                <Bot className="h-4 w-4 text-accent" />
                              </div>
                              <div className="rounded-2xl px-4 py-3 bg-card/50 border border-border/60">
                                <div className="flex items-center gap-2">
                                  <TypingDots />
                                  <span className="text-sm text-muted-foreground font-medium">Stylist is generating your looks…</span>
                                </div>
                              </div>
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>

                      <div ref={chatEndRef} />
                    </div>
                  </div>
                </div>

                {/* Latest outfit suggestions */}
                <div className="px-4 pb-4 pt-2">
                  {latestStyleTips.length > 0 && (
                    <div className="flex flex-wrap gap-2 mb-3">
                      {latestStyleTips.slice(0, 3).map((tip) => (
                        <Badge key={tip.title} variant="outline" className="border-white/10 bg-card/20 text-foreground px-3 py-1 text-xs">
                          <span className="font-semibold">{tip.title}:</span>&nbsp;{tip.description}
                        </Badge>
                      ))}
                    </div>
                  )}

                  {latestOutfits.length > 0 ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-2 gap-3">
                      {latestOutfits.slice(0, 4).map((outfit) => (
                        <motion.div
                          key={outfit.id}
                          initial={{ opacity: 0, y: 14 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={createTransition({ duration: 0.35 })}
                          className="group"
                        >
                          <div className="glass-panel rounded-3xl border-white/10 overflow-hidden">
                            <div className="relative aspect-[3/4] bg-muted">
                              <img
                                src={outfit.image}
                                alt={outfit.name}
                                loading="lazy"
                                decoding="async"
                                className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                              />
                              <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

                              <div className="absolute top-3 left-3">
                                <Badge variant="secondary" className="bg-accent/85 text-accent-foreground border-white/10">
                                  {outfit.styleScore}% match
                                </Badge>
                              </div>

                              <div className="absolute bottom-3 left-3 right-3 opacity-0 group-hover:opacity-100 translate-y-2 group-hover:translate-y-0 transition-all duration-300">
                                <div className="bg-background/80 backdrop-blur-md border border-border/70 rounded-2xl p-3">
                                  <div className="flex items-start justify-between gap-3">
                                    <div>
                                      <p className="text-xs text-muted-foreground">Outfit</p>
                                      <p className="text-sm font-semibold text-foreground leading-tight">{outfit.name}</p>
                                    </div>
                                    <p className="text-sm font-semibold text-foreground whitespace-nowrap">
                                      {formatDollars(outfit.price)}
                                    </p>
                                  </div>
                                  <div className="mt-3 flex gap-2">
                                    <Button
                                      size="sm"
                                      className="flex-1 rounded-full bg-gradient-to-r from-violet-500 to-blue-500 text-white hover:from-violet-400 hover:to-blue-400"
                                      onClick={() => openTryOn(outfit)}
                                    >
                                      <Eye className="mr-2 h-4 w-4" />
                                      Try On
                                    </Button>
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      className="rounded-full border-border/80 bg-card/30 hover:bg-card/50"
                                      onClick={() => openEdit(outfit)}
                                    >
                                      <Edit3 className="h-4 w-4 mr-2" />
                                      Edit
                                    </Button>
                                  </div>
                                  <div className="mt-2">
                                    <Button
                                      size="sm"
                                      variant="ghost"
                                      className="w-full rounded-full text-muted-foreground hover:text-accent hover:bg-accent/10"
                                      onClick={() => openReplace(outfit)}
                                    >
                                      <ArrowLeftRight className="h-4 w-4 mr-2" />
                                      Replace items
                                    </Button>
                                  </div>
                                </div>
                              </div>
                            </div>

                            <div className="p-4">
                              <h3 className="font-semibold tracking-tight">{outfit.name}</h3>
                              <div className="mt-2 flex items-center justify-between gap-3">
                                <p className="text-sm font-semibold">{formatDollars(outfit.price)}</p>
                                <p className="text-xs text-muted-foreground">Tap hover actions</p>
                              </div>
                            </div>
                          </div>
                        </motion.div>
                      ))}
                    </div>
                  ) : (
                    <div className="rounded-3xl border border-border/60 bg-card/20 p-4 text-sm text-muted-foreground">
                      Generate suggestions to see premium outfit cards here.
                    </div>
                  )}
                </div>

                {/* Input */}
                <div className="border-t border-border/60 bg-card/30 px-4 py-4">
                  <div className="flex items-end gap-3">
                    <div className="flex-1 relative">
                      <Textarea
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        placeholder="Describe your outfit… occasion, vibe, budget"
                        disabled={isGenerating}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" && !e.shiftKey) {
                            e.preventDefault();
                            void sendMessage();
                          }
                        }}
                        className="min-h-[44px] max-h-[120px] pr-10 resize-none rounded-2xl border-white/10 bg-background/40 focus-visible:ring-accent/40"
                      />

                      <div className="absolute right-2 bottom-2 flex items-center gap-2">
                        <button
                          type="button"
                          aria-label={voiceOn ? "Stop voice input" : "Start voice input"}
                          className="w-9 h-9 rounded-full bg-card/50 border border-border/60 hover:bg-card/80 transition-colors flex items-center justify-center"
                          onClick={() => (voiceOn ? stopVoice() : startVoice())}
                          disabled={isGenerating}
                        >
                          {voiceOn ? <MicOff className="h-4 w-4 text-accent" /> : <Mic className="h-4 w-4 text-accent" />}
                        </button>
                      </div>
                    </div>

                    <motion.div whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.98 }}>
                      <Button
                        size="lg"
                        className="rounded-full h-11 bg-gradient-to-r from-violet-500 to-blue-500 text-white hover:from-violet-400 hover:to-blue-400 disabled:opacity-60 disabled:hover:from-violet-500 disabled:hover:to-blue-500"
                        onClick={() => void sendMessage()}
                        disabled={!canSend}
                      >
                        {isGenerating ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Send className="h-4 w-4 mr-2" />}
                        Send
                      </Button>
                    </motion.div>
                  </div>
                  <p className="mt-3 text-xs text-muted-foreground">
                    Tip: press <span className="font-semibold">Enter</span> to send, <span className="font-semibold">Shift+Enter</span> for a new line.
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Right: AI story steps */}
          <div className="lg:sticky lg:top-24">
            <motion.div
              initial={{ opacity: 0, y: 18 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.25 }}
              transition={createTransition({ duration: 0.35, delay: 0.05 })}
              className="space-y-6"
            >
              <div className="glass-panel rounded-3xl border-white/10 p-6">
                <h3 className="heading-card">How CONFIT works</h3>
                <p className="mt-3 text-body-sm text-muted-foreground">
                  A premium flow designed to build trust—fast.
                </p>

                <div className="mt-5 space-y-4">
                  {[
                    {
                      n: 1,
                      title: "Tell us your moment",
                      body: "Occasion + vibe + budget. That's enough—no need to overthink.",
                    },
                    {
                      n: 2,
                      title: "AI builds your looks",
                      body: "We generate premium outfit suggestions and styling confidence cues.",
                    },
                    {
                      n: 3,
                      title: "Try on, then refine",
                      body: "Tap Try On, Edit, or Replace items until it feels perfect.",
                    },
                  ].map((step) => {
                    const isActive = step.n === stage;
                    const isDone = step.n < stage;
                    return (
                      <motion.div
                        key={step.n}
                        className={`rounded-2xl border p-4 transition-colors duration-300 ${
                          isActive
                            ? "border-white/15 bg-gradient-to-r from-violet-500/15 to-blue-500/10"
                            : isDone
                              ? "border-white/10 bg-card/20"
                              : "border-border/60 bg-card/10"
                        }`}
                        whileHover={{ scale: 1.01 }}
                      >
                        <div className="flex items-start justify-between gap-4">
                          <div>
                            <p className="text-xs text-muted-foreground">Step {step.n}</p>
                            <h4 className="mt-1 font-semibold tracking-tight">{step.title}</h4>
                            <p className="mt-2 text-body-sm text-muted-foreground">{step.body}</p>
                          </div>
                          <div className="w-10 h-10 rounded-2xl bg-accent/15 border border-white/10 flex items-center justify-center">
                            <span className="font-bold text-accent">{isDone ? "✓" : step.n}</span>
                          </div>
                        </div>
                      </motion.div>
                    );
                  })}
                </div>
              </div>

              <div className="glass-panel rounded-3xl border-white/10 p-6">
                <h3 className="heading-card">Confidence boosters</h3>
                <div className="mt-4 grid grid-cols-1 gap-3">
                  {[
                    { title: "No guesswork", body: "Every step shows exactly what's happening next." },
                    { title: "Premium clarity", body: "Clean layout, subtle motion, and actionable outcomes." },
                    { title: "Refine in seconds", body: "Edit and replace until the look is yours." },
                  ].map((item) => (
                    <div key={item.title} className="flex items-start gap-3">
                      <div className="mt-0.5 w-6 h-6 rounded-full bg-accent/20 border border-white/10 flex items-center justify-center">
                        <Sparkles className="h-3.5 w-3.5 text-accent" />
                      </div>
                      <div>
                        <p className="text-sm font-semibold">{item.title}</p>
                        <p className="mt-1 text-body-sm text-muted-foreground">{item.body}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="hidden md:block">
                <Button
                  size="lg"
                  className="w-full rounded-3xl bg-gradient-to-r from-violet-500 to-blue-500 text-white h-12 shadow-lg hover:from-violet-400 hover:to-blue-400"
                  onClick={() => {
                    // Small helper: nudge the user with an instant prompt if they haven't started.
                    if (messages.length <= 1) {
                      void generateWithApi("I need an outfit for a wedding under $150");
                      return;
                    }
                    const el = document.getElementById("confit-ai-experience");
                    el?.scrollIntoView({ behavior: "smooth", block: "center" });
                  }}
                >
                  Build my look
                </Button>
              </div>
            </motion.div>
          </div>
        </div>
      </div>

      {/* Try-On Modal */}
      <Dialog open={tryOnOpen} onOpenChange={setTryOnOpen}>
        <DialogContent className="max-w-3xl rounded-3xl border-white/10 bg-background">
          <DialogHeader>
            <DialogTitle className="font-playfair">Try On Preview</DialogTitle>
            <DialogDescription>
              {tryOnOutfit ? (
                <>
                  Previewing <span className="font-semibold">{tryOnOutfit.name}</span>. For the full studio, continue below.
                </>
              ) : (
                "Preview your look."
              )}
            </DialogDescription>
          </DialogHeader>

          <div className="rounded-2xl overflow-hidden border border-border/60 bg-card/20">
            <div className="relative aspect-[16/9]">
              {tryOnOutfit ? (
                <img
                  src={tryOnOutfit.image}
                  alt={tryOnOutfit.name}
                  loading="lazy"
                  decoding="async"
                  className="w-full h-full object-cover"
                />
              ) : null}
              <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-black/20 to-transparent" />
              {tryOnOutfit ? (
                <div className="absolute bottom-4 left-4 right-4 flex items-end justify-between gap-4">
                  <div>
                    <p className="text-xs text-muted-foreground">Confidence</p>
                    <p className="text-lg font-semibold text-white">
                      {tryOnOutfit.styleScore}% match
                    </p>
                  </div>
                  <Badge variant="secondary" className="bg-white/15 text-white border-white/10">
                    {formatDollars(tryOnOutfit.price)}
                  </Badge>
                </div>
              ) : null}
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              className="rounded-full border-border/70"
              onClick={() => setTryOnOpen(false)}
            >
              Close
            </Button>
            <Button
              className="rounded-full bg-gradient-to-r from-violet-500 to-blue-500 text-white hover:from-violet-400 hover:to-blue-400"
              onClick={() => {
                setTryOnOpen(false);
                router.push("/try-on");
              }}
            >
              Open Try-On Studio
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Outfit Modal */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="max-w-2xl rounded-3xl border-white/10 bg-background">
          <DialogHeader>
            <DialogTitle className="font-playfair">Edit Outfit</DialogTitle>
            <DialogDescription>
              {editOutfit ? (
                <>
                  Refine <span className="font-semibold">{editOutfit.name}</span>—tell the stylist what to change.
                </>
              ) : (
                "Refine your look."
              )}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3">
            <label className="text-sm font-medium text-foreground">What should change?</label>
            <Textarea
              value={editPrompt}
              onChange={(e) => setEditPrompt(e.target.value)}
              placeholder="Make it more minimal, add a statement accessory, adjust the silhouette…"
              disabled={isGenerating}
              className="min-h-[120px] rounded-2xl border-white/10 bg-card/20 focus-visible:ring-accent/40"
            />
            <div className="text-xs text-muted-foreground">
              We’ll generate updated outfit suggestions you can try on immediately.
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button variant="outline" className="rounded-full border-border/70" onClick={() => setEditOpen(false)}>
              Cancel
            </Button>
            <Button
              className="rounded-full bg-gradient-to-r from-violet-500 to-blue-500 text-white hover:from-violet-400 hover:to-blue-400"
              onClick={() => {
                if (!editOutfit) return;
                const msg = `Edit outfit "${editOutfit.name}": ${editPrompt}`;
                setEditOpen(false);
                void generateWithApi(msg);
              }}
              disabled={isGenerating || !editPrompt.trim()}
            >
              {isGenerating ? "Generating…" : "Apply Edit"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Replace Items Modal */}
      <Dialog open={replaceOpen} onOpenChange={setReplaceOpen}>
        <DialogContent className="max-w-2xl rounded-3xl border-white/10 bg-background">
          <DialogHeader>
            <DialogTitle className="font-playfair">Replace Items</DialogTitle>
            <DialogDescription>
              {replaceOutfit ? (
                <>
                  Keep the vibe of <span className="font-semibold">{replaceOutfit.name}</span>, but swap items based on your instructions.
                </>
              ) : (
                "Replace items."
              )}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3">
            <label className="text-sm font-medium text-foreground">Replacement instructions</label>
            <Textarea
              value={replacePrompt}
              onChange={(e) => setReplacePrompt(e.target.value)}
              placeholder="Replace the shoes with something more elevated, swap the top for a silk finish…"
              disabled={isGenerating}
              className="min-h-[120px] rounded-2xl border-white/10 bg-card/20 focus-visible:ring-accent/40"
            />
            <div className="text-xs text-muted-foreground">
              We’ll regenerate a new set of outfit suggestions so you can compare instantly.
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button variant="outline" className="rounded-full border-border/70" onClick={() => setReplaceOpen(false)}>
              Cancel
            </Button>
            <Button
              className="rounded-full bg-gradient-to-r from-violet-500 to-blue-500 text-white hover:from-violet-400 hover:to-blue-400"
              onClick={() => {
                if (!replaceOutfit) return;
                const msg = `Replace items in outfit "${replaceOutfit.name}": ${replacePrompt}`;
                setReplaceOpen(false);
                void generateWithApi(msg);
              }}
              disabled={isGenerating || !replacePrompt.trim()}
            >
              {isGenerating ? "Generating…" : "Replace Items"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  );
}

