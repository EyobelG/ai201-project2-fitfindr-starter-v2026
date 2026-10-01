"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop. Build and test them one at a time — three
untested tools joined by a loop is one problem that looks like six, because you
can't tell which layer is lying to you.

    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str

All three are stubs right now. They run and they do nothing — that's the
starting position and it's deliberate.

⚠️ Before you write any of them, fill in the **Tool Inventory** section of your
README (Milestone 2). Four lines per tool: what it does, each input with its
type, exactly what it returns, and what it returns when it has nothing to give.
That last line is what your loop branches on. "Returns a list" earns nothing —
the description has to say what is *in* the list.
"""

import re

import config  # noqa: F401 — you'll use this in search_listings
from generate import generate
from utils.data_loader import load_listings


# ── Tool 1: search_listings ───────────────────────────────────────────────────

_STOPWORDS = {
    "a", "an", "and", "the", "for", "with", "under", "over", "in", "of",
}


def _keywords(text: str) -> set[str]:
    """Lowercase words worth matching on, stopwords removed."""
    words = re.findall(r"[a-z0-9']+", (text or "").lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 1}


def _strip_price(text: str) -> str:
    """Remove price spans like "$30" so the number isn't matched as a keyword."""
    return re.sub(r"\$\s*\d+(?:\.\d+)?", " ", text or "")


def _size_tokens(size: str) -> set[str]:
    """
    Split a size string into comparable tokens.

    "S/M"      -> {"S", "M"}
    "W30 L30"  -> {"W30", "L30"}
    "US 8.5"   -> {"8.5"}
    "XL (oversized)" -> {"XL"}
    """
    s = (size or "").upper()
    s = re.sub(r"\(.*?\)", " ", s)        # drop parenthetical notes
    s = re.sub(r"\bUS\b", " ", s)         # "US 8" and "8" are the same size
    return {tok for tok in re.split(r"[\s/,]+", s) if tok}


def _size_match(wanted: str, listing_size: str) -> bool:
    """
    True when `wanted` is one of the sizes a listing is actually offered in.

    Token equality, not substring — "S" must not match "US 9", and "L" must
    not match "XL". "One Size" matches anything.
    """
    listing = (listing_size or "").upper()
    if "ONE SIZE" in listing:
        return True
    return bool(_size_tokens(wanted) & _size_tokens(listing_size))


def _haystack(listing: dict) -> set[str]:
    """Every word in a listing worth matching a query against."""
    parts = [
        listing.get("title", ""),
        listing.get("description", ""),
        " ".join(listing.get("style_tags") or []),
        listing.get("category", ""),
        listing.get("brand") or "",          # brand is None on most listings
        " ".join(listing.get("colors") or []),
    ]
    return _keywords(" ".join(parts))


