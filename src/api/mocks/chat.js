// Mock conversation data for the Legal Chat screens.

export const TENANT_SOURCES = [
  {
    id: 1, title: 'The Rent Act, 2009', section: 'Section 4 - Tenancy Agreement', type: 'Act',
    quote: '“The terms of a written tenancy agreement shall be binding on the landlord and the tenant and shall not be varied except by mutual consent.”',
  },
  {
    id: 2, title: 'The Rent Act, 2009', section: 'Section 5 - Increase in Rent', type: 'Act',
    quote: '“No landlord shall increase the rent during the currency of a tenancy agreement except in accordance with the terms of the agreement or as permitted under this Act.”',
  },
  {
    id: 3, title: 'Rent Control Rules, 2010', section: 'Rule 7 - Resolution of Disputes', type: 'Rule',
    quote: '“Any dispute between the landlord and tenant regarding rent shall be decided by the Rent Controller having jurisdiction in the district.”',
  },
]

export const TENANT_ANSWER = {
  kind: 'answer',
  time: '10:24 AM',
  doneTime: '10:26 AM',
  intro: ['In general, your landlord cannot increase the rent in the middle of a fixed-term rental contract unless the contract allows it or ', { b: 'both parties' }, ' agree. Pakistani law protects tenants from arbitrary rent increases. ', { cite: 1 }],
  lawTitle: 'What the law generally says',
  law: ['Under the Rent Act, 2009, the terms of a written rental agreement are binding on both parties. The landlord cannot unilaterally change the agreed rent during the contract period. Any increase is typically allowed only after the contract expires, subject to reasonable notice and local rent control rules (if applicable). ', { cite: 1 }, ' ', { cite: 2 }],
  steps: [
    ['Review your rental agreement for any rent increase clause.'],
    ['Politely inform the landlord that the current contract terms are binding.'],
    ['If pressure continues, send a written response (email/letter) referring to the Rent Act, 2009.'],
    ['You can approach the Rent Controller in your district if the landlord illegally increases rent or threatens eviction. ', { cite: 3 }],
  ],
  important: 'Do not stop paying rent without legal advice. Non-payment can be used as a ground for eviction even if the rent increase is unlawful.',
  outro: 'If you share your city (e.g., Islamabad, Lahore, Karachi), I can also guide you on any local rent control rules that may apply.',
  sources: TENANT_SOURCES,
  confidence: { score: 87, relevance: 92, agreement: 84, recency: 86, checked: 4, verified: '23 Sep 2026', verifiedTime: '10:26 AM' },
}

const genericSources = (act, section, quote, type = 'Act') => [
  { id: 1, title: act, section, type, quote },
  { id: 2, title: 'Constitution of Pakistan, 1973', section: 'Article 4 - Right to be dealt with in accordance with law', type: 'Act', quote: '“To enjoy the protection of law and to be treated in accordance with law is the inalienable right of every citizen.”' },
]

