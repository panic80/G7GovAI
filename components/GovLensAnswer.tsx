import React from 'react';
import { FileText, CheckCircle, AlertCircle, Volume2, StopCircle } from 'lucide-react';
import { RagResponse } from '../types';
import { useLanguage } from '../contexts/LanguageContext';
import { useSpeech } from '../hooks/useSpeech';
import { applyDynamicHighlighting } from './highlightRules';
import { MarkdownRenderer } from './MarkdownRenderer';

// Simple citation badge (click to scroll)
const CitationBadge: React.FC<{
  id: string;
  onCitationClick?: (num: number) => void;
}> = ({ id, onCitationClick }) => {
  return (
    <button
      type="button"
      className="inline-flex items-center justify-center w-5 h-5 text-[10px] font-bold rounded-full
        transition-all duration-150 cursor-pointer align-super mx-0.5
        bg-blue-100 text-gov-blue hover:bg-gov-blue hover:text-white"
      onClick={() => onCitationClick?.(parseInt(id))}
    >
      {id}
    </button>
  );
};

// Component to render text with inline citations
const TextWithCitations: React.FC<{
  text: string;
  onCitationClick?: (num: number) => void;
}> = ({ text, onCitationClick }) => {
  // Split text on citation patterns [1], [2], etc.
  const parts = text.split(/(\[\d+\])/g);

  return (
    <>
      {parts.map((part, index) => {
        const citationMatch = part.match(/^\[(\d+)\]$/);
        if (citationMatch) {
          return (
            <CitationBadge
              key={index}
              id={citationMatch[1]}
              onCitationClick={onCitationClick}
            />
          );
        }
        return <span key={index}>{part}</span>;
      })}
    </>
  );
};

// Shared function to recursively process nodes and handle citations
const createProcessNode = (
  onCitationClick?: (num: number) => void,
  keyPrefix: string = 'node'
) => {
  const processNode = (node: React.ReactNode): React.ReactNode => {
    if (typeof node === 'string') {
      if (/\[\d+\]/.test(node)) {
        return <TextWithCitations text={node} onCitationClick={onCitationClick} />;
      }
      return node;
    }
    if (Array.isArray(node)) {
      return node.map((child, i) => (
        <React.Fragment key={`${keyPrefix}-${i}`}>{processNode(child)}</React.Fragment>
      ));
    }
    if (React.isValidElement(node)) {
      const element = node as React.ReactElement<{ children?: React.ReactNode }>;
      if (element.props?.children) {
        return React.cloneElement(element, {
          ...element.props,
          children: processNode(element.props.children),
        });
      }
    }
    return node;
  };
  return processNode;
};

// Custom markdown components that handle citations
const createMarkdownComponents = (onCitationClick?: (num: number) => void) => {
  const processNode = createProcessNode(onCitationClick);

  return {
    // Override paragraph to process citations
    p: ({ children }: { children?: React.ReactNode }) => (
      <p className="mb-4 leading-relaxed last:mb-0">{processNode(children)}</p>
    ),
    // Override list items to process citations
    li: ({ children }: { children?: React.ReactNode }) => (
      <li className="pl-1">{processNode(children)}</li>
    ),
  };
};

interface GovLensAnswerProps {
  result: RagResponse;
  onCitationClick?: (citationNumber: number) => void;
}

export const GovLensAnswer: React.FC<GovLensAnswerProps> = ({ result, onCitationClick }) => {
  const { language, t } = useLanguage();
  const { speaking, loading: audioLoading, speak } = useSpeech();

  const handleSpeak = () => {
    if (result?.answer) {
      speak(result.answer, language);
    }
  };

  // Apply highlighting but don't convert citations to links
  const processText = (text: string) => {
    if (!text) return "";
    return applyDynamicHighlighting(text);
  };

  // Create custom components for markdown rendering
  const customComponents = createMarkdownComponents(onCitationClick);

  return (
    <div className="bg-white p-6 rounded-xl shadow-gov border border-gray-200 animate-fadeIn">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
          <div className="p-2 rounded-lg bg-gov-blue/10">
            <FileText className="w-5 h-5 text-gov-blue" />
          </div>
          {t('govlens.summary')}
        </h2>
        <div className="flex items-center gap-2">
          {/* TTS Button */}
          <button
            onClick={handleSpeak}
            disabled={audioLoading}
            className={`flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium transition
              ${speaking
                ? 'bg-red-100 text-red-700 hover:bg-red-200'
                : 'bg-blue-50 text-gov-blue hover:bg-blue-100'
              }`}
          >
            {audioLoading ? (
              <div className="animate-spin h-4 w-4 border-2 border-current border-t-transparent rounded-full"/>
            ) : (
              speaking ? <StopCircle size={16} /> : <Volume2 size={16} />
            )}
            {speaking ? t('govlens.stop') : t('govlens.listen')}
          </button>

          <span className={`px-3 py-1 rounded-full text-sm font-medium flex items-center gap-1
            ${result.confidence > 0.7 ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}`}>
            {result.confidence > 0.7 ? <CheckCircle size={14}/> : <AlertCircle size={14}/>}
            {t('govlens.confidence')}: {(result.confidence * 100).toFixed(0)}%
          </span>
        </div>
      </div>

      {/* Metadata Badges */}
      {(result.categories?.length || result.aggregated_themes?.length) && (
        <div className="flex flex-wrap gap-2 mb-4 pb-4 border-b border-gray-100">
          {result.categories?.map((cat) => (
            <span key={`cat-${cat}`} className="px-2 py-0.5 rounded text-xs font-semibold bg-blue-100 text-blue-800 uppercase tracking-wide">
              {cat}
            </span>
          ))}
          {result.aggregated_themes?.map((theme) => (
            <span key={`theme-${theme}`} className="px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700">
              {theme}
            </span>
          ))}
        </div>
      )}

      {result.abstained ? (
        <div className="p-4 bg-gray-50 text-gray-600 italic rounded">
          {t('govlens.abstained')}
        </div>
      ) : (
        <div className="text-gray-800">
          <MarkdownRenderer
            content={processText(result.answer)}
            customComponents={customComponents}
          />

          {result.bullets && result.bullets.length > 0 && (
            <div className="mt-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-2 uppercase tracking-wider">Key Points</h3>
              <ul className="space-y-2">
                {result.bullets.map((bullet, idx) => (
                  <li key={`bullet-${idx}-${bullet.slice(0, 20)}`} className="flex items-start gap-2 text-gray-700 text-sm">
                    <span className="block w-1.5 h-1.5 mt-1.5 rounded-full bg-gov-blue shrink-0" />
                    <div className="flex-1 [&>p]:mb-0 [&>p]:leading-normal">
                      <MarkdownRenderer
                        content={processText(bullet)}
                        customComponents={customComponents}
                      />
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
