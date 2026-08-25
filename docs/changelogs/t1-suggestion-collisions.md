# T1 suggestion/ban collisions

Date: 2026-08-25. Data pass over `lint_data/substitutions.json`, plus the
`exceptions` gate in `lint/checks_lexical.py`.

## The defect

A T1 rule flags a word and hands the writer a replacement. In 79 places that
replacement was itself banned at error tier, as a T1 pattern, a T3 hedge, or
a T6 filler or weasel word. A writer who took the advice of the tool walked
into a new error-tier finding.

`audit/collision_audit.py` reproduces the count and now guards it. Baseline
before this pass: **79 collisions**. After: **0**.

The audit gained two passes that the original script did not have:

1. Pipe-separated menus (`also | besides | too`) are audited branch by
   branch. This found 4 more collisions that the plain string check missed.
2. Each word of a multi-word replacement is audited on its own. The ban
   tables match on word boundaries. Advice to write `so that` thus walks
   the writer into the T6 filler rule for `so`. This found 10 more, 4 of
   them in rules that this pass had not otherwise touched.

The audit exits non-zero on any collision, on any word-level collision, and
on any use of `must`. `tests/run_suggestion_tests.py` runs it.

## The `exceptions` gate

`exceptions` was dead data. The field sat in the JSON and no code read it,
and the hand fix for `pull request` thus did nothing. `check_t1` now reads
the one word in front of a match and drops the finding when that word sits
in the `exceptions` list of the rule. `lint/fixer.py` reads the same gate,
and `--fix` thus cannot rewrite a compound that the check leaves alone.

Fixture: `tests/corpus_suggestions/t1_exceptions.md`.

## Word choices

Every replacement below was checked against the live tables by the audit
script, not from memory. Two words that look safe are not: `several` and
`numerous` both sit in ban tables.

A ban elsewhere blocks the natural short word for 10 rules, and those 10
replacements read worse in isolation than the word they replace. Those rules carry a note in the last section.

