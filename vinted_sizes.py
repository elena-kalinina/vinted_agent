# vinted_sizes.py

# CATALOG IDs (The Context)
CATALOGS = {
    "WOMEN_CLOTHES": 1904, # Example ID, check Vinted
    "WOMEN_SHOES": 1231,
    "MEN_CLOTHES": 2050,
    "MEN_SHOES": 1242
}

# SIZE MAPS (Context-Specific)
# These IDs are examples. You must verify them via Network Tab!
WOMEN_CLOTHES_SIZES = {
    "XS": 1, "S": 2, "M": 3, "L": 4, "XL": 5,
    "34": 1, "36": 2, "38": 3, "40": 4, "42": 5,  # Mapped to same IDs usually
}

WOMEN_SHOES_SIZES = {
    "36": 55, "37": 56, "38": 57, "39": 58, "40": 59
}

MEN_CLOTHES_SIZES = {
    "S": 201, "M": 202, "L": 203
}