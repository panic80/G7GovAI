import React, { useState, useRef } from 'react';
import { FileText, Upload, X, CheckCircle2, Loader2, AlertCircle } from 'lucide-react';
import { Language } from '../../../contexts/LanguageContext';
import { CONFIG } from '../../../config';

interface FormField {
  name: string;
  type: string;
  label: string;
  options?: string[];
  required: boolean;
}

interface FormFieldGroup {
  group_name: string;
  group_label: string;
  group_type: 'radio' | 'checkbox' | 'dropdown';
  options: Array<{ name: string; label: string }>;
  required: boolean;
  page?: number;
}

interface FormUploadProps {
  onFormUploaded: (formData: {
    pdfBase64: string;
    formName: string;
    fields: FormField[];
    field_groups?: FormFieldGroup[];
  }) => void;
  onClear: () => void;
  uploadedForm: {
    pdfBase64: string;
    formName: string;
    fields: FormField[];
    field_groups?: FormFieldGroup[];
  } | null;
  language: Language;
  t: (key: string) => string;
}

export const FormUpload: React.FC<FormUploadProps> = ({
  onFormUploaded,
  onClear,
  uploadedForm,
  language,
  t,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const processFile = async (file: File) => {
    setError(null);
    setIsProcessing(true);

    try {
      // Validate file type
      if (!file.type.includes('pdf')) {
        throw new Error(language === 'fr'
          ? 'Veuillez télécharger un fichier PDF'
          : 'Please upload a PDF file');
      }

      // Validate file size (max 10MB)
      if (file.size > 10 * 1024 * 1024) {
        throw new Error(language === 'fr'
          ? 'Le fichier est trop volumineux (max 10 Mo)'
          : 'File is too large (max 10 MB)');
      }

      // Convert to base64
      const reader = new FileReader();
      const base64Promise = new Promise<string>((resolve, reject) => {
        reader.onloadend = () => {
          const base64 = (reader.result as string).split(',')[1];
          resolve(base64);
        };
        reader.onerror = reject;
      });
      reader.readAsDataURL(file);
      const pdfBase64 = await base64Promise;

      // Send to backend to extract fields
      const response = await fetch(`${CONFIG.RAG.BASE_URL}/form/extract-fields`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          pdf_base64: pdfBase64,
          language: language
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to extract form fields');
      }

      const data = await response.json();

      if (data.field_count === 0) {
        throw new Error(language === 'fr'
          ? 'Ce PDF ne contient pas de champs de formulaire remplissables'
          : 'This PDF does not contain any fillable form fields');
      }

      onFormUploaded({
        pdfBase64,
        formName: data.form_name || file.name,
        fields: data.fields,
        field_groups: data.field_groups || []  // Include grouped fields
      });

    } catch (err) {
      if (import.meta.env.DEV) console.error('Form upload error:', err);
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      processFile(e.target.files[0]);
    }
  };

  // If form is already uploaded, show summary
  if (uploadedForm) {
    const totalFields = uploadedForm.fields.length + (uploadedForm.field_groups?.length || 0);
    const groupCount = uploadedForm.field_groups?.length || 0;

    return (
      <div className="border border-green-200 bg-green-50 rounded-lg p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="w-6 h-6 text-green-600" />
            <div>
              <p className="font-medium text-green-900">{uploadedForm.formName}</p>
              <p className="text-sm text-green-700">
                {totalFields} {language === 'fr' ? 'champs détectés' : 'fields detected'}
                {groupCount > 0 && (
                  <span className="ml-1 text-green-600">
                    ({groupCount} {language === 'fr' ? 'groupes' : 'groups'})
                  </span>
                )}
              </p>
            </div>
          </div>
          <button
            onClick={onClear}
            className="p-2 text-green-600 hover:text-green-800 hover:bg-green-100 rounded-lg transition"
            aria-label={language === 'fr' ? 'Supprimer le formulaire' : 'Remove form'}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Field preview */}
        <div className="mt-4">
          <p className="text-sm font-medium text-green-800 mb-2">
            {language === 'fr' ? 'Champs du formulaire:' : 'Form fields:'}
          </p>
          <div className="flex flex-wrap gap-2 max-h-24 overflow-y-auto">
            {/* Regular fields */}
            {uploadedForm.fields.slice(0, 8).map((field, idx) => (
              <span
                key={`field-${idx}`}
                className="inline-flex items-center px-2 py-1 text-xs bg-green-100 text-green-800 rounded"
              >
                {field.label}
                {field.required && <span className="ml-1 text-red-500">*</span>}
              </span>
            ))}
            {/* Grouped fields (with icon indicating group type) */}
            {uploadedForm.field_groups?.slice(0, 4).map((group, idx) => (
              <span
                key={`group-${idx}`}
                className="inline-flex items-center px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded"
                title={`${group.group_type}: ${group.options.length} options`}
              >
                {group.group_type === 'checkbox' ? '☑️' : group.group_type === 'radio' ? '⭕' : '📋'} {group.group_label}
                {group.required && <span className="ml-1 text-red-500">*</span>}
              </span>
            ))}
            {totalFields > 12 && (
              <span className="text-xs text-green-600">
                +{totalFields - 12} {language === 'fr' ? 'autres' : 'more'}
              </span>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Drop zone */}
      <button
        type="button"
        onClick={() => fileInputRef.current?.click()}
        onDrop={handleDrop}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        disabled={isProcessing}
        className={`
          w-full border-2 border-dashed rounded-lg p-6
          flex flex-col items-center justify-center gap-3
          transition-colors cursor-pointer
          focus:ring-4 focus:ring-gov-accent focus:ring-offset-2 focus:outline-none
          ${isDragging ? 'border-gov-blue bg-gov-blue/5' : 'border-gray-300 hover:border-gray-400'}
          ${isProcessing ? 'opacity-50 cursor-not-allowed' : ''}
        `}
        aria-label={language === 'fr'
          ? 'Télécharger un formulaire PDF à remplir'
          : 'Upload a fillable PDF form'}
      >
        {isProcessing ? (
          <>
            <Loader2 className="w-10 h-10 text-gov-blue animate-spin" />
            <p className="text-gray-600">
              {language === 'fr' ? 'Analyse du formulaire...' : 'Analyzing form...'}
            </p>
          </>
        ) : (
          <>
            <div className="flex items-center gap-2">
              <FileText className={`w-10 h-10 ${isDragging ? 'text-gov-blue' : 'text-gray-400'}`} />
              <Upload className={`w-6 h-6 ${isDragging ? 'text-gov-blue' : 'text-gray-400'}`} />
            </div>
            <div className="text-center">
              <p className="text-gray-600 font-medium">
                {language === 'fr'
                  ? 'Téléchargez un formulaire PDF à remplir'
                  : 'Upload a fillable PDF form'}
              </p>
              <p className="text-sm text-gray-400 mt-1">
                {language === 'fr'
                  ? 'Glissez-déposez ou cliquez pour parcourir'
                  : 'Drag and drop or click to browse'}
              </p>
            </div>
          </>
        )}
      </button>

      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,application/pdf"
        onChange={handleFileSelect}
        className="hidden"
        disabled={isProcessing}
      />

      {/* Error message */}
      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <p className="text-sm">{error}</p>
        </div>
      )}

      {/* Help text */}
      <p className="text-xs text-gray-500 text-center">
        {language === 'fr'
          ? 'Téléchargez un formulaire gouvernemental (ex: IMM5710, T1) et nous le remplirons automatiquement avec vos informations.'
          : 'Upload a government form (e.g., IMM5710, T1) and we\'ll auto-fill it with your information.'}
      </p>
    </div>
  );
};