| Rule id | Pattern | Old suggestion | New suggestion | Why |
| --- | --- | --- | --- | --- |
| VEI-T1-SUB-0007 | `accordingly` | `so` | `thus` (alt `as a result`) | `so` is a T6 filler |
| VEI-T1-SUB-0009 | `accurate` | `right` | `correct` (alt `exact`) | `right` is a T6 filler |
| VEI-T1-SUB-0027 | `apparent` | `clear` | `plain` (alt `obvious`) | `clear` is a T3 hedge |
| VEI-T1-SUB-0031 | `attempt` | `try` | `effort` (alt `do`) | `try` is a T6 filler |
| VEI-T1-SUB-0037 | `commence` | `begin` | `launch` (alt `open`) | `begin` is a T6 filler |
| VEI-T1-SUB-0040 | `concerning` | `about` | `on` (alt `of`) | `about` is a T3 hedge |
| VEI-T1-SUB-0042 | `consequently` | `so` | `thus` (alt `as a result`) | `so` is a T6 filler |
| VEI-T1-SUB-0061 | `endeavor` | `try` | `effort` (alt `work`) | `try` is a T6 filler |
| VEI-T1-SUB-0070 | `frequently` | `often` | `routinely` (alt `commonly`) | `often` is a T3 hedge; `many times` holds the banned `many` |
| VEI-T1-SUB-0074 | `initiate` | `start`, `begin` | `trigger` (alt `launch`) | both old alts are T6 fillers |
| VEI-T1-SUB-0086 | `optimum` | `best`, `most` | `best` (alt `ideal`) | `most` is a T3 hedge, a T6 filler, and a T6 weasel word |
| VEI-T1-SUB-0097 | `solicit` | `request` | `ask for` (alt `ask`) | `request` is itself a T1 pattern |
| VEI-T1-SUB-0107 | `along the lines of` | `as in \| like`, `similar to` | `as in \| such as` (alt `such as`) | `like` is a T3 hedge, a T6 filler, and a T6 weasel word; `similar to` is a T1 pattern |
| VEI-T1-SUB-0116 | `in a timely manner` | `on time \| promptly`, `timely` | `on time \| on schedule` (alt `on time`) | `promptly` is a T6 filler; `timely` is a T1 pattern |
| VEI-T1-SUB-0117 | `in addition` | `also \| besides \| too` | `also \| besides` (alt `also`) | `too` is a T6 filler; found by the branch pass |
| VEI-T1-SUB-0121 | `in many cases` | `often` | `commonly` (alt `routinely`) | `often` is a T3 hedge |
| VEI-T1-SUB-0124 | `pertaining to` | `about \| of \| on` | `of \| on` (alt `on`) | `about` is a T3 hedge |
| VEI-T1-SUB-0126 | `readily apparent` | `clear`, `apparent` | `obvious` (alt `plain`) | `clear` is a T3 hedge; `apparent` is a T1 pattern and a T3 hedge |
| VEI-T1-SUB-0134 | `a myriad of` | `myriad` | `countless` | `myriad` is T6 overused vocabulary |
| VEI-T1-SUB-0136 | `all of a sudden` | `suddenly` | `at once` (alt `without warning`) | `suddenly` is a T6 filler |
| VEI-T1-SUB-0139 | `almost all` | `most` | `all but a few` (alt `the bulk of`) | `most` is banned 3 times over; `nearly all` holds the banned `nearly` |
| VEI-T1-SUB-0140 | `almost never` | `seldom` | `infrequently` | `seldom` is a T3 hedge; `rarely` and `hardly` are also banned |
| VEI-T1-SUB-0142 | `an appreciable number of` | `many` | `various` (alt `plenty of`) | `many` is a T3 hedge and a T6 weasel word |
| VEI-T1-SUB-0143 | `an estimated` | `about` | `close to` | `about` is a T3 hedge; `roughly` and `nearly` are also banned |
| VEI-T1-SUB-0150 | `at all times` | `always` | `continuously` | `always` is a T3 hedge |
| VEI-T1-SUB-0157 | `carry out an evaluation of` | `evaluate` | `check` (alt `test`) | `evaluate` is a T1 pattern; the new value matches what that rule hands out |
| VEI-T1-SUB-0162 | `concerning the matter of` | `regarding` | `on` (alt `of`) | `regarding` is a T1 pattern |
| VEI-T1-SUB-0177 | `excessive number` | `too many` | `excess` | `too` and `many` are both banned; found by the word pass |
| VEI-T1-SUB-0183 | `has the ability to` | `can` | `is able to` | `can` is T3 optionality and a T3 hedge |
| VEI-T1-SUB-0184 | `has the capacity to` | `can` | `is able to` | same as above |
| VEI-T1-SUB-0185 | `has the opportunity to` | `could` | `is able to` (alt `is free to`) | `could` is T3 optionality and a T3 hedge |
| VEI-T1-SUB-0188 | `in a careful manner` | `carefully` | `with care` | `carefully` is a T6 filler |
| VEI-T1-SUB-0189 | `in a thoughtful manner` | `thoughtfully` | `with care` | `thoughtfully` is a T6 filler; `with thought` holds the banned `thought` |
| VEI-T1-SUB-0190 | `in most cases` | `usually` | `normally` (alt `as a rule`) | `usually` is banned 3 times over; `typically` is also banned |
| VEI-T1-SUB-0191 | `in some cases` | `sometimes` | `at times` (alt `on occasion`) | `sometimes` is a T3 hedge |
| VEI-T1-SUB-0195 | `in the neighborhood of` | `roughly` | `close to` | `roughly` is a T3 hedge and a T6 filler |
| VEI-T1-SUB-0197 | `it would appear that` | `apparently` | `evidently` | `apparently` is a T3 hedge and a T6 filler |
| VEI-T1-SUB-0209 | `some of the` | `some` | `part of the` | `some` is a T3 hedge |
| VEI-T1-SUB-0212 | `take into account` | `consider` | `account for` (alt `allow for`) | `consider` is a T3 hedge |
| VEI-T1-SUB-0219 | `with regard to` | `regarding` | `on` (alt `of`) | `regarding` is a T1 pattern |
| VEI-T1-SUB-0220 | `a number of` | `many`, `some` | `various` (alt `plenty of`) | both old alts are T3 hedges; `many` is also a T6 weasel word |
| VEI-T1-SUB-0232 | `appreciable` | `many` | `sizable` (alt `notable`) | `many` is a T3 hedge and a T6 weasel word |
| VEI-T1-SUB-0233 | `appropriate` | `proper`, `right` | `proper` (alt `correct`) | `right` is a T6 filler; the primary value holds |
| VEI-T1-SUB-0234 | `approximate` | `about` | `rough` (alt `close to`) | `about` is a T3 hedge |
| VEI-T1-SUB-0237 | `as to` | `about`, `on` | `on` (alt `of`) | `about` is a T3 hedge |
| VEI-T1-SUB-0255 | `deem` | `believe`, `consider`, `think` | `judge` (alts `rule`, `call`) | all 3 old alts are T3 hedges |
| VEI-T1-SUB-0268 | `evident` | `clear` | `plain` (alt `obvious`) | `clear` is a T3 hedge |
| VEI-T1-SUB-0276 | `feasible` | `can be done` | `workable` (alt `practical`) | `can` is T3 optionality; found by the word pass |
| VEI-T1-SUB-0297 | `implement` | alt `start` | alt `set up` | `start` is a T6 filler; the other 4 alts hold |
| VEI-T1-SUB-0299 | `in all likelihood` | `probably` | `expect` | `probably` is banned 4 times over; `likely` is also banned |
| VEI-T1-SUB-0303 | `in order that` | `for`, `so` | `to` (alt `for`) | `so` is a T6 filler; `so that` carries the same word |
| VEI-T1-SUB-0304 | `in regard to` | `about`, `concerning`, `on` | `on` (alt `of`) | `about` is a T3 hedge; `concerning` is a T1 pattern |
| VEI-T1-SUB-0305 | `in relation to` | `about`, `with`, `to` | `to` (alt `with`) | `about` is a T3 hedge; the other 2 alts hold |
| VEI-T1-SUB-0306 | `in some instances` | `sometimes` | `at times` (alt `on occasion`) | `sometimes` is a T3 hedge |
| VEI-T1-SUB-0313 | `in view of the above` | `so` | `thus` (alt `as a result`) | `so` is a T6 filler |
| VEI-T1-SUB-0315 | `inception` | `start` | `outset` (alt `beginning`) | `start` is a T6 filler; `beginning` clears the word boundary of `begin` |
| VEI-T1-SUB-0316 | `incumbent upon` | `must` | `shall` | O3 and DEC-TEC-TOOL-003 make `shall` the mandatory keyword |
| VEI-T1-SUB-0317 | `indicate` | alt `say` | alt `report` | `say` is a T3 hedge; the other 3 alts hold |
| VEI-T1-SUB-0323 | `is authorised to` | `may` | `is allowed to` | `may` is T3 optionality and a T3 hedge |
| VEI-T1-SUB-0324 | `is authorized to` | `may` | `is allowed to` | same as above |
| VEI-T1-SUB-0327 | `it appears` | `seems` | `evidently` | `seems` is a T3 hedge |
| VEI-T1-SUB-0329 | `it is essential` | `must` | `shall` (alt `need to`) | O3 and DEC-TEC-TOOL-003 make `shall` the mandatory keyword |
| VEI-T1-SUB-0335 | `maximum` | alt `most` | alt `highest` | `most` is banned 3 times over; `greatest` and `largest` hold |
| VEI-T1-SUB-0340 | `nevertheless` | alt `even so` | alt `all the same` | `so` is a T6 filler; found by the word pass |
| VEI-T1-SUB-0344 | `not often` | `rarely` | `infrequently` | `rarely` is a T3 hedge and a T6 filler |
| VEI-T1-SUB-0347 | `notwithstanding` | alt `in spite of` | alt dropped | `in spite of` is a T1 pattern; `despite` and `still` hold |
| VEI-T1-SUB-0352 | `on the contrary` | alt `so` | alt `instead` | `so` is a T6 filler, and reads wrong here in any case |
| VEI-T1-SUB-0353 | `on the other hand` | alt `so` | alt `by contrast` | `so` is a T6 filler, and reads wrong here in any case |
| VEI-T1-SUB-0368 | `proceed` | alt `try` | alt `continue` | `try` is a T6 filler |
| VEI-T1-SUB-0375 | `reflect` | `say`, `show` | `show` (alt `record`) | `say` is a T3 hedge |
| VEI-T1-SUB-0376 | `regarding` | `about` | `on` (alt `of`) | `about` is a T3 hedge |
| VEI-T1-SUB-0377 | `relative to` | `about` | `on` (alt `compared with`) | `about` is a T3 hedge; the alt covers the comparison sense |
| VEI-T1-SUB-0393 | `similar to` | `like` | `comparable to` (alt `close to`) | `like` is banned 3 times over |
| VEI-T1-SUB-0405 | `therefore` | `so`, `thus` | `thus` (alt `as a result`) | `so` is a T6 filler |
| VEI-T1-SUB-0419 | `warrant` | alt `permit` | alt `justify` | `permit` is a T1 pattern |
| VEI-T1-SUB-0421 | `with reference to` | `about` | `on` (alt `of`) | `about` is a T3 hedge |
| VEI-T1-SUB-0422 | `with respect to` | `about` | `on` (alt `of`) | `about` is a T3 hedge |

