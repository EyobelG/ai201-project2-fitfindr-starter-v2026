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

`create_fit_card` takes a third argument, `price_note` (str or None), added for
the price branch below. On the path where the branch doesn't fire it is None and
the prompt is exactly what it was before the branch existed.

### `compare_prices` — the fourth tool (stretch 1)

- **What it does:** Reads the listings data and says where one item's price sits against the rest of its category. No model call.
- **Inputs:** `new_item` (dict) — one listing dict, normally `session["selected_item"]`.
- **Returns:** A dict with `category` (str), `price` (float), `median` (float), `cheaper_count` (int), `total` (int), `verdict` (str — one of `"above_median"`, `"at_or_below_median"`, `"alone_in_category"`), and `cheaper` (list of up to two dicts, each `{"id", "title", "price"}`, cheapest first).
- **When it has nothing:** A category holding no other listing returns `verdict: "alone_in_category"`, `median` equal to the item's own price, `cheaper_count: 0` and `cheaper: []`. Never None, never raises — an item whose category isn't in the data is treated as alone.

The median is taken across the category *including* this item, and `cheaper`
only ever holds listings that genuinely undercut it, which is what makes the
branch below safe to fire on: if `cheaper` is non-empty there is a real
alternative to name.

---

## Planning Loop

**Branch rule:** If `search_listings` returns an empty list, put a message in
`session["error"]` naming what the user could loosen and stop — `suggest_outfit`
is never called and `fit_card` stays None. Otherwise take the first result as
`session["selected_item"]` and go to `suggest_outfit`.

There's a second branch after that one: if `suggest_outfit` comes back blank or
whitespace, the loop ends without writing a fit card, because a caption about
nothing is worse than no caption.

**Second branch rule (stretch 2) — the price branch:** After `select`, the loop
runs `compare_prices` as its own step. If the verdict is `"above_median"` **and**
`cheaper` is non-empty, it writes `session["price_note"]` and passes that into
`create_fit_card`, so the caption frames the find as a splurge. If the verdict
is anything else — at or below the median, or alone in its category — that write
is skipped, `price_note` stays None, and `create_fit_card` receives None. Both
paths then continue to the fit card, so what differs is the caption, not whether
there is one.

`selected_item` is deliberately untouched by this branch. Swapping in the
cheaper listing was the obvious move and it is wrong here: criterion 3 says the
item the search picked is the item the card describes, and an override would
make that false by design. The branch adds context rather than changing the
choice.

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

**What moves through the session:** Every step writes its result into the
session and the next step reads it back out, in this order:

| Field | Written by | Holds |
|---|---|---|
| `query` | `new_session` | what the user typed |
| `parsed` | `parse_query` | `description`, `size`, `max_price` |
| `search_results` | `search_listings` | list of listing dicts, best first |
| `selected_item` | the loop | `search_results[0]` |
| `price_check` | `compare_prices` | the dict above — category, median, verdict, cheaper |
| `price_note` | the loop | str, and only when the price branch fires |
| `wardrobe` | `new_session` | passed in by the caller |
| `outfit_suggestion` | `suggest_outfit` | str |
| `fit_card` | `create_fit_card` | str |
| `error` | the loop | set only when the branch fires |

Nothing is passed from one call straight into the next, so a whole run is one
printable dict rather than a chain of variables I've already overwritten. If
the branch fires, `error` is set and everything from `selected_item` down stays
None.

The loop isn't three calls in a row — it holds a `step` variable and each pass
decides the next step from what's in the session. `trace.check_iterations(count)`
runs at the top of every pass, so a step that never advances trips
`MAX_ITERATIONS` instead of spinning.

---

## Sample Run

**One full query**

```
$ python app.py ask 'vintage graphic tee under $30'

  Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop

  Outfit:   Pair the Y2K Baby Tee — Butterfly Print with your Baggy straight-leg jeans, dark wash and Chunky white sneakers for a classic, nostalgic streetwear look. Layer your Vintage black denim jacket over top and accessorize with the Black crossbody bag to complete the outfit.

  Fit card: Found this absolute dream of a butterfly print baby tee on Depop for just $18 and I am never taking it off. It's giving total early 2000s mall-rat energy, especially paired with baggy dark wash denim and chunky kicks. Major nostalgia in the best way possible!

0 model calls this session, 2 served from cache
```

The price and the platform in the card — `$18`, Depop — are the ones on
`lst_002`, the item the search picked. That is the state criterion passing in
the one place a user can see it.

**The empty-search branch, same command**

```
$ python app.py ask 'designer ballgown size XXS under $5'

  Nothing in the 40 listings matched. Try raising the $5 ceiling; dropping the size XXS filter; using fewer words than "designer ballgown".

0 model calls this session
```

Zero model calls on that run is the branch working: the loop stopped before
`suggest_outfit`, so neither model tool was reached.

**The three tools, tested one at a time**

```
$ python -c "
from tools import search_listings
r = search_listings('graphic tee', size='M', max_price=30)
print(len(r), 'matches')
for x in r[:3]: print(x['id'], x['title'], x['price'], x['size'], x['platform'])
print(search_listings('ballgown', size='XXS', max_price=5.0))
"

2 matches
lst_002 Y2K Baby Tee — Butterfly Print 18.0 S/M depop
lst_017 Mesh Long-Sleeve Top — Black 15.0 S/M depop
[]
```

Both halves of the spec in one command: real matches with `size='M'` landing on
`S/M` items — token matching, not substring — and `[]` rather than None or a
crash when nothing survives the filters.

