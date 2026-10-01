# FitFindr

Eyobel Gebre

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> All three tools are stubs, so that last command will do nothing useful yet.
> That's the starting position.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     HOW TO USE THIS FILE

     This is your submission. Fill each section in as you finish the milestone
     it belongs to — don't leave it all to the end.

     Unit 3 asks for the first five sections. Unit 4 adds the five below them.
     Leave the unit 4 sections alone until then; they're here so you know
     what's coming.

     Everything is pasted as TEXT. No screenshots, no images, no video links.
     A typed block of output gets full credit; a picture of the same output
     gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 3 — THE BUILD ═══════════════════════ -->

## What This Does

You type what you're after in plain language — "vintage graphic tee under $30",
"90s track jacket in size M" — and FitFindr searches 40 secondhand listings for
it. It pulls the size and the price ceiling out of the sentence, filters on
those, ranks what's left by keyword overlap, and takes the best match. Then it
styles that item against the clothes you already own and writes a short caption
you could actually post about the find. If nothing in the data matches it stops
there and says which filter to loosen, rather than inventing an outfit for an
item that doesn't exist.


---

## Tool Inventory

### `search_listings`

- **What it does:** Filters the 40 listings by size and price, then ranks what survives by how many query keywords it shares.
- **Inputs:** `description` (str) — the query with the size and price phrases already cut out; `size` (str or None) — skips size filtering when None; `max_price` (float or None) — inclusive ceiling, skips price filtering when None.
- **Returns:** A list of listing dicts, best match first, at most `config.SEARCH_RESULT_LIMIT` (10) of them. Each dict has `id`, `title`, `description`, `category`, `style_tags` (list), `size`, `condition`, `price` (float), `colors` (list), `brand` (str or None), `platform`.
- **When it has nothing:** An empty list. Not None, and it never raises.

Two decisions worth stating, because the loop and my criteria both lean on them.

**Size matching is token equality, not substring.** The data has `S`, `M`, `L`,
`XL`, `S/M`, `M/L`, `L/XL`, `US 7` through `US 9`, `W27` through `W32`,
`W30 L30`, and three flavours of `One Size`. A substring test matches `S`
against `US 9` and `L` against `XL`, which hands someone shoes when they asked
for a small top. So I strip parenthetical notes and the `US` prefix, split on
slashes and whitespace, and compare whole tokens. `One Size` matches any
request. `size="8"` finds `US 8` and nothing else.

**Scoring weights the title and the style tags.** A keyword hit anywhere scores
1; a hit in the title or a style tag scores 2. Anything scoring zero is dropped
before the sort. Broad words like "vintage" are tags on a lot of items, so a
one-word query can fill all ten slots — the real matches sit on top and the tail
is items that scored a single point. Leaving that as-is for now so the unit 4
"before" numbers show the honest baseline.

### `suggest_outfit`

- **What it does:** Asks the model to style one listing against the clothes the user already owns.
- **Inputs:** `new_item` (dict) — one listing dict from `search_listings`; `wardrobe` (dict) — has an `items` key holding a list of wardrobe item dicts, and that list may be empty.
- **Returns:** A non-empty str, two or three sentences, naming owned pieces by the exact name they're stored under.
- **When it has nothing:** An empty `wardrobe['items']` doesn't return `""` and doesn't raise — it asks for general styling ideas instead, and the answer says plainly that it's general because the wardrobe is empty.

The system prompt tells the model never to invent a piece that isn't on the
list. With no list there is nothing to name, so the empty-wardrobe path is a
different prompt rather than the same prompt with a blank in it.

### `create_fit_card`

- **What it does:** Writes a short caption about the find, in the voice of someone posting about it rather than selling it.
- **Inputs:** `outfit` (str) — the string `suggest_outfit` returned; `new_item` (dict) — the same listing dict.
- **Returns:** A str of two to four sentences, mentioning the item, its price and its platform once each.
- **When it has nothing:** An empty or whitespace-only `outfit` returns the fixed string `"No fit card — there is no outfit to write about. suggest_outfit() returned nothing."` and makes no model call.

---

## Planning Loop

**Branch rule:** If `search_listings` returns an empty list, put a message in
`session["error"]` naming what the user could loosen and stop — `suggest_outfit`
is never called and `fit_card` stays None. Otherwise take the first result as
`session["selected_item"]` and go to `suggest_outfit`.

There's a second branch after that one: if `suggest_outfit` comes back blank or
whitespace, the loop ends without writing a fit card, because a caption about
nothing is worse than no caption.

**Where it lives:** `agent.py::run_agent`

**How the query is parsed:** Regex, in `agent.py::parse_query`. Two patterns —
one for the price (`under $30`, `max $40`, a bare `$50`) and one for the size
(`size M`, `size XXS`, `size 8`). Each match is cut out of the string and
whatever's left is the description. Regex rather than asking the model because
parsing is deterministic, it costs no call, and a wrong answer shows up
immediately instead of hiding behind five runs of variation. The size pattern
lists its longest alternatives first — with `xs` ahead of `xxs`, "size XXS"
parses as `XS` and the filter quietly searches for the wrong thing. That one
cost me a debugging pass.

**What moves through the session:** `parsed` → `search_results` →
`selected_item` → `outfit_suggestion` → `fit_card`. Every step writes its result
into the session and the next step reads it back out, so a whole run is one
printable dict. If the branch fires, `error` is set and everything after
`search_results` stays None.

The loop isn't three calls in a row — it holds a `step` variable and each pass
decides the next step from what's in the session. `trace.check_iterations(count)`
runs at the top of every pass, so a step that never advances trips
`MAX_ITERATIONS` instead of spinning.

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query**

```
$ python app.py ask '...'

```

**The three tools, tested one at a time**

```
$ python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"

```

```
$ python -c "from tools import suggest_outfit; ..."

```

```
$ python -c "from tools import create_fit_card; ..."

```

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

**Moment 1**

- *What I asked for:*
- *What came back:*
- *What I changed:*

**Moment 2**

- *What I asked for:*
- *What came back:*
- *What I changed:*

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

```

```

---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 |  |  |  |  |
| 2 |  |  |  |  |
| 3 |  |  |  |  |
| 4 |  |  |  |  |
| 5 |  |  |  |  |

**Diagnoses**



---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path**

```

```

**Empty search**

```

```

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->



---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:**

**Which failure it was meant to fix:**

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->



---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
