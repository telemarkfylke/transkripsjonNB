# Program for å lese film og transkribere lyd for så å legge til undertekster
# Skript for å konvertere m4v- og mp4-filer til mp3-filer
# Deretter brukes ffmpeg til å trekke ut lyden fra videofilene
# Skriptet bruker Nasjonalbibliotekets modell for gjenkjenning av tale
# Les mer om modellen her: https://huggingface.co/NbAiLab/nb-whisper-large
# Laget av Tom Jarle Christiansen // Telemark fylkeskommune // 2024-2025
# Lisenstype: CC BY-SA 4.0

import ffmpeg, os

input_file = './filmer/Inga.mp4'
output_file = './output/ut.mp4'
subtitle_file = './ferdig_tekst/inga.srt'

# Legg til undertekster i videoen
ffmpeg.input(input_file).output(output_file, vf='subtitles=' + subtitle_file,  t=600).run()
print(f'Video med undertekster lagret i {output_file}')
