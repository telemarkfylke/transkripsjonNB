# transkripsjonNB
Diverse kode for å transkribere med nasjonalbibliotekets variant av WhisperX
Les mer her: https://huggingface.co/NbAiLab

## Installasjon
1. Klon repoet
2. Du trenger Python 3.10.x (Mulig det fungerer med andre versjoner også)
2. Last ned og installer WhisperX fra https://github.com/m-bain/whisperX
3. Du trenger også ffmpeg: https://pypi.org/project/ffmpeg-python/

## Funksjonalitet
```HuginLokalTranskripsjon.py``` settes opp til å kjøre periodisk med en launchctl/crontab eller tilsvarende. Denne vil sjekke om det er nye filer i blobstorage og transkribere disse.
Data mellom lagres på azure blob-storage og lokalt på maskinen som kjører kode. For å sende epost brukes mail-apiet til Telemark fylkeskommune. ToDo: Bruke en logic-app til å sende epost i egent tennant for bedre datasikkerhet.

Programflyten er som følger:
1. Sjekk om det er nye filer i blobstorage
2. Last ned filene
3. Transkriberer filene
4. Sender den transkriberte teksten på epost til innlogget bruker
5. Alle nedlastede og genrerert filer slettes.