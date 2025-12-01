import { RagResponse, RulesResponse, PrefillResponse, AllocationData, KnowledgeChunk, RulesResponseStream, GovLensResponseStream, LexGraphStreamEvent, Language } from "../types";
import { searchKnowledgeBase } from "./ragService";
import { logInteraction } from "./auditService";
import { CONFIG } from "../config";
import { PROMPTS } from "../prompts";
import { streamWithCallback } from "./apiClient";

// Helper to format context for the LLM
const formatContext = (chunks: KnowledgeChunk[]): string => {
  if (chunks.length === 0) return "No specific internal documents found.";
  return chunks.map(c => 
    `[Source: ${c.source_title}, ${c.section_reference}] (Effective: ${c.effective_date_start}) (ID: ${c.id})\nContent: "${c.content}"`
  ).join("\n\n");
};

// Helper: Generic Backend Generation Call
async function callBackendGeneration<T>(
  prompt: string, 
  schema: any, 
  temperature: number = 0.1,
  history: any[] = [], // Added history support
  context: string = "" // Added context support explicitly
): Promise<T> {
  const response = await fetch(`${CONFIG.RAG.BASE_URL}/generate`, {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      prompt,
      schema,
      model_name: CONFIG.GEMINI.MODEL_NAME,
      temperature,
      history, // Pass history
      context // Pass context
    })
  });

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`Backend Generation Failed: ${response.status} ${err}`);
  }

  const data = await response.json();
  if (!data.text) throw new Error("No text returned from backend");
  
  // If a schema was provided, we expect valid JSON. Otherwise, return raw text.
  if (schema) {
      try {
        return JSON.parse(data.text) as T;
      } catch (e) {
        console.warn("JSON Parse Error in Backend Response:", data.text);
        // Fallback: try to repair or just return null/throw
        throw new Error("Failed to parse JSON from backend response");
      }
  }
  
  return data.text as unknown as T;
}

// --- GovLens: RAG Search ---

export interface GovLensSearchFilters {
  categories?: string[];
  themes?: string[];
}

// Streaming Agentic Search
export const streamGovLensSearch = async (
  query: string,
  language: string,
  onStateUpdate: (newState: GovLensResponseStream) => void,
  signal?: AbortSignal,
  filters?: GovLensSearchFilters
): Promise<void> => {
  const start = Date.now();
  // Accumulate state across stream events
  let accumulatedState: Partial<GovLensResponseStream> = { query, language };

  // Build request body with optional filters
  const requestBody: Record<string, any> = { query, language };
  if (filters?.categories && filters.categories.length > 0) {
    requestBody.categories = filters.categories;
  }
  if (filters?.themes && filters.themes.length > 0) {
    requestBody.themes = filters.themes;
  }

  try {
    await streamWithCallback<{ node: string; state: Partial<GovLensResponseStream> }>(
      '/agent/govlens/stream',
      requestBody,
      (data) => {
        if (signal?.aborted) return;
        // Extract state from the nested structure and merge with accumulated state
        if (data.state) {
          accumulatedState = { ...accumulatedState, ...data.state };
        }
        onStateUpdate(accumulatedState as GovLensResponseStream);
      },
      signal
    );

    if (!signal?.aborted) {
      const duration = Date.now() - start;
      logInteraction(
        'GovLens',
        `Agent Search: ${query.substring(0, 30)}...`,
        duration,
        'success',
        { query },
      );
    }
  } catch (error) {
    if (signal?.aborted || (error as any)?.name === 'AbortError') return;
    const duration = Date.now() - start;
    logInteraction('GovLens', 'Agent Search Failed', duration, 'error', { error: String(error) });
    console.error("GovLens Agent Error", error);
    throw error;
  }
};

