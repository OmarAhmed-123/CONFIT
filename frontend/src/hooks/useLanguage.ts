/**
 * CONFIT Frontend — Language Detection Hook
 * ===========================================
 * Detects browser language and manages app-wide language preference.
 * Used for RTL support and API localization.
 */

import { useState, useEffect, useCallback } from "react";

export type Language = "en" | "ar";

interface UseLanguageReturn {
  language: Language;
  isRTL: boolean;
  setLanguage: (lang: Language) => void;
  toggleLanguage: () => void;
}

const STORAGE_KEY = "confit-preferred-language";

/**
 * Detect browser language
 */
function detectBrowserLanguage(): Language {
  if (typeof window === "undefined") return "en";

  // Check navigator.languages
  const languages = navigator.languages || [navigator.language];

  for (const lang of languages) {
    const langCode = lang.toLowerCase().split("-")[0];
    if (langCode === "ar") return "ar";
  }

  // Check navigator.language
  const navLang = navigator.language.toLowerCase();
  if (navLang.startsWith("ar")) return "ar";

  return "en";
}

/**
 * Get stored language preference
 */
function getStoredLanguage(): Language | null {
  if (typeof window === "undefined") return null;

  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "ar" || stored === "en") return stored;
  } catch {
    // LocalStorage not available
  }

  return null;
}

/**
 * Store language preference
 */
function storeLanguage(language: Language): void {
  if (typeof window === "undefined") return;

  try {
    localStorage.setItem(STORAGE_KEY, language);
  } catch {
    // LocalStorage not available
  }
}

/**
 * Hook for managing language preference
 */
export function useLanguage(): UseLanguageReturn {
  const [language, setLanguageState] = useState<Language>("en");
  const [isInitialized, setIsInitialized] = useState(false);

  // Initialize language on mount
  useEffect(() => {
    if (isInitialized) return;

    const stored = getStoredLanguage();
    const detected = stored || detectBrowserLanguage();
    setLanguageState(detected);
    setIsInitialized(true);
  }, [isInitialized]);

  // Update document attributes when language changes
  useEffect(() => {
    if (!isInitialized) return;

    // Update HTML lang and dir attributes
    document.documentElement.lang = language;
    document.documentElement.dir = language === "ar" ? "rtl" : "ltr";

    // Add/remove RTL class for Tailwind
    if (language === "ar") {
      document.body.classList.add("rtl");
    } else {
      document.body.classList.remove("rtl");
    }
  }, [language, isInitialized]);

  const setLanguage = useCallback((lang: Language) => {
    setLanguageState(lang);
    storeLanguage(lang);
  }, []);

  const toggleLanguage = useCallback(() => {
    const newLang = language === "en" ? "ar" : "en";
    setLanguage(newLang);
  }, [language, setLanguage]);

  return {
    language,
    isRTL: language === "ar",
    setLanguage,
    toggleLanguage,
  };
}

/**
 * Get current language (for non-React contexts like services)
 */
export function getCurrentLanguage(): Language {
  if (typeof window === "undefined") return "en";
  const stored = getStoredLanguage();
  return stored || detectBrowserLanguage();
}

/**
 * Check if current language is RTL
 */
export function isRTLLanguage(): boolean {
  return getCurrentLanguage() === "ar";
}
