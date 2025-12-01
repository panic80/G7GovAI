import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Search, GitMerge, TrendingUp, Users, Home, Database, ShieldCheck,
  FileText, Command, ArrowRight, Sparkles, Clock, Hash, Globe,
  MessageSquare, Scale, Brain, Upload, Settings, HelpCircle, X,
  ChevronRight, Zap
} from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';
import { Language } from '../types';

// Command types
type CommandCategory = 'navigation' | 'search' | 'action' | 'recent' | 'settings';

interface CommandItem {
  id: string;
  label: string;
  description: string;
  category: CommandCategory;
  icon: React.ComponentType<{ size?: string | number; className?: string }>;
  shortcut?: string;
  keywords?: string[];
  action: () => void;
  color?: string;
}

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

// Smart query detection - determines which module to route to
const detectQueryIntent = (query: string): { module: string; confidence: number } | null => {
  const q = query.toLowerCase();

  // LexGraph patterns (eligibility, rules, requirements)
  const lexGraphPatterns = [
    /\b(eligible|eligibility|qualify|qualification)\b/,
    /\b(am i|can i|do i)\b.*\b(eligible|qualify|apply)\b/,
    /\b(requirements?|criteria|conditions?)\b.*\b(for|to)\b/,
    /\b(immigration|visa|permit|benefits?)\b.*\b(rules?|requirements?)\b/,
    /\b(salary|income|wage)\b.*\b(\d+|threshold)\b/,
  ];

  // GovLens patterns (search, find, information)
  const govLensPatterns = [
    /\b(what|how|where|when|why|who)\b.*\?$/,
    /\b(find|search|look for|show me)\b/,
    /\b(information|info|details|about)\b/,
    /\b(policy|policies|regulation|law|act)\b/,
    /\b(document|documents|guide|guidelines)\b/,
  ];

  // ForesightOps patterns (budget, planning, optimization)
  const foresightPatterns = [
    /\b(budget|allocat|spend|cost)\b/,
    /\b(optimi[zs]e|plan|planning|prioriti[zs]e)\b/,
    /\b(infrastructure|asset|maintenance)\b/,
    /\b(risk|emergency|disaster)\b/,
  ];

  // AccessBridge patterns (help, apply, form, assistance)
  const accessPatterns = [
    /\b(help me|assist|i need)\b/,
    /\b(apply|application|form|submit)\b/,
    /\b(fill out|complete|process)\b/,
    /\b(disability|housing|welfare|support)\b.*\b(benefit|program)\b/,
  ];

  let maxScore = 0;
  let detectedModule = '';

  const checkPatterns = (patterns: RegExp[], module: string) => {
    let score = 0;
    patterns.forEach(p => { if (p.test(q)) score += 1; });
    if (score > maxScore) {
      maxScore = score;
      detectedModule = module;
    }
  };

  checkPatterns(lexGraphPatterns, 'lexgraph');
  checkPatterns(govLensPatterns, 'govlens');
  checkPatterns(foresightPatterns, 'foresight');
  checkPatterns(accessPatterns, 'access');

  if (maxScore > 0) {
    return { module: detectedModule, confidence: Math.min(maxScore / 2, 1) };
  }

  // Default to GovLens for general questions
  if (q.includes('?') || q.split(' ').length > 3) {
    return { module: 'govlens', confidence: 0.5 };
  }

  return null;
};

