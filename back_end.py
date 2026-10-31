import math

# ============================================================
# back_end.py
# Team 0x11 - codeLinc 11
# Life Insurance Needs Assessment Backend
# ============================================================


# ------------------------------------------------------------
# 1. Shared field contract
# ------------------------------------------------------------
# AI_interact.py currently uses camelCase field names.
# The backend uses snake_case internally.
# This map allows both parts of the project to work together.
# ------------------------------------------------------------

AI_TO_BACKEND_FIELDS = {
    "annualIncome": "annual_income",
    "spouseAnnualIncome": "spouse_annual_income",
    "numberOfDependents": "number_of_dependents",
    "childrenAges": "children_ages",
    "mortgageBalance": "mortgage_balance",
    "otherDebt": "other_debt",
    "finalExpenses": "final_expenses",
    "desiredAnnualIncome": "desired_annual_income",
    "incomeReplacementYears": "income_replacement_years",
    "collegeFundingNeed": "college_funding_need",
    "existingLifeInsurance": "existing_life_insurance",
    "availableAssets": "available_assets",
    "inflationRate": "inflation_rate",
    "investmentReturnRate": "investment_return_rate",
}


# ------------------------------------------------------------
# 2. Required calculation fields
# ------------------------------------------------------------

REQUIRED_FIELDS = [
    "mortgage_balance",
    "other_debt",
    "final_expenses",
    "desired_annual_income",
    "income_replacement_years",
    "college_funding_need",
    "existing_life_insurance",
    "available_assets",
]


# ------------------------------------------------------------
# 3. Normalize AI data
# ------------------------------------------------------------

def normalize_profile(profile):
    """
    Accept either camelCase data from the AI layer or
    snake_case data already prepared for the backend.

    Returns a new dictionary using snake_case field names.
    """

    if not isinstance(profile, dict):
        return {}

    normalized = dict(profile)
    # Missing optional assumptions use the same defaults as omitted keys.
    for optional in ("inflation_rate", "investment_return_rate", "inflationRate", "investmentReturnRate"):
        if normalized.get(optional) is None:
            normalized.pop(optional, None)

    for ai_field, backend_field in AI_TO_BACKEND_FIELDS.items():
        if ai_field in normalized and backend_field not in normalized:
            normalized[backend_field] = normalized[ai_field]

    return normalized


# ------------------------------------------------------------
# 4. Validate user financial information
# ------------------------------------------------------------

def validate_profile(profile):
    """
    Validate the information required by the calculator.

    Returns a list describing missing or invalid information.
    An empty list means validation passed.
    """

    profile = normalize_profile(profile)

    problems = []

    # Check required fields.
    for field in REQUIRED_FIELDS:
        if (
            field not in profile
            or profile[field] is None
            or profile[field] == ""
        ):
            problems.append({
                "field": field,
                "reason": "missing"
            })

    # Fields that should contain numeric values.
    numeric_fields = REQUIRED_FIELDS + [
        "annual_income",
        "spouse_annual_income",
        "number_of_dependents",
        "inflation_rate",
        "investment_return_rate",
    ]

    for field in numeric_fields:

        if (
            field not in profile
            or profile[field] is None
            or profile[field] == ""
        ):
            continue

        try:
            value = float(profile[field])

            if isinstance(profile[field], bool) or not math.isfinite(value):
                problems.append({"field": field, "reason": "must be a finite number"})
                continue
            if field in ("inflation_rate", "investment_return_rate") and value > 1:
                problems.append({"field": field, "reason": "must be a fraction between 0 and 1"})
            if field in ("income_replacement_years", "number_of_dependents") and value > 120:
                problems.append({"field": field, "reason": "cannot exceed 120"})
            if value < 0:
                problems.append({
                    "field": field,
                    "reason": "cannot be negative"
                })

        except (TypeError, ValueError):
            problems.append({
                "field": field,
                "reason": "must be a number"
            })

    # Income replacement years should be a whole number.
    if (
        "income_replacement_years" in profile
        and profile["income_replacement_years"] is not None
        and profile["income_replacement_years"] != ""
    ):
        try:
            years = float(profile["income_replacement_years"])

            if not years.is_integer():
                problems.append({
                    "field": "income_replacement_years",
                    "reason": "must be a whole number"
                })

        except (TypeError, ValueError):
            pass

    # Number of dependents should also be a whole number.
    if (
        "number_of_dependents" in profile
        and profile["number_of_dependents"] is not None
        and profile["number_of_dependents"] != ""
    ):
        try:
            dependents = float(profile["number_of_dependents"])

            if not dependents.is_integer():
                problems.append({
                    "field": "number_of_dependents",
                    "reason": "must be a whole number"
                })

        except (TypeError, ValueError):
            pass

    if profile.get("children_ages") is not None:
        ages = profile["children_ages"]
        if not isinstance(ages, list) or len(ages) > 30 or any(
            isinstance(age, bool) or not isinstance(age, int) or not 0 <= age <= 120 for age in ages
        ):
            problems.append({"field": "children_ages", "reason": "must contain whole-number ages from 0 to 120"})
    return problems


