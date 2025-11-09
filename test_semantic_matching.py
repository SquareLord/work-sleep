#!/usr/bin/env python3
"""Test semantic task matching functionality."""

from semantic_matcher import get_semantic_matcher

def test_semantic_matching():
    """Test the semantic matcher with example task names."""
    
    print("=" * 60)
    print("SEMANTIC TASK MATCHING TEST")
    print("=" * 60)
    print()
    
    # Initialize matcher
    matcher = get_semantic_matcher('huggingface')  # or 'openai' or 'none'
    print()
    
    # Example tasks
    print("Testing task similarity detection:")
    print("-" * 60)
    
    test_pairs = [
        ("math homework", "calculus assignment"),
        ("reading book", "studying textbook"),
        ("coding project", "programming assignment"),
        ("writing essay", "composing paper"),
        ("biology lab", "chemistry experiment"),
        ("history research", "math homework"),  # Should be low similarity
    ]
    
    for task1, task2 in test_pairs:
        similarity = matcher.compute_similarity(task1, task2)
        match_level = "🟢 HIGH" if similarity > 0.7 else "🟡 MEDIUM" if similarity > 0.4 else "🔴 LOW"
        print(f"{match_level}  '{task1}' ↔ '{task2}'")
        print(f"        Similarity: {similarity*100:.1f}%")
        print()
    
    print("-" * 60)
    print()
    
    # Test finding similar tasks
    print("Testing find_most_similar:")
    print("-" * 60)
    
    query = "calculus homework"
    candidates = [
        (1, "math assignment"),
        (2, "reading comprehension"),
        (3, "algebra problems"),
        (4, "chemistry lab"),
        (5, "statistics project"),
    ]
    
    print(f"Query: '{query}'")
    print(f"Candidates: {[name for _, name in candidates]}")
    print()
    
    similar = matcher.find_most_similar(query, candidates, threshold=0.3, limit=3)
    
    if similar:
        print("Top matches:")
        for task_id, name, score in similar:
            print(f"  {score*100:.1f}% - '{name}' (ID: {task_id})")
    else:
        print("No similar tasks found above threshold")
    
    print()
    print("=" * 60)
    print("Test complete!")
    print()
    print("💡 TIP: Set HUGGINGFACE_API_KEY to enable semantic matching")
    print("   Without it, the system uses basic keyword matching")
    print()

if __name__ == "__main__":
    test_semantic_matching()