```
$ python -c "
from tools import search_listings, suggest_outfit
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe
item = search_listings('graphic tee', max_price=30)[0]
print('OUTFIT:', suggest_outfit(item, get_example_wardrobe()))
print('EMPTY-WARDROBE:', suggest_outfit(item, get_empty_wardrobe()))
"

OUTFIT: Pair the Y2K Baby Tee — Butterfly Print with your Baggy straight-leg jeans, dark wash and Chunky white sneakers for a classic, nostalgic streetwear look. Layer your Vintage black denim jacket over top and accessorize with the Black crossbody bag to complete the outfit.
EMPTY-WARDROBE: Since your wardrobe is currently empty, I'll share some general ideas for how you could style this adorable butterfly baby tee. You could lean fully into the Y2K aesthetic by pairing it with low-rise baggy cargo pants and chunky platform sneakers. Alternatively, for a cute cottagecore twist, try tucking it into a tiered denim mini skirt and adding pastel butterfly hair clips.
```

Every piece in the first answer — the baggy straight-leg jeans, the chunky white
sneakers, the vintage black denim jacket, the black crossbody bag — is a
wardrobe item by its stored name, which is criterion 5. The empty wardrobe gets
general advice and says why it's general, instead of naming clothes nobody owns.

```
$ python -c "
from tools import search_listings, suggest_outfit, create_fit_card
from utils.data_loader import get_example_wardrobe
item = search_listings('graphic tee', max_price=30)[0]
outfit = suggest_outfit(item, get_example_wardrobe())
print('CARD:', create_fit_card(outfit, item))
print('CARD-EMPTY-OUTFIT:', create_fit_card('   ', item))
"

CARD: Found this absolute dream of a butterfly print baby tee on Depop for just $18 and I am never taking it off. It's giving total early 2000s mall-rat energy, especially paired with baggy dark wash denim and chunky kicks. Major nostalgia in the best way possible!
CARD-EMPTY-OUTFIT: No fit card — there is no outfit to write about. suggest_outfit() returned nothing.
```

Three sentences, the price and the platform once each, and the whitespace-only
outfit returns the fixed string without making a model call.

---

## How I Used AI

**Moment 1 — I had it attack my criteria instead of write them**

- *What I asked for:* I pasted my three draft criteria into Claude with the
  prompt from Milestone 3 — tell me exactly how you'd test each one using only
  what the sentence says, don't suggest improvements.
- *What came back:* It turned criteria 3 and 5 into tests without trouble. For
  my fit-card criterion, which at that point said the card should be "different
  each time and read naturally," it said it had no way to score either half:
  two cards differing by one word are different, and "naturally" is a judgment
  with no procedure attached.
- *What I changed:* I rewrote criterion 4 into things that can be counted — 2
  to 4 sentences, the price and the platform named once each, no two of five
  cards sharing an opening sentence — and split the targets, 4 of 5 for the
  prompt-driven parts and 5 of 5 for the opening-sentence check, because
  identical wording is a config bug rather than variance.

**Moment 2 — size matching, where it gave me the wrong shape first**

- *What I asked for:* I gave Claude my `search_listings` spec and the list of
  size strings in the data (`S`, `M`, `S/M`, `US 8`, `W30 L30`, `One Size`) and
  asked for the filter.
- *What came back:* A one-liner doing `size.lower() in listing["size"].lower()`.
  I ran it with `size="S"` and it returned `US 9` sneakers and an `XL` jacket,
  because `"s"` is a substring of both. It had also written `return None` for
  the no-match case, against the empty list my spec names.
- *What I changed:* Replaced the substring test with token matching — strip
  parenthetical notes and the `US` prefix, split on slashes and whitespace,
  compare whole tokens, treat `One Size` as matching anything — and made the
  no-match case `[]`, which is what the loop's branch checks. Writing the empty
  case into the spec first is why I caught the `None` instead of debugging the
  branch later.


---

## Stretch Features

Three stretch items, declared here before I built them. Each one names what it
is, what it returns or changes, and where the evidence for it sits further down
this file.

**1. A fourth tool — `compare_prices`**

A fourth tool beyond the three required: it reads the listings data and tells
you whether the item the search picked is dear or cheap for its category. No
model call, so it costs nothing and it is testable the way `search_listings`
is. Returns a dict with the category, the item's price, the category median,
how many listings undercut it, and the two cheapest of those. Lives in
`tools.py::compare_prices`, called from the loop as its own step. Evidence:
**Stretch 1 — the fourth tool in a run** below.

**2. A second branch — the price branch**

The loop already branches on an empty search. This is a second condition, and a
different one: when `compare_prices` says the item sits above its category
median *and* names at least one cheaper listing, the loop takes an extra step
that writes `session["price_note"]`, and the fit card is told about it. When the
item is at or below the median, that step is skipped and `price_note` stays
None. Both paths end in a fit card, so the difference is visible in the output
rather than in whether there is any.

It deliberately does **not** change `selected_item`. Swapping in the cheaper
listing was the first thing I tried, and it breaks criterion 3 — the item the
search picked would stop being the item the card describes. The branch adds
context to the card instead of overriding the choice. Evidence: **Stretch 2 —
both paths of the price branch** below.

**3. Style memory**

The agent remembers a wardrobe between runs. `python app.py ask --remember`
loads the wardrobe saved on disk at `data/wardrobe_saved.json` rather than the
example one, and after a successful run it files the item it just styled into
that wardrobe. The next run sees it as something you own, so the second run's
outfit is shaped by what the first one stored.

