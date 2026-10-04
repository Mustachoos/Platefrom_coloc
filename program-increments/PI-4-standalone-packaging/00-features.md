# PI-4: Standalone packaging (PartyBooth desktop app)

Goal: a non-technical user can install PartyBooth and run it autonomously, without a terminal
and without help. Packaging already exists (PyInstaller via `packaging/launcher.py` +
`launcher.spec`, installers built by `.github/workflows/release.yml`: Windows Inno Setup,
macOS `.dmg`, Linux AppImage; SQLite + per-user data dir when `IS_FROZEN`). This PI closes the
remaining gaps. Roadmap ordered by how much each gap hurts a non-technical user.

Not a PWA / Electron / Tauri: PartyBooth is a Django server that guests' phones reach over the
local network, so a service worker can't replace the backend and a wrapper adds weight for no
gain. A manifest-only PWA ("add to home screen" icon for guests) stays an optional extra.

## Feature A — Launcher and tray (first, no external accounts needed)

**Problem.** The packaged app is a console window (`console=True`): closing the terminal stops
the server, and there is no Quit button or visible state. Port 8000 is hard-coded, so if it's
taken the app just fails.

**Scope.**
- Windowed build (no console) with a tray / menu-bar icon: Open PartyBooth, show the guest URL
  (and QR), Quit.
- Free-port fallback when 8000 is taken, with a clear message instead of a crash. The chosen
  port must flow into the upload QR / `server_host` logic.
- Explain the OS firewall prompt on first launch (guests' phones need inbound access; the
  server binds `0.0.0.0`).
- Surface fatal startup errors in a dialog or log file the user can find, since there is no
  console any more.

## Feature B — Signed and notarized builds

**Problem.** Unsigned builds are blocked by macOS Gatekeeper and warned about by Windows
SmartScreen. Biggest adoption barrier.

**Scope.**
- macOS: sign + notarize in CI (needs an Apple Developer account, ~99 EUR/year — user must buy).
- Windows: code-signing certificate (optional, paid).
- Until then: document the right-click > Open workaround in the README.

## Feature C — Clean-machine testing on all three OSes

**Problem.** Only the macOS `.dmg` (v0.2.0) is in `releases/`; Windows and Linux installers
have not been verified end to end.

**Scope.** Run the CI build on all three OSes, install on clean machines (no Python, no
Docker), check first launch, migrations, upload from a phone, Drive/Wi-Fi settings, quit and
relaunch with data intact. Document uninstall behavior (user data folder is kept).

## Feature D — Update check

**Problem.** Users must manually re-download each release.

**Scope.** On launch, check the GitHub Releases API and show "new version available" with a
link. No silent auto-install. DB schema upgrades already run via `migrate` at startup.

## Feature E — Simpler Google Drive setup (optional, later)

**Problem.** Each user creates their own Google Cloud project, OAuth credentials and consent
screen — the least autonomous part of the product.

**Scope.** Investigate a shared verified OAuth app (requires Google verification) or a guided
wizard improvement. Drive stays optional.

## Order

A -> B -> C -> D -> E. A and C need no external accounts; B needs a purchase from the user.
