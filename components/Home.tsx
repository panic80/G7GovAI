
import React from 'react';
import { Link } from 'react-router-dom';
import { Search, GitMerge, TrendingUp, Users, ArrowRight, ShieldCheck, FileText, Sparkles } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

// Tailwind gradient classes must be defined statically for purging to work
const accentGradients: Record<string, string> = {
  blue: 'from-blue-50',
  purple: 'from-purple-50',
  indigo: 'from-indigo-50',
  teal: 'from-teal-50'
};

export const Home: React.FC = () => {
  const { t, language } = useLanguage();

  const cards = [
    {
      title: t('nav.govlens'),
      desc: t('nav.govlens.desc'),
      path: '/insights',
      icon: Search,
      color: 'bg-gradient-to-br from-blue-500 to-blue-600',
      problem: 'Problem #1',
      accent: 'blue'
    },
    {
      title: t('nav.lexgraph'),
      desc: t('nav.lexgraph.desc'),
      path: '/rules',
      icon: GitMerge,
      color: 'bg-gradient-to-br from-purple-500 to-purple-600',
      problem: 'Problem #2',
      accent: 'purple'
    },
    {
      title: t('nav.foresight'),
      desc: t('nav.foresight.desc'),
      path: '/plan',
      icon: TrendingUp,
      color: 'bg-gradient-to-br from-indigo-500 to-indigo-600',
      problem: 'Problem #3',
      accent: 'indigo'
    },
    {
      title: t('nav.assist'),
      desc: t('nav.assist.desc'),
      path: '/assist',
      icon: Users,
      color: 'bg-gradient-to-br from-teal-500 to-teal-600',
      problem: 'Problem #4',
      accent: 'teal'
    }
  ];

  return (
    <div className="max-w-7xl mx-auto p-6 md:p-10">
      {/* Hero Section */}
      <div className="bg-white rounded-2xl p-12 shadow-gov-lg border border-gray-200 mb-10 text-center relative overflow-hidden group animate-slideInUp">
        {/* Animated Gradient Top Bar */}
        <div className="absolute top-0 left-0 w-full h-2 bg-gradient-to-r from-gov-blue via-gov-accent to-gov-blue-light animate-gradientShift"></div>

        {/* Dot Pattern Background */}
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: 'radial-gradient(circle, #003366 1px, transparent 1px)',
            backgroundSize: '24px 24px'
          }}
        ></div>

        <div className="relative z-10 max-w-3xl mx-auto">
          {/* Badge with Live Pulse */}
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-blue-50 text-gov-blue text-xs font-bold uppercase tracking-wide mb-6 border border-blue-100 animate-pulseRing">
            <ShieldCheck size={14} className="text-gov-blue" />
            {t('home.badge')}
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
            </span>
          </div>

          {/* Gradient Title */}
          <h1 className="text-4xl md:text-6xl font-extrabold mb-6 tracking-tight leading-tight">
            <span className="gradient-text">
              {t('home.hero.title')}
            </span>
          </h1>

          <p className="text-xl text-gray-600 mb-10 leading-relaxed animate-fadeIn" style={{ animationDelay: '0.2s' }}>
            {t('home.hero.subtitle')}
          </p>

          <div className="flex justify-center gap-4 animate-fadeIn" style={{ animationDelay: '0.3s' }}>
            <Link
              to="/insights"
              className="bg-gov-blue text-white px-8 py-4 rounded-lg font-semibold hover:bg-gov-blue-dark transition-all shadow-gov hover:shadow-gov-lg hover:-translate-y-1 flex items-center gap-2 group/btn"
            >
              {t('home.btn.start')}
              <ArrowRight size={20} className="group-hover/btn:translate-x-1 transition-transform" />
            </Link>
            <Link
              to="/governance"
              className="bg-white text-gov-blue border-2 border-gray-200 px-8 py-4 rounded-lg font-semibold hover:border-gov-blue hover:bg-blue-50 transition-all flex items-center gap-2"
            >
              {t('nav.governance')}
            </Link>
          </div>
        </div>

        {/* Floating Background Elements - decorative only */}
        <div className="absolute -bottom-16 -right-16 opacity-[0.04] transform rotate-12 group-hover:rotate-6 transition-transform duration-1000 animate-float" aria-hidden="true">
          <FileText size={350} />
        </div>
        <div className="absolute -top-16 -left-16 opacity-[0.04] transform -rotate-12 group-hover:-rotate-6 transition-transform duration-1000 animate-float" style={{ animationDelay: '1.5s' }} aria-hidden="true">
          <ShieldCheck size={350} />
        </div>
        <div className="absolute top-1/2 right-8 opacity-[0.03] animate-float" style={{ animationDelay: '0.5s' }} aria-hidden="true">
          <Sparkles size={80} />
        </div>
      </div>

      {/* Module Grid with Staggered Animation */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 stagger-children">
        {cards.map((c) => {
          const Icon = c.icon;
          return (
            <Link
              key={c.path}
              to={c.path}
              className="bg-white rounded-xl p-6 shadow-sm border border-gray-200 hover:border-gov-blue hover:shadow-gov-lg transition-all duration-300 group flex flex-col justify-between h-52 relative overflow-hidden transform hover:-translate-y-2 hover:scale-[1.02]"
            >
              {/* Subtle gradient overlay on hover */}
              <div className={`absolute inset-0 bg-gradient-to-br ${accentGradients[c.accent]} to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300`}></div>

              <div className="relative z-10">
                <div className={`p-3 rounded-xl text-white ${c.color} shadow-lg group-hover:scale-110 group-hover:rotate-3 transition-all duration-300 w-fit`}>
                  <Icon size={24} />
                </div>
              </div>

              <div className="relative z-10">
                <h3 className="text-lg font-bold text-gray-900 group-hover:text-gov-blue transition-colors">
                  {c.title}
                </h3>
                <p className="text-sm text-gray-500 mt-1 line-clamp-2">
                  {c.desc}
                </p>
                <p className="text-xs font-semibold text-gray-400 mt-2 uppercase tracking-wide">
                  {c.problem}
                </p>
              </div>

              {/* Arrow indicator that slides in */}
              <div className="relative z-10 flex items-center justify-between mt-4">
                <div className="text-gov-blue text-xs font-bold uppercase tracking-wider opacity-0 group-hover:opacity-100 transition-all duration-300 flex items-center gap-1 transform -translate-x-2 group-hover:translate-x-0">
                  {t('home.card.launch')}
                </div>
                <div className="w-8 h-8 rounded-full bg-gov-blue/10 flex items-center justify-center opacity-0 group-hover:opacity-100 transform translate-x-4 group-hover:translate-x-0 transition-all duration-300">
                  <ArrowRight size={16} className="text-gov-blue" />
                </div>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
};