def _score(wanted: set[str], listing: dict) -> int:
    """
    Keyword overlap, with title and style_tags worth more than description.

    A hit anywhere scores 1; a hit in the title or a style tag scores 2.
    """
    overlap = wanted & _haystack(listing)
    if not overlap:
        return 0
    strong = _keywords(
        listing.get("title", "") + " " + " ".join(listing.get("style_tags") or [])
    )
    return sum(2 if w in strong else 1 for w in overlap)

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the listings data for items matching a description, and optionally a
    size and a price ceiling.

    This is the tool that doesn't call the model, which makes it the easiest one
    to test and the one to move onto MCP in unit 4.

    Args:
        description: keywords describing what the user wants
                     (e.g. "vintage graphic tee").
        size:        a size string to filter by, or None to skip size filtering.
                     Match case-insensitively — "M" should match "S/M".

                     ⚠️ Read the sizes in the data before you reach for a plain
                     substring test. `"s" in "us 9"` is True, and so is
                     `"l" in "xl"`. A filter that returns shoes when someone
                     asked for a small top reads like a broken search, and it
                     will quietly cost you in unit 4 when you test criterion 1.
                     What counts as a size match is part of your spec — decide
                     it and write it into your Tool Inventory.
        max_price:   maximum price, inclusive, or None to skip price filtering.

    Returns:
        A list of matching listing dicts, best match first.
        **Returns an empty list when nothing matches — an empty list, not None,
        and not an exception.** Your loop branches on this.

    Each listing dict has these fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand (str or None), platform

    Note that `brand` is None for most listings. That is deliberate and
    realistic — thrift listings often have no brand. If something you write
    assumes a brand is always there, you will find out in unit 4.

    TODO:
        1. Load every listing with load_listings().
        2. Filter by max_price and by size, when each is provided.
        3. Score what's left by keyword overlap with `description`.
        4. Drop anything scoring zero.
        5. Sort by score, highest first, and return the listing dicts —
           at most config.SEARCH_RESULT_LIMIT of them.

    Test it from a terminal before you move on:
        python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
    """
    wanted = _keywords(_strip_price(description))

    scored = []
    for listing in load_listings():
        if max_price is not None and listing["price"] > max_price:
            continue
        if size is not None and not _size_match(size, listing["size"]):
            continue
        score = _score(wanted, listing)
        if score == 0:
            continue
        scored.append((score, listing))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [listing for _, listing in scored[: config.SEARCH_RESULT_LIMIT]]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest one or two outfits.

    This one calls the model, through `generate()`. You don't need to think
    about rate limits — the adapter handles pacing for you.

    Args:
        new_item: a listing dict — the item the user is considering.
        wardrobe: a wardrobe dict with an 'items' key holding a list of items.
                  **It may be empty.** Handle that.

    Returns:
        A non-empty string with outfit suggestions.
        With an empty wardrobe, return general styling advice rather than
        raising or returning "". Unit 4 has you trigger the empty wardrobe on
        purpose, so decide now what it should do.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If it is, ask the model for general styling ideas for this item.
        3. If it isn't, format the wardrobe items into the prompt and ask for
           specific combinations naming pieces the user already owns.
        4. Return the model's response.

    Test it from a terminal before you move on:
        python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
    """
    item_line = (
        f"{new_item.get('title')} — {new_item.get('category')}, "
        f"size {new_item.get('size')}, {new_item.get('condition')} condition, "
        f"${new_item.get('price')} on {new_item.get('platform')}. "
        f"Colors: {', '.join(new_item.get('colors') or []) or 'unlisted'}. "
        f"Style: {', '.join(new_item.get('style_tags') or []) or 'unlisted'}."
    )

    items = (wardrobe or {}).get("items") or []

    if not items:
        system = (
            "You style secondhand clothing. The user has nothing saved in their "
            "wardrobe yet, so you cannot name pieces they own. Give general "
            "styling ideas for the item instead, and say plainly that these are "
            "general ideas because the wardrobe is empty. Two or three sentences."
        )
        prompt = f"Item they are considering:\n{item_line}\n\nHow would you style it?"
    else:
        owned = "\n".join(
            f"- {i.get('name')} ({i.get('category')}; "
            f"{', '.join(i.get('colors') or []) or 'colors unlisted'}; "
            f"{', '.join(i.get('style_tags') or []) or 'no tags'})"
            for i in items
        )
        system = (
            "You style secondhand clothing. Suggest one or two outfits that pair "
            "the new item with pieces the user already owns. Name the owned "
            "pieces exactly as they are written. Never invent a piece that is "
            "not on the list. Two or three sentences."
        )
        prompt = (
            f"Item they are considering:\n{item_line}\n\n"
            f"What they already own:\n{owned}\n\n"
            "What should they wear it with?"
        )

    return generate(prompt, system=system)


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a short caption someone would actually post about the find.

    This calls the model too.

    Args:
        outfit:   the outfit suggestion string from suggest_outfit().
        new_item: the listing dict for the item.

    Returns:
        A two-to-four sentence caption.
        If `outfit` is empty or whitespace, return a descriptive message rather
        than raising.

    The caption should read like a real post rather than a product description,
    mention the item and its price and platform once each, and be specific about
    the vibe.

    It should also come out **differently for different inputs**. If you run
    this three times on the same item and get three word-for-word identical
    strings, it's one of two things, and both are near the top of `config.py`:

        • CACHE_ENABLED — the adapter handed back an answer it already had
        • TEMPERATURE   — at 0.0 the model gives the same words every time

    TODO:
        1. Guard against an empty or whitespace-only `outfit`.
        2. Build a prompt with the item details and the outfit.
        3. Call generate() and return the response.

    Test it from a terminal before you move on:
        python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
    """
    if not outfit or not outfit.strip():
        return (
            "No fit card — there is no outfit to write about. "
            "suggest_outfit() returned nothing."
        )

    system = (
        "You write short captions for secondhand fashion finds. Write like "
        "someone posting about a thing they are excited about, not like a "
        "product listing. Two to four sentences. Mention the item, its price "
        "and the platform once each. Be specific about the vibe."
    )
    prompt = (
        f"The find: {new_item.get('title')} — ${new_item.get('price')} on "
        f"{new_item.get('platform')} ({new_item.get('condition')} condition, "
        f"size {new_item.get('size')}).\n"
        f"Style tags: {', '.join(new_item.get('style_tags') or []) or 'none'}.\n\n"
        f"How they are styling it:\n{outfit.strip()}\n\n"
        "Write the caption."
    )

    return generate(prompt, system=system)
