import operator
import os
import pdb
from typing import Annotated, List, TypedDict, Union
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from curl_cffi import requests

from dotenv import load_dotenv
from translator import translate_query_to_vinted_params, map_text_to_vinted_ids, apply_user_context
from vinted_search_test import HEADERS

load_dotenv()
# Google API key loaded from environment variable GOOGLE_API_KEY

session = requests.Session(impersonate="chrome120")
session.headers.update(HEADERS)

# IMPORT YOUR EXISTING MODULES
# from translator import translate_query_to_vinted_params
# from vinted_filters import CONDITIONS_FR
# from main_vinted_agent import map_text_to_vinted_ids, HEADERS (Your session headers)

# --- MOCKING IMPORTS FOR THIS EXAMPLE (Replace with your real files) ---

CONDITIONS_FR = {"neuf avec étiquette": 6, "neuf sans étiquette": 5, "très bon état": 4, "bon état": 3,
                 "satisfaisant": 2}

# TODO CHALLENGE: the whole outfit for a give price !!!
# TODO have user confirm breakdowns and / or refine search


# --- 1. THE STATE ---
class AgentState(TypedDict):
    user_query: str
    vinted_params: dict
    items_found: List[dict]
    critique_reason: str
    attempt_count: int
    status: str  # "searching", "success", "failed"


# --- 2. THE CONDITION WATERFALL ---
def expand_condition_logic(params: dict) -> dict:
    """
    If user asks for 'bon état' (3), automatically add 4, 5, and 6.
    """
    # Hierarchy: Best (6) to Worst (2)
    HIERARCHY = [6, 5, 4, 3, 2]

    current_ids = params.get('status_ids', [])
    if not current_ids:
        return params

    # Assuming we mapped single ID, pick the worst acceptable one the user chose
    # (e.g. if they said 'Good', ID is 3)
    base_condition = current_ids[0] if isinstance(current_ids, list) else current_ids

    if base_condition in HIERARCHY:
        index = HIERARCHY.index(base_condition)
        # We want everything from index 0 up to matching index
        # e.g. if index is 3 (ID 3), we want HIERARCHY[0:4] -> [6, 5, 4, 3]
        expanded_ids = HIERARCHY[:index + 1]

        print(f"🌊 Condition Waterfall: User asked {base_condition}, expanded to {expanded_ids}")
        params['status_ids'] = expanded_ids

    return params


# --- 3. THE NODES ---

llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=0)


def node_initial_plan(state: AgentState):
    print(f"🔵 NODE: Planning search for '{state['user_query']}'")

    # 1. Call your existing Level 3 Translator (Mocked here)
    raw_llm_json = translate_query_to_vinted_params(state['user_query'])
    # For demo, I simulate the LLM output:
    # raw_llm_json = {"search_text": state['user_query'], "condition": "bon état", "price_to": 20}

    # 2. Map to Vinted IDs (Your Level 2 Logic)
    params = map_text_to_vinted_ids(raw_llm_json)
    # Mocked mapping:
    # params = {"search_text": state['user_query'], "status_ids": [3], "price_to": 20}

    # 3. APPLY WATERFALL LOGIC
    new_params = expand_condition_logic(params)
    final_params = apply_user_context(raw_llm_json, new_params)

    return {"vinted_params": final_params, "attempt_count": 1}


def node_search_vinted(state: AgentState):
    print(f"🔵 NODE: Searching API... (Attempt {state['attempt_count']})")
    print(f"   Query: {state['vinted_params'].get('search_text')}")
    print(f"   Conditions: {state['vinted_params'].get('status_ids')}")

    url = "https://www.vinted.fr/api/v2/catalog/items"

    try:
        response = session.get(
            url,
            headers=HEADERS,
            params=state['vinted_params'],
            impersonate="chrome120"
        )
        if response.status_code == 200:
            items = response.json().get('items', [])
            return {"items_found": items}
        else:
            return {"items_found": [], "critique_reason": f"API Error {response.status_code}"}
    except Exception as e:
        return {"items_found": [], "critique_reason": f"Crash: {e}"}


