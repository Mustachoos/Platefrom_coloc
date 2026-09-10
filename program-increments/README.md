# Program Increment workflow

How a batch of new features gets specified, split, built, tested, and documented in this
project. Each PI (Program Increment) is 3-5 big features, run through the same six stages below,
with every stage's output written to disk so the next stage — often a fresh, context-free
agent — can pick up the work from files alone instead of a replayed conversation.

That's the core cost control: agents in stages 3-5 start cold. They are only ever as good, and
as cheap, as the `.md` file they're handed. If a story file is vague, the agent re-derives context
by re-reading the codebase, which is the expensive failure mode this process exists to avoid.

## Stages

**1. Feature intake.** The user proposes 3-5 big features for the PI in plain language.

**2. Formalization (business analyst pass).** Each feature is turned into precise, unambiguous
prose: problem, scope, out-of-scope, actors affected. Done inline in conversation — no value in
a fresh agent re-deriving context I already have from the user's framing.

**3. Splitting into User Stories.** Each feature is broken into US, and — critically — each US
spec fixes its **contract** before any code is written: inputs/outputs, the interface being
added or changed, and acceptance criteria as given/when/then. This is what lets dev and test
happen in parallel without the two negotiating with each other mid-flight: they both implement
against the same fixed contract. Also done inline; this is where the story files are authored.

**4. Dependency planning.** A planner pass reads all US for the PI and produces:
- a dependency graph (which US block which),
- **waves**: batches of US with no shared dependencies, meant to be dispatched together as
  parallel agent calls in one message, not run one after another.

A flat ordered list isn't enough — the wave grouping is what makes parallel dispatch possible
downstream, which is where the real token savings are (parallel agents share the dispatcher's
prompt cache; sequential agents don't and each pays full re-read cost).

**5. Dev + test, per US.** For each US, a dev agent and a test agent are dispatched against the
same story file and the same fixed contract from stage 3. Both start cold — the story file is
their entire briefing, plus pointers to the relevant existing files (and a `graphify query`
where useful instead of an unguided grep of the repo).

Definition of Done for a US:
- code implements the contract in the story file,
- its own unit test(s) pass,
- the **full existing test suite for the PI** still passes (regression, not just the new test),
- status logged in `03-dev-log.md`.

**6. README update.** Once every US in the PI is done, one batched pass updates the root
`README.md` with the new features and any new workflows — not incrementally per-story. One clean
diff at PI-end instead of accumulating merge churn across the PI.

## Folder layout per PI

```
program-increments/PI-<n>-<slug>/
  00-features.md          the 3-5 features as formalized in stage 2
  01-stories/
    US-<feature-slug>-<n>.md   one file per story: description, contract, acceptance criteria, deps
  02-dependency-plan.md    stage 4 output: dependency graph + dev waves
  03-dev-log.md            per-story status, test results, commit refs
  04-readme-diff.md        what changed in README.md, kept for review before merging
```

## Starting a new PI

1. User proposes the 3-5 features.
2. Formalize + split inline (stages 2-3) → write `00-features.md` and `01-stories/*.md`.
3. Run the planner pass (stage 4) → write `02-dependency-plan.md`.
4. Dispatch dev+test agents wave by wave (stage 5), logging to `03-dev-log.md` as each US closes.
5. Batch the README update (stage 6) → write `04-readme-diff.md`, then apply it to `README.md`.
