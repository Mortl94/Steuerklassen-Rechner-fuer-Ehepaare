# Steuerklassen-Rechner für Ehepaare

Vergleicht die Steuerklassen-Kombinationen **3/5**, **5/3**, **4/4** und **4+Faktor** für verheiratete Paare und zeigt:

- Monatliches Netto pro Partner und Haushalt
- Jährliches Netto
- Erstattung oder Nachzahlung bei der Einkommensteuererklärung
- Effektives Jahresergebnis nach Steuererklärung

## Kernaussage

Die **jährliche Steuerlast ist bei allen Steuerklassen-Kombinationen identisch** (Splittingtarif). Der Unterschied liegt **nur** im monatlichen Cashflow vs. Jahresausgleich bei der Steuererklärung.

---

## Installation & Start

### Voraussetzungen

- Python 3.11+
- pip

### Lokal starten

```bash
# Dependencies installieren
pip install -r requirements.txt

# App starten
streamlit run app.py
```

Die App öffnet sich unter `http://localhost:8501`.

### Docker

```bash
# Image bauen
docker build -t steuerrechner .

# Container starten
docker run -p 8501:8501 steuerrechner
```

### Tests ausführen

```bash
python -m pytest tests/ -v
```

---

## Unterstützte Steuerjahre

- **2025** und **2026**
- Neue Jahre können einfach in `engine/parameters.py` ergänzt werden

---

## Eingabeparameter

### Pflichtfelder

| Feld | Beschreibung |
|------|-------------|
| Jahresbrutto | Gesamtes Jahresbrutto pro Partner inkl. 13./14. Gehalt, Boni (0 wenn nur Elterngeld) |
| Steuerjahr | 2025 oder 2026 |
| Bundesland | Für Kirchensteuersatz (8% Bayern/BaWü, 9% Rest) |

### Optionale Felder (pro Partner)

| Feld | Default | Beschreibung |
|------|---------|-------------|
| Anzahl Gehälter | 12 | Wie viele Monatsgehälter pro Jahr (12, 13, 14) — für die Anzeige pro Gehaltsabrechnung |
| Kirchensteuer | Nein | Kirchensteuerpflichtig? |
| Beamter | Nein | Keine RV/AV/GKV/PV-Beiträge |
| PKV | Nein | Privat krankenversichert + monatlicher Beitrag |
| Elterngeld | 0 | Monatlicher Betrag + Anzahl Monate |
| KV-Zusatzbeitrag | Durchschnitt | Individueller Zusatzbeitrag der Krankenkasse |
| Weitere Einkünfte | 0 | Jährliche Einkünfte neben Gehalt |
| Werbungskosten | 0 | Betrag ÜBER der Pauschale von 1.230 EUR |
| Anzahl Kinder | 0 | Beeinflusst PV-Beitrag, Kindergeld und Kinderfreibetrag |

---

## Berechnungsmethodik

### 1. Einkommensteuer (§32a EStG)

Die Einkommensteuer wird nach der **offiziellen Formel des §32a EStG** berechnet. Der Tarif hat 5 Zonen:

| Zone | Bereich (2025) | Steuersatz |
|------|---------------|------------|
| 1 | 0 - 12.096 EUR | 0% (Grundfreibetrag) |
| 2 | 12.097 - 17.443 EUR | 14% - 23,97% (progressiv) |
| 3 | 17.444 - 68.480 EUR | 23,97% - 42% (progressiv) |
| 4 | 68.481 - 277.825 EUR | 42% (Spitzensteuersatz) |
| 5 | ab 277.826 EUR | 45% (Reichensteuer) |

**Formeln (Beispiel 2025):**
- Zone 2: `y = (zvE - 12.096) / 10.000; ESt = (932,30 * y + 1.400) * y`
- Zone 3: `z = (zvE - 17.443) / 10.000; ESt = (176,64 * z + 2.397) * z + 1.015,13`
- Zone 4: `ESt = 0,42 * zvE - 10.911,92`
- Zone 5: `ESt = 0,45 * zvE - 19.246,67`

Das Ergebnis wird auf volle Euro **abgerundet**.

### 2. Ehegattensplitting (Splittingtarif)

Bei der **Einkommensteuererklärung** wird immer der Splittingtarif angewandt:

```
Jahressteuer = 2 * ESt(gemeinsames_zvE / 2)
```

