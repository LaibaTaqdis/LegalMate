# Analyser + retrieval evaluation (real DeepSeek analyser on the gold questions)

108 legal questions, 6 out-of-scope. DeepSeek this run: 111 live call(s), 3 cache hit(s), 133921 in / 10919 out tokens, ~$0.0226 (cap 120/run, 200/day; today so far 146)

## Analyser behaviour

- intents on real legal questions: {'legal_question': 108}
- asked a clarifying question on 0 of 108 real questions (0%): []
- out-of-scope questions correctly declined: 5 of 6
  - N01 `What is the income tax rate for salaried people this year?` -> out_of_scope
  - N02 `How do I get a US visa?` -> out_of_scope
  - N03 `Who will win the cricket world cup?` -> out_of_scope
  - N04 `What is the capital gains tax on shares?` -> out_of_scope
  - N05 `Can you write me a poem about justice?` -> out_of_scope
  - N06 `What are the rules for importing a car into Pakistan?` -> legal_question
- jurisdiction contradicting the profile: none

## Retrieval from the analyser's queries (the passages the answer step actually sees)

| queries used | hit@1 | hit@3 | hit@5 | hit@8 | hit@20 | MRR |
|---|---|---|---|---|---|---|
| my hand-written query_en (reference) | 61.1 | 79.6 | 84.3 | 89.8 | 89.8 | 0.709 |
| analyser: plain query only | 40.7 | 57.4 | 64.8 | 70.4 | 73.1 | 0.511 |
| analyser: statutory query only | 52.8 | 70.4 | 74.1 | 74.1 | 75.0 | 0.613 |
| analyser: section-heading query only | 56.5 | 72.2 | 77.8 | 78.7 | 79.6 | 0.652 |
| analyser: all queries merged (production) | 58.3 | 76.9 | 83.3 | 88.9 | 91.7 | 0.687 |

## Real questions with no relevant passage in the top 8 (production queries)

- **F06** (rank 14) _Who gets custody of the children after divorce?_
  - queries: ['who gets custody of children after divorce mother father rights', 'Guardians and Wards Act custody of minor welfare of the child', 'Custody of children after divorce welfare of minor']
- **F08** (rank 9) _My husband did not pay my haq mehr. Where can I recover it?_
  - queries: ['wife recover unpaid dower haq mehr from husband', 'Muslim Family Laws Ordinance dower recovery suit family court', 'Suit for recovery of dower by wife against husband']
- **F10** (rank >20) _My brothers are not giving me my share of our father's land._
  - queries: ["brothers refusing to give sister her share in father's inherited agricultural land", 'Punjab Land Revenue Act partition of joint land inheritance shares among legal heirs', 'Partition of immovable property among co-owners legal heirs suit for partition']
- **F13** (rank >20) _Who can be appointed guardian of a minor's property?_
  - queries: ['who can be appointed guardian of property of a minor', 'Guardians and Wards Act appointment of guardian of minor property', 'Guardians and Wards Act section 12 guardian of person and property of minor']
- **C17** (rank >20) _Someone called pretending to be from my bank and took money from my ac_
  - queries: ['money taken from bank account by fraud phone call what remedy', 'Prevention of Electronic Crimes Act 2016 unauthorised access to bank account fraud', 'Punishment for unauthorised access to information system and identity theft']
- **L02** (rank >20) _My employer hasn't paid my salary for two months._
  - queries: ['employer has not paid salary for two months remedy for employee', 'Punjab Payment of Wages Act recovery of unpaid wages complaint labour court', 'Recovery of wages unpaid by employer time limit for claim']
- **L12** (rank >20) _My factory owner is keeping me as a bonded labourer to repay a loan._
  - queries: ['employer forcing worker to work to repay loan bonded labour', 'Bonded Labour System (Abolition) Act 1992 Punjab prohibition of bonded labour', 'Punishment for enforcing bonded labour and freeing bonded labourer from debt']
- **B04** (rank >20) _My 16 year old son signed an agreement. Is it valid?_
  - queries: ['is an agreement signed by a minor valid and enforceable', 'Contract Act 1872 capacity to contract age of majority minor agreement void', 'Agreements by a minor are void ab initio capacity to contract']
- **P05** (rank >20) _My neighbour sold his house. Do I have a first right to buy it?_
  - queries: ['right of pre-emption for neighbour when adjacent house sold', 'Punjab Pre-emption Act 1991 right of shafi-i-jar neighbour', 'Who may claim right of pre-emption']
- **P06** (rank 17) _Someone has illegally occupied my plot. What can I do?_
  - queries: ['remedy for person illegally dispossessed of immovable property plot', 'Specific Relief Act suit for recovery of possession of immovable property', 'Suit by person dispossessed of immovable property']
- **R02** (rank >20) _How much court fee do I pay to file a civil suit for money?_
  - queries: ['court fee payable on a civil suit for recovery of money', 'Court Fees Act 1870 ad valorem fee on plaint for money suit', 'Fee on plaint in suit for money Court Fees Act']
- **R10** (rank >20) _Which court decides a family dispute like divorce or custody?_
  - queries: ['which court has jurisdiction to decide divorce and child custody cases', 'Family Courts Act 1964 jurisdiction of family court over dissolution of marriage and custody', 'Jurisdiction of Family Court in suits for dissolution of marriage and custody of children']