# Steuerklassen-Rechner für Ehepaare

Open-Source-Rechner für verheiratete Paare in Deutschland. Die App vergleicht die Steuerklassen-Kombinationen **3/5**, **5/3**, **4/4** und **4+Faktor** und zeigt monatlichen Cashflow, Jahresausgleich und das effektive Jahresergebnis nach Einkommensteuererklärung.

## Wichtiger Hinweis

Ich habe die Berechnungen nach bestem Wissen und auf Basis eigener Recherchen umgesetzt. Trotzdem kann ich nicht garantieren, dass alle Annahmen, Parameter und Sonderfälle zu 100% korrekt oder vollständig sind. Dieses Projekt ist **keine Steuerberatung** und ersetzt keine verbindliche Auskunft durch Steuerberater, Finanzamt oder offizielle Rechner.

Die App speichert keine Eingaben dauerhaft, nutzt keine Datenbank und ist ohne Nutzerkonten gedacht. Beim Self-Hosting können trotzdem technische Server- oder Reverse-Proxy-Logs entstehen, je nachdem wie der Server betrieben wird.

## Features

- Vergleich von Steuerklasse 3/5, 5/3, 4/4 und 4+Faktor
- Monatliches Netto pro Partner und Haushalt
- Jahres-Netto, Erstattung oder Nachzahlung bei der Einkommensteuererklärung
- Effektives Jahresergebnis nach Jahresausgleich
- Vereinfachter Vergleich mit unverheirateter Einzelveranlagung
- Unterstützung für 2025 und 2026
- Sonderfälle wie Kirchensteuer, Beamte, PKV, Elterngeld, Kindergeld und Kinderfreibetrag
- Docker-Setup für lokale Nutzung und Serverbetrieb hinter zentralem Caddy

Die zentrale fachliche Annahme: Bei gemeinsamer Veranlagung ist die jährliche Steuerlast bei allen Steuerklassen-Kombinationen identisch. Die Steuerklasse beeinflusst vor allem den monatlichen Lohnsteuerabzug und damit Cashflow, Erstattung oder Nachzahlung.

## Berechnung

Die Methodik, Annahmen, Grenzen und Quellen der Steuerberechnung sind in [docs/CALCULATION.md](docs/CALCULATION.md) dokumentiert.

## Installation & Start

### Voraussetzungen

- Python 3.11+
- pip

### Lokal starten

```bash
pip install -r requirements.txt
streamlit run app.py
```

Die App öffnet sich unter `http://localhost:8501`.

### Docker

```bash
docker build -t steuerrechner .
docker run --rm -p 127.0.0.1:8501:8501 steuerrechner
```

### Docker Compose lokal

```bash
cp .env.example .env
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --build
```

Die App ist dann unter `http://127.0.0.1:8501` erreichbar.

### Self-Hosting mit Caddy

Auf dem Server sollte der Streamlit-Container **nicht direkt öffentlich exposed** werden. Nur ein Reverse Proxy wie Caddy veröffentlicht `80/443`; die App hängt intern am externen Docker-Netzwerk `caddy` und ist dort für Caddy unter `steuerrechner:8501` erreichbar.

Ein generisches Caddy-Beispiel liegt unter [examples/caddy](examples/caddy). Der komplette Ablauf ist in [docs/HOSTING.md](docs/HOSTING.md) dokumentiert.

Kurzfassung:

```bash
docker network inspect caddy >/dev/null 2>&1 || docker network create caddy

cd examples/caddy
cp .env.example .env
# .env bearbeiten: STEUERRECHNER_DOMAIN=deine-domain.de
docker compose up -d
cd ../..

cp .env.example .env
docker compose -f docker-compose.yml -f docker-compose.server.yml up -d --build
```

Vor dem Caddy-Start muss die Domain per DNS auf den Server zeigen. Auf dem Server sollte `8501` nicht per `ports:` veröffentlicht und nicht in der Firewall freigegeben werden.

## Tests

```bash
python -m pytest tests/ -v
```

Falls `python` lokal nicht verfügbar ist:

```bash
python3 -m pytest tests/ -v
```

## Mitmachen

Pull Requests und Issues sind willkommen. Bitte beachte bei Änderungen an der Steuerlogik:

- Änderungen sollten durch Tests abgesichert werden.
- Fachliche Änderungen sollten mit nachvollziehbaren Quellen oder klar dokumentierten Annahmen begründet werden.
- Vereinfachungen sind okay, müssen aber sichtbar dokumentiert sein.

Weitere Hinweise stehen in [CONTRIBUTING.md](CONTRIBUTING.md).

## Projektstruktur

```text
├── app.py                     # Streamlit UI
├── requirements.txt           # Python-Abhängigkeiten
├── Dockerfile                 # Docker-Container
├── docker-compose.yml         # Gemeinsame Compose-Basis ohne Host-Port
├── docker-compose.local.yml   # Lokaler Port-Binding-Override
├── docker-compose.server.yml  # Server-Override für externes Caddy-Netz
├── LICENSE                    # MIT-Lizenz
├── CONTRIBUTING.md            # Hinweise für Issues und Pull Requests
├── SECURITY.md                # Sicherheitskontakt und Meldeweg
├── .github/workflows/         # GitHub Actions für Tests
├── docs/
│   ├── CALCULATION.md         # Berechnungsmethodik und Annahmen
│   └── HOSTING.md             # Self-Hosting-Ablauf
├── examples/
│   └── caddy/                 # Generisches Caddy-Beispiel für Self-Hosting
├── engine/                    # Steuer-, Sozialversicherungs- und Vergleichslogik
└── tests/
    └── test_engine.py         # Unit- und Integrationstests
```

## Lizenz

Dieses Projekt steht unter der MIT-Lizenz. Siehe [LICENSE](LICENSE).
