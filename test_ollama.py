from ollama import chat
from ollama import ChatResponse
import os
from datetime import datetime

# System prompt for meeting summarization
# systemprompt = """Du er en språkmodell som skal oppsummere og lage et møtereferat basert på en ord-for-ord-transkripsjon. Det er svært viktig at du kun bruker informasjon som faktisk finnes i transkripsjonen, og at du verken legger til, trekker fra eller gjetter på innhold. Oppsummeringen/disposisjonen skal være så presis og korrekt som mulig, og alt som tas med må være direkte basert på det som står i transkripsjonen. Ikke inkluder tolkninger eller antakelser. Strukturen skal være ryddig og oversiktlig.

# Regler:

# Du skal alltid skrive på norsk bokmål.
# Ikke legg til informasjon som ikke finnes i transkripsjonen.
# Ikke utelat viktig informasjon som fremkommer i transkripsjonen.
# Ikke gjør antakelser, kun bruk det som faktisk står.
# Oppsummer nøyaktig og presist, uten å endre betydningen.
# Strukturer referatet med klare overskrifter som beskriver temaene som diskuteres.
# Ikke bruk Markdown eller annen formatering i teksten. Kun ren tekst.
# Avslutt referatet med en kort oppsummering av de viktigste punktene.

# Oppgave:
# Les gjennom transkripsjonen og lag en referat som følger reglene ovenfor. Sørg for at referatet er lett å lese og forstå, og at det gir en klar oversikt over hva som ble diskutert i møtet."""

systemprompt = "Du skal lage et nøyaktig og presist sammendrag av teksten jeg gir deg. Sammendraget skal være på norsk bokmål og skal ikke inneholde informasjon som ikke finnes i teksten. Ikke legg til, trekk fra eller gjet informasjon. Strukturer sammendraget med klare overskrifter som beskriver hovedtemaene i teksten. Ikke bruk Markdown eller annen formatering, kun ren tekst. Viktig: Skriv en kort notis i starten av sammendraget for å opplysee om at dette er et sammendrag generert av en ki/språkmodell og kan inneholde feil eller unøyaktigheter, og at brukererns ansvar å verifisere informasjonen."

# Models to test
models = [
    'gpt-oss:20b',
    'llama3.2:latest',
    'mistral-small:latest',
    'deepseek-r1:14b'
]

# Read the demo text
with open('demotekst.txt', 'r', encoding='utf-8') as file:
    innhold = file.read()

# Create output directory if it doesn't exist
os.makedirs('comp_summaries', exist_ok=True)

# Test each model
for model in models:
    print(f"\n{'='*60}")
    print(f"Testing model: {model}")
    print(f"{'='*60}")

    try:
        print(f"Generating summary with {model}...")
        # Generate summary with current model
        response: ChatResponse = chat(model=model, messages=[
            {
                'role': 'system',
                'content': systemprompt,
            },
            {
                'role': 'user',
                'content': innhold,
            },
        ])

        # Get the summary content
        summary_content = response.message.content

        # Print summary to console
        print(f"\nSummary from {model}:")
        print("-" * 40)
        print(summary_content)

        # Save summary to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"comp_summaries/summary_{model.replace(':', '_').replace('.', '_')}_{timestamp}.txt"

        with open(filename, 'w', encoding='utf-8') as output_file:
            output_file.write(f"Model: {model}\n")
            output_file.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            output_file.write(f"{'='*60}\n\n")
            output_file.write(summary_content)

        print(f"\nSummary saved to: {filename}")

    except Exception as e:
        error_msg = f"Error with model {model}: {str(e)}"
        print(f"\n❌ {error_msg}")

        # Save error to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"comp_summaries/ERROR_{model.replace(':', '_').replace('.', '_')}_{timestamp}.txt"

        with open(filename, 'w', encoding='utf-8') as error_file:
            error_file.write(f"Model: {model}\n")
            error_file.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            error_file.write(f"{'='*60}\n\n")
            error_file.write(f"ERROR: {str(e)}")

print(f"\n{'='*60}")
print("Model comparison completed!")
print("Check the 'comp_summaries' folder for individual summary files.")
print(f"{'='*60}")