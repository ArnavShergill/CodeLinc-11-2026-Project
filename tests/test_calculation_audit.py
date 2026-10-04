"""Independent formula checks and deterministic scenario regressions. Synthetic data only."""
import copy
import math
import unittest
from unittest.mock import patch
from AI_interact import get_demo_profile, REQUIRED_PROFILE_FIELDS, chat_turn
from back_end import calculate_life_needs, normalize_profile
from calculator_bridge import calculate, simulate

class CalculationAuditTests(unittest.TestCase):
    def profile(self, **updates):
        return {**get_demo_profile(), **updates}

    def test_reference_components_and_independent_geometric_sum(self):
        p=self.profile();raw=calculate_life_needs(p);r=calculate(p)
        ratio=(1+p['inflationRate'])/(1+p['investmentReturnRate'])
        support=p['desiredAnnualIncome']*(1-ratio**p['incomeReplacementYears'])/(1-ratio)
        self.assertEqual(round(support,2),440375.55)
        self.assertEqual(raw['long_term_needs']['items']['income_replacement'],round(support,2))
        self.assertEqual(r['immediateNeeds'],220000)
        self.assertEqual(r['longTermNeeds'],520375.55)
        self.assertEqual(r['totalNeeds'],740375.55)
        self.assertEqual(r['availableResources'],150000)
        self.assertEqual(r['additionalCoverageNeeded'],590375.55)
        self.assertEqual(sum(item['amount'] for item in r['breakdown']),r['totalNeeds'])
        self.assertEqual(raw['existing_resources']['items'],{'existing_life_insurance':100000,'available_assets':50000})

    def test_year_zero_payment_and_equal_rates(self):
        for years in (0,1,10,120):
            p=self.profile(desiredAnnualIncome=45000,incomeReplacementYears=years,inflationRate=.03,investmentReturnRate=.03)
            self.assertEqual(calculate_life_needs(p)['long_term_needs']['items']['income_replacement'],45000*years)
        p=self.profile(incomeReplacementYears=1,inflationRate=.99,investmentReturnRate=0)
        self.assertEqual(calculate_life_needs(p)['long_term_needs']['items']['income_replacement'],50000)

    def test_each_need_and_resource_maps_without_double_counting(self):
        zero={field:0 for field in REQUIRED_PROFILE_FIELDS}
        for field in ('mortgageBalance','otherDebt','finalExpenses','collegeFundingNeed'):
            r=calculate({**zero,field:12345.67})
            self.assertEqual(r['totalNeeds'],12345.67)
            self.assertEqual(r['additionalCoverageNeeded'],12345.67)
        for field in ('existingLifeInsurance','availableAssets'):
            r=calculate({**zero,'mortgageBalance':20000,field:12000})
            self.assertEqual(r['availableResources'],12000)
            self.assertEqual(r['additionalCoverageNeeded'],8000)

    def test_zero_excess_resources_and_no_negative_gap(self):
        self.assertEqual(calculate({field:0 for field in REQUIRED_PROFILE_FIELDS})['additionalCoverageNeeded'],0)
        p=self.profile(existingLifeInsurance=2000000,availableAssets=2000000)
        self.assertEqual(calculate(p)['additionalCoverageNeeded'],0)
        self.assertTrue(all(point['remainingGap']==0 for point in simulate(p)['timeline']))

    def test_determinism_and_no_input_mutation(self):
        p=self.profile();original=copy.deepcopy(p)
        first=calculate(p)
        for _ in range(20):self.assertEqual(calculate(p),first)
        simulate(p,'home',{'mortgageBalance':250000})
        self.assertEqual(p,original)

    def test_camel_and_snake_contracts_produce_identical_math(self):
        p=self.profile();normalized=normalize_profile(p)
        snake={k:v for k,v in normalized.items() if '_' in k}
        self.assertEqual(calculate_life_needs(p),calculate_life_needs(snake))

    def test_optional_assumptions_use_existing_defaults_not_zero(self):
        p={k:v for k,v in self.profile().items() if k in REQUIRED_PROFILE_FIELDS}
        self.assertEqual(calculate(p),calculate(self.profile()))
        self.assertEqual(calculate_life_needs({**p,'inflationRate':None,'investmentReturnRate':None}),calculate_life_needs(p))

    def test_rates_have_expected_direction(self):
        base=calculate(self.profile())['additionalCoverageNeeded']
        self.assertGreater(calculate(self.profile(inflationRate=.04))['additionalCoverageNeeded'],base)
        self.assertLess(calculate(self.profile(investmentReturnRate=.07))['additionalCoverageNeeded'],base)
        self.assertLess(calculate(self.profile(incomeReplacementYears=5))['additionalCoverageNeeded'],base)

    def test_invalid_inputs_rejected_before_math(self):
        for field,value in [('mortgageBalance',-1),('mortgageBalance',True),('mortgageBalance',float('nan')),
            ('otherDebt',float('inf')),('inflationRate',1.01),('incomeReplacementYears',1.5),
            ('incomeReplacementYears',121),('numberOfDependents',1.2),('childrenAges',[True]),('childrenAges',[121])]:
            with self.subTest(field=field,value=value):
                self.assertEqual(calculate_life_needs(self.profile(**{field:value}))['status'],'needs_more_information')
                with self.assertRaises(ValueError):calculate(self.profile(**{field:value}))

    def test_missing_required_and_overflow_are_not_results(self):
        self.assertEqual(calculate_life_needs({})['status'],'needs_more_information')
        p=self.profile(mortgageBalance=1e308,otherDebt=1e308)
        self.assertEqual(calculate_life_needs(p)['status'],'needs_more_information')
        with self.assertRaises(ValueError):calculate(p)

    def test_cents_and_whole_dollar_display_are_separate(self):
        p=self.profile(mortgageBalance=180000.37,otherDebt=25000.24,finalExpenses=15000.18)
        r=calculate(p)
        self.assertEqual(r['immediateNeeds'],220000.79)
        self.assertEqual(r['additionalCoverageNeeded'],590376.34)
        self.assertEqual(calculate_life_needs(p)['calculation']['final'],r['additionalCoverageNeeded'])

    def test_all_five_scenarios_and_baseline_preservation(self):
        p=self.profile();base=calculate(p)
        cases=[('child',{'numberOfDependents':4,'collegeFundingNeed':100000,'desiredAnnualIncome':55000},1),
            ('home',{'mortgageBalance':250000},1),('income',{'annualIncome':100000,'desiredAnnualIncome':60000},1),
            ('debt',{'otherDebt':0},-1),('married',{'spouseAnnualIncome':60000,'desiredAnnualIncome':55000},1)]
        for scenario,changes,direction in cases:
            with self.subTest(scenario=scenario):
                projection=simulate(p,scenario,changes,300000,10)
                self.assertEqual(projection['profile'],{**p,**changes})
                self.assertEqual(projection['changes'],changes)
                self.assertEqual(projection['baseResult'],base)
                self.assertEqual(projection['result'],calculate({**p,**changes}))
                self.assertGreater(direction*(projection['result']['additionalCoverageNeeded']-base['additionalCoverageNeeded']),0)
                self.assertEqual(projection['timeline'][0]['additionalNeed'],projection['result']['additionalCoverageNeeded'])
                self.assertEqual(projection['timeline'][2]['proposedCoverage'],0)
                self.assertTrue(all(point['remainingGap']>=0 for point in projection['timeline']))
        self.assertEqual(p,self.profile())

    def test_context_only_changes_intentionally_do_not_change_math(self):
        base=calculate(self.profile())
        for scenario,changes in [('child',{'numberOfDependents':4}),('income',{'annualIncome':100000}),('married',{'spouseAnnualIncome':60000})]:
            self.assertEqual(simulate(self.profile(),scenario,changes)['result'],base)

    def test_invalid_scenario_overrides_and_policy_controls(self):
        for args in [('home',{'otherDebt':0},None,None),('unknown',{'mortgageBalance':0},None,None),
            ('home',{},-1,None),('home',{},True,None),('home',{},None,0),('home',{},None,2.5)]:
            with self.assertRaises(ValueError):simulate(self.profile(),*args)

    def test_projection_explanation_rejects_invented_coverage(self):
        projection=simulate(self.profile(),'home',{'mortgageBalance':250000},300000,10)
        with patch('AI_interact._chat',return_value='You should buy a million dollars of insurance.'):
            result=chat_turn('Explain my current future projection',context={'profile':self.profile(),'simulation':projection})
        self.assertIn('660375.55',result['reply'])
        self.assertNotIn('million',result['reply'])
        self.assertNotIn('590375.55',result['reply'])

if __name__=='__main__':unittest.main()