Das Einkommen beider Partner wird zusammengerechnet, halbiert, besteuert und verdoppelt. Das ist bei hoher Einkommensdifferenz günstiger als Einzelveranlagung.

### 3. Steuerklassen und monatlicher Lohnsteuerabzug

Die Steuerklasse bestimmt **nur den monatlichen Lohnsteuerabzug**, nicht die finale Jahressteuer:

| Steuerklasse | Berechnung | Effekt |
|-------------|-----------|--------|
| **SK 4** | Grundtabelle (wie Einzelperson) | Standard bei gleichen Einkommen |
| **SK 3** | Splittingtarif auf ein Einkommen (doppelter Grundfreibetrag) | Weniger monatliche Steuer |
| **SK 5** | Grundtabelle ohne Grundfreibetrag | Mehr monatliche Steuer |
| **SK 4+Faktor** | SK4-Steuer * Faktor (< 1,0) | Annäherung an tatsächliche Jahressteuer |

**Faktor-Berechnung:**
```
Faktor = Splitting-ESt(P1 + P2) / (SK4-ESt(P1) + SK4-ESt(P2))
```

### 4. Monatliches Netto

Für jeden Partner wird berechnet:

```
Brutto
- Lohnsteuer (je nach Steuerklasse)
- Solidaritätszuschlag
- Kirchensteuer (optional)
- Krankenversicherung (AN-Anteil)
- Rentenversicherung (AN-Anteil)
- Arbeitslosenversicherung (AN-Anteil)
- Pflegeversicherung (AN-Anteil)
= Netto
```

### 5. Zu versteuerndes Einkommen (zvE)

Vom Jahresbrutto werden abgezogen:
- **Werbungskostenpauschale**: 1.230 EUR (oder höhere tatsächliche Kosten)
- **Sonderausgabenpauschale**: 36 EUR (72 EUR bei SK 3)
- **Vorsorgepauschale**: Vereinfachte Berechnung basierend auf den AN-Sozialversicherungsbeiträgen (RV + KV + PV)

### 6. Solidaritätszuschlag

- **Satz**: 5,5% der Einkommensteuer
- **Freigrenze** (2025): 19.950 EUR (Einzelperson) / 39.900 EUR (Paar)
- **Milderungszone**: Über der Freigrenze maximal 11,9% des Überschreitungsbetrags
- Seit 2021 zahlen nur noch Gutverdiener Soli

### 7. Kirchensteuer

- **Bayern & Baden-Württemberg**: 8% der Einkommensteuer
- **Alle anderen Bundesländer**: 9% der Einkommensteuer

### 8. Sozialversicherungsbeiträge

Alle Beiträge werden **50/50 zwischen Arbeitnehmer und Arbeitgeber** geteilt und bis zur **Beitragsbemessungsgrenze (BBG)** berechnet:

| Versicherung | Gesamtsatz | AN-Anteil | BBG 2025 | BBG 2026 |
|-------------|-----------|-----------|----------|----------|
| Krankenversicherung (GKV) | 14,6% + Zusatzbeitrag | Hälfte | 66.150 EUR | 69.750 EUR |
| Rentenversicherung | 18,6% | 9,3% | 96.600 EUR | 101.400 EUR |
| Arbeitslosenversicherung | 2,6% | 1,3% | 96.600 EUR | 101.400 EUR |
| Pflegeversicherung | 3,6% | variabel | 66.150 EUR | 69.750 EUR |

**KV-Zusatzbeitrag**: Durchschnitt 2,5% (2025) / 2,9% (2026), individuell je Krankenkasse.

**Pflegeversicherung AN-Anteil**:
- Kinderlos: Basis (1,8%) + 0,6% Zuschlag = **2,4%**
- 1 Kind: **1,8%** (Basis)
- 2 Kinder: 1,8% - 0,25% = **1,55%**
- 3 Kinder: 1,8% - 0,50% = **1,30%**
- 4 Kinder: 1,8% - 0,75% = **1,05%**
- 5+ Kinder: 1,8% - 1,00% = **0,80%**

### 9. Sonderfälle

#### Beamte
- **Keine** Beiträge zu RV, AV, GKV und PV
- Stattdessen: Private Krankenversicherung (PKV) mit Beihilfe
- Nur der PKV-Beitrag (AN-Anteil) wird vom Brutto abgezogen

