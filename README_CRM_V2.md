# Dato skrevet: 23.06.2026
# Forfatter: William Berg Steffenak - copyright
# Lokal CRM V3.2 Layout

## Hva som er endret
- Mer arbeidsflate-basert navigasjon i stedet for mange like tekniske faner
- Teknisk støy redusert: ID-er og metadata skjules som standard i datavisning
- Kundekort, oppdragskort, salg, drift og fakturering er gruppert mer naturlig
- Eksport beholdt, men filnavn er mer lesbare enn før
- Valgfri toggle for å vise tekniske ID-er ved behov

## Designprinsipp for ID-er
- ID-er brukes fortsatt i databasen og interne koblinger
- ID-er skal bare vises i brukergrensesnittet når de er nyttige for feilsøking, eksport eller entydig valg
- I daglig bruk er navn, adresse, status, pris og dato mer nyttig enn UUID-er

## Kjøring
```bash
python3 -m pip install -r requirements.txt
python3 -m streamlit run app_v32_layout.py
```