Opt-in on purpose. Without `--remember` the agent loads the example wardrobe
exactly as it did before, because my five criteria are written against that
wardrobe and a run that quietly grew its own inputs would make them
unmeasurable. Evidence: **Stretch 3 — two runs, the second shaped by the
first** below.


### Unit 4 stretch — a second tool moved onto MCP

Declared here before I built it, the same way the three above were.

Milestone 1 moved `search_listings` onto the MCP server. This moves a second
one: `compare_prices`. It is the right next candidate for the same reason
`search_listings` was — it reads the listings data and makes no model call, so
nothing is slow, nothing changes between runs, and the only thing I am
exercising is the protocol seam.

What changes: `compare_prices` is registered on `mcp_server.py` alongside
`search_listings`, with its own written description and typed inputs, and the
loop's `price_check` step calls it through `mcp_client.call_tool` instead of
importing it from `tools.py`. The implementation in `tools.py` is untouched —
the server wraps it, exactly as it wraps the search.

What should not change: the returned dict, key for key. The price branch reads
`verdict` and `cheaper` off it, so if the shape shifted in transit the branch
would silently stop firing. The evidence below is a direct-versus-MCP equality
check on that dict, plus a run showing the branch still taking both paths.

One thing I expected to be harder than it was: `compare_prices` takes a whole
listing dict as its input, not flat strings and numbers like `search_listings`
does. FastMCP builds that into an object in the input schema from the `dict`
type hint, and `mcp_client._unwrap` puts the returned dict back without
needing the `{"result": ...}` unwrapping a bare value needs.

Evidence: **Unit 4 stretch — `compare_prices` over MCP** below.


### Stretch 1 — the fourth tool in a run

`compare_prices` on its own, covering the dear case, the cheap case and the
empty case. From `tools.py::compare_prices`:

```
$ python -c "
from tools import compare_prices
from utils.data_loader import load_listings
import json
L = {x['id']: x for x in load_listings()}
print(json.dumps(compare_prices(L['lst_022']), indent=2, ensure_ascii=False))
print(json.dumps(compare_prices(L['lst_002']), indent=2, ensure_ascii=False))
print(json.dumps(compare_prices({'id':'x','category':'swimwear','price':10.0}), indent=2, ensure_ascii=False))
"

{
  "category": "outerwear",
  "price": 75.0,
  "median": 41.0,
  "cheaper_count": 7,
  "total": 8,
  "verdict": "above_median",
  "cheaper": [
    {
      "id": "lst_038",
      "title": "Denim Vest — Medium Wash, Studded",
      "price": 27.0
    },
    {
      "id": "lst_032",
      "title": "Shacket — Olive Canvas",
      "price": 33.0
    }
  ]
}
{
  "category": "tops",
  "price": 18.0,
  "median": 21.0,
  "cheaper_count": 3,
  "total": 15,
  "verdict": "at_or_below_median",
  "cheaper": [
    {
      "id": "lst_017",
      "title": "Mesh Long-Sleeve Top — Black",
      "price": 15.0
    },
    {
      "id": "lst_020",
      "title": "Henley Long Sleeve — Washed Burgundy",
      "price": 16.0
    }
  ]
}
{
  "category": "swimwear",
  "price": 10.0,
  "median": 10.0,
  "cheaper_count": 0,
  "total": 1,
  "verdict": "alone_in_category",
  "cheaper": []
}
```

The bomber is the dearest outerwear in the data at $75 against a $41 median, so
`verdict` is `above_median` and seven listings undercut it. The baby tee at $18
sits under the $21 tops median, so it comes back `at_or_below_median` — and
`cheaper` is still populated there, which is why the branch tests the verdict
rather than just checking whether `cheaper` has anything in it. The third call
passes a category that doesn't exist in the data at all and gets
`alone_in_category` rather than a `StatisticsError` from taking the median of an
empty list.

**And the agent calling it.** The run below is the whole loop, and the step
order is `parse → search → select → price_check → outfit → fit_card`. The
`price_check` step is the fourth tool; the note it produced is what shaped the
caption.

### Stretch 2 — both paths of the price branch

Same command, two items, one branch. The condition is `verdict ==
"above_median" and cheaper` — in `agent.py::run_agent`, the `price_check` step.

**The path where it fires** — the bomber, $75 against a $41 median:

```
$ AI201_CACHE=0 python app.py ask '90s leather bomber'

  Found:    90s Leather Bomber — Black — $75.0 on depop

  Outfit:   Layer the 90s Leather Bomber over the white ribbed tank top and pair them with the baggy straight-leg jeans, dark wash. Finish the look with the chunky white sneakers and the black crossbody bag for an effortless 90s streetwear vibe.

  Fit card: Totally caved and splurged $75 on this buttery vintage leather bomber on Depop, but honestly, look at it. Threw it on over a beat-up white tank and baggy dark wash denim for the ultimate heavy-metal-off-duty-model energy. It's properly heavy and worn in just right—worth every single penny.

2 model calls this session, 553 prompt + 124 output tokens
```

**The path where it doesn't** — the baby tee, $18 against a $21 median:

