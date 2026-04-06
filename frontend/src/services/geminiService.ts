/**
 * CONFIT Gemini AI Service
 * =========================
 * Integration with Google Gemini API for intelligent fashion recommendations
 * and conversational AI responses.
 */

import { getPublicApiBaseUrl } from '@/lib/env';

interface GeminiResponse {
  text: string;
  suggestions?: string[];
  actions?: { label: string; action: string }[];
}

interface GeminiRequest {
  message: string;
  context?: {
    previousMessages?: Array<{ role: 'user' | 'assistant'; content: string }>;
    userProfile?: {
      preferences?: string[];
      style?: string;
      budget?: string;
    };
  };
}

class GeminiService {
  private backendUrl = `${getPublicApiBaseUrl()}/api/stylist/chat`;

  hasApiKey(): boolean {
    return true;
  }

  /**
   * Generate intelligent response — proxied through the backend to keep API keys server-side.
   */
  async generateResponse(request: GeminiRequest): Promise<GeminiResponse> {
    try {
      const token = localStorage.getItem('confit_token');
      const response = await fetch(this.backendUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          message: request.message,
          context: request.context,
        }),
      });

      if (!response.ok) {
        throw new Error(`Backend stylist error: ${response.status}`);
      }

      const data = await response.json();
      const text: string = data.response || data.text || data.message || '';
      return this.parseResponse(text);
    } catch (error) {
      console.error('Gemini (via backend) error:', error);
      throw error;
    }
  }

  /**
   * Parse backend response to extract suggestions and actions
   */
  private parseResponse(text: string): GeminiResponse {
    const suggestions: string[] = [];
    const actions: { label: string; action: string }[] = [];

    // Extract numbered suggestions
    const numberedMatches = text.match(/\d+\.\s+([^.\n]+)/g);
    if (numberedMatches) {
      suggestions.push(...numberedMatches.map(match => 
        match.replace(/^\d+\.\s+/, '').trim()
      ));
    }

    // Extract bullet point actions
    const bulletMatches = text.match(/•\s+([^.\n]+)/g);
    if (bulletMatches) {
      actions.push(...bulletMatches.map(match => {
        const action = match.replace(/•\s+/, '').trim();
        return {
          label: action,
          action: this.getActionUrl(action)
        };
      }));
    }

    // Clean up the main text by removing suggestions and actions
    let cleanText = text;
    cleanText = cleanText.replace(/\d+\.\s+([^.\n]+)/g, '').trim();
    cleanText = cleanText.replace(/•\s+([^.\n]+)/g, '').trim();

    return {
      text: cleanText,
      suggestions: suggestions.slice(0, 3), // Limit to 3 suggestions
      actions: actions.slice(0, 2) // Limit to 2 actions
    };
  }

  /**
   * Convert action text to appropriate URL
   */
  private getActionUrl(action: string): string {
    const actionLower = action.toLowerCase();
    
    if (actionLower.includes('style quiz') || actionLower.includes('chatbot')) {
      return '/chatbot';
    }
    if (actionLower.includes('style challenge') || actionLower.includes('challenge')) {
      return '/challenges';
    }
    if (actionLower.includes('outfit') || actionLower.includes('build')) {
      return '/outfits';
    }
    if (actionLower.includes('discover') || actionLower.includes('browse') || actionLower.includes('shop')) {
      return '/discover';
    }
    if (actionLower.includes('profile') || actionLower.includes('preferences')) {
      return '/profile';
    }
    if (actionLower.includes('wardrobe')) {
      return '/wardrobe';
    }
    
    return '/chatbot'; // Default fallback
  }

  /**
   * Fallback response when API is unavailable
   */
  getFallbackResponse(message: string): GeminiResponse {
    const lowerMessage = message.toLowerCase();
    
    if (lowerMessage.includes('style challenge')) {
      return {
        text: "Style challenges are fun daily quests to explore your fashion creativity! Each challenge gives you specific constraints to work with, helping you build better outfits and earn points on the leaderboard.",
        suggestions: ["What's today's challenge?", "How do I submit an outfit?", "Tell me about the leaderboard"],
        actions: [{ label: "View Today's Challenge", action: "/challenges" }]
      };
    }
    
    if (lowerMessage.includes('outfit')) {
      return {
        text: "Building great outfits is all about balance! Consider color harmony, proportion, and occasion. I'd love to help you create the perfect look.",
        suggestions: ["Business casual outfit", "Weekend casual look", "Evening elegant style"],
        actions: [{ label: "Outfit Builder", action: "/outfits" }]
      };
    }
    
    if (lowerMessage.includes('color')) {
      return {
        text: "Color theory is key to great style! Complementary colors create contrast, analogous colors create harmony, and neutrals tie everything together.",
        suggestions: ["Color combinations for my skin tone", "Best colors for work", "Seasonal color palettes"],
        actions: []
      };
    }
    
    return {
      text: "I'm here to help with your style journey! I can assist with outfit recommendations, color advice, trend information, and style challenges. What would you like to explore?",
      suggestions: ["Tell me about style challenges", "Help me build an outfit", "Color advice", "Fashion trends"],
      actions: [{ label: "Start Style Quiz", action: "/chatbot" }]
    };
  }
}

// Export singleton instance
export const geminiService = new GeminiService();
export type { GeminiRequest, GeminiResponse };
