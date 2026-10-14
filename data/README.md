# SkiErgportal

Lokal Streamlit-app for analyse av SkiErg-okter fra Concept2 Logbook.

## Kom i gang

1. Installer [Python 3.11 eller nyere](https://www.python.org/downloads/windows/). Hvis Python mangler, apner launcheren automatisk nedlastingssiden.
2. Last ned prosjektet eller klon det fra GitHub.
3. Dobbeltklikk `Trykk her for å starte skiergportal.cmd`.
4. Vent mens appen oppretter et lokalt virtuelt milj&#248; og synkroniserer avhengighetene fra `data/system/pyproject.toml` og `uv.lock` med uv.

Appen apner normalt i nettleseren pa `http://localhost:8501`.

## Legg til dine data

Velg en av datakildene i appen:

- Eksporter Concept2 Logbook-data som CSV og legg filene i `%LOCALAPPDATA%\SkiErgPortal\Data\` med navn som `concept2-season-2026.csv`.
- Oppgi din egen read-only Concept2 access token i portalen for a hente data fra API-et. Tokenet lagres ikke av portalen.

Alle data lagres bare lokalt pa din maskin. Launcheren flytter eksisterende filer fra `data/system/Data/` til `%LOCALAPPDATA%\SkiErgPortal\Data\` ved forste oppstart. Denne mappen ligger utenfor appinstallasjonen, sa CSV-filer, kommentarer, laktat, vekt, cache og token overlever oppgraderinger.

## Manuell oppstart

```powershell
cd data\system
uv sync --frozen
uv run --frozen streamlit run treningshistorikk_app/app.py
```

## Personvern ved videreutvikling

F&#248;r du publiserer egne endringer, kontroller at lokale brukerdata og `data/system/.streamlit/secrets.toml` ikke er med i commit-en. Bruk aldri en API-token i kildekode eller i filer som skal deles.

## Windows-bygg

GitHub Actions-workflowen `Windows build` kan startes manuelt fra fanen Actions. Den bygger en PyInstaller `--onedir`-distribusjon, starter Streamlit pa en Windows-runner for en helsesjekk og laster opp `SkiErgPortal-windows-x64` som artifact. Pakk ut hele mappen og start `SkiErgPortal.exe`. Brukerdata lagres separat i `%LOCALAPPDATA%\SkiErgPortal\Data` og blir ikke pakket inn i bygget.