# Which data each study was built on: the inventory, and a draft rule

22 October 2026 · For the owner · Status: **step 1 done (read-only); the rule is a draft for your decision** ·
[The index](index.md) · [The rule draft](rule_draft.md) · [Process log](process_log.md)

## What you asked

> "We dont want the studies to point to "new versions" but we may want the process of HOW to recreate the old version
> IF we need to, but may not want to keep all the old versions […] We also probably need a process to ensure future
> agents automatically update this when necessary […] without my manual execution."

Then: "start step 1 and draft the rule."

## What the inventory found

* **13 versions of the match history are on disk.**
  * the repository's own, rebuilt on 21 Oct;
  * six that the shared rebuilds saved before replacing them (7, 8, 14 and 21 Oct);
  * the frozen reference of 8 Oct;
  * five inside build folders, each with that build's accepted packages and feed merged in.

  Two pairs are the same history under different names.
* **296 of the 1,275 tables that hold matches (6.5 GB) are built on an older history** than the repository's. Most
  are studies' own outputs, as expected.
* **Almost nothing can be recreated exactly today.** The frozen reference can, because it keeps its code and
  environment beside its tables. A build folder can only while it exists, because its code lives inside it. Everything
  else lacks the code that built it.
* **Code that mixes versions: three cases confirmed.**
  * the unpriced-leads study's extra features and its rhythm features (the study behind the live five-pattern
    adjustment);
  * the serve/return study.

  Each joins an early-October table with today's history, so a few hundred to about 1,400 of roughly 870,000 matches
  silently drop or go blank. That's small, but it's silent.
  * 25 more files are candidates, and the rest of the flags are weak.
  * Reading code statically can't settle this: it missed one of the three confirmed cases. The runtime check in the
    plan, where tables carry the history they were built from and joins refuse a mismatch, is what catches mixing
    reliably.
* **The build folders take 103 GB**:
  * the model in use (17.4 GB) and its fallback (16.5 GB);
  * three older study sandboxes of 20–24 GB each;
  * small ones.

  Before any of them could become "a recipe instead of a copy", their code has to be captured, because it exists only
  inside them.

## The rule

The [draft](rule_draft.md) has seven lines. Each says whether it is your words or my choice, and which check enforces
it. It ends with three questions for you:
1. Adopt it?
2. Keep the code as one small compressed copy per version (my recommendation), or commit more often instead?
3. Delete retired model folders once their recipe is proven and backed up (my recommendation), or keep the last two?

## Next, once you've decided

Step 3 of the plan, the automation, starting with capturing the code at every build and study run. Then the two tests,
pinning the three mixing places, and the dated notes. Deletions come last.
