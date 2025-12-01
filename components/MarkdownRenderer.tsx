import React from 'react';
import ReactMarkdown, { Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MarkdownRendererProps {
  content: string;
  customComponents?: Partial<Components>;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content, customComponents }) => {
  if (!content) return null;

  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        p: ({ children }) => <p className="mb-4 leading-relaxed last:mb-0">{children}</p>,
        ul: ({ children }) => <ul className="list-disc pl-5 mb-4 space-y-2">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal pl-5 mb-4 space-y-2">{children}</ol>,
        li: ({ children }) => <li className="pl-1">{children}</li>,
        h1: ({ children }) => <h1 className="text-2xl font-bold mb-4 mt-6">{children}</h1>,
        h2: ({ children }) => <h2 className="text-xl font-semibold mb-3 mt-5">{children}</h2>,
        h3: ({ children }) => <h3 className="text-lg font-medium mb-2 mt-4">{children}</h3>,
        blockquote: ({ children }) => (
          <blockquote className="border-l-4 border-blue-200 pl-4 italic my-4 text-gray-600 bg-gray-50 py-2 rounded-r">
            {children}
          </blockquote>
        ),
        code: ({ children }) => (
          <code className="bg-gray-100 rounded px-1 py-0.5 text-sm font-mono text-red-600">
            {children}
          </code>
        ),
        ...customComponents, // Merge custom components if provided
      }}
    >
      {content}
    </ReactMarkdown>
  );
};