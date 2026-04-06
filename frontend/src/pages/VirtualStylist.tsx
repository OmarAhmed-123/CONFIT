import { useState, useRef, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { motion } from 'framer-motion';
import { Send, Sparkles, Calendar, DollarSign, Palette, RefreshCw } from 'lucide-react';
import { MainLayout } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { occasions, styleTypes } from '@/services/mockData';
import type { OccasionType, StyleType, OutfitSuggestion } from '@/types';
import { useGender } from '@/context/GenderContext';

import { apiUrl } from '@/lib/api';
import { createTransition } from '@/motion';
import { GlassCard } from '@/components/shared';
import { ScrollReveal } from '@/components/motion/ScrollReveal';

interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  outfitSuggestions?: OutfitSuggestion[];
}

// ── Fallback data for when backend is not available ──────────────

const fallbackOutfits: OutfitSuggestion[] = [
  {
    id: '1',
    name: 'Executive Elegance',
    image: 'https://images.unsplash.com/photo-1594938298603-c8148c4dae35?w=300&h=400&fit=crop',
    price: 485,
    styleScore: 92,
  },
  {
    id: '2',
    name: 'Power Meeting',
    image: 'https://images.unsplash.com/photo-1539109136881-3be0616acf4b?w=300&h=400&fit=crop',
    price: 520,
    styleScore: 88,
  },
  {
    id: '3',
    name: 'Corporate Chic',
    image: 'https://images.unsplash.com/photo-1617019114583-affb34d1b3cd?w=300&h=400&fit=crop',
    price: 395,
    styleScore: 90,
  },
];

// ── API Helper ───────────────────────────────────────────────────

async function callStylistAPI(
  message: string,
  conversationHistory: { role: string; content: string }[],
  occasion?: string | null,
  budget?: string,
  stylePreference?: string | null,
  gender?: string,
): Promise<{
  content: string;
  outfitSuggestions?: OutfitSuggestion[];
  detectedOccasion?: string;
} | null> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 8000);
    
    const response = await fetch(apiUrl('/api/stylist/chat'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        conversationHistory,
        occasion: occasion || undefined,
        budget: budget || undefined,
        stylePreference: stylePreference || undefined,
        gender: gender || undefined,
      }),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      console.warn('Stylist API timeout, using local fallback');
    } else {
      console.warn('Stylist API not available, using local fallback:', error);
    }
    return null;
  }
}

// ── Local fallback logic ─────────────────────────────────────────

function localFallbackResponse(input: string, selectedOccasion: string | null, gender?: string): {
  content: string;
  outfitSuggestions?: OutfitSuggestion[];
  detectedOccasion?: string;
} {
  const lowerInput = input.toLowerCase();
  let responseContent = `I've analyzed your request for ${gender === 'men' ? "men's" : "women's"} fashion. Here are some personalized suggestions.`;
  let detectedOccasion: string | undefined;

  if (lowerInput.includes('wedding') || lowerInput.includes('formal')) {
    responseContent = "A formal occasion! I'll find elegant and sophisticated options.";
    detectedOccasion = 'formal';
  } else if (lowerInput.includes('party') || lowerInput.includes('club') || lowerInput.includes('night out')) {
    responseContent = "Time to shine! Here are some trendy party looks.";
    detectedOccasion = 'party';
  } else if (lowerInput.includes('work') || lowerInput.includes('office') || lowerInput.includes('business')) {
    responseContent = "Let's keep it professional yet stylish!";
    detectedOccasion = 'work';
  } else if (lowerInput.includes('date') || lowerInput.includes('dinner')) {
    responseContent = "Ooh, a date! I'll find something impressive yet comfortable.";
    detectedOccasion = 'date';
  } else if (lowerInput.includes('casual') || lowerInput.includes('everyday')) {
    responseContent = "Keeping it casual and cool. Check out these daily picks.";
    detectedOccasion = 'casual';
  } else if (lowerInput.includes('active') || lowerInput.includes('gym') || lowerInput.includes('run')) {
    responseContent = "Get ready to move! Functional and stylish activewear sets.";
    detectedOccasion = 'active';
  }

  // Color advice
  const colorAdvice: Record<string, string> = {
    blue: "Blue goes great with white, beige, or grey.",
    red: "Red is bold! Pair with black, white, or denim.",
    green: "Green works well with earth tones and crisp white.",
    black: "Black is versatile — go monochrome or add a pop of color.",
    white: "White pairs beautifully with pastels or bold primaries.",
  };

  for (const [color, advice] of Object.entries(colorAdvice)) {
    if (lowerInput.includes(color)) {
      responseContent += ` ${advice}`;
      break;
    }
  }

  if (!detectedOccasion && !selectedOccasion) {
    responseContent = "I'd love to help! Could you tell me more about the occasion? Work, a date, party, or casual outing?";
  }

  const showOutfits = detectedOccasion || selectedOccasion ||
    lowerInput.includes('show') || lowerInput.includes('recommend');

  return {
    content: responseContent,
    outfitSuggestions: showOutfits ? fallbackOutfits : undefined,
    detectedOccasion,
  };
}

