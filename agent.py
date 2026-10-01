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
from tools import search_listings, suggest_outfit, create_fit_card
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
        "wardrobe": wardrobe,        # the user's wardrobe
        "outfit_suggestion": None,   # what suggest_outfit returned
        "fit_card": None,            # what create_fit_card returned
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
    count = 0

    # The loop picks its next step by reading the session, not by running a
    # fixed list. `step` is what it decided to do next; "done" ends the run.
    step = "parse"

    while step != "done":
        count += 1
        trace.check_iterations(count)

        if step == "parse":
            session["parsed"] = parse_query(query)
            step = "search"

        elif step == "search":
            parsed = session["parsed"]
            session["search_results"] = search_listings(
                parsed["description"],
                size=parsed["size"],
                max_price=parsed["max_price"],
            )
            # THE BRANCH: nothing came back, so there is nothing to style.
            if not session["search_results"]:
                session["error"] = _no_results_message(session["parsed"])
                return session
            step = "select"

        elif step == "select":
            session["selected_item"] = session["search_results"][0]
            step = "outfit"

        elif step == "outfit":
            session["outfit_suggestion"] = suggest_outfit(
                session["selected_item"], session["wardrobe"]
            )
            # Branch again: no outfit text means no caption worth writing.
            step = "fit_card" if (session["outfit_suggestion"] or "").strip() else "done"

        elif step == "fit_card":
            session["fit_card"] = create_fit_card(
                session["outfit_suggestion"], session["selected_item"]
            )
            step = "done"

        else:
            session["error"] = f"The loop reached an unknown step: {step!r}."
            return session

    return session


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
