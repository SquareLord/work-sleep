# Semantic Task Matching Setup

The application now uses AI-powered semantic similarity to match task names intelligently. This means it can understand that "math homework" and "calculus assignment" are similar, even without exact word matches.

## Quick Start (No API Key Required)

By default, the system will use **local keyword matching** if no API key is configured. This works fine but won't catch semantic similarities.

## Using AI Semantic Matching (Recommended)

### Option 1: Hugging Face API (FREE!)

1. Create a free account at https://huggingface.co/
2. Get your API token from https://huggingface.co/settings/tokens
3. Set the environment variable:

```bash
export HUGGINGFACE_API_KEY='hf_your_token_here'
```

4. Or add to your shell profile (~/.bashrc or ~/.zshrc):

```bash
echo "export HUGGINGFACE_API_KEY='hf_your_token_here'" >> ~/.bashrc
source ~/.bashrc
```

**Benefits:**
- 100% FREE for reasonable usage
- No credit card required
- Fast inference API
- Good quality embeddings

### Option 2: OpenAI API (Paid)

1. Get an API key from https://platform.openai.com/api-keys
2. Set the environment variable:

```bash
export OPENAI_API_KEY='sk-your_key_here'
```

3. Update the API provider in code (optional - edit `task_database.py`):

```python
# In get_similar_tasks method, change:
matcher = get_semantic_matcher('openai')  # instead of default 'huggingface'
```

**Benefits:**
- Higher quality embeddings
- Very fast API response
- More consistent results

**Cost:** ~$0.00002 per task comparison (extremely cheap)

## How It Works

When you enter a new task name:

1. **System checks** if you've done this exact task before
   - If yes → uses your learned weights from that task

2. **If new task**, system searches for similar tasks:
   - Converts task names to semantic embeddings via API
   - Computes similarity scores (0-100%)
   - Finds tasks with >30% similarity

3. **Transfers weights** from similar tasks:
   - Weighted average based on similarity scores
   - Example: "reading textbook" (80% match) + "studying notes" (60% match)
   - Your new task starts with smart initial weights!

## Example Matches

With semantic matching enabled:

- "math homework" ↔ "calculus assignment" (85% match)
- "reading book" ↔ "studying textbook" (78% match)  
- "coding project" ↔ "programming assignment" (82% match)
- "writing essay" ↔ "composing paper" (76% match)

Without semantic matching (keyword only):

- "math homework" ↔ "calculus assignment" (0% match - no shared words!)
- "reading book" ↔ "studying textbook" (0% match)

## Testing

After setting your API key, run the app and check the console:

```
✓ Using Hugging Face API for semantic matching
ℹ  No similar tasks found for 'math homework'. Using default weights.
```

Then add a similar task:

```
✓ Found 1 similar task(s) for 'calculus assignment':
  - 'math homework' (85.3% match)
  → Transferred weights from similar tasks
```

## Fallback Mode

If the API is unavailable or no key is set:
- System automatically falls back to local keyword matching
- Still works, just less intelligent about semantic relationships
- You'll see: `ℹ  Using local keyword matching (no API)`

## Privacy Note

- Task names are sent to the API for embedding generation
- Only task names are sent, no personal data or monitoring data
- Embeddings are computed on-the-fly, not stored by the API
- If privacy is a concern, use local-only mode (no API key)