const TOPICS = {
  employment: {
    title: 'Employment termination', tag: 'Labour Law', question: 'Can my employer terminate me without notice?',
    intro: 'In most cases, a permanent employee in Pakistan cannot be terminated without either a notice period or payment in lieu of notice, unless the termination is for proven misconduct.',
    law: 'Under the Standing Orders Ordinance, a permanent worker is generally entitled to one month’s notice or one month’s wages in lieu of notice. Termination for misconduct requires a written charge and an opportunity to respond.',
    steps: ['Check your appointment letter and company policy for notice terms.', 'Ask your employer for the reason for termination in writing.', 'Keep copies of salary slips, emails and your termination letter.', 'You may file a grievance or approach the Labour Court within the limitation period.'],
    sources: genericSources('Industrial & Commercial Employment (Standing Orders) Ordinance, 1968', 'Standing Order 12 - Termination of Employment', '“The employment of a permanent workman shall not be terminated for any reason other than misconduct unless one month’s notice is given or one month’s wages are paid in lieu thereof.”'),
    confidence: 84,
  },
  cnic: {
    title: 'CNIC renewal process', tag: 'Identity', question: 'What documents are required to renew my CNIC?',
    intro: 'You can renew your CNIC at any NADRA Registration Centre or online through the Pak-ID portal. Renewal should ideally be done before the card expires.',
    law: 'NADRA requires your existing or expired CNIC, biometric verification and the applicable fee. Changes in address or marital status may need supporting documents.',
    steps: ['Keep your current CNIC ready.', 'Visit a NADRA centre or apply via the Pak-ID mobile app.', 'Complete biometric verification and pay the fee.', 'Track your application and collect the card when ready.'],
    sources: genericSources('National Database and Registration Authority Ordinance, 2000', 'Section 10 - Issue of National Identity Card', '“Every citizen who has attained the age of eighteen years shall get himself registered and obtain a National Identity Card.”'),
    confidence: 90,
  },
  inheritance: {
    title: 'Inheritance laws', tag: 'Family Law', question: 'How is property distributed among heirs after death?',
    intro: 'For Muslims in Pakistan, inheritance is distributed according to Islamic law of succession, with fixed shares for legal heirs such as spouse, children and parents.',
    law: 'Shares are determined by personal law. Daughters are legally entitled to a share and cannot be deprived of it; depriving a woman of inheritance is a criminal offence.',
    steps: ['Obtain the death certificate and family registration certificate from NADRA.', 'Apply for a succession certificate or letter of administration.', 'Identify all legal heirs and their shares.', 'Transfer property through the relevant revenue or registration office.'],
    sources: genericSources('Pakistan Penal Code, 1860', 'Section 498A - Prohibition of depriving woman from inheriting property', '“Whoever by deceitful or illegal means deprives any woman from inheriting any movable or immovable property at the time of opening of succession shall be punished…”'),
    confidence: 86,
  },
  consumer: {
    title: 'Consumer complaint', tag: 'Consumer Rights', question: 'I received a faulty product. What can I do?',
    intro: 'As a consumer you are entitled to a product that matches its description and is free from defects. You can ask for repair, replacement or a refund.',
    law: 'Provincial consumer protection laws allow you to file a claim before the Consumer Court after giving the seller written notice and a chance to remedy the defect.',
    steps: ['Keep your receipt, warranty card and photos of the defect.', 'Send a written notice to the seller or manufacturer.', 'Wait for the notice period (usually 15 days) for a response.', 'File a complaint in the Consumer Court of your district.'],
    sources: genericSources('Punjab Consumer Protection Act, 2005', 'Section 28 - Filing of claim', '“A consumer who has suffered damage shall, before filing a claim, give notice to the defendant… allowing fifteen days to remedy the defect.”'),
    confidence: 85,
  },
  marriage: {
    title: 'Marriage registration', tag: 'Family Law', question: 'What is the procedure for marriage registration?',
    intro: 'Marriages in Pakistan should be registered with the Union Council through the Nikah Registrar. Registration protects the rights of both spouses.',
    law: 'The Muslim Family Laws Ordinance requires every marriage to be registered. The Nikahnama is then used to obtain a Marriage Registration Certificate from NADRA.',
    steps: ['Ensure the Nikah is performed by a licensed Nikah Registrar.', 'Fill in all columns of the Nikahnama carefully.', 'The registrar submits it to the Union Council.', 'Obtain the computerised Marriage Registration Certificate.'],
    sources: genericSources('Muslim Family Laws Ordinance, 1961', 'Section 5 - Registration of marriages', '“Every marriage solemnized under Muslim Law shall be registered in accordance with the provisions of this Ordinance.”'),
    confidence: 91,
  },
  fir: {
    title: 'Police FIR process', tag: 'Criminal Law', question: 'How to file an online FIR?',
    intro: 'You can report a cognizable offence at the relevant police station or, in many provinces, through an online complaint portal. The police must register an FIR for cognizable offences.',
    law: 'Section 154 CrPC requires the officer in charge to record information about a cognizable offence. If the police refuse, you can approach the Justice of Peace.',
    steps: ['Write down the facts: date, time, place and people involved.', 'Submit your complaint online or at the police station.', 'Get a copy of the FIR free of cost.', 'If refused, file a petition before the Justice of Peace under Section 22-A CrPC.'],
    sources: genericSources('Code of Criminal Procedure, 1898', 'Section 154 - Information in cognizable cases', '“Every information relating to the commission of a cognizable offence… shall be reduced to writing by the officer in charge of a police station.”'),
    confidence: 88,
  },
  land: {
    title: 'Land dispute resolution', tag: 'Property Law', question: 'What is the legal process for a land dispute?',
    intro: 'Land disputes are usually resolved through the revenue authorities for record corrections and through civil courts for title and possession claims.',
    law: 'Revenue records (Fard, Jamabandi) can be challenged before revenue officers, while ownership and possession are decided by civil courts under the Specific Relief Act.',
    steps: ['Collect the Fard, registry, mutation and any sale documents.', 'Verify records at the Arazi Record Centre.', 'Try mediation or a legal notice first.', 'File a civil suit for declaration or possession if needed.'],
    sources: genericSources('Specific Relief Act, 1877', 'Section 42 - Discretion of court as to declaration of status or right', '“Any person entitled to any legal character, or to any right as to any property, may institute a suit…”'),
    confidence: 83,
  },
  custody: {
    title: 'Child custody laws', tag: 'Family Law', question: 'What factors affect custody of a child?',
    intro: 'Custody decisions in Pakistan are made by the Guardian Court, and the welfare of the minor is the most important consideration.',
    law: 'Under the Guardians and Wards Act, the court considers the child’s age, sex, wishes (if old enough), and the character and capacity of the parents.',
    steps: ['File a custody or visitation petition before the Guardian Court.', 'Provide evidence about the child’s welfare and living conditions.', 'Request interim custody or visitation if urgent.', 'Follow court-ordered mediation where required.'],
    sources: genericSources('Guardians and Wards Act, 1890', 'Section 17 - Matters to be considered by the Court', '“In appointing or declaring the guardian of a minor, the Court shall… be guided by what… appears in the circumstances to be for the welfare of the minor.”'),
    confidence: 87,
  },
}