```
$ AI201_CACHE=0 python app.py ask 'vintage graphic tee under $30'

  Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop

  Outfit:   Pair the Y2K Baby Tee — Butterfly Print with your baggy straight-leg jeans and chunky white sneakers for a classic noughties street style look. Layer the Vintage black denim jacket over top and accessorize with your black crossbody bag to complete the outfit.

  Fit card: Obsessed with this little butterfly tee I just scored on Depop for only $18! It’s giving total early 2000s pop star off-duty, especially when paired with baggy jeans and chunky sneakers. Threw on a black denim jacket to toughen it up a bit—can't wait to live in this all summer.

2 model calls this session, 470 prompt + 124 output tokens
```

The branch is visible in the two cards. The first one opens on "totally caved
and splurged" and closes on "worth every single penny" — that framing is the
`price_note` reaching the prompt. The second never mentions value at all,
because `price_note` was None and `create_fit_card` got the prompt it always
had. The note itself, which the caption paraphrases rather than quotes:

```
$ python -c "
from agent import run_agent
from utils.data_loader import get_example_wardrobe
s = run_agent('90s leather bomber', get_example_wardrobe())
print('verdict:   ', s['price_check']['verdict'])
print('price_note:', s['price_note'])
print('selected_item is still search_results[0]:',
      s['selected_item']['id'] == s['search_results'][0]['id'])
"

verdict:    above_median
price_note: $75 is above the $41 median for outerwear; 7 of 8 are cheaper, the lowest being Denim Vest — Medium Wash, Studded at $27.
selected_item is still search_results[0]: True
```

That last line is the thing I was protecting. The branch had an obvious louder
version — pick the $27 denim vest instead — and it would have made criterion 3
false on every run that took it.

### Stretch 3 — two runs, the second shaped by the first

Starting from no saved file, so run 1 falls back to the ten example items.

**Run 1** — styles a pair of cargo pants, then files them:

```
$ rm -f data/wardrobe_saved.json
$ AI201_CACHE=0 python app.py ask --remember 'low-rise cargo pants'

(style memory on — 10 items remembered)

  Found:    Low-Rise Cargo Pants — Khaki — $27.0 on poshmark

  Outfit:   Pair the Low-Rise Cargo Pants — Khaki with the fitted White ribbed tank top for a classic Y2K streetwear silhouette. Throw on the Black cropped zip hoodie and finish the outfit with Chunky white sneakers.

  Fit card: My Y2K streetwear dreams are finally coming true thanks to these khaki low-rise cargo pants. I scored them on Poshmark for just $27 and they have the exact slouchy, 2000s pocket-heavy vibe I've been hunting for. Paired with a fitted ribbed tank, a cropped zip hoodie, and chunky sneakers, this fit is peak nostalgic perfection.

  (remembered: Low-Rise Cargo Pants — Khaki — 11 items in your saved wardrobe)

2 model calls this session, 466 prompt + 124 output tokens
```

**Run 2** — a separate process, styling a different item:

```
$ AI201_CACHE=0 python app.py ask --remember 'y2k baby tee butterfly'

(style memory on — 11 items remembered)

  Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop

  Outfit:   Pair the Y2K Baby Tee — Butterfly Print with your Low-Rise Cargo Pants — Khaki and Chunky white sneakers for a nostalgic 2000s streetwear look. Add the Black crossbody bag to complete the outfit.

  Fit card: Found this absolute dream of a butterfly print baby tee on Depop for just $18, and I am obsessed. The Y2K cottagecore energy is so strong, especially paired with low-rise cargos and chunky white sneakers. It's giving major early 2000s mall-goth-meets-fairy vibes and I never want to take it off.

  (remembered: Y2K Baby Tee — Butterfly Print — 12 items in your saved wardrobe)

2 model calls this session, 499 prompt + 124 output tokens
```

Run 2's outfit names **"your Low-Rise Cargo Pants — Khaki"** — an item that was
a listing in run 1 and is a wardrobe item by run 2. It isn't just that the
count went 10 → 11 → 12; the stored item is the one the second outfit reached
for, over the two pairs of bottoms that were there all along. That is the
wardrobe shaping the advice.

It worked on this pairing because the cargo pants share `y2k` and `2000s` tags
with the tee, and the pre-existing bottoms are baggy jeans and khaki trousers.
Run 1 saving the leather bomber and run 2 styling the same tee gave an outfit
that ignored the bomber entirely — memory that stores the item but doesn't
change the answer, which would not have been evidence of anything. Both
attempts are in my history; this is the one that demonstrates the feature.

What persists, after those two runs:

```
$ python -c "
import json
saved = json.load(open('data/wardrobe_saved.json'))
print(json.dumps(saved['items'][-2:], indent=2, ensure_ascii=False))
"

[
  {
    "name": "Low-Rise Cargo Pants — Khaki",
    "category": "bottoms",
    "colors": [
      "khaki",
      "tan"
    ],
    "style_tags": [
      "y2k",
      "cargo",
      "2000s",
      "streetwear"
    ],
    "from_listing": "lst_011"
  },
  {
    "name": "Y2K Baby Tee — Butterfly Print",
    "category": "tops",
    "colors": [
      "white",
      "pink",
      "purple"
    ],
    "style_tags": [
      "y2k",
      "vintage",
      "graphic tee",
      "cottagecore"
    ],
    "from_listing": "lst_002"
  }
]
```

`from_listing` is why re-running the same query doesn't file the item twice, and
it's how a wardrobe item that came from a find can be told from one that was
always there.

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

### Unit 4 stretch — `compare_prices` over MCP

The server now offers two tools. `python mcp_client.py` lists both, each with
its own description and a schema built from the type hints:

```
  search_listings
    - description: string
    - size: string  (optional)
    - max_price: number  (optional)

  compare_prices
    - new_item: object
```

