# SkiErgportal

Lokal Streamlit-app for analyse av SkiErg-okter fra Concept2 Logbook.

## Kom i gang

1. Installer [Python 3.11 eller nyere](https://www.python.org/downloads/windows/). Hvis Python mangler, apner launcheren automatisk nedlastingssiden.
2. Last ned prosjektet eller klon det fra GitHub.
3. Dobbeltklikk `Trykk her for å starte skiergportal.cmd`.
4. Vent mens appen oppretter et lokalt virtuelt milj&#248; og synkroniserer avhengighetene fra `data/system/pyproject.toml` og `uv.lock` med uv.

Appen apner normalt i nettleseren pa `http://localhost:8501`.

## Last ned Windows-versjonen

Nar en GitHub Release er publisert, last ned `SkiErgPortal-windows-x64.zip` fra [siste release](https://github.com/Teamcereal/skiergportal/releases/latest). Pakk ut hele ZIP-filen til en skrivbar mappe, for eksempel `%LOCALAPPDATA%\Programs\SkiErgPortal`, og start `SkiErgPortal.exe` derfra. Ikke pakk appen ut i `%LOCALAPPDATA%\SkiErgPortal`, som er reservert for brukerdata, og ikke flytt ut EXE-filen alene.

Launcheren varsler nar en nyere versjon er tilgjengelig. Oppdateringen krever bekreftelse og bevarer brukerdataene i `%LOCALAPPDATA%\SkiErgPortal\Data`. Hvis nettverket er utilgjengelig, kan appen fortsatt brukes.

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

For lokal utvikling med hot reload og isolerte testdata, se [Local development](../docs/local-development.md). For Windows-test for merge og planlagt iOS-forstudie, se [release- og plattformplanen](../docs/windows-releases-and-updates.md).

## Personvern ved videreutvikling

F&#248;r du publiserer egne endringer, kontroller at lokale brukerdata og `data/system/.streamlit/secrets.toml` ikke er med i commit-en. Bruk aldri en API-token i kildekode eller i filer som skal deles.

## Windows-bygg

GitHub Actions-workflowen `Windows build` kan startes manuelt fra fanen Actions for testing. Den bygger en ZIP og checksum, starter Streamlit pa en Windows-runner for en helsesjekk og laster opp `SkiErgPortal-windows-x64` som artifact.

For a publisere en release: oppdater versjonen i `data/system/skiergportal_version.py`, merge endringen til `main`, og push en tilsvarende tag, for eksempel `v0.2.0`. Workflowen avviser tagger som ikke matcher versjonen, og oppretter en GitHub Release med ZIP og SHA-256 etter bestatt build og smoke tests.