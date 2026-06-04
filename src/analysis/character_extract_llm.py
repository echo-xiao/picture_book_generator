"""Character extraction using Gemini LLM.

More accurate than spaCy NER for literary texts, especially older/complex prose.
Extracts characters with names, roles, appearance, personality, and relationships.
"""

import json
import logging
from typing import Any

from src.agent.gemini_client import generate_json

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """\
You are a literary analyst. Extract ALL named characters from the given text.
Be precise — only extract actual PEOPLE, not places, objects, or abstract concepts.
For each character, provide accurate details based ONLY on what the text says."""

EXTRACT_PROMPT = """\
Extract ALL named characters from this text. For each character provide:

## Text
{text}

## Output Format
Return JSON:
{{
  "characters": [
    {{
      "name": "Full canonical name (e.g., 'Sydney Carton', not just 'Carton')",
      "aliases": ["other names or titles used for this character"],
      "role": "main" or "supporting" or "minor",
      "appearance_description": ["physical descriptions from the text"],
      "personality_traits": ["key personality traits shown in the text"],
      "background": "1-2 sentence summary of who this character is and what they do in the story",
      "relationships": {{"other_character_name": "relationship description"}},
      "mention_count_estimate": approximate number of times mentioned
    }}
  ]
}}

RULES:
- Only extract REAL PEOPLE characters, not places, objects, or concepts
- "role" is "main" if they drive the plot, "supporting" if they appear in multiple scenes, "minor" if brief appearance
- Use the character's most common/full name as "name"
- Include ALL aliases (nicknames, titles, shortened names)
- appearance_description should quote or closely paraphrase the text
- Do NOT invent details not in the text
"""


def extract_characters_llm(
    text: str,
    chapters: list[dict] | None = None,
) -> list[dict]:
    """Extract characters using Gemini LLM.

    Args:
        text: Full text or chapter text to analyze.
        chapters: Optional chapter list (uses first few + last for context).

    Returns:
        List of character dicts compatible with the rest of the pipeline.
    """
    # For very long texts, sample beginning + middle + end
    if len(text) > 30000:
        chunk_size = 10000
        beginning = text[:chunk_size]
        middle_start = len(text) // 2 - chunk_size // 2
        middle = text[middle_start:middle_start + chunk_size]
        ending = text[-chunk_size:]
        sample = (
            f"[BEGINNING OF BOOK]\n{beginning}\n\n"
            f"[MIDDLE OF BOOK]\n{middle}\n\n"
            f"[END OF BOOK]\n{ending}"
        )
    else:
        sample = text

    prompt = EXTRACT_PROMPT.format(text=sample[:40000])

    try:
        result = generate_json(prompt, system_instruction=SYSTEM_INSTRUCTION)
    except Exception as e:
        logger.error("Gemini character extraction failed: %s", e)
        return []

    characters = result.get("characters", [])

    # Convert to pipeline-compatible format
    output = []
    for i, char in enumerate(characters):
        name = char.get("name", "").strip()
        if not name or len(name) < 2:
            continue

        output.append({
            "name": name,
            "aliases": char.get("aliases", []),
            "role": char.get("role", "minor"),
            "mention_count": char.get("mention_count_estimate", 1),
            "first_appearance": 0,
            "co_occurring_characters": {
                k: 1 for k in char.get("relationships", {}).keys()
            },
            # Extended fields for character sheets
            "appearance_description": char.get("appearance_description", []),
            "personality_traits": char.get("personality_traits", []),
            "background": char.get("background", f"A character in the story."),
            "relationships": char.get("relationships", {}),
        })

    logger.info("Gemini extracted %d characters", len(output))
    return output
