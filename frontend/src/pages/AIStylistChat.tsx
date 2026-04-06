import { useState, useRef, useEffect, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Send, Sparkles, RefreshCw, ShoppingBag, Heart, Eye,
  ChevronDown, X, Loader2, Bot, User, Palette, DollarSign,
  Calendar, Star, MessageCircle, MoreHorizontal
} from 'lucide-react';
import { MainLayout } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { useGender } from '@/context/GenderContext';
import { apiUrl } from '@/lib/api';
import { useStylistStore } from '@/stores/stylistStore';
import { createTransition } from '@/motion';
import { museService, type MuseChatResponse as MuseV1Response, type MuseOutfit } from '@/services/aiFeaturesService';

// ═══════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════

interface OutfitSuggestion {
  id: string;
  name: string;
  price: number;
  styleScore: number;
  image: string;
}

interface ProductRecommendation {
  id: string;
  productId: string;
  name: string;
  brand: string;
  price: number;
  image: string;
  matchScore: number;
  category?: string;
  color?: string;
}

interface WardrobeSuggestion {
  itemId: string;
  name: string;
  category: string;
  color?: string;
  imageUrl?: string;
  stylingTip?: string;
}

interface StyleTip {
  title: string;
  description: string;
  category?: string;
}

interface ChatResponse {
  content: string;
  sessionId: string;
  detectedOccasion?: string;
  detectedBudget?: string;
  detectedStyle?: string;
  detectedColors?: string[];
  outfitSuggestions?: OutfitSuggestion[];
  productRecommendations?: ProductRecommendation[];
  wardrobeSuggestions?: WardrobeSuggestion[];
  styleTips?: StyleTip[];
  cached?: boolean;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  outfitSuggestions?: OutfitSuggestion[];
  productRecommendations?: ProductRecommendation[];
  wardrobeSuggestions?: WardrobeSuggestion[];
  styleTips?: StyleTip[];
  detectedOccasion?: string;
  isStreaming?: boolean;
}

interface QuickAction {
  id: string;
  label: string;
  icon?: string;
  actionType: 'occasion' | 'budget' | 'style';
  value: string;
}

// ═══════════════════════════════════════════════════════════════════
// ANIMATION VARIANTS
// ═══════════════════════════════════════════════════════════════════

const messageVariants = {
  hidden: { opacity: 0, y: 20, scale: 0.95 },
  visible: { 
    opacity: 1, 
    y: 0, 
    scale: 1,
    transition: { type: 'spring' as const, stiffness: 300, damping: 24 }
  },
  exit: { opacity: 0, scale: 0.9, transition: { duration: 0.2 } }
};

const cardVariants = {
  hidden: { opacity: 0, y: 30 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.1, type: 'spring' as const, stiffness: 300, damping: 24 }
  }),
  hover: { 
    y: -8, 
    boxShadow: '0 20px 40px rgba(0,0,0,0.15)',
    transition: { type: 'spring' as const, stiffness: 400, damping: 17 }
  }
};

const typingDotsVariants = {
  animate: {
    scale: [1, 1.2, 1],
    transition: { repeat: Infinity, duration: 0.6 }
  }
};

const quickActionVariants = {
  hidden: { opacity: 0, scale: 0.8 },
  visible: { 
    opacity: 1, 
    scale: 1,
    transition: { type: 'spring' as const, stiffness: 400, damping: 17 }
  },
  hover: { scale: 1.05 },
  tap: { scale: 0.95 }
};

// ═══════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════

