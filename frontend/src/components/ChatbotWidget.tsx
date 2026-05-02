import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { MessageCircle, X, Sparkles, Send, Bot, User, Settings } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { geminiService, type GeminiRequest } from '@/services/geminiService';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'bot';
  timestamp: Date;
}

interface SmartResponse {
  text: string;
  suggestions?: string[];
  actions?: { label: string; action: string }[];
}

const SMART_RESPONSES: Record<string, SmartResponse> = {
  'style challenge': {
    text: "Style challenges are fun daily quests to help you explore your fashion creativity! Each challenge gives you specific constraints to work with, helping you build better outfits and earn points on the leaderboard.",
    suggestions: [
      "What's today's challenge?",
      "How do I submit an outfit?",
      "Tell me about the leaderboard"
    ],
    actions: [
      { label: "View Today's Challenge", action: "/challenges" },
      { label: "Build Outfit", action: "/outfits" }
    ]
  },
  'outfit': {
    text: "Building great outfits is all about balance! Consider color harmony, proportion, and occasion. Would you like tips on creating a specific type of outfit?",
    suggestions: [
      "Business casual outfit",
      "Weekend casual look",
      "Evening elegant style",
      "Sporty comfortable outfit"
    ],
    actions: [
      { label: "Outfit Builder", action: "/outfits" },
      { label: "Style Quiz", action: "/chatbot" }
    ]
  },
  'color': {
    text: "Color theory is key to great style! Complementary colors create contrast, analogous colors create harmony, and neutrals tie everything together. What's your favorite color to wear?",
    suggestions: [
      "Color combinations for my skin tone",
      "Best colors for work",
      "Seasonal color palettes"
    ]
  },
  'trend': {
    text: "Fashion trends are exciting but remember: the best trend is the one that makes you feel confident! Currently trending are oversized blazers, wide-leg pants, and statement accessories.",
    suggestions: [
      "Trends for my body type",
      "How to wear trends casually",
      "Timeless vs trendy pieces"
    ]
  },
  'help': {
    text: "I'm here to help with all your style questions! I can assist with outfit recommendations, color advice, trend information, and style challenges. What would you like to know?",
    suggestions: [
      "Style challenges",
      "Outfit advice",
      "Color combinations",
      "Fashion trends",
      "Personal styling"
    ],
    actions: [
      { label: "Start Style Quiz", action: "/chatbot" },
      { label: "Style Challenges", action: "/challenges" }
    ]
  },
  'hello': {
    text: "Hello! Welcome to CONFIT - your personal fashion assistant. I'm here to help you discover your style, build amazing outfits, and stay on trend. How can I assist you today?",
    suggestions: ["Show me trending styles", "Help me build an outfit", "What are style challenges?"],
    actions: [{ label: "Discover Fashion", action: "/discover" }]
  },
  'hi': {
    text: "Hi there! I'm your CONFIT style assistant, ready to help you look and feel your best. Whether you need outfit advice, color tips, or want to explore style challenges - I've got you covered!",
    suggestions: ["Personal styling tips", "Build my outfit", "Explore trends"],
    actions: [{ label: "Virtual Try-On", action: "/try-on" }]
  },
  'thank': {
    text: "You're very welcome! I'm always happy to help with your fashion journey. Is there anything else you'd like to know about styling, trends, or building the perfect outfit?",
    suggestions: ["More style tips", "Show me products", "Style challenges"]
  },
  'size': {
    text: "Finding the right size is crucial for comfort and confidence! I recommend checking our size guide for each brand, as sizing can vary. Would you like tips on measuring yourself or understanding fit types?",
    suggestions: ["How to measure myself", "Slim vs regular fit", "Size guide explanation"]
  },
  'price': {
    text: "CONFIT offers a wide range of fashion items across different price points. You can filter products by price range on the Discover page. Are you looking for something specific within a budget?",
    suggestions: ["Budget-friendly options", "Premium picks", "Sale items"],
    actions: [{ label: "Browse Products", action: "/discover" }]
  },
  'shipping': {
    text: "We offer various shipping options including standard (5-7 days) and express (2-3 days). Shipping is free for orders over $50. You can track your order in the Order History section.",
    suggestions: ["Track my order", "Shipping costs", "International delivery"],
    actions: [{ label: "Order History", action: "/orders" }]
  },
  'return': {
    text: "We have a 30-day return policy for unworn items with original tags. Returns are free and easy - just initiate a return from your order history and we'll provide a prepaid label.",
    suggestions: ["How to return", "Refund timeline", "Exchange policy"]
  },
  'wardrobe': {
    text: "Your digital wardrobe helps you organize and plan outfits! You can add items, create outfit combinations, and get AI-powered suggestions based on what you own.",
    suggestions: ["Add items to wardrobe", "Create outfit", "Wardrobe tips"],
    actions: [{ label: "My Wardrobe", action: "/wardrobe" }]
  },
  'virtual try': {
    text: "Our Virtual Try-On feature lets you see how clothes look on you before buying! Upload your photo, select a product, and get a realistic preview of the fit.",
    suggestions: ["How does it work", "Try on clothes", "Best results tips"],
    actions: [{ label: "Try Virtual Try-On", action: "/try-on" }]
  },
  'brand': {
    text: "CONFIT partners with over 200 curated brands, from luxury designers to sustainable fashion labels. Each brand is vetted for quality and authenticity. Would you like to explore our brand directory?",
    suggestions: ["Popular brands", "Sustainable brands", "New arrivals"],
    actions: [{ label: "Browse Brands", action: "/brands" }]
  },
  'sustainable': {
    text: "Sustainability is important to us! We feature many eco-friendly brands that use organic materials, recycled fabrics, and ethical manufacturing. Look for the green leaf icon on sustainable products.",
    suggestions: ["Eco-friendly brands", "Sustainable materials", "How to shop sustainably"]
  },
  'sale': {
    text: "Great news - we often have sales and special offers! Check the Discover page for discounted items, or sign up for our newsletter to get notified about exclusive deals.",
    suggestions: ["Current sales", "Newsletter signup", "Discount codes"],
    actions: [{ label: "Shop Sales", action: "/discover" }]
  },
  'recommend': {
    text: "I'd love to give you personalized recommendations! To give you the best advice, tell me about your style preferences, the occasion you're dressing for, or your favorite colors.",
    suggestions: ["Casual everyday style", "Work attire", "Special occasion outfit"]
  }
};

