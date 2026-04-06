/**
 * CONFIT Frontend - MUSE Chat Component
 * AI-powered virtual stylist chat interface
 */

'use client';

import React, { useState, useRef, useEffect } from 'react';
import { useMuse } from '@/hooks/useMuse';
import { 
  MessageCircle, Send, Loader2, Sparkles, 
  ShoppingBag, ChevronRight, X, RefreshCw 
} from 'lucide-react';

interface MuseChatProps {
  language?: 'en' | 'ar';
  onClose?: () => void;
  embedded?: boolean;
}

export function MuseChat({ language = 'en', onClose, embedded = false }: MuseChatProps) {
  const {
    messages,
    isLoading,
    error,
    currentOutfits,
    followUpQuestions,
    sendMessage,
    clearSession,
  } = useMuse({ language });

  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    await sendMessage(input.trim());
    setInput('');
    inputRef.current?.focus();
  };

  const handleFollowUp = (question: string) => {
    sendMessage(question);
  };

  return (
    <div className={`flex flex-col bg-white ${embedded ? '' : 'rounded-2xl shadow-xl max-w-md mx-auto'}`}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b bg-gradient-to-r from-purple-600 to-pink-500 text-white rounded-t-2xl">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h2 className="font-semibold">MUSE</h2>
            <p className="text-xs text-white/80">
              {language === 'ar' ? 'Your AI Stylist' : 'Your AI Stylist'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={clearSession}
            className="p-2 hover:bg-white/20 rounded-full transition-colors"
            title="New conversation"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          {onClose && (
            <button
              onClick={onClose}
              className="p-2 hover:bg-white/20 rounded-full transition-colors"
              title="Close chat"
              aria-label="Close chat"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-[300px] max-h-[400px]">
        {messages.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            <MessageCircle className="w-12 h-12 mx-auto mb-3 text-gray-300" />
            <p className="text-sm">
              {language === 'ar' 
                ? 'Ask me about styling, outfits, or fashion advice!'
                : 'Ask me about styling, outfits, or fashion advice!'}
            </p>
            <p className="text-xs mt-2 text-gray-400">
              Try: "What should I wear to a wedding?"
            </p>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-2 ${
                msg.role === 'user'
                  ? 'bg-purple-600 text-white rounded-br-md'
                  : 'bg-gray-100 text-gray-800 rounded-bl-md'
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-2xl rounded-bl-md px-4 py-2">
              <Loader2 className="w-4 h-4 animate-spin text-purple-600" />
            </div>
          </div>
        )}

        {error && (
          <div className="text-center py-2">
            <p className="text-sm text-red-500">{error}</p>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Outfit Recommendations */}
      {currentOutfits.length > 0 && (
        <div className="border-t p-4 bg-gray-50">
          <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <ShoppingBag className="w-4 h-4" />
            Recommended Outfits
          </h3>
          <div className="space-y-3">
            {currentOutfits.map((outfit) => (
              <div
                key={outfit.outfit_id}
                className="bg-white rounded-lg p-3 shadow-sm border"
              >
                <p className="font-medium text-sm">{outfit.title}</p>
                <p className="text-xs text-gray-500 mt-1">
                  {outfit.items.length} items · ${outfit.total_price.toFixed(2)}
                </p>
                {outfit.styling_tips.length > 0 && (
                  <p className="text-xs text-purple-600 mt-2">
                    Tip: {outfit.styling_tips[0]}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Follow-up Questions */}
      {followUpQuestions.length > 0 && (
        <div className="border-t p-3 bg-gray-50">
          <p className="text-xs text-gray-500 mb-2">Quick questions:</p>
          <div className="flex flex-wrap gap-2">
            {followUpQuestions.slice(0, 3).map((q, idx) => (
              <button
                key={idx}
                onClick={() => handleFollowUp(q)}
                className="text-xs bg-white border rounded-full px-3 py-1 hover:bg-purple-50 hover:border-purple-300 transition-colors"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t">
        <div className="flex items-center gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={language === 'ar' ? 'Ask MUSE...' : 'Ask MUSE...'}
            className="flex-1 border rounded-full px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="p-2 bg-purple-600 text-white rounded-full hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            title="Send message"
            aria-label="Send message"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </form>
    </div>
  );
}

export default MuseChat;
