// Frontend-only guided conversation, using the team contract's synthetic fixture.
export const mockConversation = {
 introduction:"Hi Amos! Let’s build your protection plan. I’ll ask a few simple questions.",
 complete:'Your example profile is ready. Let’s review your information.',
 acknowledgement:'I’ve added the example value to your plan. You can update it in review.',
 questions:[
  ['annualIncome','First, what’s your annual income?','$75,000'],
  ['numberOfDependents','How many people financially depend on you?','3'],
  ['mortgageBalance','Do you have a mortgage? What’s the remaining balance?','$180,000'],
  ['existingLifeInsurance','How much life insurance do you already have?','$100,000']
 ]
};