function getSmartResponse(message: string): SmartResponse {
  const lowerMessage = message.toLowerCase();
  
  // Check for specific keywords in order of priority
  const keywords = [
    'style challenge', 'outfit', 'color', 'trend', 'help', 'hello', 'hi',
    'thank', 'size', 'price', 'shipping', 'return', 'wardrobe', 'virtual try',
    'brand', 'sustainable', 'sale', 'recommend'
  ];
  
  for (const key of keywords) {
    if (lowerMessage.includes(key)) {
      return SMART_RESPONSES[key];
    }
  }
  
  // Check for question patterns
  if (lowerMessage.includes('?') || lowerMessage.startsWith('what') || lowerMessage.startsWith('how') || lowerMessage.startsWith('why')) {
    return {
      text: "That's a great question! I specialize in fashion advice, outfit building, and style challenges. Could you tell me more about what you're looking for? I can help with specific styling tips, color coordination, or finding the perfect outfit for any occasion.",
      suggestions: ["Style advice", "Outfit ideas", "Color matching", "Fashion tips"],
      actions: [{ label: "Explore Styles", action: "/discover" }]
    };
  }
  
  // Default response for unclear messages
  return {
    text: "I'm here to help with your fashion journey! I can assist with outfit recommendations, color advice, style challenges, and trend information. What would you like to explore today?",
    suggestions: ["Tell me about style challenges", "Help me build an outfit", "Color advice", "Fashion trends"],
    actions: [{ label: "Start Style Quiz", action: "/chatbot" }]
  };
}

