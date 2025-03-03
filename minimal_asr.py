from transformers import pipeline
import ffmpeg
import os, sys


with open("huginlog.txt", "a") as log_file:
   log_file.write("Skript kjørerrrrrrrr" + "\n")

asr = pipeline("automatic-speech-recognition", "NbAiLab/nb-whisper-medium", device="cpu") # Sett device='cuda' eller device='cpu' om ønskelig

json_tekst = asr("blobber/1740663520586-audio_king.mp3", chunk_length_s=28, return_timestamps=True, generate_kwargs={'num_beams': 5, 'task': 'transcribe', 'language': 'no', 'forced_decoder_ids': 'false'})


print(str("Hallaaaaaaa"))

# Log json_tekst to huginlog.txt
with open("huginlog.txt", "a") as log_file:
 log_file.write(str(json_tekst) + "\n")