export function topicAnswer(key, time) {
  const t = TOPICS[key]
  return {
    kind: 'answer', time, doneTime: time,
    intro: [t.intro, ' ', { cite: 1 }],
    lawTitle: 'What the law generally says',
    law: [t.law, ' ', { cite: 1 }, ' ', { cite: 2 }],
    steps: t.steps.map(s => [s]),
    important: 'This is general information. For your specific situation, consider consulting a qualified lawyer.',
    outro: 'Tell me more about your situation and I can guide you on the next steps.',
    sources: t.sources,
    confidence: { score: t.confidence, relevance: t.confidence + 4, agreement: t.confidence - 3, recency: t.confidence - 1, checked: 3, verified: '23 Sep 2026', verifiedTime: time },
  }
}

export function genericAnswer(question, time) {
  const q = question.toLowerCase()
  const match = Object.keys(TOPICS).find(k => q.includes(k) || TOPICS[k].title.toLowerCase().split(' ').some(w => w.length > 4 && q.includes(w)))
  if (/rent|landlord|tenan/.test(q)) return { ...TENANT_ANSWER, time, doneTime: time }
  if (match) return topicAnswer(match, time)
  return {
    kind: 'answer', time, doneTime: time,
    intro: ['Thanks for your question. Based on general principles of Pakistani law, the answer depends on the specific facts, the documents involved and the province you are in. ', { cite: 1 }],
    lawTitle: 'What the law generally says',
    law: ['Every citizen has the right to be treated in accordance with law. Most civil disputes are first addressed through written notice and negotiation, and then through the relevant court or tribunal if they cannot be resolved. ', { cite: 1 }],
    steps: [['Collect all relevant documents and correspondence.'], ['Write down a clear timeline of events.'], ['Send a polite written notice to the other party if appropriate.'], ['Consult a lawyer or legal aid organisation for advice specific to your case.']],
    important: 'Limitation periods may apply. Do not delay taking action on time-sensitive matters.',
    outro: 'If you share more details (city, dates and documents), I can give more specific guidance.',
    sources: genericSources('Constitution of Pakistan, 1973', 'Article 10A - Right to fair trial', '“For the determination of his civil rights and obligations or in any criminal charge against him a person shall be entitled to a fair trial and due process.”').slice(0, 2),
    confidence: { score: 78, relevance: 80, agreement: 76, recency: 79, checked: 2, verified: '23 Sep 2026', verifiedTime: time },
  }
}

