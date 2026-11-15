# Homebrew tap

Install tools from `veryshyjelly`:

```sh
brew install veryshyjelly/tap/eitri
brew install --cask veryshyjelly/tap/vocabulary-studio
```

Vocabulary Studio installs a prebuilt macOS app into Applications, selecting the
Apple Silicon or Intel download for your Mac. It requires macOS 13 or later.
No Go, Bun, or Wails installation is required to use the app. On Homebrew 7 and
newer, the fully qualified install command grants trust to this cask only.

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

## CraftCoders

CraftCoders Homebrew support is prepared for the first verified public release.
No formula is checked in until genuine release archives are available. After
that release and the next hourly or manual update, install with:

```sh
brew install veryshyjelly/tap/craftcoders
craftcoders --version
```

The formula installs prebuilt macOS and Linux binaries for ARM64 and Intel/AMD64,
without Rust. Linux archives use Ubuntu 22.04/glibc 2.35 as their build baseline;
compatibility with older systems is not promised. macOS releases are built and
smoke-tested on the configured macOS 15 runners; older macOS versions are not
claimed as validated. Local challenge instructions, testing, and submissions
use cached course content. Initial course acquisition and updates need network
access; building challenge testers needs Go or Docker. These tester dependencies
are separate from installing the prebuilt CraftCoders CLI.

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
python3 scripts/update_craftcoders.py
```

The Vocabulary Studio updater skips gracefully before the first published
release, rejects prereleases and incomplete releases, and verifies both Mac
archives before changing the cask. It requires Python 3.11 or later and `gh`.

After generating the cask:

```sh
brew style ./Casks/vocabulary-studio.rb
brew tap veryshyjelly/tap
brew trust --cask veryshyjelly/tap/vocabulary-studio
brew audit --cask --online veryshyjelly/tap/vocabulary-studio
```

The CraftCoders updater requires Python 3.11 or later and `gh`. It polls
`veryshyjelly/craftcoders-cli`, skips only a latest-release HTTP 404, and rejects
draft, prerelease, incomplete, ambiguous, or corrupt releases. It verifies all
four archives against `checksums.txt` before atomically replacing the formula;
it never runs downloaded content. Other upstream failures stop the workflow.
Existing formula content is retained on verification or replacement failure.

After the genuine release has generated a formula, validate it with:

```sh
ruby -c Formula/craftcoders.rb
brew style ./Formula/craftcoders.rb
brew audit --online veryshyjelly/tap/craftcoders
brew test veryshyjelly/tap/craftcoders
```

The upstream release workflow publishes only a complete verified stable tag.
If it leaves a failed draft, inspect the failed job and draft assets, then
explicitly recover or remove that unpublished draft before retrying. Never
replace artifacts of an already published version; publish a new version for
repairs. A missing first release creates no placeholder formula or checksums.
