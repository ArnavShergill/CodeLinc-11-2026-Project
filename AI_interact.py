import json
import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ValidationError

try:
    import ollama
except ImportError:
    ollama = None


logger = logging.getLogger(__name__)

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


def get_demo_profile() -> Dict[str, Any]:
    """Return a fresh copy of the synthetic workflow fixture."""
    return dict(DEMO_PROFILE, childrenAges=list(DEMO_PROFILE["childrenAges"]))


def _validated_profile(profile: Optional[dict]) -> Dict[str, Any]:
    return LifeNeedsProfile(**(profile or {})).model_dump(exclude_none=True)


def _message_content(response: Any) -> str:
    if isinstance(response, dict):
        message = response.get("message", {})
        return message.get("content", "") if isinstance(message, dict) else ""

    message = getattr(response, "message", None)
    return getattr(message, "content", "")


def _chat(messages: List[dict], *, json_mode: bool = False) -> str:
    if ollama is None:
        raise RuntimeError("The Ollama Python package is not installed.")

    chat_options = {"model": "llama3", "messages": messages}
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
    try:
        existing_profile = _validated_profile(current_profile_state)
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
        return {**existing_profile, **extracted_profile}
    except (json.JSONDecodeError, ValidationError, TypeError, ValueError, RuntimeError):
        logger.exception("Could not extract a profile from the user message.")
        try:
            return _validated_profile(current_profile_state)
        except (ValidationError, TypeError):
            return {}
    except Exception as e:
        logger.exception("Ollama profile extraction failed: %s", e)
        try:
            return _validated_profile(current_profile_state)
        except (ValidationError, TypeError):
            return {}


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