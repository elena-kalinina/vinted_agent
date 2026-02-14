# Vinted Search Agent

An AI-powered multi-agent system for intelligent product search on Vinted. Built with LangGraph and Google Gemini, this agent can understand natural language queries, decompose outfit requests into individual items, and search Vinted's catalog with smart filtering and refinement.

## Features

- **Natural Language Search**: Describe what you're looking for in plain English (e.g., "cheap blue high-waist jeans")
- **Outfit Decomposition**: Request complete outfits and the agent breaks them into searchable items (e.g., "Boheme dress with cowboy boots")
- **Photo-to-Search**: Upload a photo and get item descriptions to search for similar pieces
- **Smart Query Translation**: Automatically translates colors, conditions, and materials to French Vinted filters
- **Multi-Agent Architecture**: Supervisor agent coordinates worker agents for parallel item searches
- **Self-Refining Search**: Critic agent evaluates results and refines queries if they don't match user intent
- **User Profile Integration**: Automatic size injection based on saved preferences

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Outfit Supervisor                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐      │
│  │   Planner   │───▶│  Workers    │───▶│  Assembler  │      │
│  └─────────────┘    └─────────────┘    └─────────────┘      │
│                           │                                  │
│                     ┌─────┴─────┐                            │
│                     ▼           ▼                            │
│               ┌─────────┐ ┌─────────┐                        │
│               │ Worker 1│ │ Worker 2│  (parallel searches)   │
│               └─────────┘ └─────────┘                        │
│                     │           │                            │
│                     ▼           ▼                            │
│               Search → Critic → Refiner (retry loop)         │
└─────────────────────────────────────────────────────────────┘
```

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/vinted_agent.git
cd vinted_agent
```

### 2. Create virtual environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

- **VINTED_SESSION_COOKIE**: Get from browser DevTools → Application → Cookies → `_vinted_fr_session`
- **VINTED_BEARER_TOKEN**: Get from browser DevTools → Network tab → look for API requests with `Authorization: Bearer ...` header
- **GEMINI_API_KEY** / **GOOGLE_API_KEY**: Get from [Google AI Studio](https://aistudio.google.com/)

### 5. Prepare data files

The `DATA/` folder should contain Vinted filter mappings (colors, brands, sizes, etc.). These JSON files are used to translate text filters to Vinted API IDs.

## Usage

### Single Item Search Agent

```bash
python vinted_search_agent.py
```

This runs the self-refining search agent that:
1. Translates your query to Vinted parameters
2. Searches the API
3. Critiques results against original intent
4. Refines and retries if needed (up to 3 attempts)

### Multi-Agent Outfit Search

```bash
python vinted_search_multiagent.py
```

This runs the full orchestrator that:
1. Decomposes outfit requests into individual items
2. Spawns parallel worker agents for each item
3. Each worker runs the search-critique-refine loop
4. Assembles final results

### Photo-to-Search

```python
from translator import gemini_describe_photo
from pathlib import Path

# Get item descriptions from a photo
items = gemini_describe_photo(Path("your_photo.jpg"))
```

## Project Structure

```
vinted_agent/
├── vinted_search_agent.py      # Single-item search agent with LangGraph
├── vinted_search_multiagent.py # Multi-agent outfit orchestrator
├── translator.py               # Gemini-powered query translation
├── collect_data.py             # Vinted API search functions
├── tools.py                    # MCP tools and API wrappers
├── vinted_search_test.py       # API connection test
├── user_profile.py             # User size/preference profiles
├── vinted_sizes.py             # Size and catalog mappings
├── api.py                      # Data classes
├── DATA/                       # Vinted filter mappings (JSON)
└── Vinted-data/                # External Vinted data library
```

## Configuration

### User Profile

Edit `user_profile.py` to set your default sizes:

```python
USER_PROFILE = {
    "defaults": {
        "WOMEN_CLOTHES": [WOMEN_CLOTHES_SIZES["M"]],
        "WOMEN_SHOES": [WOMEN_SHOES_SIZES["38"]],
    }
}
```

## Notes

- The Vinted API requires valid session cookies and bearer tokens which expire periodically
- This project uses `curl_cffi` to impersonate Chrome's TLS fingerprint and bypass bot detection
- Search results are in French (Vinted FR domain) - modify `vinted = Vinted(domain="fr")` for other regions

## License

MIT
