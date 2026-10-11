"""
The FitFindr planning loop.

This is the file that makes FitFindr an agent rather than a script. It decides
which tool to run next based on what the last one returned.

If your loop calls all three tools no matter what comes back, you have a list
of function calls. A loop looks at the last result before it picks the next
step. **That branch is the graded part of this unit.**

Build and test your three tools in `tools.py` first. Then come here.

    python agent.py          runs both example paths below
"""

import re

import config
import trace
from tools import suggest_outfit, create_fit_card
from mcp_client import call_tool, MCPError
from generate import ModelUnavailable


# ── reading the query ───────────────────────────────────────────

# Regex, not the model: parsing is deterministic, it costs no call, and a
# wrong answer here is something you can see rather than something you have to
# re-run five times to catch.

_PRICE_RE = re.compile(r"(?:under|below|less than|max|up to)?\s*\$\s*(\d+(?:\.\d+)?)", re.I)
# Longest alternatives first, or "XXS" matches as "XS" and "XL" as "L".
_SIZE_RE = re.compile(
    r"\bsize\s+("
    r"xxs|xxl|xs|xl|s/m|m/l|l/xl|s|m|l"
    r"|us\s*\d+(?:\.\d+)?|w\d+|\d+(?:\.\d+)?"
    r")\b",
    re.I,
)


