# LifeMap challenge alignment

Based on the supplied 2026 codeLinc 11 opening presentation, Life Insurance path (slides 15 and 17–19). Event registration and tooling instructions in the deck are context, not app requirements.

- Conversational needs assessment: empty profile → stated facts → confirmation → review. Questions cover financial dependents, income-support goals, debts, education and existing resources.
- Personalized math: the existing team reference calculator owns the arithmetic. The adapter exposes its result and explains immediate needs, income/education support and subtraction of resources. It is not represented as Lincoln’s proprietary formula.
- Calm explanations: AI uses verified calculator amounts, avoids fear or sales pressure, and separates estimates from policy quotes.
- Product understanding: AI mini-lessons cover term and permanent coverage, time horizons and affordability. Whole life is presented as a type of permanent coverage. The optional budget is teaching context, not a premium quote.
- Connected exploration: users can learn first or build first, return to their plan, change inputs and try life events. The simulator explains potential beneficiary support after a covered death, not investment income generated when coverage starts.
- Projection boundaries: fewer remaining years of income support; other financial values held constant unless edited; proposed additional coverage expires at the entered duration. Existing insurance expiry, loan amortization, cash values, underwriting and premiums are not modeled.

The public Lincoln resources linked in the presentation are available from the lessons. The internal presentation itself is not published as a website asset.

Remaining external dependency: the teammate’s Lincoln calculator integration. Replace the calculation owner at `calculator_bridge.py` or configure the agreed backend endpoints; do not replace it with AI-generated financial numbers.
