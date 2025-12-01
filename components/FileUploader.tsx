import React, { useState, useRef, useCallback } from 'react';
import { Upload, FileText, Image, X, Loader2, CheckCircle2 } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';
import { CONFIG } from '../config';

interface UploadedFile {
  id: string;
  name: string;
  type: string;
  size: number;
  status: 'uploading' | 'processing' | 'done' | 'error';
  extractedText?: string;
  error?: string;
}

interface FileUploaderProps {
  onFilesProcessed: (texts: string[]) => void;
  disabled?: boolean;
  maxFiles?: number;
  acceptedTypes?: string[];
}

export const FileUploader: React.FC<FileUploaderProps> = ({
  onFilesProcessed,
  disabled = false,
  maxFiles = 5,
  acceptedTypes = ['.pdf', '.png', '.jpg', '.jpeg'],
}) => {
  const { language } = useLanguage();
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Notify parent when files change
  React.useEffect(() => {
    const processedTexts = files
      .filter((f) => f.status === 'done' && f.extractedText)
      .map((f) => f.extractedText!);
    onFilesProcessed(processedTexts);
  }, [files, onFilesProcessed]);

  const processFile = async (file: File, fileId: string) => {
    try {
      // Update status to processing
      setFiles((prev) =>
        prev.map((f) => (f.id === fileId ? { ...f, status: 'processing' } : f))
      );

      // Convert file to base64
      const reader = new FileReader();
      const base64Promise = new Promise<string>((resolve, reject) => {
        reader.onloadend = () => {
          const base64 = (reader.result as string).split(',')[1];
          resolve(base64);
        };
        reader.onerror = reject;
      });
      reader.readAsDataURL(file);
      const fileBase64 = await base64Promise;

      // Determine file type
      let fileType = 'pdf';
      if (file.type.includes('png')) fileType = 'png';
      else if (file.type.includes('jpeg') || file.type.includes('jpg')) fileType = 'jpg';

      // Send to OCR endpoint
      const response = await fetch(`${CONFIG.RAG.BASE_URL}/ocr`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          file_base64: fileBase64,
          file_type: fileType,
          language: language,
        }),
      });

      if (!response.ok) {
        throw new Error(`OCR failed: ${response.status}`);
      }

      const data = await response.json();

      // Update file with extracted text
      setFiles((prev) =>
        prev.map((f) =>
          f.id === fileId
            ? { ...f, status: 'done', extractedText: data.text }
            : f
        )
      );
    } catch {
      setFiles((prev) =>
        prev.map((f) =>
          f.id === fileId
            ? {
                ...f,
                status: 'error',
                error: language === 'fr' ? 'Échec du traitement' : 'Processing failed',
              }
            : f
        )
      );
    }
  };

  const handleFiles = useCallback(
    async (newFiles: FileList) => {
      const filesToAdd: UploadedFile[] = [];

      for (let i = 0; i < Math.min(newFiles.length, maxFiles - files.length); i++) {
        const file = newFiles[i];

        // Validate file type
        const isValidType = acceptedTypes.some(
          (type) =>
            file.name.toLowerCase().endsWith(type) ||
            file.type.includes(type.replace('.', ''))
        );

        if (!isValidType) {
          continue;
        }

        // Validate file size (max 10MB)
        if (file.size > 10 * 1024 * 1024) {
          continue;
        }

        const fileId = `${Date.now()}-${i}`;
        filesToAdd.push({
          id: fileId,
          name: file.name,
          type: file.type,
          size: file.size,
          status: 'uploading',
        });

        // Process file asynchronously
        processFile(file, fileId);
      }

      setFiles((prev) => [...prev, ...filesToAdd]);
    },
    [files.length, maxFiles, acceptedTypes, language]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);

      if (disabled) return;
      if (e.dataTransfer.files) {
        handleFiles(e.dataTransfer.files);
      }
    },
    [disabled, handleFiles]
  );

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    if (!disabled) {
      setIsDragging(true);
    }
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleClick = () => {
    if (!disabled) {
      fileInputRef.current?.click();
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      handleFiles(e.target.files);
    }
  };

  const removeFile = (fileId: string) => {
    setFiles((prev) => {
      const updated = prev.filter((f) => f.id !== fileId);
      return updated;
    });
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getFileIcon = (type: string) => {
    if (type.includes('pdf')) return <FileText className="w-5 h-5" />;
    if (type.includes('image')) return <Image className="w-5 h-5" />;
    return <FileText className="w-5 h-5" />;
  };

  return (
    <div className="space-y-4">
      {/* Drop zone - using button for proper semantics */}
      <button
        type="button"
        onClick={handleClick}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            handleClick();
          }
        }}
        disabled={disabled}
        className={`
          w-full border-2 border-dashed rounded-lg p-8
          flex flex-col items-center justify-center gap-4
          transition-colors cursor-pointer
          focus:ring-4 focus:ring-gov-accent focus:ring-offset-2 focus:outline-none
          ${isDragging ? 'border-gov-blue bg-gov-blue/5' : 'border-gray-300 hover:border-gray-400'}
          ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
        `}
        aria-label={language === 'fr'
          ? 'Zone de téléchargement de fichiers. Glissez-déposez ou cliquez pour parcourir. PDF, PNG, JPG acceptés, maximum 10 Mo'
          : 'File upload area. Drag and drop or click to browse. PDF, PNG, JPG accepted, max 10 MB'}
      >
        <Upload
          className={`w-12 h-12 ${isDragging ? 'text-gov-blue' : 'text-gray-400'}`}
          aria-hidden="true"
        />
        <div className="text-center">
          <p className="text-gray-600">
            {language === 'fr'
              ? 'Glissez-déposez vos fichiers ici ou cliquez pour parcourir'
              : 'Drag and drop files here or click to browse'}
          </p>
          <p className="text-sm text-gray-400 mt-1">
            {language === 'fr'
              ? 'PDF, PNG, JPG (max 10 Mo)'
              : 'PDF, PNG, JPG (max 10 MB)'}
          </p>
        </div>
      </button>

      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept={acceptedTypes.join(',')}
        onChange={handleInputChange}
        className="hidden"
        disabled={disabled}
      />

      {/* File list */}
      {files.length > 0 && (
        <div className="space-y-2">
          {files.map((file) => (
            <div
              key={file.id}
              className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg"
            >
              <div className="text-gray-500">{getFileIcon(file.type)}</div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{file.name}</p>
                <p className="text-xs text-gray-400">{formatFileSize(file.size)}</p>
              </div>
              <div className="flex items-center gap-2">
                {file.status === 'uploading' || file.status === 'processing' ? (
                  <Loader2 className="w-5 h-5 text-gov-blue animate-spin" />
                ) : file.status === 'done' ? (
                  <CheckCircle2 className="w-5 h-5 text-green-500" />
                ) : file.status === 'error' ? (
                  <span className="text-xs text-red-500">{file.error}</span>
                ) : null}
                <button
                  onClick={() => removeFile(file.id)}
                  className="p-1 hover:bg-gray-200 rounded"
                  aria-label={language === 'fr' ? 'Supprimer' : 'Remove'}
                >
                  <X className="w-4 h-4 text-gray-500" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Status summary */}
      {files.length > 0 && (
        <p className="text-sm text-gray-500">
          {files.filter((f) => f.status === 'done').length} / {files.length}{' '}
          {language === 'fr' ? 'fichiers traités' : 'files processed'}
        </p>
      )}
    </div>
  );
};
