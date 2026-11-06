"""Gold test questions for retrieval evaluation.

Each question has:
  question   what a user would type (English, Roman Urdu or Urdu)
  query_en   what the analyser step would hand to retrieval (plain English search query, no statute wording on purpose)
  jur        user's jurisdiction from their profile (Punjab | ICT | Federal)
  rel        relevant specs: a chunk is relevant if it matches ANY spec. A spec matches when the chunk's act title
             contains `act` (case-insensitive) AND its header contains `head` (if given) AND its text contains ALL of `has`.
  neg        True = out-of-scope question; nothing relevant exists (used to tune the "no source" threshold)
"""
from __future__ import annotations

GOLD: list[dict] = []


def q(id_, cat, question, query_en, jur, *rel, neg=False, lang="en"):
    GOLD.append({"id": id_, "cat": cat, "question": question, "query_en": query_en, "jur": jur, "lang": lang,
                 "neg": neg, "rel": [dict(act=r[0], head=r[1] if len(r) > 1 else "", has=list(r[2]) if len(r) > 2 else []) for r in rel]})


RRP = "Punjab Rented Premises"
# ---------------------------------------------------------------- tenancy
q("T01", "tenancy", "My landlord wants me out because his son needs the house. Can he do that?",
  "landlord wants to evict tenant because he needs the house for his own family member", "Punjab", (RRP, "grounds for eviction"))
q("T02", "tenancy", "I haven't paid rent for three months. Can the landlord throw me out?",
  "tenant failed to pay rent landlord eviction", "Punjab", (RRP, "grounds for eviction"))
q("T03", "tenancy", "Does a rent agreement have to be in writing and registered?",
  "is a written tenancy agreement compulsory registration with rent registrar", "Punjab", (RRP, "agreement between landlord and tenant"), (RRP, "contents of tenancy agreement"))
q("T04", "tenancy", "Can my tenant give a room to someone else without asking me?",
  "tenant letting part of rented premises to another person without landlord permission", "Punjab", (RRP, "subletting"))
q("T05", "tenancy", "My landlord switched off electricity and water to force me out.",
  "landlord cuts off utilities water electricity of tenant", "Punjab", (RRP, "obligations of landlord"))
q("T06", "tenancy", "Where do I file a case against my landlord in Lahore?",
  "which forum or tribunal hears landlord tenant disputes", "Punjab", (RRP, "establishment of rent tribunal"), (RRP, "filing of application"))
q("T07", "tenancy", "Landlord refuses to take rent. What should I do?",
  "landlord refuses to accept rent tenant deposit rent", "Punjab", (RRP, "application for deposit of rent"), (RRP, "payment of rent"))
q("T08", "tenancy", "Who has to pay for repairs, tenant or landlord?",
  "repairs of rented house responsibility landlord or tenant", "Punjab", (RRP, "obligations of landlord"), (RRP, "obligations of tenant"))
q("T09", "tenancy", "Can my landlord raise the rent in Islamabad whenever he wants?",
  "annual increase of rent by landlord in Islamabad", "ICT", ("Islamabad Rent Restriction", "", ["rent"]))
q("T10", "tenancy", "How can a landlord get his shop vacated in Islamabad?",
  "ejectment of tenant from premises Islamabad grounds", "ICT", ("Islamabad Rent Restriction", "eject"), ("Islamabad Rent Restriction", "evict"))
q("T11", "tenancy", "Mera landlord bagair notice ke makaan khali karwana chahta hai, kya yeh jaiz hai?",
  "landlord wants to evict tenant without notice is it lawful", "Punjab", (RRP, "grounds for eviction"), (RRP, "eviction"), lang="ur-roman")
q("T12", "tenancy", "Do I have to pay pagri or a big advance to get a shop on rent?",
  "pagri advance security taken from tenant at time of letting", "Punjab", (RRP, "", ["pagri"]))
# ---------------------------------------------------------------- family
q("F01", "family", "How can a wife get a divorce from court if her husband doesn't support her?",
  "wife seeks dissolution of marriage in court grounds husband failed to maintain her", "Punjab", ("Dissolution of Muslim Marriages", "grounds for decree"))
q("F02", "family", "What is khula and how does a woman get it?",
  "khula dissolution of marriage on wife's request family court", "Punjab", ("Family Court", "", ["khula"]))
