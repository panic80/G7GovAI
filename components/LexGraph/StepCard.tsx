import React, { useState, useEffect } from 'react';
import { Check, ChevronDown, ChevronUp } from 'lucide-react';
import { StepStatus } from '../../types';
import {
  statusStyles,
  badgeStyles,
  iconStyles,
  textStyles,
  StatusIcon,
  getAnimationClass,
} from '../../stores/utils/statusStyles';

interface StatItem {
  label: string;
  value: string | number;
}

interface StepCardProps {
  stepNumber?: number;
  title: string;
  status: StepStatus;
  summary?: string;
  stats?: StatItem[];
  children?: React.ReactNode;
  autoCollapseDelay?: number;
  icon?: React.ComponentType<{ size?: string | number; className?: string }>;
}

export const StepCard: React.FC<StepCardProps> = ({
  stepNumber,
  title,
  status,
  summary,
  stats,
  children,
  autoCollapseDelay = 2000,
  icon: Icon,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  // Auto-expand when in_progress, auto-collapse after completion
  useEffect(() => {
    if (status === 'in_progress') {
      setIsExpanded(true);
    } else if (status === 'completed') {
      const timer = setTimeout(() => setIsExpanded(false), autoCollapseDelay);
      return () => clearTimeout(timer);
    }
  }, [status, autoCollapseDelay]);

  const hasContent = Boolean(children);

  return (
    <div
      className={`border-2 rounded-xl overflow-hidden transition-all duration-300 ${statusStyles[status]} ${getAnimationClass(status)}`}
    >
      {/* Progress bar for in_progress */}
      {status === 'in_progress' && (
        <div className="h-1 bg-gray-200 overflow-hidden">
          <div className="h-full w-1/2 bg-gradient-to-r from-gov-blue to-gov-accent animate-shimmer"></div>
        </div>
      )}

      {/* Header - Always Visible */}
      <div
        className={`flex items-center justify-between p-3 ${hasContent ? 'cursor-pointer hover:bg-white/50 transition-colors' : ''}`}
        onClick={() => hasContent && setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3">
          {/* Step Number Badge */}
          {stepNumber !== undefined && (
            <div
              className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shadow-sm transition-all duration-300 ${badgeStyles[status]}`}
            >
              {status === 'completed' ? <Check size={14} className="animate-scaleIn" /> : stepNumber}
            </div>
          )}

          {/* Icon + Title */}
          <div className="flex items-center gap-2">
            {Icon && (
              <Icon
                size={16}
                className={`transition-colors ${iconStyles[status]}`}
              />
            )}
            <span
              className={`font-medium text-sm transition-colors ${textStyles[status]}`}
            >
              {title}
            </span>
          </div>

          {/* Status Indicator */}
          <StatusIcon status={status} size={14} />
        </div>

        {/* Right Side: Stats, Summary + Expand Toggle */}
        <div className="flex items-center gap-2">
          {/* Stats display */}
          {stats && stats.length > 0 && (
            <div className="flex gap-2">
              {stats.map((stat, i) => (
                <span key={i} className="text-xs bg-gray-100 px-2 py-0.5 rounded-full text-gray-600">
                  {stat.label}: <span className="font-medium">{stat.value}</span>
                </span>
              ))}
            </div>
          )}
          {!isExpanded && summary && (
            <span className={`text-xs max-w-[180px] truncate font-medium ${
              status === 'completed' ? 'text-green-600 bg-green-100 px-2 py-0.5 rounded-full' : 'text-gray-500'
            }`}>
              {summary}
            </span>
          )}
          {hasContent && (
            <div className="text-gray-400 hover:text-gray-600 transition-colors">
              {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </div>
          )}
        </div>
      </div>

      {/* Expandable Content */}
      {isExpanded && children && (
        <div className="px-3 pb-3 pt-0 text-sm text-gray-600 border-t border-gray-200/50 animate-slideInUp">
          {children}
        </div>
      )}
    </div>
  );
};