// Legacy/Fallback (Non-Streaming)
export const generateRagResponse = async (
    query: string,
    language: Language,
    history: Array<{ role: 'user' | 'model', content: string }> = []
): Promise<RagResponse> => {
  const start = Date.now();
  
  try {
    let search_query = query;

    // 0. Contextual Query Rewriting (if history exists)
    if (history.length > 0) {
        const last_turn = history.slice(-2); // Last 2 messages for context
        const history_text = last_turn.map(msg => `${msg.role}: ${msg.content}`).join("\n");
        
        // Quick LLM call to rewrite query
        const rewrite_prompt = `Given the chat history, rewrite the last user question to be a standalone search query.
        History:
        ${history_text}
        
        User Question: ${query}
        
        Standalone Query (only the text):`;

        try {
            // We expect a raw string back now
            const rewrite_text = await callBackendGeneration<string>(
                rewrite_prompt, 
                null, // No schema, just text
                0.0
            );
            if (rewrite_text) {
                search_query = rewrite_text.trim();
                if (import.meta.env.DEV) console.log(`[GovLens] Query Rewritten: "${query}" -> "${search_query}"`);
            }
        } catch (e) {
            if (import.meta.env.DEV) console.warn("Query rewriting failed, using original query", e);
        }
    }

    // 1. RETRIEVE using the potentially rewritten query
    const retrievedChunks = await searchKnowledgeBase(search_query, language);
    const contextText = formatContext(retrievedChunks);

    const schema = {
      type: "OBJECT",
      properties: {
        answer: { type: "STRING", description: "The summarized answer based ONLY on context." },
        lang: { type: "STRING", description: "Language code en or fr." },
        bullets: { 
          type: "ARRAY", 
          items: { type: "STRING" },
          description: "Key takeaways."
        },
        citations: {
          type: "ARRAY",
          items: {
            type: "OBJECT",
            properties: {
              doc_id: { type: "STRING", description: "The ID of the source document from context." },
              locator: { type: "STRING", description: "Section or page number." }
            }
          }
        },
        confidence: { type: "NUMBER", description: "Confidence score 0-1." },
        abstained: { type: "BOOLEAN", description: "Set to true if the context does not contain the answer." }
      },
      required: ["answer", "bullets", "citations", "confidence", "abstained"]
    };

    // 2. GENERATE with History & Context
    // Note: We pass the ORIGINAL query + history to the answer generator so it feels natural,
    // but we provided context based on the REWRITTEN query.
    const response = await callBackendGeneration<RagResponse>(
      query, 
      schema,
      0.0,
      history, 
      contextText 
    );

    // Aggregate Metadata for Answer View
    const uniqueCategories = Array.from(new Set(retrievedChunks.map(c => c.category).filter(Boolean))) as string[];
    const uniqueThemes = Array.from(new Set(
      retrievedChunks
        .map(c => c.themes)
        .filter(Boolean)
        .flatMap(t => (t as string).split(',').map(s => s.trim()))
    )) as string[];

    response.categories = uniqueCategories;
    // Take top 5 themes to avoid clutter
    response.aggregated_themes = uniqueThemes.slice(0, 5);

    // Enrich Citations with Metadata from Retrieval
    response.citations.forEach(cit => {
      // 1. Try exact match
      let chunk = retrievedChunks.find(c => c.id === cit.doc_id);
      
      // 2. Fallback: Try partial match if LLM stripped the ID
      if (!chunk) {
         chunk = retrievedChunks.find(c => c.id.includes(cit.doc_id) || cit.doc_id.includes(c.id));
      }

      if (chunk) {
        cit.title = chunk.source_title;
        cit.category = chunk.category; // Populate category
        // Use themes if available, otherwise snippet
        const themes = chunk.themes; 
        cit.snippet = themes ? themes : chunk.content.substring(0, 60) + "...";
      } else {
        // Fallback if not found
        cit.title = cit.doc_id;
        cit.snippet = "Source reference not found in context.";
      }
    });

    const duration = Date.now() - start;
    logInteraction('GovLens', `Search: ${search_query.substring(0, 30)}...`, duration, 'success', { query: search_query, abstained: response.abstained });
    return response;

  } catch (error) {
    const duration = Date.now() - start;
    logInteraction('GovLens', 'Search Failed', duration, 'error', { error: String(error) });
    console.error("GovLens Error", error);
    throw error;
  }
};

// --- LexGraph: Rules Engine ---
// Now uses streaming for LangGraph agent with node-aware events
export const streamLexGraphEvaluation = async (
  scenario: string,
  language: string,
  effectiveDate: string,
  onStateUpdate: (event: LexGraphStreamEvent) => void, // Callback receives node + state
  signal?: AbortSignal
): Promise<void> => {
  const start = Date.now();
  try {
    await streamWithCallback<LexGraphStreamEvent>(
      '/agent/lexgraph/stream',
      { query: scenario, language, effective_date: effectiveDate },
      (data) => {
        if (signal?.aborted) return;
        onStateUpdate(data);
      },
      signal
    );

    if (!signal?.aborted) {
      const duration = Date.now() - start;
      logInteraction(
        'LexGraph',
        `Agent Eval: ${scenario.substring(0, 30)}...`,
        duration,
        'success',
        { query: scenario },
      );
    }
  } catch (error) {
    if (signal?.aborted || (error as any)?.name === 'AbortError') return;
    const duration = Date.now() - start;
    logInteraction('LexGraph', 'Agent Evaluation Failed', duration, 'error', { error: String(error) });
    console.error("LexGraph Agent Error", error);
    throw error;
  }
};

