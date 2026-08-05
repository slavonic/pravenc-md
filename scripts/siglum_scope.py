#!/usr/bin/env python3
"""Scope the siglum-expansion problem across pravenc-md.

The Orthodox Encyclopedia abbreviates each article's headword to a siglum in the
body of its own article: КОНДАК -> "К.", "Алексий, человек Божий" -> "А. ч. Б.".
That convention makes the headword term almost unfindable by lexical search in
the very article that defines it.

Before committing to a full, case-restoring expansion, this script measures the
*scope* on real numbers: how many siglum occurrences exist, and what fraction
can be expanded safely and automatically because the grammatical case is fixed
by an adjacent agreeing modifier ("многострофных К." -> genitive plural) or a
governing preposition ("в К." -> prepositional) -- versus occurrences that
stand alone and would need editorial judgement.

It does NOT modify anything. It reports, and optionally writes one JSONL row per
occurrence for deeper analysis or to seed an expander later.

Scope of detection:
  * Single-word headwords (КОНДАК, КАНОН, ...) -- the dominant, high-value case
    that broke retrieval -- are matched and context-classified in full.
  * Multi-word headwords (А. ч. Б.) are detected and counted separately as the
    acknowledged harder case, without deep per-occurrence classification.

Usage:
    python tools/siglum_scope.py articles/ [--limit N] [--filter SUBSTR]
           [--out occurrences.jsonl] [--samples 3] [--context 45]

Requires: pymorphy3, pyyaml   (pip install pymorphy3 pyyaml)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("Missing dependency: pip install pyyaml")
try:
    import pymorphy3
except ImportError:
    sys.exit("Missing dependency: pip install pymorphy3")

# Prepositions whose object's case is grammatically governed → the siglum's case
# is inferable without reading a modifier. (Not exhaustive, but the common ones.)
PREPOSITIONS = {
    "в", "во", "на", "о", "об", "обо", "при", "по", "с", "со", "из", "изо",
    "от", "ото", "до", "у", "к", "ко", "за", "над", "надо", "под", "подо",
    "перед", "передо", "про", "для", "без", "безо", "через", "сквозь",
    "между", "меж", "среди", "около", "возле", "вокруг", "ради", "против",
    "кроме", "вместо", "внутри", "близ",
}

# Words that do NOT contribute an initial to a multi-word siglum (articles skip
# these when forming the abbreviation). Conservative list.
SIGLUM_SKIP = {"и", "во", "в", "на", "с", "со", "от", "из", "к", "о", "об",
               "для", "при", "по", "за", "над", "под", "у", "не", "ни"}

CYR = "А-Яа-яЁё"
_WORD = re.compile(f"[{CYR}]+(?:-[{CYR}]+)?")
_TITLE_TOKENS = re.compile(f"[{CYR}]+")

morph = pymorphy3.MorphAnalyzer()
_CASE_CACHE: dict[str, tuple] = {}


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split a `---`-delimited YAML frontmatter file into (metadata, body)."""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            try:
                meta = yaml.safe_load(parts[1]) or {}
            except yaml.YAMLError:
                meta = {}
            return meta, parts[2]
    return {}, text


def siglum_letters(title: str) -> list[str]:
    """Ordered initial letters of the significant headword words.

    'КОНДАК' -> ['К']; 'АЛЕКСИЙ, ЧЕЛОВЕК БОЖИЙ' -> ['А', 'Ч', 'Б'].
    """
    letters = []
    for w in _TITLE_TOKENS.findall(title):
        if w.lower() in SIGLUM_SKIP:
            continue
        letters.append(w[0].upper())
    return letters


def build_siglum_regex(letters: list[str]) -> re.Pattern | None:
    """Regex matching the dotted-initial siglum in body text, case-insensitive.

    Single letter L -> matches 'L.' as a standalone abbreviation, not glued to
    other Cyrillic. Multi-letter -> the full 'A. b. C.' dotted sequence.
    A negative lookbehind/ahead keeps it off personal-initial runs where we can.
    """
    if not letters:
        return None
    esc = [re.escape(l) for l in letters]
    if len(letters) == 1:
        # standalone single-letter siglum, not preceded/followed by Cyrillic
        pat = rf"(?<![{CYR}])(?:{esc[0]})\.(?![{CYR}])"
    else:
        # dotted initials separated by optional spaces: "А. ч. Б."
        pat = rf"(?<![{CYR}])" + r"\.\s*".join(esc) + r"\."
    return re.compile(pat, re.IGNORECASE)


