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