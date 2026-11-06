# Retrieval evaluation

Model: `BAAI/bge-small-en-v1.5`  |  chunks: 21,138  |  labelled questions: 108  |  out-of-scope questions: 6

Hit rate (%) = share of questions with a relevant law section in the top k results; MRR = mean reciprocal rank.

## Configurations (question rewritten to English by the analyser, `query_en`)

| configuration | hit@1 | hit@3 | hit@5 | hit@10 | hit@20 | MRR |
|---|---|---|---|---|---|---|
| keyword only (BM25) |  55.6 |  73.1 |  81.5 |  89.8 |  96.3 | 0.667 |
| vector only, with bge query prefix |  50.9 |  72.2 |  82.4 |  89.8 |  91.7 | 0.646 |
| vector only, no prefix |  48.1 |  71.3 |  76.9 |  84.3 |  89.8 | 0.613 |
| hybrid 1:1 |  62.0 |  78.7 |  86.1 |  94.4 |  97.2 | 0.724 |
| hybrid vector 2 : keyword 1 |  62.0 |  78.7 |  87.0 |  93.5 |  96.3 | 0.725 |
| hybrid vector 1 : keyword 2 |  63.0 |  78.7 |  84.3 |  94.4 |  99.1 | 0.734 |
| hybrid 1:1, no jurisdiction handling |  55.6 |  73.1 |  81.5 |  93.5 |  97.2 | 0.676 |
| hybrid 1:1, no de-duplication |  62.0 |  78.7 |  86.1 |  94.4 |  97.2 | 0.724 |

## Weight grid (vector : keyword), jurisdiction on

| w_vec | w_lex | rrf_k | hit@1 | hit@5 | hit@10 | MRR |
|---|---|---|---|---|---|---|
| 1 | 1 | 60 | 62.0 | 86.1 | 94.4 | 0.724 |
| 1 | 1 | 20 | 60.2 | 85.2 | 95.4 | 0.717 |
| 1 | 1 | 10 | 55.6 | 85.2 | 95.4 | 0.693 |
| 3 | 1 | 60 | 63.0 | 87.0 | 93.5 | 0.727 |
| 1 | 0.5 | 60 | 62.0 | 87.0 | 93.5 | 0.725 |
| 1 | 0.25 | 60 | 61.1 | 87.0 | 92.6 | 0.718 |
| 1 | 1.5 | 60 | 63.0 | 84.3 | 93.5 | 0.734 |
| 1 | 3 | 60 | 62.0 | 83.3 | 93.5 | 0.727 |
| 1 | 1 | 100 | 62.0 | 88.0 | 94.4 | 0.724 |

Best on this set: vector 1 : keyword 1, rrf_k 100.

## Does the analyser rewrite matter? (English questions only)

| input to retrieval | hit@1 | hit@3 | hit@5 | hit@10 | hit@20 | MRR |
|---|---|---|---|---|---|---|
| rewritten query (`query_en`) |  61.5 |  77.9 |  87.5 |  94.2 |  97.1 | 0.719 |
| raw user question |  27.9 |  45.2 |  52.9 |  57.7 |  68.3 | 0.389 |

## By category (best configuration)

| category | n | hit@1 | hit@3 | hit@5 | hit@10 | hit@20 | MRR |
|---|---|---|---|---|---|---|---|
| contract | 16 |  75.0 |  75.0 |  93.8 | 100.0 | 100.0 | 0.796 |
| criminal | 20 |  60.0 |  75.0 |  80.0 |  90.0 |  90.0 | 0.695 |
| family | 14 |  64.3 |  85.7 |  85.7 |  85.7 | 100.0 | 0.724 |
| labour | 13 |  38.5 |  76.9 |  92.3 | 100.0 | 100.0 | 0.590 |
| procedure | 10 |  50.0 |  70.0 |  90.0 | 100.0 | 100.0 | 0.659 |
| property | 13 |  69.2 |  84.6 |  84.6 |  92.3 |  92.3 | 0.779 |
| rights | 10 |  70.0 |  90.0 |  90.0 | 100.0 | 100.0 | 0.814 |
| tenancy | 12 |  66.7 |  75.0 |  91.7 |  91.7 | 100.0 | 0.737 |

Roman-Urdu questions (retrieved via their English rewrite): 4 questions,  75.0 | 100.0 | 100.0 | 100.0 | 100.0 | 0.833

## 'No source found' threshold

Top-1 signals for real legal questions vs out-of-scope questions (higher = more confident a source exists).

