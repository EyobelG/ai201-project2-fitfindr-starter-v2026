"""
Utility functions for loading the mock listings dataset and wardrobe schema.
Use these in your tool implementations to access the data without re-reading
the files each time.
"""

import json
import os
from typing import Optional

# Resolve the path to the data directory relative to this file
_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def load_listings() -> list[dict]:
    """
    Load all mock listings from the dataset.

    Returns:
        A list of listing dictionaries. Each listing has the following fields:
        - id (str)
        - title (str)
        - description (str)
        - category (str): one of tops, bottoms, outerwear, shoes, accessories
        - style_tags (list[str])
        - size (str)
        - condition (str): excellent, good, or fair
        - price (float)
        - colors (list[str])
        - brand (str or None)
        - platform (str): depop, thredUp, or poshmark
    """
    path = os.path.join(_DATA_DIR, "listings.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_wardrobe_schema() -> dict:
    """
    Load the wardrobe schema, including the example wardrobe and empty template.

    Returns:
        A dictionary containing:
        - schema: the field definitions for a wardrobe item
        - example_wardrobe: a sample wardrobe with 10 items
        - empty_wardrobe: a starting template for a new user
    """
    path = os.path.join(_DATA_DIR, "wardrobe_schema.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _wardrobe(name: str) -> dict:
    """
    Pull one wardrobe out of the schema file, without the documentation keys.

    The JSON uses underscore-prefixed keys (_description, _note) to explain
    itself to a human reader. Those are notes about the file, not part of a
    wardrobe, and stripping them here means both wardrobes below come back
    the same shape. Otherwise the empty one carries an extra _note key, and a
    tool that formats the whole dict into a prompt would send the model a
    sentence about templates.
    """
    wardrobe = load_wardrobe_schema()[name]
    return {k: v for k, v in wardrobe.items() if not k.startswith("_")}


def get_example_wardrobe() -> dict:
    """
    Convenience function — returns just the example wardrobe items list.

    Returns:
        A wardrobe dict with an 'items' key containing a list of wardrobe items.
    """
    return _wardrobe("example_wardrobe")


def get_empty_wardrobe() -> dict:
    """
    Convenience function — returns an empty wardrobe template.

    Returns:
        A wardrobe dict with an empty 'items' list. Same shape as the example
        wardrobe — the only difference is that 'items' is empty.
    """
    return _wardrobe("empty_wardrobe")


# --- Quick sanity check ---
if __name__ == "__main__":
    listings = load_listings()
    print(f"Loaded {len(listings)} listings.")
    print(f"First listing: {listings[0]['title']} — ${listings[0]['price']}")

    wardrobe = get_example_wardrobe()
    print(f"\nExample wardrobe has {len(wardrobe['items'])} items.")
    print(f"First item: {wardrobe['items'][0]['name']}")


# ── Style memory (stretch 3) ──────────────────────────────────────────────────
#
# The three functions above all return a fresh wardrobe read from the schema
# file, which is why nothing the agent does survives the process exiting. These
# two give it somewhere to write, declared in the README's Stretch Features
# section. They are opt-in: nothing calls them unless `--remember` is passed,
# so the default run loads the example wardrobe exactly as it did before.

_SAVED_WARDROBE = os.path.join(_DATA_DIR, "wardrobe_saved.json")


def load_saved_wardrobe() -> dict:
    """
    The wardrobe remembered from earlier runs.

    Returns:
        A wardrobe dict with an 'items' key. On the very first run — no file
        yet — this is the example wardrobe, so the agent starts from the same
        ten items the rest of the project is written against rather than from
        nothing. A file that exists but is corrupt is treated the same way.
    """
    if not os.path.exists(_SAVED_WARDROBE):
        return get_example_wardrobe()
    try:
        with open(_SAVED_WARDROBE, "r", encoding="utf-8") as f:
            saved = json.load(f)
    except (json.JSONDecodeError, OSError):
        return get_example_wardrobe()
    if not isinstance(saved, dict) or "items" not in saved:
        return get_example_wardrobe()
    return saved


def remember_item(wardrobe: dict, listing: dict) -> dict:
    """
    File a listing into the saved wardrobe and write it to disk.

    The listing dict and a wardrobe item dict are different shapes — a listing
    has a title, an id and a price; a wardrobe item has a name. So the fields
    that carry over are mapped rather than copied, and the listing id is kept
    so a second run can tell this came from a find rather than being typed in.

    Args:
        wardrobe: the wardrobe to add to — normally load_saved_wardrobe().
        listing:  the listing dict the agent just styled.

    Returns:
        The wardrobe, with the item added. An item whose id is already saved is
        not added twice, so re-running the same query doesn't grow the file.
    """
    items = list(wardrobe.get("items") or [])
    listing_id = listing.get("id")

    if any(item.get("from_listing") == listing_id for item in items):
        return {**wardrobe, "items": items}

    items.append({
        "name": listing.get("title"),
        "category": listing.get("category"),
        "colors": list(listing.get("colors") or []),
        "style_tags": list(listing.get("style_tags") or []),
        "from_listing": listing_id,
    })

    saved = {**wardrobe, "items": items}
    with open(_SAVED_WARDROBE, "w", encoding="utf-8") as f:
        json.dump(saved, f, indent=2)
    return saved
