<div align="center">

# GovAI Platform

### A Modular AI Platform for Government Services

![React](https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi)
![LangGraph](https://img.shields.io/badge/LangGraph-Orchestration-orange?style=flat-square)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vectors-purple?style=flat-square)
![TypeScript](https://img.shields.io/badge/TypeScript-5.8-3178C6?style=flat-square&logo=typescript)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python)

</div>

---

## G7 GovAI Grand Challenge Submission

> **Primary Module: GovLens** - RAG-based search system with transparent citations for government knowledge retrieval.

### Quick Start for Evaluators

1. **Configure API Key**: Navigate to the **Governance** page and enter your **Gemini API key**
2. **Ingest Sample Documents**: Go to the **Knowledge Base** tab and ingest the provided sample documents before testing
3. **Test GovLens**: Use the **GovLens** module to search and receive cited answers from ingested documents

Without completing steps 1-2, the GovLens module will not function properly.

---

## Overview

GovAI is a **modular AI platform** designed to address common challenges in government service delivery. Rather than building separate applications for each use case, we engineered a **shared infrastructure** that powers four specialized agents—each solving a distinct problem while sharing common components for consistency and maintainability.

### Core Philosophy

**Neuro-Symbolic Architecture**: We combine **neural AI capabilities** (LLMs for understanding, extraction, generation) with **symbolic reasoning** (deterministic rule engines, constraint solvers). This achieves both the flexibility of modern AI and the **auditability required for government decisions**.

Why this matters:
- **LLMs alone** are non-deterministic and can hallucinate—unacceptable for official decisions
- **Rules engines alone** can't handle natural language or subjective terms
- **Combining both** lets LLMs do what they're good at (understanding language) while symbolic systems do what they're good at (deterministic, auditable evaluation)

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Modules](#modules)
   - [GovLens - RAG Search](#govlens---rag-search)
   - [LexGraph - Neuro-Symbolic Rules Engine](#lexgraph---neuro-symbolic-rules-engine)
   - [ForesightOps - Resource Optimization](#foresightops---resource-optimization)
   - [AccessBridge - Multimodal Intake](#accessbridge---multimodal-intake)
3. [Technology Stack](#technology-stack)
4. [Getting Started](#getting-started)
5. [API Reference](#api-reference)
6. [Development](#development)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React 19)                       │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────────┐   │
│  │  GovLens  │ │ LexGraph  │ │ Foresight │ │ AccessBridge  │   │
│  │    UI     │ │    UI     │ │    UI     │ │      UI       │   │
│  └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └───────┬───────┘   │
│        │             │             │               │             │
│        └─────────────┴─────────────┴───────────────┘             │
│                           │                                       │
│                   JSONL Streaming                                 │
└───────────────────────────┼───────────────────────────────────────┘
                            │
┌───────────────────────────┼───────────────────────────────────────┐
│                        BACKEND (FastAPI)                          │
│                           │                                       │
│  ┌────────────────────────┴────────────────────────┐             │
│  │              Shared Infrastructure               │             │
│  │  ┌──────────────┐ ┌───────────┐ ┌────────────┐  │             │
│  │  │  LLM Service │ │ Streaming │ │ Embeddings │  │             │
│  │  └──────────────┘ └───────────┘ └────────────┘  │             │
│  └─────────────────────────────────────────────────┘             │
│                           │                                       │
│  ┌────────────┬───────────┼───────────┬────────────┐             │
│  │            │           │           │            │             │
│  ▼            ▼           ▼           ▼            │             │
│ GovLens   LexGraph   Foresight  AccessBridge       │             │
│ Agent     Agent      Agent      Agent              │             │
│  │            │           │           │            │             │
│  └────────────┴───────────┼───────────┴────────────┘             │
│                           │                                       │
│                    ┌──────┴──────┐                               │
│                    │   ChromaDB  │                               │
│                    │   (Vectors) │                               │
│                    └─────────────┘                               │
└───────────────────────────────────────────────────────────────────┘
```

### Why LangGraph for Agent Orchestration?

| Factor | LangGraph | Raw LangChain | Custom Python |
|--------|-----------|---------------|---------------|
| **State management** | Built-in TypedDict state | Manual passing | Manual |
| **Conditional routing** | Native graph edges | Chain of conditionals | If/else code |
| **Streaming** | Built-in `.astream()` | Manual SSE setup | Manual |
| **Visualization** | Graph structure visible | Opaque | Opaque |

LangGraph provides **deterministic, inspectable workflows** while still allowing LLM calls within nodes.

### Why JSONL Streaming over WebSockets?

We chose JSONL (JSON Lines) streaming because:
1. **Simpler**: No connection management, heartbeats, reconnection logic
2. **HTTP-native**: Works through any proxy/CDN without special config
3. **Debuggable**: `curl` can consume the stream directly
4. **Sufficient**: Our use case is server→client streaming, not bidirectional

---

## Modules

---

### GovLens - RAG Search

**Main Point**: Retrieval-Augmented Generation (RAG) system that synthesizes answers from government documents with **full citations, algorithmic confidence scores, and complete audit trails**.

#### The Problem
Government agencies produce vast quantities of documents—legislation, regulations, policies, forms. Finding relevant information is challenging due to:
- **Volume**: Thousands of documents across departments
- **Language variations**: Bilingual (EN/FR) content with inconsistent terminology
- **Fragmentation**: Information scattered across acts, regulations, policies, and guidance
- **Trust deficit**: Citizens can't verify AI-generated answers

Traditional search returns document links; users must still read and synthesize. Pure LLM chatbots hallucinate and provide untraceable answers. **GovLens bridges this gap with verifiable, citation-backed responses.**

#### Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Hybrid Search** | BM25 + Semantic | Lexical search catches exact matches (statute numbers like "SOR/2002-227"); semantic search catches conceptual matches. Neither alone is sufficient. |
| **Vector DB** | ChromaDB | Embedded (no server), has built-in BM25, zero ops overhead. PostgreSQL pgvector would require database management. |
| **Diversity** | MMR Reranking | Maximal Marginal Relevance prevents returning 5 near-duplicate paragraphs—balances relevance with information diversity. |
| **Query Expansion** | 5 semantic variations + FR | Improves recall by searching for conceptually similar queries; includes French translation to catch bilingual content. |
| **Confidence Scoring** | Algorithmic (not LLM) | LLM self-reported confidence is unreliable. We calculate confidence from retrieval metrics: top document similarity × coverage. |

#### Tech Stack

**Backend:**
- **ChromaDB** - Vector storage with hybrid search (768-dim Gemini embeddings)
- **LangGraph** - 6-node workflow orchestration with conditional routing
- **Google Gemini** - LLM for query understanding, grading, and synthesis

**Frontend:**
- **React 19** with streaming hooks (JSONL/EventSource)
- **Zustand** - State persistence across navigation
- **Citation UI** - Clickable [1], [2] badges that scroll to sources

#### 6-Node LangGraph Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                        GOVLENS PIPELINE                              │
│                                                                      │
│  ┌──────────┐    ┌───────────┐    ┌──────────────────────────────┐ │
│  │  ROUTER  │───▶│ RETRIEVE  │───▶│      CONDITIONAL BRANCH      │ │
│  │          │    │           │    │                              │ │
│  │ Classify │    │ Hybrid    │    │  Simple Query?               │ │
│  │ simple/  │    │ Search +  │    │  ├─ YES → GENERATE           │ │
│  │ complex  │    │ MMR       │    │  └─ NO  → GRADER             │ │
│  └──────────┘    └───────────┘    └──────────────────────────────┘ │
│                                              │                       │
│                                              ▼                       │
│                       ┌──────────────────────────────────────────┐  │
│                       │              GRADER                       │  │
│                       │  Are retrieved docs sufficient?          │  │
│                       │  ├─ YES → GENERATE                       │  │
│                       │  └─ NO  → REWRITER (max 3 iterations)    │  │
│                       └──────────────────────────────────────────┘  │
│                                              │                       │
│                                              ▼                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                        GENERATE                                │  │
│  │  Synthesize answer with numbered citations [1], [2], [3]      │  │
│  │  Calculate algorithmic confidence (0.0-1.0)                   │  │
│  │  Can ABSTAIN if insufficient information                      │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

**Node Responsibilities:**

| Node | Input | Output | LLM Used? |
|------|-------|--------|-----------|
| **Router** | User query | "simple" or "complex" | Yes |
| **Retrieve** | Query + 5 expansions | Top 20 diverse documents | No (embeddings only) |
| **Grader** | Documents + query | Relevance assessment | Yes |
| **Rewriter** | Query + missing info | Reformulated query | Yes |
| **Generate** | Documents + query | Answer + citations + confidence | Yes |

#### Explainability Features

GovLens is built for **government-grade transparency**:

**1. Numbered Citations**
Every claim in the answer links to a specific source document:
```json
{
  "answer": "Skilled workers must earn at least $60,000 [1] and have a valid job offer [2]...",
  "citations": [
    { "doc_id": "ircc-gts-2024", "title": "Global Talent Stream Guidelines", "locator": "Section 4.2" },
    { "doc_id": "irpr-203", "title": "IRPA Regulations SOR/2002-227", "locator": "§203(1)(a)" }
  ]
}
```

**2. Live Trace Log**
Users see real-time processing steps in the UI:
```
Router: Selected 'complex' strategy - query requires synthesis
Retrieved 147 candidates using 5 query variations
MMR reranking: selected 20 diverse documents
Grader: Documents rated SUFFICIENT
Generating answer with 6 citations...
```

**3. Algorithmic Confidence**
Confidence is calculated from retrieval metrics, **not LLM self-assessment**:
```
Confidence = (avg_top_3_similarity × 0.7) + (coverage_score × 0.3)
           = (0.82 × 0.7) + (1.0 × 0.3)
           = 0.874 → displayed as 87%
```
Scaled to intuitive range: 0.6 (low) to 0.98 (high). Never 100%—prevents overconfidence.

**4. Abstention Capability**
When information is insufficient, GovLens **explicitly refuses** rather than fabricating:
```json
{
  "answer": "I cannot answer this question based on the available documents.",
  "abstained": true,
  "confidence": 0.25,
  "reason": "No documents found matching 'quantum fishing regulations'"
}
```

#### Responsible AI Design

| Principle | Implementation |
|-----------|----------------|
| **Hallucination Prevention** | Answers grounded strictly in retrieved documents. System prompt enforces "Answer ONLY from provided documents." |
| **Bias Mitigation** | MMR diversity reranking (λ=0.7 relevance, 0.3 diversity). Max 3 chunks per source. Cross-language search includes both EN and FR. |
| **Auditability** | Every step logged. Citations traceable to source. Deterministic retrieval ranking (same query → same docs). |
| **Privacy** | Stateless architecture—no user queries stored. No session tracking. No training on user data. |
| **Transparency** | Live trace shown to users. Confidence calculated algorithmically. Full source metadata exposed. |

#### Query Expansion Strategy

To maximize recall, each query generates 5 variations:

```
Original: "immigration requirements for skilled workers"
    ├─ Variation 1: "skilled worker visa eligibility criteria"
    ├─ Variation 2: "work permit qualifications Canada"
    ├─ Variation 3: "LMIA exempt occupation requirements"
    ├─ Variation 4: "Express Entry minimum requirements"
    └─ French: "exigences d'immigration pour travailleurs qualifiés"
```

Special handling for legislative references:
- "Bill C-3" → also searches "history of Bill C-3", "amendments to Bill C-3"
- Catches older versions and related documents

#### Document Ingestion Pipeline

Before documents can be searched, they must be ingested into the vector database. The pipeline handles parsing, analysis, chunking, and embedding:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      DOCUMENT INGESTION PIPELINE                             │
│                                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────────────────┐ │
│  │   UPLOAD     │────▶│    PARSE     │────▶│         ANALYZE              │ │
│  │              │     │              │     │                              │ │
│  │ POST /ingest │     │ PDF, HTML,   │     │ Gemini extracts:             │ │
│  │ Validate:    │     │ CSV, TXT,    │     │ • Title                      │ │
│  │ • Extension  │     │ MD, JSON     │     │ • Category (Policy, Legal,   │ │
│  │ • Size <50MB │     │              │     │   Report, Guidance, etc.)    │ │
│  │ • MIME type  │     │ Table→MD     │     │ • Themes (1-3 topics)        │ │
│  └──────────────┘     └──────────────┘     └──────────────────────────────┘ │
│                                                       │                      │
│                                                       ▼                      │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                         CHUNK                                         │   │
│  │  Semantic chunking: split by paragraphs, max 2000 chars              │   │
│  │  Preserves sentence boundaries for coherent retrieval                │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                       │                      │
│                                                       ▼                      │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────────────────┐ │
│  │    EMBED     │────▶│    STORE     │────▶│         READY                │ │
│  │              │     │              │     │                              │ │
│  │ Gemini       │     │ ChromaDB     │     │ Chunks searchable via        │ │
│  │ text-embed-  │     │ Persistent   │     │ vector similarity            │ │
│  │ ding-004     │     │ • Vectors    │     │                              │ │
│  │ 768 dims     │     │ • Metadata   │     │ Metadata: source_id,         │ │
│  │ Parallel     │     │ • Documents  │     │ category, themes, dates      │ │
│  └──────────────┘     └──────────────┘     └──────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Pipeline Stages:**

| Stage | Technology | Details |
|-------|------------|---------|
| **Parse** | pdfplumber, BeautifulSoup | Extracts text and tables (→ Markdown), removes boilerplate (nav, headers, footers) |
| **Analyze** | Gemini LLM | Categorizes document (Policy, Legal, Report, etc.), extracts 1-3 themes |
| **Chunk** | Custom semantic chunker | Paragraph-aware splitting, 2000 char max, 240 char min |
| **Embed** | Gemini text-embedding-004 | 768 dimensions, batched 20 at a time for throughput |
| **Store** | ChromaDB | Persistent vector DB with full metadata for filtering |

**Supported File Types:**

| Format | Parser | Special Handling |
|--------|--------|------------------|
| PDF | pdfplumber | Table extraction → Markdown format |
| HTML | BeautifulSoup | Canada.ca optimized, removes nav/header/footer |
| CSV | csv module | Batch processing, QP Notes format detection |
| TXT/MD | Direct read | Markdown preserved |
| JSON | json module | Arrays → batch, objects → single doc |

#### Retrieval Pipeline

When a user submits a query, the retrieval pipeline finds the most relevant document chunks:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RETRIEVAL PIPELINE                                   │
│                                                                              │
│  ┌────────────┐                                                             │
│  │   QUERY    │  "What are immigration requirements for skilled workers?"   │
│  └─────┬──────┘                                                             │
│        │                                                                     │
│        ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  QUERY EXPANSION (5 semantic variations + French translation)           ││
│  │  ├─ "skilled worker visa eligibility criteria"                          ││
│  │  ├─ "work permit qualifications Canada"                                 ││
│  │  ├─ "Express Entry minimum requirements"                                ││
│  │  └─ "exigences d'immigration pour travailleurs qualifiés"               ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│        │                                                                     │
│        ▼                                                                     │
│  ┌──────────────────────┐     ┌──────────────────────┐                      │
│  │   VECTOR SEARCH      │     │   KEYWORD SEARCH     │                      │
│  │                      │     │                      │                      │
│  │ Embed query →        │     │ Extract identifiers: │                      │
│  │ ChromaDB similarity  │     │ "Bill C-4", "SOR/    │                      │
│  │ Top 100 candidates   │     │ 2002-227"            │                      │
│  └──────────┬───────────┘     └──────────┬───────────┘                      │
│             │                            │                                   │
│             └────────────┬───────────────┘                                   │
│                          ▼                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  MERGE & DEDUPLICATE                                                    ││
│  │  Keyword matches get +20.0 boost │ Keep best score per doc              ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                          │                                                   │
│                          ▼                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  FILTER & DIVERSIFY                                                     ││
│  │  • Date filter (time-travel: only docs effective before reference date) ││
│  │  • Theme/category filter                                                ││
│  │  • Source diversity: max 3 chunks per source (prevents repetition)      ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                          │                                                   │
│                          ▼                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  RERANK                                                                 ││
│  │  ┌─────────────────────────┐  OR  ┌─────────────────────────────────┐   ││
│  │  │ Cross-Encoder           │      │ MMR (Maximal Marginal Relevance)│   ││
│  │  │ ms-marco-MiniLM-L-6-v2  │      │ λ=0.6 balances relevance vs     │   ││
│  │  │ Semantic reranking      │      │ diversity                       │   ││
│  │  └─────────────────────────┘      └─────────────────────────────────┘   ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                          │                                                   │
│                          ▼                                                   │
│  ┌────────────┐                                                             │
│  │  TOP K     │  Return 5-20 most relevant, diverse documents               │
│  │  RESULTS   │  with metadata + scores                                     │
│  └────────────┘                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Reranking Strategies:**

| Strategy | Use Case | Behavior |
|----------|----------|----------|
| `relevance` | Default, precision-focused | Cross-encoder (ms-marco-MiniLM-L-6-v2) semantic reranking |
| `diverse` | Exploratory queries | MMR reranking balances relevance (λ=0.6) with diversity |

**Key Optimizations:**

| Optimization | Benefit |
|--------------|---------|
| **Embedding cache** | 1000-entry LRU cache eliminates redundant API calls |
| **Hybrid search** | Vector + keyword catches both concepts and exact identifiers (Bill C-4, SOR/2002-227) |
| **Query expansion** | 5 variations + French translation improves recall across terminology |
| **Source throttling** | Max 3 chunks per source prevents repetitive results from single documents |

#### Usage

**Sample Query (after ingesting Sample Data):**
> "What bills pertain to small businesses that were impacted by COVID?"

**API Endpoint:**
```bash
curl -X POST http://localhost:8000/api/agent/govlens/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the immigration requirements for skilled workers?",
    "language": "en"
  }'
```

**Response (JSONL stream):**
```jsonl
{"node": "router", "state": {"search_strategy": "complex", "trace_log": ["Router: complex strategy"]}}
{"node": "retrieve", "state": {"documents": [...], "retrieval_confidence": 0.82}}
{"node": "grader", "state": {"relevance": "sufficient"}}
{"node": "generate", "state": {"answer_text": "...", "citations": [...], "confidence": 0.87}}
{"node": "complete", "state": {}}
```

**Frontend Integration:**
```tsx
import { useGovLensSearch } from '@/hooks/useGovLensSearch';

function SearchPage() {
  const { search, isLoading, results, citations, trace } = useGovLensSearch();

  return (
    <div className="grid grid-cols-3 gap-4">
      {/* Left: Answer with inline citations */}
      <div className="col-span-2">
        <GovLensAnswer answer={results} citations={citations} />
      </div>

      {/* Right: Live trace + expandable citations */}
      <div>
        <GovLensProgressPanel trace={trace} />
        <GovLensCitations citations={citations} />
      </div>
    </div>
  );
}
```

---

### LexGraph - Neuro-Symbolic Rules Engine

**Main Point**: Combines LLM understanding with deterministic rule evaluation to make auditable, explainable eligibility decisions.

#### The Problem
Government decisions are governed by complex rules spread across legislation, regulations, and policies. These contain subjective terms ("genuine salary"), interdependencies, and temporal conditions. Citizens receive decisions without understanding why.

#### Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Neuro-Symbolic** | LLM + Rules Engine | LLMs handle understanding natural language; deterministic engine handles actual decisions. Same input = same output, every time. |
| **Dynamic Schema** | No hardcoded rules | Rules are extracted from retrieved documents at runtime, making the system domain-agnostic (works for any benefit type). |
| **Condition Filtering** | Validate against facts | LLMs may extract invalid fact keys; we filter to ensure only valid, evaluable conditions are used. |
| **Trace Logging** | Every condition logged | Full audit trail of what was evaluated, with what value, and the result. Essential for contestability. |

#### Why Neuro-Symbolic?

| Approach | Problem |
|----------|---------|
| **Pure LLM** | Non-deterministic. Same input → different outputs. Cannot audit. Hallucination risk. |
| **Pure Rules Engine** | Cannot handle natural language. Cannot interpret subjective terms. Requires manual rule authoring. |
| **Neuro-Symbolic** | LLM handles understanding (fuzzy) → Rules engine handles decision (deterministic). |

#### Tech Stack

**Backend:**
- **Custom Rules Engine** (`backend/rules.py`) - Pure Python, deterministic evaluation with operator dispatch
- **LangGraph** - 5-stage pipeline (Retrieve → Extract Rules → Resolve Thresholds → Extract Facts → Evaluate)
- **Pydantic** - Strict validation of extracted rules and facts

**Frontend:**
- **React** with decision trace visualization
- **Tree view** for rule hierarchy display

#### The 5-Stage Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│  STAGE 1: RETRIEVE                                                      │
│  Input: User scenario ("I have a $95k salary...")                       │
│  Output: Relevant legislative documents                                 │
├─────────────────────────────────────────────────────────────────────────┤
│  STAGE 2: EXTRACT RULES (Neural)                                        │
│  Input: Legislative documents                                           │
│  Output: [{ rule_id, conditions: [{fact_key, operator, value}] }]       │
├─────────────────────────────────────────────────────────────────────────┤
│  STAGE 3: RESOLVE THRESHOLDS (Neural)                                   │
│  Input: Rules with subjective terms ("genuine salary")                  │
│  Output: "genuine salary" → salary_offer >= 60000                       │
├─────────────────────────────────────────────────────────────────────────┤
│  STAGE 4: EXTRACT FACTS (Neural)                                        │
│  Input: User's natural language scenario                                │
│  Output: { salary_offer: 95000, has_job_offer: true, ... }              │
├─────────────────────────────────────────────────────────────────────────┤
│  STAGE 5: EVALUATE (Symbolic - NO LLM)                                  │
│  Input: Structured rules + Structured facts                             │
│  Output: Decision + Complete trace of every condition                   │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Example Decision Trace

```json
{
  "eligible": true,
  "program": "Global Talent Stream",
  "trace": [
    {
      "step": "salary_offer >= 60000",
      "value": 95000,
      "result": "pass",
      "source": "IRCC Policy EN-2023-001 §4.2"
    },
    {
      "step": "has_job_offer == true",
      "value": true,
      "result": "pass",
      "source": "IRPA Regulations SOR/2002-227 §203"
    }
  ]
}
```

#### Usage

**API Endpoint:**
```bash
curl -X POST http://localhost:8000/api/agent/lexgraph/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "I have a job offer for $95,000 as a software developer. Am I eligible?",
    "language": "en",
    "effective_date": "2024-01-15"
  }'
```

**Frontend Integration:**
```tsx
import { useLexGraphStream } from '@/hooks/useLexGraphStream';

function EligibilityChecker() {
  const { evaluate, isLoading, decision, trace } = useLexGraphStream();

  const handleCheck = () => {
    evaluate({
      query: "I earn $95,000 with a job offer",
      language: "en"
    });
  };

  return (
    <div>
      <button onClick={handleCheck}>Check Eligibility</button>
      {decision && (
        <div>
          <p>Decision: {decision.eligible ? "ELIGIBLE" : "INELIGIBLE"}</p>
          <TraceViewer trace={trace} />
        </div>
      )}
    </div>
  );
}
```

---

### ForesightOps - Resource Optimization

**Main Point**: Constrained multi-objective optimization for infrastructure resource allocation with risk modeling.

#### The Problem
Government resource allocation is often reactive (wait until failure), siloed (each department optimizes independently), and budget-blind (plans made without hard constraints).

#### Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Risk Model** | Custom Python (NumPy/Pandas) | Government-specific risk formulas. Off-the-shelf ML models don't capture policy constraints. |
| **Optimization** | OR-Tools + Greedy | OR-Tools for complex constraint satisfaction; greedy for interpretable asset prioritization. |
| **Database** | SQLite + SQLAlchemy | Simple persistence for asset data. PostgreSQL would be used in production. |
| **Visualization** | Recharts | React-native, customizable. D3 is more powerful but higher complexity for our needs. |

#### Tech Stack

**Backend:**
- **OR-Tools** - Google's operations research library for constraint optimization
- **NumPy/Pandas** - Risk calculations and data manipulation
- **SQLAlchemy** - ORM for asset database
- **LangGraph** - Workflow orchestration

**Frontend:**
- **Recharts** - Charts for budget allocation, risk trends
- **React-Force-Graph** - Network visualization of asset dependencies

#### Risk Calculation

```
Risk Score = P(failure) × Impact × Criticality

P(failure) = f(age, condition, usage_trend)
Impact = population_served × service_criticality
```

#### Usage

**API Endpoint:**
```bash
curl -X POST http://localhost:8000/api/agent/foresight/stream \
  -H "Content-Type: application/json" \
  -d '{
    "budget_total": 10000000,
    "planning_horizon_years": 5,
    "priority_weights": {"critical_infrastructure": 2.0}
  }'
```

**Frontend Integration:**
```tsx
import { useForesightStream } from '@/hooks/useForesightStream';

function ResourcePlanner() {
  const { optimize, isLoading, allocation, riskReport } = useForesightStream();

  const handleOptimize = () => {
    optimize({ budget_total: 10000000, planning_horizon_years: 5 });
  };

  return (
    <div>
      <button onClick={handleOptimize}>Optimize Allocation</button>
      {allocation && <AllocationChart data={allocation} />}
    </div>
  );
}
```

---

### AccessBridge - Multimodal Intake

**Main Point**: Multimodal intake assistant that extracts structured data from any input (voice, documents, text) with per-field provenance.

#### The Problem
Citizens interacting with government face complex forms, unclear document requirements, and accessibility gaps. Not everyone can type; some have documents, not answers.

#### Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Multimodal Input** | Voice + PDF + Image + Text | Accessibility-first design. Accept whatever the user can provide. |
| **Per-Field Provenance** | Source + Evidence tracking | Every extracted value traces back to its source—no "magic" black-box extraction. |
| **Confidence Scores** | 0-1 per field | Low confidence fields flagged for verification. Prevents auto-submission of uncertain data. |
| **Gap Analysis** | Required vs. provided | Identifies missing information and generates clarifying questions. |

#### Tech Stack

**Backend:**
- **LangGraph** - Orchestrates multimodal processing pipeline
- **pypdf** - PDF text and form field extraction
- **LLM Vision** - Image understanding (IDs, documents, handwriting)

**Frontend:**
- **VoiceRecorder** - Browser-native audio recording
- **FileUploader** - Drag-and-drop document upload
- **Provenance UI** - Shows source for each extracted field

#### Per-Field Provenance

Every extracted field carries:

```typescript
interface ExtractedField {
  key: string;              // "annual_income"
  value: any;               // 52000
  confidence: number;       // 0.87
  source: "document" | "voice" | "text";
  evidence: string;         // "From T4 slip, Box 14"
  requires_verification: boolean;
}
```

#### Usage

**API Endpoint:**
```bash
curl -X POST http://localhost:8000/api/agent/accessbridge/stream \
  -H "Content-Type: application/json" \
  -d '{
    "raw_text_input": "I need help with disability benefits. My name is Jane Smith, born March 15, 1985.",
    "program_type": "auto"
  }'
```

**Frontend Integration:**
```tsx
import { useAccessBridgeStream } from '@/hooks/useAccessBridgeStream';

function IntakeForm() {
  const { process, isLoading, fields, gaps } = useAccessBridgeStream();

  const handleSubmit = (input: string) => {
    process({ raw_text_input: input, program_type: "auto" });
  };

  return (
    <div>
      <VoiceRecorder onTranscript={handleSubmit} />
      <FileUploader onUpload={handleDocumentProcess} />
      {fields && <ExtractedFieldsTable fields={fields} />}
      {gaps && <GapQuestions gaps={gaps} />}
    </div>
  );
}
```

---

## Technology Stack

### Frontend

| Technology | Version | Purpose |
|------------|---------|---------|
| React | 19 | UI framework with concurrent rendering |
| TypeScript | 5.8 | Type safety and IDE support |
| Vite | 6 | Fast build tool with HMR |
| React Router | 7 | File-based routing |
| Zustand | 5 | Lightweight state management |
| Recharts | 3 | React-native charting |
| React-Force-Graph | 1.29 | WebGL graph visualization |
| Lucide React | - | Icon library |

### Backend

| Technology | Version | Purpose |
|------------|---------|---------|
| FastAPI | 0.100+ | Async web framework with OpenAPI |
| LangGraph | - | Agent workflow orchestration |
| LangChain | 0.3+ | LLM abstractions and prompts |
| Pydantic | 2.0+ | Runtime type validation |
| ChromaDB | 0.4+ | Vector database with hybrid search |
| SQLAlchemy | 2.0+ | ORM with async support |
| Sentence-Transformers | - | Local embeddings and reranking |
| OR-Tools | 9.8+ | Constraint optimization |

### Infrastructure

| Technology | Purpose |
|------------|---------|
| Docker | Containerization |
| Docker Compose | Multi-container orchestration |
| Uvicorn | ASGI server |

---

## Getting Started

### Prerequisites

- **Docker Desktop** (recommended) OR Node.js 20+ and Python 3.10+
- **LLM API Key** (supports various providers via LangChain)
- **8GB RAM** minimum (for sentence-transformer models)

### Quick Start (Docker)

```bash
# 1. Clone
git clone https://github.com/panic80/GovAI.git
cd GovAI

# 2. Configure
cp .env.example .env
# Edit .env with your API keys

# 3. Run
docker compose up --build

# 4. Access
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Manual Setup (without Docker)

```bash
# Terminal 1: Backend
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Terminal 2: Frontend (from project root)
cp .env.example .env
npm install
npm run dev
```

**Access:**
- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Environment Variables

```env
# Required - LLM Provider
GEMINI_API_KEY=your_api_key         # For Google Gemini
# OR
OPENAI_API_KEY=your_api_key         # For OpenAI

# Optional - Model Selection
LLM_FAST_MODEL=gemini-2.0-flash-lite
LLM_REASONING_MODEL=gemini-2.0-flash

# Optional - Limits
MAX_UPLOAD_SIZE_MB=10
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

---

## API Reference

### Agent Streaming Endpoints

All agent endpoints return JSONL streams for real-time progress updates.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agent/govlens/stream` | POST | RAG search with citations |
| `/api/agent/lexgraph/stream` | POST | Eligibility evaluation with trace |
| `/api/agent/foresight/stream` | POST | Resource optimization |
| `/api/agent/accessbridge/stream` | POST | Multimodal intake processing |

### Response Format

All streaming endpoints return JSONL (one JSON object per line):

```jsonl
{"node": "retrieve", "state": {"documents": [...], "trace_log": ["Step 1..."]}}
{"node": "generate", "state": {"final_answer": "...", "trace_log": ["Step 2..."]}}
{"node": "complete", "state": {}}
```

### Health Check

```bash
curl http://localhost:8000/health
# {"status": "healthy", "version": "1.0.0"}
```

---

## Development

### Project Structure

```
GovAI/
├── backend/
│   ├── agent/
│   │   ├── core/           # Shared LLM, streaming infrastructure
│   │   ├── govlens/        # RAG search agent
│   │   ├── lexgraph/       # Rules evaluation agent
│   │   ├── foresight/      # Optimization agent
│   │   └── accessbridge/   # Intake agent
│   ├── api/routers/        # FastAPI route handlers
│   ├── connectors/         # Data source connectors
│   ├── core/               # Config, models, logging
│   └── tests/              # pytest test suite
├── components/             # React components
│   ├── GovLens*.tsx        # Search UI
│   ├── LexGraph/           # Eligibility UI
│   ├── ForesightOps/       # Planning UI
│   └── AccessBridge/       # Intake UI
├── hooks/                  # React streaming hooks
├── services/               # API client, audio, translation
├── stores/                 # Zustand state stores
└── docker-compose.yml
```

### Adding a New Agent

1. Create `backend/agent/newagent/state.py` - Define state TypedDict
2. Create `backend/agent/newagent/nodes.py` - Implement processing nodes
3. Create `backend/agent/newagent/graph.py` - Wire nodes into LangGraph
4. Add endpoint in `backend/api/routers/agents.py`
5. Create frontend hook `hooks/useNewAgentStream.ts`

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
npm run test
```

### Type Checking

```bash
# Backend
cd backend
mypy .

# Frontend
npx tsc --noEmit
```

---

## License

MIT License

Copyright (c) 2025 Albert Kim

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

<div align="center">

**Built for Government Service Excellence**

[Report Issues](https://github.com/panic80/GovAI/issues)

</div>
