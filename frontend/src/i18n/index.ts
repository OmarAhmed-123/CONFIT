/**
 * CONFIT Frontend — Internationalization (i18n) Setup
 * =====================================================
 * Manages translations and language switching.
 */

import ar from './ar.json';
import en from './en.json';

export type Language = 'en' | 'ar';
export type TranslationKeys = typeof en;

const translations: Record<Language, TranslationKeys> = { en, ar };

/**
 * Get translation by key path (supports dot notation like "common.loading")
 */
export function t(key: string, lang: Language = 'en'): string {
  const keys = key.split('.');
  let value: any = translations[lang];

  for (const k of keys) {
    if (value && typeof value === 'object' && k in value) {
      value = value[k];
    } else {
      // Fallback to English if key not found
      if (lang !== 'en') {
        return t(key, 'en');
      }
      return key; // Return the key itself as fallback
    }
  }

  return typeof value === 'string' ? value : key;
}

/**
 * Get nested translation object
 */
export function getTranslations(lang: Language): TranslationKeys {
  return translations[lang];
}

/**
 * Check if language is RTL
 */
export function isRTL(lang: Language): boolean {
  return lang === 'ar';
}

/**
 * Get text direction for language
 */
export function getTextDirection(lang: Language): 'ltr' | 'rtl' {
  return isRTL(lang) ? 'rtl' : 'ltr';
}

export { ar, en };