def node_critic(state: AgentState):
    print("🔵 NODE: Critiquing Results against ORIGINAL Intent...")
    items = state['items_found']

    # Scenario A: Nothing found (unchanged)
    if not items:
        return {"status": "retry", "critique_reason": "0 items found."}

    # Scenario B: Analyze titles against User Intent
    titles = [item['title'] for item in items[:5]]
    current_keywords = state['vinted_params'].get('search_text')
    original_intent = state['user_query']

    # --- UPGRADED PROMPT ---
    prompt = f"""
    You are a strict Fashion Critic and Search Quality Auditor.

    1. ORIGINAL USER INTENT: "{original_intent}"
    2. CURRENT SEARCH KEYWORDS USED: "{current_keywords}"
    3. FOUND ITEM TITLES: {titles}

    Your Task:
    Determine if the FOUND ITEMS actually satisfy the ORIGINAL USER INTENT.

    Logic:
    - If the items match the Current Keywords but VIOLATE the Original Intent (Semantic Drift), you must FAIL.
    - Example: User wanted "Goth" -> We searched "Black Dress" -> Found "Black Office Dress". -> FAIL (Style mismatch).
    - Example: User wanted "Cyber Y2K" -> We searched "Floral Top" -> Found "Floral Top". -> FAIL (Total drift).

    Output:
    - If they match the vibe of the ORIGINAL query: output "PASS".
    - If they fail: output "FAIL: [Reason explaining the mismatch]".
    """

    response = llm.invoke(prompt).content.strip()
    print(f"🤔 Judge says: {response}")

    if response.startswith("PASS"):
        return {"status": "success"}
    else:
        # We pass the LLM's explanation back to the refiner so it knows WHY it failed
        return {"status": "retry", "critique_reason": response}

def node_refiner(state: AgentState):
    print("🔵 NODE: Refining Query...")
    original_intent = state.get('user_query')
    current_keywords = state['vinted_params']['search_text']
    critique = state['critique_reason']

    # --- UPGRADED PROMPT ---
    prompt = f"""
    We are trying to find items for: "{original_intent}"

    We tried searching for: "{current_keywords}"

    The Critic failed this search because: "{critique}"

    Your Task:
    Generate a NEW, BETTER 'search_text' string.

    Strategies:
    1. If the critique says "0 items", try removing specific filters or being broader.
    2. If the critique says "Style mismatch" or "Drift", REVERT to keywords closer to the "{original_intent}".
    3. Use synonyms that sellers actually use (e.g. instead of "Y2K", try "2000s", "00s", "rhinestone").

    Output ONLY the new search_text string. No explanation.
    """

    new_keywords = llm.invoke(prompt).content.strip()
    print(f"💡 Refiner proposes: {new_keywords}")

    # Update params
    new_params = state['vinted_params'].copy()
    new_params['search_text'] = new_keywords

    return {"vinted_params": new_params, "attempt_count": state['attempt_count'] + 1}

# --- 4. THE GRAPH LOGIC ---

workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("planner", node_initial_plan)
workflow.add_node("searcher", node_search_vinted)
workflow.add_node("critic", node_critic)
workflow.add_node("refiner", node_refiner)

# Set Entry
workflow.set_entry_point("planner")


# Conditional Logic
def check_results(state):
    if state['status'] == "success":
        return "end"
    if state['attempt_count'] > 3:  # Max 3 retries
        print("🛑 Max attempts reached. Giving up.")
        return "end"
    return "refine"


# Edges
workflow.add_edge("planner", "searcher")
workflow.add_edge("searcher", "critic")
workflow.add_conditional_edges(
    "critic",
    check_results,
    {
        "end": END,
        "refine": "refiner"
    }
)
workflow.add_edge("refiner", "searcher")  # Loop back to search

# Compile
app = workflow.compile()

# --- 5. EXECUTION ---
if __name__ == "__main__":
    # Test: A tricky query that might need refinement
    query = "Cyber Y2K top cheap"

    inputs = {"user_query": query, "attempt_count": 0, "status": "start"}

    print("\n🚀 STARTING EPIC AGENT...\n")
    final_state = app.invoke(inputs)

    print("\n🏁 FINAL REPORT:")
    if final_state['items_found']:
        print(f"Found {len(final_state['items_found'])} items.")
        print(f"Top Pick: {final_state['items_found'][0]['title']}")
        print(f"URL: {final_state['items_found'][0]['url']}")
    else:
        print("Failed to find items after multiple attempts.")