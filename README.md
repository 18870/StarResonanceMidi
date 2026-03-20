# StarResonanceMidi


StarResonanceMidi is a MIDI-to-keyboard playback tool with a Flet GUI, playlist sequencing, localized UI text, and timing controls.

Primary use case: map MIDI files to keyboard input for in-game performance in Star Resonance.

Language versions:
- English (default): this page
- Chinese: [README.zh-CN.md](README.zh-CN.md)
- Japanese: [README.ja.md](README.ja.md)

## License

This project is licensed under **GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later)**.

## Copyright, Music, and Trademark Notice

- This software is an independent fan-made tool and is not affiliated with or endorsed by game publishers or rights holders.
- You are responsible for the legality of any songs and MIDI files you use.
- Do not upload, distribute, or perform copyrighted songs/MIDI files without proper authorization.
- The trademark/name "Blue Protocol" belongs to **BANDAI NAMCO**.
- The game/copyright for "Star Resonance / Blue Protocol: Star Resonance / ブループロトコル：スターレゾナンス" belongs to **BOKURA**.

## What Is The Header Constraint Template?

The file header template includes four fields:
- `Author`: ownership/maintainer context.
- `Purpose`: what the file is responsible for.
- `Constraints`: engineering rules for contributors (for example: keep translatable text in locales, do not break callback signatures).
- `License`: legal license identifier.

`Constraints` are **not** a software license. They are contributor guardrails for code quality and consistency.

## Requirements

- Python 3.10+
- Packages used by this project: `flet`, `mido`, `pynput`

Example installation:

```bash
python -m pip install flet mido pynput
```

## Run

From project root:

```bash
python main.py
```

## Locale Key Convention

All user-facing app-flow text should come from `locales.json` via locale keys.

Key grouping convention:
- `nav_*`: navigation labels
- `play_*`: player view
- `lib_*`: library view
- `set_*`: settings view
- `msg_*`: runtime status and notifications

When adding a new key:
1. Add it to all locales (`en`, `ja`, `zh`).
2. Keep key order/grouping consistent across locales.
3. Reference the key from code (do not hardcode UI message strings).

## Translation Contributions

Contributions for additional languages are welcome.

Scope:
- UI/app-flow strings: edit [locales.json](locales.json)
- Documentation translation: add a new file like README.xx.md and link it from [README.md](README.md)

Recommended process:
1. Create a locale code entry in [locales.json](locales.json), for example fr, de, or ko.
2. Copy all keys from the English section and translate values only.
3. Keep placeholders unchanged, for example {} and {:.1f}.
4. Run locale consistency check: python scripts/check_locales.py
5. If you add a new README translation, update the language links in [README.md](README.md), [README.zh-CN.md](README.zh-CN.md), and [README.ja.md](README.ja.md).

PR checklist:
- No missing locale keys
- No changed placeholder format tokens
- Terminology is consistent within the language
- Existing behavior is unchanged

Attribution and license:
- By submitting translation contributions, you agree your changes are licensed under AGPL-3.0-or-later for this repository.
- If you want your name listed as translator, include it in your PR description.

## Locale Consistency Check

Script: [scripts/check_locales.py](scripts/check_locales.py)

Run:

```bash
python scripts/check_locales.py
```

Behavior:
- Exit `0`: all locales have exactly the same key set.
- Exit `1`: key mismatch detected; script prints missing/extra keys per locale.

## Community Templates

This repository includes a full GitHub collaboration template set:

- Pull request template: [.github/PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md)
- Issue templates:
	- [.github/ISSUE_TEMPLATE/bug_report.yml](.github/ISSUE_TEMPLATE/bug_report.yml)
	- [.github/ISSUE_TEMPLATE/feature_request.yml](.github/ISSUE_TEMPLATE/feature_request.yml)
	- [.github/ISSUE_TEMPLATE/translation_request.yml](.github/ISSUE_TEMPLATE/translation_request.yml)
	- [.github/ISSUE_TEMPLATE/legal_notice.yml](.github/ISSUE_TEMPLATE/legal_notice.yml)
	- [.github/ISSUE_TEMPLATE/config.yml](.github/ISSUE_TEMPLATE/config.yml)
- Contribution guide: [CONTRIBUTING.md](CONTRIBUTING.md)
- Code of Conduct: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- Security policy: [SECURITY.md](SECURITY.md)
- Support guide: [SUPPORT.md](SUPPORT.md)
- Code owners: [.github/CODEOWNERS](.github/CODEOWNERS)
