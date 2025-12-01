import React, { useState } from 'react';
import { Download, FileCheck, Eye, EyeOff, CheckCircle2, AlertTriangle, Copy, Check } from 'lucide-react';
import { Language } from '../../../contexts/LanguageContext';
import { COPY_FEEDBACK_MS } from '../../../constants';

interface FieldMapping {
  [fieldName: string]: {
    value: string;
    source?: string;
    confidence?: number;
  };
}

interface FormPreviewProps {
  filledPdfBase64: string | null;
  fieldMapping: FieldMapping;
  fieldsFilled: number;
  unmappedFields: string[];
  unusedData: string[];
  formName: string;
  t: (key: string) => string;
  language: Language;
}

export const FormPreview: React.FC<FormPreviewProps> = ({
  filledPdfBase64,
  fieldMapping,
  fieldsFilled,
  unmappedFields,
  unusedData,
  formName,
  t,
  language,
}) => {
  const [showMapping, setShowMapping] = useState(true);
  const [copied, setCopied] = useState(false);

  const handleDownload = () => {
    if (!filledPdfBase64) return;

    // Create blob from base64
    const byteCharacters = atob(filledPdfBase64);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    const blob = new Blob([byteArray], { type: 'application/pdf' });

    // Create download link
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `filled_${formName.replace(/\s+/g, '_')}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleCopyMapping = () => {
    const mappingText = Object.entries(fieldMapping)
      .map(([field, data]: [string, { value: string; source?: string; confidence?: number }]) => `${field}: ${data.value}`)
      .join('\n');
    navigator.clipboard.writeText(mappingText);
    setCopied(true);
    setTimeout(() => setCopied(false), COPY_FEEDBACK_MS);
  };

  if (!filledPdfBase64) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-gray-500">
        <FileCheck className="w-12 h-12 mb-4 opacity-50" />
        <p>
          {language === 'fr'
            ? 'Le formulaire rempli apparaîtra ici'
            : 'Filled form will appear here'}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <CheckCircle2 className="w-6 h-6 text-green-500" />
          <div>
            <h3 className="font-semibold text-gray-900">{formName}</h3>
            <p className="text-sm text-gray-500">
              {fieldsFilled} {language === 'fr' ? 'champs remplis' : 'fields filled'}
            </p>
          </div>
        </div>
        <button
          onClick={handleDownload}
          className="flex items-center gap-2 px-4 py-2 bg-gov-blue text-white rounded-lg hover:bg-blue-800 transition focus:ring-4 focus:ring-gov-accent focus:ring-offset-2 focus:outline-none"
        >
          <Download className="w-4 h-4" />
          {language === 'fr' ? 'Télécharger PDF' : 'Download PDF'}
        </button>
      </div>

      {/* Toggle Mapping View */}
      <button
        onClick={() => setShowMapping(!showMapping)}
        className="flex items-center gap-2 text-sm text-gov-blue hover:underline"
      >
        {showMapping ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
        {showMapping
          ? (language === 'fr' ? 'Masquer le mapping' : 'Hide field mapping')
          : (language === 'fr' ? 'Afficher le mapping' : 'Show field mapping')}
      </button>

      {/* Field Mapping Table */}
      {showMapping && (
        <div className="border border-gray-200 rounded-lg overflow-hidden">
          <div className="bg-gray-50 px-4 py-2 flex items-center justify-between border-b">
            <h4 className="font-medium text-gray-700">
              {language === 'fr' ? 'Champs remplis' : 'Filled Fields'}
            </h4>
            <button
              onClick={handleCopyMapping}
              className="p-1 text-gray-500 hover:text-gray-700"
              aria-label={language === 'fr' ? 'Copier' : 'Copy'}
            >
              {copied ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
            </button>
          </div>
          <div className="max-h-64 overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="text-left px-4 py-2 text-gray-600">
                    {language === 'fr' ? 'Champ' : 'Field'}
                  </th>
                  <th className="text-left px-4 py-2 text-gray-600">
                    {language === 'fr' ? 'Valeur' : 'Value'}
                  </th>
                  <th className="text-center px-4 py-2 text-gray-600">
                    {language === 'fr' ? 'Confiance' : 'Confidence'}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {Object.entries(fieldMapping).map(([fieldName, data]: [string, { value: string; source?: string; confidence?: number }], idx) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className="px-4 py-2 text-gray-700 font-mono text-xs">
                      {fieldName.split('.').pop()?.replace(/\[\d+\]/g, '') || fieldName}
                    </td>
                    <td className="px-4 py-2 text-gray-900">
                      {data.value}
                    </td>
                    <td className="px-4 py-2 text-center">
                      {data.confidence !== undefined && (
                        <span className={`px-2 py-0.5 rounded text-xs ${
                          data.confidence > 0.8
                            ? 'bg-green-100 text-green-700'
                            : 'bg-yellow-100 text-yellow-700'
                        }`}>
                          {Math.round(data.confidence * 100)}%
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Unmapped Fields Warning */}
      {unmappedFields.length > 0 && (
        <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="font-medium text-yellow-800">
                {language === 'fr' ? 'Champs non remplis' : 'Unfilled Fields'}
              </h4>
              <p className="text-sm text-yellow-700 mt-1">
                {language === 'fr'
                  ? 'Ces champs nécessitent des informations supplémentaires:'
                  : 'These fields require additional information:'}
              </p>
              <div className="flex flex-wrap gap-2 mt-2">
                {unmappedFields.slice(0, 8).map((field, idx) => (
                  <span key={idx} className="text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded">
                    {field.split('.').pop()?.replace(/\[\d+\]/g, '') || field}
                  </span>
                ))}
                {unmappedFields.length > 8 && (
                  <span className="text-xs text-yellow-700">
                    +{unmappedFields.length - 8} {language === 'fr' ? 'autres' : 'more'}
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* PDF Preview (iframe) */}
      <div className="border border-gray-200 rounded-lg overflow-hidden">
        <div className="bg-gray-50 px-4 py-2 border-b">
          <h4 className="font-medium text-gray-700">
            {language === 'fr' ? 'Aperçu du formulaire' : 'Form Preview'}
          </h4>
        </div>
        <div className="h-96 bg-gray-100">
          <iframe
            src={`data:application/pdf;base64,${filledPdfBase64}`}
            className="w-full h-full"
            title={language === 'fr' ? 'Aperçu du PDF' : 'PDF Preview'}
          />
        </div>
      </div>
    </div>
  );
};
