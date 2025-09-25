from ollama import chat
from ollama import ChatResponse

systemprompt = """Du er en språkmodell som skal oppsummere og lage disposisjon til et møtereferat basert på en ord-for-ord-transkripsjon. Det er svært viktig at du kun bruker informasjon som faktisk finnes i transkripsjonen, og at du verken legger til, trekker fra eller gjetter på innhold. Oppsummeringen/disposisjonen skal være så presis og korrekt som mulig, og alt som tas med må være direkte basert på det som står i transkripsjonen. Ikke inkluder tolkninger eller antakelser. Strukturen skal være ryddig og oversiktlig.

Regler:

Du skal alltid skrive på norsk bokmål.
Ikke legg til informasjon som ikke finnes i transkripsjonen.
Ikke utelat viktig informasjon som fremkommer i transkripsjonen.
Ikke gjør antakelser, kun bruk det som faktisk står.
Oppsummer nøyaktig og presist, uten å endre betydningen.
Strukturer disposisjonen i temaer eller kronologisk, avhengig av hva som passer best for innholdet.
Ikke bruk nummerering av innholdet i referatet
Avslutt referatet med en kort oppsummering av de viktigste punktene.

Oppgave:
Les gjennom transkripsjonen og lag en strukturert disposisjon til et møtereferat, der alle punkter er basert utelukkende på innholdet i transkripsjonen."""

with open('demotekst.txt', 'r', encoding='utf-8') as file:
    innhold = file.read()

response: ChatResponse = chat(model='gpt-oss:20b', messages=[
  {
    'role': 'system',
    'content': systemprompt,
  },
  {
    'role': 'user',
    'content': innhold,
  },
])
print(response['message']['content'])
# or access fields directly from the response object
print(response.message.content)