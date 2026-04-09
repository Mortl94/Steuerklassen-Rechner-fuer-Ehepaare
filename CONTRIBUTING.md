# Mitmachen

Pull Requests und Issues sind willkommen.

## Einstieg: Issue oder direkt PR?

- Öffne zuerst ein Issue, wenn unklar ist, ob etwas ein Bug, eine gewünschte Änderung oder fachlich korrekt ist.
- Erstelle direkt einen PR, wenn es ein kleiner, klar abgegrenzter Fix ist.

## Issues

Bitte beschreibe bei Bugs:

- welche Eingaben verwendet wurden
- welches Ergebnis erwartet wurde
- welches Ergebnis tatsächlich angezeigt wurde
- ob es eine Quelle oder Vergleichsrechnung gibt, z. B. BMF-Rechner oder amtliche Werte

## Pull Requests

Minimaler Ablauf:

1. Repository forken oder Branch im eigenen Clone erstellen.
2. Änderungen umsetzen und lokal testen.
3. PR gegen `main` eröffnen und kurz beschreiben, was geändert wurde und warum.

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
