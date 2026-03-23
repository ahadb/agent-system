import json
import re
from sys import exc_info
from typing import Any

import structlog
logger = structlog.get_logger()

def _parse_llm_response(text: str) -> dict[str, Any]:
    """Parse LLM response as JSON. Expects either {tool, kwargs} or {done: true, answer: str}."""
    # Strip markdown code block if present
    text = text.strip()
    if "```json" in text:
        text = re.sub(r"^```json\s*", "", text)
    if "```" in text:
        text = re.sub(r"\s*```\s*$", "", text)
    text = text.strip()
    
    try: 
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error("parse_llm_response failed", error=str(e), raw=text[:500], exc_info=True)
        raise 