q("F03", "family", "My husband said talaq three times. What is the legal procedure?",
  "pronouncement of talaq notice to union council chairman waiting period", "Punjab", ("Muslim Family Laws", "talaq"))
q("F04", "family", "Can my husband marry a second time without my permission?",
  "second marriage by husband without permission of existing wife arbitration council", "Punjab", ("Muslim Family Laws", "polygamy"))
q("F05", "family", "Is it compulsory to register a nikah?",
  "registration of muslim marriage nikah registrar", "Punjab", ("Muslim Family Laws", "registration of marriages"))
q("F06", "family", "Who gets custody of the children after divorce?",
  "custody of minor children guardian welfare of the child after divorce", "Punjab", ("Guardians and Wards", "", ["welfare of the minor"]), ("Guardians and Wards", "", ["welfare"]))
q("F07", "family", "How do I claim monthly maintenance for my children?",
  "suit for maintenance of wife and children family court", "Punjab", ("Family Court", "", ["maintenance"]))
q("F08", "family", "My husband did not pay my haq mehr. Where can I recover it?",
  "recovery of dower haq mehr suit family court jurisdiction", "Punjab", ("Family Court", "", ["dower"]))
q("F09", "family", "Do daughters get a share in their father's property?",
  "inheritance share of daughters in father's property muslim law", "Punjab", ("Muslim Personal Law", "", ["succession"]), ("Muslim Personal Law", "", ["inheritance"]))
q("F10", "family", "My brothers are not giving me my share of our father's land.",
  "women deprived of inheritance property by relatives complaint", "Punjab", ("Enforcement of Women", "", ["deprive"]), ("Enforcement of Women", "", ["dispossess"]))
q("F11", "family", "What is the legal age of marriage in Punjab?",
  "minimum age for marriage punishment for child marriage", "Punjab", ("Child Marriage Restraint", "", ["child marriage"]))
q("F12", "family", "My husband beats me. What can I do legally?",
  "protection of women against domestic violence complaint protection order", "Punjab", ("Protection of Women Against Violence", "", ["violence"]))
q("F13", "family", "Who can be appointed guardian of a minor's property?",
  "appointment of guardian for minor child and property by court", "Federal", ("Guardians and Wards", "appointment"), ("Guardians and Wards", "", ["guardian of the person"]))
q("F14", "family", "Meri biwi khula ka case kar rahi hai, kya main usay rok sakta hoon?",
  "wife filed khula case can husband stop it family court", "Punjab", ("Family Court", "", ["khula"]), lang="ur-roman")
# ---------------------------------------------------------------- criminal
q("C01", "criminal", "Someone stole my mobile phone. What law applies?",
  "theft of mobile phone punishment", "Federal", ("Pakistan Penal Code", "", ["punishment for theft"]))
q("C02", "criminal", "The police are refusing to register my FIR.",
  "how to register first information report police refuses to record complaint", "Federal", ("Code of Criminal Procedure", "information in cognizable cases"))
q("C03", "criminal", "How do I get bail after being arrested?",
  "bail for accused in non-bailable offence court power to grant bail", "Federal", ("Code of Criminal Procedure", "when bail may be taken"), ("Code of Criminal Procedure", "in what cases bail to be taken"))
q("C04", "criminal", "A customer's cheque I deposited bounced. What can I do?",
  "dishonoured cheque criminal case against issuer", "Federal", ("Pakistan Penal Code", "dishonestly issuing a cheque"))
q("C05", "criminal", "Someone is spreading lies about me on social media.",
  "defamation false statements about a person punishment", "Federal", ("Pakistan Penal Code", "punishment for defamation"), ("Prevention of Electronic Crimes Act", "", ["dignity"]))
q("C06", "criminal", "A man keeps messaging and following me online. Is it a crime?",
  "online harassment stalking cyber stalking of a woman", "Federal", ("Prevention of Electronic Crimes Act", "cyber stalking"))
q("C07", "criminal", "Someone hacked my Facebook account.",
  "unauthorised access to someone's account or information system", "Federal", ("Prevention of Electronic Crimes Act", "unauthorized access"))
q("C08", "criminal", "Someone made a fake profile with my photos.",
  "fake social media profile using another person's photograph identity", "Federal", ("Prevention of Electronic Crimes Act", "", ["identity"]), ("Prevention of Electronic Crimes Act", "dignity"))
