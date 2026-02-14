# user_profile.py
from vinted_sizes import WOMEN_CLOTHES_SIZES, WOMEN_SHOES_SIZES

# The User says: "I am a Woman, Size M in clothes, Size 38 in shoes."
USER_PROFILE = {
    "defaults": {
        "WOMEN_CLOTHES": [WOMEN_CLOTHES_SIZES["M"]],      # e.g., [3]
        "WOMEN_SHOES":   [WOMEN_SHOES_SIZES["38"]],       # e.g., [57]
        "MEN_CLOTHES":   [], # No default
    }
}