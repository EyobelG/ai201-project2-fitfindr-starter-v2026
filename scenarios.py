"""
The runs your test needs. ← UNIT 4, MILESTONE 3

Each of your five criteria needs something run against it. A criterion about
the empty-search branch needs an impossible query. One about the fit card needs
the same item run more than once. Working that out is Milestone 3's first step,
and this file is where you write it down.

`run_eval.py` runs everything here five times and writes the run log — five
because your criteria are written out of five.

Three scenarios are filled in to show the shape. Add or change whatever your
own criteria need — these are a starting point, not a fixed set.
"""

SCENARIOS = [
    {
        # A query the data can match. Criterion 1.
        "name": "matching query completes",
        "query": "vintage graphic tee under $30",
        "wardrobe": "example",
        "criterion": 1,
    },
    {
        # A query nothing can match. Criterion 2 — the branch.
        "name": "impossible query stops early",
        "query": "designer ballgown size XXS under $5",
        "wardrobe": "example",
        "criterion": 2,
    },
    {
        # A user with nothing saved. One of unit 4's three failure modes.
        "name": "empty wardrobe",
        "query": "denim jacket under $50",
        "wardrobe": "empty",
        "criterion": None,
    },
    {
        # Criterion 3 — the item the search picked is the item the card
        # describes. Any matching query will do, because what is being checked
        # is what ends up in the session, not what the user typed. This one is
        # used because its top result is stable across runs: the search is
        # keyword overlap with no model in it, so result [0] does not move.
        "name": "selected item matches the card",
        "query": "y2k baby tee butterfly print",
        "wardrobe": "example",
        "criterion": 3,
    },
    {
        # Criterion 4 — fit cards in-spec and not repeats. The criterion says
        # "run the same item 5 times with the cache off", which is exactly
        # what run_eval.py does to one scenario: five tries, caching off.
        # Phrased to land on one specific listing so all five cards describe
        # the same item and the opening-sentence check means something.
        "name": "same item five times, cards compared",
        "query": "vintage levi 501 jeans medium wash",
        "wardrobe": "example",
        "criterion": 4,
    },
    {
        # Criterion 5 — the outfit never names a garment the user doesn't own.
        # Needs a non-empty wardrobe and an item the wardrobe can actually be
        # styled around. An accessory is the harder case on purpose: there is
        # less in the wardrobe that obviously goes with a bag, which is when a
        # model is most tempted to invent a piece.
        "name": "outfit names only owned garments",
        "query": "tan leather mini shoulder bag",
        "wardrobe": "example",
        "criterion": 5,
    },
    {
        # Diagnostic, not one of the five. The looser retry (stretch): the
        # data holds Levi's 501s but none in XXS, so the first search comes
        # back empty, the size filter is dropped, and the second search finds
        # them. Here so the run log carries the retry and the constraint it
        # dropped, five times over.
        "name": "empty search retries without the size filter",
        "query": "levi 501 denim size XXS",
        "wardrobe": "example",
        "criterion": None,
    },
    {
        # Diagnostic, not one of the five. The price branch firing, so the run
        # log holds evidence of the second branch under test conditions too.
        "name": "price branch fires",
        "query": "chunky brown knit cardigan",
        "wardrobe": "example",
        "criterion": None,
    },
]

WARDROBES = ("example", "empty")


def validate() -> list[str]:
    """Complain about anything malformed, before a long run rather than during."""
    problems = []
    for i, scenario in enumerate(SCENARIOS, 1):
        if not scenario.get("query", "").strip():
            problems.append(f"scenario {i} has no query")
        if scenario.get("wardrobe") not in WARDROBES:
            problems.append(
                f"scenario {i} has wardrobe {scenario.get('wardrobe')!r} — "
                f"it should be one of {WARDROBES}"
            )
    return problems