q("C09", "criminal", "A neighbour threatened to kill me.",
  "threat to kill criminal intimidation punishment", "Federal", ("Pakistan Penal Code", "criminal intimidation"))
q("C10", "criminal", "A man took money from me promising a job abroad and disappeared.",
  "cheating fraud taking money on false promise punishment", "Federal", ("Pakistan Penal Code", "cheating and dishonestly inducing"), ("Emigration Ordinance", "", ["promoter"]))
q("C11", "criminal", "What are my rights if the police arrest me?",
  "rights of arrested person informed of grounds produced before magistrate within 24 hours", "Federal", ("Constitution of the Islamic", "safeguards as to arrest"), ("Code of Criminal Procedure", "", ["twenty-four hours"]))
q("C12", "criminal", "What is the punishment for murder in Pakistan?",
  "punishment for intentional murder qatl-i-amd", "Federal", ("Pakistan Penal Code", "qatl-i-amd"))
q("C13", "criminal", "What is the punishment for rape?",
  "punishment for rape and gang rape", "Federal", ("Pakistan Penal Code", "rape"))
q("C14", "criminal", "Someone kidnapped my brother.",
  "kidnapping or abduction of a person punishment", "Federal", ("Pakistan Penal Code", "kidnapping"))
q("C15", "criminal", "What can I do if the police arrest someone without showing a warrant?",
  "arrest without warrant by police power and limits", "Federal", ("Code of Criminal Procedure", "", ["without an order from a magistrate"]), ("Code of Criminal Procedure", "", ["without warrant"]))
q("C16", "criminal", "Someone threw acid on my sister.",
  "acid attack hurt by corrosive substance punishment", "Federal", ("Pakistan Penal Code", "", ["corrosive substance"]), ("Pakistan Penal Code", "", ["acid"]))
q("C17", "criminal", "Someone called pretending to be from my bank and took money from my account.",
  "electronic fraud cyber fraud bank account theft through deception", "Federal", ("Prevention of Electronic Crimes Act", "", ["fraud"]))
q("C18", "criminal", "What is the punishment for possessing drugs?",
  "possession of narcotic drugs punishment quantity", "Federal", ("Control of Narcotic Substances", "", ["possess"]))
q("C19", "criminal", "Mera cheque bounce ho gaya hai, kya FIR ho sakti hai?",
  "cheque dishonoured can criminal case be registered", "Federal", ("Pakistan Penal Code", "dishonestly issuing a cheque"), lang="ur-roman")
q("C20", "criminal", "Can I be arrested for a family dispute complaint made by my in-laws?",
  "false case arrest on complaint cancellation of bail quashing of case", "Federal", ("Code of Criminal Procedure", "", ["bail"]))
# ---------------------------------------------------------------- labour
q("L01", "labour", "My company fired me without notice. Can I challenge it?",
  "termination of employment without notice worker grievance remedy", "Punjab", ("Punjab Labour Code", "", ["terminat"]), ("Industrial Relations Act", "individual grievances"), ("Standing Orders", "", ["terminat"]))
q("L02", "labour", "My employer hasn't paid my salary for two months.",
  "non-payment of wages delay in payment employer", "Punjab", ("Payment of Wages", "", ["wages"]), ("Punjab Labour Code", "", ["wages"]))
q("L03", "labour", "What is the minimum wage in Punjab?",
  "minimum wage fixation for workers in punjab", "Punjab", ("Punjab Minimum Wages", "", ["minimum"]))
q("L04", "labour", "How many days of maternity leave am I entitled to?",
  "maternity leave for female employee period with full pay", "Punjab", ("Punjab Labour Code", "", ["maternity"]), ("Maternity and Paternity Leave", "", ["maternity leave"]), ("Maternity Benefit", "", ["maternity"]))
q("L05", "labour", "My boss is harassing me at work. What can I do?",
  "sexual harassment at workplace complaint inquiry committee", "Federal", ("Harassment of Women at the Workplace", "", ["inquiry committee"]))
q("L06", "labour", "Can a 12 year old child work in a workshop?",
  "employment of children minimum age prohibited", "Punjab", ("Employment of Children", "", ["child"]))
q("L07", "labour", "I work as a maid. Do I have any legal rights?",
  "domestic worker rights wages leave contract", "Punjab", ("Domestic Workers", "", ["domestic worker"]))
