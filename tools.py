from curl_cffi import requests
import sys
import os
import pdb
# This adds the 'Vinted-data' directory to the list of places
# Python will look for modules.
sys.path.append(os.path.join(os.path.dirname(__file__), 'Vinted-data'))

from typing import Dict, List, Any, Union
from collect_data import searchVinted
from vinted_scraper import VintedScraper
from vinted import Vinted
from vinted.models.items import User, Item, DetailedItem # DetailedUser
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from api import VintedItem, VintedUser, SearchArgs

"""
Tools for the agent to perform Vinted searches
- simple search by keywords
- search full outfits ("brunch with friends")
- search outfit components ("what shoes should I wear with this")
- search by photo
- smart recommendations based on purchase history (what about proactive monitoring for an item ?)
- pricing recommendations
- interactive, i.e. allow refinements
- personalization: sizing, location, desired item condition, seller ratings

"""

load_dotenv()

# Load credentials from environment variables
vinted = Vinted(domain="fr")
REAL_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
REAL_COOKIE = "_vinted_fr_session=" + os.getenv("VINTED_SESSION_COOKIE", "")
MY_BEARER = "Bearer " + os.getenv("VINTED_BEARER_TOKEN", "")

# Inject into the wrapper's session
vinted.headers.update({
    "User-Agent": REAL_USER_AGENT,
    "Cookie": REAL_COOKIE,
    "Authorization": MY_BEARER,
})

HEADERS = {
    "User-Agent": REAL_USER_AGENT,
    # PASTE YOUR FULL COOKIE HERE
    "Cookie": REAL_COOKIE,
    # PASTE YOUR BEARER HERE
    "Authorization": MY_BEARER,
    # PASTE CSRF (Optional, but good to have)
    # "X-Csrf-Token": "..."
}


mcp = FastMCP(
    name="vinted_agent",
)
# app.include_router(mcp_router, prefix="/api/v1")
# https://www.vinted.be/api/v2/catalog/items?page=1&per_page=96&search_text=&catalog_ids=2632&order=relevance&size_ids=&brand_ids=&status_ids=&color_ids=13&material_ids=
# Request Method
# GET

#https://www.vinted.be/api/v2/catalog/items?page=1&per_page=96&time=1763304432&search_text=&catalog_ids=2632&order=relevance&size_ids=&brand_ids=14&status_ids=&color_ids=13&material_ids=
# Request Method
# GET

"""
adidas silver sneakers size 39
https://www.vinted.be/api/v2/catalog/items?page=1&per_page=96&time=1763304434&search_text=&catalog_ids=2632&order=relevance&size_ids=59&brand_ids=14&status_ids=&color_ids=13&material_ids=
Request Method
GET
Status Code

https://www.vinted.be/api/v2/catalog/items?page=1&per_page=96&time=1763304439&search_text=adidas+silver+samba+sneakers&catalog_ids=2632&order=relevance&size_ids=59&brand_ids=14&status_ids=&color_ids=13&material_ids=
Request Method
GET

https://www.vinted.be/api/v2/catalog/items?page=1&per_page=96&time=1763304799&global_search_session_id=c56bb4a0-d2df-4afd-882f-291f14bea813&search_text=adidas+silver+samba+sneakers&catalog_ids=&order=relevance&size_ids=59&brand_ids=&status_ids=&color_ids=&material_ids=
Request Method
GET

"""


# @mcp.tool()
def search_products_query(search_text: str) -> List[VintedItem]:
    '''
    This function is used to search products on vinted corresponding to a text query.
    Examples: silver samba sneakers adidas, sleeveless velvet black top, leather oversize blazer
    Input: search_text: str
    Returns: list of objects of type VintedItem, each containing detailed product information
    '''
    params = {
        "search_text": search_text
        # Add other query parameters like the pagination and so on
    }
   #  items = scraper.search(params)
    search_url = f"https://www.vinted.fr/api/v2/catalog/items?search_text={search_text}&page=1&per_page=10"
    response = requests.get(search_url, headers=HEADERS)
    # pdb.set_trace()
    if response.status_code == 200:
        # 3. PRINT THE WIN
        # The structure is usually data['items'] or data['catalog_items']
        data = response.json()
        items = data.get('items', [])

        if items:
            print(f"✅ SUCCESS! Found {len(items)} items.")
            first_item = items[0]
            print(f"👕 Title: {first_item.get('title')}")
            print(f"💰 Price: {first_item.get('price')} {first_item.get('currency')}")
            print(f"🖼️ Photo: {first_item.get('photo', {}).get('url')}")
        else:
            print("⚠️ Authorized, but found 0 items. Check your search_text.")

    elif response.status_code == 401 or response.status_code == 403:
        print("❌ 401 Unauthorized. Your Bearer token or Cookie might have typos.")
    else:
        print(f"❌ Error {response.status_code}: {response.text}")
    # print ([item.title for item in items[:15]])
    return items

# @mcp.tool()
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
    if items:
        return items # .items
    else:
        return []

# @mcp.tool()
def get_product_details(product_id: int) -> DetailedItem:
    '''
    This function returns a detailed product details object.
    Input: product_id: int
    Returns: DetailedItem
    '''
    item = vinted.item_info(product_id)
    return item.item

# @mcp.tool()
def get_user_details(user_id: int) -> User:
    '''
    This function returns a detailed user description object.
    Input: user_id: int
    Returns: DetailedUser
    '''
    user_details = vinted.user_info(user_id)
    return user_details.user

# @mcp.tool()
def filter_search_results(search_results: List[Union[Item, DetailedItem]]) -> List[Union[Item, DetailedItem]]:
    pass



if __name__ == "__main__":

   # mcp.run(transport="sse")
    products = search_products_query("levis 501")
    #pdb.set_trace()
   # if products:
   #     print(len(products), [product.title for product in products])
   #     product_ids = [product.id for product in products]
   #     user_ids = [product.user.id for product in products]
   #     for prid in product_ids:
   #         print(get_product_details(prid))
   #     for usid in user_ids:
   #         print(get_user_details(usid))

        #print(len(products), [(product.title, product.id, product.user.id) for product in products[:5]])
    # else:
     #   print("No products found")

    search_args = SearchArgs(size=["39"], brand=["adidas"], search_text="samba sneakers")
    param_products = search_products_params(search_args)
    pdb.set_trace()
    print(len(param_products), [(product['title'], product['id'], product['user']['id'], product['brand_title']) for product in param_products[:10]])
   # except Exception as e:
    #   print(e)
