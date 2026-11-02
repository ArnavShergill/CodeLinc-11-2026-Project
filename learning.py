"""Grounded, personalized mini-lessons for the Life Insurance challenge."""
import json
import re
from AI_interact import _chat
from chat_features import clean_context

LESSONS = {
 'protection': ('Who life insurance helps', 'Life insurance can provide financial support to beneficiaries after a covered death, subject to policy terms. It does not pay regular income merely because a policy starts. Tie examples to financial dependents, debts and income support.'),
 'needs': ('Understand your coverage estimate', 'Explain immediate needs (mortgage, other debt and final expenses), income-support/education goals, and resources (existing coverage and available assets). Only use supplied calculator numbers. The reference calculator uses desiredAnnualIncome rather than annual salary. Explain a gap calmly, not as a sales pitch.'),
 'types': ('Term and permanent coverage', 'Term covers a defined period and can align with time-bound responsibilities. Permanent coverage is designed to remain longer if policy requirements are met and may have cash value features. Whole life is one type of permanent coverage, not a synonym for every permanent policy. Costs and features vary; do not quote premiums or guarantee returns. Explain time horizon and affordability tradeoffs, without recommending a specific product.'),
 'future': ('Life events and future planning', 'Revisit plans after changes in family, debt or income-support goals. A simulation is conditional, not a prediction. Read provided scenario inputs and results; never invent projected amounts or assume loans amortize. A policy death benefit helps beneficiaries if a covered claim is payable; it is not the insured person’s investment income.'),
 'next': ('Make an informed next step', 'Review assumptions, whether employer coverage remains available when employment changes, chosen beneficiaries, coverage duration and what the user can comfortably afford. A coverage estimate is not a premium quote. A licensed professional can explain actual products, underwriting and policy terms. Encourage informed questions without pressure.'),
}


def offline_lesson(topic, context):
    """An explicitly labelled, curated lesson when live tutoring is unavailable."""
    title, brief = LESSONS[topic]
    profile = context.get('profile', {})
    example = 'A family may use a payable death benefit to help meet financial responsibilities.'
    if profile.get('numberOfDependents', 0) > 0:
        example = 'Because people depend on your income, consider how long they would need support and which expenses matter most.'
    elif profile.get('mortgageBalance', 0) > 0:
        example = 'Your mortgage is a responsibility to review when comparing a defined coverage period with longer-lasting coverage.'
    if context.get('preferences', {}).get('monthlyBudget') is not None:
        example += ' Compare coverage duration with a payment you can comfortably maintain; this tool does not quote premiums.'
    return {'topic':topic, 'title':title, 'explanation':brief,
        'example':example, 'question':'What is the best way to use this lesson?',
        'choices':['Review your responsibilities and policy terms','Treat it as a guaranteed quote','Assume every policy is the same'],
        'correctIndex':0, 'why':'Use confirmed details and review policy terms. This is education, not financial advice or a quote.',
        'sourceUrl':'https://www.lincolnfinancial.com/public/individuals/products/lifeinsurance',
        'mode':'offline', 'notice':'Live AI tutoring is unavailable. This is a prepared educational lesson.'}


def make_lesson(topic, context):
    if topic not in LESSONS: raise ValueError('Unknown lesson.')
    title, grounding = LESSONS[topic]
    context = clean_context(context)
    prompt = (
        'You are a calm LifeMap educator. Create a short interactive lesson grounded in the supplied teaching brief. '
        'Write for an adult who is new to insurance: respectful, practical language, no childish tone. Define unfamiliar terms as they appear. '
        'Avoid fear and adapt an example to confirmed details if present; otherwise label it a hypothetical example. '
        'Never invent missing facts, calculator numbers, premium prices, guaranteed returns or a product recommendation. '
        'Return ONLY a JSON object with title, explanation (2 short paragraphs), example (one concrete example), '
        'question (one comprehension question), choices (3 brief strings), correctIndex (0,1 or 2), why (2 sentences). '
        'The answer must follow directly from the lesson. Make choices unambiguous. '
        'Teaching brief: ' + grounding
    )
    try:
        raw = _chat([{'role':'system','content':prompt}, {'role':'user','content':json.dumps({'topic':title,'confirmedContext':context})}], json_mode=True).strip()
    except Exception:
        lesson = offline_lesson(topic, context)
        lesson['explanation'] = lesson['notice'] + ' ' + lesson['explanation']
        return lesson
    if raw.startswith('```'): raw = re.sub(r'\A```(?:json)?\s*|\s*```\Z','',raw)
    try:
        lesson = json.loads(raw)
        if not isinstance(lesson,dict): raise ValueError()
        for key in ('title','explanation','example','question','why'):
            if not isinstance(lesson.get(key),str) or not lesson[key].strip() or len(lesson[key])>3000: raise ValueError()
        choices=lesson.get('choices');correct=lesson.get('correctIndex')
        if not isinstance(choices,list) or len(choices)!=3 or any(not isinstance(c,str) or not c.strip() or len(c)>300 for c in choices): raise ValueError()
        if isinstance(correct,bool) or not isinstance(correct,int) or not 0<=correct<3: raise ValueError()
    except (ValueError,TypeError) as error:
        raise RuntimeError('The lesson could not be generated. Please retry.') from error
    from AI_interact import _qualitative_only
    texts = [lesson[key] for key in ('title','explanation','example','question','why')] + lesson['choices']
    if any(not _qualitative_only(text) for text in texts):
        return offline_lesson(topic, context)
    return {**{key:lesson[key] for key in ('title','explanation','example','question','choices','correctIndex','why')}, 'topic':topic,
            'sourceUrl':'https://www.lincolnfinancial.com/public/individuals/products/lifeinsurance'}
