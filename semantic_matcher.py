"""Semantic similarity matching for task names using AI embeddings via API."""
import numpy as np
from typing import List, Tuple, Optional
import json
import os

class SemanticMatcher:
    """
    Uses API-based embeddings to compute semantic similarity between task names.
    This allows the system to recognize that "math homework" and "calculus assignment" 
    are similar even if they don't share exact words.
    
    Supports multiple API providers:
    - Hugging Face Inference API (free tier available)
    - OpenAI Embeddings API
    - Fallback to local keyword matching
    """
    
    def __init__(self, api_provider: str = 'huggingface'):
        """
        Initialize semantic matcher with API provider.
        
        Args:
            api_provider: 'huggingface', 'openai', or 'none' for local only
        """
        self.api_provider = api_provider
        self.api_key = None
        self.model_name = None
        self._setup_api()
    
    def _setup_api(self):
        """Setup API credentials and model based on provider."""
        if self.api_provider == 'huggingface':
            # Check for Hugging Face API key
            self.api_key = os.environ.get('HUGGINGFACE_API_KEY') or os.environ.get('HF_TOKEN')
            self.model_name = 'sentence-transformers/all-MiniLM-L6-v2'
            
            if not self.api_key:
                print("⚠️  HUGGINGFACE_API_KEY not found in environment.")
                print("   Get a free API key from: https://huggingface.co/settings/tokens")
                print("   Set it with: export HUGGINGFACE_API_KEY='your_key_here'")
                print("   Falling back to keyword matching.")
                self.api_provider = 'none'
            else:
                print("✓ Using Hugging Face API for semantic matching")
                
        elif self.api_provider == 'openai':
            # Check for OpenAI API key
            self.api_key = os.environ.get('OPENAI_API_KEY')
            self.model_name = 'text-embedding-3-small'
            
            if not self.api_key:
                print("⚠️  OPENAI_API_KEY not found in environment.")
                print("   Get an API key from: https://platform.openai.com/api-keys")
                print("   Set it with: export OPENAI_API_KEY='your_key_here'")
                print("   Falling back to keyword matching.")
                self.api_provider = 'none'
            else:
                print("✓ Using OpenAI API for semantic matching")
        else:
            print("ℹ  Using local keyword matching (no API)")
    
    def _get_hf_embedding(self, text: str) -> Optional[np.ndarray]:
        """Get embedding from Hugging Face Inference API."""
        try:
            import requests
            
            api_url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{self.model_name}"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            
            response = requests.post(
                api_url,
                headers=headers,
                json={"inputs": text, "options": {"wait_for_model": True}}
            )
            
            if response.status_code == 200:
                embedding = np.array(response.json())
                # If the response is a list of embeddings, take the mean
                if len(embedding.shape) > 1:
                    embedding = np.mean(embedding, axis=0)
                return embedding
            else:
                print(f"HF API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Error calling Hugging Face API: {e}")
            return None
    
    def _get_openai_embedding(self, text: str) -> Optional[np.ndarray]:
        """Get embedding from OpenAI API."""
        try:
            import requests
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                "https://api.openai.com/v1/embeddings",
                headers=headers,
                json={"input": text, "model": self.model_name}
            )
            
            if response.status_code == 200:
                data = response.json()
                embedding = np.array(data['data'][0]['embedding'])
                return embedding
            else:
                print(f"OpenAI API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            return None
    
    def compute_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        Compute semantic embedding for a text string via API.
        
        Args:
            text: The text to embed
            
        Returns:
            Numpy array of embeddings, or None if API unavailable
        """
        if self.api_provider == 'huggingface':
            return self._get_hf_embedding(text)
        elif self.api_provider == 'openai':
            return self._get_openai_embedding(text)
        else:
            return None
    
    def compute_similarity(self, text1: str, text2: str) -> float:
        """
        Compute semantic similarity between two text strings.
        
        Args:
            text1: First text string
            text2: Second text string
            
        Returns:
            Similarity score between 0.0 and 1.0 (cosine similarity)
        """
        if self.api_provider == 'none':
            return self._jaccard_similarity(text1, text2)
        
        try:
            emb1 = self.compute_embedding(text1)
            emb2 = self.compute_embedding(text2)
            
            if emb1 is None or emb2 is None:
                return self._jaccard_similarity(text1, text2)
            
            # Compute cosine similarity
            similarity = np.dot(emb1, emb2) / (
                np.linalg.norm(emb1) * np.linalg.norm(emb2)
            )
            
            # Convert from [-1, 1] to [0, 1] range
            similarity = (similarity + 1) / 2
            return float(similarity)
            
        except Exception as e:
            print(f"Error computing similarity: {e}")
            return self._jaccard_similarity(text1, text2)
    
    def find_most_similar(self, query: str, candidates: List[Tuple[int, str]], 
                         threshold: float = 0.6, limit: int = 5) -> List[Tuple[int, str, float]]:
        """
        Find the most similar candidates to a query string.
        
        Args:
            query: The query text to match
            candidates: List of (id, text) tuples to compare against
            threshold: Minimum similarity score to include (0.0-1.0)
            limit: Maximum number of results to return
            
        Returns:
            List of (id, text, similarity) tuples sorted by similarity (highest first)
        """
        if not candidates:
            return []
        
        if self.api_provider == 'none':
            return self._fallback_similarity(query, candidates, threshold, limit)
        
        try:
            # Get query embedding
            query_emb = self.compute_embedding(query)
            if query_emb is None:
                return self._fallback_similarity(query, candidates, threshold, limit)
            
            # Get embeddings for all candidates (batch if possible)
            results = []
            
            for candidate_id, candidate_text in candidates:
                candidate_emb = self.compute_embedding(candidate_text)
                
                if candidate_emb is not None:
                    # Compute cosine similarity
                    similarity = np.dot(query_emb, candidate_emb) / (
                        np.linalg.norm(query_emb) * np.linalg.norm(candidate_emb)
                    )
                    # Convert from [-1, 1] to [0, 1]
                    similarity = (similarity + 1) / 2
                    
                    if similarity >= threshold:
                        results.append((candidate_id, candidate_text, float(similarity)))
            
            # Sort by similarity (descending)
            results.sort(key=lambda x: x[2], reverse=True)
            return results[:limit]
            
        except Exception as e:
            print(f"Error in semantic matching: {e}")
            return self._fallback_similarity(query, candidates, threshold, limit)
    
    def _jaccard_similarity(self, text1: str, text2: str) -> float:
        """Fallback: Simple Jaccard similarity based on word overlap."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if len(words1 | words2) == 0:
            return 0.0
        
        return len(words1 & words2) / len(words1 | words2)
    
    def _fallback_similarity(self, query: str, candidates: List[Tuple[int, str]], 
                            threshold: float, limit: int) -> List[Tuple[int, str, float]]:
        """Fallback similarity using Jaccard when API unavailable."""
        results = []
        query_words = set(query.lower().split())
        
        for candidate_id, candidate_text in candidates:
            candidate_words = set(candidate_text.lower().split())
            
            if len(query_words | candidate_words) > 0:
                similarity = len(query_words & candidate_words) / len(query_words | candidate_words)
                
                if similarity >= threshold:
                    results.append((candidate_id, candidate_text, similarity))
        
        results.sort(key=lambda x: x[2], reverse=True)
        return results[:limit]


# Global instance (lazy loaded)
_semantic_matcher = None

def get_semantic_matcher(api_provider: str = 'huggingface') -> SemanticMatcher:
    """
    Get or create the global semantic matcher instance.
    
    Args:
        api_provider: 'huggingface', 'openai', or 'none' for local only
    """
    global _semantic_matcher
    if _semantic_matcher is None:
        _semantic_matcher = SemanticMatcher(api_provider=api_provider)
    return _semantic_matcher
