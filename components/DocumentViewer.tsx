import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  FileText,
  Calendar,
  Tag,
  Loader2,
  AlertCircle,
  BookOpen,
  Hash,
} from 'lucide-react';
import { CONFIG } from '../config';
import { useLanguage } from '../contexts/LanguageContext';

interface DocumentChunk {
  chunk_id: string;
  content: string;
  section_reference: string;
}

interface DocumentMetadata {
  source_id: string;
  source_title: string;
  doc_type: string;
  category: string;
  themes: string;
  effective_date_start: string;
  effective_date_end?: string | null;
  language: string;
}

interface DocumentResponse {
  metadata: DocumentMetadata;
  chunks: DocumentChunk[];
  total_chunks: number;
}

export const DocumentViewer: React.FC = () => {
  const { docId } = useParams<{ docId: string }>();
  const navigate = useNavigate();
  const { t } = useLanguage();

  const [document, setDocument] = useState<DocumentResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const abortController = new AbortController();

    const fetchDocument = async () => {
      if (!docId) {
        setError('No document ID provided');
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);

        const response = await fetch(
          `${CONFIG.RAG.BASE_URL}/documents/${encodeURIComponent(docId)}`,
          { signal: abortController.signal }
        );

        if (!response.ok) {
          if (response.status === 404) {
            throw new Error('Document not found');
          }
          throw new Error(`Failed to fetch document: ${response.statusText}`);
        }

        const data = await response.json();
        setDocument(data);
      } catch (err) {
        // Ignore abort errors (component unmounted)
        if (err instanceof Error && err.name === 'AbortError') return;
        setError(err instanceof Error ? err.message : 'Failed to load document');
      } finally {
        setLoading(false);
      }
    };

    fetchDocument();

    // Cleanup: abort pending request on unmount
    return () => abortController.abort();
  }, [docId]);

  const handleBack = () => {
    navigate(-1);
  };

  // Format doc type for display
  const formatDocType = (type: string) => {
    return type.charAt(0).toUpperCase() + type.slice(1).replace(/_/g, ' ');
  };

  // Parse themes string into array
  const parseThemes = (themes: string): string[] => {
    if (!themes) return [];
    return themes.split(',').map(t => t.trim()).filter(Boolean);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-gov-blue animate-spin mx-auto mb-4" />
          <p className="text-gray-600">{t('doc.loading')}</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-8">
        <div className="bg-white rounded-xl border border-red-200 p-8 max-w-md text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">{t('doc.errorTitle')}</h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <button
            onClick={handleBack}
            className="inline-flex items-center gap-2 px-4 py-2 bg-gov-blue text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            {t('doc.goBack')}
          </button>
        </div>
      </div>
    );
  }

  if (!document) {
    return null;
  }

  const { metadata, chunks, total_chunks } = document;
  const themes = parseThemes(metadata.themes);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-8 py-4">
          <div className="flex items-center gap-4">
            <button
              onClick={handleBack}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              title="Go back"
            >
              <ArrowLeft className="w-5 h-5 text-gray-600" />
            </button>
            <div className="flex-1 min-w-0">
              <h1 className="text-xl font-bold text-gray-900 truncate">
                {metadata.source_title}
              </h1>
              <div className="flex items-center gap-3 mt-1 text-sm text-gray-500">
                <span className="inline-flex items-center gap-1">
                  <FileText className="w-4 h-4" />
                  {formatDocType(metadata.doc_type)}
                </span>
                {metadata.category && (
                  <span className="bg-gray-100 text-gray-700 px-2 py-0.5 rounded-full text-xs uppercase">
                    {metadata.category}
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-8 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-3">
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
              <div className="p-6 border-b border-gray-100">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                    <BookOpen className="w-5 h-5 text-gov-blue" />
                    {t('doc.content')}
                  </h2>
                  <span className="text-sm text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
                    {total_chunks} {total_chunks !== 1 ? t('doc.chunks') : t('doc.chunk')}
                  </span>
                </div>
              </div>

              <div className="divide-y divide-gray-100">
                {chunks.map((chunk, idx) => (
                  <div key={chunk.chunk_id} className="p-6">
                    {chunk.section_reference && (
                      <div className="flex items-center gap-2 mb-3">
                        <Hash className="w-4 h-4 text-gray-400" />
                        <span className="text-sm font-medium text-gray-500">
                          {chunk.section_reference}
                        </span>
                      </div>
                    )}
                    <div className="prose prose-sm max-w-none text-gray-700 whitespace-pre-wrap">
                      {chunk.content}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 sticky top-24">
              <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider mb-4">
                {t('doc.info')}
              </h3>

              <div className="space-y-4">
                {/* Source ID */}
                <div>
                  <label className="text-xs font-medium text-gray-500 uppercase">{t('doc.sourceId')}</label>
                  <p className="text-sm text-gray-700 font-mono mt-1 break-all">{metadata.source_id}</p>
                </div>

                {/* Effective Dates */}
                {metadata.effective_date_start && (
                  <div>
                    <label className="text-xs font-medium text-gray-500 uppercase flex items-center gap-1">
                      <Calendar className="w-3.5 h-3.5" />
                      {t('doc.effectiveDate')}
                    </label>
                    <p className="text-sm text-gray-700 mt-1">
                      {metadata.effective_date_start}
                      {metadata.effective_date_end && ` - ${metadata.effective_date_end}`}
                    </p>
                  </div>
                )}

                {/* Language */}
                <div>
                  <label className="text-xs font-medium text-gray-500 uppercase">{t('doc.language')}</label>
                  <p className="text-sm text-gray-700 mt-1">
                    {metadata.language === 'en' ? 'English' : metadata.language === 'fr' ? 'Français' : metadata.language}
                  </p>
                </div>

                {/* Themes */}
                {themes.length > 0 && (
                  <div>
                    <label className="text-xs font-medium text-gray-500 uppercase flex items-center gap-1">
                      <Tag className="w-3.5 h-3.5" />
                      {t('doc.themes')}
                    </label>
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {themes.map((theme) => (
                        <span
                          key={theme}
                          className="text-xs bg-blue-50 text-gov-blue px-2 py-1 rounded-full"
                        >
                          {theme}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
