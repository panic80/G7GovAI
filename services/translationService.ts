import { CONFIG } from '../config';

interface TranslationCache {
  [langCode: string]: {
    [key: string]: string;
  };
}

// In-memory cache for current session
const memoryCache: TranslationCache = {};

// Storage key for localStorage persistence
const STORAGE_KEY = 'govai-translations';

// Common language codes with display names
export const SUPPORTED_LANGUAGES = {
  en: 'English',
  fr: 'Français',
  es: 'Español',
  zh: '中文',
  ar: 'العربية',
  pa: 'ਪੰਜਾਬੀ',
  tl: 'Tagalog',
  hi: 'हिन्दी',
  ko: '한국어',
  vi: 'Tiếng Việt',
  pt: 'Português',
  de: 'Deutsch',
  it: 'Italiano',
  ja: '日本語',
  ru: 'Русский',
} as const;

export type LanguageCode = keyof typeof SUPPORTED_LANGUAGES;

/**
 * Load cached translations from localStorage
 */
function loadFromStorage(): TranslationCache {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return JSON.parse(stored);
    }
  } catch (e) {
    console.warn('Failed to load translations from storage:', e);
  }
  return {};
}

/**
 * Save translations to localStorage
 */
function saveToStorage(cache: TranslationCache): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(cache));
  } catch (e) {
    console.warn('Failed to save translations to storage:', e);
  }
}

/**
 * Initialize cache from localStorage on module load
 */
const persistedCache = loadFromStorage();
Object.assign(memoryCache, persistedCache);

/**
 * Get a cached translation if available
 */
export function getCachedTranslation(langCode: string, key: string): string | null {
  return memoryCache[langCode]?.[key] || null;
}

/**
 * Store a translation in cache
 */
export function cacheTranslation(langCode: string, key: string, value: string): void {
  if (!memoryCache[langCode]) {
    memoryCache[langCode] = {};
  }
  memoryCache[langCode][key] = value;
  saveToStorage(memoryCache);
}

/**
 * Batch translate multiple texts via backend API
 */
export async function translateTexts(
  texts: string[],
  targetLanguage: string,
  sourceLanguage: string = 'en'
): Promise<Record<string, string>> {
  // Check cache first
  const uncachedTexts: string[] = [];
  const results: Record<string, string> = {};

  for (const text of texts) {
    const cached = getCachedTranslation(targetLanguage, text);
    if (cached) {
      results[text] = cached;
    } else {
      uncachedTexts.push(text);
    }
  }

  // If all texts were cached, return immediately
  if (uncachedTexts.length === 0) {
    return results;
  }

  // Call backend translation endpoint
  try {
    const response = await fetch(`${CONFIG.RAG.BASE_URL}/translate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        texts: uncachedTexts,
        target_language: targetLanguage,
        source_language: sourceLanguage,
      }),
    });

    if (!response.ok) {
      throw new Error(`Translation failed: ${response.status}`);
    }

    const data = await response.json();

    // Cache and return results
    for (const [original, translated] of Object.entries(data.translations as Record<string, string>)) {
      cacheTranslation(targetLanguage, original, translated);
      results[original] = translated;
    }

    return results;
  } catch (error) {
    console.error('Translation error:', error);
    // Return originals for failed translations
    for (const text of uncachedTexts) {
      results[text] = text;
    }
    return results;
  }
}

/**
 * Translate a single text
 */
export async function translateText(
  text: string,
  targetLanguage: string,
  sourceLanguage: string = 'en'
): Promise<string> {
  const results = await translateTexts([text], targetLanguage, sourceLanguage);
  return results[text] || text;
}

/**
 * Clear all cached translations
 */
export function clearTranslationCache(): void {
  Object.keys(memoryCache).forEach(key => delete memoryCache[key]);
  localStorage.removeItem(STORAGE_KEY);
}

/**
 * Get all cached translations for a language
 */
export function getCachedTranslationsForLanguage(langCode: string): Record<string, string> {
  return memoryCache[langCode] || {};
}

export default {
  translateTexts,
  translateText,
  getCachedTranslation,
  cacheTranslation,
  clearTranslationCache,
  SUPPORTED_LANGUAGES,
};