q("L08", "labour", "Is my employer allowed to make me work 12 hours a day?",
  "maximum working hours per day overtime for workers", "Punjab", ("Factories Act", "", ["hours"]), ("Punjab Labour Code", "", ["working hours"]), ("Shops and Establishments", "", ["hours"]))
q("L09", "labour", "How can workers form a trade union?",
  "registration of trade union by workers requirements", "Federal", ("Industrial Relations Act", "", ["trade union"]))
q("L10", "labour", "I was injured at work. Who pays compensation?",
  "employer liability to pay compensation for workplace injury", "Federal", ("Workmen", "", ["compensation"]))
q("L11", "labour", "Do I get a pension when I retire from a private job?",
  "old age pension for employees of private establishments", "Federal", ("Old-Age Benefits", "", ["pension"]))
q("L12", "labour", "My factory owner is keeping me as a bonded labourer to repay a loan.",
  "bonded labour peshgi debt forced labour abolition", "Punjab", ("Bonded Labour", "", ["bonded"]))
q("L13", "labour", "Meri company ne mujhe achanak nikaal diya, mujhe kya karna chahiye?",
  "worker dismissed suddenly employment terminated what remedy", "Punjab", ("Punjab Labour Code", "", ["terminat"]), ("Industrial Relations Act", "individual grievances"), lang="ur-roman")
# ---------------------------------------------------------------- contracts / business
q("B01", "contract", "Is a verbal agreement legally binding?",
  "are oral agreements valid contracts requirement of writing", "Federal", ("Contract act", "what agreements are contracts"))
q("B02", "contract", "The other party broke our contract. What compensation can I claim?",
  "compensation for loss caused by breach of contract", "Federal", ("Contract act", "compensation for loss or damage caused by breach"))
q("B03", "contract", "Is a contract void if no money or value was exchanged?",
  "agreement without consideration validity", "Federal", ("Contract act", "agreement without consideration"))
q("B04", "contract", "My 16 year old son signed an agreement. Is it valid?",
  "contract by a minor competence to contract age of majority", "Federal", ("Contract act", "who are competent to contract"))
q("B05", "contract", "I signed a contract because I was forced. Can I cancel it?",
  "contract made under coercion undue influence free consent voidable", "Federal", ("Contract act", "coercion"), ("Contract act", "free consent"))
q("B06", "contract", "The contract says I must pay 10 lakh penalty if I leave. Is that enforceable?",
  "penalty clause liquidated damages stipulated sum enforceable", "Federal", ("Contract act", "penalty stipulated"))
q("B07", "contract", "How can a business partnership be dissolved?",
  "dissolution of partnership firm by partners", "Federal", ("Partnership Act", "", ["dissolution"]))
q("B08", "contract", "I bought a defective product from a shop. Can I get a refund?",
  "defective goods sale implied condition quality fitness buyer remedy", "Federal", ("Sale of Goods", "implied condition"), ("Punjab Consumer Protection", "", ["defective"]))
q("B09", "contract", "Do I have to pay stamp duty on a rent or sale agreement?",
  "stamp duty on agreement instruments chargeable", "Punjab", ("Stamp Act", "", ["agreement"]))
q("B10", "contract", "Our contract has an arbitration clause. How does arbitration work?",
  "arbitration agreement appointment of arbitrator award", "Federal", ("Arbitration Act", "", ["arbitrat"]))
q("B11", "contract", "I stood guarantor for a friend's loan. Am I liable if he doesn't pay?",
  "liability of surety guarantor for principal debtor's default", "Federal", ("Contract act", "", ["guarantee"]))
q("B12", "contract", "A cheque I received was returned unpaid. What are my rights as holder?",
  "dishonour of cheque by non-payment notice holder rights negotiable instrument", "Federal", ("Negotiable Instruments", "", ["dishonour"]))
q("B13", "contract", "How do I register a company in Pakistan?",
  "incorporation of a company registration with SECP requirements", "Federal", ("Companies Act", "", ["incorporation"]), ("Companies Act", "", ["register"]))
q("B14", "contract", "I want to file a consumer complaint against an online seller.",
  "consumer complaint defective service product consumer court", "Punjab", ("Punjab Consumer Protection", "", ["consumer court"]), ("Punjab Consumer Protection", "", ["complaint"]))
