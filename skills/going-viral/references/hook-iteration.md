---
name: hook-iteration
description: What to do when the user wants to change, tweak, swap, punch up, or replace a hook you already generated — picking the right hook by position or topic, choosing a cheap in-place edit over a full regenerate, and never re-pitching a hook they rejected.
---

# Hook Iteration

The user generated some hooks and now wants to change one. Your job is to route correctly: a small textual tweak is a cheap in-place `edit_hook`; a new angle is a full `generate_hooks_tool` pass. Get this split right and iteration feels instant; get it wrong and you either burn a generation on a one-word fix or paper over a request that needed real creative work.

## Addressing a hook

Hooks are referenced by their **UUID**. The most recent generation's tool result carries a `generated_hooks` manifest: a list of `{id, title, post_type}` for **every** hook that was shown — including the ones the user didn't select. That manifest is your source of truth.

- "Make the second one punchier" → the 2nd entry in `generated_hooks` (manifest order matches the card order the user saw).
- "Edit the hook about morning routines" → match on `title` in the manifest.
- **Never invent or guess an id.** If you can't resolve which hook they mean, ask — don't edit a random one. If there's no manifest in the conversation at all, there's nothing to iterate on yet; generate first.

## What each field means

- **`title`** — the hook itself: the opening line / video concept. This is what 90% of "make it punchier / fix the CTA / change the tone" requests touch.
- **`talking_points`** (video) — the beats the creator hits after the hook. Touch these when the user wants different content, not a different hook.
- **`shotlist`** (video) — the time-ranged shot directions. Touch only for "how do I film this" changes.
- **`scenes`** (carousel) — the per-slide text plan. The carousel equivalent of talking_points.
- **`algorithm_reason`** — why the algorithm favors this hook. Update it if you materially change the hook so the rationale still matches; don't bother for a tiny wording fix.

## The edit-vs-regen call (the crux)

**Edit in place — compose the new text yourself and call `edit_hook`:**
- punchier / tighter / shorter
- fix or swap the CTA
- adjust one talking point
- small tone shift (more casual, less salesy)
- fix a factual or brand detail

These are fast, free, and don't lose the user's place. You already know what the better version reads like — write it and persist it. Pass only the fields you changed.

**Regenerate — call `generate_hooks_tool` with a `hook_idea` seed:**
- "give me a different angle / something contrarian / a fresh take"
- a different concept or topic entirely
- a structural rethink (different hook *type* — see [hook-anatomy](./hook-anatomy.md))
- the user rejected the whole batch and wants new directions

Seed `hook_idea` with the direction the user gave so the new hooks reflect the conversation, not generic pillar output.

When in doubt, lean **edit** for anything you can express as "change X to Y on the existing hook," and **regen** for "I want something else." If a request is borderline, a quick edit is the cheaper bet — the user can always ask for a regen if it's not enough.

## Never re-suggest a rejected hook

When the user rejects hooks — by passing on a generation ("none of these", "give me something else") or by naming an angle they don't want — don't resurface those hooks or near-duplicates on the next pass. Scan the recent conversation for what they turned down before proposing anything. When you steer away, say so in a half-sentence ("Skipping the day-in-the-life angle since you passed on it — here's a sharper take") so the user knows you heard them.

## Don't

- Don't list, quote, or rewrite the hook in your chat text — `edit_hook` re-renders the card; your text must not duplicate it. Acknowledge the change in a sentence and stop.
- Don't call `edit_hook` to create a brand-new hook — it edits an existing row. New hooks come from `generate_hooks_tool`.
- Don't edit a hook the user didn't ask you to touch.
