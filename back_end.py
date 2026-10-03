def calculate_life_needs(profile):
    """
    Calculate a life-insurance needs assessment from structured user data.

    The backend is responsible for:
    - validating financial inputs
    - calculating immediate needs
    - calculating long-term needs
    - calculating total needs
    - subtracting existing resources
    - returning a consistent result structure

    AI should explain these results, not calculate them.
    """

    # -----------------------------
    # 1. Read user financial inputs
    # -----------------------------

    mortgage_balance = float(profile.get("mortgage_balance", 0))
    other_debt = float(profile.get("other_debt", 0))
    final_expenses = float(profile.get("final_expenses", 0))

    desired_annual_income = float(
        profile.get("desired_annual_income", 0)
    )

    income_replacement_years = int(
        profile.get("income_replacement_years", 0)
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

    # -----------------------------
    # 2. Immediate needs
    # -----------------------------

    immediate_needs = (
        mortgage_balance
        + other_debt
        + final_expenses
    )

    # -----------------------------
    # 3. Long-term income need
    # -----------------------------

    income_replacement = 0

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

    long_term_needs = (
        income_replacement
        + college_funding_need
    )

    # -----------------------------
    # 4. Total needs
    # -----------------------------

    total_needs = (
        immediate_needs
        + long_term_needs
    )

    # -----------------------------
    # 5. Existing resources
    # -----------------------------

    existing_resources = (
        existing_life_insurance
        + available_assets
    )

    # -----------------------------
    # 6. Additional coverage
    # -----------------------------

    before_minimum = (
        total_needs
        - existing_resources
    )

    additional_coverage_needed = max(
        0,
        before_minimum
    )

    # -----------------------------
    # 7. Return structured result
    # -----------------------------

    return {
        "currency": "USD",

        "additional_coverage_needed":
            round(additional_coverage_needed, 2),

        "immediate_needs": {
            "total": round(immediate_needs, 2),

            "items": {
                "mortgage": round(mortgage_balance, 2),
                "other_debt": round(other_debt, 2),
                "final_expenses": round(final_expenses, 2)
            }
        },

        "long_term_needs": {
            "total": round(long_term_needs, 2),

            "items": {
                "income_replacement":
                    round(income_replacement, 2),

                "education":
                    round(college_funding_need, 2)
            }
        },

        "total_needs":
            round(total_needs, 2),

        "existing_resources": {
            "total": round(existing_resources, 2),

            "items": {
                "existing_life_insurance":
                    round(existing_life_insurance, 2),

                "available_assets":
                    round(available_assets, 2)
            }
        },

        "calculation": {
            "formula":
                "total_needs - existing_resources",

            "before_minimum":
                round(before_minimum, 2),

            "final":
                round(additional_coverage_needed, 2)
        },

        "assumptions": {
            "income_replacement_years":
                income_replacement_years,

            "inflation_rate":
                inflation_rate,

            "investment_return_rate":
                investment_return_rate
        },

        "missing_information": [],

        "explanation_facts": [
            "Immediate needs include mortgage, debt, and final expenses.",
            "Long-term needs include income replacement and education funding.",
            "Existing resources reduce the amount of additional coverage needed."
        ]
    }