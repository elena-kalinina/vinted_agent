import os
import io
import pdb
from curl_cffi import requests
from pathlib import Path
from typing import List
from google import genai
import google.generativeai as genai
import json
from google.ai.generativelanguage_v1beta.types import content
from collect_data import searchVinted
from api import SearchArgs
from vinted.models.items import User, Item, DetailedItem
from vinted_search_test import HEADERS

# loading mappings:
# data = io.open("Data/status.json", 'r', encoding="utf-8")
# myjson = json.load(data)

# 1. SETUP
# Get your key from https://aistudio.google.com/ and set GEMINI_API_KEY environment variable
from dotenv import load_dotenv
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY", ""))
session = requests.Session(impersonate="chrome120")
session.headers.update(HEADERS)
# client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# main_vinted_agent.py
colors_file = io.open("DATA/color.json", "r", encoding="utf-8")
COLORS_FR = json.load(colors_file)
conditions_file = io.open("DATA/status.json", "r", encoding="utf-8")
CONDITIONS_FR =json.load(conditions_file)
brands_file = io.open("DATA/brand.json", "r", encoding="utf-8")
BRANDS = json.load(brands_file)
materials_file = io.open("DATA/material.json", "r", encoding="utf-8")
MATERIALS_FR = json.load(materials_file)
sizers_file = io.open("DATA/size.json", "r", encoding="utf-8")
SIZE = json.load(sizers_file)
CATALOG_FR = json.load(open("DATA/catalog.json", "r", encoding="utf-8"))

from user_profile import USER_PROFILE
from vinted_sizes import CATALOGS


def gemini_describe_photo(image_path: Path) -> str:
    '''
    this function gets a textual description of a photo from Gemini
    :param image_path: photo to describe
    :return: textual description of the photo
    '''
    model = genai.GenerativeModel("gemini-2.5-flash")
    image_file = genai.upload_file(image_path)
    result = model.generate_content(
        [image_file, "\n\n", "break down the outfit in the photo in a list of key items, comma-separated, max four, so that "
                             "each item from the list could be used in a search engine"]
    )
    print(f"{result.text=}")
    return result.text

def apply_user_context(llm_params, vinted_params):

    # 1. Standard Params
    # (Map price, order, search_text as before...)

    # 2. DETECT CONTEXT
    # Did the LLM find a macro category? e.g. "WOMEN_SHOES"
    if type(llm_params) is list:
        llm_params = llm_params[0]
    context = llm_params.get('macro_category', 'WOMEN_CLOTHES')  # Default to Women Clothes if unsure

    # 3. APPLY CATALOG FILTER
    # Always narrow the search to the category to prevent "Size 38" finding random stuff
    if context in CATALOGS:
        vinted_params['catalog_ids'] = [CATALOGS[context]]

    # 4. APPLY SIZE LOGIC
    # Case A: User explicitly asked for a size in the query ("Size 40 dress")
    if 'size' in llm_params:
        # logic to map specific text size to ID...
        pass

        # Case B: User didn't specify size -> USE PROFILE DEFAULTS
    else:
        # Check if the user has a default for this specific context (e.g. WOMEN_SHOES)
        default_sizes = USER_PROFILE['defaults'].get(context)
        if default_sizes:
            print(f"✨ Auto-applying User Size for {context}: {default_sizes}")
            vinted_params['size_ids'] = default_sizes

    return vinted_params


