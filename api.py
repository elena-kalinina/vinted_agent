from dataclasses import dataclass, field
from enum import Enum
from typing import List, Any, Optional


@dataclass
class VintedItem:
    type: str

@dataclass
class VintedUser:
    user_id: str

@dataclass
class SearchArgs:
    color: List = field(default_factory=list)
    brand: List = field(default_factory=list)
    size: List = field(default_factory=list)
    material: List = field(default_factory=list)
    status: List = field(default_factory=list)
    country: List = field(default_factory=list)
    search_text: str = ""