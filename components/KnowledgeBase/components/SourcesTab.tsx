import React from 'react';
import { FileText, Database, Loader2, RefreshCw, ExternalLink } from 'lucide-react';
import { useLanguage } from '../../../contexts/LanguageContext';
import { Link } from 'react-router-dom';

interface DocumentSource {
  source_title: string;
  source_id: string;
  doc_type: string;
  category: string;
  themes: string;
  chunk_count: number;
  updated_at: string;
}

interface SourcesTabProps {
  sources: DocumentSource[];
  loading: boolean;
  onRefresh: () => void;
}

const getDocTypeIcon = (docType: string) => {
  switch (docType.toLowerCase()) {
    case 'pdf':
      return <FileText size={16} className="text-red-500" />;
    case 'csv':
    case 'json':
      return <Database size={16} className="text-green-500" />;
    default:
      return <FileText size={16} className="text-blue-500" />;
  }
};

const getCategoryColor = (category: string) => {
  const colors: Record<string, string> = {
    'Policy': 'bg-blue-100 text-blue-800',
    'Legal': 'bg-purple-100 text-purple-800',
    'Guidance': 'bg-green-100 text-green-800',
    'Report': 'bg-yellow-100 text-yellow-800',
    'Dataset': 'bg-teal-100 text-teal-800',
    'Technical': 'bg-gray-100 text-gray-800',
    'Form': 'bg-pink-100 text-pink-800',
  };
  return colors[category] || 'bg-gray-100 text-gray-600';
};

export const SourcesTab: React.FC<SourcesTabProps> = ({
  sources,
  loading,
  onRefresh,
}) => {
  const { t } = useLanguage();

  if (loading) {
    return (
      <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-12 flex flex-col items-center justify-center">
        <Loader2 className="animate-spin text-gov-blue mb-4" size={32} />
        <p className="text-gray-500">Loading sources...</p>
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 flex justify-between items-center">
        <div>
          <h3 className="font-bold text-gray-800">Ingested Sources</h3>
          <p className="text-sm text-gray-500">{sources.length} documents in knowledge base</p>
        </div>
        <button
          onClick={onRefresh}
          className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:text-gov-blue hover:bg-blue-50 rounded-lg transition"
        >
          <RefreshCw size={16} />
          Refresh
        </button>
      </div>

      {/* Empty State */}
      {sources.length === 0 ? (
        <div className="p-12 text-center">
          <Database size={48} className="mx-auto text-gray-300 mb-4" />
          <h4 className="text-lg font-medium text-gray-700 mb-2">No sources ingested yet</h4>
          <p className="text-gray-500 text-sm">
            Upload documents or import from G7 connectors to populate the knowledge base.
          </p>
        </div>
      ) : (
        /* Sources Table */
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-600 text-left">
              <tr>
                <th className="px-6 py-3 font-medium">Source</th>
                <th className="px-6 py-3 font-medium">Type</th>
                <th className="px-6 py-3 font-medium">Category</th>
                <th className="px-6 py-3 font-medium">Themes</th>
                <th className="px-6 py-3 font-medium text-center">Chunks</th>
                <th className="px-6 py-3 font-medium">Updated</th>
                <th className="px-6 py-3 font-medium"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {sources.map((source) => (
                <tr key={source.source_id} className="hover:bg-gray-50 transition">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      {getDocTypeIcon(source.doc_type)}
                      <span className="font-medium text-gray-900 truncate max-w-xs" title={source.source_title}>
                        {source.source_title}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className="uppercase text-xs font-mono text-gray-500">
                      {source.doc_type}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getCategoryColor(source.category)}`}>
                      {source.category}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-gray-500 text-xs truncate max-w-[150px] block" title={source.themes}>
                      {source.themes || '-'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-center">
                    <span className="inline-flex items-center justify-center w-8 h-8 bg-blue-50 text-blue-700 rounded-full text-xs font-bold">
                      {source.chunk_count}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-gray-500 text-xs">
                    {source.updated_at || '-'}
                  </td>
                  <td className="px-6 py-4">
                    <Link
                      to={`/documents/${encodeURIComponent(source.source_id)}`}
                      className="text-gov-blue hover:text-blue-700 flex items-center gap-1 text-xs font-medium"
                    >
                      View <ExternalLink size={12} />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
