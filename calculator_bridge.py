"""Expose the team's existing reference calculator without changing its formulas.

Replace calculate_life_needs at this boundary when the Lincoln integration lands.
"""
import math
from back_end import calculate_life_needs
from chat_features import clean_profile

SCENARIO_FIELDS = {
    'child': {'numberOfDependents', 'collegeFundingNeed', 'desiredAnnualIncome'},
    'home': {'mortgageBalance'},
    'income': {'annualIncome', 'desiredAnnualIncome'},
    'debt': {'otherDebt'},
    'married': {'spouseAnnualIncome', 'desiredAnnualIncome'},
}


def calculate(profile):
    profile = clean_profile(profile)
    raw = calculate_life_needs(profile)
    if raw['status'] != 'complete':
        fields = ', '.join(item['field'] for item in raw['missing_information'])
        raise ValueError('Please complete these planning details: ' + fields)
    immediate = raw['immediate_needs']; long_term = raw['long_term_needs']
    result = {
        'immediateNeeds': immediate['total'], 'longTermNeeds': long_term['total'],
        'totalNeeds': raw['total_needs'], 'availableResources': raw['existing_resources']['total'],
        'additionalCoverageNeeded': raw['additional_coverage_needed'],
        'breakdown': [
            {'label': 'Mortgage', 'amount': immediate['items']['mortgage']},
            {'label': 'Other debt', 'amount': immediate['items']['other_debt']},
            {'label': 'Final expenses', 'amount': immediate['items']['final_expenses']},
            {'label': 'Income support', 'amount': long_term['items']['income_replacement']},
            {'label': 'Education goals', 'amount': long_term['items']['education']},
        ],
        'assumptions': [
            'Calculated from your confirmed inputs by the team reference calculator; this is not Lincoln’s proprietary calculator or a policy quote.',
            f"Income support lasts {profile['incomeReplacementYears']} years at ${profile['desiredAnnualIncome']:,.0f} per year before the calculator's inflation/return adjustment.",
            f"Inflation assumption: {profile.get('inflationRate', .02):.6%}; investment return assumption: {profile.get('investmentReturnRate', .05):.6%}. These are assumptions, not promised returns.",
            'Existing insurance and available assets are counted separately from the additional coverage estimate.',
            'Annual salary and dependent count are context; this calculator uses your explicitly chosen income-support and education amounts rather than deriving them from salary or family size.',
        ],
        'calculator': 'team-reference',
    }
    if any(not math.isfinite(result[key]) for key in ('totalNeeds','availableResources','additionalCoverageNeeded','immediateNeeds','longTermNeeds')):
        raise ValueError('The amounts are too large to calculate. Please review your inputs.')
    return result


def simulate(profile, scenario=None, changes=None, proposed_coverage=None, policy_years=None):
    base = clean_profile(profile)
    updates = clean_profile(changes or {})
    if updates and (scenario not in SCENARIO_FIELDS or not set(updates).issubset(SCENARIO_FIELDS[scenario])):
        raise ValueError('Only the selected life-event fields can change in this scenario.')
    updated = {**base, **updates}
    current = calculate(base); result = calculate(updated)
    coverage = current['additionalCoverageNeeded'] if proposed_coverage is None else proposed_coverage
    if isinstance(coverage, bool) or not isinstance(coverage, (int,float)) or not math.isfinite(coverage) or coverage < 0:
        raise ValueError('Proposed additional coverage must be a non-negative amount.')
    policy_years = max(1,base['incomeReplacementYears']) if policy_years is None else policy_years
    if isinstance(policy_years, bool) or not isinstance(policy_years, int) or not 1 <= policy_years <= 120:
        raise ValueError('The modeled policy duration must be between 1 and 120 whole years.')
    timeline = []
    for elapsed in (0,5,10,15,20):
        future = {**updated, 'incomeReplacementYears': max(0, updated['incomeReplacementYears'] - elapsed)}
        future_result = calculate(future)
        in_force_coverage = coverage if elapsed < policy_years else 0
        timeline.append({'year':elapsed, 'additionalNeed':future_result['additionalCoverageNeeded'],
                         'proposedCoverage':in_force_coverage,
                         'remainingGap':max(0,round(future_result['additionalCoverageNeeded']-in_force_coverage,2))})
    return {'scenario':scenario, 'result':result, 'baseResult':current, 'profile':updated, 'changes':updates,
            'proposedCoverage':coverage, 'policyYears':policy_years, 'timeline':timeline,
            'assumptions':[
                'This is a conditional planning illustration, not a prediction or guaranteed outcome.',
                'The same team reference calculator is rerun with fewer remaining years of income support. Dollar inputs are held at their present planning values.',
                'Mortgage, other debts, education goals, available assets, and existing insurance remain unchanged unless you explicitly change them. No automatic loan payoff or investment growth is assumed.',
                f'The proposed additional policy amount is held constant for {policy_years} years and shown as zero after that modeled duration. Existing coverage is held constant; its actual expiry is not modeled.',
                'Coverage is potential support for beneficiaries after a covered death while a policy is in force and a claim is payable. It is not income received simply for owning a policy.',
                'Premium affordability, underwriting, policy exclusions, cash value, and actual products are not calculated here.',
            ]}