export function ChatbotWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      text: "Hi! I'm your CONFIT stylist assistant. I can help with style challenges, outfit advice, and fashion questions. How can I assist you today?",
      sender: 'bot',
      timestamp: new Date()
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [apiKey, setApiKey] = useState('');
  const [useGemini, setUseGemini] = useState(geminiService.hasApiKey());
  const router = useRouter();

  useEffect(() => {
    setUseGemini(geminiService.hasApiKey());
  }, []);

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: inputValue,
      sender: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsTyping(true);

    try {
      let response;
      
      if (useGemini && geminiService.hasApiKey()) {
        // Use Gemini API
        const request: GeminiRequest = {
          message: inputValue,
          context: {
            previousMessages: messages.map(msg => ({
              role: msg.sender === 'user' ? 'user' as const : 'assistant' as const,
              content: msg.text
            }))
          }
        };
        
        response = await geminiService.generateResponse(request);
      } else {
        // Use fallback smart responses
        response = getSmartResponse(inputValue);
      }

      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: response.text,
        sender: 'bot',
        timestamp: new Date()
      };

      setMessages(prev => [...prev, botMessage]);
      
      // Store suggestions and actions for the last bot message
      setLastBotResponse(response);
      
    } catch (error) {
      console.error('Error generating response:', error);
      
      // Fallback to smart responses on error
      const fallbackResponse = getSmartResponse(inputValue);
      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: fallbackResponse.text,
        sender: 'bot',
        timestamp: new Date()
      };

      setMessages(prev => [...prev, botMessage]);
      setLastBotResponse(fallbackResponse);
    }
    
    setIsTyping(false);
  };

  const [lastBotResponse, setLastBotResponse] = useState<any>(null);

  const handleSuggestionClick = (suggestion: string) => {
    setInputValue(suggestion);
  };

  const handleActionClick = (action: string) => {
    setIsOpen(false);
    router.push(action);
  };

  const handleApiKeySave = () => {
    if (apiKey.trim()) {
      geminiService.setApiKey(apiKey.trim());
      setUseGemini(true);
      setShowSettings(false);
      setApiKey('');
      
      // Add confirmation message
      const confirmationMessage: Message = {
        id: Date.now().toString(),
        text: "Perfect! Gemini AI is now enabled. I'll provide more intelligent and personalized responses using Google's AI technology.",
        sender: 'bot',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, confirmationMessage]);
    }
  };

  const handleDisableGemini = () => {
    setUseGemini(false);
    setShowSettings(false);
    
    const confirmationMessage: Message = {
      id: Date.now().toString(),
      text: "Gemini AI has been disabled. I'll continue helping you with smart preset responses.",
      sender: 'bot',
      timestamp: new Date()
    };
    setMessages(prev => [...prev, confirmationMessage]);
  };

  return (
    <>
      {/* Floating Button */}
      <motion.button
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.9 }}
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 w-14 h-14 bg-accent text-accent-foreground rounded-full shadow-lg hover:shadow-xl transition-shadow duration-300 flex items-center justify-center z-50"
        aria-label="Open Chatbot"
      >
        <MessageCircle className="h-6 w-6" />
      </motion.button>

      {/* Chat Modal */}
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsOpen(false)}
              className="fixed inset-0 bg-black/50 z-40"
            />

            {/* Chat Window */}
            <motion.div
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 20 }}
              className="fixed bottom-20 right-6 w-80 max-w-[calc(100vw-2rem)] max-h-[600px] z-50"
            >
              <Card className="shadow-2xl h-full flex flex-col">
                <CardHeader className="pb-3 flex-shrink-0">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg flex items-center gap-2">
                      <div className="w-3 h-3 bg-accent rounded-full animate-pulse" />
                      CONFIT Stylist
                      {useGemini && (
                        <Badge variant="outline" className="text-xs">
                          Gemini AI
                        </Badge>
                      )}
                    </CardTitle>
                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setShowSettings(!showSettings)}
                        className="h-8 w-8 p-0"
                      >
                        <Settings className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setIsOpen(false)}
                        className="h-8 w-8 p-0"
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Ask me anything about style and fashion!
                  </p>
                  
                  {/* Settings Panel */}
                  <AnimatePresence>
                    {showSettings && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="border-t pt-3 mt-3"
                      >
                        <div className="space-y-3">
                          <div>
                            <label className="text-sm font-medium">AI Assistant</label>
                            <div className="mt-1 space-y-2">
                              {useGemini ? (
                                <div className="flex items-center justify-between p-2 bg-muted rounded">
                                  <span className="text-sm">Gemini AI Enabled</span>
                                  <Button size="sm" variant="outline" onClick={handleDisableGemini}>
                                    Disable
                                  </Button>
                                </div>
                              ) : (
                                <div className="space-y-2">
                                  <div className="flex gap-2">
                                    <Input
                                      placeholder="Enter Gemini API Key"
                                      value={apiKey}
                                      onChange={(e) => setApiKey(e.target.value)}
                                      type="password"
                                      className="flex-1"
                                    />
                                    <Button size="sm" onClick={handleApiKeySave} disabled={!apiKey.trim()}>
                                      Save
                                    </Button>
                                  </div>
                                  <p className="text-xs text-muted-foreground">
                                    Get your free API key from{' '}
                                    <a 
                                      href="https://makersuite.google.com/app/apikey" 
                                      target="_blank" 
                                      rel="noopener noreferrer"
                                      className="text-accent hover:underline"
                                    >
                                      Google AI Studio
                                    </a>
                                  </p>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </CardHeader>
                
                <CardContent className="flex-1 flex flex-col pt-0 min-h-0">
                  {/* Messages */}
                  <div className="flex-1 overflow-y-auto space-y-3 mb-3 min-h-0 max-h-[350px]">
                    {messages.map((message) => (
                      <motion.div
                        key={message.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                      >
                        <div className={`flex items-start gap-2 max-w-[80%] ${message.sender === 'user' ? 'flex-row-reverse' : ''}`}>
                          <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 ${
                            message.sender === 'user' ? 'bg-accent text-accent-foreground' : 'bg-muted'
                          }`}>
                            {message.sender === 'user' ? <User className="h-3 w-3" /> : <Bot className="h-3 w-3" />}
                          </div>
                          <div className={`p-2 rounded-lg text-sm break-words ${
                            message.sender === 'user' 
                              ? 'bg-accent text-accent-foreground' 
                              : 'bg-muted'
                          }`}>
                            {message.text}
                          </div>
                        </div>
                      </motion.div>
                    ))}
                    
                    {isTyping && (
                      <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="flex justify-start"
                      >
                        <div className="flex items-start gap-2">
                          <div className="w-6 h-6 rounded-full bg-muted flex items-center justify-center">
                            <Bot className="h-3 w-3" />
                          </div>
                          <div className="bg-muted p-2 rounded-lg">
                            <div className="flex gap-1">
                              <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" />
                              <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                              <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                            </div>
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </div>

                  {/* Suggestions and Actions */}
                  {lastBotResponse && !isTyping && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="space-y-2 flex-shrink-0"
                    >
                      {lastBotResponse.suggestions && (
                        <div className="flex flex-wrap gap-1">
                          {lastBotResponse.suggestions.map((suggestion: string, index: number) => (
                            <Badge
                              key={index}
                              variant="outline"
                              className="cursor-pointer hover:bg-accent hover:text-accent-foreground text-xs"
                              onClick={() => handleSuggestionClick(suggestion)}
                            >
                              {suggestion}
                            </Badge>
                          ))}
                        </div>
                      )}
                      
                      {lastBotResponse.actions && (
                        <div className="space-y-1">
                          {lastBotResponse.actions.map((action: { label: string; action: string }, index: number) => (
                            <Button
                              key={index}
                              size="sm"
                              variant="outline"
                              onClick={() => handleActionClick(action.action)}
                              className="w-full justify-start text-left h-auto p-2"
                            >
                              <Sparkles className="h-3 w-3 mr-2" />
                              {action.label}
                            </Button>
                          ))}
                        </div>
                      )}
                    </motion.div>
                  )}

                  {/* Input - Fixed at bottom */}
                  <div className="flex gap-2 mt-3 pt-3 border-t border-border flex-shrink-0">
                    <Input
                      value={inputValue}
                      onChange={(e) => setInputValue(e.target.value)}
                      placeholder="Ask about style, challenges..."
                      onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                      className="flex-1"
                    />
                    <Button
                      size="sm"
                      onClick={handleSendMessage}
                      disabled={!inputValue.trim() || isTyping}
                      className="flex-shrink-0"
                    >
                      <Send className="h-4 w-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
