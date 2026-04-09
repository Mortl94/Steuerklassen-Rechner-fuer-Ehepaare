# Self-Hosting mit Docker und Caddy

Diese Anleitung beschreibt ein generisches Hosting-Setup mit einem zentralen Caddy-Reverse-Proxy. Die App selbst wird dabei nicht direkt öffentlich exposed.

## Architektur

- Caddy ist der einzige Container mit öffentlichen Ports `80` und `443`.
- Die Streamlit-App hängt am externen Docker-Netzwerk `caddy`.
- Caddy erreicht die App intern unter `steuerrechner:8501`.
- Port `8501` wird auf dem Server nicht per `ports:` veröffentlicht und sollte nicht in der Firewall geöffnet werden.

## Voraussetzungen

- Docker und Docker Compose auf dem Server
- Domain mit `A`/`AAAA` Record auf den Server
- Firewall erlaubt `80/tcp`, `443/tcp` und optional `443/udp`
- Firewall blockiert `8501`

## 1. Repository auf den Server holen

```bash
git clone https://github.com/Mortl94/Steuerklassen-Rechner-fuer-Ehepaare.git
cd Steuerklassen-Rechner-fuer-Ehepaare
```

Bei späteren Updates:

```bash
git pull
```

## 2. Gemeinsames Docker-Netzwerk anlegen

```bash
docker network inspect caddy >/dev/null 2>&1 || docker network create caddy
```

Wenn du einen anderen Netzwerknamen nutzt, setze denselben Wert in `examples/caddy/.env` und in der App-`.env`.

## 3. Caddy starten

```bash
cd examples/caddy
cp .env.example .env
```

In `examples/caddy/.env` die Domain setzen:

```dotenv
CADDY_NETWORK=caddy
STEUERRECHNER_DOMAIN=deine-domain.de
```

Dann Caddy starten:

```bash
docker compose up -d
cd ../..
```

Die Beispiel-Caddyfile:

```caddyfile
{$STEUERRECHNER_DOMAIN:steuerklassen-rechner.de} {
	encode zstd gzip
	reverse_proxy steuerrechner:8501
}
```

## 4. App starten

Im Repository-Root:

```bash
cp .env.example .env
docker compose -f docker-compose.yml -f docker-compose.server.yml up -d --build
```

Die App hängt dadurch am externen `caddy`-Netzwerk, veröffentlicht aber keinen Host-Port.

## 5. Prüfen

```bash
docker ps
docker network inspect caddy
docker compose -f examples/caddy/docker-compose.yml logs -f
docker compose -f docker-compose.yml -f docker-compose.server.yml logs -f
```

Die Website sollte über `https://deine-domain.de` erreichbar sein, sobald DNS korrekt gesetzt ist und Caddy das Zertifikat holen konnte.

## Updates

```bash
git pull
docker compose -f docker-compose.yml -f docker-compose.server.yml up -d --build
```

Caddy muss nur neu gestartet werden, wenn sich `examples/caddy/Caddyfile`, `examples/caddy/docker-compose.yml` oder `examples/caddy/.env` geändert hat:

```bash
cd examples/caddy
docker compose up -d
```

## Hinweise zu Logs und Datenschutz

Das Beispiel aktiviert keine expliziten Caddy-Access-Logs. Wenn du Access-Logs aktivierst, dokumentiere die Aufbewahrung bewusst, weil IP-Adresse und User-Agent personenbezogene Daten sein können.