# ------------------------------------------------------------
# 5. Main life-insurance needs calculator
# ------------------------------------------------------------


def _invalid_result(profile, validation_problems):
    return {
        "currency": "USD",
        "status": "needs_more_information",

        "additional_coverage_needed": None,

        "immediate_needs": None,
        "long_term_needs": None,
        "total_needs": None,
        "existing_resources": None,

        "calculation": None,

        "assumptions": {
            "inflation_rate": profile.get(
                "inflation_rate",
                0.02
            ),
            "investment_return_rate": profile.get(
                "investment_return_rate",
                0.05
            ),
        },

        "missing_information": validation_problems,

        "explanation_facts": [],
    }

def calculate_life_needs(profile):
    """
    Calculate a life-insurance needs assessment from
    structured user information.

    The backend:
    - validates financial information
    - calculates immediate needs
    - calculates long-term needs
    - calculates total needs
    - subtracts existing resources
    - returns a structured result

    The AI layer should explain the result rather than
    independently calculating a coverage amount.

    IMPORTANT:
    This deterministic calculation is an MVP/reference
    calculation layer. It should not be presented as
    Lincoln Financial's proprietary internal formula.
    """

    # Convert AI camelCase fields to backend snake_case.
    profile = normalize_profile(profile)

    # --------------------------------------------------------
    # Validate before calculating
    # --------------------------------------------------------

    validation_problems = validate_profile(profile)

    if validation_problems:
        return _invalid_result(profile, validation_problems)

    # --------------------------------------------------------
    # Read calculation inputs
    # --------------------------------------------------------

    mortgage_balance = float(
        profile.get("mortgage_balance", 0)
    )

    other_debt = float(
        profile.get("other_debt", 0)
    )

    final_expenses = float(
        profile.get("final_expenses", 0)
    )

    desired_annual_income = float(
        profile.get("desired_annual_income", 0)
    )

    income_replacement_years = int(
        float(profile.get("income_replacement_years", 0))
    )

    college_funding_need = float(
        profile.get("college_funding_need", 0)
    )

    existing_life_insurance = float(
        profile.get("existing_life_insurance", 0)
    )

    available_assets = float(
        profile.get("available_assets", 0)
    )

    inflation_rate = float(
        profile.get("inflation_rate", 0.02)
    )

    investment_return_rate = float(
        profile.get("investment_return_rate", 0.05)
    )

    # --------------------------------------------------------
    # Immediate financial needs
    # --------------------------------------------------------
    # Examples:
    # mortgage
    # other debt
    # final expenses
    # --------------------------------------------------------

    immediate_needs = (
        mortgage_balance
        + other_debt
        + final_expenses
    )

    # --------------------------------------------------------
    # Long-term income replacement
    # --------------------------------------------------------
    # This uses the reference behavior we previously tested:
    #
    # future income grows with inflation
    # and is discounted using the investment return rate.
    #
    # The first year's payment begins at year 0.
    # --------------------------------------------------------

    income_replacement = 0.0

    for year in range(income_replacement_years):

        future_income = (
            desired_annual_income
            * ((1 + inflation_rate) ** year)
        )

        present_value = (
            future_income
            / ((1 + investment_return_rate) ** year)
        )

        income_replacement += present_value

    # --------------------------------------------------------
    # Long-term needs
    # --------------------------------------------------------

    long_term_needs = (
        income_replacement
        + college_funding_need
    )

    # --------------------------------------------------------
    # Total financial needs
    # --------------------------------------------------------

    total_needs = (
        immediate_needs
        + long_term_needs
    )

    # --------------------------------------------------------
    # Existing resources
    # --------------------------------------------------------

    existing_resources = (
        existing_life_insurance
        + available_assets
    )

    # --------------------------------------------------------
    # Additional coverage needed
    # --------------------------------------------------------

    before_minimum = (
        total_needs
        - existing_resources
    )

    additional_coverage_needed = max(
        0,
        before_minimum
    )

    if not all(math.isfinite(value) for value in (immediate_needs, income_replacement,
            long_term_needs, total_needs, existing_resources, before_minimum)):
        return _invalid_result(profile, [{"field": "financial_amounts", "reason": "too large to calculate safely"}])

    # --------------------------------------------------------
    # Return structured result
    # --------------------------------------------------------

    return {
        "currency": "USD",

        "status": "complete",

        "additional_coverage_needed": round(
            additional_coverage_needed,
            2
        ),

        "immediate_needs": {
            "total": round(
                immediate_needs,
                2
            ),

            "items": {
                "mortgage": round(
                    mortgage_balance,
                    2
                ),

                "other_debt": round(
                    other_debt,
                    2
                ),

                "final_expenses": round(
                    final_expenses,
                    2
                ),
            },
        },

        "long_term_needs": {
            "total": round(
                long_term_needs,
                2
            ),

            "items": {
                "income_replacement": round(
                    income_replacement,
                    2
                ),

                "education": round(
                    college_funding_need,
                    2
                ),
            },
        },

        "total_needs": round(
            total_needs,
            2
        ),

        "existing_resources": {
            "total": round(
                existing_resources,
                2
            ),

            "items": {
                "existing_life_insurance": round(
                    existing_life_insurance,
                    2
                ),

                "available_assets": round(
                    available_assets,
                    2
                ),
            },
        },

        "calculation": {
            "formula":
                "total_needs - existing_resources",

            "before_minimum": round(
                before_minimum,
                2
            ),

            "final": round(
                additional_coverage_needed,
                2
            ),
        },

        "assumptions": {
            "income_replacement_years":
                income_replacement_years,

            "inflation_rate":
                inflation_rate,

            "investment_return_rate":
                investment_return_rate,
        },

        "missing_information": [],

        "explanation_facts": [
            (
                "Immediate needs include mortgage, debt, "
                "and final expenses."
            ),
            (
                "Long-term needs include income replacement "
                "and education funding."
            ),
            (
                "Total needs are immediate needs plus "
                "long-term needs."
            ),
            (
                "Existing resources reduce the amount of "
                "additional coverage needed."
            ),
            (
                "Additional coverage cannot be less than zero."
            ),
        ],
    }


