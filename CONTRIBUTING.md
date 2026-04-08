# Mitmachen

Pull Requests und Issues sind willkommen.

## Issues

Bitte beschreibe bei Bugs:

- welche Eingaben verwendet wurden
- welches Ergebnis erwartet wurde
- welches Ergebnis tatsächlich angezeigt wurde
- ob es eine Quelle oder Vergleichsrechnung gibt, z. B. BMF-Rechner oder amtliche Werte

## Pull Requests

Für Änderungen an der Steuerlogik gilt:

- Bitte Tests ergänzen oder bestehende Tests anpassen.
- Fachliche Änderungen brauchen eine nachvollziehbare Quelle oder eine klar dokumentierte Annahme.
- Vereinfachungen sind okay, müssen aber in `docs/CALCULATION.md` sichtbar sein.
- Bitte keine unrelated Refactorings in fachliche Korrektur-PRs mischen.

Vor einem PR bitte lokal ausführen:

```bash
python -m pytest tests/ -v
```

Falls `python` lokal nicht verfügbar ist:

```bash
python3 -m pytest tests/ -v
```

## Hinweis zur Genauigkeit

Dieses Projekt ist keine Steuerberatung. Auch Beiträge, die nach bestem Wissen recherchiert wurden, können falsch oder unvollständig sein. Fachliche Verbesserungen sind deshalb ausdrücklich willkommen.