q("B15", "contract", "Is charging interest on a personal loan allowed in Punjab?",
  "interest on private loans prohibition penalty", "Punjab", ("Prohibition of Interest on Private Loans", "", ["interest"]))
q("B16", "contract", "A moneylender is harassing me for a loan.",
  "debtor protection moneylender recovery of debts relief", "Punjab", ("Debtors", "", ["debt"]), ("Prohibition of Interest on Private Loans", "", ["interest"]))
# ---------------------------------------------------------------- property / land
q("P01", "property", "Do I have to register the sale deed when buying a house?",
  "transfer of immovable property by sale must be by registered instrument", "Punjab", ("Transfer of Property", "sale how made"), ("Registration Act", "documents of which registration is compulsory"))
q("P02", "property", "How can I legally gift my house to my son?",
  "gift of immovable property how it is made registered instrument", "Punjab", ("Transfer of Property", "", ["gift"]))
q("P03", "property", "Can I get my mortgaged house back after repaying the loan?",
  "right of mortgagor to redeem mortgaged property after payment", "Punjab", ("Transfer of Property", "", ["redeem"]))
q("P04", "property", "Does a lease of more than one year need to be registered?",
  "lease of immovable property how made year registered deed", "Punjab", ("Transfer of Property", "leases how made"))
q("P05", "property", "My neighbour sold his house. Do I have a first right to buy it?",
  "right of pre-emption shufa of neighbour or co-sharer on sale of property", "Punjab", ("Pre-emption", "", ["pre-emption"]))
q("P06", "property", "Someone has illegally occupied my plot. What can I do?",
  "illegal possession of immovable property by land grabber remedy", "Punjab", ("Protection of Ownership of Immovable Property", "", ["illegal possession"]), ("Protection of Ownership of Immovable Property", "illegal possession"))
q("P07", "property", "The seller refuses to complete the sale after taking an advance. Can I force him?",
  "specific performance of agreement to sell property enforce contract", "Federal", ("Specific Relief", "", ["specific performance"]))
q("P08", "property", "I was forcibly thrown out of my property. Can I get possession back quickly?",
  "suit by person dispossessed of immovable property recover possession", "Federal", ("Specific Relief", "dispossessed"))
q("P09", "property", "What is mutation and how do I get my land record updated?",
  "mutation of land records patwari revenue record of rights", "Punjab", ("Punjab Land Revenue", "", ["mutation"]))
q("P10", "property", "My house is in a katchi abadi. Can I get ownership rights?",
  "regularisation of katchi abadi proprietary rights residents", "Punjab", ("Katchi Abadis", "", ["katchi abadi"]))
q("P11", "property", "How many years do I have to sue to recover money I lent?",
  "limitation period for suit to recover money lent time limit", "Federal", ("Limitation Act", "", ["money lent"]), ("Limitation Act", "", ["money payable"]))
q("P12", "property", "How much compensation will I get if the government acquires my land?",
  "compensation for compulsory acquisition of land determination of amount", "Punjab", ("Land Acquisition", "", ["compensation"]))
q("P13", "property", "Is a gift made by a will valid for the whole property?",
  "will testamentary disposition of property succession", "Federal", ("Succession Act", "", ["will"]))
# ---------------------------------------------------------------- courts / procedure / evidence
q("R01", "procedure", "When can a court reject my plaint?",
  "rejection of plaint grounds civil suit", "Federal", ("Code of Civil Procedure", "rejection of plaint"))
q("R02", "procedure", "How much court fee do I pay to file a civil suit for money?",
  "court fee payable on plaint ad valorem value of suit", "Federal", ("Court", "", ["ad valorem"]))
q("R03", "procedure", "What is the time limit to file an appeal against a decree?",
  "limitation period for filing appeal against decree days", "Federal", ("Limitation Act", "", ["appeal"]))
q("R04", "procedure", "Is there a quick court for small money claims?",
  "small claims court summary procedure value of claim", "Federal", ("Small Claims", "", ["small claim"]))
q("R05", "procedure", "Can we settle our dispute through mediation instead of court?",
  "alternative dispute resolution mediation centre settlement punjab", "Punjab", ("Alternate Dispute Resolution", "", ["mediation"]), ("Alternative Dispute Resolution", "", ["mediation"]))
