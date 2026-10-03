// Mock data for the Community Q&A forum. See BACKEND_API.md.
export const CATEGORIES = ['Family Law', 'Property Law', 'Criminal Law', 'Corporate Law', 'Employment Law', 'Tax Law', 'Immigration', 'Consumer Rights', 'Other']

export const MOCK_QUESTIONS = [
  {
    id: 'q_1', title: 'Is a verbal rental agreement legally binding in Pakistan?', category: 'Property Law',
    body: "My landlord and I only agreed verbally on rent and terms — no written contract. Can he still evict me without notice, and can I use our WhatsApp messages as proof of the agreement?",
    authorName: 'Bilal H.', anonymous: false, createdAt: '2026-09-26T10:00:00Z', viewCount: 412,
    answers: [
      { id: 'a_1', authorName: 'Zainab Farooq', isExpert: true, text: 'A verbal tenancy is enforceable under the Contract Act, but proving its exact terms is harder. Keep your WhatsApp messages, rent receipts and any witnesses — these count as evidence. Your landlord still needs to follow the notice period set by your provincial Rent Restriction Ordinance before eviction.', upvotes: 34, createdAt: '2026-09-26T14:00:00Z' },
      { id: 'a_2', authorName: 'Kiran M.', isExpert: false, text: 'Happened to me too — get everything in writing from now on, even a simple signed note helps a lot.', upvotes: 9, createdAt: '2026-09-27T08:00:00Z' },
    ],
  },
  {
    id: 'q_2', title: 'What counts as wrongful termination under Pakistani labour law?', category: 'Employment Law',
    body: "I was let go over the phone with no written notice or severance. Is this legal, and what can I claim?",
    authorName: 'Anonymous', anonymous: true, createdAt: '2026-09-25T09:00:00Z', viewCount: 268,
    answers: [
      { id: 'a_3', authorName: 'Faisal Khan', isExpert: true, text: 'Under the Industrial and Commercial Employment Ordinance, termination without written notice or pay in lieu of notice is generally unlawful for permanent staff. You may be entitled to notice pay and, if your service was long enough, a gratuity or provident fund payout.', upvotes: 41, createdAt: '2026-09-25T13:00:00Z' },
    ],
  },
  {
    id: 'q_3', title: 'How long does khula usually take to finalise?', category: 'Family Law',
    body: 'My wife has filed for khula. How long does the process typically take through the Family Court, and what happens to haq mehr?',
    authorName: 'Owais R.', anonymous: false, createdAt: '2026-09-24T11:00:00Z', viewCount: 590,
    answers: [
      { id: 'a_4', authorName: 'Zainab Farooq', isExpert: true, text: 'Contested khula cases typically take 6-12 months depending on the court\'s workload and whether both sides cooperate. Courts commonly require the wife to return the haq mehr (or part of it) as a condition, though this varies by case.', upvotes: 52, createdAt: '2026-09-24T16:00:00Z' },
      { id: 'a_5', authorName: 'Sana K.', isExpert: false, text: 'Mine took about 8 months. Get a good family lawyer, it really speeds things up.', upvotes: 12, createdAt: '2026-09-25T09:00:00Z' },
    ],
  },
  {
    id: 'q_4', title: 'Can I register a private limited company remotely from abroad?', category: 'Corporate Law',
    body: "I'm an overseas Pakistani and want to register an SMC-Pvt or Pvt Ltd company with SECP without visiting in person. Is that possible?",
    authorName: 'Hina J.', anonymous: false, createdAt: '2026-09-23T08:00:00Z', viewCount: 201,
    answers: [
      { id: 'a_6', authorName: 'Sara Riaz', isExpert: true, text: 'Yes — SECP\'s eServices portal allows fully online incorporation. You will need scanned CNIC/passport copies, digital signatures, and a registered office address in Pakistan. A local lawyer or company secretary can act as your authorised representative for the filing.', upvotes: 28, createdAt: '2026-09-23T12:00:00Z' },
    ],
  },
  {
    id: 'q_5', title: 'What is the filing deadline for income tax returns this year?', category: 'Tax Law',
    body: 'As a salaried individual, when is my income tax return due, and what is the penalty for filing late?',
    authorName: 'Usman T.', anonymous: false, createdAt: '2026-09-20T08:00:00Z', viewCount: 875,
    answers: [
      { id: 'a_7', authorName: 'Laiba', isExpert: true, text: 'The standard deadline for salaried individuals is 30 September, though FBR sometimes extends it. Filing late can mean a penalty (commonly the higher of Rs. 1,000/day or a percentage of tax payable) and being placed on the Active Taxpayer List late, which affects withholding tax rates on banking and property transactions.', upvotes: 63, createdAt: '2026-09-20T15:00:00Z' },
    ],
  },
  {
    id: 'q_6', title: "Do I need an NOC to change my child's surname on their B-Form?", category: 'Family Law',
    body: "After a custody change, I want to update my son's surname on his NADRA B-Form. What documents does NADRA ask for?",
    authorName: 'Anonymous', anonymous: true, createdAt: '2026-09-18T08:00:00Z', viewCount: 156,
    answers: [],
  },
  {
    id: 'q_7', title: 'Can a landlord keep the full security deposit for normal wear and tear?', category: 'Property Law',
    body: 'Moving out after 2 years, landlord wants to deduct the full deposit for "repainting" and minor scuffs. Is that allowed?',
    authorName: 'Mahnoor S.', anonymous: false, createdAt: '2026-09-15T08:00:00Z', viewCount: 333,
    answers: [
      { id: 'a_8', authorName: 'Bilal Ahmed', isExpert: true, text: 'Deductions should reflect actual damage beyond normal wear and tear, not routine repainting. Ask for an itemised breakdown in writing; if it is unreasonable you can raise it with the Rent Controller in your district.', upvotes: 19, createdAt: '2026-09-15T13:00:00Z' },
    ],
  },
  {
    id: 'q_8', title: 'What are my rights if a company refuses to refund a defective product?', category: 'Consumer Rights',
    body: 'Bought an appliance that stopped working within a week. The shop refuses a refund and only offers repair after a month. What can I do?',
    authorName: 'Kiran M.', anonymous: false, createdAt: '2026-09-10T08:00:00Z', viewCount: 140,
    answers: [],
  },
]