#### Privat Krankenversicherte (PKV)
- Eigener monatlicher PKV-Beitrag statt GKV-Berechnung
- PV-Beitrag wird trotzdem nach GKV-Regeln berechnet (sofern nicht Beamter)

#### Elterngeld
- **Steuerfrei**, wird nicht vom Arbeitgeber abgezogen
- Löst aber den **Progressionsvorbehalt** aus:
  1. Fiktives Gesamteinkommen = reguläres Einkommen + Elterngeld
  2. Steuersatz auf fiktives Gesamteinkommen berechnen
  3. Diesen höheren Satz auf das reguläre Einkommen anwenden
- **Eingabe**: Brutto/Monat = 0, Elterngeld = Betrag, Monate = Dauer
- Elterngeld wird separat ausgezahlt und erscheint nicht im monatlichen Netto

#### Kindergeld vs. Kinderfreibetrag (Günstigerprüfung)
- **Kindergeld** (2025: 255 EUR/Kind/Monat, 2026: 259 EUR) wird automatisch ausgezahlt
- **Kinderfreibetrag** (2025: 9.600 EUR/Paar, 2026: 9.756 EUR) reduziert das zvE
- Das Finanzamt prüft automatisch, was günstiger ist
- Bei hohen Einkommen (ca. > 85.000 EUR zvE) lohnt sich der Kinderfreibetrag
- Der Rechner führt diese Günstigerprüfung automatisch durch

### 10. Jahresausgleich (Einkommensteuererklärung)

Am Jahresende wird die **tatsächliche Steuerschuld** berechnet:

1. Beide Einkommen addieren
2. Freibeträge und Vorsorgeaufwendungen abziehen
3. Splittingtarif anwenden: `2 * ESt(zvE / 2)`
4. Soli + Kirchensteuer berechnen
5. Vergleich: Einbehalten vs. Tatsächlich
6. **Differenz** = Erstattung (positiv) oder Nachzahlung (negativ)

Da alle Steuerklassen die gleiche Jahressteuer ergeben, gilt:
- SK 3/5: Mehr monatlich verfügbar, aber oft Nachzahlung
- SK 4/4: Weniger monatlich, aber oft Erstattung
- SK 4+Faktor: Am nächsten an der tatsächlichen Steuerlast

---

## Technische Details

### Projektstruktur

```
├── app.py                     # Streamlit UI (4 Tabs)
├── requirements.txt           # Python-Abhängigkeiten
├── Dockerfile                 # Docker-Container
├── .dockerignore
├── engine/
│   ├── __init__.py
│   ├── models.py              # Pydantic Ein-/Ausgabe-Modelle
│   ├── parameters.py          # Steuerparameter 2025 + 2026
│   ├── tax.py                 # ESt, Soli, Kirchensteuer
│   ├── social.py              # Sozialversicherungsbeiträge
│   ├── payroll.py             # Monatl. Lohnsteuer pro Steuerklasse
│   └── comparison.py          # SK-Vergleich + Jahresausgleich
└── tests/
    └── test_engine.py         # 46 Unit- und Integrationstests
```

### Abhängigkeiten

| Paket | Version | Zweck |
|-------|---------|-------|
| streamlit | >= 1.36.0 | Web-UI |
| pydantic | >= 2.6.0 | Datenvalidierung |
| plotly | >= 5.18.0 | Interaktive Charts |
| pandas | >= 2.0.0 | Tabellen-Darstellung |
| pytest | >= 8.0.0 | Tests |

### Genauigkeit

- **Einkommensteuer**: Offizielle §32a EStG Formeln, abgerundet auf volle Euro
- **Vorsorgepauschale**: Vereinfachte Berechnung (AN-Sozialversicherungsanteile statt vollem BMF-Programmablaufplan)
- **Erwartete Abweichung**: Typisch < 10 EUR/Monat zum offiziellen BMF-Steuerrechner
- **Quellen**: bmf-steuerrechner.de, finanz-tools.de, §32a EStG

---

## Disclaimer

Alle Berechnungen ohne Gewähr. Dies ist **keine Steuerberatung**. Die Ergebnisse dienen nur zur Orientierung. Für verbindliche Auskünfte wenden Sie sich an einen Steuerberater oder das zuständige Finanzamt.