## Change classes

- **Preposition family (13 rules).** `about` is a T3 hedge. The whole
  `regarding` and `with respect to` family thus moved to `on`, with `of`
  as the alt. This is the largest single class.
- **Connective family (6 rules).** `so` is a T6 filler. `accordingly`,
  `consequently`, `therefore`, and `in view of the above` moved to `thus`.
  `on the contrary` and `on the other hand` took `instead` and `by contrast`,
  which also repairs a semantic error: `so` never meant either of them.
- **Modal family (6 rules).** `can`, `could`, `may`, and `must` are all
  banned. Ability phrases moved to `is able to` and `is allowed to`.
  Obligation phrases moved to `shall`, per O3.
- **Frequency family (8 rules).** `often`, `usually`, `sometimes`, `always`,
  `rarely`, and `seldom` are all T3 hedges. Each moved to a word that names
  a rate, not a feeling.
- **Quantity family (6 rules).** `many`, `most`, and `some` are hedges and
  weasel words. These moved to `various`, `all but a few`, `sizable`, and
  `part of the`, following the `multiple` and `numerous` fixes already in
  the tree.
- **Self-reference (9 rules).** A T1 rule pointed at another T1 pattern:
  `solicit` pointed at `request`, and `with regard to` pointed at
  `regarding`. Each now points past the second rule to a word that neither
  rule flags.