// --- ForesightOps: Planning ---
export const generateAllocationPlan = async (
  currentData: any[], 
  budgetConstraint: number, 
  equityWeight: number,
  language: string
): Promise<AllocationData[]> => {
  const start = Date.now();
  
  try {
    const schema = {
      type: "ARRAY",
      items: {
        type: "OBJECT",
        properties: {
          region: { type: "STRING" },
          demand: { type: "NUMBER" },
          allocated: { type: "NUMBER" },
          capacity: { type: "NUMBER" },
          optimized: { type: "NUMBER" }
        }
      }
    };

    const response = await callBackendGeneration<AllocationData[]>(
      PROMPTS.FORESIGHT_OPS(JSON.stringify(currentData), budgetConstraint, equityWeight, language),
      schema,
      0.1
    );

    const duration = Date.now() - start;
    logInteraction('ForesightOps', 'Optimization Run', duration, 'success', { budget: budgetConstraint, equity: equityWeight });
    return response;

  } catch (error) {
    const duration = Date.now() - start;
    logInteraction('ForesightOps', 'Optimization Failed', duration, 'error', { error: String(error) });
    console.error("ForesightOps Error", error);
    throw error;
  }
};

// --- AccessBridge: Prefill ---
export const prefillForm = async (docText: string, language: Language): Promise<PrefillResponse> => {
  const start = Date.now();

  try {
    // 1. RETRIEVE program guidelines that might explain WHY fields are needed
    const retrievedChunks = await searchKnowledgeBase("eligibility application requirements", language);
    const contextText = formatContext(retrievedChunks);

    const schema = {
      type: "OBJECT",
      properties: {
        form_id: { type: "STRING" },
        fields: {
          type: "ARRAY",
          items: {
            type: "OBJECT",
            properties: {
              key: { type: "STRING" },
              value: { type: "STRING" },
              source: { type: "STRING" },
              why: { type: "STRING" }
            }
          }
        },
        gaps: {
          type: "ARRAY",
          items: {
            type: "OBJECT",
            properties: {
              field: { type: "STRING" },
              ask: { type: "STRING" },
              why: { type: "STRING" }
            }
          }
        }
      }
    };

    const response = await callBackendGeneration<PrefillResponse>(
      PROMPTS.ACCESS_BRIDGE(contextText, docText, language),
      schema,
      0.1
    );

    const duration = Date.now() - start;
    logInteraction('AccessBridge', 'Document Extraction', duration, 'success', { docLen: docText.length });
    return response;

  } catch (error) {
    const duration = Date.now() - start;
    logInteraction('AccessBridge', 'Extraction Failed', duration, 'error', { error: String(error) });
    console.error("AccessBridge Error", error);
    throw error;
  }
};

// --- Shared: Text-to-Speech ---
export const generateSpeech = async (text: string, language: string): Promise<string> => {
  const start = Date.now();

  try {
    const response = await fetch(`${CONFIG.RAG.BASE_URL}/tts`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            text,
            language,
            model_name: CONFIG.GEMINI.TTS_MODEL
        })
    });

    if (!response.ok) {
        const err = await response.text();
        throw new Error(`TTS Failed: ${response.status} ${err}`);
    }

    const data = await response.json();
    // Backend returns { audio_base64: "..." }
    if (data.audio_base64) {
      const duration = Date.now() - start;
      logInteraction('GovLens', 'TTS Generation', duration, 'success', { charCount: text.length });
      return data.audio_base64;
    }
    throw new Error("No audio data returned");

  } catch (error) {
    const duration = Date.now() - start;
    logInteraction('GovLens', 'TTS Failed', duration, 'error', { error: String(error) });
    console.error("TTS Error", error);
    throw error;
  }
};

export const summarizeText = async (text: string): Promise<string> => {
  const prompt = `Summarize this text in 2-3 concise sentences using **Markdown**. **Bold** key policy or legal requirements.
  
  Text:
  "${text}"
  
  Summary:`;
  
  // Using generic call with no schema (returns string)
  return await callBackendGeneration<string>(prompt, null, 0.2);
};

export const summarizeAllText = async (texts: string[]): Promise<string> => {
    const combinedText = texts.map((t, i) => `[Chunk ${i+1}]: ${t}`).join("\n\n");
    const prompt = `Synthesize the following ${texts.length} text chunks into a single, coherent summary using **Markdown**.
    Use **bolding** for key themes and *italics* for citations or references.
    
    Input Chunks:
    ${combinedText}
    
    Comprehensive Summary (3-4 sentences):`;
    
    return await callBackendGeneration<string>(prompt, null, 0.2);
  };
