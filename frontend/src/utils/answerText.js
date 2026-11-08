/* Fixed words on an answer card, in the language the answer is written in.
   m.language is "en", "ur" (Urdu script) or "ur-roman" (Urdu in Latin letters); anything else falls back to English. */
const TEXT = {
  en: {
    steps: 'Steps you can take', important: 'Important', sources: 'Sources', confidence: 'Confidence',
    save: 'Save to Vault', brief: 'Create Case Brief', followUps: 'Suggested follow-up questions',
    carry: 'Continue', typeOwn: 'Or type your own answer below.',
    copied: 'Answer copied to clipboard', saved: 'Answer saved to your Legal Vault',
    thanksUp: 'Thanks for your feedback!', thanksDown: 'Thanks - we’ll use this to improve.',
  },
  ur: {
    steps: 'آپ کیا کر سکتے ہیں', important: 'اہم بات', sources: 'ماخذ', confidence: 'اعتماد',
    save: 'والٹ میں محفوظ کریں', brief: 'کیس بریف بنائیں', followUps: 'مزید سوالات کی تجاویز',
    carry: 'آگے بڑھیں', typeOwn: 'یا نیچے اپنا جواب خود لکھیں۔',
    copied: 'جواب کاپی ہو گیا', saved: 'جواب آپ کے لیگل والٹ میں محفوظ ہو گیا',
    thanksUp: 'آپ کی رائے کا شکریہ!', thanksDown: 'شکریہ، ہم اسے بہتری کے لیے استعمال کریں گے۔',
  },
  'ur-roman': {
    steps: 'Aap kya kar saktay hain', important: 'Aham baat', sources: 'Sources', confidence: 'Bharosa',
    save: 'Vault mein save karein', brief: 'Case Brief banayein', followUps: 'Mazeed sawalat ki tajaweez',
    carry: 'Aagay barhein', typeOwn: 'Ya neeche apna jawab khud likhein.',
    copied: 'Jawab copy ho gaya', saved: 'Jawab aap ke Legal Vault mein save ho gaya',
    thanksUp: 'Aap ki raay ka shukriya!', thanksDown: 'Shukriya, hum isay behtari ke liye istemal karenge.',
  },
}

export const answerText = lang => TEXT[lang] || TEXT.en

/** The composer's answer-language choices: label shown, value sent to the API. "Auto" answers in the language the user wrote in. */
export const ANSWER_LANGS = [
  { label: 'Auto', value: 'auto', hint: 'Same language as your question' },
  { label: 'English', value: 'en' },
  { label: 'اردو', value: 'ur' },
  { label: 'Roman Urdu', value: 'ur-roman' },
]