| signal | real questions: min / p10 / median | out-of-scope: max / median | gap (p10 real - max out-of-scope) |
|---|---|---|---|
| best cosine similarity | 0.623 / 0.705 / 0.768 | 0.739 / 0.661 | -0.034 |
| best keyword score | 14.299 / 20.907 / 29.528 | 22.467 / 16.420 | -1.560 |
| fused score | 0.019 / 0.019 / 0.020 | 0.020 / 0.019 | -0.000 |

## Questions without a relevant result in the top 5 (13 of 108)

- **B01** (rank 7) _Is a verbal agreement legally binding?_
  - expected: Contract act / what agreements are contracts
  - got: ermination > Section 141 - Form of employment agreement || 03 - Exclusion of evidence of oral agreement (part 2/4) || 03 - Exclusion of evidence of oral agreement (part 4/4)
- **C10** (rank 7) _A man took money from me promising a job abroad and disappeared._
  - expected: Pakistan Penal Code / cheating and dishonestly inducing; Emigration Ordinance / promoter
  - got: nt, falsification, forgery, fraud, deception (part 3/3) || nt, falsification, forgery, fraud, deception (part 2/3) || es Against Property > Section 415 - Cheating (part 1/3)
- **C18** (rank 6) _What is the punishment for possessing drugs?_
  - expected: Control of Narcotic Substances / punishment for contravention
  - got: ncing the trafficking of narcotic drugs etc (part 8/16) || ncing the trafficking of narcotic drugs etc (part 7/16) || cing the trafficking of narcotic drugs etc (part 13/16)
- **F06** (rank 14) _Who gets custody of the children after divorce?_
  - expected: Guardians and Wards / welfare of the minor; Guardians and Wards / welfare
  - got: Section 24 - Rescue of destitute and neglected children || ustment of the custody of destitute and neglected child || ion And Rehabilitation > Section 25 - Temporary custody
- **F09** (rank 14) _Do daughters get a share in their father's property?_
  - expected: Muslim Personal Law / application of the muslim personal law
  - got:  Laws Ordinance, 1961 (Punjab) > Section 4 - Succession || ng To Tenants > Section 19A - Succession to the tenancy || ce (Amendment) Act, 1929 (Punjab) > Section 3 - Savings
- **L02** (rank 6) _My employer hasn't paid my salary for two months._
  - expected: Payment of Wages / time of payment of wages; Punjab Labour Code / payment of wages authority
  - got: nd penalty for malicious or vexatious claims (part 2/4) || nd penalty for malicious or vexatious claims (part 1/4) || r recovering under payments and non-payments (part 2/3)
- **R02** (rank 7) _How much court fee do I pay to file a civil suit for money?_
  - expected: Court / ad valorem
  - got: nd jurisdictional value to be the same in certain suits ||  9; * * * * * * *; Application for review of judgment,  || nd jurisdictional value to be the same in certain suits
- **P02** (rank 8) _How can I legally gift my house to my son?_
  - expected: Transfer of Property / gift
  - got: er VII - Of Gifts > Section 123 - Transfer how effected || s Of Immovable Property > Section 107 - Leases how made ||  of oral gift of an immovable property, not being a SET
- **G04** (rank 7) _Is education a legal right for my child?_
  - expected: Constitution of the Islamic / right to education
  - got: lsory Education > Section 4 - Duty to provide education || on > Section 3 - Right to free and compulsory education || nd Compulsory Education Act, 2014 > Preamble - Preamble
- **T05** (rank 16) _My landlord switched off electricity and water to force me out._
  - expected: Punjab Rented Premises / obligations of landlord
  - got: isconnect service pipes and cut off supplies (part 1/3) || isconnect service pipes and cut off supplies (part 3/3) ||  prevent damage, contamination and waste etc (part 2/5)
- **C02** (rank >20) _The police are refusing to register my FIR._
  - expected: Code of Criminal Procedure / information in cognizable cases
  - got: XIV > Section 173 - Report of police-officer (part 2/3) || ons of the District Public Safety Commission (part 1/3) || ion 71 - Reasons for refusal to register to be recorded
- **C20** (rank >20) _Someone filed a false case against me. Can I get bail before I am arrested?_
  - expected: Code of Criminal Procedure / power to direct admission to bail
  - got: may be taken in case of non-bailable offence (part 3/3) ||  - Of Bail > Section 499 - Bond of accused and sureties || re by Magistrate before whom person arrested is brought
- **P05** (rank >20) _My neighbour sold his house. Do I have a first right to buy it?_
  - expected: Pre-emption / pre-emption
  - got: operty where more than one persons are equally entitled || tion 6 - Persons in whom the right of pre-emption vests || ption Act, 1991 Doc > Section 12 - Right to revoke sale
