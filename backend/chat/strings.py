"""Fixed texts the app itself says (greeting, errors, clarifying prompt, headings, disclaimer), in the user's language.

The model writes the answer; these are the sentences that do not come from the model. Keys have one entry per answer language:
"en", "ur" (Urdu script) and "ur-roman" (Urdu in Latin letters). Keep Act names and numbers in Latin letters in all of them.
"""
from __future__ import annotations

_T: dict[str, dict[str, str]] = {
    "greeting": {
        "en": "Hello! I can explain Pakistani law in plain language, with the sources I used. Ask me about tenancy, family, criminal, labour, contract or property matters, or upload a document.",
        "ur": "السلام علیکم! آپ پاکستانی قانون کے بارے میں سوال پوچھ سکتے ہیں؛ جواب آسان زبان میں اور حوالوں کے ساتھ ملے گا۔ کرایہ داری، خاندانی، فوجداری، مزدوری، معاہدے یا جائیداد کا کوئی بھی معاملہ پوچھیں، یا کوئی دستاویز اپ لوڈ کریں۔",
        "ur-roman": "Assalam o alaikum! Aap Pakistani qanoon ke baare mein sawal pooch saktay hain; jawab aasan zubaan mein aur hawalon ke saath milega. Kiraya daari, khandani, faujdari, mazdoori, muaahide ya jaidad ka koi bhi masla poochein, ya koi dastaveez upload karein.",
    },
    "out_of_scope": {
        "en": "I can only help with questions about Pakistani law. Could you tell me about your legal question?",
        "ur": "یہاں صرف پاکستانی قانون سے متعلق سوالات کے جواب دیے جاتے ہیں۔ براہ کرم اپنا قانونی سوال بتائیں۔",
        "ur-roman": "Yahan sirf Pakistani qanoon se mutaliq sawalaat ke jawab diye jaate hain. Meharbani karke apna qanooni sawal batayein.",
    },
    "no_source": {
        "en": "I could not find a specific law that matches this question. Please try rephrasing it, or ask a qualified lawyer.",
        "ur": "اس سوال سے متعلق کوئی مخصوص قانون نہیں مل سکا۔ براہ کرم سوال کو دوسرے الفاظ میں لکھ کر دیکھیں، یا کسی مستند وکیل سے پوچھیں۔",
        "ur-roman": "Is sawal se mutaliq koi makhsoos qanoon nahi mil saka. Meharbani karke sawal doosray alfaaz mein likh kar dekhein, ya kisi mustanad wakeel se poochein.",
    },
    "error": {
        "en": "I can't answer right now. Please try again in a few minutes.",
        "ur": "اس وقت جواب دینا ممکن نہیں۔ براہ کرم چند منٹ بعد دوبارہ کوشش کریں۔",
        "ur-roman": "Is waqt jawab dena mumkin nahi. Meharbani karke chand minute baad dobara koshish karein.",
    },
    "error_answer": {
        "en": "I could not prepare an answer just now. Please try again.",
        "ur": "ابھی جواب تیار نہیں ہو سکا۔ براہ کرم دوبارہ کوشش کریں۔",
        "ur-roman": "Abhi jawab tayyar nahi ho saka. Meharbani karke dobara koshish karein.",
    },
    "busy": {
        "en": "LegalMate has reached its answer limit for today. Please try again tomorrow.",
        "ur": "آج کے لیے LegalMate کے جوابات کی حد پوری ہو چکی ہے۔ براہ کرم کل دوبارہ کوشش کریں۔",
        "ur-roman": "Aaj ke liye LegalMate ke jawabaat ki had poori ho chuki hai. Meharbani karke kal dobara koshish karein.",
    },
    "clarify_intro": {
        "en": "To give you accurate guidance I need a little more information. Tap an option or type your own answer:",
        "ur": "درست رہنمائی کے لیے مجھے تھوڑی مزید معلومات درکار ہیں۔ کوئی آپشن چنیں یا اپنا جواب خود لکھیں:",
        "ur-roman": "Durust rehnumai ke liye mujhe thori mazeed maloomat darkar hain. Koi option chunein ya apna jawab khud likhein:",
    },
    "disclaimer": {
        "en": "This is general legal information based on the Pakistani laws available to LegalMate, not legal advice. Laws change: please verify with a qualified lawyer.",
        "ur": "یہ عمومی قانونی معلومات ہیں جو LegalMate کے پاس موجود پاکستانی قوانین پر مبنی ہیں، قانونی مشورہ نہیں۔ قوانین بدلتے رہتے ہیں، اس لیے کسی مستند وکیل سے تصدیق کر لیں۔",
        "ur-roman": "Yeh aam qanooni maloomat hain jo LegalMate ke paas maujood Pakistani qawaneen par mabni hain, qanooni mashwara nahi. Qawaneen badalte rehte hain, is liye kisi mustanad wakeel se tasdeeq kar lein.",
    },
    "emergency": {
        "en": "If you or someone else is in immediate danger, call Police on 15 or Rescue on 1122 now. (Numbers shown for Pakistan; confirm local helplines in the Emergency section.)",
        "ur": "اگر آپ یا کوئی اور فوری خطرے میں ہے تو ابھی پولیس کو 15 یا ریسکیو کو 1122 پر کال کریں۔ (یہ نمبر پاکستان کے لیے ہیں؛ مقامی ہیلپ لائنز ایمرجنسی سیکشن میں دیکھ لیں۔)",
        "ur-roman": "Agar aap ya koi aur foori khatre mein hai to abhi Police ko 15 ya Rescue ko 1122 par call karein. (Yeh numbers Pakistan ke liye hain; maqami helplines Emergency section mein dekh lein.)",
    },
    "law_title": {"en": "What the law says", "ur": "قانون کیا کہتا ہے", "ur-roman": "Qanoon kya kehta hai"},
    "some_places": {"en": "some jurisdictions", "ur": "کچھ علاقوں", "ur-roman": "kuch ilaqon"},
    "note_repealed": {
        "en": "Marked as repealed in {scope}. Check the current law before relying on it.",
        "ur": "{scope} میں منسوخ قرار دیا گیا ہے۔ اس پر بھروسہ کرنے سے پہلے موجودہ قانون دیکھ لیں۔",
        "ur-roman": "{scope} mein mansookh qarar diya gaya hai. Is par bharosa karne se pehle mojooda qanoon dekh lein.",
    },
    "note_amended": {
        "en": "Amended later by {titles}. The wording below may have changed: check the current law.",
        "ur": "بعد میں ترمیم ہو چکی ہے: {titles}۔ نیچے دیا گیا متن بدل چکا ہو سکتا ہے، موجودہ قانون دیکھ لیں۔",
        "ur-roman": "Baad mein tarmeem ho chuki hai: {titles}. Neeche diya gaya matan badal chuka ho sakta hai, mojooda qanoon dekh lein.",
    },
}


def tr(key: str, lang: str, **kw: str) -> str:
    entry = _T[key]
    text = entry.get(lang) or entry["en"]
    return text.format(**kw) if kw else text
