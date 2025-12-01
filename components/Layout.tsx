
import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Search, GitMerge, TrendingUp, Users, Menu, Globe, ShieldCheck, Home as HomeIcon, Database, Key, AlertTriangle } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';
import { useApiKey } from '../contexts/ApiKeyContext';
import { Language } from '../types';

interface LayoutProps {
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();
  const { language, setLanguage, t } = useLanguage();
  const { isConfigured, isLoading } = useApiKey();

  const navItems = [
    { path: '/', label: t('nav.home'), icon: HomeIcon, desc: null },
    { path: '/knowledge-base', label: t('nav.knowledgebase'), icon: Database, desc: t('nav.knowledgebase.desc') },
    { path: '/insights', label: t('nav.govlens'), icon: Search, desc: t('nav.govlens.desc') },
    { path: '/rules', label: t('nav.lexgraph'), icon: GitMerge, desc: t('nav.lexgraph.desc') },
    { path: '/plan', label: t('nav.foresight'), icon: TrendingUp, desc: t('nav.foresight.desc') },
    { path: '/assist', label: t('nav.assist'), icon: Users, desc: t('nav.assist.desc') },
    { path: '/governance', label: t('nav.governance'), icon: ShieldCheck, desc: t('nav.governance.desc') },
  ];

  const toggleLanguage = () => {
    setLanguage(language === Language.EN ? Language.FR : Language.EN);
  };

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* Sidebar with enhanced official gradient */}
      <aside className="hidden md:flex flex-col w-72 bg-gradient-to-b from-gov-blue to-[#002244] text-white fixed h-full z-20 shadow-2xl">
        <div className="p-6 border-b border-white/10 flex justify-between items-center">
          <Link to="/">
            <div className="group cursor-pointer">
              <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2 group-hover:opacity-90 transition">
                <span className="bg-white text-gov-blue px-2 rounded shadow-sm">G7</span>
                GovAI
              </h1>
              <p className="text-blue-200 text-xs mt-1 tracking-wide uppercase opacity-70">{t('layout.subtitle')}</p>
            </div>
          </Link>
        </div>

        <nav className="flex-1 p-4 space-y-1.5">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;
            const Icon = item.icon;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`relative flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 group
                  ${isActive
                    ? 'bg-white/15 text-white shadow-inner'
                    : 'text-blue-100 hover:bg-white/10 hover:text-white hover:translate-x-1'
                  }`}
              >
                {/* Active Indicator Bar */}
                {isActive && (
                  <div className="absolute right-0 top-2 bottom-2 w-1 bg-white rounded-l-full animate-slideInLeft" />
                )}

                {/* Icon with scale on active/hover */}
                <div className={`p-1.5 rounded-lg transition-all duration-300 ${
                  isActive ? 'bg-white/20' : 'group-hover:bg-white/10'
                }`}>
                  <Icon
                    size={18}
                    className={`transition-all duration-300 ${
                      isActive ? 'text-white scale-110' : 'text-blue-300 group-hover:text-white group-hover:scale-110'
                    }`}
                  />
                </div>

                <div className="flex-grow">
                  <div className={`font-medium text-sm tracking-wide ${isActive ? 'text-white' : ''}`}>
                    {item.label}
                  </div>
                  {item.desc && (
                    <div className="text-xs text-blue-300/70 font-light truncate max-w-[140px]">
                      {item.desc}
                    </div>
                  )}
                </div>
              </Link>
            );
          })}
        </nav>

        <div className="p-6 border-t border-white/10 bg-black/10 space-y-4">
          <button
            onClick={toggleLanguage}
            className="w-full flex items-center justify-center gap-2 bg-white/10 hover:bg-white/20 py-2.5 rounded-lg text-sm transition-all duration-300 font-semibold tracking-wide hover:scale-[1.02] active:scale-95"
          >
            <Globe size={16} className="transition-transform group-hover:rotate-12" />
            {language === Language.EN ? 'Français' : 'English'}
          </button>

          <div className="flex items-center gap-3 pt-2 group cursor-pointer">
            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-blue-400 to-indigo-500 ring-2 ring-white/30 flex items-center justify-center text-xs font-bold shadow-lg transition-transform group-hover:scale-105">
              AK
            </div>
            <div>
              <p className="text-sm font-medium text-white">{t('layout.user.name')}</p>
              <p className="text-xs text-blue-300/80">{t('layout.user.role')}</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Mobile Header */}
      <header className="md:hidden fixed top-0 w-full bg-gov-blue text-white z-20 p-4 flex justify-between items-center shadow-md">
        <Link to="/" className="font-bold text-xl flex items-center gap-2">
           <span className="bg-white text-gov-blue px-1.5 rounded text-sm">G7</span> GovAI
        </Link>
        <div className="flex items-center gap-4">
          <button onClick={toggleLanguage} className="font-bold text-sm bg-white/10 px-2 py-1 rounded">
            {language === Language.EN ? 'FR' : 'EN'}
          </button>
          <Menu />
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 md:ml-72 pt-16 md:pt-0 transition-all duration-200">
        {/* API Key Required Banner */}
        {!isLoading && !isConfigured && (
          <div className="bg-amber-50 border-b border-amber-200 px-4 py-3">
            <div className="max-w-4xl mx-auto flex items-center gap-3">
              <div className="flex-shrink-0 p-2 bg-amber-100 rounded-full">
                <Key className="w-5 h-5 text-amber-600" />
              </div>
              <div className="flex-1">
                <p className="text-amber-800 font-medium text-sm">
                  {t('governance.noApiKey')}
                </p>
                <p className="text-amber-600 text-xs">
                  {t('governance.noApiKeyDesc')}
                </p>
              </div>
              <Link
                to="/governance"
                className="flex-shrink-0 bg-amber-600 hover:bg-amber-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              >
                {t('governance.configure') || 'Configure'}
              </Link>
            </div>
          </div>
        )}

        <div className="min-h-screen p-4 md:p-0">
          {children}
        </div>
      </main>
    </div>
  );
};
