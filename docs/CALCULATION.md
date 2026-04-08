# Berechnungsmethodik und Annahmen

Diese Dokumentation beschreibt, wie der Steuerklassen-Rechner rechnet und wo bewusst vereinfacht wird.

Ich habe die Berechnungen nach bestem Wissen und auf Basis eigener Recherchen umgesetzt. Trotzdem kann ich nicht garantieren, dass alle Annahmen, Parameter und Sonderfälle zu 100% korrekt oder vollständig sind. Die Ergebnisse sind nur eine Orientierung und **keine Steuerberatung**.

## Unterstützte Steuerjahre

- 2025
- 2026

Neue Jahre können in `engine/parameters.py` ergänzt werden.

## Eingabeparameter

### Pflichtfelder

| Feld | Beschreibung |
|------|--------------|
| Jahresbrutto | Gesamtes Jahresbrutto pro Partner inkl. 13./14. Gehalt, Boni; `0`, wenn nur Elterngeld berücksichtigt werden soll |
| Steuerjahr | 2025 oder 2026 |
| Bundesland | Für Kirchensteuersatz: 8% Bayern/Baden-Württemberg, 9% in den anderen Bundesländern |

### Optionale Felder pro Partner

| Feld | Default | Beschreibung |
|------|---------|--------------|
| Anzahl Gehälter | 12 | Wie viele Gehaltsabrechnungen pro Jahr, z. B. 12, 13 oder 14 |
| Kirchensteuer | Nein | Kirchensteuerpflichtig? |
| Beamter | Nein | Keine RV/AV/GKV/PV-Beiträge |
| PKV | Nein | Privat krankenversichert plus monatlicher Beitrag |
| Elterngeld | Kein | Kein, Basis oder Plus |
| Brutto vor Geburt | 0 | Jahresbrutto vor der Geburt als Basis für die Elterngeld-Berechnung |
| KV-Zusatzbeitrag | Offizieller Durchschnitt | Individueller Zusatzbeitrag der Krankenkasse |
| Weitere Einkünfte | 0 | Jährliche Einkünfte neben Gehalt |
| Werbungskosten | 0 | Betrag über der Pauschale von 1.230 EUR |
| Anzahl Kinder | 0 | Beeinflusst PV-Beitrag, Kindergeld und Kinderfreibetrag |

## 1. Einkommensteuer (§32a EStG)

Die Einkommensteuer wird nach der Formel des §32a EStG berechnet. Der Tarif hat fünf Zonen:

| Zone | Bereich 2025 | Steuersatz |
|------|--------------|------------|
| 1 | 0 - 12.096 EUR | 0% Grundfreibetrag |
| 2 | 12.097 - 17.443 EUR | 14% - 23,97%, progressiv |
| 3 | 17.444 - 68.480 EUR | 23,97% - 42%, progressiv |
| 4 | 68.481 - 277.825 EUR | 42% Spitzensteuersatz |
| 5 | ab 277.826 EUR | 45% Reichensteuer |

Formeln für 2025:

- Zone 2: `y = (zvE - 12.096) / 10.000; ESt = (932,30 * y + 1.400) * y`
- Zone 3: `z = (zvE - 17.443) / 10.000; ESt = (176,64 * z + 2.397) * z + 1.015,13`
- Zone 4: `ESt = 0,42 * zvE - 10.911,92`
- Zone 5: `ESt = 0,45 * zvE - 19.246,67`

Das Ergebnis wird auf volle Euro abgerundet.

## 2. Ehegattensplitting

Bei der Einkommensteuererklärung wird für Ehepaare in gemeinsamer Veranlagung der Splittingtarif angewandt:

```text
Jahressteuer = 2 * ESt(gemeinsames_zvE / 2)
```

Das Einkommen beider Partner wird zusammengerechnet, halbiert, besteuert und verdoppelt. Bei hoher Einkommensdifferenz ist das günstiger als Einzelveranlagung.

Der Tab `Unverheiratet` zeigt zusätzlich eine pragmatische Näherung:

- Verheiratet: tatsächliche Jahressteuer nach Splittingtarif
- Unverheiratet: beide Partner einzeln nach Grundtabelle
- Splitting-Vorteil: Differenz aus unverheirateter Einzelsteuer und verheirateter Splittingsteuer

