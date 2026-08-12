# Frontend & UX Specification

## 1. Aesthetic

The UI should feel like a minimal research notebook, not a chat app.

Visual principles:

- monochrome-first palette;
- one restrained accent color at most;
- generous whitespace;
- 1px borders;
- subtle radius, not pill-heavy design;
- no gradients required;
- no large decorative illustrations;
- motion only when it communicates state;
- typography and hierarchy do most of the visual work.

## 2. Recommended frontend stack

- Next.js App Router
- TypeScript
- Tailwind CSS
- `shadcn/ui` selectively, not wholesale
- `lucide-react` icons
- native `fetch` or TanStack Query for history endpoints
- Server-Sent Events or streaming `fetch` for progress

## 3. Page structure

```text
/                   Research screen
/r/[runId]          Shareable result page
/history            Authenticated run history
/about              Short methodology / limitations
```

## 4. Main screen

### Header

Left:

- wordmark: `DeepScout`

Right:

- History
- About
- Sign in / user menu

Keep the header under ~64 px.

### Hero / input state

Preferred copy:

**Research with evidence.**

Supporting line:

"Ask a focused question. DeepScout searches, reads, and returns a source-backed brief."

Input:

- multiline textarea;
- auto-resizes up to ~8 lines;
- `Cmd/Ctrl + Enter` submits;
- character count appears only near limit;
- submit button label: `Research`.

Example prompts may appear as quiet text buttons below the input, maximum three.

## 5. Researching state

Do not show fake chain-of-thought. Show only stage-level telemetry.

Example:

```text
Researching

✓ Planning search
✓ Searching sources                7 found
● Reading sources                  4 / 6
○ Selecting evidence
○ Writing report
○ Verifying citations
```

Rules:

- completed stages use a check;
- current stage uses a subtle spinner/pulse;
- future stages remain muted;
- update counts when available;
- include a `Cancel` action only if backend cancellation is implemented.

## 6. Complete state

Desktop layout:

```text
-----------------------------------------------
Report                         Sources (sticky)
-----------------------------------------------
Executive summary              [1] Source card
                               [2] Source card
Key findings                   [3] Source card

Comparison / analysis

Limitations
-----------------------------------------------
```

Mobile:

- report first;
- sources become a collapsible section after the report;
- inline citations remain tappable.

## 7. Citation interaction

Inline format:

```text
The framework supports structured tool calls.[1]
```

On hover/focus:

- show source title + domain in a small popover;
- do not load full page previews in v1.

Click:

- if user clicks citation marker, scroll/highlight matching source card;
- source card click opens original URL in a new tab.

## 8. Source card

Fields:

- numeric citation ID;
- title, max 2 lines;
- domain;
- optional published date if reliably parsed;
- external-link icon.

Never display a source as successfully used if retrieval failed.

## 9. Error UX

### Generic recoverable error

Title: `Research run failed`

Body should describe the stage without exposing stack traces.

Actions:

- `Try again`
- `Edit question`

### Quota error

Title: `Demo limit reached`

Body examples:

- "This demo allows 5 research runs per day per visitor. Try again after the quota resets."
- "This question exceeded the demo token budget. Try making it more focused."

### Provider unavailable

"The inference provider is temporarily unavailable. Please retry shortly."

Avoid blaming vendor names in the main UX unless useful for debugging mode.

## 10. Accessibility

- keyboard-accessible submit and source controls;
- visible focus indicators;
- WCAG AA contrast target;
- status changes announced with `aria-live="polite"`;
- never encode status by color alone;
- reduced-motion preference respected.

## 11. Performance

- shell should render before API calls;
- no large client-side chart libraries;
- lazy-load history content;
- reserve layout space for progress state to reduce shift;
- stream report progressively only if partial prose quality is acceptable; otherwise stream stages and deliver report atomically.

## 12. Design tokens

Example conceptual tokens:

```text
background: neutral-0 / neutral-950 in dark mode
surface: neutral-50 / neutral-900
text-primary: neutral-950 / neutral-50
text-muted: neutral-500 / neutral-400
border: neutral-200 / neutral-800
accent: one restrained blue/indigo/green
radius: 8-12px
content max-width: 1120px
report measure: 70-78ch
```

Keep exact color values in the Tailwind theme rather than scattered through components.