q("R06", "procedure", "I cannot afford a lawyer. Is there free legal help?",
  "free legal aid for poor persons legal aid authority", "Punjab", ("Legal Aid", "", ["legal aid"]))
q("R07", "procedure", "Is an email or WhatsApp message accepted as evidence in court?",
  "admissibility of electronic documents and electronic evidence", "Federal", ("Electronic Transactions Ordinance", "", ["electronic"]), ("Qanun-e-Shahadat", "", ["electronic"]))
q("R08", "procedure", "Is a digital signature legally valid?",
  "validity of electronic signature advanced electronic signature legal recognition", "Federal", ("Electronic Transactions Ordinance", "", ["signature"]))
q("R09", "procedure", "Can someone be kept in police custody for more than 24 hours?",
  "detention of arrested person not more than twenty-four hours production before magistrate", "Federal", ("Code of Criminal Procedure", "", ["twenty-four hours"]), ("Constitution of the Islamic", "safeguards as to arrest"))
q("R10", "procedure", "Which court decides a family dispute like divorce or custody?",
  "jurisdiction of family court over marriage custody maintenance disputes", "Punjab", ("Family Court", "jurisdiction"))
# ---------------------------------------------------------------- rights / constitution / misc
q("G01", "rights", "Is freedom of speech protected in Pakistan?",
  "fundamental right freedom of speech expression restrictions", "Federal", ("Constitution of the Islamic", "freedom of speech"))
q("G02", "rights", "Do I have a right to a fair trial?",
  "right to fair trial and due process", "Federal", ("Constitution of the Islamic", "right to fair trial"))
q("G03", "rights", "Is it legal for an employer to discriminate between men and women?",
  "equality of citizens non-discrimination on grounds of sex", "Federal", ("Constitution of the Islamic", "equality of citizens"))
q("G04", "rights", "Is education a legal right for my child?",
  "right to free and compulsory education for children", "Federal", ("Constitution of the Islamic", "right to education"))
q("G05", "rights", "Can the government take my property without compensation?",
  "protection of property rights compulsory acquisition", "Federal", ("Constitution of the Islamic", "property rights"))
q("G06", "rights", "How can I get information from a government office?",
  "right of access to information request public body time limit", "Punjab", ("Right to Information", "", ["information"]))
q("G07", "rights", "My relative was detained illegally. Can the court order his release?",
  "habeas corpus illegal detention high court direction release", "Federal", ("Code of Criminal Procedure", "habeas corpus"), ("Constitution of the Islamic", "", ["habeas corpus"]))
q("G08", "rights", "What happens if a driver kills someone in an accident? Can the family claim compensation?",
  "compensation to family of person killed by negligence wrongful act", "Federal", ("Fatal Accidents", "", ["compensation"]))
q("G09", "rights", "How can I get my CNIC corrected?",
  "national identity card issuance correction NADRA registration", "Federal", ("National Database and Registration", "", ["identity card"]))
q("G10", "rights", "What law protects women from violence in Punjab?",
  "protection of women against violence law punjab protection centre", "Punjab", ("Protection of Women Against Violence", "", ["violence"]))
# ---------------------------------------------------------------- out of scope / no answer in corpus
q("N01", "negative", "What is the income tax rate for salaried people this year?",
  "income tax slab rates for salaried individuals", "Federal", neg=True)
q("N02", "negative", "How do I get a US visa?",
  "united states visa application requirements", "Federal", neg=True)
q("N03", "negative", "Who will win the cricket world cup?",
  "cricket world cup winner prediction", "Federal", neg=True)
q("N04", "negative", "What is the capital gains tax on shares?",
  "capital gains tax on sale of shares", "Federal", neg=True)
q("N05", "negative", "Can you write me a poem about justice?",
  "write a poem about justice", "Federal", neg=True)
q("N06", "negative", "What are the rules for importing a car into Pakistan?",
  "customs duty and rules for importing a vehicle", "Federal", neg=True)

# ---------------------------------------------------------------- tightened after checking the real section headings
def _edit(id_, *rel, question=None, query_en=None):
    g = next(x for x in GOLD if x["id"] == id_)
    g["rel"] = [dict(act=r[0], head=r[1] if len(r) > 1 else "", has=list(r[2]) if len(r) > 2 else []) for r in rel]
    if question:
        g["question"] = question
    if query_en:
        g["query_en"] = query_en


