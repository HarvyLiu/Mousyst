# Mousyst review and implementation plan

Reviewed 2026-11-15 · source baseline `bcbe928` · website https://mousyst.vercel.app

## 1. Recommendation

Keep the current Python/PySide6/Qt Quick desktop stack and Astro website. Preserve the accepted dark visual design, fixed suggestion space, in-place number layer, and scroll storytelling. The next release should first make input ordering and text editing dependable, then add an everyday editing shelf, shortcut favorites, and saved phrases. Improve recognition using measured failures and an explicit personal dictionary.

This document is a plan, not a claim that the changes below are implemented. The only source-tree addition from this review is this document. No new version was published and no production typing was injected during the review.

### Reviewed and verified

- Read desktop host, input adapter, UI Automation, settings, QML, recognition/editor/practice, packaging, tests, release workflow, website, and current documentation. The earlier radial prototype is historical; maintain its history rather than add features there.
- Visited the deployed homepage and docs, switched languages, tested guide search, and inspected a 390 × 844 mobile viewport.
- Existing unit suite: **28 passed**. Python lint: **passed**.
- Isolated offscreen desktop UI smoke: **passed**, including repeated keys, layouts, symbols, suggestion geometry, number-layer replacement, and bounded trail fading.
- Astro production build: **passed**, nine pages.
- Safe fake-output tests reproduced wrong punctuation shortcuts, Shift-symbol failures, unsafe auto-space deletion, and an unverified-origin delayed insertion. A controlled delayed-recognizer test reproduced a dropped word.
- Recognition diagnostic on 100 ideal generated paths: median 20.3 ms, p95 39.7 ms; 99 top-1 and 100 top-3. These are **synthetic-path results**, not human accuracy, release-to-insertion latency, or proof of typing speed.
- Not re-qualified here: real cross-application focus behavior on every supported application, clean Windows without Python, real-user recognition accuracy, browser frame-rate profiles, or all mixed-DPI combinations. The plan supplies specific checks for these gaps.

### Existing strengths to retain

Offline recognition; shared letter coordinates; foreground-window dispatch guard; candidate ownership checks; finally-released modifiers; atomic validated settings; fixed candidate strip; same-space number switching; matching icon style; portable packaging; functioning GitHub/Vercel deployment.

## 2. Findings, prioritized

P1 means fix before advertising a more dependable desktop release. P2 means the next improvement batch. P3 means polish or maintenance. Some issues below can affect text, but this review is not a security certification or legal compliance verdict.

