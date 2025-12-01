import { KnowledgeChunk, Language } from '../types';
import { CONFIG } from '../config';

const RAG_API_URL = `${CONFIG.RAG.BASE_URL}${CONFIG.RAG.ENDPOINTS.SEARCH}`;
const FILTER_OPTIONS_URL = `${CONFIG.RAG.BASE_URL}/filter-options`;

export interface SearchRequest {
  query: string;
  language?: string;
  limit?: number;
  reference_date?: string; // YYYY-MM-DD
  categories?: string[];  // Filter by document categories
  themes?: string[];      // Filter by themes
}

export interface FilterOptions {
  categories: string[];
  themes: string[];
}

export interface BackendSearchResult {
  id: string;
  content: string;
  source_title: string;
  score: number;
  metadata: {
    source_id: string;
    source_title?: string;
    source_url: string;
    language: string;
    section_reference?: string;
    effective_date_start?: string;
    effective_date_end?: string;
    doc_type?: string;
    themes?: string;
    category?: string; // Added
  };
}


/**
 * Fetch available filter options (categories and themes) from the knowledge base.
 */
export const fetchFilterOptions = async (): Promise<FilterOptions> => {
  try {
    const response = await fetch(FILTER_OPTIONS_URL);
    if (!response.ok) {
      throw new Error(`Failed to fetch filter options: ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    console.error("Error fetching filter options:", error);
    return { categories: [], themes: [] };
  }
};

export interface SearchFilters {
  categories?: string[];
  themes?: string[];
}

export const searchKnowledgeBase = async (
  query: string,
  language: Language,
  referenceDateStr?: string, // Optional date for time travel (YYYY-MM-DD)
  limit: number = CONFIG.RETRIEVAL.DEFAULT_LIMIT,
  filters?: SearchFilters
): Promise<KnowledgeChunk[]> => {
  try {
    const requestBody: SearchRequest = {
      query,
      language,
      limit,
    };

    if (referenceDateStr) {
      requestBody.reference_date = referenceDateStr;
    }

    // Add filters if provided
    if (filters?.categories && filters.categories.length > 0) {
      requestBody.categories = filters.categories;
    }
    if (filters?.themes && filters.themes.length > 0) {
      requestBody.themes = filters.themes;
    }

    const response = await fetch(RAG_API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(`Backend error: ${errorData.detail || response.statusText}`);
    }

    const results: BackendSearchResult[] = await response.json();

    // Map SearchResult to KnowledgeChunk
    const knowledgeChunks: KnowledgeChunk[] = results.map(result => ({
      id: result.id,
      content: result.content,
      source_id: result.metadata.source_id,
      source_title: result.metadata.source_title || result.source_title, 
      source_url: result.metadata.source_url,
      language: result.metadata.language as Language, 
      section_reference: result.metadata.section_reference,
      effective_date_start: result.metadata.effective_date_start,
      effective_date_end: result.metadata.effective_date_end,
      doc_type: result.metadata.doc_type as any,
      themes: result.metadata.themes,
      category: result.metadata.category, // Map category
      score: result.score, 
    }));

    return knowledgeChunks;

  } catch (error) {
    console.error("Error calling RAG backend:", error);
    // Surface the error so callers can render proper error states instead of silent empty results.
    throw error instanceof Error ? error : new Error(String(error));
  }
};