export const CommandPalette: React.FC<CommandPaletteProps> = ({ isOpen, onClose }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { t, language, setLanguage } = useLanguage();
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  // Navigate with query pre-filled
  const navigateWithQuery = useCallback((path: string, queryParam?: string) => {
    onClose();
    if (queryParam) {
      navigate(`${path}?q=${encodeURIComponent(queryParam)}`);
    } else {
      navigate(path);
    }
  }, [navigate, onClose]);

  // Define all commands
  const allCommands: CommandItem[] = useMemo(() => [
    // Navigation
    {
      id: 'nav-home',
      label: 'Go to Home',
      description: 'Return to the main dashboard',
      category: 'navigation',
      icon: Home,
      shortcut: 'G H',
      keywords: ['home', 'dashboard', 'main'],
      action: () => navigateWithQuery('/'),
      color: 'text-gray-600',
    },
    {
      id: 'nav-govlens',
      label: 'Go to GovLens',
      description: 'Search documents with AI-powered RAG',
      category: 'navigation',
      icon: Search,
      shortcut: 'G S',
      keywords: ['search', 'govlens', 'rag', 'documents', 'find'],
      action: () => navigateWithQuery('/insights'),
      color: 'text-blue-600',
    },
    {
      id: 'nav-lexgraph',
      label: 'Go to LexGraph',
      description: 'Evaluate eligibility rules',
      category: 'navigation',
      icon: GitMerge,
      shortcut: 'G R',
      keywords: ['rules', 'lexgraph', 'eligibility', 'evaluate'],
      action: () => navigateWithQuery('/rules'),
      color: 'text-purple-600',
    },
    {
      id: 'nav-foresight',
      label: 'Go to ForesightOps',
      description: 'Budget optimization and planning',
      category: 'navigation',
      icon: TrendingUp,
      shortcut: 'G P',
      keywords: ['foresight', 'budget', 'plan', 'optimize'],
      action: () => navigateWithQuery('/plan'),
      color: 'text-indigo-600',
    },
    {
      id: 'nav-access',
      label: 'Go to AccessBridge',
      description: 'Citizen assistance wizard',
      category: 'navigation',
      icon: Users,
      shortcut: 'G A',
      keywords: ['access', 'assist', 'help', 'citizen', 'bridge'],
      action: () => navigateWithQuery('/assist'),
      color: 'text-teal-600',
    },
    {
      id: 'nav-kb',
      label: 'Go to Knowledge Base',
      description: 'Manage documents and data sources',
      category: 'navigation',
      icon: Database,
      shortcut: 'G K',
      keywords: ['knowledge', 'database', 'documents', 'upload'],
      action: () => navigateWithQuery('/knowledge-base'),
      color: 'text-orange-600',
    },
    {
      id: 'nav-governance',
      label: 'Go to Governance',
      description: 'View audit logs and model info',
      category: 'navigation',
      icon: ShieldCheck,
      shortcut: 'G G',
      keywords: ['governance', 'audit', 'logs', 'security'],
      action: () => navigateWithQuery('/governance'),
      color: 'text-green-600',
    },

    // Actions
    {
      id: 'action-search',
      label: 'Search Documents',
      description: 'Ask a question to search the knowledge base',
      category: 'action',
      icon: MessageSquare,
      keywords: ['search', 'ask', 'question', 'query'],
      action: () => navigateWithQuery('/insights'),
      color: 'text-blue-600',
    },
    {
      id: 'action-rules',
      label: 'Check Eligibility',
      description: 'Evaluate if a scenario meets requirements',
      category: 'action',
      icon: Scale,
      keywords: ['eligible', 'check', 'qualify', 'rules'],
      action: () => navigateWithQuery('/rules'),
      color: 'text-purple-600',
    },
    {
      id: 'action-optimize',
      label: 'Run Budget Optimization',
      description: 'Optimize resource allocation with AI',
      category: 'action',
      icon: Brain,
      keywords: ['optimize', 'budget', 'allocate', 'plan'],
      action: () => navigateWithQuery('/plan'),
      color: 'text-indigo-600',
    },
    {
      id: 'action-upload',
      label: 'Upload Documents',
      description: 'Add new documents to the knowledge base',
      category: 'action',
      icon: Upload,
      keywords: ['upload', 'add', 'document', 'file'],
      action: () => navigateWithQuery('/knowledge-base'),
      color: 'text-orange-600',
    },

    // Settings
    {
      id: 'settings-language',
      label: language === Language.EN ? 'Switch to French' : 'Switch to English',
      description: language === Language.EN ? 'Passer en français' : 'Change to English',
      category: 'settings',
      icon: Globe,
      shortcut: 'L',
      keywords: ['language', 'french', 'english', 'français', 'translate'],
      action: () => {
        setLanguage(language === Language.EN ? Language.FR : Language.EN);
        onClose();
      },
      color: 'text-gray-600',
    },
  ], [navigateWithQuery, language, setLanguage, onClose]);

  // Smart query detection for direct routing
  const queryIntent = useMemo(() => {
    if (query.length > 10) {
      return detectQueryIntent(query);
    }
    return null;
  }, [query]);

  // Filter commands based on search query
  const filteredCommands = useMemo(() => {
    if (!query.trim()) {
      // Show categorized commands when no query
      return allCommands;
    }

    const q = query.toLowerCase();
    return allCommands.filter(cmd => {
      const searchText = `${cmd.label} ${cmd.description} ${cmd.keywords?.join(' ') || ''}`.toLowerCase();
      return searchText.includes(q) ||
             cmd.keywords?.some(k => k.includes(q)) ||
             cmd.label.toLowerCase().includes(q);
    });
  }, [query, allCommands]);

  // Handle keyboard navigation
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setSelectedIndex(prev =>
            prev < filteredCommands.length - 1 ? prev + 1 : 0
          );
          break;
        case 'ArrowUp':
          e.preventDefault();
          setSelectedIndex(prev =>
            prev > 0 ? prev - 1 : filteredCommands.length - 1
          );
          break;
        case 'Enter':
          e.preventDefault();
          if (queryIntent && query.length > 10) {
            // Smart routing for natural language queries
            const paths: Record<string, string> = {
              govlens: '/insights',
              lexgraph: '/rules',
              foresight: '/plan',
              access: '/assist',
            };
            navigateWithQuery(paths[queryIntent.module] || '/insights', query);
          } else if (filteredCommands[selectedIndex]) {
            filteredCommands[selectedIndex].action();
          }
          break;
        case 'Escape':
          e.preventDefault();
          onClose();
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, selectedIndex, filteredCommands, queryIntent, query, navigateWithQuery, onClose]);

  // Scroll selected item into view
  useEffect(() => {
    const selectedElement = listRef.current?.children[selectedIndex] as HTMLElement;
    selectedElement?.scrollIntoView({ block: 'nearest' });
  }, [selectedIndex]);

  // Reset selection when results change
  useEffect(() => {
    setSelectedIndex(0);
  }, [filteredCommands.length]);

  if (!isOpen) return null;

  // Group commands by category
  const groupedCommands = filteredCommands.reduce((acc, cmd) => {
    if (!acc[cmd.category]) acc[cmd.category] = [];
    acc[cmd.category].push(cmd);
    return acc;
  }, {} as Record<CommandCategory, CommandItem[]>);

  const categoryLabels: Record<CommandCategory, string> = {
    navigation: 'Navigate',
    search: 'Search',
    action: 'Actions',
    recent: 'Recent',
    settings: 'Settings',
  };

  const categoryOrder: CommandCategory[] = ['action', 'navigation', 'settings'];

  // Calculate flat index for keyboard navigation
  let flatIndex = -1;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 animate-fadeIn"
        onClick={onClose}
      />

      {/* Command Palette Modal */}
      <div className="fixed inset-x-4 top-[15%] md:inset-x-auto md:left-1/2 md:-translate-x-1/2 md:w-full md:max-w-2xl z-50 animate-scaleIn">
        <div className="bg-white rounded-2xl shadow-2xl border border-gray-200 overflow-hidden">
          {/* Search Input */}
          <div className="flex items-center gap-3 px-4 py-4 border-b border-gray-100">
            <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-gov-blue to-gov-accent">
              <Command className="w-5 h-5 text-white" />
            </div>
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Type a command or ask a question..."
              className="flex-1 text-lg outline-none placeholder:text-gray-400"
              autoComplete="off"
              spellCheck={false}
            />
            <div className="flex items-center gap-2">
              {query && (
                <button
                  onClick={() => setQuery('')}
                  className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
                >
                  <X size={18} />
                </button>
              )}
              <kbd className="hidden md:inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-gray-500 bg-gray-100 rounded-lg">
                ESC
              </kbd>
            </div>
          </div>

          {/* Smart Query Detection Banner */}
          {queryIntent && query.length > 10 && (
            <div className="px-4 py-3 bg-gradient-to-r from-gov-blue/5 to-gov-accent/5 border-b border-gray-100">
              <div className="flex items-center gap-3">
                <Zap className="w-5 h-5 text-gov-blue" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-800">
                    {queryIntent.module === 'govlens' && 'Search with GovLens'}
                    {queryIntent.module === 'lexgraph' && 'Check eligibility with LexGraph'}
                    {queryIntent.module === 'foresight' && 'Plan with ForesightOps'}
                    {queryIntent.module === 'access' && 'Get help with AccessBridge'}
                  </p>
                  <p className="text-xs text-gray-500">Press Enter to submit your question</p>
                </div>
                <ChevronRight className="w-5 h-5 text-gray-400" />
              </div>
            </div>
          )}

          {/* Results */}
          <div ref={listRef} className="max-h-[60vh] overflow-y-auto py-2">
            {filteredCommands.length === 0 ? (
              <div className="px-4 py-8 text-center">
                <div className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center mx-auto mb-3">
                  <Search className="w-6 h-6 text-gray-400" />
                </div>
                <p className="text-gray-500">No commands found</p>
                <p className="text-xs text-gray-400 mt-1">Try a different search term</p>
              </div>
            ) : (
              categoryOrder.map(category => {
                const commands = groupedCommands[category];
                if (!commands?.length) return null;

                return (
                  <div key={category} className="mb-2">
                    <div className="px-4 py-2">
                      <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
                        {categoryLabels[category]}
                      </span>
                    </div>
                    {commands.map((cmd) => {
                      flatIndex++;
                      const isSelected = flatIndex === selectedIndex;
                      const Icon = cmd.icon;

                      return (
                        <button
                          key={cmd.id}
                          onClick={() => cmd.action()}
                          onMouseEnter={() => setSelectedIndex(flatIndex)}
                          className={`w-full flex items-center gap-3 px-4 py-3 text-left transition-all ${
                            isSelected
                              ? 'bg-gov-blue/10'
                              : 'hover:bg-gray-50'
                          }`}
                        >
                          <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                            isSelected ? 'bg-gov-blue text-white' : 'bg-gray-100'
                          }`}>
                            <Icon size={20} className={isSelected ? 'text-white' : cmd.color || 'text-gray-600'} />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className={`font-medium ${isSelected ? 'text-gov-blue' : 'text-gray-900'}`}>
                                {cmd.label}
                              </span>
                              {cmd.shortcut && (
                                <kbd className="hidden md:inline-flex px-1.5 py-0.5 text-[10px] font-mono text-gray-400 bg-gray-100 rounded">
                                  {cmd.shortcut}
                                </kbd>
                              )}
                            </div>
                            <p className="text-sm text-gray-500 truncate">{cmd.description}</p>
                          </div>
                          <ArrowRight size={16} className={`${isSelected ? 'text-gov-blue' : 'text-gray-300'} transition-transform ${isSelected ? 'translate-x-0' : '-translate-x-2 opacity-0'}`} />
                        </button>
                      );
                    })}
                  </div>
                );
              })
            )}
          </div>

          {/* Footer */}
          <div className="px-4 py-3 border-t border-gray-100 bg-gray-50 flex items-center justify-between text-xs text-gray-500">
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1">
                <kbd className="px-1.5 py-0.5 bg-white rounded border border-gray-200">↑</kbd>
                <kbd className="px-1.5 py-0.5 bg-white rounded border border-gray-200">↓</kbd>
                <span>to navigate</span>
              </span>
              <span className="flex items-center gap-1">
                <kbd className="px-1.5 py-0.5 bg-white rounded border border-gray-200">↵</kbd>
                <span>to select</span>
              </span>
            </div>
            <div className="flex items-center gap-1">
              <Sparkles size={12} className="text-gov-blue" />
              <span>Powered by GovAI</span>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

// Hook for managing Command Palette state
export const useCommandPalette = () => {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd+K (Mac) or Ctrl+K (Windows/Linux)
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen(prev => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return {
    isOpen,
    open: () => setIsOpen(true),
    close: () => setIsOpen(false),
    toggle: () => setIsOpen(prev => !prev),
  };
};