`new_item: object` is the one difference from the search. `compare_prices`
takes a whole listing dict rather than flat scalars, and FastMCP turns the
`dict` hint into an object in the input schema.

**The returned dict is identical across the seam.** Checked on two items, one
on each side of the median, since the price branch reads `verdict` and
`cheaper` off this dict and a shape change in transit would stop the branch
firing without any error:

```
Vintage Levi's 501 Jeans — Medium Wash
  direct == mcp : True
  keys match    : True
  verdict       : above_median
  cheaper type  : list
Y2K Baby Tee — Butterfly Print
  direct == mcp : True
  keys match    : True
  verdict       : at_or_below_median
  cheaper type  : list
```

**The price branch still fires through MCP.** Both MCP calls are visible in
order in the trace, steps 2 and 4, and step 5 is the branch deciding on what
step 4 returned:

```
[1] parse_query
      in:  vintage Levi 501 jeans medium wash
      out: {'description': 'vintage Levi 501 jeans medium wash', 'size': None, 'max_price': None}
[2] search_listings (via MCP)
      in:  {'description': 'vintage Levi 501 jeans medium wash', 'size': None, 'max_price': None}
      out: 10 items: Vintage Levi's 501 Jeans — Medium Wash, Baggy Carpenter Jeans — Dark Wash, Denim Vest — Medium Wash, Studded … +7 more
      →    10 match(es)
[3] select_item
      out: Vintage Levi's 501 Jeans — Medium Wash ($38.0, depop)
[4] compare_prices (via MCP)
      in:  Vintage Levi's 501 Jeans — Medium Wash ($38.0, depop)
      out: {'category': 'bottoms', 'price': 38.0, 'median': 30.0, 'cheaper_count': 9, 'total': 10, 'verdict': 'above_medi…
[5] branch
      →    above median with a cheaper option: carrying a price note into the fit card
[6] suggest_outfit
      in:  Vintage Levi's 501 Jeans — Medium Wash ($38.0, depop)
      out: Pair the Vintage Levi's 501 Jeans with the White ribbed tank top and the Oversized grey crewneck sweatshirt la…
[7] create_fit_card
      in:  Vintage Levi's 501 Jeans — Medium Wash ($38.0, depop)
      out: Found my holy grail vintage Levi's 501 jeans on Depop and honestly, at $38, they were a total splurge compared…

price_note: $38 is above the $30 median for bottoms; 9 of 10 are cheaper, the
lowest being Biker Shorts — Black, Shiny at $14.
```

The other two paths are unchanged. `python agent.py` still takes the
at-or-below-median path without a price note on the first query, and the
empty-search branch on the second query still stops before `suggest_outfit`
with `fit_card` left as None.

**What this cost.** Each `call_tool` starts `mcp_server.py` as a fresh process
over stdio and stops it again, so a run that used to make one in-process
function call for the price check now pays a process launch for it. Two tools
on MCP means two launches per run. That is the wrong trade for production and
the right one for seeing the seam, which is what `mcp_client.py` says about
holding the connection open.

**One failure mode this introduced.** Both MCP steps catch `MCPError` and set
`session["error"]` rather than letting a stack trace out, because an
unreachable server is now a way the run can fail that did not exist when the
tools were imported. The price-check handler stops the run before
`suggest_outfit`, which is arguably too strict — the price note is optional
context, so a failed price check could log and carry on to a fit card with no
note. I left it strict so that a broken server is loud rather than silent.


## Failure Modes

Three failures, triggered one at a time, with what the agent actually said.
Two of the three behave the way they should. The third is where the real
finding is.

### 1. Empty search — passes

Query: `ceremonial walrus-hide spacesuit size XXS under $3`. Nothing in the 40
listings is close, and all three filters are set, so this cannot match.

```
[2] search_listings (via MCP)
      in:  {'description': 'ceremonial walrus-hide spacesuit', 'size': 'XXS', 'max_price': 3.0}
      out: [] (empty)
      →    0 match(es)
[3] branch
      →    search returned []: stopping before suggest_outfit

  Nothing in the 40 listings matched. Try raising the $3 ceiling; dropping the size XXS filter; using fewer words than "ceremonial walrus-hide spacesuit".

0 model calls this session
```

The loop stops at step 3 and names all three things the user could change,
built from what was actually parsed rather than from a fixed string. **Zero
model calls** — the branch fires before anything is spent, which is the part
worth checking. `agent.py::_no_results_message` wrote that message.

### 2. Empty wardrobe — passes

`python app.py ask 'cropped cardigan' --empty-wardrobe`. The search still finds
items; the wardrobe handed to `suggest_outfit` holds nothing.

```
[6] suggest_outfit
      out: Since your wardrobe is currently empty, these are general ideas for styling this vintage light wash cropped de…
```

Full text returned:

> Since your wardrobe is currently empty, these are general ideas for styling
> this vintage light wash cropped denim jacket. You could lean into a
> streetwear aesthetic by layering it over an oversized graphic tee with black
> biker shorts and chunky sneakers. Alternatively, for a classic look, pair it
> with high-waisted wide-leg trousers and a fitted ribbed tank top.

No crash, no empty string, and it says plainly that the wardrobe is empty
instead of inventing pieces the user does not own. The run continues to a fit
card. `tools.py::suggest_outfit` takes the empty-wardrobe path at its first
branch and asks for general advice.

### 3. Model unavailable — partly fails

**First, something the assignment step could not have told me.** The
instruction is to change one character of the key in `.env`. I did, and the
run succeeded with two live model calls — the bad key had no effect at all.