## T2 soft collisions

Replacements that land on a T2 vague term went from 12 to 18. T2 sits at
warning tier, and the brief ranks a natural word above a T2-clean one. The
6 new ones are `various` on 2 rules and `close to` on 4. `various` follows
the `multiple` and `numerous` fixes already in the tree. The audit prints
this list on every run.

## Flagged: rules that need a decision, not a better word

1. **`must` remains in `substitutions.json`, inside the `excluded` block.**
   Rule `shall` -> `must` was dropped at build time, and the block records
   what was dropped and why. The engine reads `rules` only, and this value
   thus never reaches a writer. A rewrite falsifies the record of what
   was excluded, and the value stands. The 424 active rules hold no `must`.

2. **`VEI-T1-SUB-0328`: `it is` -> empty string. `--fix` deletes text and
   leaves broken prose.** 14 rules carry an empty suggestion with a single
   empty alt. `lint/fixer.py` auto-applies any rule that holds one alt, and
   `--fix` thus writes the deletion to disk. Measured on this input:

   - before: `It is important that the operator selects the type of report.`
   - after `--fix`: ` important that the operator selects the  of report.`

   Two deletions in one line, both ungrammatical. `type` -> empty string
   (`VEI-T1-SUB-0412`) is the worse of the pair, because `type` is a common
   technical noun. The `omit_ok` field that the schema carries for this case
   is dead data: no code reads it. `VEI-T6-AI-0004` already catches
   `It is important to note that` as a whole phrase with a better message.
   `VEI-T1-SUB-0328` thus adds damage on top of a duplicate finding.

   Recommended: guard `lint/fixer.py` with a check that skips any rule whose
   suggestion is empty after strip. Then decide per rule whether to keep
   the T1 entry at all. Left alone in this pass, per the brief.

