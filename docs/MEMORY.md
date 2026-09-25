# JARVIS V2 — Memory Architecture & RAG Retrieval

## 1. Multi-Tier Memory Hierarchy

JARVIS implements a 5-tier cognitive memory model:

1. **Working Memory (In-Memory Ring Buffer):**
   - Retains the immediate multi-turn conversational context.
   - Dynamic sliding window with automated token trimming to keep context within provider limits.

2. **Short-Term Conversational History:**
   - Persisted session-level turns in SQLite / Supabase `messages` table.
   - Preserves user goals across momentary interruptions and tool observation chains.

3. **Semantic Long-Term Memory (Vector Space):**
   - 384-dimensional dense embeddings generated via local `sentence-transformers/all-MiniLM-L6-v2`.
   - Stored in Supabase `memories` table with `pgvector` indexing (`vector(384)` with HNSW/IVFFlat cosine distance).
   - Local fallback in SQLite using optimized NumPy cosine distance.

4. **Episodic & Relational Memory (Knowledge Graph):**
   - Graph entity connections stored in `memory_links`:
     `User -> Project -> Technology -> Preference -> Contact`.
   - Enables associative memory queries (e.g., "What was the project Setty worked on with FastAPI?").

5. **Document RAG Memory:**
   - Text and PDF ingestion engine (`memory/document.py`).
   - Token-aware chunking (500 words with 50-word overlap) indexed into searchable project context.

---

## 2. Multi-Factor Contextual Reranking

Raw vector distance alone often retrieves superficially similar but contextually irrelevant facts. JARVIS applies a 4-factor contextual reranking formula (`memory/reranker.py`):

$$\text{Final Score} = 0.50 \cdot \text{Sim} + 0.20 \cdot \text{Imp} + 0.15 \cdot \text{Recency} + 0.15 \cdot \text{Lexical}$$

- **$\text{Sim}$ (Semantic Similarity):** Cosine similarity between query and memory embedding.
- **$\text{Imp}$ (Importance):** User or model assigned importance rating (0.0 to 1.0).
- **$\text{Recency}$:** Exponential decay based on age in days:
  $$\text{Recency} = \max(0.1, 1.0 - \frac{\text{age\_days}}{365})$$
- **$\text{Lexical}$:** Exact keyword token overlap between query terms and memory text.

---

## 3. Natural Language Memory Commands

JARVIS natively parses voice and text directives:
- **Remember:** *"Jarvis, remember that my favorite IDE theme is Dracula."*
- **Forget:** *"Jarvis, forget my old phone number."*
- **Show Memories:** *"Jarvis, what do you remember about my setup?"*
- **Clear Memories:** Triggers confirmation-gated memory purge.