| ID | Priority | Finding / reproducible scenario | Evidence at review baseline |
| --- | --- | --- | --- |
| A01 | P1 | After a swipe adds a space, move to another caret/field and click punctuation. The code can send Backspace at the new position, deleting unrelated text. | `src/desktop_app.py:184`, `:244`; `src/text_model.py:23`. Owner is cleared before punctuation dispatch, and auto-space removal does not verify the target. |
| A02 | P1 | Submit a word then immediately click punctuation or swipe another word while recognition is pending. The previous word is silently discarded by generation invalidation. Controlled test: pending “hello” + period became just `.`. | `src/practice.py:246`, `:275`; `src/desktop_app.py:278`; `src/ui/Desktop.qml:110`. |
| A03 | P1 | `Shift+1` produces `1`; `Shift+;` produces `;`. Shortcut punctuation uses character code points as virtual keys: Ctrl+[ can emit the Windows key, Ctrl+/ Help, Ctrl+, PrintScreen. | `src/desktop_app.py:244`; `src/desktop.py:151`. Fake output/API tests confirmed this; no live shortcuts were sent. |
| A04 | P1 | If a stroke has no origin accessibility snapshot, a later snapshot from another field can be accepted; no original field identity exists to compare. | `src/desktop_app.py:280–294`, `:318`. Safe fake snapshots reproduced delayed insertion into identity `(2)` after an unknown origin. |
| A05 | P1 | UI Automation calls block the UI caller for up to 250 ms; timed-out calls remain in a one-worker queue. Full document values/prefixes are read before truncation. | `src/accessibility.py:51–54`, `:92–109`; callers include show, stroke, receive, alternative, Undo in `desktop_app.py`. |
| A06 | P2 | Number/symbol mode hides the board that contains Backspace, Enter, Shift, and Esc, leaving ordinary number correction/submission awkward. | `src/ui/Desktop.qml:73`, `:115–145`. |
| A07 | P2 | Password status is sampled at summon; context can change within the same top-level window. Exact clicks still update the shared local editor. Hide/cancel does not immediately clear its text/auto-space. | `src/desktop_app.py:244–247`, `:413–423`, `:505–538`; `src/accessibility.py:37–47`. |
| A08 | P2 | No calibrated “no match” result: even implausible/unknown paths receive candidate words. Ideal `desmos` returned `demos, dennis, denis`; `mousyst` returned `most, moist, midget`. Repeated-letter words intentionally share shapes. | `src/word_recognizer.py:33–65`. |
| A09 | P2 | No global physical Escape handler reaches the nonactivating keyboard, despite the docs promising physical Escape cancellation. | `src/ui/Desktop.qml`; `src/desktop_app.py:230`; website typing guide. On-screen Esc exists in letters mode. |
| A10 | P2 | Window height is limited but width is not fitted to available monitor space. Large/full layouts and narrow/high-scale screens need qualification. | `src/ui/Desktop.qml:13–14`; screen clamp in `src/desktop_app.py:520–534`. |
| A11 | P2 | Failed Undo still changes the local model, and a partially failed replacement can leave ownership misleading. | `src/desktop_app.py:373–380` ignores the dispatch result before `editor.undo()`. |
| A12 | P2/P3 | The production host inherits practice task/participant/measurement state, which couples new product functions to an unrelated experiment controller. | `src/desktop_app.py:32`; `src/practice.py:52–80`. |
| W01 | P1 | At small widths a global rule hides the first child of every navigation. It also hides “Getting started” in the docs sidebar. | `website/src/layouts/Shell.astro:16`; confirmed on live mobile docs. |
| W02 | P1 | Reduced-motion mode selects only instruction scene 2 and hides the other three. Users lose the summon/swipe/correction explanations. | `website/src/scripts/scroll-story.ts:89–98`. |
| W03 | P1 | Hero action links become fully transparent but remain focusable and clickable. Storage failure can abort reveal initialization. JS failure leaves some content offscreen/hidden. | `website/src/scripts/chapters.ts:23`; `website/src/layouts/Shell.astro:8–16`; feature positioning in `website/src/pages/index.astro`. Live: opacity 0, link tabIndex 0. |
| W04 | P2 | Chinese hero text breaks inside 鍵盤; bilingual copy is switched client-side, while titles/metadata remain English. Language is not represented in shared URLs. | Live mobile: computed hero font 65 px; `Shell.astro:4,8–10`; competing hero rules in `index.astro`. |
| W05 | P2 | Guide search filters titles only. Searching “Space” returns no results although the guides explain Spacebar scrubbing. Docs lack annotated screenshots and a complete settings/error reference. | `website/src/pages/docs/[...slug].astro:3–42`; confirmed live. |
| W06 | P2 | Both scroll controllers update all chapters, including offscreen ones; key geometry is repeatedly read during SVG writes. Frame-rate impact has not yet been measured. | `website/src/scripts/chapters.ts:19–67`; `scroll-story.ts:42–70,84–115`. |
| W07 | P2 | Long mobile story lacks chapter navigation or a visible short route once the first hero fades. | Live mobile page 12,836 px at 844 px viewport (~15.2 screen heights), no skip link; chapter nav hidden below 1,100 px. Keep the story, add navigation. |
| R01 | P2 | Preview tags are accepted but not explicitly marked prerelease; reruns can overwrite published ZIPs/checksums. No embedded app version/About exists. | `.github/workflows/windows-release.yml:60,105–107`; app host. |
| R02 | P2 | The shipped notice inventory does not include the distinct wordfreq source/data notices referred to by attribution. No root application reuse license is selected. | `src/data/ATTRIBUTION.md:11`; `tools/build_vocabulary.py:20`; `build-preview.ps1:17`. Inventory finding, not a legal determination. |
| R03 | P2 | Offscreen packaged tests run on the same Python-equipped build runner. They do not establish no-Python installation or desktop focus compatibility. | `.github/workflows/windows-release.yml:28–50`; `EXPERIMENT.md:78`. |
| R04 | P2/P3 | No website type/link/accessibility CI; website-only commits rebuild the Windows app. Practice docs describe obsolete main-branch milestones. | `.github/workflows/windows-release.yml:3–9`; `website/package.json`; `EXPERIMENT.md:4,79`. |

## 3. Delivery rules and architecture

- Keep the letters, essential controls and suggestion strip stationary while typing. New shelves replace a panel or use reserved space; they must not unexpectedly move Enter or change the window size.
- Keep middle-click as the default activation. Auto-pop remains removed. Background field validation must never show or hide the keyboard by itself except to stop an invalid session safely.
- Keep inference local. No cloud LLM, automatic clipboard history, hidden text logging, or silent dictionary learning.
- Distinguish observed defects from proposed features and performance targets. A passing build is not proof of cross-app compatibility or human accuracy.
- Deliver small pull requests with the acceptance checks listed below. Work on `codex/` branches and use Vercel previews before production site changes.
- Do not make a language rewrite a prerequisite. First measure idle, visible, typing, and stalled-accessibility states.

### Proposed modules

| New or extracted module | Responsibility |
| --- | --- |
| `src/input_session.py` | Session identity, field/window binding, sensitive/unknown state, owned insertion range, external invalidation. |
| `src/input_actions.py` | Typed text, swipe, chord, navigation, snippet and replacement action records with immutable submission state. |
| `src/input_queue.py` | Ordered input transactions and bounded asynchronous recognition. |
| `src/keymap.py` | Display labels, printable characters, named keys, shifted symbols, layout-aware shortcut mapping. |
| `src/edit_service.py` | Owned space removal, candidate replacement, Undo, native edit commands. |
| `src/user_content.py` | Validated local snippets, shortcut favorites and personal words; explicit persistence. |
| `src/ui/components/` | Reusable Key, SuggestionBar, ControlRow, Shelf, StatusNotice, dialog components. |
| `website/src/scripts/motion/` | One scheduler, geometry cache and typed chapter timelines. |
| `website/src/content/docs/{en,zh-TW}/` | Versioned localized guides, separate from rendering. |

Extract along with the bug fixes that need the boundary; avoid a large behavior-changing rewrite first.

## 4. Batch A — dependable desktop input

### A-1: Centralize target ownership and safe edits (A01, A04, A07)

**Changes**

1. Introduce an `InputSession` with ID, target HWND, field identity if known, observation timestamp, sensitive-state enum (`normal/password/unknown`), and optional owned span.
2. Route punctuation auto-space removal, alternatives and Undo through a single `EditService`. Clear ownership only after the decision, not at the beginning of every key action.
3. Before any deletion/replacement, verify field identity, selection/caret and expected owned suffix. If ownership is absent/stale, invalidate it and insert punctuation normally without a preceding Backspace.
4. Capture stroke origin at submission. Never manufacture an origin from a later result-time snapshot. If origin cannot be verified, offer exact-click compatibility mode with replacement/prediction disabled; do not silently insert a delayed guess into a newly discovered field.
5. In known password fields, send exact clicks without appending plaintext to the local echo/editor/history. Clear transient text, candidates, auto-space and pending work on session end, field change or transition to sensitive/unknown state.
6. On dispatch failure/partial output, clear ownership and stop the remaining action. Report uncertainty; do not attempt blind external rollback with Backspaces.
7. Return an explicit output outcome (`success`, `blocked`, `partially_applied`) from dispatch. Commit local Undo only on success; partial outcomes invalidate local text ownership and show a recovery notice. Clear sensitive text in memory rather than merely hiding it; this finding does not mean it was saved to disk.

**Acceptance**

- Given swipe `hello `, when the caret moves or a different field in the same window is selected before period, then no unrelated character is deleted.
- Given an unknown stroke origin and a subsequently discovered different field, when the result returns, then the result is discarded with an explanation.
- Given a password/unknown field, when exact keys are clicked, then no local prediction buffer, snippet history or vocabulary learner receives those characters.
- Fake-target tests cover changed HWND, same-HWND/different-field, changed selection, missing UIA, and partial send failure. Real disposable control tests cover the same supported cases.
- A failed Undo must not report success or leave usable candidate ownership; a failure after the Nth deletion must not trigger a blind rollback.

### A-2: Preserve rapid actions with an ordered queue (A02)

**Changes**

1. Add monotonically numbered input actions capturing session ID, case/modifier state and recognition input at submission.
2. Recognize off the UI thread and commit in action order. Later internal typing must not invalidate earlier submitted input; external target/caret changes cancel the session's pending actions.
3. Start with one recognition in flight and a bounded queue of eight pending actions. If full, reject the new action visibly; never silently drop an old word. Expose a small pending indicator in existing reserved space.
4. When there is no confident match, pause dependent actions and show `Spell word` / `Cancel pending entry`. Preserve later queued punctuation until the user resolves or explicitly cancels that transaction.
5. Make hide, cancellation, reset and sensitive-field transition flush pending work. Late callbacks must be harmless.

**Acceptance**

- With a 200 ms fake recognizer: swipe `hello`, then `world` → `hello world ` exactly once, in order.
- Swipe `hello`, immediately period → `hello.`; immediately Backspace → behavior matches sequential completion then one Backspace.
- Capture Shift at submission; toggling Shift later cannot alter an earlier queued word.
- Run 50 delayed/mixed action sequences and timeout/error cases with no silent loss, duplication or cross-session commit.

### A-3: Correct key semantics (A03)

**Changes**

1. Separate `insert_text(character)` from `send_chord(physical/named key, modifiers)`; no `ord(punctuation)` shortcut fallback.
2. Use the foreground target's keyboard layout and a proper virtual-key/shift-state mapping for printable shortcut keys. Reject unrepresentable keys explicitly. Keep numpad keys distinct from top-row digits.
3. Define US-English displayed Shift symbols (`1→!`, `;→:`, `/→?`, etc.) in the shared key map. Render the character that will be inserted.
4. Handle extended-key flags for navigation/numpad as appropriate; send a chord's down/up sequence as a bounded batch, with cleanup for any injected modifiers.

**Acceptance**

- Shift+1/;/slash insert `!`, `:`, `?`; Ctrl+[ uses the bracket virtual key, not Win; Ctrl+/ and Ctrl+, do not emit Help/PrintScreen.
- Assert event packets for punctuation, Shift+arrows, Ctrl+Backspace, F-keys and numpad; test US and one non-US target layout.
- All injected keys are released after success, cancellation or simulated API failure. Unsupported mappings produce a visible error.

### A-4: Make accessibility and cancellation responsive (A05, A09)

**Changes**

1. Replace GUI-thread `.result(timeout=.25)` with asynchronous requests carrying session/action IDs. Cache a bounded snapshot and perform validation without blocking the pointer UI.
2. Allow one UIA request in flight and one newest pending request; drop superseded requests. A stalled provider must not create an unbounded executor backlog. Evaluate an isolated worker process if COM calls cannot be interrupted reliably; do not claim thread cancellation stops a running COM call.
3. Read only the bounded context needed for validation, preferably using cloned text ranges, rather than extracting entire document text and slicing afterward. Define Python-character/UTF-16 offsets explicitly and test emoji/surrogate pairs and long native Edit selections.
4. Correct the Escape docs immediately. Add an actual session-scoped physical-Escape cancellation mechanism that is active only while the overlay/pending input is active; decide and document whether Escape is consumed in that state. Pass it through when Mousyst is inactive. Preserve middle-click and visible cancellation as independent fallbacks.
5. Expand the existing status notice: distinguish unavailable field metadata, changed target, held physical modifier, blocked OS input and recognition failure. Never recommend elevation as a blanket solution.

**Acceptance**

- A deliberately stalled accessibility provider does not freeze animation, pointer tracking, middle-click cancellation or tray Quit; UI acknowledgement target below 50 ms on the development machine, measured separately from validation completion.
- Provider timeouts do not accumulate arbitrary queued calls; a worker failure invalidates the session and recovers on a fresh request.
- Physical Escape cancels a stroke/pending result exactly once; inactive Escape reaches the target normally. Update docs only after packaged verification.

### A-5: Essential controls and screen fit (A06, A10)

**Changes**

1. Extract Backspace, Enter, Shift and Cancel into persistent control positions shared by letters, symbols and numpad. Preserve the reserved suggestion bar and in-place layer switch.
2. Compute an effective display scale from monitor work-area width and height. Keep the user's requested size separately; explain temporary fitting. Do not resize mid-stroke.
3. Clamp settings and keyboard windows to the selected monitor; handle negative coordinates, work-area/taskbar changes and monitor disconnects.
4. Keep the selected candidate index/wheel accumulator tied to the current owned word, clearing them on a new transaction or field change. Process high-resolution wheel deltas without accidental multi-replacement.

**Acceptance**

- In numpad mode, enter `123`, Backspace, `4`, Enter without switching to ABC.
- Full layout at 65–160% on 1366×768, 1920×1080 and a scaled narrow work area remains fully reachable; 100/150/200% DPI, negative monitor origin and disconnect cases are recorded.
- Layer switches do not move the persistent controls or suggestion strip. A new word starts at candidate zero regardless of the previous word's correction.

## 5. Batch B — everyday program features

These are proposed additions, prioritized for the user's chosen direction. A-1/A-2/A-3 are dependencies for features that dispatch text or shortcuts. All additions use normal settings controls and optional import/export, not an exposed JSON editor.

| Feature | Concrete behavior and implementation | Acceptance / dependencies |
| --- | --- | --- |
| **B-1 Editing shelf** | Add a fixed-size `Edit` shelf with Copy, Cut, Paste, Select All, Undo, Redo, previous/next word, select previous/next character, and delete previous word. Use ordinary target-app chords via `EditService`; do not mirror the clipboard into Mousyst. Keep app Undo distinct from “Undo Mousyst word.” | A-1/A-3. In disposable Edit/browser controls, select a word, copy/paste, undo/redo and delete a word entirely by mouse. Each command checks the session and explains unavailable behavior. Shelf preserves window/control geometry. |
| **B-2 Favorite shortcuts** | Add Settings → Shortcuts: create/rename/reorder/delete up to 12 tiles, choose modifiers and a key using controls, show the chord on every tile. Ship editable Copy/Paste/Undo/Screenshot examples. Validate against the key map; no arbitrary scripts or executable launch in this first version. | A-3, B-1 shelf. Ctrl+C/V and Win+Shift+S dispatch exactly one chord per click; invalid key combinations cannot be saved; import/export round-trip. OS reserved shortcuts may fail and must not claim universal support. |
| **B-3 Saved phrases** | Add Settings → Phrases and a `Phrases` shelf. Explicit user-authored label/text/category, search, pin/reorder/delete, up to 100 entries and 2,000 characters each. Store versioned atomic `phrases.json` under APPDATA. Preserve multiline/Unicode; render newlines as intended native line-break actions. Insert through the ordered text service; no clipboard-history watcher or automatic capture. Editing the phrase dialog must not overwrite the remembered destination. | A-1/A-2, B-1. Create a phrase, restart, search and insert it once into a selected target. Confirm no output when target changes during insertion; stop remaining chunks on failure. No snippet preview/insertion in password mode by default. Import has schema/size limits and preserves previous valid data on failure. |
| **B-4 Personal dictionary** | Add Settings → Words: explicitly add/edit/delete spellings and case; optional import/export. Validate alphabetic English words initially, limit length/count, create normalized templates through existing geometry. Merge a bounded personal-word bonus into geometric ranking. No automatic learning. Treat contractions/hyphenated tokens as an explicit follow-on tokenizer task. | After recognition evaluation in C-1. Add `Mousyst`, swipe its path and see it among candidates; restart retains it; delete removes its personal boost/template. Password/unknown sessions cannot add words. |
| **B-5 Activation and positioning** | Default stays middle-click. Add capture-and-test controls for an alternate mouse side-button or supported keyboard hotkey; validate conflicts and offer a tray recovery path. Add tray Pause/Resume interception and per-app exclusions. Position modes: near pointer, remembered per monitor, docked bottom. Reposition only on summon or explicit drag. | A-4/A-5. Unassigned buttons pass through; Pause restores ordinary middle-click; invalid hotkey leaves old binding intact; exclusions never swallow the mouse button. Never intercept a side-button by default. No auto-pop. |
| **B-6 Case and word selection** | Keep single-click Shift as one-shot; add explicit Caps Lock/double-click Shift with a distinct locked indicator and predictable reset. Add hold-and-drag selection mode on Space as an optional setting (plain horizontal scrubbing remains default), or use Edit shelf selection controls first. | A-3/B-1. One-shot, locked, shortcut and queued-word case states have separate tests; Shift lock does not accidentally apply to a future Ctrl command. Selection direction/release outside the keyboard cancels reliably. |
| **B-7 Math/symbol favorites** | Add a searchable symbol shelf with everyday punctuation and a small math set. Offer `Plain text` forms such as `<=`, `>=`, `sqrt()` separately from Unicode `≤`, `≥`, `√`; label them clearly for tools such as Desmos. Allow pinning favorites and inserting paired brackets with an explicit caret-placement action. | A-1/A-2/A-3, B-1. Each mode inserts exactly the displayed output; paired insertion validates the same session before moving the caret. Changing symbol mode replaces content within the panel. No claim that every Unicode symbol is valid syntax in every app. |
| **B-8 Per-app profiles** | Explicit profiles keyed by executable identity: layout, size, position, number format and favorite shelf. No window-title/browser-URL/text capture. Provide Default, Duplicate, Delete and Reset controls. Apply at session start; postpone changes until a stroke/queue is finished or canceled. | B-5 plus stable settings schema. Switching between two known apps applies the right profile; an unknown app uses Default; deleting a profile restores Default. App updates do not create unbounded duplicate profiles. |
| **B-9 About, startup and update notice** | Add version/build, shortcuts/help, license inventory and diagnostic export to About. Provide an optional user-scoped Start with Windows toggle; only remove the startup item created by Mousyst. Manual `Check for updates` reads release metadata and opens a verified release link; no silent executable replacement. Diagnostics are aggregate/error codes by default, no raw text/clipboard/path recording. | R-1/R-2. Installed version matches tag/ZIP/About; offline update check fails cleanly; startup toggle round-trips; export preview shows what will be shared and only exports on request. |

**Recommended feature order:** B-1 → B-2 → B-3 → B-4 → B-5. B-6/B-7 can follow once the shared services are stable. B-8 is lower priority than a dependable default profile. B-9 version/About should ship earlier with release hardening; startup/update conveniences can follow.

## 6. Batch C — recognition quality with evidence

### C-1: Build a useful evaluation set first

- Extend `tools/evaluate_swipes.py` to validate schema and report labelled/unlabelled/malformed totals, top-1/top-3, rejection and false-insertion rates, per-word failures, sample density, repeated-letter categories, and cold/warm/end-to-end timing.
- Save fixtures with anonymous session/participant IDs, expected word, normalized points, duration, intended outcome and vocabulary version. Split tuning and held-out evaluation by session/participant; keep human strokes separate from ideal paths.
- Include fast sparse paths, jitter, repeated letters, misspellings, names, unknown words, wrong endpoints, accidental scribbles and canceled gestures. Collect recordings only with explicit consent; do not add recording to ordinary production use.
- Correct the old practice comparison's editing asymmetry, or label it an interaction pilot. No mandatory return to a practice-only product milestone.
- Acceptance: malformed/unlabelled samples cannot silently improve reported accuracy; report individual failures and preserve unsuccessful tasks. Save the baseline before tuning.

### C-2: Confidence and exact-input fallback

- Return a typed `RecognitionResult`: candidate words, shape scores, margin, confidence state, vocabulary version and timings. Separate ambiguous valid paths from implausible/no-match paths.
- Calibrate a no-match threshold on C-1 data. For rejected paths, show `No confident match — click to spell`; do not insert the nearest arbitrary word. For ambiguous valid paths, keep three stable alternatives.
- Measure release→commit latency including queueing, UIA validation and actual dispatch. Proposed warm p95 goal: <100 ms on a named development machine; report cold start separately. Keep tests at 200 ms simulated latency to verify correctness independent of speed.
- Repeated letters cannot be uniquely inferred from identical paths. Try a small optional offline previous-word prior only after baseline evaluation, retaining geometric ranking and click entry. Disable context on sensitive/unknown sessions.
- Acceptance: fewer false insertions on the invalid set; no regression in overall held-out top-3 accuracy beyond an explicitly reviewed tolerance; report ambiguous-set changes separately.

## 7. Batch W — improve the website without losing its character

### W-1: Reliable content and navigation (W01–W04, W07)

1. Scope mobile header selectors to `header nav`; restore the first docs link. Add current-page state to docs navigation.
2. Add a visible `Skip story / Download` control available throughout the mobile narrative and a keyboard skip-to-main link. Keep full scroll storytelling as the normal experience. Add an optional compact overview; do not force a complete story replay for returning download visitors.
3. Render all instructions/features in ordinary semantic document flow by default. Only enable pinning/hidden scenes after a `data-motion-ready` handshake from initialized controllers.
4. Reduced-motion mode shows all four steps, in order, with static illustrations. A user preference change updates the mode without a full reload or lost location.
5. Set `inert` on fully hidden CTA groups; restore it on reverse scroll. Keep at least one visible download route. Avoid moving focused elements into hidden scenes.
6. Wrap optional storage access; memory fallback must not prevent language switching or content display. Test JS disabled and module failure.
7. Consolidate competing CSS overrides and use Chinese-specific heading size/line breaking. Keep words such as 鍵盤 together. Check 320/390/768/1440 widths, 844×390 landscape, 200% zoom and short laptop heights.

Acceptance: mobile “Getting started” is visible; no invisible Tab targets; all four instructions/features readable with reduced motion/JS disabled; direct downloads/docs remain reachable; no unintended horizontal overflow or cropped controls at the stated sizes.

### W-2: One measured motion system (W06)

- Extract one `ScrollDirector` and a typed chapter configuration for duration and entrance/hold/exit ranges. Retain intro montage, interruption cards, solution typography, exact swipe demo, feature cards and finale.
- Cache selectors, chapter bounds and local key centers in a measure pass. Recompute on resize, font readiness or content changes. Reuse the shared geometry for the SVG trail; do not read key offsets inside each frame.
- Use IntersectionObserver to activate only the current chapter and adjacent chapter. Split reads from writes; skip unchanged output. Stop updating the hidden hero illustration and inactive finale tiles.
- Add timeline sample tests at chapter boundaries, forward/reverse scroll and responsive changes. Check keyboard pointer at each W/O/R/L/D center.
- Performance acceptance is a target to measure: on a named desktop, p95 controller work <8 ms; trace contains no repeated layout-read/write chain caused by the controllers. Test one real mid-range phone for dropped frames. Reduce decoration before shortening readable holds.

### W-3: First-class bilingual docs and search (W04–W05)

- Generate `/en/` and `/zh-TW/` pages from locale dictionaries and Astro content collections. Redirect existing `/docs/...` links to English equivalents; keep old section links valid where possible. Make `/` a deliberate default entry rather than relying on stored text replacement.
- Switch to the equivalent page and section. Server-render language, title, description, accessible names, placeholders and empty states. Add canonical/hreflang, sitemap, robots, social preview and an accessible 404.
- Split each guide into Markdown/MDX with locale, translated route key, supported app version and last-reviewed date. Add full-text static search with snippets and heading links, result counts and keyboard traversal.
- Add annotated current screenshots for extraction/tray/settings; a settings table with defaults/ranges; target-app compatibility table; exact status-message→recovery instructions; copyable build commands.
- Acceptance: fresh direct Chinese URL works without JS; changing language preserves topic/section; searching `Space`, `repeat delay`, `password`, `游標` and `重複` finds relevant content. No missing locale keys/links in CI.

### W-4: Download handoff, evidence and visual consistency

- Generate a release manifest with version, stable ZIP URL, byte size, checksum URL and release-notes URL. Read release metadata at build time with a checked-in fallback; do not call GitHub on every visitor scroll/page load. Rebuild the site when a stable app release is published.
- Primary Download goes to the correct Windows ZIP, with a secondary GitHub Releases link and concise “extract the whole folder, retain _internal” instructions. Detect non-Windows only to explain compatibility, not block downloads.
- Add actual app screenshots and a captioned one-minute recording. Publish genuine feedback/results only; mark the illustrated keyboard as an illustration. Keep browser typing demo as a separate pending decision for the homework requirement.
- Use one set of design tokens and a deterministic vector M/icon set across site/app. Final logo remains a later design decision. Self-host licensed font files with a subset/weight plan; remeasure key geometry after fonts load.
- Scope the color preview to the preview keyboard, or relabel it as a site-theme control. If layout/size previews are offered, display the real supported options and keep them explicitly separate from desktop settings.
- Acceptance: ZIP metadata agrees with the released build; offline metadata fallback leaves downloads usable; video has captions/poster/text summary; preview selection never suggests it changed the installed app.

## 8. Batch R — release and maintenance

### R-1 Versioning and immutable releases

- Generate one version/build record from the release tag; embed it in EXE resources, About, diagnostics and release metadata.
- Explicitly mark hyphenated versions prerelease and prevent them becoming stable Latest. Do not overwrite an existing published ZIP/checksum on routine reruns. If a same-tag rebuild differs, fail and publish a new version instead.
- Keep ZIP plus checksum, add changelog highlights and known limitations tied to a specific build. Preserve a fallback to previous stable download.
- Acceptance: preview tags never change the stable download; rerun checksum mismatch is caught; app/ZIP/tag/docs manifest agree.

### R-2 Notices, provenance and licensing decisions

- Inventory exact shipped dependencies, including Qt/PySide, numpy, comtypes, vocabulary and fonts. Include third-party notices in the extracted ZIP and About → Licenses.
- Fix vocabulary generation so its source/version/hash/derivation and applicable code/data notices are reproducible; do not assume wheel dist-info contains all source notices.
- Ask the project owner to select the application source reuse license before adding one. A public repository does not itself settle the intended reuse terms.
- Acceptance: packaging checks verify all declared notice files exist in the final ZIP. This task establishes an inventory; obtain qualified advice if license interpretation is uncertain.

### R-3 Verification that matches the product promise

- Keep fast unit/offscreen checks. Add fake-output session/queue/keymap tests for A-1 through A-4 and a disposable-native-control integration job or release qualification run; never inject into unrelated real user documents.
- Qualify one clean Windows x64 VM without Python, networking disabled: extract/run, tray show/hide, exact input/swipe/correction, Quit/restart, settings persistence, version display and folder removal. Record build checksum and OS/display scale.
- Maintain a small compatibility matrix: Notepad, browser input, browser textarea/contenteditable, Office if available, VS Code/Monaco, password field, read-only field and an elevated target. Record `verified`, `limited`, `blocked`, `untested`; do not imply unsupported apps are fixed by raising permissions.
- Profile hidden/visible/typing/stalled-provider memory, CPU, cold-start and latency. Set budgets after the current baseline; no speculative rewrite or memory promise based on old metrics.

### R-4 Separate CI and update documentation

- Website checks: `npm ci`, Astro/type check, static link/content/locale validation, focused browser smoke, keyboard/reduced-motion/responsive checks. Use paths for website-only changes.
- App checks: Python lint/tests, isolated QML checks, packaging and release qualification. Website-only pushes skip app packaging; every version tag still runs full app checks.
- Mark EXPERIMENT.md as historical/practice-only and remove incorrect statements about main and future desktop integration. Keep one current capability/status table driving docs and release notes.
- Acceptance: a broken locale route or unsupported documented shortcut fails before deployment; a website-only change runs web checks without rebuilding Qt; version-tag publishing still requires the full desktop build.

### R-5 Incremental host separation (A12)

- Extract only the shared recognition, key geometry, editing and queued-action services from `practice.Controller`. Have separate `DesktopController` and `PracticeController` hosts compose them.
- Keep task presentation, participants, stroke recording and research exports in the practice host. Keep OS hooks, target validation, tray and settings in the desktop host.
- Acceptance: the desktop host no longer initializes trials, participant/result collections or recording state; all desktop regression checks and existing practice tests still pass. This cleanup can accompany service extraction and must not delay A-1's text-safety fix.

## 9. Dependency order and first pull requests

| Order | Suggested branch / work item | Deliverable | Must pass before next dependent work |
| --- | --- | --- | --- |
| 1 | `codex/input-ownership` | A-1, regression tests, truthful Escape documentation | No stale-space deletion or unknown-origin delayed commit. |
| 2 | `codex/ordered-input` | A-2 plus session-safe asynchronous verification from A-4 | Delayed mixed-action sequences preserve order and cancel safely. |
| 3 | `codex/keymap-controls` | A-3, persistent controls and initial screen fit from A-5 | Correct symbol/chord packets, usable numeric editing. |
| 4 | `codex/website-access` | W-1 and website CI foundation | Mobile docs link, static/reduced-motion paths, focus navigation. Can run alongside app work. |
| 5 | `codex/edit-shortcut-shelf` | B-1, B-2 | Real disposable edit flows and no geometry jumps. |
| 6 | `codex/phrases` | B-3 | Atomic persistence, explicit content insertion, target-change failure cases. |
| 7 | `codex/recognition-evidence` | C-1 then C-2, B-4 | Baseline held-out report and dictionary tests. |
| 8 | `codex/motion-docs` | W-2, W-3, W-4 | Measured animation traces, bilingual full-text docs and correct download manifest. |
| 9 | `codex/desktop-convenience` | B-5/B-6/B-7; B-8 only after stable defaults | Activation recovery, Caps behavior, math output, profile fallback. |
| 10 | `codex/release-quality` | R-1–R-4, B-9 | Clean-VM/package checks, version/notices, immutable stable release. Version/About/notices can be pulled forward. |

This is the sequence of reviewable changes, not a promise of a specific number of hours or a same-day release. Keep each batch shippable; do not hold a critical text-safety fix until all optional functions are ready.

## 10. Decisions intentionally left open

1. Browser typing demo for homework: user previously chose to decide later. A showcase illustration is not evidence that the report's interactive-browser requirement is satisfied. Confirm teacher acceptance or scope a separately labelled demo later.
2. Application reuse license: maintainer chooses; do not silently select it.
3. Chinese text composition: localizing settings/help is a reasonable future task; Chinese IME composition is a separate technical investigation, not another English word list.
4. Clipboard history, cloud prediction, auto-pop, silent learning and self-updating EXEs: outside the recommended first expansion. Saved phrases and native paste offer useful convenience without introducing these systems.

## 11. Technical references checked

- [Microsoft VkKeyScanExW](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-vkkeyscanexw): character-to-virtual-key and modifier mapping depends on the keyboard layout.
- [Microsoft SendInput](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendinput): inserted-event counts, current modifier state and integrity-level restrictions matter to dispatch/error handling.
- [Astro internationalization routing](https://docs.astro.build/en/guides/internationalization/): locale routes and equivalent-page navigation.
- [wordfreq source and data license explanation](https://github.com/rspeer/wordfreq#license), [Qt for Python license inventory](https://doc.qt.io/qtforpython-6/licenses.html): inputs to a proper shipped-notice inventory; no broad legal compliance conclusion is made here.
