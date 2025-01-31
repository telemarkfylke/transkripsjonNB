# Program for å lese film og transkribere lyd for så å legge til undertekster
# Skript for å konvertere m4v- og mp4-filer til mp3-filer
# Deretter brukes ffmpeg til å trekke ut lyden fra videofilene
# Skriptet bruker Nasjonalbibliotekets modell for gjenkjenning av tale
# Les mer om modellen her: https://huggingface.co/NbAiLab/nb-whisper-large
# Les mer om modellen her: https://huggingface.co/NbAiLab/nb-whisper-large
# Telemark fylkeskommune // 2024-2025 // Lisens: CC BY-SA 4.0

import ffmpeg, os
from transformers import pipeline
import json
from datetime import datetime, timedelta

# Definerer kildemappen og destinasjonsmappen
sourcedir = './filmer'
temp_audio_dir = './lyd'
subtitle_dir = './ferdig_tekst'
output_dir = './output'

# Globale variabler
hallusinasjon = False

# Opprett nødvendige mapper hvis de ikke finnes
os.makedirs(temp_audio_dir, exist_ok=True)
os.makedirs(subtitle_dir, exist_ok=True)
os.makedirs(output_dir, exist_ok=True)

# Looper gjennom alle filene i kildemappen
print(os.listdir(sourcedir))
for filename in os.listdir(sourcedir):
    if filename.endswith('.m4v') or filename.endswith('.mp4'):
        input_file = os.path.join(sourcedir, filename)
        audio_file = os.path.join(temp_audio_dir, filename.rsplit('.', 1)[0] + '.mp3')
        subtitle_file = os.path.join(subtitle_dir, filename.rsplit('.', 1)[0] + '.srt')
        output_file = os.path.join(output_dir, filename)

        # Konverter video til MP3
        ffmpeg.input(input_file).output(audio_file, acodec='libmp3lame', format='mp3').run()
        print(f'Hentet ut lyd fra {input_file} og lagret i {audio_file}')

        # Laster inn KI-modellen fra Huggingface
        asr = pipeline("automatic-speech-recognition", "NbAiLab/nb-whisper-medium"y) # Sett CUDA eller CPU

        # Transkriberer lydfilen til tekst i JSON-format
        print(f'Transkriberer lyd fra {audio_file} til tekst. Obs: Dette er en tidkrevende prosess.')
        json_tekst = asr(audio_file, chunk_length_s=28, return_timestamps=True, generate_kwargs={'num_beams': 5, 'task': 'transcribe', 'language': 'no'})

        # Laster inn JSON-dataen
        data = json_tekst
        srt_data = []
        srt_data_vasket = []
        hallusinasjonSjekk = False
 
        # Looper over JSON-rådataen og formaterer den til SRT-format
        for i, item in enumerate(data["chunks"], start=1):
            start_time = datetime.fromtimestamp(item['timestamp'][0]) - timedelta(hours=1)
            end_time = datetime.fromtimestamp(item['timestamp'][1]) - timedelta(hours=1) if item['timestamp'][1] is not None else start_time

            start_time_str = start_time.strftime('%H:%M:%S,%f')[:-3]
            end_time_str = end_time.strftime('%H:%M:%S,%f')[:-3]

            # Lager SRT-strengen og legger den til i listen
            srt_string = f"{i}\n{start_time_str} --> {end_time_str}\n{item['text']}\n"
            srt_data.append(srt_string)

        # Sjekker om det er hallusinasjoner i teksten og fjerner disse (Sånn passe bra)
        for i in range(1, len(srt_data)):
            if srt_data[i].split('\n')[2] == srt_data[i-1].split('\n')[2]:
                hallusinasjonSjekk = True
                # srt_data_vasket.append("x")
            elif hallusinasjonSjekk:
                hallusinasjonSjekk = False
                # srt_data_vasket.append("x")
            else:
                srt_data_vasket.append(srt_data[i-1])
            
        print(srt_data[0].split('\n')[2])
        # Skriver til SRT-fil
        with open(subtitle_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(srt_data_vasket))
        with open('raw.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

        print(f'Transkripsjonen er lagret i {subtitle_file}')

        # Legg til undertekster i videoen
        ffmpeg.input(input_file).output(output_file, vf='subtitles=' + subtitle_file).run()
        print(f'Video med undertekster lagret i {output_file}')
