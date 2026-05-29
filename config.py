# config.py

PROVIDER = "ollama"   # "ollama" | "anthropic" | "openai"

# --- Ollama (local) ---
OLLAMA_BASE_URL    = "http://localhost:11434/v1"
OLLAMA_CHAT_MODEL  = "mistral-small:latest"
OLLAMA_EMBED_MODEL = "nomic-embed-text"

# --- Anthropic ---
ANTHROPIC_API_KEY  = ""
ANTHROPIC_MODEL    = "claude-sonnet-4-5"

# --- OpenAI ---
OPENAI_API_KEY     = ""
OPENAI_CHAT_MODEL  = "gpt-4o-mini"
OPENAI_EMBED_MODEL = "text-embedding-3-small"

# --- Shared agent settings ---
MAX_ITERATIONS = 3
TOP_K_CHUNKS   = 3

# --- Model routing ---
# Simple questions use the FAST model (cheap, low latency)
# Complex questions use the CAPABLE model (better reasoning)
# Ollama: same model for both — routing still works, just no cost difference
FAST_MODEL     = OLLAMA_CHAT_MODEL    # swap to "gpt-4o-mini" or "claude-haiku-3"
CAPABLE_MODEL  = OLLAMA_CHAT_MODEL    # swap to "gpt-4o" or "claude-sonnet-4-5"

# Routing thresholds
# Questions needing multi-doc synthesis or above this chunk count → CAPABLE model
COMPLEX_CHUNK_THRESHOLD = 2    # if answer requires chunks from 2+ documents
COMPLEX_QUERY_KEYWORDS  = [    # keywords that signal complexity
    "compare", "difference between", "summarize", "explain",
    "how does", "why does", "what are all", "list all",
]

# --- Streaming ---
STREAM_ENABLED = True    # stream synthesis output token by token