def parse_query(query: str) -> dict:
    """
    Pull a description, a size and a price ceiling out of what the user typed.

    Returns a dict with 'description', 'size' and 'max_price'. Size and price
    are None when the query didn't mention them.
    """
    text = query or ""

    max_price = None
    price_hit = _PRICE_RE.search(text)
    if price_hit:
        max_price = float(price_hit.group(1))
        text = text[: price_hit.start()] + " " + text[price_hit.end() :]

    size = None
    size_hit = _SIZE_RE.search(text)
    if size_hit:
        size = size_hit.group(1).strip()
        text = text[: size_hit.start()] + " " + text[size_hit.end() :]

    description = " ".join(text.split())
    return {"description": description, "size": size, "max_price": max_price}


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.

    The session is the single source of truth for a run. Every tool result goes
    in here, and the next tool reads it back out.

    You could pass values straight from one call to the next. It would work,
    and you would not be able to test it — you can't print a variable you have
    already overwritten. Going through the session is what makes the state
    visible, and unit 4 has you write a criterion about exactly that.

    Add fields if you need them.
    """
    return {
        "query": query,              # what the user typed
        "parsed": {},                # description / size / max_price you pulled out of it
        "search_results": [],        # everything search_listings returned
        "selected_item": None,       # the one you chose — goes into suggest_outfit
        "price_check": None,         # what compare_prices returned (stretch tool 4)
        "price_note": None,          # set only when the price branch fires (stretch 2)
        "wardrobe": wardrobe,        # the user's wardrobe
        "outfit_suggestion": None,   # what suggest_outfit returned
        "fit_card": None,            # what create_fit_card returned
        "retry_dropped": None,       # the size filter dropped on a retry (stretch)
        "retry_note": None,          # what to tell the user about that retry
        "error": None,               # set when the run ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Run the loop once and return the finished session.

    Args:
        query:    what the user asked for, in plain language
                  (e.g. "vintage graphic tee under $30, size M").
        wardrobe: a wardrobe dict — get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py.

    Returns:
        The session dict. **Check session["error"] first** — if it isn't None,
        the run ended early and the later fields will still be None.

    ─────────────────────────────────────────────────────────────────────────
    TODO — build this, following the branch rule you wrote in Milestone 2.

      1. Start a session with new_session().

      2. Count the times round the loop, and call trace.check_iterations(count)
         on each one before you go again. It raises when the count passes
         MAX_ITERATIONS in config.py — see trace.py.

      3. Parse the query into a description, a size, and a max_price. Regex,
         string splitting, or asking the model are all fine — say which you
         chose in your README. Put the result in session["parsed"].

      4. Call search_listings() with what you parsed.
         Put the results in session["search_results"].

         ⚠️ THIS IS THE BRANCH. If nothing came back:
              - put a message in session["error"] saying what the user could
                change — "No results" is not that message
              - return the session
              - do NOT call suggest_outfit with nothing

      5. Choose an item — the first result is fine. Put it in
         session["selected_item"].

      6. Call suggest_outfit() with the selected item and the wardrobe.
         Put the result in session["outfit_suggestion"].

      7. Call create_fit_card() with the outfit and the item.
         Put the result in session["fit_card"].

      8. Return the session.

    ─────────────────────────────────────────────────────────────────────────
    IN UNIT 4 you come back and add two things:

      • Trace calls. One per step. `trace.step("search_listings", inputs=...,
        returned=...)` — see trace.py. Your README needs the output.

      • A handler for ModelUnavailable, so a bad key produces a message rather
        than a stack trace. The import is already at the top of this file.
    """
    session = new_session(query, wardrobe)
    trace.start_trace()
    count = 0

    # The loop picks its next step by reading the session, not by running a
    # fixed list. `step` is what it decided to do next; "done" ends the run.
    step = "parse"

    while step != "done":
        count += 1
        trace.check_iterations(count)

        if step == "parse":
            session["parsed"] = parse_query(query)
            trace.step("parse_query", inputs=query,
                       returned=str(session["parsed"]))
            step = "search"

        elif step == "search":
            parsed = session["parsed"]
            # search_listings lives on the MCP server now (mcp_server.py). The
            # call changes shape; the return value does not.
            try:
                session["search_results"] = call_tool("search_listings", {
                    "description": parsed["description"],
                    "size": parsed["size"],
                    "max_price": parsed["max_price"],
                })
            except MCPError as exc:
                session["error"] = f"The listing search is unavailable: {exc}"
                trace.step("search_listings (via MCP)", inputs=str(parsed),
                           note="MCP call failed: stopping before suggest_outfit")
                return session
            trace.step("search_listings (via MCP)", inputs=str(parsed),
                       returned=session["search_results"],
                       note=f"{len(session['search_results'])} match(es)")
            # STRETCH: before the branch fires, try once more without the
            # size filter. An empty search with a size in the parse has two
            # possible causes and the message cannot tell them apart — the
            # data holds nothing like this, or it holds it in other sizes.
            # One more search separates them. The description and the price
            # ceiling are kept; only the size is dropped.
            if not session["search_results"] and session["parsed"].get("size"):
                dropped = session["parsed"]["size"]
                try:
                    retry_results = call_tool("search_listings", {
                        "description": parsed["description"],
                        "size": None,
                        "max_price": parsed["max_price"],
                    })
                except MCPError as exc:
                    session["error"] = f"The listing search is unavailable: {exc}"
                    trace.step("search_listings (retry, via MCP)",
                               note="MCP call failed on the retry")
                    return session
                session["retry_dropped"] = dropped
                trace.step("search_listings (retry, via MCP)",
                           inputs=f"size dropped: {dropped!r}",
                           returned=retry_results,
                           note=f"{len(retry_results)} match(es) without the size filter")
                if retry_results:
                    session["search_results"] = retry_results
                    session["retry_note"] = (
                        f"Nothing matched in size {dropped}, so the size filter "
                        f"was dropped and the search run again. What follows is "
                        f"not in your size."
                    )
                    trace.step("branch",
                               note=f"retry without size {dropped!r} found "
                                    f"{len(retry_results)}: continuing")

            # THE BRANCH: nothing came back, so there is nothing to style.
            if not session["search_results"]:
                session["error"] = _no_results_message(session["parsed"])
                trace.step("branch",
                           note="search returned []: stopping before suggest_outfit")
                return session
            step = "select"

        elif step == "select":
            session["selected_item"] = session["search_results"][0]
            trace.step("select_item", returned=session["selected_item"])
            step = "price_check"

        elif step == "price_check":
            # The second tool on MCP (stretch). Same seam as the search.
            try:
                session["price_check"] = call_tool("compare_prices", {
                    "new_item": session["selected_item"],
                })
            except MCPError as exc:
                session["error"] = f"The price check is unavailable: {exc}"
                trace.step("compare_prices (via MCP)",
                           inputs=session["selected_item"],
                           note="MCP call failed: stopping before suggest_outfit")
                return session
            trace.step("compare_prices (via MCP)", inputs=session["selected_item"],
                       returned=str(session["price_check"]))
            # THE SECOND BRANCH: dear for its category, and something cheaper
            # exists to name. Note it and carry the note into the fit card.
            # selected_item is left alone on purpose — swapping it here would
            # break criterion 3.
            check = session["price_check"]
            if check["verdict"] == "above_median" and check["cheaper"]:
                session["price_note"] = _price_note(check)
                trace.step("branch", note="above median with a cheaper option: "
                                          "carrying a price note into the fit card")
            else:
                trace.step("branch", note=f"verdict {check['verdict']!r}: no price note")
            step = "outfit"

        elif step == "outfit":
            # Both remaining steps call the model, so both can fail in a way
            # the earlier steps cannot. Catching it here keeps the session —
            # the parse, the search results and the price check are already in
            # it, and they cost something to produce.
            try:
                session["outfit_suggestion"] = suggest_outfit(
                    session["selected_item"], session["wardrobe"]
                )
            except ModelUnavailable as exc:
                session["error"] = _model_down_message("suggest_outfit", exc)
                trace.step("suggest_outfit",
                           inputs=session["selected_item"],
                           note="model unavailable: stopping with no outfit")
                return session
            trace.step("suggest_outfit", inputs=session["selected_item"],
                       returned=session["outfit_suggestion"])
            # Branch again: no outfit text means no caption worth writing.
            step = "fit_card" if (session["outfit_suggestion"] or "").strip() else "done"

        elif step == "fit_card":
            try:
                session["fit_card"] = create_fit_card(
                    session["outfit_suggestion"],
                    session["selected_item"],
                    price_note=session["price_note"],
                )
            except ModelUnavailable as exc:
                # The outfit survived, so say so rather than throwing the run
                # away: the user still has something usable on screen.
                session["error"] = _model_down_message("create_fit_card", exc)
                trace.step("create_fit_card",
                           inputs=session["selected_item"],
                           note="model unavailable: outfit kept, no caption")
                return session
            trace.step("create_fit_card", inputs=session["selected_item"],
                       returned=session["fit_card"])
            step = "done"

        else:
            session["error"] = f"The loop reached an unknown step: {step!r}."
            return session

    return session


