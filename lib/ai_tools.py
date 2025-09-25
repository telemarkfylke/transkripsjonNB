"""
AI Tools Library for Transcription Service
Provides integration with Ollama for generating meeting summaries and abstracts.
"""

import os
import logging
from typing import Optional, Dict, Any
from ollama import chat, ChatResponse

logger = logging.getLogger(__name__)

def generate_meeting_summary(
    transcription_text: str,
    model: str = "gpt-oss:20b",
    language: str = "norsk bokmål"
) -> Optional[str]:
    """
    Generate a meeting summary using Ollama.

    Args:
        transcription_text: The transcribed text to summarize
        model: Ollama model to use (default: gpt-oss:20b)
        language: Output language (default: norsk bokmål)

    Returns:
        Generated summary text or None if failed
    """

    system_prompt = f"""Du er en språkmodell som skal oppsummere og lage disposisjon til et møtereferat basert på en ord-for-ord-transkripsjon. Det er svært viktig at du kun bruker informasjon som faktisk finnes i transkripsjonen, og at du verken legger til, trekker fra eller gjetter på innhold. Oppsummeringen/disposisjonen skal være så presis og korrekt som mulig, og alt som tas med må være direkte basert på det som står i transkripsjonen. Ikke inkluder tolkninger eller antakelser. Strukturen skal være ryddig og oversiktlig.

Regler:

På starten og slutten av referatet skal det være en kort advarsel om at referatet er KI-generert og basert på en automatisk transkripsjon, og at det kan inneholde feil.
Du skal alltid skrive på {language}.
Ikke legg til informasjon som ikke finnes i transkripsjonen.
Ikke utelat viktig informasjon som fremkommer i transkripsjonen.
Ikke gjør antakelser, kun bruk det som faktisk står.
Oppsummer nøyaktig og presist, uten å endre betydningen.
Strukturer disposisjonen i temaer eller kronologisk, avhengig av hva som passer best for innholdet. Ikke bruke nummerering.
Avslutt referatet med en kort oppsummering av de viktigste punktene og åpne felt der referent og godkjenner kan signere.

Oppgave:
Les gjennom transkripsjonen og lag en strukturert disposisjon til et møtereferat, der alle punkter er basert utelukkende på innholdet i transkripsjonen."""

    try:
        logger.info(f"Generating summary using model: {model}")

        response: ChatResponse = chat(
            model=model,
            messages=[
                {
                    'role': 'system',
                    'content': system_prompt,
                },
                {
                    'role': 'user',
                    'content': transcription_text,
                },
            ]
        )

        # Extract content from response
        if hasattr(response, 'message') and hasattr(response.message, 'content'):
            summary_text = response.message.content
        elif isinstance(response, dict) and 'message' in response:
            summary_text = response['message'].get('content', '')
        else:
            logger.error(f"Unexpected response format from Ollama: {type(response)}")
            return None

        logger.info("Successfully generated meeting summary")
        return summary_text

    except Exception as e:
        logger.error(f"Error generating summary with Ollama: {str(e)}")
        return None


def is_ollama_available(model: str = "gpt-oss:20b") -> bool:
    """
    Check if Ollama service is available and the specified model is accessible.

    Args:
        model: Model name to check

    Returns:
        True if Ollama and model are available, False otherwise
    """
    try:
        # Test with a minimal prompt
        response: ChatResponse = chat(
            model=model,
            messages=[
                {
                    'role': 'user',
                    'content': 'Test',
                },
            ]
        )
        return True
    except Exception as e:
        logger.warning(f"Ollama not available or model '{model}' not found: {str(e)}")
        return False


def get_available_models() -> list:
    """
    Get list of available Ollama models.

    Returns:
        List of available model names, empty list if error
    """
    try:
        from ollama import list as list_models
        models = list_models()
        if isinstance(models, dict) and 'models' in models:
            return [model['name'] for model in models['models']]
        return []
    except Exception as e:
        logger.error(f"Error fetching available models: {str(e)}")
        return []