import json
import logging
import os
import re
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, Field

try:
    import ollama
except ImportError:
    ollama = None


logger = logging.getLogger(__name__)
OLLAMA_MODEL = os.environ.get("LIFEMAP_OLLAMA_MODEL", "gemma3:latest")
OLLAMA_URL = os.environ.get(
    "LIFEMAP_OLLAMA_URL", "http://127.0.0.1:11434/api/chat"
)

# 1. Define the shared data contract verbatim from the workflow document
class LifeNeedsProfile(BaseModel):
    annualIncome: Optional[float] = None
    spouseAnnualIncome: Optional[float] = None
    numberOfDependents: Optional[int] = None
    childrenAges: Optional[List[int]] = Field(default_factory=list)
    mortgageBalance: Optional[float] = None
    otherDebt: Optional[float] = None
    finalExpenses: Optional[float] = None
    desiredAnnualIncome: Optional[float] = None
    incomeReplacementYears: Optional[int] = None
    collegeFundingNeed: Optional[float] = None
    existingLifeInsurance: Optional[float] = None
    availableAssets: Optional[float] = None
    inflationRate: Optional[float] = None
    investmentReturnRate: Optional[float] = None


# Development-only synthetic values; not Lincoln-provided customer data.
DEMO_PROFILE = {
    "annualIncome": 75000,
    "spouseAnnualIncome": 45000,
    "numberOfDependents": 3,
    "childrenAges": [7, 11],
    "mortgageBalance": 180000,
    "otherDebt": 25000,
    "finalExpenses": 15000,
    "desiredAnnualIncome": 50000,
    "incomeReplacementYears": 10,
    "collegeFundingNeed": 80000,
    "existingLifeInsurance": 100000,
    "availableAssets": 50000,
    "inflationRate": 0.02,
    "investmentReturnRate": 0.05,
}

REQUIRED_PROFILE_FIELDS = (
    "mortgageBalance",
    "otherDebt",
    "finalExpenses",
    "desiredAnnualIncome",
    "incomeReplacementYears",
    "collegeFundingNeed",
    "existingLifeInsurance",
    "availableAssets",
)

_MISSING_FIELD_QUESTIONS = {
    "mortgageBalance": "What is your remaining mortgage balance?",
    "otherDebt": "How much other debt should be included?",
    "finalExpenses": "How much would you like to set aside for final expenses?",
    "desiredAnnualIncome": "How much annual income should the plan replace?",
    "incomeReplacementYears": "For how many years should that income be replaced?",
    "collegeFundingNeed": "How much would you like to allocate for education funding?",
    "existingLifeInsurance": "How much life insurance coverage do you already have?",
    "availableAssets": "How much in available assets should be counted toward this need?",
}

_NUMBER_PATTERN = re.compile(
    r"(?<![\w.])(?:\$)?(\d[\d,]*(?:\.\d+)?)\s*"
    r"(k|thousand|m|million|b|billion)?(?!\w)",
    re.IGNORECASE,
)


def get_demo_profile() -> Dict[str, Any]:
    """Return a fresh copy of the synthetic workflow fixture."""
    return dict(DEMO_PROFILE, childrenAges=list(DEMO_PROFILE["childrenAges"]))

def API_request(message: str, conversation: Optional[List[dict]] = None) -> str:
    """Send a chat request to the configured local or cloud Ollama service."""
    if not isinstance(message, str) or not message.strip():
        raise ValueError("A non-empty message is required.")

    messages = [{
        "role": "system",
        "content": (
            "You are LifeMap AI, an educational life-insurance planning assistant. "
            "Be clear and supportive but do not answer in more than 3 sentences. Do not present estimates as quotes or "
            "professional financial advice."
            "Actually help the user plan their life insurance needs instead of being a Q&A bot."
        ),
    }]
    for turn in (conversation or [])[-20:]:
        if (
            isinstance(turn, dict)
            and turn.get("role") in ("user", "assistant")
            and isinstance(turn.get("content"), str)
        ):
            messages.append({
                "role": turn["role"],
                "content": turn["content"],
            })
    if not conversation or messages[-1].get("content") != message:
        messages.append({"role": "user", "content": message})

    headers = {"Content-Type": "application/json"}
    api_key = os.environ.get("OLLAMA_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = Request(
        OLLAMA_URL,
        data=json.dumps({
            "model": OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
        }).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Ollama returned HTTP {error.code}: {detail or error.reason}"
        ) from error
    except URLError as error:
        raise RuntimeError(
            "Could not reach Ollama at "
            f"{request.full_url}. Start Ollama and ensure the model "
            f"{OLLAMA_MODEL} is available."
        ) from error

    reply = _message_content(result).strip()
    if not reply:
        raise RuntimeError("Ollama returned an empty chat response.")
    return reply

def _validated_profile(profile: Optional[dict]) -> Dict[str, Any]:
    return LifeNeedsProfile(**(profile or {})).model_dump(exclude_none=True)


def _message_content(response: Any) -> str:
    if isinstance(response, dict):
        message = response.get("message", {})
        return message.get("content", "") if isinstance(message, dict) else ""

    message = getattr(response, "message", None)
    return getattr(message, "content", "")


