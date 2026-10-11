# Acceptance criteria — FitFindr

Five criteria that say what "working" means for this agent, written in unit 3
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"The agent handles errors"* is an opinion.
*"When search returns nothing, the agent stops before calling the second tool,
in 5 of 5 tries"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter one. A reason that says something about your tools, your loop, or the
data earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

**Two are written for you. You write three.**

---

## 1. A matching query completes all three tools

Given a query that matches at least one listing, the agent completes all three
tool calls and returns a fit card — in at least 4 of 5 tries.

**Why this target:** The search is keyword overlap, not a model. "jumper",
"sweater" and "trainers" all return zero even though the data holds two
crewnecks, a cardigan and four pairs of shoes. Whether a query lands depends on
phrasing, so 4 of 5 — 5 of 5 would claim a synonym vocabulary I didn't build.

---

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling
`suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

**Why this target:** This path never reaches the model — regex parse, Python
filter, branch on an empty list. Nothing in it varies between runs. A branch
that works 4 times out of 5 is a broken branch, so 5 of 5.

---

## 3. The item the search picked is the item the card describes

Across 5 runs of a matching query, `session["selected_item"]["id"]` equals
`session["search_results"][0]["id"]`, and the price and platform printed in
`session["fit_card"]` are the ones on that same item — 5 of 5.

**Why this target:** The id half is plain assignment — anything under 5 of 5
means the loop overwrote state. Price and platform come through the card
verbatim; titles get paraphrased, so they'd fail for reasons that aren't state.

---

## 4. Fit cards are in-spec and not repeats

Run the same item 5 times with the cache off. Each card is 2 to 4 sentences and
names the price and the platform once each — in at least 4 of 5. Across those
5 cards, no two share an opening sentence — 5 of 5.

The price counts as named whether it reads `$18` or `$18.0`; the platform
counts on the name alone, any capitalisation.

**Why this target:** Sentence count and the two mentions are prompt
instructions, not code — at `TEMPERATURE = 0.9` one miss in five is the cost of
a caption that doesn't read like a listing. The opening-sentence check is 5 of
5 because identical wording means the cache or the temperature is wrong, which
is a config bug, not variance.

---

## 5. The outfit never names a garment the user doesn't own

Given a non-empty wardrobe, every garment named in `session["outfit_suggestion"]`
appears in `wardrobe["items"]` — in at least 4 of 5 runs. Scored by reading the
outfit and listing each piece it names; a piece counts as owned if its wardrobe
`name` is recognisable in the sentence ("Chunky white sneakers" named as "the
chunky white sneakers" counts, "white sneakers" with no such item does not).
The new item itself doesn't count — it's the thing being styled.

**Why this target:** "Never invent a piece that is not on the list" is a line in
a system prompt, and a model that wants a complete outfit will reach for a belt
nobody owns. 4 of 5 rather than 5 of 5 because the only thing stopping it is
wording — if I wanted 5 of 5 I'd have to check the output in code and retry,
which I haven't built. This is the failure that matters most here: advice naming
clothes you don't have is worse than no advice.

> **Revised in unit 4:** Given a non-empty wardrobe, every garment named in
> `session["outfit_suggestion"]` appears in `wardrobe["items"]` **and** across
> 5 tries on the same item no two outfits share an opening sentence — both in
> at least 4 of 5 tries, scored the same way plus an exact-string comparison of
> first sentences, split on `.!?`.
>
> **Why revised:** the original measured the wrong half of the output. It sets
> a floor on correctness and no ceiling on repetition, so an agent that returns
> one correct outfit forever scores 5 of 5 on it — which is exactly what
> happened in the before run: five independent model calls at temperature 0.9
> with caching off, and four of the five opened with the identical sentence.
> The original line is unfalsifiable against the defect it was written to catch.
> Criterion 4b already applies the opening-sentence test to fit cards; this
> extends the same checkable test to outfits. The target stays at 4 of 5 —
> revising the measure, not loosening the number.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 4 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 4. Fit cards are in-spec and not repeats

         The fit card is different every time.

         **Why this target:** ...

         > **Revised in unit 4:** For 5 different items, the 5 fit cards share
         > no opening sentence.
         >
         > **Why revised:** "different" wasn't checkable — two cards that
         > differed by one word still counted. The new version is something I
         > can actually score.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said the empty search stops it 5 of 5 times, but I got 3 of 5,
            so 3 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
