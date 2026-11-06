# Chat pilot

Live run of the engine on selected scenarios. See `chat/pilot.py`.

## S03: The police are refusing to register my FIR for the theft of my motorbike.
_expect: CrPC s.154 (needs the statutory hint)_

```
analysis: {"intent": "legal_question", "language": "en", "jurisdiction": null, "emergency": false, "needs_clarification": false, "search_queries": ["police refuse to register FIR for stolen motorbike how to get report recorded", "Code of Criminal Procedure duty of police to record information of cognizable offence theft", "Code of Criminal Procedure section 154 information in cognizable cases"], "tag": "Criminal Law"}
The law says that when you give information about a cognizable offence (an offence the police can investigate on their own, like theft) to the officer in charge of a police station, it must be written down, read back to you and signed by you [1]. If the police station officer unjustifiably refuses to register the FIR, the District Public Safety Commission can direct the District Police Officer to look into it and have the FIR registered [2].
-- What the law says: Under **Section 154**, every information about a cognizable offence given orally to the officer in charge of a police station must be **reduced to writing**, read over to you, and **signed by you**, and its substance entered in a book [1]. After receiving such information, the station house officer must send a report to a Magistrate and investigate the facts [3]. If the officer in charge **unjustifiably refused or avoided** registering the FIR, the District Public Safety Commission can direct the District Police Officer to hold an inquiry and cause the FIR to be registered under section 154, and report back within **forty-eight hours** [2]. Please note these passages carry a note that they were amended later, so the current wording should be checked.
  1. Go back to the police station and give your information orally or in writing, and ask that it be written down, read over to you and signed by you [1].
  2. If the officer still refuses, put your complaint in writing to the District Public Safety Commission, asking it to direct the District Police Officer to inquire and register the FIR [2].
  3. Keep a copy of whatever you submit and note the date, so you can show the refusal clearly [2].
  4. For advice on your exact situation, speak to a qualified lawyer.
!! The passages say these provisions were amended later, so check the current text of the law before you act, and do not delay because time limits can matter.
outro: Would you like help understanding what details to put in your written complaint to the Commission?
  [1] Code of Criminal Procedure, 1898 | Section 154 - Information in cognizable cases | p. 79 | quote verified=True
      “Every information relating to the commission of a cognizable offence if given orally to an officer in charge of a police-station, shall be reduced to writing”
      NOTE: Amended later by Code of Criminal Procedure (Amendment) Act, 2026. Amendments are not merged into this text.
  [2] Police Act, 1861 | Section 55 - Furicaons of the District Public Safety Commission | pp. 23-24 | quote verified=True
      “unjustifiably refused or avoided to register any First Information Report, to conduct an inquiry into the matter and cause the registration of he First Informa
  [3] Code of Criminal Procedure, 1898 | Section 157 - Procedure where cognizable offence suspected | pp. 80-81 | quote verified=True
      “he shall forthwith send a report of the same to a Magistrate empowered to take cognizance of such offence upon a police-report”
      NOTE: Amended later by Code of Criminal Procedure (Amendment) Act, 2026. Amendments are not merged into this text.
confidence 80 (relevance 80, agreement 90, recency 67) | sufficient=True | follow-ups: ['What should I write in my complaint to the District Public Safety Commission?', "What does 'cognizable offence' mean?"]
verify: {"issues": [], "cited_fraction": 0.8, "quote_rate": 1.0, "unverified_sections": [], "unverified_numbers": []}
```

## S05: What is khula and how does a woman get it?
_expect: Family Courts Act / Dissolution of Muslim Marriages Act_