export const CONVERSATIONS = [
  { id: 'tenant-rights', group: 'Today', icon: 'chat', title: 'Tenant rights in Pakistan', preview: 'What are my rights if the landlord...', time: '10:24 AM', tag: 'Property Law' },
  { id: 'employment', group: 'Today', icon: 'briefcase', title: 'Employment termination', preview: 'Can my employer terminate me...', time: '09:15 AM', tag: 'Labour Law' },
  { id: 'cnic', group: 'Today', icon: 'doc', title: 'CNIC renewal process', preview: 'What documents are required...', time: '08:42 AM', tag: 'Identity' },
  { id: 'inheritance', group: 'Previous 7 Days', icon: 'home', title: 'Inheritance laws', preview: 'How is property distributed...', time: '20 Sep', tag: 'Family Law' },
  { id: 'consumer', group: 'Previous 7 Days', icon: 'message', title: 'Consumer complaint', preview: 'I received a faulty product...', time: '19 Sep', tag: 'Consumer Rights' },
  { id: 'marriage', group: 'Previous 7 Days', icon: 'doc', title: 'Marriage registration', preview: 'What is the procedure for...', time: '18 Sep', tag: 'Family Law' },
  { id: 'fir', group: 'Older', icon: 'doc', title: 'Police FIR process', preview: 'How to file an online FIR?', time: '15 Sep', tag: 'Criminal Law' },
  { id: 'land', group: 'Older', icon: 'file', title: 'Land dispute resolution', preview: 'What is the legal process...', time: '12 Sep', tag: 'Property Law' },
  { id: 'custody', group: 'Older', icon: 'person', title: 'Child custody laws', preview: 'What factors affect custody...', time: '10 Sep', tag: 'Family Law' },
]

export function initialMessages() {
  const map = {
    'tenant-rights': [
      { kind: 'user', text: 'What are my rights if the landlord wants to increase rent in the middle of the contract in Pakistan?', time: '10:24 AM' },
      TENANT_ANSWER,
    ],
  }
  Object.keys(TOPICS).forEach(k => {
    const c = CONVERSATIONS.find(x => x.id === k)
    map[k] = [{ kind: 'user', text: TOPICS[k].question, time: c.time.includes('M') ? c.time : '11:00 AM' }, topicAnswer(k, c.time.includes('M') ? c.time : '11:01 AM')]
  })
  return map
}

export const TOPIC_CARDS = [
  { key: 'tenant-rights', icon: 'home', title: 'Tenant rights', text: 'Rent, eviction, agreements', starter: 'What are my rights if the landlord wants to increase rent in the middle of the contract in Pakistan?' },
  { key: 'employment', icon: 'briefcase', title: 'Employment termination', text: 'Your workplace rights', starter: 'Can my employer terminate me without notice?' },
  { key: 'inheritance', icon: 'users', title: 'Family inheritance', text: 'Property, wills and succession', starter: 'How is property distributed among heirs after death?' },
  { key: 'consumer', icon: 'cart', title: 'Consumer complaint', text: 'Refunds, faulty products, consumer rights', starter: 'I received a faulty product. What can I do?' },
]
