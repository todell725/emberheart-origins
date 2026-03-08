"""
RAG (Retrieval Augmented Generation) Engine
Semantic search over D&D reference materials using vector embeddings
"""

import json
import logging
import pickle
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import hashlib

logger = logging.getLogger("RAG_Engine")

# Try to import sentence transformers for embeddings
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    logger.warning("sentence-transformers not installed. Install with: pip install sentence-transformers")


class RAGEngine:
    """
    Retrieval Augmented Generation Engine for D&D reference materials

    Uses semantic search to find relevant content from:
    - RAW_DND: Official D&D rules, spells, items, monsters
    - gamebooks_md: Campaign sourcebooks and scenarios
    """

    def __init__(self, docs_dir: Path):
        self.docs_dir = Path(docs_dir)
        self.raw_dnd_dir = self.docs_dir / "RAW_DND"
        self.gamebooks_dir = self.docs_dir / "gamebooks_md"

        self.index_file = self.docs_dir / ".rag_index.pkl"
        self.cache_file = self.docs_dir / ".rag_cache.json"

        self.documents = []  # List of {path, content, metadata}
        self.embeddings = None  # numpy array of embeddings
        self.model = None

        if EMBEDDINGS_AVAILABLE:
            # Use a lightweight, fast model
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("RAG Engine initialized with sentence-transformers")
        else:
            logger.warning("RAG Engine running in fallback mode (keyword search only)")

    def index_documents(self, force_rebuild: bool = False):
        """
        Index all D&D reference documents

        Args:
            force_rebuild: If True, rebuild index even if cache exists
        """
        # Check if index already exists
        if self.index_file.exists() and not force_rebuild:
            logger.info("Loading existing RAG index...")
            self._load_index()
            return

        logger.info("Building RAG index from markdown files...")

        # Index RAW_DND (official rules)
        if self.raw_dnd_dir.exists():
            self._index_directory(self.raw_dnd_dir, category="rules")

        # Index gamebooks (campaigns/scenarios)
        if self.gamebooks_dir.exists():
            self._index_directory(self.gamebooks_dir, category="campaigns")

        logger.info(f"Indexed {len(self.documents)} documents")

        # Generate embeddings if available
        if EMBEDDINGS_AVAILABLE and self.model:
            logger.info("Generating embeddings...")
            texts = [doc["content"][:512] for doc in self.documents]  # First 512 chars
            self.embeddings = self.model.encode(texts, show_progress_bar=True)
            logger.info(f"Generated {len(self.embeddings)} embeddings")

        # Save index
        self._save_index()

    def _index_directory(self, directory: Path, category: str):
        """Recursively index all markdown files in a directory"""
        for md_file in directory.rglob("*.md"):
            try:
                content = md_file.read_text(encoding='utf-8', errors='ignore')

                # Skip empty files
                if len(content.strip()) < 50:
                    continue

                # Extract metadata from path
                relative_path = md_file.relative_to(directory)

                # Parse title from first heading or filename
                title = self._extract_title(content, md_file.name)

                doc = {
                    "path": str(md_file),
                    "relative_path": str(relative_path),
                    "title": title,
                    "content": content,
                    "category": category,
                    "size": len(content),
                    "hash": hashlib.md5(content.encode()).hexdigest()
                }

                self.documents.append(doc)

            except Exception as e:
                logger.warning(f"Failed to index {md_file}: {e}")

    def _extract_title(self, content: str, filename: str) -> str:
        """Extract title from markdown content or filename"""
        lines = content.split('\n')
        for line in lines[:10]:  # Check first 10 lines
            line = line.strip()
            if line.startswith('# '):
                return line[2:].strip()
            if line.startswith('## '):
                return line[3:].strip()

        # Fallback to filename without extension
        return filename.replace('.md', '').replace('_', ' ')

    def search(self, query: str, top_k: int = 5, category: Optional[str] = None) -> List[Dict]:
        """
        Search for relevant documents

        Args:
            query: Search query
            top_k: Number of results to return
            category: Optional filter ("rules" or "campaigns")

        Returns:
            List of documents with relevance scores
        """
        if not self.documents:
            logger.warning("No documents indexed. Run index_documents() first.")
            return []

        # Filter by category if specified
        candidates = self.documents
        if category:
            candidates = [doc for doc in candidates if doc["category"] == category]

        if EMBEDDINGS_AVAILABLE and self.model and self.embeddings is not None:
            return self._semantic_search(query, candidates, top_k)
        else:
            return self._keyword_search(query, candidates, top_k)

    def _semantic_search(self, query: str, candidates: List[Dict], top_k: int) -> List[Dict]:
        """Semantic search using vector embeddings"""
        # Generate query embedding
        query_embedding = self.model.encode([query])[0]

        # Get embeddings for candidates
        candidate_indices = [self.documents.index(doc) for doc in candidates]
        candidate_embeddings = self.embeddings[candidate_indices]

        # Calculate cosine similarity
        similarities = np.dot(candidate_embeddings, query_embedding) / (
            np.linalg.norm(candidate_embeddings, axis=1) * np.linalg.norm(query_embedding)
        )

        # Get top-k results
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            doc = candidates[idx]
            results.append({
                **doc,
                "score": float(similarities[idx]),
                "rank": len(results) + 1
            })

        return results

    def _keyword_search(self, query: str, candidates: List[Dict], top_k: int) -> List[Dict]:
        """Fallback keyword-based search"""
        query_terms = query.lower().split()

        scored_docs = []
        for doc in candidates:
            content_lower = doc["content"].lower()
            title_lower = doc["title"].lower()

            # Score based on keyword matches
            score = 0
            for term in query_terms:
                # Title matches worth more
                score += title_lower.count(term) * 10
                # Content matches
                score += content_lower.count(term)

            if score > 0:
                scored_docs.append((score, doc))

        # Sort by score and take top-k
        scored_docs.sort(reverse=True, key=lambda x: x[0])

        results = []
        for score, doc in scored_docs[:top_k]:
            results.append({
                **doc,
                "score": score,
                "rank": len(results) + 1
            })

        return results

    def get_context(self, query: str, max_tokens: int = 2000, category: Optional[str] = None) -> str:
        """
        Get relevant context for a query (formatted for LLM consumption)

        Args:
            query: Search query
            max_tokens: Approximate max tokens to return
            category: Optional filter

        Returns:
            Formatted context string
        """
        results = self.search(query, top_k=5, category=category)

        if not results:
            return "No relevant D&D reference materials found."

        context_parts = []
        total_chars = 0
        max_chars = max_tokens * 4  # Rough approximation

        for result in results:
            # Extract a relevant snippet
            content = result["content"]
            title = result["title"]
            score = result.get("score", 0)

            # Get first 500 characters or find most relevant section
            snippet = self._extract_snippet(content, query)

            entry = f"## {title} (relevance: {score:.2f})\n{snippet}\n"

            if total_chars + len(entry) > max_chars:
                break

            context_parts.append(entry)
            total_chars += len(entry)

        return "\n---\n".join(context_parts)

    def _extract_snippet(self, content: str, query: str, snippet_length: int = 500) -> str:
        """Extract most relevant snippet from content"""
        query_terms = query.lower().split()

        # Try to find section with most query terms
        lines = content.split('\n')
        best_start = 0
        best_score = 0

        for i in range(len(lines)):
            # Check window of 10 lines
            window = '\n'.join(lines[i:i+10]).lower()
            score = sum(window.count(term) for term in query_terms)

            if score > best_score:
                best_score = score
                best_start = i

        # Extract snippet around best match
        snippet_lines = lines[best_start:best_start+10]
        snippet = '\n'.join(snippet_lines)

        # Truncate if needed
        if len(snippet) > snippet_length:
            snippet = snippet[:snippet_length] + "..."

        return snippet

    def find_item(self, item_name: str) -> Optional[Dict]:
        """Quick lookup for magic items"""
        results = self.search(item_name, top_k=1, category="rules")
        if results and "magic item" in results[0]["content"].lower():
            return results[0]
        return None

    def find_spell(self, spell_name: str) -> Optional[Dict]:
        """Quick lookup for spells"""
        results = self.search(spell_name, top_k=1, category="rules")
        if results and ("spell" in results[0]["content"].lower() or
                       "Spell Lists" in results[0]["content"]):
            return results[0]
        return None

    def find_monster(self, monster_name: str) -> Optional[Dict]:
        """Quick lookup for monsters"""
        results = self.search(monster_name, top_k=1, category="rules")
        if results:
            return results[0]
        return None

    def _save_index(self):
        """Save index to disk"""
        try:
            index_data = {
                "documents": self.documents,
                "embeddings": self.embeddings
            }

            with open(self.index_file, 'wb') as f:
                pickle.dump(index_data, f)

            logger.info(f"RAG index saved to {self.index_file}")
        except Exception as e:
            logger.error(f"Failed to save index: {e}")

    def _load_index(self):
        """Load index from disk"""
        try:
            with open(self.index_file, 'rb') as f:
                index_data = pickle.load(f)

            self.documents = index_data["documents"]
            self.embeddings = index_data["embeddings"]

            logger.info(f"Loaded {len(self.documents)} documents from index")
        except Exception as e:
            logger.error(f"Failed to load index: {e}")
            self.documents = []
            self.embeddings = None

    def get_stats(self) -> Dict:
        """Get statistics about the indexed content"""
        if not self.documents:
            return {"total_documents": 0}

        stats = {
            "total_documents": len(self.documents),
            "total_size_mb": sum(doc["size"] for doc in self.documents) / 1024 / 1024,
            "by_category": {},
            "has_embeddings": self.embeddings is not None
        }

        for doc in self.documents:
            category = doc["category"]
            if category not in stats["by_category"]:
                stats["by_category"][category] = 0
            stats["by_category"][category] += 1

        return stats


# Global instance
rag_engine = None

def get_rag_engine(docs_dir: Path = None) -> RAGEngine:
    """Get or create global RAG engine instance"""
    global rag_engine

    if rag_engine is None:
        if docs_dir is None:
            from core.config import ROOT_DIR
            docs_dir = ROOT_DIR / "docs"

        rag_engine = RAGEngine(docs_dir)

    return rag_engine
