# Contributing

Thanks for contributing.

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


## Translation Contributing

Scope:
- UI/app-flow strings: edit [locales.json](locales.json)
- Documentation translation: add a new file like README.xx.md and link it from [README.md](README.md)

Recommended process:
1. Create a locale code entry in [locales.json](locales.json), for example fr, de, or ko.
2. Copy all keys from the English section and translate values only.
3. Keep placeholders unchanged, for example {} and {:.1f}.
4. Run locale consistency check: python scripts/check_locales.py
5. If you add a new README translation, update the language links in [README.md](README.md), [README.zh-CN.md](README.zh-CN.md), [README.ja.md](README.ja.md) and so on.

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


## Legal reminders

- Do not commit copyrighted songs or MIDI files without authorization.
- Respect trademark/copyright ownership statements documented in README.

## License

By contributing, you agree your contributions are licensed under AGPL-3.0-or-later.