import operator
import os
from curl_cffi import requests
from typing import Annotated, List, TypedDict, Dict
from langgraph.graph import StateGraph, END, START
from langgraph.constants import Send


from translator import translate_query_to_vinted_params, map_text_to_vinted_ids, \
    apply_user_context  # Your existing splitter function
from vinted_search_agent import expand_condition_logic, node_search_vinted, node_critic, node_refiner

from dotenv import load_dotenv
from vinted_search_test import HEADERS

load_dotenv()
# Google API key loaded from environment variable GOOGLE_API_KEY

session = requests.Session(impersonate="chrome120")
session.headers.update(HEADERS)

# --- WORKER STATE (Same as before) ---
# Used by the single-item search agent
class ItemState(TypedDict):
    # Input
    item_definition: dict  # The params from the splitter
    user_query: str  # "Boheme outfit" (for context)

    # Internal
    vinted_params: Annotated[dict, lambda a, b: {**a, **b}]
    items_found: List[dict]
    critique_reason: str
    attempt_count: int
    status: str  # "searching", "success", "failed"

    # Output
    final_selected_item: dict  # The best item found


# --- SUPERVISOR STATE (The Big Picture) ---
class OutfitState(TypedDict):
    user_query: str  # "Boheme dress with texas boots"
    outfit_plan: List[dict]  # The list returned by the Splitter
    final_outfit_results: Annotated[List[dict], operator.add]  # Accumulates results from workers


def node_outfit_planner(state: OutfitState):
    print(f"👑 SUPERVISOR: Planning outfit for '{state['user_query']}'")

    # 1. Use your existing Splitter LLM
    # It returns: [{'item_debug_name': 'Dress', ...}, {'item_debug_name': 'Boots', ...}]
    plan = translate_query_to_vinted_params(state['user_query'])
    # Mocked mapping:
    # params = {"search_text": state['user_query'], "status_ids": [3], "price_to": 20}

    print(f"👑 SUPERVISOR: Decomposed into {len(plan)} items.")
    return {"outfit_plan": plan}


# Reuse your existing node functions: node_search_vinted, node_critic, node_refiner
# Just ensure they use 'ItemState' now.

def node_worker_initialization(state: ItemState):
    """Prepares the worker state based on the Supervisor's definition"""
    print(f"👷 WORKER: Starting search for {state['item_definition']}")

    # Map the definition to vinted params (using your existing logic)
    # initial_params = map_text_to_vinted_ids(state['item_definition'])
    # Mocking for now:
    initial_params = state['item_definition']

    return {"vinted_params": initial_params, "attempt_count": 1}


def node_worker_finalize(state: ItemState):
    """Selects the top item to send back to the supervisor"""
    if state['items_found']:
        best_item = state['items_found'][0]
        return {"final_selected_item": best_item}
    return {"final_selected_item": {"title": "Not Found", "url": ""}}


# ... (Include node_search_vinted, node_critic, node_refiner here) ...

# BUILD THE WORKER GRAPH
worker_workflow = StateGraph(ItemState)
worker_workflow.add_node("init", node_worker_initialization)
worker_workflow.add_node("search", node_search_vinted)
worker_workflow.add_node("critic", node_critic)
worker_workflow.add_node("refiner", node_refiner)
worker_workflow.add_node("finalize", node_worker_finalize)

worker_workflow.set_entry_point("init")
worker_workflow.add_edge("init", "search")
worker_workflow.add_edge("search", "critic")


# The Logic Loop
def check_worker_status(state):
    if state['status'] == "success":
        return "finalize"
    if state['attempt_count'] > 3:
        return "finalize"  # Give up and return whatever we have
    return "refiner"


worker_workflow.add_conditional_edges("critic", check_worker_status, {"finalize": "finalize", "refiner": "refiner"})
worker_workflow.add_edge("refiner", "search")
worker_workflow.add_edge("finalize", END)

worker_app = worker_workflow.compile()


def distribute_tasks(state: OutfitState):
    """
    Takes the plan list and spawns a worker for each item.
    """
    tasks = []
    for item_def in state['outfit_plan']:
        # We prepare the input for the Worker State
        params = map_text_to_vinted_ids(item_def)
        new_params = expand_condition_logic(params)
        final_params = apply_user_context(item_def, new_params)
        worker_input = {
            "item_definition": final_params,
            "user_query": state['user_query'],  # Pass context down
            "items_found": [],
            "attempt_count": 0,
            "status": "start"
        }
        # We tell LangGraph: "Send this input to the 'worker_node'"
        tasks.append(Send("worker_node", worker_input))

    return tasks


def node_assembler(state: OutfitState):
    print("👑 SUPERVISOR: All workers finished. Assembling outfit...")

    results = state['final_outfit_results']

    # Optional: Supervisor Logic / Reasoning
    # "Did we find everything?" "Do the colors match?"

    summary = []
    for item in results:
        summary.append(f"- {item.get('title', 'Unknown')} ({item.get('price', '?')})")

    print("\n✨ FINAL OUTFIT:")
    print("\n".join(summary))

    return {}  # Done


main_workflow = StateGraph(OutfitState)

main_workflow.add_node("planner", node_outfit_planner)
# We add the compiled worker graph as a node
main_workflow.add_node("worker_node", worker_app)
main_workflow.add_node("assembler", node_assembler)

main_workflow.set_entry_point("planner")

# 🌟 THE CONDITIONAL FAN-OUT
# Instead of a normal edge, we use the distribute_tasks function
main_workflow.add_conditional_edges("planner", distribute_tasks, ["worker_node"])

# 🌟 THE FAN-IN
# Workers always go to assembler when done
main_workflow.add_edge("worker_node", "assembler")
main_workflow.add_edge("assembler", END)

app = main_workflow.compile()

# --- RUN IT ---
if __name__ == "__main__":
    query = "Boheme dress with texas boots"
    inputs = {"user_query": query, "final_outfit_results": []}

    print("🚀 STARTING OUTFIT ORCHESTRATOR...")
    app.invoke(inputs)