def map_text_to_vinted_ids(llm_params):
    mapped_params = {}

    # Pass through standard fields
    for key in ['search_text', 'price_to', 'price_from', 'order']:
        if key in llm_params:
            mapped_params[key] = llm_params[key]

    # --- MAP COLORS (French) ---
    if 'color' in llm_params:
        # Lowercase everything: "Rouge" -> "rouge"
        color_input = llm_params['color'] # .lower()
        found = False
        for color in COLORS_FR:
            if color_input == color["title"]:
                mapped_params['color_ids'] = [color["id"]]
                found = True
                break
            else:
                # Fallback: Try to find partial match (e.g. LLM says "bleu marine", Map has "bleu")
                # This is a simple "Startswith" check.
                for item in COLORS_FR:
                    if item["title"].lower() in color_input:  # If "bleu" is inside "bleu marine"
                        mapped_params['color_ids'] = [item["id"]]
                        found = True
                        break

        if not found:
            print(f"⚠️ Color '{color_input}' not found in map. Added to text search.")
            mapped_params['search_text'] = f"{mapped_params.get('search_text', '')} {llm_params['color']}"

    # --- MAP CONDITIONS (French) ---
    if 'condition' in llm_params:
        cond_input = llm_params.get('condition', '') #.lower() # actually agentic reasoning required here, whether 1 size id or more !!!
        for item in CONDITIONS_FR:
            if cond_input == item['title']:
                mapped_params['status_ids'] = [item['id']]
    # ... Repeat for Material/Brand ...

    if 'brand_title' in llm_params:
        # Lowercase everything: "Rouge" -> "rouge"
        brand_input = llm_params['brand_title'] # .lower()

        for item in BRANDS:
            if brand_input == item["title"] or brand_input.lower() == item['slug']:
                mapped_params['brand_ids'] = [item["id"]]

    if 'material' in llm_params:
        mapped_params['search_text'] = f"{mapped_params.get('search_text', '')} {llm_params['material']}"

    return mapped_params

def search_products_params(search_args: SearchArgs) -> List[Item]:
    '''
        This function is used to search products on vinted corresponding to a set of parameters. .
        These parameters include:
        - color
        - brand
        - size
        - catalog
        - material
        - status
        - country
        - text query
        Input: search_args: SearchArgs (dataclass)
        Returns: list of objects of type Item, each containing detailed product information
        '''

    items = searchVinted(searchText=search_args.search_text,
                         color=search_args.color,brand=search_args.brand,
                         size=search_args.size,
                         material=search_args.material,status=search_args.status,country=search_args.country)
    return items