```
analysis: {"intent": "legal_question", "language": "en", "jurisdiction": "Punjab", "emergency": false, "needs_clarification": false, "search_queries": ["how a woman obtains khula dissolution of marriage by court", "Muslim Family Laws Ordinance khula right of wife to dissolve marriage", "Dissolution of marriage by wife khula grounds and procedure"], "tag": "Family Law"}
Khula is a form of **dissolution of marriage** that a wife can seek through the Family Court [1][2]. In Punjab, the court first tries to reconcile the couple, and if that fails, it passes the decree and may ask the wife to give back part of her dower [2].
-- What the law says: A suit for **dissolution of marriage, including Khula**, can be filed in the Family Court [1]. The court holds a **pre-trial hearing** and tries to bring about a compromise between the parties [2]. If reconciliation fails in a suit for dissolution of marriage, the court shall **immediately pass a decree** for dissolution [2]. In a Khula case, the court may direct the wife to **surrender up to fifty percent of her deferred dower** or up to twenty-five percent of her admitted prompt dower to the husband [2]. A wife may also claim dissolution including Khula in her written statement if the husband has sued for restitution of conjugal rights [3].
  1. File a suit for dissolution of marriage (Khula) in the Family Court [1].
  2. Attend the pre-trial hearing, where the court will try to reconcile you and your husband [2].
  3. If reconciliation fails, the court will pass the dissolution decree and may order you to return part of your dower [2].
!! If reconciliation fails, the court can order you to give up up to 50% of your deferred dower or up to 25% of your prompt dower, so be ready for this.
outro: Would you like to know more about how dower is calculated in a Khula case?
  [1] Family Courts Act, 1964 | Schedule, Rule 1 to 9 - Dissolution of marriage [including Khula; Dower; Maintenance | pp. 13-14 | quote verified=True
      “1. Dissolution of marriage [including Khula].”
  [2] Family Courts Act, 1964 | Section 10 - Pre-trial proceedings | pp. 7-8 | quote verified=True
      “in case of dissolution of marriage through khula, may direct the wife to surrender up to fifty percent of her deferred dower or up to twenty-five percent of he
  [3] Family Courts Act, 1964 | Section 9 - Written statement | p. 6 | quote verified=True
      “A defendant wife may, in the written statement to a suit for restitution of conjugal rights, make a claim for dissolution of marriage including khula”
confidence 81 (relevance 68, agreement 100, recency 85) | sufficient=True | follow-ups: ['What is deferred dower and prompt dower?', 'Can a woman get Khula without going to court?']
verify: {"issues": [], "cited_fraction": 1.0, "quote_rate": 1.0, "unverified_sections": [], "unverified_numbers": []}
```

## S06: My company fired me without notice. Can I challenge it?
_expect: Punjab Labour Code termination / IR Act s.33_

```
analysis: {"intent": "legal_question", "language": "en", "jurisdiction": "Punjab", "emergency": false, "needs_clarification": false, "search_queries": ["employee dismissed without notice can challenge termination before labour court", "Punjab Industrial Relations Act unfair labour practice dismissal without notice", "Remedies for workman dismissed without notice or inquiry"], "tag": "Labour & Employment"}
Yes, you can challenge it. In Punjab, a permanent workman must normally get **one month's notice** or one month's wages instead of notice, and any dismissal must be by a **written order that states the reason** [1].
-- What the law says: For a permanent workman, ending a job for any reason other than misconduct needs **one month's notice** from the employer, or one month's wages paid instead of notice [1]. Your services cannot be ended except by a **written order that clearly states the reason** [1]. If you are aggrieved by the termination, you may take action under **Section 33 of the Punjab Industrial Relations Act 2010**, which deals with individual grievances [1]. The Punjab Labour Code, 2026 also says an employee must be given a chance to defend himself before termination for conduct or performance, and that dues must be paid within two working days of termination [2].
  1. Check whether your appointment letter or contract calls you a permanent workman, because the notice rule applies to permanent workmen [1].
  2. Ask the employer in writing for the written termination order and the reason stated in it [1].
  3. Keep copies of your contract, salary records and any termination letter, and note the date you were fired.
  4. If you want to challenge it, consider using the individual grievance route under Section 33 of the Punjab Industrial Relations Act 2010 [1], and speak to a labour lawyer about the time limits.
!! Grievance and appeal routes usually have strict time limits, so do not delay in getting advice about your deadline.
outro: Would you like to know what details a written termination order should contain?
  [1] Industrial and Commercial Employment (Standing Orders) Ordinance, 1968 | Schedule, Rule 12 - Termination of employment | p. 12 | quote verified=True
      “he may [take action in accordance with the provisions of ] [Section 33] of the [Punjab Industrial Relations Act 2010”
  [2] Punjab Labour Code, 2026 | Section 146 - Termination of employment agreement | p. 75 | quote verified=True
      “shall be paid before the expiry of the second working day from the day of termination”
confidence 74 (relevance 59, agreement 90, recency 87) | sufficient=True | follow-ups: ['What should a written termination order contain?', 'What is the individual grievance route under Section 33?']
verify: {"issues": [], "cited_fraction": 0.8, "quote_rate": 1.0, "unverified_sections": [], "unverified_numbers": []}
```

