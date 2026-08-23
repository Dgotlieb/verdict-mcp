# verdict — Build, Ship & Exposure Plan

**Scope decisions locked in:** pytest-first adapter · ~5 hrs/week (nights) · target: v0.1 public launch in ~12 weeks
**Goal behind the goal:** every week of this build should produce both working code *and* a teachable artifact for the curriculum. The plan is structured so the two are the same activity.

---

## 0. One strategic revision before building

The original brief specced a Go daemon. At five hours a week, solo, with a Python-first audience, that's the wrong call for v0.1. Build it in **Python on FastMCP**: you ship 3–4x faster, your first users can read the source (which matters enormously for a credibility project), `uv tool install verdict-mcp` makes distribution one line, and the performance-critical part — running tests — happens inside containers anyway, so daemon language barely affects perceived speed. If verdict earns a v1.0, a Go or Rust core is a great sequel story ("why we rewrote verdict") — that's future content, not present work.

Second scope cut: v0.1 ships **import-graph-based impact selection** (using `grimp` to map changed files → affected test modules), not coverage-map-based selection. Coverage maps are the precise v0.2 upgrade; the import graph is deterministic, cheap, and honest about being approximate. Say so in the README — stated limitations build more trust than silent ones.

## 1. What v0.1 is (and is not)

v0.1 is one sharp claim you can prove in a GIF: **"Your agent's test feedback, 100x smaller and actually structured — run in a sandbox, with memory."** Concretely, four MCP tools:

`verify(scope?)` — computes changed files from git, selects affected test modules via the import graph, runs pytest with `pytest-json-report` inside an ephemeral rootless container (Podman preferred, Docker fallback, auto-detected) with the worktree mounted read-only + tmpfs overlay, and returns typed verdict objects: assertion, expected/actual, minimal stack slice intersecting the diff, and a failure fingerprint (hash of normalized failure signature).

`explain_failure(check_id)` — full detail for one failure on demand, so the summary payload stays tiny.

`history(fingerprint)` — answers the question agents get wrong constantly: *did this failure exist before my change?* Backed by SQLite keyed on fingerprints. This is the feature no wrapper has; protect it in scope negotiations with yourself.

`run_checks(linters)` — ruff and mypy adapters (both emit JSON natively; nearly free to add) normalized into the same verdict schema, proving the schema generalizes beyond tests.

**Explicitly out of v0.1:** coverage-based selection, flake detection (needs run volume — v0.2), non-Python adapters (community bait — see §5), devcontainer.json support (v0.2), any web UI (never, per your own constraints).

## 2. Twelve-week milestone plan (~5 hrs/week)

| Weeks | Milestone | Definition of done | Content byproduct |
|---|---|---|---|
| 1–2 | Walking skeleton | FastMCP server; `verify` runs full pytest suite in a container on a sample repo; JSON report parsed into verdict schema v0 | Post: "Anatomy of an MCP verification server" |
| 3–4 | Fingerprints + history | Normalized failure hashing; SQLite store; `history` + `explain_failure` working; regression-vs-pre-existing verdict field | Post: "Why agents misdiagnose test failures" |
| 5–6 | Impact selection + cache | grimp import graph; diff→test-module mapping; content-addressed result cache (tree hash, check, image digest) | Post: "Import-graph test selection in 200 lines" |
| 7–8 | Hardening + DX | Podman/Docker autodetect; `verdict init` config generator; great error messages; ruff/mypy adapters; dogfood on 2–3 real OSS repos | Post: token-cost benchmark (see §4 — this is the launch asset) |
| 9–10 | Packaging + docs | PyPI + `uv tool install`; pinned executor OCI images on GHCR; README with 90-second demo GIF; copy-paste config for Claude Code, Cursor, Codex CLI; Apache-2.0; CI + release automation | The README *is* the content |
| 11–12 | Launch | Launch blog post, Show HN, registry submissions, awesome-list PRs (see §4); respond to everything for 72 hours | Launch retro post |

Rules that keep a 5 hr/week project alive: never start a session without a pre-written next task (leave yourself a `TODO-next.md` each night); every two-week milestone ends in something demoable even if ugly; if a milestone slips, cut scope from it rather than extending it — the twelve-week clock matters more than any single feature, because side projects die of staleness, not smallness.

## 3. Shipping checklist (weeks 9–10, mechanical)

Package as `verdict-mcp` on PyPI with `uv`-first install docs. Publish executor base images (`ghcr.io/<you>/verdict-runner-py3.12` etc.) with digest pinning — this is also your security story. Repo hygiene that signals seniority: Apache-2.0, `SECURITY.md` (you're running untrusted-ish code; say how sandboxing works and what it doesn't protect against — reviewers *will* probe this), architecture doc with one clean diagram, `CONTRIBUTING.md` centered on the adapter interface, conventional commits + release-please, and a test suite that tests verdict *with* verdict once it can.

## 4. Exposure plan

**The launch asset comes before the launch.** In week 7–8 you produce one rigorous, reproducible benchmark: take three real OSS repos, run an identical agent task with raw `pytest` shell-out vs. verdict, and measure tokens consumed, wall-clock, and iterations-to-green. Publish the harness in the repo. One honest number ("median 38,700 → 410 tokens per verification cycle across N=30 runs") outperforms any amount of feature prose, and it's the headline for every channel below.

**Launch week, in order:** (1) Blog post on your own domain — the benchmark plus the design story; everything else links here. (2) **Show HN** — title shaped like "Show HN: Verdict – structured, sandboxed test feedback for coding agents"; post morning US Eastern midweek; first comment is yours, stating limitations candidly (HN rewards this). (3) Registry sweep the same day: the official MCP registry, plus Glama, PulseMCP, mcp.so, Smithery, and a PR to `awesome-mcp-servers`. (4) r/Python and r/ExperiencedDevs (angle: engineering discipline for agents, not AI hype), lobste.rs if you have an invite. (5) Pitch the newsletters that cover this beat: Python Weekly, TLDR AI, Latent.Space, Changelog News — a benchmark number is exactly what they can excerpt.

**The compounding channel is build-in-public.** One short technical post per milestone (the right-hand column of the table) on your blog, cross-posted to X/LinkedIn/dev.to. You accumulate six posts before launch day — which means launch traffic lands on an author with a visible track record, not an empty blog. This sequence is also, verbatim, the first draft of your curriculum's case-study module.

**After launch, convert attention into gravity:** tag 3–5 `good-first-issue`s on the adapter interface (vitest and `go test -json` adapters are perfectly scoped external contributions — your first stranger-PR is worth more than 500 stars); submit a talk to PyCon or a local Python/AI meetup ("Turning test output into a feedback protocol for agents" — meetups are low-bar, high-credibility); and put a single quiet line in the README: *"Built as the reference project for [curriculum name]"* — the funnel, without the smell of a funnel.

**Metrics that matter** (stars are vanity): weekly installs, issues filed by strangers, one merged external adapter PR, and newsletter/registry referral traffic to the curriculum page. Check monthly, not daily.

## 5. Risks and pre-decided responses

*Someone ships something similar mid-build:* likely a thin wrapper; your moat is fingerprints + history + the benchmark. Don't restart — cite them in your comparison table and keep going. *Sandboxing draws security criticism at launch:* pre-empt with SECURITY.md and honest threat-model language; "rootless container, read-only mount, no network by default" is a defensible v0.1 posture. *Motivation dip around week 6 (always week 6):* the milestone content posts are the antidote — public small wins create external pull. *Scope creep toward the Go rewrite or coverage maps:* both are written down as v0.2+; the plan is the contract with yourself.
