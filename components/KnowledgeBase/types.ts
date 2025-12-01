// KnowledgeBase Types

export interface IngestionLog {
  timestamp: string;
  message: string;
  type: 'info' | 'error' | 'success' | 'warning';
}

export interface UploadHistoryItem {
  fileName: string;
  status: 'success' | 'error' | 'skipped';
  timestamp: string;
  details?: string;
}

export interface Connector {
  id: string;
  name: string;
  country: string;
  description: string;
  datasets: string[];
}

export interface Dataset {
  id: string;
  name: string;
  description: string;
  asset_type: string;
  estimated_records: number;
  last_updated?: string;
}

export interface KnowledgeBaseStats {
  total_documents: number;
  by_source: Record<string, number>;
  by_connector: Record<string, number>;
  last_updated?: string;
}

export interface SampleDataProgressState {
  message: string;
  progress: number;
  currentFile?: string;
  fileIndex?: number;
  totalFiles?: number;
  phase?: string;
  model?: string;
}

export interface SampleDataFile {
  name: string;
  title: string;
  status: 'pending' | 'processing' | 'complete' | 'error';
  phase?: string;
}

export interface ImportProgressState {
  phase: string;
  progress: number;
  message: string;
}

export type UploadStatus = 'idle' | 'uploading' | 'batch_complete' | 'error';
export type IngestionStep = 'reading' | 'analyzing' | 'embedding' | 'complete';

// Sample file descriptions for better UX
export const SAMPLE_FILE_TITLES: Record<string, string> = {
  'uk_skilled_worker_2024.txt': 'UK Skilled Worker Visa Requirements',
  'canada_irpr_2024.txt': 'Canada Immigration & Refugee Protection Regulations',
  'uk_global_talent_2024.txt': 'UK Global Talent Visa Guidelines',
  'SOR-98-282.pdf': 'Immigration & Refugee Protection Regulations (SOR/98-282)',
  'SOR-2002-227.pdf': 'Immigration & Refugee Protection Act Regulations',
  'SOR-2018-108.pdf': 'Temporary Foreign Worker Program Regulations',
  'qpnotes.csv.gz': 'Question Period Notes Database (Immigration)',
};
