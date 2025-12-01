'use client';

import React from 'react';
import { LegislativeExcerpt } from '../../types';
import { X, BookOpen, Copy, Check, FileText, Scale } from 'lucide-react';

interface LegislativeExcerptModalProps {
  excerpt: LegislativeExcerpt | null;
  onClose: () => void;
}

export const LegislativeExcerptModal: React.FC<LegislativeExcerptModalProps> = ({ excerpt, onClose }) => {
  const [copied, setCopied] = React.useState(false);

  if (!excerpt) return null;

  const handleCopyCitation = async () => {
    await navigator.clipboard.writeText(`${excerpt.act_name}, ${excerpt.citation}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getConfidenceBadge = () => {
    if (!excerpt.confidence) return null;
    const colors = {
      HIGH: 'bg-green-100 text-green-800 border-green-200',
      MEDIUM: 'bg-yellow-100 text-yellow-800 border-yellow-200',
      LOW: 'bg-gray-100 text-gray-800 border-gray-200',
    };
    return (
      <span className={`px-2 py-1 text-xs font-medium rounded border ${colors[excerpt.confidence]}`}>
        {excerpt.confidence} Confidence
      </span>
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div
        className="bg-white rounded-xl shadow-2xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-indigo-50">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 rounded-lg">
                <Scale className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900">{excerpt.act_name}</h2>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-sm font-mono text-blue-600">{excerpt.citation}</span>
                  {getConfidenceBadge()}
                </div>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1 rounded-full hover:bg-gray-200 transition-colors"
            >
              <X className="w-5 h-5 text-gray-500" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="px-6 py-4 overflow-y-auto max-h-[60vh]">
          {/* Section Title */}
          {excerpt.section_title && (
            <div className="mb-4">
              <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-1">Section</h3>
              <p className="text-base font-medium text-gray-900">{excerpt.section_title}</p>
            </div>
          )}

          {/* Legislative Text */}
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-2">
              <FileText className="w-4 h-4 text-gray-400" />
              <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide">Legislative Text</h3>
            </div>
            <blockquote className="border-l-4 border-blue-400 pl-4 py-2 bg-blue-50/50 rounded-r-lg">
              <p className="text-gray-800 text-sm leading-relaxed italic">
                &ldquo;{excerpt.text}&rdquo;
              </p>
            </blockquote>
          </div>

          {/* Plain Language Explanation */}
          {excerpt.plain_language && (
            <div>
              <div className="flex items-center gap-2 mb-2">
                <BookOpen className="w-4 h-4 text-gray-400" />
                <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide">Plain Language</h3>
              </div>
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <p className="text-gray-800 text-sm leading-relaxed">
                  {excerpt.plain_language}
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex justify-between items-center">
          <button
            onClick={handleCopyCitation}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            {copied ? (
              <>
                <Check className="w-4 h-4 text-green-500" />
                Copied!
              </>
            ) : (
              <>
                <Copy className="w-4 h-4" />
                Copy Citation
              </>
            )}
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default LegislativeExcerptModal;
