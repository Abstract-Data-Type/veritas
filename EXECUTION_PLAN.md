## VeritasNews — Four-Prototype Execution Plan

Purpose: Clear, step-by-step build notes for an AI/code agent that cannot take screenshots or use Google Drive. All outputs (notes, prompts, examples) must be saved as Markdown/text inside this repo.

Scope & constraints:
- No screenshots; use text examples and short walkthroughs instead.
- No Google Drive; store everything in-repo.
- Human will deploy to Vercel; you must ensure the project builds locally and is ready for import.
- Keep code minimal and readable; prefer the simplest working approach.

Deliverables overview:
- Four branches: `feat/VERITAS-11-prototype-1` → `feat/VERITAS-11-prototype-4` (each builds on the last).
- A working app per branch (local `npm run build` succeeds).
- `docs/notebook.md` with prompts, examples (text), and reflections for each prototype.
- `data/feed.json` with 4–6 topics (mock data) used by all prototypes.

### Step 0 — Prerequisites and Local Setup (brief)
- Node.js 18+ and npm 9+ installed.
- Initialize a Next.js App Router project (JavaScript, minimal dependencies):
```bash
npx create-next-app@latest veritasnews-web \
  --use-npm \
  --eslint \
  --app \
  --no-tailwind \
  --no-src-dir \
  --import-alias "@/*"
```
- Verify dev and build locally:
```bash
cd veritasnews-web
npm run dev
npm run build
```

### Step 1 — Repository Layout and Shared Files (brief)
Create minimal shared structure (paths relative to project root). Add files progressively in later steps.
- `data/feed.json` (mock topics; 4–6 entries)
- `app/page.js` (feed page)
- `app/topic/[id]/page.js` (detail stub; P2+)
- `components/ContextBlurb.js`
- `components/CoveragePills.js`
- `components/TopicCard.js`
- `components/SortBar.js` (P2+)
- `components/QuickCompareDrawer.js` (P3+)
- `components/PrimarySourceList.js` (P2+)
- `components/Toast.js`
- `components/DotViz.js` (P4)
- `lib/sorting.js`, `lib/metrics.js`
- `docs/notebook.md` (final notebook; no screenshots, text examples only)

### Prototype 1 — Static Feed Mock (Baseline)
Objective: Demonstrate the information hierarchy with static JSON; no interactivity beyond links.

User flow:
- Open `/` → see 3–5 `TopicCard`s.
- “Compare two angles” may be disabled/no-op.
- “Open source” links on examples point to example URLs.

Implementation notes:
- Branch: `feat/VERITAS-11-prototype-1`.
- Create `data/feed.json` with 4–6 topics (see object shape in spec; include at least the four sample topics provided).
- Implement `components/ContextBlurb.js`, `components/CoveragePills.js`, `components/TopicCard.js` with minimal inline styles and accessible labels (“Context”, “Coverage”).
- In `app/page.js`, import `data/feed.json` and map topics to `TopicCard` ordered by `updatedAt` desc.
- Show novelty badge “New to you” if `novelty.score > 0.6`.
- Add empty state: “No topics right now. Try refresh.”

Verification:
```bash
npm run build && npm run start -p 3000
```

Notebook (to fill later in `docs/notebook.md`):
- Paste the P1 prompt.
- Add 1–2 text examples of rendered cards (title, context, coverage counts, novelty badge).
- Add ≤½ page reflections on clarity and hierarchy.

### Prototype 2 — Interactive Sorting (Success)
Objective: Add client-side sorting and a topic detail stub while continuing to use static JSON.

User flow:
- Open `/` → default “Sorted by: Recency”.
- Change SortBar to “Diversity” or “Novelty” → cards reorder instantly.
- Click “Open topic” → navigate to `/topic/:id` with repeated info and primary sources.

Implementation notes:
- Branch: `feat/VERITAS-11-prototype-2` (branch off `feat/VERITAS-11-prototype-1`).
- Add `components/SortBar.js` (select with Recency/Diversity/Novelty + helper text under it).
- Add `lib/metrics.js` and `lib/sorting.js` for diversity calculation and sort helpers.
- Manage sort mode with React state in `app/page.js`; compute sorted array per mode.
- Add `/topic/[id]/page.js` stub showing Title, UpdatedAt, Context, Coverage pills, and `PrimarySourceList` with “Why this matters”.