MODIFIER_POS = {"ADJF", "ADJS", "PRTF", "PRTS", "NUMR"}

# Abbreviations whose trailing dot is NOT a sentence end. Without this, every
# "сир. Г." or "в 1939 г. А." looks like a new sentence (and vice versa: without
# sentence detection, "церковным. А." looks like agreement). Extend freely —
# the encyclopedia's abbreviation set is large and this list drives accuracy.
ABBREV = {
    # languages / peoples / adjectival
    "сир", "греч", "лат", "слав", "церк", "христ", "визант", "евр", "араб",
    "груз", "арм", "рус", "серб", "болг", "копт", "эфиоп", "зап", "вост",
    "сев", "юж", "южнослав", "древнерус", "старослав", "цслав", "к-польск",
    "правосл", "католич", "монаш", "литург", "богослуж",
    # ranks / titles
    "св", "свт", "прп", "прмч", "сщмч", "мч", "мц", "блж", "блгв", "ап",
    "архиеп", "еп", "митр", "патр", "игум", "архим", "прот", "иером", "мон",
    "равноап", "прав", "исп", "новомч", "имп", "кн",
    # bibliographic / editorial
    "г", "гг", "в", "вв", "ст", "стб", "с", "т", "тт", "изд", "ред", "пер",
    "сост", "примеч", "напр", "др", "ср", "см", "ок", "нач", "кон", "сер",
    "пол", "л", "лл", "об", "рис", "табл", "ч", "гл", "отд", "вып", "сб",
    "е", "д", "п", "н", "м", "мн", "тыс", "млн",
}

_TOKEN = re.compile(rf"[{CYR}]+(?:-[{CYR}]+)?|\d+")


def word_info(word: str) -> tuple[str | None, str | None, str | None, bool]:
    """(POS, case, number, is_pronominal) for a word, cached."""
    key = word.lower()
    if key in _CASE_CACHE:
        return _CASE_CACHE[key]
    p = morph.parse(word)
    if not p:
        out = (None, None, None, False)
    else:
        tag = p[0].tag
        out = (
            str(tag.POS) if tag.POS else None,
            str(tag.case) if tag.case else None,
            str(tag.number) if tag.number else None,
            "Apro" in tag,          # который, этот, наш … — relative/demonstrative
        )
    _CASE_CACHE[key] = out
    return out


def classify(body: str, start: int) -> tuple[str, str | None, str | None, str]:
    """Classify one siglum occurrence by the grammar immediately before it.

    Returns (klass, case, number, trigger_word) where klass is one of:
      modifier         adjacent agreeing adjective/participle fixes the case
      prep             adjacent governing preposition fixes the case
      sentence_initial the siglum opens a sentence (likely nominative subject,
                       but only verb agreement proves it) — NOT auto-expandable
      noun_head        directly preceded by a noun (often a genitive dependent,
                       e.g. "жанры сир. Г.") — a plausible next-level heuristic
      standalone       nothing usable

    Punctuation matters: "церковным. А." is a sentence break, so "церковным"
    does NOT agree with the siglum, while "сир. Г." is an abbreviation dot and
    the phrase continues. Only strictly adjacent triggers count — in
    "с именем А." the preposition governs "именем", not the siglum.
    """
    before = body[max(0, start - 120):start]
    toks = list(_TOKEN.finditer(before))
    if not toks:
        return "sentence_initial", None, None, ""

    last = toks[-1]
    word = last.group(0)
    gap = before[last.end():]          # raw punctuation/space before the siglum

    # hard sentence terminators
    if re.search(r"[!?;:]", gap):
        return "sentence_initial", None, None, word
    # a period ends the sentence unless the preceding token is a known
    # abbreviation or a number ("1939 г." keeps the sentence going)
    if "." in gap and word.lower() not in ABBREV and not word.isdigit():
        return "sentence_initial", None, None, word
    # a comma, dash, bracket or quote breaks direct modification
    if re.search(r"[,\-–—()\[\]«»\"]", gap):
        return "standalone", None, None, word

    if word.lower() in PREPOSITIONS:
        return "prep", None, None, word

    pos, case, number, is_apro = word_info(word)
    if pos in MODIFIER_POS and case and not is_apro:
        return "modifier", case, number, word
    if pos == "NOUN":
        return "noun_head", None, None, word
    return "standalone", None, None, word