Kindergeld bleibt in diesem Vergleich außen vor. Kinderfreibetrag-Details für unverheiratete Eltern werden in dieser Version nicht separat simuliert.

## 3. Steuerklassen und monatlicher Lohnsteuerabzug

Die Steuerklasse bestimmt nur den monatlichen Lohnsteuerabzug, nicht die finale Jahressteuer:

| Steuerklasse | Berechnung | Effekt |
|--------------|------------|--------|
| SK 4 | Grundtabelle wie Einzelperson | Standard bei ähnlichen Einkommen |
| SK 3 | Splittingtarif auf ein Einkommen, doppelter Grundfreibetrag | Weniger monatliche Steuer |
| SK 5 | Grundtabelle ohne Grundfreibetrag | Mehr monatliche Steuer |
| SK 4+Faktor | SK4-Steuer mal Faktor kleiner/gleich 1 | Annäherung an tatsächliche Jahressteuer |

Faktor-Berechnung:

```text
Faktor = Splitting-ESt(P1 + P2) / (SK4-ESt(P1) + SK4-ESt(P2))
```

## 4. Monatliches Netto

Für jeden Partner wird berechnet:

```text
Brutto
- Lohnsteuer
- Solidaritätszuschlag
- Kirchensteuer
- Krankenversicherung
- Rentenversicherung
- Arbeitslosenversicherung
- Pflegeversicherung
= Netto
```

Bei mehr als 12 Gehältern wird die Monatsansicht als Netto pro Gehaltsabrechnung dargestellt:

- Brutto pro Gehaltsabrechnung = `Jahresbrutto / Anzahl Gehälter`
- Lohnsteuer, Solidaritätszuschlag und Kirchensteuer werden vereinfacht über die Anzahl der Gehaltsabrechnungen verteilt.
- Die Jahreswerte verwenden weiterhin das tatsächliche Jahresbrutto.

Ein 13./14. Gehalt wird in dieser App vereinfacht wie eine reguläre Gehaltsabrechnung behandelt. Die App bildet keine echte Lohnabrechnung für sonstige Bezüge wie Weihnachtsgeld, Urlaubsgeld oder Boni nach. In der Praxis kann der Lohnsteuerabzug im Auszahlungsmonat deshalb abweichen; die finale Jahressteuer wird über den Jahresausgleich betrachtet.

## 5. Zu versteuerndes Einkommen

Vom Jahresbrutto werden abgezogen:

- Werbungskostenpauschale: 1.230 EUR oder höhere tatsächliche Kosten
- Sonderausgabenpauschale: 36 EUR, beziehungsweise 72 EUR bei SK 3
- Vorsorgepauschale: vereinfachte Berechnung basierend auf den Arbeitnehmer-Sozialversicherungsbeiträgen für RV, KV und PV

Die Vorsorgepauschale ist bewusst vereinfacht und bildet nicht den vollständigen BMF-Programmablaufplan ab.

## 6. Solidaritätszuschlag

- Satz: 5,5% der Einkommensteuer
- Freigrenze 2025: 19.950 EUR Einzelperson / 39.900 EUR Paar
- Milderungszone: Über der Freigrenze maximal 11,9% des Überschreitungsbetrags

Seit 2021 zahlen nur noch Gutverdiener Solidaritätszuschlag.

## 7. Kirchensteuer

- Bayern und Baden-Württemberg: 8% der Einkommensteuer
- Alle anderen Bundesländer: 9% der Einkommensteuer

## 8. Sozialversicherungsbeiträge

Alle Beiträge werden 50/50 zwischen Arbeitnehmer und Arbeitgeber geteilt und bis zur Beitragsbemessungsgrenze berechnet:

| Versicherung | Gesamtsatz | AN-Anteil | BBG 2025 | BBG 2026 |
|--------------|------------|-----------|----------|----------|
| Krankenversicherung | 14,6% + Zusatzbeitrag | Hälfte | 66.150 EUR | 69.750 EUR |
| Rentenversicherung | 18,6% | 9,3% | 96.600 EUR | 101.400 EUR |
| Arbeitslosenversicherung | 2,6% | 1,3% | 96.600 EUR | 101.400 EUR |
| Pflegeversicherung | 3,6% | variabel | 66.150 EUR | 69.750 EUR |

KV-Zusatzbeitrag:

- 2025: durchschnittlich 2,5%
- 2026: durchschnittlich 2,9%
- optional individuell überschreibbar

Pflegeversicherung, Arbeitnehmer-Anteil:

- Kinderlos: Basis 1,8% + 0,6% Zuschlag = 2,4%
- 1 Kind: 1,8%
- 2 Kinder: 1,55%
- 3 Kinder: 1,30%
- 4 Kinder: 1,05%
- 5+ Kinder: 0,80%

## 9. Sonderfälle

### Beamte

- Keine Beiträge zu RV, AV, GKV und PV
- Stattdessen private Krankenversicherung mit Beihilfe
- Nur der PKV-Beitrag wird vom Brutto abgezogen

### Privat Krankenversicherte

- Eigener monatlicher PKV-Beitrag statt GKV-Berechnung
- PV-Beitrag wird trotzdem nach GKV-Regeln berechnet, sofern die Person nicht als Beamter markiert ist

### Elterngeld

Das Elterngeld wird aus dem Jahresbrutto vor der Geburt berechnet. Dieses Feld ist unabhängig vom aktuellen Gehalt. So kann ein Partner aktuell 0 EUR verdienen und trotzdem Elterngeld auf Basis des früheren Gehalts erhalten.

| Variante | Dauer | Min/Monat | Max/Monat | Ersatzrate |
|----------|-------|-----------|-----------|------------|
| Elterngeld Basis | 12 Monate | 300 EUR | 1.800 EUR | 65% - 67% |
| Elterngeld Plus | 24 Monate | 150 EUR | 900 EUR | 65% - 67% |

Berechnung des Elterngeld-Netto:

```text
Brutto vor Geburt
- Werbungskostenpauschale anteilig
= Bemessungs-Brutto
- Lohnsteuer, immer Steuerklasse 4
- Sozialversicherungsbeiträge
= Elterngeld-Netto
```

Ersatzrate:

| Elterngeld-Netto | Ersatzrate |
|------------------|------------|
| unter 1.000 EUR | 67% + 0,1% pro 2 EUR unter 1.000, maximal 100% |
| 1.000 - 1.200 EUR | 67% |
| über 1.200 EUR | 65% |

Steuerliche Behandlung:

- Elterngeld ist steuerfrei und erscheint nicht im monatlichen Netto.
- Es löst aber den Progressionsvorbehalt aus.
- Dadurch steigt die Steuerlast auf das verbleibende Einkommen des Haushalts.

### Kindergeld und Kinderfreibetrag

- Kindergeld 2025: 255 EUR pro Kind und Monat
- Kindergeld 2026: 259 EUR pro Kind und Monat
- Kinderfreibetrag 2025: 9.600 EUR pro Paar
- Kinderfreibetrag 2026: 9.756 EUR pro Paar

Die App führt eine vereinfachte Günstigerprüfung durch.

## 10. Jahresausgleich

Am Jahresende wird die tatsächliche Steuerschuld berechnet:

1. Beide Einkommen addieren
2. Freibeträge und Vorsorgeaufwendungen abziehen
3. Splittingtarif anwenden
4. Solidaritätszuschlag und Kirchensteuer berechnen
5. Einbehaltene Steuer mit tatsächlicher Jahressteuer vergleichen
6. Differenz als Erstattung oder Nachzahlung ausweisen

Da alle Steuerklassen die gleiche Jahressteuer ergeben, gilt:

- SK 3/5: mehr monatlich verfügbar, aber oft Nachzahlung
- SK 4/4: weniger monatlich verfügbar, aber oft Erstattung
- SK 4+Faktor: meistens näher an der tatsächlichen Steuerlast

## Genauigkeit und Grenzen

- Einkommensteuer: §32a EStG-Formeln, auf volle Euro abgerundet
- Vorsorgepauschale: vereinfacht, nicht vollständiger BMF-Programmablaufplan
- Sonderzahlungen: vereinfachte Behandlung wie reguläre Gehaltsabrechnungen
- Elterngeld und Kinderfreibetrag: pragmatische Näherung, nicht jeder Sonderfall abgedeckt
- Erwartete Abweichung: typischerweise klein, aber nicht garantiert

Quellen und Orientierung:

- BMF-Steuerrechner
- finanz-tools.de
- §32a EStG

Alle Berechnungen ohne Gewähr.
