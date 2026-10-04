/** Shared contract v1 — field names copied from the team build contract.
 * No schema existed in this workspace. Numeric types reflect the synthetic fixture.
 * The contract does not define breakdown item shape; UI mock entries use label/amount.
 * Confirm that item shape with the backend owner before integration.
 * @typedef {Object} LifeNeedsProfile
 * @property {number} annualIncome
 * @property {number} spouseAnnualIncome
 * @property {number} numberOfDependents
 * @property {number[]} childrenAges
 * @property {number} mortgageBalance
 * @property {number} otherDebt
 * @property {number} finalExpenses
 * @property {number} desiredAnnualIncome
 * @property {number} incomeReplacementYears
 * @property {number} collegeFundingNeed
 * @property {number} existingLifeInsurance
 * @property {number} availableAssets
 * @property {number} inflationRate
 * @property {number} investmentReturnRate
 * @typedef {Object} LifeNeedsResult
 * @property {number} immediateNeeds
 * @property {number} longTermNeeds
 * @property {number} totalNeeds
 * @property {number} availableResources
 * @property {number} additionalCoverageNeeded
 * @property {{label:string, amount:number}[]} breakdown UI fixture convention, pending backend agreement.
 * @property {string[]} assumptions
 */
export const profileFields = [
 ['annualIncome','Annual income','money'],['spouseAnnualIncome','Spouse annual income','money'],
 ['numberOfDependents','People relying on your income','count'],['childrenAges','Children’s ages','ages'],
 ['mortgageBalance','Mortgage balance','money'],['otherDebt','Other debt','money'],
 ['finalExpenses','Final expenses','money'],['desiredAnnualIncome','Yearly income for your family','money'],
 ['incomeReplacementYears','Years of family income support','count'],['collegeFundingNeed','College funding need','money'],
 ['existingLifeInsurance','Existing life insurance','money'],['availableAssets','Savings and other available money','money'],
 ['inflationRate','Inflation rate','rate'],['investmentReturnRate','Investment return rate','rate']
];
export function validateProfile(profile) {
 return profileFields.flatMap(([key,label,type]) => {
  const value = profile[key];
  if(type==='ages') return Array.isArray(value) && value.every(n=>Number.isInteger(n)&&n>=0&&n<=120) ? [] : [label];
  return typeof value==='number' && Number.isFinite(value) && value>=0 && (type!=='count'||(Number.isInteger(value)&&value<=120)) && (type!=='rate'||value<=1) ? [] : [label];
 });
}