// ── Main Component ───────────────────────────────────────────────

export default function VirtualStylistPage() {
  const searchParams = useSearchParams();
  const { selectedGender } = useGender();
  const initialOccasion = searchParams.get('occasion') as OccasionType | null;

  const [selectedOccasion, setSelectedOccasion] = useState<OccasionType | null>(initialOccasion);
  const [selectedStyle, setSelectedStyle] = useState<StyleType | null>(null);
  const [budget, setBudget] = useState<string>('');
  const [inputMessage, setInputMessage] = useState('');
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      type: 'assistant',
      content: "Hi! I'm your personal CONFIT stylist. Tell me about your occasion, style preferences, and budget, and I'll create the perfect outfits for you. What are you getting dressed for today?",
      timestamp: new Date(),
    },
  ]);
  const [isTyping, setIsTyping] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isTyping) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: inputMessage,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    const currentInput = inputMessage;
    setInputMessage('');
    setIsTyping(true);

    // Build conversation history for the API
    const history = messages
      .filter(m => m.id !== '1') // skip initial greeting
      .map(m => ({
        role: m.type === 'user' ? 'user' : 'assistant',
        content: m.content,
      }));

    // Try backend first with timeout, fallback to local immediately
    const apiPromise = callStylistAPI(
      currentInput,
      history,
      selectedOccasion,
      budget,
      selectedStyle,
      selectedGender
    );
    
    // Use local fallback immediately if API takes too long
    const timeoutPromise = new Promise<null>((resolve) => {
      setTimeout(() => resolve(null), 3000);
    });
    
    const apiResult = await Promise.race([apiPromise, timeoutPromise]);
    const result = apiResult || localFallbackResponse(currentInput, selectedOccasion, selectedGender);

    // Update detected occasion
    if (result.detectedOccasion) {
      setSelectedOccasion(result.detectedOccasion as OccasionType);
    }

    const assistantMessage: Message = {
      id: (Date.now() + 1).toString(),
      type: 'assistant',
      content: result.content,
      timestamp: new Date(),
      outfitSuggestions: result.outfitSuggestions as OutfitSuggestion[] | undefined,
    };

    setMessages(prev => [...prev, assistantMessage]);
    setIsTyping(false);
  };

  const handleQuickSelect = async (occasion: OccasionType) => {
    setSelectedOccasion(occasion);
    const occasionLabel = occasions.find(o => o.id === occasion)?.label || occasion;

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: `I need an outfit for: ${occasionLabel}`,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMessage]);
    setIsTyping(true);

    // Try backend with timeout
    const apiPromise = callStylistAPI(
      `I need an outfit for: ${occasionLabel}`,
      [],
      occasion,
      budget,
      selectedStyle,
      selectedGender
    );
    
    const timeoutPromise = new Promise<null>((resolve) => {
      setTimeout(() => resolve(null), 3000);
    });
    
    const apiResult = await Promise.race([apiPromise, timeoutPromise]);
    const fallback = localFallbackResponse(`I need an outfit for: ${occasionLabel}`, occasion, selectedGender);
    const defaultContent = apiResult?.content || fallback.content || `Great choice! I'll style you for a ${occasionLabel} occasion. What's your budget range, and do you have any style preferences?`;

    const assistantMessage: Message = {
      id: (Date.now() + 1).toString(),
      type: 'assistant',
      content: defaultContent,
      timestamp: new Date(),
      outfitSuggestions: (apiResult?.outfitSuggestions || fallback.outfitSuggestions) as OutfitSuggestion[] | undefined,
    };

    setMessages(prev => [...prev, assistantMessage]);
    setIsTyping(false);
  };

  return (
    <MainLayout>
      <div className="container py-8">
        <div className="max-w-5xl mx-auto">
          {/* Header */}
          <ScrollReveal className="text-center mb-8">
            <div className="inline-flex items-center gap-2 bg-accent/10 text-accent px-4 py-2 rounded-full mb-4">
              <Sparkles className="h-4 w-4" />
              <span className="text-sm font-medium">AI-Powered Styling</span>
            </div>
            <h1 className="heading-hero mb-4">Virtual Stylist</h1>
            <p className="text-muted-foreground max-w-xl mx-auto">
              Tell me about your occasion and style preferences. I'll curate personalized outfit recommendations just for you.
            </p>
          </ScrollReveal>

          {/* Quick Occasion Selection */}
          {!selectedOccasion && messages.length < 3 && (
            <div className="mb-8">
              <p className="text-center text-sm text-muted-foreground mb-4">Quick start — select an occasion:</p>
              <div className="flex flex-wrap justify-center gap-3">
                {occasions.slice(0, 6).map((occasion) => (
                  <button
                    key={occasion.id}
                    onClick={() => handleQuickSelect(occasion.id)}
                    className="flex items-center gap-2 bg-secondary hover:bg-accent/10 hover:text-accent px-4 py-2 rounded-full transition-colors"
                  >
                    <span>{occasion.icon}</span>
                    <span className="text-sm font-medium">{occasion.label}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Chat Interface */}
          <GlassCard className="overflow-hidden">
            {/* Chat Messages */}
            <div className="h-[500px] overflow-y-auto p-6 space-y-6">
              {messages.map((message) => (
                <ChatMessage key={message.id} message={message} />
              ))}

              {isTyping && (
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 rounded-full bg-accent/10 flex items-center justify-center shrink-0">
                    <Sparkles className="h-5 w-5 text-accent" />
                  </div>
                  <div className="bg-muted rounded-2xl rounded-tl-none px-4 py-3">
                    <div className="flex gap-1">
                      <span className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Input Bar */}
            <div className="border-t border-border p-4">
              <div className="flex gap-3">
                <div className="flex-1 relative">
                  <Input
                    type="text"
                    placeholder="Describe what you're looking for..."
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                    className="pr-12 h-12"
                  />
                </div>
                <Button
                  variant="hero"
                  size="icon-lg"
                  onClick={handleSendMessage}
                  disabled={!inputMessage.trim() || isTyping}
                >
                  <Send className="h-5 w-5" />
                </Button>
              </div>

              {/* Quick Actions */}
              <div className="flex flex-wrap gap-2 mt-3">
                <button
                  onClick={() => {
                    if (!selectedOccasion) {
                      const msg: Message = {
                        id: Date.now().toString(),
                        type: 'user',
                        content: 'I need help choosing an occasion for my outfit.',
                        timestamp: new Date(),
                      };
                      setMessages(prev => [...prev, msg]);
                      setIsTyping(true);
                      callStylistAPI('I need help choosing an occasion for my outfit.', [], undefined, undefined, undefined, selectedGender).then(result => {
                        setMessages(prev => [...prev, {
                          id: (Date.now() + 1).toString(),
                          type: 'assistant',
                          content: result?.content || 'I can help with that! Are you dressing for work, a date night, a casual outing, or something more formal? Select from the options above or tell me more.',
                          timestamp: new Date(),
                        }]);
                        setIsTyping(false);
                      });
                    }
                  }}
                  className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-accent px-3 py-1.5 rounded-full border border-border hover:border-accent transition-colors"
                >
                  <Calendar className="h-3 w-3" />
                  Add occasion
                </button>
                <button
                  onClick={() => {
                    const budgetInput = prompt('Enter your budget (e.g., $200, $500):');
                    if (budgetInput) {
                      setBudget(budgetInput);
                      const msg: Message = {
                        id: Date.now().toString(),
                        type: 'user',
                        content: `My budget is ${budgetInput}`,
                        timestamp: new Date(),
                      };
                      setMessages(prev => [...prev, msg]);
                      setIsTyping(true);
                      callStylistAPI(`My budget is ${budgetInput}`, [], selectedOccasion, budgetInput, undefined, selectedGender).then(result => {
                        setMessages(prev => [...prev, {
                          id: (Date.now() + 1).toString(),
                          type: 'assistant',
                          content: result?.content || `Perfect! I'll keep your ${budgetInput} budget in mind. I'll find you the best options within your range while maximizing style and quality.`,
                          timestamp: new Date(),
                          outfitSuggestions: result?.outfitSuggestions as OutfitSuggestion[] | undefined,
                        }]);
                        setIsTyping(false);
                      });
                    }
                  }}
                  className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-accent px-3 py-1.5 rounded-full border border-border hover:border-accent transition-colors"
                >
                  <DollarSign className="h-3 w-3" />
                  {budget ? `Budget: ${budget}` : 'Set budget'}
                </button>
                <button
                  onClick={() => {
                    const styles = ['Classic', 'Modern', 'Bohemian', 'Minimalist', 'Edgy', 'Romantic'];
                    const styleChoice = prompt(`Choose your style preference:\n${styles.map((s, i) => `${i + 1}. ${s}`).join('\n')}\n\nEnter number or style name:`);
                    if (styleChoice) {
                      const styleName = isNaN(Number(styleChoice)) ? styleChoice : styles[Number(styleChoice) - 1];
                      if (styleName) {
                        const msg: Message = {
                          id: Date.now().toString(),
                          type: 'user',
                          content: `I prefer a ${styleName} style`,
                          timestamp: new Date(),
                        };
                        setMessages(prev => [...prev, msg]);
                        setIsTyping(true);
                        callStylistAPI(`I prefer a ${styleName} style`, [], selectedOccasion, budget, styleName, selectedGender).then(result => {
                          setMessages(prev => [...prev, {
                            id: (Date.now() + 1).toString(),
                            type: 'assistant',
                            content: result?.content || `Love it! ${styleName} style is timeless. I'll curate pieces that perfectly capture that aesthetic for you.`,
                            timestamp: new Date(),
                            outfitSuggestions: result?.outfitSuggestions as OutfitSuggestion[] | undefined,
                          }]);
                          setIsTyping(false);
                        });
                      }
                    }
                  }}
                  className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-accent px-3 py-1.5 rounded-full border border-border hover:border-accent transition-colors"
                >
                  <Palette className="h-3 w-3" />
                  Style preference
                </button>
                <button
                  onClick={() => {
                    setIsTyping(true);
                    callStylistAPI('Show me some fresh outfit ideas and trending looks', [], selectedOccasion, budget, undefined, selectedGender).then(result => {
                      setMessages(prev => [...prev, {
                        id: Date.now().toString(),
                        type: 'assistant',
                        content: result?.content || "Here are some fresh outfit ideas based on what's trending right now!",
                        timestamp: new Date(),
                        outfitSuggestions: (result?.outfitSuggestions as OutfitSuggestion[] | undefined) || fallbackOutfits,
                      }]);
                      setIsTyping(false);
                    });
                  }}
                  className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-accent px-3 py-1.5 rounded-full border border-border hover:border-accent transition-colors"
                >
                  <RefreshCw className="h-3 w-3" />
                  More options
                </button>
              </div>
            </div>
          </GlassCard>
        </div>
      </div>
    </MainLayout>
  );
}

function ChatMessage({ message }: { message: Message }) {
  if (message.type === 'user') {
    return (
      <motion.div 
        className="flex justify-end"
        initial={{ opacity: 0, x: 10 }}
        animate={{ opacity: 1, x: 0 }}
        transition={createTransition({ duration: 0.3 })}
      >
        <motion.div 
          className="bg-primary text-primary-foreground rounded-2xl rounded-tr-none px-4 py-3 max-w-md shadow-md"
          whileHover={{ scale: 1.02 }}
          transition={createTransition({ type: "spring", stiffness: 400, damping: 17 })}
        >
          <p className="text-sm leading-relaxed">{message.content}</p>
        </motion.div>
      </motion.div>
    );
  }

  return (
    <motion.div 
      className="flex items-start gap-3"
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={createTransition({ duration: 0.3 })}
    >
      <motion.div 
        className="w-10 h-10 rounded-full bg-gradient-to-br from-accent/20 to-accent/10 flex items-center justify-center shrink-0 ring-2 ring-accent/20"
        whileHover={{ scale: 1.1 }}
        transition={createTransition({ type: "spring", stiffness: 400, damping: 17 })}
      >
        <Sparkles className="h-5 w-5 text-accent" />
      </motion.div>
      <div className="flex-1 space-y-4">
        <motion.div 
          className="bg-muted/80 backdrop-blur-sm rounded-2xl rounded-tl-none px-4 py-3 max-w-xl border border-border/50 shadow-sm"
          initial={{ opacity: 0, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          transition={createTransition({ delay: 0.1 })}
        >
          <p className="text-sm leading-relaxed text-foreground">{message.content}</p>
        </motion.div>

        {message.outfitSuggestions && (
          <div className="grid grid-cols-3 gap-4">
            {message.outfitSuggestions.map((outfit) => (
              <motion.div
                key={outfit.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="group cursor-pointer"
              >
                <div className="relative aspect-[3/4] rounded-lg overflow-hidden mb-2">
                  <img
                    src={outfit.image}
                    alt={outfit.name}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-charcoal/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                  <div className="absolute bottom-2 left-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <Button variant="gold" size="sm" className="w-full text-xs">
                      Try On
                    </Button>
                  </div>
                </div>
                <h4 className="font-medium text-sm">{outfit.name}</h4>
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>${outfit.price}</span>
                  <span>{outfit.styleScore}% match</span>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
}

function QuickAction({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <button className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-accent px-3 py-1.5 rounded-full border border-border hover:border-accent transition-colors">
      {icon}
      {label}
    </button>
  );
}
