"""Chat boundaries: capture facts and explain results; calculator owns all math."""
import json
import math
import re
from AI_interact import LifeNeedsProfile, _chat

FIELDS = set(LifeNeedsProfile.model_fields)
COUNTS = {"numberOfDependents", "incomeReplacementYears"}
RATES = {"inflationRate", "investmentReturnRate"}


def clean_profile(value):
    if not isinstance(value, dict):
        raise ValueError("Profile must be an object.")
    result = {}
    for key, item in value.items():
        if key not in FIELDS or item is None:
            continue
        if key == "childrenAges":
            if not isinstance(item, list) or len(item) > 30 or any(
                isinstance(age, bool) or not isinstance(age, int) or not 0 <= age <= 120 for age in item
            ):
                raise ValueError("Children's ages must be whole numbers from 0 to 120.")
        elif isinstance(item, bool) or not isinstance(item, (float, int)) or not math.isfinite(item) or item < 0:
            raise ValueError("Profile values must be non-negative numbers.")
        elif key in COUNTS and (int(item) != item or item > 120):
            raise ValueError("Counts must be whole numbers from 0 to 120.")
        elif key in RATES and item > 1:
            raise ValueError("Rates must be fractions between 0 and 1.")
        result[key] = item
    return result


def clean_context(value):
    if not isinstance(value, dict):
        raise ValueError("Context must be an object.")
    result = {"profile": clean_profile(value.get("profile", {})), "resultSource": value.get("resultSource", "mock")}
    result["profileSource"] = value.get("profileSource", "confirmed")
    if result["profileSource"] not in ("example", "confirmed"):
        raise ValueError("Invalid profile source.")
    if result["resultSource"] not in ("mock", "backend"):
        raise ValueError("Invalid result source.")
    calculation = value.get("result")
    preferences = value.get("preferences", {})
    if not isinstance(preferences, dict):
        raise ValueError("Preferences must be an object.")
    budget = preferences.get("monthlyBudget")
    if budget is not None:
        if isinstance(budget, bool) or not isinstance(budget, (int,float)) or not math.isfinite(budget) or budget < 0:
            raise ValueError("Monthly budget must be a non-negative amount.")
        result["preferences"] = {"monthlyBudget": budget}
    learning = value.get("learning")
    if learning is not None:
        if not isinstance(learning,dict): raise ValueError("Invalid learning context.")
        result["learning"] = {}
        for key in ("topic", "title", "explanation", "question", "why"):
            text = learning.get(key)
            if text is not None:
                if not isinstance(text,str) or len(text)>3000: raise ValueError("Invalid learning text.")
                result["learning"][key] = text
    simulation = value.get("simulation")
    if simulation is not None:
        if not isinstance(simulation,dict): raise ValueError("Invalid simulation context.")
        result["simulation"] = {"changes":clean_profile(simulation.get("changes",{}))}
        for key in ("policyYears","proposedCoverage"):
            item=simulation.get(key)
            if isinstance(item,bool) or not isinstance(item,(int,float)) or not math.isfinite(item) or item<0: raise ValueError("Invalid simulation number.")
            result["simulation"][key]=item
        points=simulation.get("timeline",[])
        if not isinstance(points,list) or len(points)>10: raise ValueError("Invalid timeline.")
        result["simulation"]["timeline"] = []
        for point in points:
            if not isinstance(point,dict): raise ValueError("Invalid timeline point.")
            clean={}
            for key in ("year","additionalNeed","proposedCoverage","remainingGap"):
                item=point.get(key)
                if isinstance(item,bool) or not isinstance(item,(int,float)) or not math.isfinite(item) or item<0: raise ValueError("Invalid timeline amount.")
                clean[key]=item
            result["simulation"]["timeline"].append(clean)
    if calculation is not None:
        if not isinstance(calculation, dict):
            raise ValueError("Result must be an object.")
        result["result"] = {}
        if calculation.get("calculator") == "team-reference":
            result["result"]["calculator"] = "team-reference"
        assumptions = calculation.get("assumptions", [])
        if not isinstance(assumptions,list) or len(assumptions)>20 or any(not isinstance(text,str) or len(text)>1000 for text in assumptions):
            raise ValueError("Invalid calculator assumptions.")
        result["result"]["assumptions"] = assumptions
        for key in ("immediateNeeds", "longTermNeeds", "totalNeeds", "availableResources", "additionalCoverageNeeded"):
            item = calculation.get(key)
            if isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(item) or item < 0:
                raise ValueError("Invalid calculator result.")
            result["result"][key] = item
        breakdown = calculation.get("breakdown", [])
        if not isinstance(breakdown, list) or len(breakdown) > 30:
            raise ValueError("Invalid breakdown.")
        result["result"]["breakdown"] = []
        for item in breakdown:
            if not isinstance(item, dict) or not isinstance(item.get("label"), str) or len(item["label"]) > 200:
                raise ValueError("Invalid breakdown label.")
            amount = item.get("amount")
            if isinstance(amount, bool) or not isinstance(amount, (int, float)) or not math.isfinite(amount) or amount < 0:
                raise ValueError("Invalid breakdown amount.")
            result["result"]["breakdown"].append({"label": item["label"], "amount": amount})
    return result


def capture_intake(message, profile, field):
    profile = clean_profile(profile)
    if field is not None and field not in FIELDS:
        raise ValueError("Unknown intake field.")
    prompt = (
        "Extract only facts explicitly stated in the user's latest message. Return ONLY a JSON object with "
        "updates (an object of changed LifeNeedsProfile fields) and help (a short plain-language explanation if the user asks a question or is unsure). "
        "For a question, updates must be empty; explain the current concept calmly and ask one focused question. Never calculate coverage or infer facts. "
        "Use null or omit unknown fields. A bare numeric answer refers to the current question field. "
        "If a message is a question or ambiguous, leave updates empty. Convert explicitly stated monthly income "
        "to annual income, k to thousands, and percentages to fractional rates. No negative values. "
        "Children's ages must be an array of integers. Corrections replace previous field values. "
        "Saying no mortgage means mortgageBalance=0; no children means childrenAges=[]; "
        "do not assume no other dependents. Schema: " + json.dumps(LifeNeedsProfile.model_json_schema())
    )
    raw = _chat([
        {"role": "system", "content": prompt},
        {"role": "user", "content": json.dumps({"currentField": field, "confirmedProfile": profile, "latestMessage": message})},
    ], json_mode=True)
    try:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = re.sub(r"\A```(?:json)?\s*|\s*```\Z", "", raw)
        parsed = json.loads(raw)
        updates = clean_profile(parsed.get("updates", parsed) if isinstance(parsed,dict) else parsed)
    except (ValueError, TypeError) as error:
        raise RuntimeError("I couldn't confidently read those details. Please rephrase your answer.") from error
    if not updates:
        help_text = parsed.get("help", "")
        if not isinstance(help_text,str) or len(help_text)>1000: help_text=""
        return {"updates": {}, "reply": help_text or "I haven't changed your information. Please answer the current question with an amount or number, or edit your details in Review."}
    return {"updates": updates, "reply": "Please confirm the details below before I add them to your plan."}