def context(body: str, start: int, end: int, width: int) -> str:
    s = body[max(0, start - width):end + width].replace("\n", " ")
    return re.sub(r"\s+", " ", s).strip()


def main() -> None:
    ap = argparse.ArgumentParser(description="Scope siglum expansion across pravenc-md.")
    ap.add_argument("articles_dir", nargs="?", default="articles",
                    help="Directory of *.md article files (default: articles).")
    ap.add_argument("--limit", type=int, default=0, help="Process only the first N files.")
    ap.add_argument("--filter", default="", help="Only titles containing this substring (ci).")
    ap.add_argument("--out", default="", help="Write one JSONL row per occurrence here.")
    ap.add_argument("--samples", type=int, default=3, help="Example occurrences per class to print.")
    ap.add_argument("--context", type=int, default=45, help="Context chars around each example.")
    args = ap.parse_args()

    files = sorted(Path(args.articles_dir).glob("*.md"))
    if args.limit:
        files = files[: args.limit]
    if not files:
        sys.exit(f"No *.md files in {args.articles_dir!r}.")

    out_fh = open(args.out, "w", encoding="utf-8") if args.out else None

    n_articles = n_single = n_multi = 0
    n_no_siglum = 0
    single_occ = Counter()          # class -> count
    case_dist = Counter()           # case -> count (modifier occurrences)
    number_dist = Counter()
    multi_articles = 0
    multi_occurrences = 0
    per_article_counts = []         # single-word siglum count per article
    top_articles = Counter()        # title -> siglum occurrences
    samples: dict[str, list] = {"modifier": [], "prep": [], "sentence_initial": [],
                                "noun_head": [], "standalone": []}
    multi_samples: list = []

    for i, f in enumerate(files, 1):
        meta, body = parse_frontmatter(f.read_text(encoding="utf-8"))
        title = str(meta.get("article_title", "")).strip()
        if not title:
            continue
        if args.filter and args.filter.lower() not in title.lower():
            continue
        n_articles += 1

        letters = siglum_letters(title)
        rx = build_siglum_regex(letters)
        if rx is None:
            continue
        multiword = len(letters) > 1

        matches = list(rx.finditer(body))
        if not matches:
            n_no_siglum += 1

        if multiword:
            n_multi += 1
            if matches:
                multi_articles += 1
                multi_occurrences += len(matches)
                if len(multi_samples) < args.samples and matches:
                    m = matches[0]
                    multi_samples.append(
                        (title, context(body, m.start(), m.end(), args.context)))
            continue

        # single-word headword: classify each occurrence
        n_single += 1
        count_here = 0
        for m in matches:
            # skip if this looks like part of a personal-initial run: "К. В."
            after = body[m.end(): m.end() + 4]
            if re.match(rf"\s*[{CYR}]\.", after):
                continue
            klass, case, number, trig = classify(body, m.start())
            single_occ[klass] += 1
            count_here += 1
            if klass == "modifier":
                if case:
                    case_dist[case] += 1
                if number:
                    number_dist[number] += 1
            if len(samples[klass]) < args.samples:
                samples[klass].append(
                    (title, trig, context(body, m.start(), m.end(), args.context)))
            if out_fh:
                out_fh.write(json.dumps({
                    "id": f.stem, "title": title, "siglum": letters[0] + ".",
                    "class": klass, "case": case, "number": number,
                    "trigger": trig,
                    "context": context(body, m.start(), m.end(), args.context),
                }, ensure_ascii=False) + "\n")
        if count_here:
            per_article_counts.append(count_here)
            top_articles[title] += count_here

        if i % 2000 == 0:
            print(f"  ...{i}/{len(files)} files", file=sys.stderr)

    if out_fh:
        out_fh.close()

    # ---- report ----
    total_single = sum(single_occ.values())
    expandable = single_occ["modifier"] + single_occ["prep"]

    def pct(x, whole):
        return f"{100 * x / whole:.1f}%" if whole else "0.0%"

    print("\n" + "=" * 64)
    print("SIGLUM SCOPING REPORT — pravenc-md")
    print("=" * 64)
    print(f"Articles scanned:            {n_articles}")
    print(f"  single-word headwords:     {n_single}")
    print(f"  multi-word headwords:      {n_multi}")
    print(f"  no headword siglum found:  {n_no_siglum}")

    print("\n--- SINGLE-WORD headwords (the automatable target) ---")
    print(f"Total siglum occurrences:    {total_single}")
    print(f"  agreeing modifier (adjacent): {single_occ['modifier']:>7}  ({pct(single_occ['modifier'], total_single)})")
    print(f"  governing preposition (adj.): {single_occ['prep']:>7}  ({pct(single_occ['prep'], total_single)})")
    print(f"  => SAFELY EXPANDABLE:         {expandable:>7}  ({pct(expandable, total_single)})")
    print()
    print(f"  sentence-initial (likely nom):{single_occ['sentence_initial']:>7}  ({pct(single_occ['sentence_initial'], total_single)})")
    print(f"  after noun (often genitive):  {single_occ['noun_head']:>7}  ({pct(single_occ['noun_head'], total_single)})")
    print(f"  standalone / unresolved:      {single_occ['standalone']:>7}  ({pct(single_occ['standalone'], total_single)})")

    if case_dist:
        print("\n  case of modifier-fixed occurrences:")
        for c, n in case_dist.most_common():
            print(f"    {c:<6} {n:>7}  ({pct(n, sum(case_dist.values()))})")
    if number_dist:
        print("  number:", ", ".join(f"{k}={v}" for k, v in number_dist.most_common()))

    if per_article_counts:
        per_article_counts.sort()
        mid = per_article_counts[len(per_article_counts) // 2]
        print(f"\n  per-article siglum count: min {per_article_counts[0]}, "
              f"median {mid}, max {per_article_counts[-1]}")
        print("  most siglum-dense articles:")
        for title, n in top_articles.most_common(8):
            print(f"    {n:>5}  {title}")

    print("\n--- MULTI-WORD headwords (harder; not auto-classified) ---")
    print(f"Articles with a multi-word siglum in body: {multi_articles}")
    print(f"Total multi-word siglum occurrences:       {multi_occurrences}")

    print("\n--- EXAMPLES ---")
    for klass in ("modifier", "prep", "sentence_initial", "noun_head", "standalone"):
        if samples[klass]:
            print(f"\n  [{klass}]")
            for title, trig, ctx in samples[klass]:
                tg = f"(trigger: {trig}) " if trig else ""
                print(f"    {title}: {tg}…{ctx}…")
    if multi_samples:
        print("\n  [multi-word]")
        for title, ctx in multi_samples:
            print(f"    {title}: …{ctx}…")

    print("\n" + "=" * 64)
    print(f"HEADLINE: of {total_single} single-word siglum occurrences, "
          f"{pct(expandable, total_single)} are SAFELY auto-expandable")
    print("          (strictly adjacent modifier or preposition, no sentence break).")
    print(f"          A further {pct(single_occ['sentence_initial'], total_single)} are sentence-initial "
          "(resolvable via verb agreement)")
    print(f"          and {pct(single_occ['noun_head'], total_single)} follow a noun "
          "(often genitive) — both need more work.")
    print("=" * 64)
    if args.out:
        print(f"\nPer-occurrence detail written to {args.out}")


if __name__ == "__main__":
    main()
