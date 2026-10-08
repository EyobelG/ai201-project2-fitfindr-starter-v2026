"""
Your MCP server. ← UNIT 4, MILESTONE 1

Right now your tools only exist inside your own program. Nothing else can reach
them. MCP is an agreed shape you wrap a tool in so that anything speaking the
same protocol can call it — your agent today, a different agent tomorrow,
someone else's app after that.

**You're moving one tool. Not three.** The point is to see the seam.
`search_listings` is the one to move: it doesn't call the model, so nothing is
slow and nothing changes between runs while you're learning the shape.

    python mcp_server.py        starts the server (it will just sit there — that's right)
    python mcp_client.py        asks the server what it offers

─────────────────────────────────────────────────────────────────────────────
TODO — register one tool.

Uncomment the block below and fill it in. Three things matter:

  1. **The name.** Exactly what your agent will ask for.

  2. **The description.** This is the part that isn't code and matters most.
     Write it before you look at the example. You are not writing it for your
     agent — you're writing it for an agent someone else builds, that will
     never see your implementation. That isn't hypothetical; it's what every
     MCP server on the registry is.

     Two things to get right: name units and types ("price" is ambiguous,
     "max_price, in whole dollars" isn't), and state the empty case. Last unit
     the empty case was on your spec sheet for your loop's benefit. Here it's
     part of a published contract.

  3. **The typed inputs.** These come straight from your Tool Inventory. If the
     types here don't match your README, one of the two is wrong — fix it.

Then point your agent at it. In `run_agent()`, swap the direct call:

    results = search_listings(description, size, max_price)

for the MCP one:

    from mcp_client import call_tool
    results = call_tool("search_listings", {
        "description": description,
        "size": size,
        "max_price": max_price,
    })

**What comes back should not change.** If it does, that difference is your
first clue about what your tool was really returning before.

🛑 Stop rule: if this isn't connecting after 40 minutes, stop. Keep your direct
call, and write down in your README exactly where it broke — the error text and
the last thing that worked. Then carry on to Milestone 2. Everything after this
works with a direct call, and **a documented failure earns the point in full.**
─────────────────────────────────────────────────────────────────────────────
"""

from mcp.server.fastmcp import FastMCP

from tools import search_listings as _search_listings_impl  # noqa: F401 — you'll use this below
from tools import compare_prices as _compare_prices_impl

# log_level="WARNING" keeps the server from printing an INFO line for every
# request. Without it your terminal fills with "Processing request of type
# CallToolRequest" and the output you actually care about scrolls away.
mcp = FastMCP("fitfindr", log_level="WARNING")


# ── the one tool this server offers ───────────────────────────────────────────

@mcp.tool()
def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search a fixed catalogue of 40 secondhand clothing listings and return the
    ones matching a plain-language description, ranked best match first.

    Matching is keyword overlap against each listing's title, description,
    style tags, category, brand and colors; a listing sharing no keyword with
    `description` is never returned, so an empty or purely generic description
    yields nothing.

    Args:
        description: keywords for the wanted item, e.g. "vintage graphic tee".
                     Required, and the only field that ranks results.
        size:        a size label to filter by, matched case-insensitively on
                     whole tokens, not substrings — "S" does not match "US 9"
                     and "L" does not match "XL", while a listing sized
                     "One Size" matches any requested size. Omit to skip size
                     filtering. Sizes in this catalogue are lettered ("XS",
                     "S/M", "L"), US shoe ("US 9") or waist/length ("W30 L30").
        max_price:   price ceiling in whole US dollars, inclusive — 30 keeps a
                     $30.00 listing. Omit to skip price filtering.

    Returns:
        A list of at most 10 listing dicts, highest keyword score first. Each
        dict has the keys: id, title, description, category, style_tags (list
        of str), size (str), condition (str), price (float, US dollars),
        colors (list of str), brand (str, or null for most listings) and
        platform (str).

        Returns an empty list when nothing matches — an empty list, never null
        and never an error. An empty list means the filters and keywords ruled
        everything out, and the caller should loosen the price ceiling, drop
        the size, or use fewer words.
    """
    return _search_listings_impl(description, size, max_price)


# ── a second tool on MCP (unit 4 stretch) ─────────────────────────────────────
#
# Same reasoning as the search: no model call, so the only thing this exercises
# is the protocol seam. Declared in the README before it was built.

@mcp.tool()
def compare_prices(new_item: dict) -> dict:
    """
    Say whether one secondhand listing is expensive or cheap for its own
    category, by comparing it against every other listing in that category.

    Args:
        new_item: a full listing dict, as returned by `search_listings`. Only
                  three of its keys are read: `category` (str), `price`
                  (float, US dollars) and `id` (str, so the item is not
                  compared against itself).

    Returns:
        A dict with these keys:
            category       (str)        the category compared within
            price          (float)      this item's own price, US dollars
            median         (float)      median price of that category,
                                        excluding this item
            cheaper_count  (int)        how many listings in the category
                                        undercut this one
            total          (int)        how many listings are in the category,
                                        excluding this item
            verdict        (str)        one of "above_median",
                                        "at_or_below_median" or
                                        "alone_in_category"
            cheaper        (list[dict]) up to two cheapest undercutting
                                        listings, each {id, title, price}

        When there is nothing to compare against: a category holding no other
        listing returns verdict "alone_in_category", `median` equal to the
        item's own price, `cheaper_count` 0 and `cheaper` an empty list. An
        item whose category is missing from the data is treated the same way.
        It never returns null and never raises, so a caller can read `verdict`
        unconditionally.
    """
    return _compare_prices_impl(new_item)

# ──────────────────────────────────────────────────────────────────────────────
#
# Two notes on the block above.
#
# The registered name is the *function* name — so the block above registers
# "search_listings", which is exactly what call_tool("search_listings", ...)
# asks for. That is also why the import at the top of this file brings the real
# implementation in under an alias: without it, the registered function and the
# one it calls would be the same name, and the tool would call itself.
#
# FastMCP builds the input schema from your type hints, which is why the hints
# are not optional here. `description: str` becomes a required string;
# `max_price: float | None = None` becomes an optional number. Getting these
# wrong is the most common reason a call is rejected.


if __name__ == "__main__":
    mcp.run()
