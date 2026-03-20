# Contributing to StarResonanceMidi

Thanks for contributing.

## Ground rules

- Keep behavior changes explicit and scoped.
- Keep user-facing text in locales, not hardcoded in Python logic.
- Keep callback signatures stable unless coordinated in the same PR.
- Follow file header template: Author, Purpose, Constraints, License.

## Development flow

1. Fork and create a branch.
2. Make focused changes.
3. Run checks:

```bash
python scripts/check_locales.py
```

4. Open a pull request using the template.

## Translation contributions

- Update `locales.json` with complete key coverage.
- Preserve formatting placeholders exactly (`{}`, `{:.1f}`).
- If adding a translated README page, update language links in all README files.

## Legal reminders

- Do not commit copyrighted songs or MIDI files without authorization.
- Respect trademark/copyright ownership statements documented in README.

## License

By contributing, you agree your contributions are licensed under AGPL-3.0-or-later.