Verification:
```bash
npm run build && npm run start -p 3000
```

Notebook:
- Paste the P2 prompt.
- Provide text lists of topic IDs for each sort mode order.
- Add ≤½ page notes on perceived responsiveness and reduced uncertainty.

### Prototype 3 — Quick Compare Drawer (Exploratory)
Objective: Let users preview two contrasting article angles inline before clicking out.

User flow:
- Click “Compare two angles” on a card → a drawer expands within that card.
- Shows two ArticleMini panels (Left vs Right) from `coverage.examples`.
- If fewer than 2 distinct leans, show: “Not enough contrasting coverage yet.”
- Only one drawer open at a time; opening a new one closes the previous.

Implementation notes:
- Branch: `feat/VERITAS-11-prototype-3` (branch off `feat/VERITAS-11-prototype-2`).
- Add `components/QuickCompareDrawer.js`; render outlet, lean badge text, headline (1-line), oneLineAngle, and “Open source” link.
- Track `openTopicId` in the feed page; pass `drawerOpen` and `onToggleDrawer` to `TopicCard`.
- Provide keyboard control (Enter/Space toggles); set `aria-expanded` on the toggle button.
- Add a small chevron (optional) that visually indicates open state.

Verification:
```bash
npm run build && npm run start -p 3000
```

Notebook:
- Paste the P3 prompt.
- Include textual drawer content for one topic (Left vs Right mini details and URLs).
- ≤½ page on whether the contrast is understandable.

### Prototype 4 — Personalized Feed with Visualization (Experimental)
Objective: Visualize diversity×novelty and add a toggle to prioritize unfamiliar perspectives.

User flow:
- Toggle ON: “Prioritize unfamiliar perspectives” → order prefers high diversity and novelty.
- Each card shows a tiny 40×40 dot viz placing a point at (diversity, novelty) with an aria-label.
- Below the card, include a brief “Why this order?” disclosure.

Implementation notes:
- Branch: `feat/VERITAS-11-prototype-4` (branch off `feat/VERITAS-11-prototype-3`).
- Add `components/DotViz.js` (no external chart libs).
- Sorting when ON: score = diversity*0.6 + novelty*0.4; reuse shared `sortTopics` helper.
- Update `TopicCard` to show the viz and the two-line disclosure when toggle is ON.

Verification:
```bash
npm run build && npm run start -p 3000
```

Notebook:
- Paste the P4 prompt.
- Provide OFF vs ON text ordering of topic IDs; include one aria-label example.
- ≤½ page on whether the toggle materially changes ordering and viz legibility.
 
### Notebook template and prompts (to create `docs/notebook.md`)
At repo path `docs/notebook.md`, paste the following scaffold and fill in as you build. Use text examples instead of screenshots. Match the style in the example (Interaction Paradigm, Tech Stack/Model, Branch/Deployed links, Pros/Cons, Example interaction when relevant).

