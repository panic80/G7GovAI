
import React, { createContext, useContext, useState, ReactNode } from 'react';
import { Language } from '../types';
import en from '../locales/en.json';
import fr from '../locales/fr.json';
import de from '../locales/de.json';
import it from '../locales/it.json';
import ja from '../locales/ja.json';

// Re-export Language for convenience
export { Language } from '../types';

type TranslationMap = Record<string, string>;

type Translations = {
  [key in Language]: TranslationMap;
};

// G7 Languages constant for AccessBridge language selection
export const G7_LANGUAGES: { code: Language; name: string; nativeName: string }[] = [
  { code: Language.EN, name: 'English', nativeName: 'English' },
  { code: Language.FR, name: 'French', nativeName: 'Français' },
  { code: Language.DE, name: 'German', nativeName: 'Deutsch' },
  { code: Language.IT, name: 'Italian', nativeName: 'Italiano' },
  { code: Language.JA, name: 'Japanese', nativeName: '日本語' },
];

const translations: Translations = {
  [Language.EN]: en,
  [Language.FR]: fr,
  [Language.DE]: de,
  [Language.IT]: it,
  [Language.JA]: ja,
};

// Export translations for local use in components like AccessBridge
export { translations };

interface LanguageContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: string) => string;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export const LanguageProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [language, setLanguage] = useState<Language>(Language.EN);

  const t = (key: string) => {
    return translations[language][key] || key;
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
};