export default function AIStylistChatPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { selectedGender } = useGender();
  const { conversationId, setConversationId, clearConversation } = useStylistStore();
  
  const initialOccasion = searchParams?.get('occasion') ?? null;
  
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: "Hi! I'm your personal AI stylist. I can help you discover your perfect style, build outfits from your wardrobe, and find new pieces that match your taste. What are you dressing for today?",
      timestamp: new Date(),
    },
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [quickActions, setQuickActions] = useState<{
    occasions: QuickAction[];
    budgets: QuickAction[];
    styles: QuickAction[];
  } | null>(null);
  const [showQuickActions, setShowQuickActions] = useState(true);
  const [activeTab, setActiveTab] = useState<'occasions' | 'budgets' | 'styles'>('occasions');
  
  const chatEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  
  // Auto-scroll to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);
  
  // Fetch quick actions on mount
  useEffect(() => {
    fetchQuickActions();
  }, []);
  
  const fetchQuickActions = async () => {
    try {
      const response = await fetch(apiUrl('/api/stylist/quick-actions'));
      if (response.ok) {
        setQuickActions(await response.json());
      }
    } catch (error) {
      console.warn('Failed to fetch quick actions:', error);
    }
  };
  
  const sendMessage = useCallback(async (message: string) => {
    if (!message.trim() || isTyping) return;
    
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: message.trim(),
      timestamp: new Date(),
    };
    
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsTyping(true);
    setShowQuickActions(false);
    
    try {
      // Use v1 MUSE service
      const data: MuseV1Response = await museService.chat({
        message: message.trim(),
        language: 'en',
        session_id: sessionId || undefined,
      });
      
      if (data.session_id) {
        setSessionId(data.session_id);
      }
      
      // Map v1 response to local message format
      const outfitSuggestions: OutfitSuggestion[] = (data.outfits || []).map((o: MuseOutfit) => ({
        id: o.outfit_id,
        name: o.title,
        price: o.total_price,
        styleScore: 90,
        image: o.items[0]?.image_url || '',
      }));
      
      const productRecommendations: ProductRecommendation[] = (data.outfits || []).flatMap((o: MuseOutfit) =>
        o.items.map((it) => ({
          id: it.sku,
          productId: it.sku,
          name: it.name,
          brand: it.brand || '',
          price: it.price || 0,
          image: it.image_url || '',
          matchScore: 0.9,
          category: undefined,
          color: undefined,
        }))
      );
      
      const assistantMessage: Message = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: data.reply,
        timestamp: new Date(),
        outfitSuggestions,
        productRecommendations,
        wardrobeSuggestions: [],
        styleTips: (data.follow_ups || []).map((f: string) => ({ title: f, description: '' })),
      };
      
      setMessages(prev => [...prev, assistantMessage]);
      
    } catch (error) {
      console.error('Chat error:', error);
      
      // Fallback response
      const fallbackMessage: Message = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: "I'm having trouble connecting right now. Please try again in a moment.",
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, fallbackMessage]);
    }
    
    setIsTyping(false);
  }, [isTyping, sessionId, selectedGender]);
  
  const handleQuickAction = (action: QuickAction) => {
    sendMessage(`I need an outfit for ${action.label.toLowerCase()}`);
  };
  
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(inputValue);
    }
  };
  
  const clearChat = () => {
    setMessages([{
      id: 'welcome',
      role: 'assistant' as const,
      content: "Hi! I'm your personal AI stylist. What are you dressing for today?",
      timestamp: new Date(),
    }]);
    if (sessionId) {
      museService.clearSession(sessionId).catch(() => {});
    }
    setSessionId(null);
    setShowQuickActions(true);
    clearConversation();
  };
  
  return (
    <MainLayout>
      <div className="container py-8 px-4 md:px-8 max-w-6xl mx-auto">
        {/* Header */}
        <motion.div 
          className="text-center mb-8"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={createTransition({ duration: 0.5 })}
        >
          <div className="inline-flex items-center gap-2 bg-gradient-to-r from-accent/20 to-accent/10 text-accent px-4 py-2 rounded-full mb-4">
            <Sparkles className="h-4 w-4" />
            <span className="text-sm font-medium">AI-Powered Styling</span>
          </div>
          <h1 className="text-3xl md:text-4xl font-bold mb-3">Personal AI Stylist</h1>
          <p className="text-muted-foreground max-w-xl mx-auto">
            Your fashion expert that understands your style, occasion, and budget to create perfect outfit recommendations.
          </p>
        </motion.div>
        
        {/* Main Chat Container */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Sidebar - Quick Actions */}
          <motion.div 
            className="lg:col-span-1 hidden lg:block"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={createTransition({ delay: 0.2 })}
          >
            <Card className="sticky top-8 bg-card/50 backdrop-blur-sm border-border/50">
              <CardContent className="p-4 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-sm">Quick Start</h3>
                  <Button variant="ghost" size="sm" onClick={clearChat} className="h-8 px-2">
                    <RefreshCw className="h-3 w-3 mr-1" />
                    New
                  </Button>
                </div>
                
                {quickActions && (
                  <>
                    {/* Occasions */}
                    <div className="space-y-2">
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <Calendar className="h-3 w-3" />
                        Occasion
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {quickActions.occasions.slice(0, 6).map((action) => (
                          <motion.button
                            key={action.id}
                            variants={quickActionVariants}
                            whileHover="hover"
                            whileTap="tap"
                            onClick={() => handleQuickAction(action)}
                            className="px-2.5 py-1 text-xs bg-secondary hover:bg-accent/20 hover:text-accent rounded-full transition-colors"
                          >
                            {action.icon} {action.label}
                          </motion.button>
                        ))}
                      </div>
                    </div>
                    
                    {/* Budgets */}
                    <div className="space-y-2">
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <DollarSign className="h-3 w-3" />
                        Budget
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {quickActions.budgets.map((action) => (
                          <motion.button
                            key={action.id}
                            variants={quickActionVariants}
                            whileHover="hover"
                            whileTap="tap"
                            onClick={() => handleQuickAction(action)}
                            className="px-2.5 py-1 text-xs bg-secondary hover:bg-accent/20 hover:text-accent rounded-full transition-colors"
                          >
                            {action.label}
                          </motion.button>
                        ))}
                      </div>
                    </div>
                    
                    {/* Styles */}
                    <div className="space-y-2">
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <Palette className="h-3 w-3" />
                        Style
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {quickActions.styles.slice(0, 5).map((action) => (
                          <motion.button
                            key={action.id}
                            variants={quickActionVariants}
                            whileHover="hover"
                            whileTap="tap"
                            onClick={() => handleQuickAction(action)}
                            className="px-2.5 py-1 text-xs bg-secondary hover:bg-accent/20 hover:text-accent rounded-full transition-colors"
                          >
                            {action.label}
                          </motion.button>
                        ))}
                      </div>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
          </motion.div>
          
          {/* Chat Area */}
          <div className="lg:col-span-3">
            <Card className="bg-card/80 backdrop-blur-sm border-border/50 overflow-hidden">
              {/* Messages */}
              <div className="h-[500px] md:h-[600px] overflow-y-auto p-4 md:p-6 space-y-4">
                <AnimatePresence mode="popLayout">
                  {messages.map((message) => (
                    <motion.div
                      key={message.id}
                      variants={messageVariants}
                      initial="hidden"
                      animate="visible"
                      exit="exit"
                      layout
                      className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <MessageBubble message={message} router={router} />
                    </motion.div>
                  ))}
                </AnimatePresence>
                
                {/* Typing Indicator */}
                {isTyping && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex justify-start"
                  >
                    <div className="flex items-start gap-3">
                      <motion.div 
                        className="w-10 h-10 rounded-full bg-gradient-to-br from-accent/30 to-accent/10 flex items-center justify-center ring-2 ring-accent/20"
                        animate={{ scale: [1, 1.05, 1] }}
                        transition={createTransition({ repeat: Infinity, duration: 2 })}
                      >
                        <Sparkles className="h-5 w-5 text-accent" />
                      </motion.div>
                      <div className="bg-muted/80 rounded-2xl rounded-tl-none px-4 py-3">
                        <div className="flex gap-1">
                          {[0, 1, 2].map((i) => (
                            <motion.div
                              key={i}
                              className="w-2 h-2 bg-accent rounded-full"
                              variants={typingDotsVariants}
                              animate="animate"
                              style={{ animationDelay: `${i * 0.15}s` }}
                            />
                          ))}
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )}
                
                <div ref={chatEndRef} />
              </div>
              
              {/* Mobile Quick Actions */}
              {showQuickActions && messages.length < 3 && quickActions && (
                <div className="md:hidden px-4 pb-4">
                  <div className="flex gap-2 overflow-x-auto pb-2">
                    {quickActions.occasions.slice(0, 4).map((action) => (
                      <motion.button
                        key={action.id}
                        variants={quickActionVariants}
                        whileHover="hover"
                        whileTap="tap"
                        onClick={() => handleQuickAction(action)}
                        className="flex-shrink-0 px-3 py-2 text-sm bg-secondary hover:bg-accent/20 hover:text-accent rounded-full transition-colors whitespace-nowrap"
                      >
                        {action.icon} {action.label}
                      </motion.button>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Input Area */}
              <div className="border-t border-border/50 p-4 bg-muted/30">
                <div className="flex gap-3 items-end">
                  <div className="flex-1 relative">
                    <Input
                      ref={inputRef}
                      value={inputValue}
                      onChange={(e) => setInputValue(e.target.value)}
                      onKeyDown={handleKeyDown}
                      placeholder="Ask about outfits, colors, styles..."
                      disabled={isTyping}
                      className="pr-12 bg-background/80 border-border/50 focus:border-accent/50 resize-none"
                    />
                  </div>
                  <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                    <Button
                      onClick={() => sendMessage(inputValue)}
                      disabled={!inputValue.trim() || isTyping}
                      className="bg-accent hover:bg-accent/90 text-accent-foreground"
                    >
                      {isTyping ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Send className="h-4 w-4" />
                      )}
                    </Button>
                  </motion.div>
                </div>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </MainLayout>
  );
}

// ═══════════════════════════════════════════════════════════════════
// MESSAGE BUBBLE COMPONENT
// ═══════════════════════════════════════════════════════════════════

function MessageBubble({
  message,
  router,
}: {
  message: Message;
  router: ReturnType<typeof useRouter>;
}) {
  const isUser = message.role === 'user';
  
  return (
    <div className={`flex items-start gap-3 max-w-[85%] ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <motion.div 
        className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${
          isUser 
            ? 'bg-primary text-primary-foreground' 
            : 'bg-gradient-to-br from-accent/30 to-accent/10 ring-2 ring-accent/20'
        }`}
        whileHover={{ scale: 1.1 }}
        transition={createTransition({ type: 'spring', stiffness: 400, damping: 17 })}
      >
        {isUser ? <User className="h-5 w-5" /> : <Sparkles className="h-5 w-5 text-accent" />}
      </motion.div>
      
      <div className="space-y-3">
        {/* Message Content */}
        <motion.div 
          className={`px-4 py-3 rounded-2xl ${
            isUser 
              ? 'bg-primary text-primary-foreground rounded-tr-none' 
              : 'bg-muted/80 backdrop-blur-sm rounded-tl-none border border-border/50'
          }`}
          whileHover={{ scale: isUser ? 1.02 : 1 }}
        >
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
        </motion.div>
        
        {/* Outfit Suggestions */}
        {message.outfitSuggestions && message.outfitSuggestions.length > 0 && (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 pt-2">
            {message.outfitSuggestions.map((outfit, i) => (
              <OutfitCard key={outfit.id} outfit={outfit} index={i} router={router} />
            ))}
          </div>
        )}
        
        {/* Product Recommendations */}
        {message.productRecommendations && message.productRecommendations.length > 0 && (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 pt-2">
            {message.productRecommendations.slice(0, 6).map((product, i) => (
              <ProductCard key={product.id} product={product} index={i} router={router} />
            ))}
          </div>
        )}
        
        {/* Wardrobe Suggestions */}
        {message.wardrobeSuggestions && message.wardrobeSuggestions.length > 0 && (
          <div className="space-y-2 pt-2">
            <p className="text-xs text-muted-foreground font-medium">From Your Wardrobe:</p>
            <div className="flex flex-wrap gap-2">
              {message.wardrobeSuggestions.map((item) => (
                <Badge key={item.itemId} variant="outline" className="px-3 py-1.5">
                  {item.name}
                  {item.color && <span className="ml-1 opacity-60">({item.color})</span>}
                </Badge>
              ))}
            </div>
          </div>
        )}
        
        {/* Style Tips */}
        {message.styleTips && message.styleTips.length > 0 && (
          <div className="space-y-2 pt-2">
            {message.styleTips.map((tip, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={createTransition({ delay: i * 0.1 })}
                className="flex items-start gap-2 text-xs text-muted-foreground bg-secondary/50 rounded-lg px-3 py-2"
              >
                <Star className="h-3 w-3 text-accent shrink-0 mt-0.5" />
                <div>
                  <span className="font-medium text-foreground">{tip.title}:</span> {tip.description}
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// OUTFIT CARD COMPONENT
// ═══════════════════════════════════════════════════════════════════

function OutfitCard({
  outfit,
  index,
  router,
}: {
  outfit: OutfitSuggestion;
  index: number;
  router: ReturnType<typeof useRouter>;
}) {
  return (
    <motion.div
      custom={index}
      variants={cardVariants}
      initial="hidden"
      animate="visible"
      whileHover="hover"
      className="group cursor-pointer"
      onClick={() => router.push(`/outfits/${outfit.id}`)}
    >
      <div className="relative aspect-[3/4] rounded-xl overflow-hidden bg-muted">
        <img
          src={outfit.image}
          alt={outfit.name}
          className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
          loading="lazy"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
        
        {/* Overlay Content */}
        <div className="absolute bottom-0 left-0 right-0 p-3 translate-y-2 group-hover:translate-y-0 transition-transform duration-300">
          <h4 className="font-medium text-sm text-white truncate">{outfit.name}</h4>
          <div className="flex items-center justify-between mt-1">
            <span className="text-white/90 text-xs font-semibold">${outfit.price}</span>
            <Badge variant="secondary" className="text-[10px] px-1.5 py-0.5 bg-accent/90 text-accent-foreground">
              {outfit.styleScore}% match
            </Badge>
          </div>
        </div>
        
        {/* Action Buttons */}
        <div className="absolute top-2 right-2 flex flex-col gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
          <motion.button
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            className="w-7 h-7 rounded-full bg-white/90 flex items-center justify-center shadow-md hover:bg-white"
            onClick={(e) => {
              e.stopPropagation();
              router.push(`/try-on?outfit=${outfit.id}`);
            }}
          >
            <Eye className="h-3.5 w-3.5 text-foreground" />
          </motion.button>
          <motion.button
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            className="w-7 h-7 rounded-full bg-white/90 flex items-center justify-center shadow-md hover:bg-white"
            onClick={(e) => {
              e.stopPropagation();
              // Add to wishlist
            }}
          >
            <Heart className="h-3.5 w-3.5 text-foreground" />
          </motion.button>
        </div>
      </div>
    </motion.div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// PRODUCT CARD COMPONENT
// ═══════════════════════════════════════════════════════════════════

function ProductCard({
  product,
  index,
  router,
}: {
  product: ProductRecommendation;
  index: number;
  router: ReturnType<typeof useRouter>;
}) {
  return (
    <motion.div
      custom={index}
      variants={cardVariants}
      initial="hidden"
      animate="visible"
      whileHover="hover"
      className="group cursor-pointer"
      onClick={() => router.push(`/products/${product.productId}`)}
    >
      <div className="relative aspect-square rounded-xl overflow-hidden bg-muted">
        <img
          src={product.image}
          alt={product.name}
          className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
          loading="lazy"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
        
        {/* Match Score Badge */}
        <div className="absolute top-2 left-2">
          <Badge className="bg-accent text-accent-foreground text-[10px] px-2 py-0.5">
            {Math.round(product.matchScore * 100)}% match
          </Badge>
        </div>
        
        {/* Overlay Content */}
        <div className="absolute bottom-0 left-0 right-0 p-2.5 translate-y-1 group-hover:translate-y-0 transition-transform duration-300">
          <p className="text-xs text-white/80 truncate">{product.brand}</p>
          <h4 className="font-medium text-sm text-white truncate">{product.name}</h4>
          <span className="text-white/90 text-xs font-semibold">${product.price}</span>
        </div>
        
        {/* Quick Add Button */}
        <motion.button
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          className="absolute bottom-2 right-2 w-8 h-8 rounded-full bg-accent text-accent-foreground flex items-center justify-center shadow-lg opacity-0 group-hover:opacity-100 transition-opacity"
          onClick={(e) => {
            e.stopPropagation();
            // Add to cart
          }}
        >
          <ShoppingBag className="h-4 w-4" />
        </motion.button>
      </div>
    </motion.div>
  );
}