```markdown
# VeritasNews Prototypes Notebook

- Overall feature: Help readers make deliberate, informed choices by surfacing neutral context and diversity before clicking.
- Linear issue: <PASTE_LINEAR_LINK>
- GitHub repo: <PASTE_REPO_LINK>
- Best prototype (deployed): <PASTE_VERCEL_URL>

# Prototype 1 — Static Feed Mock (Baseline)
- Interaction Paradigm: Static web feed (no interactivity)
- Tech Stack: Next.js App Router (JS)
- Model (if any): N/A
- Branch Link: <https://github.com/.../tree/feat/VERITAS-11-prototype-1>
- Deployed Link: <PASTE_OR_NA>

Prompt (Model: <MODEL_IF_USED>):
<P1_PROMPT_TEXT>

Pros / Cons:
- Pros: Clear hierarchy; fast to render; minimal complexity.
- Cons: No interactivity; limited demonstration of behavior.

Examples (text):
- Title: Congress advances grid resilience funding
  - Context: Lawmakers advanced a package...
  - Coverage: Left 3 · Center 2 · Right 2
  - Novelty: New to you (0.74)

# Prototype 2 — Interactive Sorting (Success)
- Interaction Paradigm: Web app with client-side sorting
- Tech Stack: Next.js App Router (JS)
- Model (if any): N/A
- Branch Link: <https://github.com/.../tree/feat/VERITAS-11-prototype-2>
- Deployed Link: <PASTE_OR_NA>

Prompt (Model: <MODEL_IF_USED>):
<P2_PROMPT_TEXT>

Pros / Cons:
- Pros: Instant feedback; clearly demonstrates diversity/novelty value.
- Cons: Still static data; no persistence.

Examples (text):
- Recency order: [...]
- Diversity order: [...]
- Novelty order: [...]

# Prototype 3 — Quick Compare Drawer (Exploratory)
- Interaction Paradigm: Web app with in-card drawer
- Tech Stack: Next.js App Router (JS)
- Model (if any): N/A
- Branch Link: <https://github.com/.../tree/feat/VERITAS-11-prototype-3>
- Deployed Link: <PASTE_OR_NA>

Prompt (Model: <MODEL_IF_USED>):
<P3_PROMPT_TEXT>

Pros / Cons:
- Pros: Signature behavior; contrast visible without leaving.
- Cons: Requires careful accessibility; limited by example availability.

Examples (text):
- Drawer content for grid topic:
  - Left: The Nation — “Congress boosts climate resilience...” — angle: climate readiness
  - Right: WSJ — “House advances grid plan...” — angle: costs and permitting

# Prototype 4 — Personalized Feed with Visualization (Experimental)
- Interaction Paradigm: Web app with personalization toggle + micro-viz
- Tech Stack: Next.js App Router (JS)
- Model (if any): N/A
- Branch Link: <https://github.com/.../tree/feat/VERITAS-11-prototype-4>
- Deployed Link: <PASTE_OR_NA>

Prompt (Model: <MODEL_IF_USED>):
<P4_PROMPT_TEXT>

Pros / Cons:
- Pros: Makes prioritization legible; accessible viz with aria-labels.
- Cons: Heuristic ranking; viz is intentionally simple.

Examples (text):
- Toggle OFF (Recency): [...]
- Toggle ON (Personalized): [...]
- Viz aria-label example: “Diversity 0.67, Novelty 0.74”
```

Prompts to use (paste into the notebook as you go):
- P1: Build a minimal Next.js App Router page that renders a feed of Topic cards using `data/feed.json`. Each card shows Title, a Context section, Coverage pills (Left/Center/Right counts with text and subtle background color), a novelty badge if score > 0.6, and two actions: a disabled “Compare two angles” and an “Open topic” link (can be `#`). Keep styling simple and accessible.
- P2: Add a client-side SortBar for Recency/Diversity/Novelty with helper text; add `/topic/[id]` that repeats the card and lists primary sources (“Why this matters”).
- P3: Add `QuickCompareDrawer` that shows two contrasting ArticleMinis (left vs right). If insufficient contrast, show a fallback. Only one drawer open at a time. Keyboard toggle + `aria-expanded`.
- P4: Add a toggle “Prioritize unfamiliar perspectives” that orders by diversity*0.6 + novelty*0.4 and show a tiny 40×40 dot viz with an aria-label.

### Deployment (human executes on Vercel) and Done criteria

Deployment (you prepare; human deploys):
- Ensure local build passes on the branch to deploy (recommend P4):
```bash
npm run build
```
- Push all branches to GitHub and confirm repository visibility.
- Human: In Vercel → New Project → Import GitHub repo → Framework: Next.js (auto) → Build: `npm run build` → Output: `.next` (auto) → No env vars needed → select branch and deploy.
- Copy the production URL and paste it at the top of `docs/notebook.md`.

Done criteria checklist:
- Four branches exist
- Each branch builds locally without errors.
- `docs/notebook.md` is complete for all four prototypes (no empty sections; text examples included).
- One prototype is deployed; the deployed link is recorded in the notebook along with Linear and GitHub links.