def _extract_direct_answer(
    user_input: str, current_profile_state: Optional[dict]
) -> Dict[str, Any]:
    """Use a numeric reply for the currently requested field if possible."""
    profile = _validated_profile(current_profile_state)
    missing_fields = get_missing_required_fields(profile)
    if not missing_fields:
        return profile

    field = missing_fields[0]
    match = _NUMBER_PATTERN.search(user_input)
    if match is None:
        return profile

    value = float(match.group(1).replace(",", ""))
    magnitude = (match.group(2) or "").lower()
    value *= {
        "k": 1_000,
        "thousand": 1_000,
        "m": 1_000_000,
        "million": 1_000_000,
        "b": 1_000_000_000,
        "billion": 1_000_000_000,
    }.get(magnitude, 1)

    if field == "incomeReplacementYears":
        if not value.is_integer():
            return profile
        profile[field] = int(value)
    else:
        profile[field] = value
    return profile


def _chat(messages: List[dict], *, json_mode: bool = False) -> str:
    if ollama is None:
        raise RuntimeError("The Ollama Python package is not installed.")

    chat_options = {"model": OLLAMA_MODEL, "messages": messages}
    if json_mode:
        chat_options["format"] = "json"
    response = ollama.chat(**chat_options)
    return _message_content(response)


def extract_profile_data(
    user_input: str, current_profile_state: Optional[dict] = None
) -> dict:
    """
    Takes natural language input, processes it through Ollama,
    and returns a strictly formatted dictionary for the backend calculator.
    """
    # The system prompt enforces the AI boundary: extract data, do not calculate.
    existing_profile = _validated_profile(current_profile_state)
    try:
        schema = json.dumps(LifeNeedsProfile.model_json_schema(), indent=2)
        system_prompt = (
            "Extract only facts explicitly stated by the user into a JSON object "
            "using the exact LifeNeedsProfile field names and schema below. "
            "Do not calculate insurance needs, infer unstated values, or ask a question. "
            "Omit unknown fields or set them to null.\n"
            f"Schema:\n{schema}"
        )
        content = _chat([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ], json_mode=True)
        extracted_data = json.loads(content)
        if not isinstance(extracted_data, dict):
            raise ValueError("Ollama returned a non-object profile.")

        extracted_profile = LifeNeedsProfile(**extracted_data).model_dump(
            exclude_unset=True, exclude_none=True
        )
        updated_profile = {**existing_profile, **extracted_profile}
        if updated_profile != existing_profile:
            return updated_profile
    except Exception as e:
        logger.warning("Profile extraction failed; trying a direct answer: %s", e)

    fallback_profile = _extract_direct_answer(user_input, existing_profile)
    if fallback_profile != existing_profile:
        return fallback_profile

    raise RuntimeError(
        "Could not extract an answer. Start Ollama with the llama3 model, "
        "or answer the current question with a number (for example, $180,000 or 10 years)."
    )


def get_missing_required_fields(profile: Optional[dict]) -> List[str]:
    """List the calculator inputs that have not yet been supplied."""
    validated_profile = _validated_profile(profile)
    return [
        field
        for field in REQUIRED_PROFILE_FIELDS
        if validated_profile.get(field) is None
    ]


def get_next_question(profile: Optional[dict]) -> Optional[str]:
    """Return the next targeted intake question, or None when intake is complete."""
    missing_fields = get_missing_required_fields(profile)
    return _MISSING_FIELD_QUESTIONS[missing_fields[0]] if missing_fields else None


def _result_value(result: dict, camel_name: str, snake_name: str) -> Any:
    value = result.get(camel_name, result.get(snake_name))
    if isinstance(value, dict):
        return value.get("total")
    return value


def _fallback_explanation(result: dict) -> str:
    coverage = _result_value(
        result, "additionalCoverageNeeded", "additional_coverage_needed"
    )
    if coverage is None:
        return "The calculation result is available, but an explanation could not be generated."

    immediate = _result_value(result, "immediateNeeds", "immediate_needs")
    long_term = _result_value(result, "longTermNeeds", "long_term_needs")
    resources = _result_value(result, "availableResources", "existing_resources")
    if resources is None:
        resources = result.get("available_resources")

    details = []
    if immediate is not None:
        details.append(f"immediate needs of {immediate}")
    if long_term is not None:
        details.append(f"long-term needs of {long_term}")
    if resources is not None:
        details.append(f"available resources of {resources}")
    if details:
        return (
            f"The calculation reports additional coverage needed of {coverage}. "
            f"The reported result includes {', '.join(details)}."
        )
    return f"The calculation reports additional coverage needed of {coverage}."


def explain_result(result: dict) -> str:
    """Explain a backend result without changing or recalculating its values."""
    result_json = json.dumps(result, indent=2)
    try:
        explanation = _chat([
            {
                "role": "system",
                "content": (
                    "Explain the supplied life-insurance needs result in plain language. "
                    "Use only the result's stated values and assumptions. Do not calculate, "
                    "round, alter, or invent any result; make clear this is an estimate."
                ),
            },
            {"role": "user", "content": f"Backend result JSON:\n{result_json}"},
        ])
        if explanation.strip():
            return explanation.strip()
    except Exception:
        logger.exception("Could not explain the backend result with Ollama.")

    return _fallback_explanation(result)

# --- Example usage for the First Vertical Slice ---
if __name__ == "__main__":
    # 1. User sends one natural-language message
    mock_user_message = "I make 75000 a year and my spouse brings in 45000. We have 3 kids, ages 7 and 11. Our mortgage balance is 180000."

    # 2. AI extracts profile fields into a dictionary
    backend_dictionary = extract_profile_data(mock_user_message, get_demo_profile())

    print("Dictionary to send to Backend/Math layer:")
    print(json.dumps(backend_dictionary, indent=2))
    print("Next question:", get_next_question(backend_dictionary))