_edit("T09", ("Islamabad Rent Restriction", "increase of rent"))
_edit("T10", ("Islamabad Rent Restriction", "eviction of tenant"))
_edit("F02", ("Family Court", "khula; dower; maintenance"))
_edit("F07", ("Family Court", "khula; dower; maintenance"))
_edit("F08", ("Family Court", "khula; dower; maintenance"))
_edit("F09", ("Muslim Personal Law", "application of the muslim personal law"))
_edit("F10", ("Enforcement of Women", "complaint to the ombudsman"), ("Enforcement of Women", "delivery of possession"))
_edit("F11", ("Child Marriage Restraint", "punishment"))
_edit("F13", ("Guardians and Wards", "appointment"))
_edit("C11", ("Constitution of the Islamic", "safeguards as to arrest"), ("Code of Criminal Procedure", "twenty-four hours"))
_edit("C15", ("Code of Criminal Procedure", "when police may arrest without warrant"))
_edit("C18", ("Control of Narcotic Substances", "punishment for contravention"))
_edit("C20", ("Code of Criminal Procedure", "power to direct admission to bail"),
      question="Someone filed a false case against me. Can I get bail before I am arrested?",
      query_en="pre-arrest bail anticipatory bail false criminal case high court sessions court")
_edit("R09", ("Code of Criminal Procedure", "twenty-four hours"), ("Constitution of the Islamic", "safeguards as to arrest"))
_edit("L01", ("Punjab Labour Code", "termination of employment agreement"), ("Punjab Labour Code", "notice of termination"),
      ("Punjab Labour Code", "prohibited grounds for termination"), ("Industrial Relations Act", "individual grievances"))
_edit("L13", ("Punjab Labour Code", "termination of employment agreement"), ("Punjab Labour Code", "notice of termination"),
      ("Industrial Relations Act", "individual grievances"))
_edit("L02", ("Payment of Wages", "time of payment of wages"), ("Punjab Labour Code", "payment of wages authority"))
_edit("L07", ("Domestic Workers", "rights and entitlements"))
_edit("L08", ("Factories Act", "daily hours"), ("Factories Act", "weekly hours"), ("Factories Act", "extra pay for overtime"), ("Punjab Labour Code", "normal working hours"))
_edit("L09", ("Industrial Relations Act", "application for registration"))
_edit("L10", ("Workmen", "employer's liability for compensation"))
_edit("L11", ("Old-Age Benefits", "old-age pension"))
_edit("L12", ("Bonded Labour", "abolition of bonded labour system"))
_edit("B07", ("Partnership Act", "dissolution"))
_edit("B09", ("Stamp Act", "instruments chargeable with duty"))
_edit("B10", ("Arbitration Act", "arbitration agreement"), ("Arbitration Act", "appointment"), ("Arbitration Act", "appoint arbitrator"))
_edit("B11", ("Contract act", "guarantee"))
_edit("B12", ("Negotiable Instruments", "dishonour by non-payment"), ("Negotiable Instruments", "notice of dishonour"))
_edit("B13", ("Companies Act, 2017", "registration of memorandum"), ("Companies Act, 2017", "effect of registration"), ("Companies Act, 2017", "incorporation"))
_edit("P01", ("Transfer of Property", '"sale" defined'), ("Registration Act", "documents of which registration is compulsory"))
_edit("P02", ("Transfer of Property", "gift"))
_edit("P03", ("Transfer of Property", "right of mortgagor to redeem"))
_edit("P07", ("Specific Relief", "cases in which specific performance"))
_edit("P08", ("Specific Relief", "", ["dispossessed"]))
_edit("P12", ("Land Acquisition", "determining compensation"), ("Land Acquisition", "amount of compensation"))
_edit("P13", ("Succession Act", "capable of making wills"), ("Succession Act", "execution of unprivileged wills"),
      question="Who can make a valid will and how must it be signed?",
      query_en="who is capable of making a will and execution of a will witnesses")
_edit("R07", ("Electronic Transactions", "legal recognition of electronic forms"), ("Qanun-e-Shahadat", "", ["modern devices"]))

if __name__ == "__main__":
    import collections
    import json
    from pathlib import Path
    out = Path(__file__).with_name("gold.json")
    out.write_text(json.dumps(GOLD, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(GOLD), "questions", dict(collections.Counter(g["cat"] for g in GOLD)), "->", out)
