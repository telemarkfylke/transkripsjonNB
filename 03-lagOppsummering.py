import os, dotenv
from openai import OpenAI
import pprint as pp
from docx import Document

dotenv.load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI()

# Importer srt-fil og legg innholdet i en variabel som heter tekst
undertekstfil = "./ferdig_tekst/<filnavn>.srt"
tekst = ""
språk =input("Hvilket språk skal oppsummeringen lages på? ")
oppsummering = input("Hvilken fil skal oppsummeringen lagres i? ")

with open(undertekstfil, "r") as file:
    tekst = file.read()

# Systeminstruksjon
systeminstruksjon = "Brukeren legger inn en tekst som er en transkripsjon av et møte eller foredrag. Teksten er formater som en srt-undertekstfil. Din oppgave er å lage et korrekt og nøyaktig referat av innholdet. Følg disse instruksene: 1. Det er viktig at oppsummeringen er helt riktig. 2. Skriv overskrifter når det er nytt tema. 3. Oppsummeringen skal være fyldig og beskrive hva det ble snakket om. 4. Oversett eller forklar forkortelser og fagbegreper når disse er vanskelige. 5. Bruk et klart og tydelig språk som er lett å forstå. 6. Oppsummeringen skal være på ca 1500 ord. 7. Oppsummeringen skal være på markdown-format. 8. Oppsummeringen skal være på " + språk + "."


completion = client.chat.completions.create(
  model="gpt-4o",
  messages=[
    {"role": "system", "content": systeminstruksjon},
    {"role": "user", "content": tekst}
  ]
)

pp.pprint(completion.choices[0].message.content)

# Write to markdown file
with open("./oppsummeringer/" + oppsummering + ".md", "w") as file:
    file.write(completion.choices[0].message.content)

# Skriv til docx-fil
doc = Document()
doc.add_paragraph(completion.choices[0].message.content)
doc.save("./oppsummeringer/" + oppsummering + ".docx")