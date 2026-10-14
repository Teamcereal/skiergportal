# SkiErgportal

Lokal Streamlit-portal for analyse av Concept2 SkiErg-økter. Appen kan lese lokale Concept2 CSV-eksporter eller hente historikk fra Concept2 API-et.

## Status

Dette er en lokal Python-app med en separat PyInstaller-distribusjon for Windows. Se [prosjektets hovedguide](../../README.md) for installasjon, oppstart og personvern.

Portalen inneholder blant annet:

- Økttabell med søk, filtre, klikkbare rader, totaldistanse og kompakt intervalloppsett.
- Leaderboard for standarddistanser, tidsøkter og registrerte intervallprotokoller.
- Øktdetaljer med kommentarer, tagger, kroppsvekt, laktat per drag og terskeltestanalyse.
- Analyseflater for volum, effekt, puls, pace og laktat.

## Kjør lokalt

### Start via launcher

Kjør [startfilen](../../../Trykk%20her%20for%20%C3%A5%20starte%20skiergportal.cmd) fra rotmappen. Launcheren oppretter `data/system/.venv` og synkroniserer avhengighetene med uv første gang.

### Start fra terminal

Fra `system/`:

```powershell
uv sync --frozen
uv run --frozen streamlit run treningshistorikk_app/app.py
```

Appen åpner normalt på `http://127.0.0.1:8501`. Direkte terminaloppstart finner `data/system/Data/`; oppstart via launcheren bruker `%LOCALAPPDATA%\SkiErgPortal\Data\`.

## Datakilder

### Lokale CSV-filer

Legg Concept2 Logbook CSV-eksporter med navnet `concept2-season-*.csv` i appens aktive datamappe. Via launcheren er dette `%LOCALAPPDATA%\SkiErgPortal\Data\`; direkte terminaloppstart bruker `data/system/Data/`. Velg **CSV (system/Data)** i sidepanelet. Alle sesongfilene leses samtidig; avgrens deretter med portalfiltrene.

CSV-filer kan lastes opp for den aktive nettleserøkten. Opplastede filer lagres ikke automatisk i datamappen.

### Concept2 API

Concept2 API er valgt som standard. Via GUI-launcheren skrives en personlig, read-only access token inn i launcherens tokenfelt. Hvis **Husk token lokalt** er valgt, fyller launcheren tokenet inn maskert i portalens API-felt ved oppstart. Et token skrevet bare i Streamlit-sidepanelet lagres ikke.

API-resultater mellomlagres lokalt i `api_cache_skierg.json` i datamappen for raskere senere oppstart.

## Lokal data og personvern

Lokale CSV-filer, API-cache, innstillinger, kommentarer, tagger, laktat og vektdata ligger i datamappen. Via launcheren lagres disse utenfor appinstallasjonen, slik at de overlever oppgraderinger. Ikke commit private data eller token til Git.

Ikke lagre token i kode, Streamlit-konfigurasjon eller filer som deles. Launcherens valg for tokenlagring lagrer det bare lokalt på denne PC-en i brukerens datamappe; del aldri denne mappen. Ved direkte terminaloppstart kan `CONCEPT2_ACCESS_TOKEN` brukes til å forhåndsutfylle tokenfeltet, ellers oppgis tokenet kun for portaløkten.

## Avhengigheter

Runtime-avhengigheter er definert i [`pyproject.toml`](../pyproject.toml) og lases fra `uv.lock`. De viktigste er Streamlit, pandas, Plotly, NumPy, requests, Pillow og `streamlit-aggrid`.