## S07: Is a verbal agreement legally binding?
_expect: Contract Act s.10_

```
analysis: {"intent": "legal_question", "language": "en", "jurisdiction": null, "emergency": false, "needs_clarification": false, "search_queries": ["is an oral verbal agreement legally enforceable in Pakistan", "Contract Act 1872 oral agreement validity free consent consideration", "What agreements are contracts"], "tag": "Contract Law"}
Yes, in general a verbal (oral) agreement can be a valid contract if the basic conditions of a contract are met [1]. But some agreements must be in writing, and proving a verbal term can be hard [2][1].
-- What the law says: All agreements are contracts if they are made by the **free consent** of parties competent to contract, for a **lawful consideration** and with a **lawful object**, and are not expressly declared void [1]. Consent means the parties agree on the same thing in the same sense [3], and it is free when it is not caused by coercion, undue influence, fraud, misrepresentation or mistake [3]. The law also preserves any rule that requires a contract to be in writing, in the presence of witnesses, or to be registered [1]. For example, a written agreement silent on a term may stop a party from later proving a verbal term on that subject [2]. In the text available to me, this passage is marked as amended later, so the current wording should be checked [2].
  1. Check that both sides freely agreed on the same terms, for a lawful purpose, with something given in return [1][3].
  2. Find out whether your type of agreement must be in writing or registered, because then a verbal deal may not be enough [1].
  3. Keep any proof of the verbal terms, such as messages, receipts or witnesses, since proving oral terms can be difficult [2].
  4. For anything valuable or long-term, put the agreement in writing and consider asking a qualified lawyer to review it [1].
!! A verbal agreement may be valid, but if the law requires writing or registration for that kind of deal, or if a written contract already covers the point, you may not be able to rely on the spoken words.
outro: Would you like to tell me what kind of agreement it is (for example, a sale, rent or job) so I can point to the closer rules?
  [1] Contract act, 1872 | Section 10 - What agreements are contracts | p. 14 | quote verified=True
      “All agreements are contracts if they are made by the free consent of parties competent to contract, for a lawful consideration and with a lawful object”
  [2] Qanun-e-Shahadat Order, 1984 | Section 103 - Exclusion of evidence of oral agreement | p. 48 | quote verified=True
      “A hires lodgings of B for a year, and regularly stamped agreement, drawn up by an advocate, is made between them. It is silent on the subject of board.”
      NOTE: Amended later by Qanun-e-Shahadat (Amendment) Act, 2025. Amendments are not merged into this text.
  [3] Contract act, 1872 | Section 13 to 14 - “Consent” defined; “Free consent” defined | p. 15 | quote verified=True
      “Consent is said to be free when it is not caused by— (1) coercion, as defined in section 15, or (2) undue influence”
confidence 81 (relevance 75, agreement 100, recency 69) | sufficient=True | follow-ups: ['Does a rent agreement have to be in writing?', 'How can I prove a verbal agreement in court?']
verify: {"issues": [], "cited_fraction": 1.0, "quote_rate": 1.0, "unverified_sections": [], "unverified_numbers": []}
```

## S12: I need help with my property
_expect: too vague: clarifying questions with options_