3. **`VEI-T1-SUB-0320`: `interface` -> `meet`.** The upstream list meant the
   verb (`interface with the vendor`). The rule fired on the noun,
   which is a core technical term for the audience of this tool, and `meet`
   is nonsense there. This one had a data-level fix, which was applied. The
   rule gained an `exceptions` list of determiners and common modifiers:
   `the`, `a`, `an`, `this`, `each`, `user`, `hardware`, `api`.
   That matches the `preceded_by` heuristic that `lint_data/pos_heuristics.json`
   already records for the noun reading, at high confidence. The verb use
   still fires. A bare `interface` with no modifier in front still fires,
   which is the residual false positive.

4. **`VEI-T1-SUB-0393`: `similar to` -> `comparable to`.** T1 means a
   shorter match exists. The only shorter match is `like`, which 3 tables
   ban. The new value holds the meaning but is not shorter. The rule thus
   no longer does what T1 claims. Recommend dropping the rule.

5. **Bare `start`, `begin`, `try`, `so`, and `right` sit in T6
   `fillers_and_intensifiers`.** These are ordinary technical verbs and
   adverbs, not filler. They forced awkward values on `commence`, `attempt`,
   `endeavor`, and `initiate` (`launch`, `effort`, `trigger`). Recommend a
   review of those 5 filler entries. A narrower pattern such as `try and`
   or `start off` frees the natural words.

6. **`VEI-T1-SUB-0299` (`in all likelihood`), `VEI-T1-SUB-0197`
   (`it would appear that`), and `VEI-T1-SUB-0327` (`it appears`) swap one
   hedge for another.** `probably`, `apparently`, and `seems` are all
   banned. The values are now `expect` and `evidently`, which read better
   but still hedge. The honest advice for all 3 is to state the claim and let T3
   catch the rest. Recommend review.

7. **`VEI-T1-SUB-0340`: `nevertheless` -> `besides`.** Not a collision, but
   `besides` does not mean `nevertheless`. `still`, already an alt, does.
   Recommend making `still` the primary value.

## Generator note

`build_lint_data.py` and `builddata/` generate `lint_data/*.json` from
`handoff/prose_lint_wordlists.json`. That source file is not in this repo.
The generator thus cannot run, and `lint_data/*.json` is the source of
truth. This pass edits the JSON directly, which is correct here.

`builddata/t1_substitutions.py` still holds the old generation logic. **A
re-run of the generator wipes every fix in this changelog**, along with
the `multiple`, `numerous`, `require`, and `request` fixes that predate it.
That is a repo-level issue, out of scope here.

## Files

- `lint_data/substitutions.json` -- 77 rules changed, 1 rule gained
  `exceptions`. Schema untouched.
- `lint/checks_lexical.py` -- `exceptions` gate in `check_t1`.
- `lint/fixer.py` -- same gate for `--fix`.
- `lint_config.json` -- `tests/corpus_suggestions/` added to `never_lint`.
- `audit/collision_audit.py` -- branch pass, word pass, non-zero exit.
- `tests/run_suggestion_tests.py` -- 4 checks.
- `tests/corpus_suggestions/*.md` -- 3 fixtures.