def translate_query_to_vinted_params(user_query):

    # 2. MODEL CONFIGURATION
    # We use 'response_mime_type' to force JSON output.
    # Note: In Dec 2025, check if the model name is 'gemini-3.0-pro' or similar.
    # If 3.0 isn't in your list yet, fallback to 'gemini-1.5-pro'
    # model_name = "gemini-2.5-flash"  # Change to "gemini-3.0-pro" if available

    # 3. THE PROMPT
    # We define the schema in the prompt to ensure correct fields
    # translator.py

    # ... setup code ...


    print(f"🧠 Gemini thinking... Translating '{user_query}' to French Vinted filters...")

    # ... model setup ...

    system_prompt = """
    You are an Expert Fashion Stylist and Vinted Search Engine.
    
    YOUR GOAL: 
    Analyze the input text (which describes an outfit or a list of items) and break it down into a JSON LIST of separate searchable items.

    FOR EACH ITEM DETECTED:
    1. **Expand the Style:** If the description implies a vibe or a style (e.g., "Boheme", "Y2K", "Office"), turn the 'search_text' into a description of that item that fits this style.
    2. **Translate Filters:** Convert specific attributes (Color, Condition, Material) into FRENCH.
    3. **Detect Category:** Assign a 'macro_category' to help with sizing.
    
    
    Output JSON Schema:
    - search_text (string): The original request (keep these in the User's original language or English) OR the descriptive search query you provided.
    - price_to (number): Max price.
    - price_from (number): Min price.
    - brand_title (string): Brand name (e.g., "Nike", "Zara").
    - size (string): Standard Vinted French size string (e.g., "S", "38", "One size").
    - color (string): The color in FRENCH (e.g., "Rouge", "Bleu", "Noir", "Beige").
    - condition (string): The condition in FRENCH (e.g., "Neuf avec étiquette", "Très bon état", "Satisfaisant").
    - material (string): The material in FRENCH (e.g., "Cuir", "Soie", "Coton").
    - macro_category (string): MUST be one of ["WOMEN_CLOTHES", "WOMEN_SHOES", "MEN_CLOTHES", "MEN_SHOES", "OTHER"]. 

    CRITICAL RULE: The values for 'color', 'condition', 'size', 'material', and 'catalog' MUST be translated into FRENCH, because our backend maps use French keys.
   
    Examples:
   
    
    Examples:
    1. User: "Red leather jacket new with tags"
       Output: {
         "search_text": "leather jacket", 
         "color": "Rouge", 
         "material": "Cuir", 
         "condition": "Neuf avec étiquette",
         "macro_category": "WOMEN_CLOTHES",
       }

    2. User: "Cheap blue high-waist jeans"
       Output: {
         "search_text": "high-waist jeans", 
         "color": "Bleu", 
         "order": "price_low_to_high",
         "macro_category": "WOMEN_CLOTHES",
       }
    
    3. User: "I want a boheme dress under 50 and cowboy boots"
        Output: 
        [
          {
            "search_text": "maxi dress floral printed with lace",
            "price_to": 50,
            "color": "Multicolore", 
            "macro_category": "WOMEN_CLOTHES"
          },
          {
            "search_text": "boots santiags en cuir",
            "macro_category": "WOMEN_SHOES"
          }
        ]

    Input: "Outfit with vintage levis 501, white tee and black leather blazer"
    Output:
    [
      {
        "search_text": "jeans high waist straight leg",
        "brand": "Levi\'s",
        "macro_category": "WOMEN_CLOTHES"
      },
      {
        "search_text": "t-shirt basic cotton",
        "color": "Blanc",
        "macro_category": "WOMEN_CLOTHES"
      },
      {
        "search_text": "blazer",
        "color": "Noir",
        "material": "Cuir",
        "macro_category": "WOMEN_CLOTHES"
      }
    ]

    (Note: If color isn't specified, add common colors for that style like black/gold for evening, but prioritize generic descriptive terms).
    
    Constraint:
    - Do NOT paraphrase the query if the user asks for a specific item (e.g. "Nike Air Force 1"). Only expand for vague Styles/Vibes.

    """

    # ... generate content ...
    # 4. EXECUTE
    try:
        # response = client.models.generate_content(
        #    model="gemini-2.5-flash",
        #    contents=f"{system_prompt}\n\nUser Request: {user_query}",
        # )

        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]

        model_name = "gemini-2.5-flash"  # Change to "gemini-3.0-pro" if available

        generation_config = {
            "temperature": 0.1,  # Low temp = more deterministic/precise
            "response_mime_type": "application/json",
        }

        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=generation_config,
            safety_settings=safety_settings,
        )
        response = model.generate_content(
            f"{system_prompt}\n\nUser Request: {user_query}"
        )

        # 5. PARSE
        # Since we forced JSON mime_type, text should be valid JSON
        return json.loads(response.text)

    except Exception as e:
        print(f"❌ Gemini Error: {e}")
        # Fallback safe search
        return {"search_text": user_query}


# --- TEST BLOCK ---
if __name__ == "__main__":
    # Test it
    user_input = gemini_describe_photo(Path('DATA/80s-fashion.jpg'))  # "blazer 90s style, white tee and mom's jeans"
    pdb.set_trace()
    # 2. Translate it using Gemini TODO improve prompt
    outfit_list = translate_query_to_vinted_params(user_input) # TODO if nothing found adjust the search tex agentically in a self improving manner
    for i, raw_item_params in enumerate(outfit_list):

        print(f"\n🔎 Processing Item {i + 1}: {raw_item_params.get('search_text')}")

        # A. Apply Personalization (Size Injection)
        # The 'apply_user_context' function needs to handle the 'macro_category' key
        mapped_params = map_text_to_vinted_ids(raw_item_params)
        vinted_params = apply_user_context(raw_item_params, mapped_params)

        # B. Map Text to IDs (Brands/Colors to French IDs)


        print(f"   ➡ Searching Vinted: {vinted_params['search_text']}")

        # C. Call API
        response = session.get(
            "https://www.vinted.fr/api/v2/catalog/items",
            headers=HEADERS,
            params=vinted_params,
            impersonate="chrome120"
        )

        # D. Display Top Result
        if response.status_code == 200:
            items = response.json().get('items', [])
            if items:
                top_pick = items[0]
                print(f"   ✅ Top Match: {top_pick['title']} - {top_pick['price']}") # {top_pick['currency_code']}
                print(f"      URL: {top_pick['url']}")
            else:
                print("   ⚠️ No items found.")
        else:
            print(f"   ❌ API Error: {response.status_code}")