The cause: `GEMINI_API_KEY` is exported in my shell environment, and
`load_dotenv()` at `config.py:18` does not override variables that are already
set. So `.env` was never being read on this machine, and every run this whole
project has used the shell value. Editing `.env` to break the key is a no-op
here. Worth knowing because it means `.env` is not the authoritative source
of the key on my setup, and the error text the agent prints ("Check
GEMINI_API_KEY in your .env file") points at the wrong file.

Triggering it properly, by overriding the variable for one run on a query I
had not asked before, so nothing could come from the cache:

```
GEMINI_API_KEY="<a deliberately invalid key>" python app.py ask 'chunky brown knit cardigan' --trace
```

```
[4] compare_prices (via MCP)
      out: {'category': 'tops', 'price': 35.0, 'median': 21.0, 'cheaper_count': 14, 'total': 15, 'verdict': 'above_median…
[5] branch
      →    above median with a cheaper option: carrying a price note into the fit card

ModelUnavailable: The model rejected your API key. Check GEMINI_API_KEY in your .env file, or create a fresh key at aistudio.google.com.

1 model calls this session
```

Through `app.py` the user sees one readable line, not a traceback. That is not
my loop doing it, though — it is the broad `except Exception` at `app.py:230`,
which the starter put there precisely so students read a message rather than a
stack trace. My loop contributes nothing.

Calling `run_agent()` directly, the way `run_eval.py` and `serve.py` do,
shows what the loop actually does with the failure:

```
Traceback (most recent call last):
  File "<string>", line 4, in <module>
  File ".../agent.py", line 232, in run_agent
    session["outfit_suggestion"] = suggest_outfit(
  File ".../tools.py", line 239, in suggest_outfit
    return generate(prompt, system=system)
  File ".../generate.py", line 332, in generate
    raise ModelUnavailable(_explain(exc)) from exc
generate.ModelUnavailable: The model rejected your API key.
```

So the real behaviour is: **`ModelUnavailable` is imported at `agent.py:22` and
never caught.** The exception leaves `run_agent()` mid-loop, `session["error"]`
is never set, and the session dict — with its parsed query, its 5 search
results, its price check and its price note, all of which cost something to
produce — is discarded. Anything calling the loop as a library gets a
traceback. Only the CLI is protected, and only by accident.

That is the gap the improvement in **The Improvement** closes.

### A note on the cache, and on where the key lives now

Two things I got wrong while triggering failure 3, both worth recording.

**The cache hid the failure once.** After rotating the key I wanted to confirm
the old one was dead, so I called `generate("Say Ready")` with it and got a
reply back. I read that as "still valid". It was not: I had already run that
exact prompt earlier in the session, so the answer came from the build cache
without any request leaving the machine. Re-running with `AI201_CACHE=0` and a
prompt containing a random number — one that could not possibly be cached —
returned `ModelUnavailable` immediately. The key had been revoked all along.

This is exactly what the milestone instructions warn about, and reading it as a
pass is an easy mistake to make, because a cache hit and a live call look
identical in the output. The only reliable signals are the `N model calls this
session` line at the end of a run and turning the cache off outright.

**`.env` is authoritative now.** The shadowing described above was real at the
time those runs were made, and the evidence stands as recorded. I have since
deleted the `export GEMINI_API_KEY=` line from `~/.zshrc` and rotated the key,
so `load_dotenv()` at `config.py:18` now has nothing to be overridden by and
`.env` is the single source. Re-running the milestone's step as written — break
one character of the key in `.env` — produces `ModelUnavailable` on this
machine today.


## Run Log — Before

`python run_eval.py --label before` — 7 scenarios, 5 tries each, caching off,
temperature 0.9, 61 model calls. Full output in
`results/run_2026-10-07_2234_before.md`, committed alongside this file.

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. A matching query completes all three tools | ≥4 of 5 | PASS | PASS | PASS | PASS | PASS | **MET (5/5)** |
| 2. An impossible query stops before the second tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | **MET (5/5)** |
| 3. The item the search picked is the item the card describes | 5 of 5 | PASS | PASS | PASS | PASS | PASS | **MET (5/5)** |
| 4. Fit cards in-spec (2–4 sentences, price and platform once each) | ≥4 of 5 | PASS | PASS | PASS | PASS | PASS | **MET (5/5)** |
| 4b. No two cards share an opening sentence | 5 of 5 | PASS | PASS | PASS | PASS | PASS | **MET (5/5)** |
| 5. The outfit never names a garment the user doesn't own | ≥4 of 5 | PASS | PASS | PASS | PASS | PASS | **MET (5/5)** |
| empty wardrobe _(diagnostic — not one of the five)_ | — | advice | advice | advice | advice | advice | n/a |
| price branch fires _(diagnostic — not one of the five)_ | — | note | note | note | note | note | n/a |

All five met. How each column was decided:

- **1** — `stopped early: no`, and both an outfit and a fit card present. All
  five produced both.
- **2** — `stopped early: yes`, and no `[n] suggest_outfit` step in the trace.
  All five traces end at `[3] branch`.
- **3** — the title at `[2] search_listings` position 0 equals the title at
  `[3] select_item`, and the card contains that item's price and platform.
  `$18` and `depop` appear in all five cards.
- **4** — sentences counted on `.!?`, then one occurrence each of `$38` and
  `depop`. Every card came out at exactly 3 sentences with one mention each.
  Openings compared as exact strings: 5 unique of 5.
- **5** — read by hand, since "is this garment owned" is not a string match.
  Across the five tries the outfits name the white ribbed tank top, the
  wide-leg khaki trousers, the baggy straight-leg jeans and the chunky white
  sneakers. All four are in the wardrobe. Nothing was invented.

**Real output, one try per criterion.** All of it is from
`results/run_2026-10-07_2234_before.md`, produced by `agent.py::run_agent`
driving `tools.py` — the search through `mcp_server.py::search_listings`, the
price check through `mcp_server.py::compare_prices`, and the two model-calling
tools as `tools.py::suggest_outfit` and `tools.py::create_fit_card`.

**Criterion 1, try 1** — `agent.py::run_agent`, all three tools, query
`vintage graphic tee under $30`:

```
- stopped early: no
- selected_item: Y2K Baby Tee — Butterfly Print ($18.0, depop)
- search_results: 10

Outfit suggestion:

Pair the Y2K Baby Tee — Butterfly Print with your Baggy straight-leg jeans,
dark wash and Chunky white sneakers for a classic nostalgic look. Layer the
Vintage black denim jacket over top and complete the outfit with your Black
crossbody bag.

Fit card:

Finally scored this dreamy little butterfly baby tee on Depop for just $18 and
I am obsessed. It's giving major early 2000s mall-rat energy, especially paired
with baggy dark wash denim and chunky white sneakers. Throwing on a black denim
jacket over top makes it feel just grungy enough.
```

**Criterion 2, try 1** — `agent.py::_no_results_message`, query
`designer ballgown size XXS under $5`:

```
- stopped early: yes — Nothing in the 40 listings matched. Try raising the $5
  ceiling; dropping the size XXS filter; using fewer words than "designer
  ballgown".
- selected_item: (none)
- search_results: 0
```

The trace for that try ends three steps in, with no `suggest_outfit` step at
all:

```
[2] search_listings (via MCP)
      in:  {'description': 'designer ballgown', 'size': 'XXS', 'max_price': 5.0}
      out: [] (empty)
      →    0 match(es)
[3] branch
      →    search returned []: stopping before suggest_outfit
```

**Criterion 3, try 1** — the state check. `select_item` in
`agent.py::run_agent` takes `search_results[0]`, and
`tools.py::create_fit_card` is given that same dict:

```
- stopped early: no
- selected_item: Y2K Baby Tee — Butterfly Print ($18.0, depop)
- search_results: 10

Fit card:

Found the ultimate Y2K butterfly baby tee on Depop for just $18, and I am
officially obsessed. It's giving total early-2000s mall rat energy, especially
paired with baggy straight-leg denim and chunky kicks. Can't wait to live in
this all summer!
```

The trace confirms the two halves match: `[2]` lists
`Y2K Baby Tee — Butterfly Print` first and `[3] select_item` returns that same
listing. `$18` and `depop` both appear in the card.

**Criterion 4, try 1** — `tools.py::create_fit_card`, the same item run five
times. Try 1's card, three sentences, `$38` once and `Depop` once:

```
Okay, a total splurge at $38 on Depop, but these vintage Levi's 501s are worth
every single penny for that perfect, broken-in feel. I'm living in this exact
medium wash denim paired with a cozy grey crewneck and chunky sneakers for the
ultimate effortless streetwear look. Honestly, finding a 30x30 that actually
fits like this is literal secondhand magic.
```

The five opening sentences across the five tries, which is what the
no-repeats half of the criterion is scored on:

```
1: Okay, a total splurge at $38 on Depop, but these vintage Levi's 501s are worth every single penny…
2: Okay, total splurge since most bottoms on here go for way less, but scoring these vin…
3: Total splurge compared to my usual thrifting budget, but scoring these vintage Levi's…
4: Okay, breaking my own budget rules for these vintage Levi's 501 jeans, but how could…
5: I totally splurged on these vintage Levi's 501 jeans on Depop for $38, but look at th…
```

All five open differently. Every one of them reaches for "splurge", because
`agent.py::_price_note` told the card the jeans are above the median for
bottoms — the branch is shaping the wording in all five.

**Criterion 5, try 1** — `tools.py::suggest_outfit` with a non-empty wardrobe:

```
- stopped early: no
- selected_item: Mini Shoulder Bag — Tan Leather ($38.0, poshmark)
- search_results: 10

Outfit suggestion:

Pair the mini shoulder bag with the white ribbed tank top and baggy
straight-leg jeans for a casual, classic look. Complete the outfit with the
chunky white sneakers to tie the vintage streetwear vibe together.
```

An accessory was chosen for this criterion on purpose: there is less in the
wardrobe that obviously goes with a bag, so it is where a model is most tempted
to reach for a piece nobody owns. It didn't — the tank top, the jeans and the
sneakers are all in `wardrobe["items"]`.

### One thing the table doesn't show

Criterion 5 passed 5 of 5, and the five outfits are nearly the same outfit.
Tries 2, 3, 4 and 5 all open with the identical sentence:

> Pair the Mini Shoulder Bag with the White ribbed tank top and Wide-leg khaki
> trousers for an effortless, neutral-toned look.

Caching was off and the temperature was 0.9, so these are five separate model
calls that independently produced one answer four times. Criterion 4 checks for
exactly this in the fit cards — where the five openings came out all different —
but no criterion checks it for the outfit, so nothing in the table is allowed to
fail on it.

That is the diagnosis the improvement below works from. It is not a missed
target; it is a gap in what the targets measure.

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

One `trace.step()` per step of the loop, placed where the step writes its
result into the session. Both MCP calls are visible among them, steps 2 and 4.
The `branch` entries are not tool calls — they record the loop deciding, which
is the thing a trace is for.

**Happy path** — `python app.py ask 'oversized flannel shirt plaid red black' --trace`

```
[1] parse_query
      in:  oversized flannel shirt plaid red black
      out: {'description': 'oversized flannel shirt plaid red black', 'size': None, 'max_price': None}
[2] search_listings (via MCP)
      in:  {'description': 'oversized flannel shirt plaid red black', 'size': None, 'max_price': None}
      out: 10 items: Oversized Flannel Shirt — Plaid Red/Black, Oversized College Crewneck — Faded Red, Knit Cardigan — Chunky Brown … +7 more
      →    10 match(es)
[3] select_item
      out: Oversized Flannel Shirt — Plaid Red/Black ($22.0, thredUp)
[4] compare_prices (via MCP)
      in:  Oversized Flannel Shirt — Plaid Red/Black ($22.0, thredUp)
      out: {'category': 'tops', 'price': 22.0, 'median': 21.0, 'cheaper_count': 8, 'total': 15, 'verdict': 'above_median'…
[5] branch
      →    above median with a cheaper option: carrying a price note into the fit card
[6] suggest_outfit
      in:  Oversized Flannel Shirt — Plaid Red/Black ($22.0, thredUp)
      out: Layer the Oversized Flannel Shirt open over the White ribbed tank top and pair it with the Baggy straight-leg …
  [rate limit] service pushed back. Waiting 43s (attempt 1 of 5). This is the limiter doing its job, not a bug.
[7] create_fit_card
      in:  Oversized Flannel Shirt — Plaid Red/Black ($22.0, thredUp)
      out: Okay, I totally splurged a little on this red and black plaid oversized flannel and honestly, zero regrets. Fo…

  Found:    Oversized Flannel Shirt — Plaid Red/Black — $22.0 on thredUp

  Outfit:   Layer the Oversized Flannel Shirt open over the White ribbed tank top and pair it with the Baggy straight-leg jeans for a classic grunge look. Finish this streetwear-inspired outfit with the Chunky white sneakers and the Black crossbody bag.

  Fit card: Okay, I totally splurged a little on this red and black plaid oversized flannel and honestly, zero regrets. Found it on thredUp for $22, and it’s giving me the ultimate 90s streetwear grunge energy when I throw it open over a ribbed tank and baggy jeans. The fit is ridiculously good, so yeah, worth every penny of the splurge.

3 model calls this session, 564 prompt + 127 output tokens
```

Three things in that trace worth pointing at.

`[5] branch` fires on what `[4]` returned, not on anything the user typed. The
flannel is $22 against a $21 median for tops, so the price note is written and
carried into the fit card, which is why the card opens by calling it a splurge.
A dollar either way and that line would not exist.

The `[rate limit]` line between steps 6 and 7 is real output, not an error. The
limiter in `generate.py` paced the second model call because `run_eval.py` was
running against the same key at the same time. I left it in rather than
re-running for a clean trace, because it is the only place in this project
where the cost of two model calls per run is visible.

`3 model calls this session` at the end accounts for every call: the outfit, the
fit card, and one made by `run_eval.py`'s concurrent run sharing the counter.
The two MCP steps cost no model calls at all, which is why `search_listings`
was the right tool to move first.

**Empty search** — `python app.py ask 'ceremonial walrus-hide spacesuit size XXS under $3' --trace`

```
[1] parse_query
      in:  ceremonial walrus-hide spacesuit size XXS under $3
      out: {'description': 'ceremonial walrus-hide spacesuit', 'size': 'XXS', 'max_price': 3.0}
[2] search_listings (via MCP)
      in:  {'description': 'ceremonial walrus-hide spacesuit', 'size': 'XXS', 'max_price': 3.0}
      out: [] (empty)
      →    0 match(es)
[3] branch
      →    search returned []: stopping before suggest_outfit

  Nothing in the 40 listings matched. Try raising the $3 ceiling; dropping the size XXS filter; using fewer words than "ceremonial walrus-hide spacesuit".

0 model calls this session
```

Three steps against seven, and **0 model calls against 3**. The branch at `[3]`
returns before `select_item`, so there is no item to price-check and nothing to
style. That length difference is the branch working: if both traces ran to seven
steps, the loop would be a list of function calls with an `if` that does nothing.

**On the MCP move:** two tools moved, not one. `search_listings` was the
required move and `compare_prices` followed as a stretch feature. In both cases
the direct import came out of `agent.py` and the call became
`mcp_client.call_tool(name, {...})`, with the implementations in `tools.py`
untouched — `mcp_server.py` wraps them and publishes a description written for
a caller that cannot read the code.

Nothing behaved differently afterwards, which was the point of checking rather
than assuming. `direct == mcp` is `True` for the search's list of 10 dicts and
for the price check's dict on both sides of the median. The branches that read
those values — the empty-search branch on a list, the price branch on
`verdict` and `cheaper` — still fire on the same inputs.

Two things did change, and neither is visible in the output. Every
`call_tool` starts `mcp_server.py` as a subprocess over stdio and stops it
again, so a run now pays two process launches it did not pay before. And an
unreachable server became a new way for a run to fail, so both MCP steps catch
`MCPError` and set `session["error"]` rather than letting it escape — the same
treatment `ModelUnavailable` now gets.

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