# ------------------------------------------------------------
# 6. Development test
# ------------------------------------------------------------
# This section only runs when back_end.py is executed directly.
# It does NOT run when another file imports the backend.
# ------------------------------------------------------------

if __name__ == "__main__":

    # Synthetic development information only.
    # This is NOT real customer data.

    demo_profile = {
        "annualIncome": 75000,
        "spouseAnnualIncome": 45000,
        "numberOfDependents": 3,
        "childrenAges": [7, 11],

        "mortgageBalance": 150000,
        "otherDebt": 0,
        "finalExpenses": 0,

        "desiredAnnualIncome": 45000,
        "incomeReplacementYears": 20,

        "collegeFundingNeed": 0,

        "existingLifeInsurance": 100000,
        "availableAssets": 0,

        "inflationRate": 0.02,
        "investmentReturnRate": 0.05,
    }

    result = calculate_life_needs(demo_profile)

    print("\nBACKEND TEST")
    print("============")

    print(
        "STATUS:",
        result["status"]
    )

    if result["status"] == "complete":

        print(
            "IMMEDIATE:",
            result["immediate_needs"]["total"]
        )

        print(
            "LONG TERM:",
            result["long_term_needs"]["total"]
        )

        print(
            "TOTAL:",
            result["total_needs"]
        )

        print(
            "RESOURCES:",
            result["existing_resources"]["total"]
        )

        print(
            "ADDITIONAL:",
            result["additional_coverage_needed"]
        )

    else:

        print(
            "MISSING:",
            result["missing_information"]
        )
        