```
analysis: {"intent": "legal_question", "language": "en", "jurisdiction": null, "emergency": false, "needs_clarification": true, "search_queries": ["property dispute rights of owner", "Transfer of Property Act ownership possession remedy", "Suit by person dispossessed of immovable property"], "tag": "Property Law"}
To give you accurate guidance I need a little more information. Tap an option or type your own answer:
  ? What is the property problem?  ['Tenant or landlord dispute', 'Buying or selling', 'Inheritance share', 'Someone occupying my land']
  ? Which city is the property in?  ['Lahore', 'Islamabad', 'Other Punjab city', 'Other province']
verify: null
```

## S16: Police are at my door arresting my brother without any warrant. What are his rights?
_expect: emergency note + CrPC / Constitution Art. 10_

```
analysis: {"intent": "legal_question", "language": "en", "jurisdiction": null, "emergency": true, "needs_clarification": false, "search_queries": ["rights of person arrested without warrant by police", "Code of Criminal Procedure arrest without warrant grounds and safeguards", "Code of Criminal Procedure section 54 when police may arrest without warrant"], "tag": "Criminal Law"}
Police in Pakistan can arrest a person without a warrant in certain situations, for example when there is reasonable suspicion of a serious (cognizable) offence [1]. So the lack of a warrant alone does not make the arrest unlawful, but the police must still follow the rules [1][2].
-- What the law says: A police officer may arrest without a warrant a person who has been involved in a **cognizable offence** (a serious offence police can investigate on their own), or against whom a reasonable complaint, credible information or reasonable suspicion exists [1]. If a senior officer sends a subordinate to make the arrest, the officer must carry a **written order** naming the person and the offence, and must tell the arrested person the substance of that order and show it if asked [2]. The passages available to me do not set out the full rights of an arrested person (such as being told the grounds of arrest or being produced before a Magistrate), so those details should be checked in the current law. These passages are from the Code of Criminal Procedure, 1898, which a note says was amended later, so the current text should be checked [1][2].
  1. Calmly ask the police officers which offence your brother is suspected of and whether they have a written order; if a subordinate officer is arresting him, he can ask to see that order [2].
  2. Note down the officers' names, badge numbers, police station and the time of arrest, without interfering with the police.
  3. Do not resist or obstruct the officers, because obstructing a police officer in the execution of duty is itself a ground for arrest without warrant [1].
  4. Contact a qualified lawyer as soon as possible to check the current law and your brother's full rights.
!! If you or someone else is in immediate danger, call Police on 15 or Rescue on 1122 now. (Numbers shown for Pakistan; confirm local helplines in the Emergency section.) The law on arrest has been amended after these passages were written, so confirm the current rules with a lawyer quickly, as time limits for producing an arrested person before a Magistrate may apply.
outro: Would you like me to explain what a cognizable offence means in simple words?
  [1] Code of Criminal Procedure, 1898 | Section 54 - When police may arrest without warrant | pp. 43-44 | quote verified=True
      “Any police-officer may, without an order from a Magistrate and without a warrant, arrest— first, any person who has been concerned in any cognizable offence”
      NOTE: Amended later by Code of Criminal Procedure (Amendment) Act, 2026. Amendments are not merged into this text.
  [2] Code of Criminal Procedure, 1898 | Section 56 - Procedure when police officer deputes subordinate to arrest without warrant | p. 44 | quote verified=True
      “he shall deliver to the officer required to make the arrest an order in writing, specifying the person to be arrested and the offence”
      NOTE: Amended later by Code of Criminal Procedure (Amendment) Act, 2026. Amendments are not merged into this text.
confidence 88 (relevance 100, agreement 82, recency 65) | sufficient=True | follow-ups: ['What does cognizable offence mean?', 'What should we do right after the arrest?']
verify: {"issues": [], "cited_fraction": 0.64, "quote_rate": 1.0, "unverified_sections": [], "unverified_numbers": []}
```

---
DeepSeek this run: 9 live call(s), 2 cache hit(s), 18793 in / 3270 out tokens, ~$0.0075 (cap 14/run, 200/day; today so far 155)