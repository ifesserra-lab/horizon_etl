# Research: Weekly CI Workflow Validation and Export Compression

## Decision 1: Chrome/Chromedriver for Lattes in CI

**Decision**: Install `chromium-browser` + `chromium-driver` from apt on ubuntu-latest; set `CHROME_BINARY=/usr/bin/chromium-browser` and `CHROMEDRIVER_PATH=/usr/bin/chromedriver`.

**Rationale**: Playwright does NOT bundle chromedriver — it uses its own CDP protocol internally. Selenium (used by scriptLattes) requires a standalone chromedriver binary. The `chromium-browser` + `chromium-driver` apt packages are an auto-versioned pair (guaranteed version-match), identical to the Dockerfile approach. They are available on ubuntu-latest without extra configuration. Installing them takes ~5s and eliminates any version mismatch between browser and driver.

**Alternatives considered**:
- Reuse Playwright Chromium binary path: Playwright stores Chromium at `~/.cache/ms-playwright/chromium-<rev>/chrome-linux/chrome` but there is no bundled chromedriver. Path is runtime-dependent.
- `webdriver-manager` pip package: Downloads chromedriver at runtime matching installed Chrome; adds network dependency and pip install step.
- `browser-actions/setup-chrome` GitHub Action: Manages Chrome + matching chromedriver; works but adds an external Action dependency for what apt handles natively.

## Decision 2: Export File Compression Approach

**Decision**: `find data/ -type f -size +10M -exec sh -c 'for f; do zip -m -j "$f.zip" "$f"; done' sh {} +`

**Rationale**: `find -size +10M` targets files strictly over 10 MB (matches spec threshold). `zip -m` moves the original into the archive (deletes source after compression). `-j` strips directory paths so the archive extracts cleanly. Running in a `sh -c` loop batches multiple matches without spawning one `zip` process per file. No extra tooling needed — `zip` is pre-installed on ubuntu-latest.

**Alternatives considered**:
- `gzip` per-file: Produces `.gz` not `.zip`; less portable for Windows consumers downloading artifacts.
- `actions/upload-artifact` built-in compression: v4 compresses the full artifact but doesn't reduce per-file threshold control.
- GNU parallel: Faster for many large files but requires `parallel` installed; overkill for ~1-3 files over 10 MB.

## Decision 3: Artifact Retention Period

**Decision**: 30 days via `retention-days: 30` on `actions/upload-artifact@v4`.

**Rationale**: Weekly schedule = 4 runs/month. 30 days covers the last 4 runs with room for debugging. GitHub default (90 days) would retain 12+ runs, wasting storage. 7 days risks losing the previous run before the next completes.

**Alternatives considered**:
- 90 days (default): Retains ~13 runs; excessive for a dataset refreshed weekly.
- 7 days: Too short; if a run fails on Saturday and is only noticed Monday, the prior artifact is already gone.

## Decision 4: `permissions: actions: write`

**Decision**: Add `actions: write` to the workflow-level permissions block alongside `contents: read`.

**Rationale**: GitHub's fine-grained token model sets any unspecified permission to `none` when a `permissions:` block exists. `actions/upload-artifact@v4` requires `actions: write` to create artifact entries in the Actions API. Without it, upload silently fails on repos with fine-grained token enforcement.

**Alternatives considered**:
- Remove `permissions:` block entirely: Reverts to permissive defaults; against security best-practice of minimal privilege.
- Add only at job level: Equivalent; workflow-level is cleaner and applies to all future jobs.

## Decision 5: Playwright Chromium for SigPesq (unchanged)

**Decision**: Keep the existing `playwright install --with-deps chromium` step. SigPesq uses Playwright's own browser API (not Selenium/chromedriver) — no changes needed.

**Rationale**: `agent_sigpesq` calls Playwright's async API directly. Playwright manages its own browser instance completely separately from Selenium. The two tools share the system chromium only if `CHROME_BINARY` points to the same binary, but they use different driver protocols and do not conflict when run sequentially.
