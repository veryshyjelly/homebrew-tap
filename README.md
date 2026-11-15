# Homebrew tap

Install tools from `veryshyjelly`:

```sh
brew install veryshyjelly/tap/eitri
brew install --cask veryshyjelly/tap/vocabulary-studio
```

Vocabulary Studio installs a prebuilt macOS app into Applications, selecting the
Apple Silicon or Intel download for your Mac. It requires macOS 13 or later.
Its cask becomes available after the first app release is published and the
updater runs. No Go, Bun, or Wails installation is required to use the app.

```sh
brew update
brew upgrade --cask vocabulary-studio
brew uninstall --cask vocabulary-studio
```

Uninstalling keeps app settings and saved sessions. Use `brew uninstall --zap
--cask vocabulary-studio` to also remove its settings and local session files.
Keychain credentials remain in the macOS Keychain; sign out in the app first to
remove them.

If you previously installed Vocabulary Studio manually, move the old app from
`/Applications` or `~/Applications` to the Trash before installing the cask.

Vocabulary Studio currently uses ad-hoc signing without Apple notarization. If
macOS blocks it on first launch, attempt to open the app, then use **System
Settings → Privacy & Security → Open Anyway**. The cask preserves macOS quarantine
and Gatekeeper protections.

## Maintaining the tap

The hourly **Update Homebrew packages** workflow checks upstream releases and
commits updated formulae and casks only after verifying downloaded artifacts
against the release checksums. Run the workflow manually to update immediately.
It needs no cross-repository credentials: the tap's own `GITHUB_TOKEN` can read
public releases and commit updates here.

To update locally from an authenticated GitHub CLI session:

```sh
python3 -m unittest discover -s scripts
python3 scripts/update.py
python3 scripts/update_vocabulary_studio.py
```

The Vocabulary Studio updater skips gracefully before the first published
release, rejects prereleases and incomplete releases, and verifies both Mac
archives before changing the cask. It requires Python 3.11 or later and `gh`.

After generating the cask:

```sh
brew style ./Casks/vocabulary-studio.rb
brew tap veryshyjelly/tap
brew audit --cask --online veryshyjelly/tap/vocabulary-studio
```