def _model_down_message(tool: str, exc: Exception) -> str:
    """Name the step that failed and what the user can do about it."""
    return (
        f"The model couldn't be reached, so {tool} didn't run. "
        f"{exc} "
        f"The listings search doesn't use the model, so searching still works "
        f"— rerun once the key is fixed to get the styling."
    )


def _price_note(check: dict) -> str:
    """One line on where this price sits, naming the cheapest alternative."""
    cheapest = check["cheaper"][0]
    return (
        f"${check['price']:.0f} is above the ${check['median']:.0f} median for "
        f"{check['category']}; {check['cheaper_count']} of "
        f"{check['total']} are cheaper, the lowest being "
        f"{cheapest['title']} at ${cheapest['price']:.0f}."
    )


def _no_results_message(parsed: dict) -> str:
    """Say what the user could change, not just that there was nothing."""
    loosen = []
    if parsed.get("max_price") is not None:
        loosen.append(f"raising the ${parsed['max_price']:.0f} ceiling")
    if parsed.get("size"):
        loosen.append(f"dropping the size {parsed['size']} filter")
    if parsed.get("description"):
        loosen.append(f"using fewer words than \"{parsed['description']}\"")

    tail = "; ".join(loosen) if loosen else "describing the item differently"
    return f"Nothing in the 40 listings matched. Try {tail}."


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== A query it can't ===")
    _show(run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    ))

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )
