"""Same-happening pairs, September 2026 — the labels the verified matching tier
(correlation/verify.py) was measured on. Article pairs (founding articles of two
events) -> do they report the same real-world happening?

TWO SETS, AND THEY ARE NOT EQUALLY TRUSTED.

BATCH_3_CROSSLINGUAL — two human labellers, batch MGDmtLPZOdjy (2026-09-17),
compiled 2026-09-25 by `tools.gold_crosslingual --compile MGDmtLPZOdjy`: 150
tasks, 43 same / 225 not; 40 pairs the labellers disputed are excluded, never
recorded as negatives. Seeds are non-English founders, candidates English events
at headline cosine >= 0.30. Its "no"s include judgement calls the verifier reads
the other way ("India squad announced" vs "Naman Dhir gets maiden call-up" is
labelled different; it is one announcement) — read disagreements before trusting
a precision number off this set.

SILVER_SAME_LANGUAGE — labelled by Claude from each event's English headline and
summary (2026-09-25), NOT by a person, and not yet ratified. 135 pairs sampled
from a week's candidates across headline cosine bands 0.39–1.0, 64 same / 64 not,
7 left unlabelled as genuinely ambiguous. It exists because the other two sets
carry almost no same-language templated local news — two cooperative societies'
results, two districts' Lok Adalats — which is exactly where similarity fails. A
labeller batch built from it replaces it when answered; until then, quote its
numbers as silver.

Measured on them (docs/CANONICALIZATION.md):

    AUC                      silver   batch 3   gold_pairs (July)
    gist embedding            0.913    0.992     0.940
    first body chunk          0.456    0.956     0.832
    Jev, headline+summary     0.993    0.985     0.964
"""

# (seed_article_id, candidate_article_id) -> same real-world happening?
BATCH_3_CROSSLINGUAL: dict[tuple[str, str], bool] = {
    ("9dae8f20-4df4-4b09-ac5d-d5c190352107", "45306997-c541-4ff9-8ced-a5bd3fd98d7d"): False,  # headline:0.12 · Camel trapped on railway tracks in Gujar || SC asks CJ of Gujarat HC to register cas
    ("9dae8f20-4df4-4b09-ac5d-d5c190352107", "d1edc439-f96f-42fb-9aee-3ac3d0d8fe0e"): False,  # headline:0.12 · Camel trapped on railway tracks in Gujar || Fatigue, rostering: Pilot body flags 6 d
    ("48dbcae9-67d1-4dc3-b98f-fa3ec895c21c", "a3d4b687-d386-483a-892c-8bce635a57d2"): False,  # headline:0.16 · High Court clarifies GBA license is not  || Fortis moves Supreme Court against Delhi
    ("48dbcae9-67d1-4dc3-b98f-fa3ec895c21c", "2190ae5d-fd9a-46bf-bcdc-020746b46b21"): False,  # headline:0.14 · High Court clarifies GBA license is not  || Chennai Corporation collects 6.60 lakh i
    ("b3e993f6-c2b6-43eb-a8cc-6aa6d8a82365", "d31e1f7e-034b-4800-aff5-3c3246e6a146"): True,  # headline:0.44 · Jiram Valley Naxal attack case; 10 convi || Death penalty for all 10 convicts in 201
    ("b3e993f6-c2b6-43eb-a8cc-6aa6d8a82365", "5451c0a6-d3bd-4764-8b98-5aaea7085315"): False,  # headline:0.16 · Jiram Valley Naxal attack case; 10 convi || Man posing as Naxal to frighten villager
    ("44122f6b-4cef-4de9-a3b2-cce8dbffe122", "28f53e43-b4c2-4365-9c8c-83ea0ae6544b"): False,  # headline:0.38 · Houthi Attempted Attack on Mecca Reporte || India 'deeply concerned' over alleged Ho
    ("2a0c97fc-8c00-4506-83c8-b2412f9cb943", "f1b21c8a-2fbe-4b77-aeda-62315f630b7f"): False,  # headline:0.19 · Farmers protest against stopping water s || Maradu water treatment plant set to add 
    ("2a0c97fc-8c00-4506-83c8-b2412f9cb943", "6b2e0531-9abc-4ad7-8647-f4f05c336a02"): False,  # headline:0.15 · Farmers protest against stopping water s || Residents block key stretch near Ambur d
    ("b45e6a8e-bd75-45aa-a4f1-03ef66265d7c", "5bb2ed1e-fabf-49ac-a1c6-d8d9e19a2804"): False,  # headline:0.14 · Bagalkote officials issued notice over p || US limits visas for South African offici
    ("b45e6a8e-bd75-45aa-a4f1-03ef66265d7c", "32a243ff-567e-497c-ad81-2dc0de8eed74"): False,  # headline:0.14 · Bagalkote officials issued notice over p || Tamil Nadu Assembly: Files on sanitation
    ("429cf853-f006-4461-a573-f3ad7c0be9f7", "8895d77a-924a-4e5d-928a-e001ba1a90e7"): False,  # headline:0.13 · TMC leader questions Ganpati pandal buil || A.P. launches free online single-window 
    ("429cf853-f006-4461-a573-f3ad7c0be9f7", "6b867268-b2f9-44ff-bbf8-5da590382087"): False,  # headline:0.11 · TMC leader questions Ganpati pandal buil || Ganpati visarjan: Thane noise levels hit
    ("4f7cdd6e-7baa-45b3-9ac6-751f97d487b6", "cb8ce0cd-e99c-438b-af0e-8437b7074558"): False,  # headline:0.12 · Aaditya Thackeray rejects BJP allegation || India rejects Pakistan-China Boundary Jo
    ("6e645d8f-dbd4-4f0b-8a42-88210468068a", "d023375f-4ffd-4d94-867d-850cf6a08356"): True,  # headline:0.46 · BJP members are vultures, they wait for  || BJP leaders are like vultures, who explo
    ("6e645d8f-dbd4-4f0b-8a42-88210468068a", "2b67b422-79c3-4b91-aeb4-621d929ccc40"): False,  # headline:0.11 · BJP members are vultures, they wait for  || A visa that came in time, a flood they e
    ("839352f5-a471-4f11-a102-2d3ad55f8748", "0c336a1c-18ce-4270-a776-28640d04d93c"): False,  # headline:0.21 · 46th Gauri Ganesha Festival Commences in || KSRTC to operate 2,400 special buses for
    ("839352f5-a471-4f11-a102-2d3ad55f8748", "2f6b722d-0893-4480-92e1-799886fb037b"): False,  # headline:0.12 · 46th Gauri Ganesha Festival Commences in || Keralam CM launches nature festival logo
    ("093ba2b6-9a71-427c-87cc-1f5bdc343cd2", "1e962550-b7f2-4444-b08c-fd1ac0fc39ad"): False,  # headline:0.15 · Matthew Wade retires from all cricket || Former BJP MLA Narendra Pawar steps down
    ("6ac5ed57-bc54-49a9-9309-f0a163a6836b", "1c3c6e73-6a6d-41d5-bfd1-3d68e5159434"): False,  # headline:0.20 · UPI merchant fees to end free digital pa || No rethink: Govt firm on UPI merchant fe
    ("e0a88999-cd04-4d50-9faf-d47e29e7367e", "3779692c-22aa-46b5-9fe9-28bff44292c8"): True,  # headline:0.62 · Government proposes mandatory CCTV in me || India proposes mandatory CCTVs at medica
    ("e0a88999-cd04-4d50-9faf-d47e29e7367e", "fe547a24-f3e8-403a-8c82-c3b6376600a8"): False,  # headline:0.17 · Government proposes mandatory CCTV in me || Drug Control raids expose painkiller sal
    ("a3f7a651-7c51-4654-8630-3236797d00b0", "0b63602e-1523-41e1-a0b6-f4750e6fb5b7"): False,  # headline:0.36 · Clash between ABVP and NSUI at Delhi Uni || Die Is Caste In DUSU Elections As NSUI A
    ("a3f7a651-7c51-4654-8630-3236797d00b0", "e04adc53-9397-480c-8e8b-752e55537c2f"): False,  # headline:0.19 · Clash between ABVP and NSUI at Delhi Uni || AMD partners with Delhi University to tr
    ("74d54a94-f9ed-43e5-9a2a-7131b239f084", "ac0bdd3f-f59b-45f8-bd45-7ed738b0099e"): False,  # headline:0.14 · Madikeri Dasara festival date changed ag || England bowl first again in second ODI a
    ("3bc04265-3598-4bb9-8df4-2081c8460806", "f2dde99f-b82f-4dad-9040-38b5bb76b186"): False,  # headline:0.19 · Husband's wife crushed in front of chore || Man Arrested for Killing Wife Over Marit
    ("3bc04265-3598-4bb9-8df4-2081c8460806", "0549edf6-21f5-4aed-a706-141c1af6d50f"): False,  # headline:0.18 · Husband's wife crushed in front of chore || ICE agent accused of shooting Venezuelan
    ("4221b657-8d27-4b19-b9b8-304a07158fbb", "cb8ce0cd-e99c-438b-af0e-8437b7074558"): True,  # headline:1.00 · India rejects China-Pakistan Boundary Jo || India rejects Pakistan-China Boundary Jo
    ("4221b657-8d27-4b19-b9b8-304a07158fbb", "58105978-1f60-4181-8f6a-3b17d78dc37a"): False,  # headline:0.21 · India rejects China-Pakistan Boundary Jo || No basis in international law: China rej
    ("3b3581b6-93a9-4441-83cf-17ad1d240d2c", "69d16847-d222-489c-b294-283eff38e825"): False,  # headline:0.13 · Three individuals rob motorcycle rider a || BMC plans 46cr repairs, noise barriers o
    ("3b3581b6-93a9-4441-83cf-17ad1d240d2c", "1530cb8b-c7c0-43f1-9575-5f57b6d631ac"): False,  # headline:0.10 · Three individuals rob motorcycle rider a || Bangladesh to tour Nepal for three T20Is
    ("6cf63173-7d3e-4e08-bc18-2d56f13cc440", "28f09cc7-1736-4324-8509-7286668ed6c1"): False,  # headline:0.18 · Asian Games 2026: Suchika, Harshveer, an || Asian Games 2026: Gonsalves-Beg Pair To 
    ("6cf63173-7d3e-4e08-bc18-2d56f13cc440", "0d37013c-80f7-4988-9542-a6b2bdc829dc"): False,  # headline:0.17 · Asian Games 2026: Suchika, Harshveer, an || Kushal Malla back in Nepal's squad for A
    ("34b1427b-1c65-448a-b071-4c76d83a78e3", "806be43e-518c-4969-bc79-a9b151289942"): False,  # headline:0.18 · Girl scream 'I won't die', accused flees || 10 fake doctors held for running clinics
    ("34b1427b-1c65-448a-b071-4c76d83a78e3", "f5e7307c-b672-4193-96a2-44856696b08e"): False,  # headline:0.12 · Girl scream 'I won't die', accused flees || Brawl between neighbours after harassmen
    ("e5df9cc3-d40c-4a81-84f2-635eac7deff5", "c3569f35-c215-46f8-8063-c02207d53ad6"): False,  # headline:0.14 · All Karnataka Folk Artists Federation de || Folk song workshop held for Pang school 
    ("e5df9cc3-d40c-4a81-84f2-635eac7deff5", "356228a6-c497-436c-87c7-3a42fcc0b08c"): False,  # headline:0.10 · All Karnataka Folk Artists Federation de || Dasara: Kambala set for October 18 and 1
    ("c590e375-30ec-4d43-a1a7-125c2bf65040", "2c9d6a75-43d8-4e39-ae44-bf28aaaca917"): True,  # headline:0.56 · N. Chandrasekaran reappointed as Tata So || Tata Sons reappoints N Chandrasekaran as
    ("c590e375-30ec-4d43-a1a7-125c2bf65040", "6f8ac11c-0a4e-4c6a-8fea-e9a4d67d65b9"): False,  # headline:0.30 · N. Chandrasekaran reappointed as Tata So || Trusts may urge Tata Sons to seek RBI re
    ("fb1f205f-2486-4e10-8831-e333151d09d2", "67ffeb0f-f442-4ff7-a0c6-487c998bc25c"): False,  # headline:0.15 · BJP denies alliance in Punjab as Akali f || Punjab Ambedkar Statue Row: BJP Leader I
    ("fb1f205f-2486-4e10-8831-e333151d09d2", "21895b56-5a74-4c44-8653-fe2d344168f3"): False,  # headline:0.15 · BJP denies alliance in Punjab as Akali f || Nestle completes 50 yrs of partnership w
    ("994fd59e-a1cc-44e9-a5e7-03d10efab103", "05d27648-4c5d-4889-9917-da9be02b7659"): False,  # headline:0.15 · Youth dies after falling into a canal wh || Fake alert: MEA denies reports of world 
    ("994fd59e-a1cc-44e9-a5e7-03d10efab103", "c87f4dd0-7cc1-4bcc-b9a2-2b83ed63236c"): False,  # headline:0.14 · Youth dies after falling into a canal wh || Hyderabad Man Dies Mysteriously In US
    ("970cad07-a081-407b-98bd-70513e4e6517", "ae312c5d-317d-4f22-b496-e706ae44939a"): False,  # headline:0.26 · Petition filed in Supreme Court to cance || Lahore High Court dismisses Rizwan's pet
    ("627c10df-c40a-4b93-8990-0017a906a3a0", "ddef607a-0014-4fac-8d4f-2c6f69e5d305"): False,  # headline:0.17 · Article 371(J) is a safeguard for Kalyan || Sports City, IT park, CCTV camera networ
    ("ac01ce15-5c4f-4e27-a19b-89d1f9ee4ea8", "4ae833b0-af28-48f4-874c-65386e56a858"): True,  # headline:0.46 · United States deploys weapons in space f || US acknowledges for first time that it h
    ("ac01ce15-5c4f-4e27-a19b-89d1f9ee4ea8", "087c7f3f-19c6-47df-b098-66226df54db7"): False,  # headline:0.20 · United States deploys weapons in space f || US Fed hikes interest rates for first ti
    ("77342588-0fc4-4a1c-993d-ddfea3b1e808", "7c0f4599-2ae7-4746-bc91-5891c0064176"): False,  # headline:0.14 · Demand to declare Wadagera taluk drought || New Green Card rules from September 18: 
    ("77342588-0fc4-4a1c-993d-ddfea3b1e808", "202c57f1-0d31-42c1-bf41-24ee44e7f116"): False,  # headline:0.13 · Demand to declare Wadagera taluk drought || Sri Lanka lose rain-affected warm-up aga
    ("2e02f4b7-eeec-46db-b8d0-670989d53a83", "2401c912-c3de-4364-bdd2-674130a4037d"): False,  # headline:0.14 · Ground report: Local roads near Samruddh || US-Contracted Vessel Hit By Iranian Miss
    ("2e02f4b7-eeec-46db-b8d0-670989d53a83", "c1afe10e-2f96-429d-9226-6f09ebebfd3b"): False,  # headline:0.12 · Ground report: Local roads near Samruddh || Despite no rain, Agumbe Ghat riddled wit
    ("aef525cb-694d-45b6-b810-5b63a762272a", "9d788cfa-c5ed-40ff-a99e-5ff7c16da542"): False,  # headline:0.12 · Nandini booths to be set up at Indira Ca || Rayachoti set for major infrastructure p
    ("aef525cb-694d-45b6-b810-5b63a762272a", "356228a6-c497-436c-87c7-3a42fcc0b08c"): False,  # headline:0.11 · Nandini booths to be set up at Indira Ca || Dasara: Kambala set for October 18 and 1
    ("6341ae54-98da-4c87-98e5-b69368aab9d1", "4777ca39-9aae-4a41-a1db-7865afb8570e"): False,  # headline:0.13 · Iran mocks United States with Minesweepe || VCK joined the alliance for Ministerial 
    ("6341ae54-98da-4c87-98e5-b69368aab9d1", "19e805fc-232d-441d-9242-c159c32cc208"): False,  # headline:0.11 · Iran mocks United States with Minesweepe || AI translation vs English: Viral post by
    ("f55443e2-39b4-4d81-8f9d-a2c6f363eff8", "050ad08d-c6e9-4bbe-9141-04f28ab14768"): True,  # headline:0.49 · Chennai Pattinapakkam fishermen protest  || Fishermen urge Tamil Nadu government to 
    ("f55443e2-39b4-4d81-8f9d-a2c6f363eff8", "94a51f78-4615-457a-b955-4f079f4c22f6"): False,  # headline:0.28 · Chennai Pattinapakkam fishermen protest  || Tamil Nadu government identifies three s
    ("38bea791-812d-429b-8355-d2c7ca573a84", "52c2b736-e2db-4072-8d9e-5740cc422af2"): False,  # headline:0.21 · Will a 44-year record cyclone hit India  || Mandhana's record ton powers India to se
    ("38bea791-812d-429b-8355-d2c7ca573a84", "585a43ff-cb7c-4540-840b-2ad0fce1a2b7"): False,  # headline:0.16 · Will a 44-year record cyclone hit India  || Collector reviews monsoon preparedness i
    ("eadfa20c-4075-4faa-b810-9c5bb7c62904", "92cd5ab6-fd7b-46c1-829e-1e323c1a8574"): False,  # headline:0.15 · Anant Nag First Reaction After Receiving || Meet Sethuraman Panchanathan, first Indi
    ("9edeb2a8-c08a-47a6-8e6c-2b3cc25f7719", "685b468d-7651-486e-b791-f5b73d536510"): False,  # headline:0.29 · Pant appointed captain of Rest of India  || List of India, India A and Rest of India
    ("4e0eea26-0f33-4a5b-b400-4fc946f9ff5c", "705d1532-a25d-44d7-af8f-b020f3e4f75d"): False,  # headline:0.15 · ED is BJP's election machine alleges Ran || CPI alleges vote deletions in A.P. SIR
    ("4e0eea26-0f33-4a5b-b400-4fc946f9ff5c", "c2ef7d39-c17c-4559-be3b-ce7996859ba1"): False,  # headline:0.12 · ED is BJP's election machine alleges Ran || Government is surrendering to American p
    ("c5a2da5a-493c-479f-af9c-baea2560ea4d", "9c215f4b-c741-4f3e-aeee-17d3ec5ec5f0"): False,  # headline:0.20 · Rajasthan: What is the current state of  || CJP to launch Adivasi School Thik Karo c
    ("c5a2da5a-493c-479f-af9c-baea2560ea4d", "4d22f4e7-6801-4fac-b397-336fcf1a0826"): False,  # headline:0.18 · Rajasthan: What is the current state of  || Inter-State cyber fraudster from Rajasth
    ("c2a88a65-73e9-4bdc-b39f-98c08f0e7901", "0c336a1c-18ce-4270-a776-28640d04d93c"): False,  # headline:0.19 · Ganesha Festival held peacefully under t || KSRTC to operate 2,400 special buses for
    ("b0ba8ecc-5d8d-4bae-9160-132fb3964ba6", "1d479874-df17-49fb-b30d-f3787d2233b6"): True,  # headline:0.47 · Box Office Report: Hanuman Ansh joins 30 || Hanuman Ansh box office collections day 
    ("b0ba8ecc-5d8d-4bae-9160-132fb3964ba6", "6e1327f1-3a97-4814-a2a6-3d477e7259f7"): False,  # headline:0.14 · Box Office Report: Hanuman Ansh joins 30 || IIA Kerala chapter office-bearers to ass
    ("51e640ac-c236-4a2c-82d1-bbb8830268ba", "f967b573-ff1d-4898-8e72-5bfc40e446d4"): True,  # headline:0.46 · Prime Minister Narendra Modi receives bi || Putin, Trump extend birthday wishes to P
    ("51e640ac-c236-4a2c-82d1-bbb8830268ba", "4dfcf699-851d-4d35-bfc3-39021a8d4ace"): False,  # headline:0.34 · Prime Minister Narendra Modi receives bi || PM Modi Birthday: From RSS worker to thi
    ("a235cce9-f190-41b0-86db-9a18cc7a2bc8", "f967b573-ff1d-4898-8e72-5bfc40e446d4"): False,  # headline:0.14 · Dharmendra Pradhan offers prayers at Maa || Putin, Trump extend birthday wishes to P
    ("a235cce9-f190-41b0-86db-9a18cc7a2bc8", "bd19029a-d148-4d35-94b1-a836f85a1645"): False,  # headline:0.12 · Dharmendra Pradhan offers prayers at Maa || NDA allies to meet in Varanasi tomorrow 
    ("ef413b6b-622e-4b92-9468-8cc456646a4e", "a3d4b687-d386-483a-892c-8bce635a57d2"): False,  # headline:0.50 · Punjab Government Challenges High Court  || Fortis moves Supreme Court against Delhi
    ("ef413b6b-622e-4b92-9468-8cc456646a4e", "30827730-d7ea-4611-9a88-1c2f67e482af"): False,  # headline:0.33 · Punjab Government Challenges High Court  || Rizwan challenges NCCIA summons in Lahor
    ("afecfe32-4152-4c51-9b7c-c35e3e0887a8", "7883bf42-68c2-4d3f-9cc0-76bf7a9d8b21"): False,  # headline:0.28 · Eshwar B. Khandre inaugurates new tree p || Increasing green cover should be our pri
    ("6831884e-3860-42d8-81ae-aed37516b00d", "3904708d-4df1-4d7e-9aa2-823d131a7cc2"): True,  # headline:0.46 · Tamil Nadu CM's deepfake video used for  || CB-CID registers case over deepfake vide
    ("ad199136-e5f0-417b-a63e-1ed9cf825918", "1b78fe88-8bd7-4b3b-af20-bac99e8a4489"): False,  # headline:0.21 · AYUSH health camp in Kumta taluk on Sept || Over 1,000 Cyberabad traffic police pers
    ("ad199136-e5f0-417b-a63e-1ed9cf825918", "13d1fa46-0626-442d-80ac-af226e4c1ac8"): False,  # headline:0.12 · AYUSH health camp in Kumta taluk on Sept || Case booked against six on charges of ki
    ("a967eb98-2d2a-4b17-87ae-825c7d4b81b5", "78cd659e-4440-49d5-af55-8cb314aef107"): False,  # headline:0.11 · CBS News releases photos of damage to US || Wild elephants cause scare in Belagavi d
    ("a967eb98-2d2a-4b17-87ae-825c7d4b81b5", "70db0188-1636-43b8-abc2-525f6bf7f0dc"): False,  # headline:0.11 · CBS News releases photos of damage to US || KNRUHS releases Phase-2 MBBS allotment l
    ("70d642fa-6b1b-4cc9-89c9-dad0f2db1a31", "7f8c11f3-d654-448c-abc7-b6ed20b210f6"): False,  # headline:0.15 · 6 crore grant sanctioned for STP unit in || SRM medical college launches mobile card
    ("70d642fa-6b1b-4cc9-89c9-dad0f2db1a31", "067e8bef-4160-47c1-a6e2-b167e963f171"): False,  # headline:0.13 · 6 crore grant sanctioned for STP unit in || Only Prime Minister’s Office can grant s
    ("abaad0f2-5e2c-4e58-a280-888b7b4ccb89", "622669bc-9ccd-4938-b51c-95a1c6c7f903"): False,  # headline:0.14 · Provide solution to Pandeshwar and Hoige || This Energy Solution Stock Jumps 40% Aft
    ("abaad0f2-5e2c-4e58-a280-888b7b4ccb89", "b75750e3-3120-4e1f-a2e1-9fae1f0a65fa"): False,  # headline:0.10 · Provide solution to Pandeshwar and Hoige || Three held for alleged robbery near Aluv
    ("e9a9898e-0f42-4769-bd5e-84b3b5d9a481", "8e98e1b8-cd88-418a-b627-00271480140e"): False,  # headline:0.15 · Congress high command issues directive t || Attackers Exploit Issabel Framework Flaw
    ("e9a9898e-0f42-4769-bd5e-84b3b5d9a481", "26c39113-52d6-43f7-bba0-3a5fce53d5ec"): False,  # headline:0.11 · Congress high command issues directive t || Expedite resolution of revenue issues: C
    ("bd9206d4-07bf-4424-98f3-71763a83df74", "54513ed3-827d-48ce-b415-9af75c2f5700"): True,  # headline:0.55 · Father and daughter murdered by relative || Father, daughter hacked to death over pr
    ("bd9206d4-07bf-4424-98f3-71763a83df74", "f2dde99f-b82f-4dad-9040-38b5bb76b186"): False,  # headline:0.17 · Father and daughter murdered by relative || Man Arrested for Killing Wife Over Marit
    ("e047fca5-8bd6-4392-80f2-3a1488744c3f", "14c18ad2-dbd6-4085-af04-3a714aadde81"): False,  # headline:0.12 · Leopard kills calf in Aladakatte village || Imam unlikely to play rest of Lord's Tes
    ("e047fca5-8bd6-4392-80f2-3a1488744c3f", "033dbb9d-893d-4c59-9628-19c0c45b3e9b"): False,  # headline:0.10 · Leopard kills calf in Aladakatte village || Tenant farmer, daughter dead at Gandrai 
    ("0ab3410c-a98b-464f-a954-39b01b3ae5c6", "04367e65-f7fe-4864-ac2c-0060f0ef7641"): False,  # headline:0.17 · CCTV captures mobile snatching incident  || Elon Musk’s Starlink mobile plan should 
    ("0ab3410c-a98b-464f-a954-39b01b3ae5c6", "5b86df56-2b30-425a-a1f1-80a1eb8ee5c5"): False,  # headline:0.14 · CCTV captures mobile snatching incident  || Muslim Youth League protests against Mai
    ("da65e4f5-0a10-4157-8286-b188a0f8849b", "05d27648-4c5d-4889-9917-da9be02b7659"): True,  # headline:0.53 · MEA Denies Rumors Regarding Illness of W || Fake alert: MEA denies reports of world 
    ("da65e4f5-0a10-4157-8286-b188a0f8849b", "a72b0f7d-893f-4a08-837d-e37338dd6495"): False,  # headline:0.22 · MEA Denies Rumors Regarding Illness of W || CISF handles movement of over 1,000 dele
    ("3cc821fa-a842-40e4-b415-ae31200788cc", "ad912351-1408-4e47-bdd4-fc328aab1df5"): True,  # headline:0.72 · Anant Nag receives Dadasaheb Phalke Awar || Actor Anant Nag to be honoured with Dada
    ("3cc821fa-a842-40e4-b415-ae31200788cc", "92cd5ab6-fd7b-46c1-829e-1e323c1a8574"): False,  # headline:0.11 · Anant Nag receives Dadasaheb Phalke Awar || Meet Sethuraman Panchanathan, first Indi
    ("41f9e52e-53ac-4610-b66d-8ff69db50b81", "9b63767d-0d8d-4c16-b62a-00afc029e563"): False,  # headline:0.00 · Gurugram police arrest two men for hitti || 59-year-old man injured in wild boar att
    ("41f9e52e-53ac-4610-b66d-8ff69db50b81", "1fbd67c4-0f83-4dda-bc3b-f2904693dfa5"): False,  # headline:0.00 · Gurugram police arrest two men for hitti || Bombay Court allows correction of school
    ("d5ac5cd1-6bf1-47ff-a5a2-8528d735857c", "b6119dd1-9307-42e3-bcb8-6cde006768ba"): False,  # headline:0.13 · CEO Gitte Madhav visits various villages || Govt. augmenting power supply infra in v
    ("d5ac5cd1-6bf1-47ff-a5a2-8528d735857c", "c770f752-84f5-4b03-ac4f-15163b442f6a"): False,  # headline:0.09 · CEO Gitte Madhav visits various villages || Salesforce CEO wants AI firms to follow 
    ("d4937295-df17-4de2-ad67-c84e3c6a7c63", "f967b573-ff1d-4898-8e72-5bfc40e446d4"): False,  # headline:0.16 · PM Modi celebrates 76th birthday with re || Putin, Trump extend birthday wishes to P
    ("d4937295-df17-4de2-ad67-c84e3c6a7c63", "a4c52f3b-87e9-406f-bcf0-360b45023987"): False,  # headline:0.15 · PM Modi celebrates 76th birthday with re || PM Modi birthday: Wishes pour in from ac
    ("f4ec4f2d-91da-4275-bb20-af0856a6a736", "82ba0d49-90f7-4313-ab9a-56e30d63a614"): True,  # headline:0.47 · PCB to decide on Rizwan and Imam after N || PCB To Decide Rizwan, Imam Fate After Pr
    ("f4ec4f2d-91da-4275-bb20-af0856a6a736", "30827730-d7ea-4611-9a88-1c2f67e482af"): False,  # headline:0.32 · PCB to decide on Rizwan and Imam after N || Rizwan challenges NCCIA summons in Lahor
    ("b27c0ef9-08be-4f21-aac5-2c4cf755bc91", "28f53e43-b4c2-4365-9c8c-83ea0ae6544b"): True,  # headline:0.56 · India condemns Houthi drone attack attem || India 'deeply concerned' over alleged Ho
    ("b27c0ef9-08be-4f21-aac5-2c4cf755bc91", "dfe8cf47-e905-45b9-8d54-6b5e2e4c7247"): False,  # headline:0.40 · India condemns Houthi drone attack attem || Exercise restraint: Mirwaiz on reported 
    ("f7cdb5f6-c5f9-43fb-8ddc-ade1073869bc", "a3d4b687-d386-483a-892c-8bce635a57d2"): False,  # headline:0.44 · Supreme Court quashes Karnataka High Cou || Fortis moves Supreme Court against Delhi
    ("f7cdb5f6-c5f9-43fb-8ddc-ade1073869bc", "31562ada-13c4-4125-97b9-b17495317a90"): False,  # headline:0.30 · Supreme Court quashes Karnataka High Cou || Bengaluru land dispute: Karnataka High C
    ("d30662bf-b0d2-49f2-8abd-3a4d50b5d6cb", "8707bcc8-7cbd-41ae-92fc-89310eb9fcac"): True,  # headline:0.52 · Trump praises PM Modi for India's action || Trump praises PM Modi’s opium crackdown,
    ("62268d53-f9a6-4a17-a921-87ef1f14d60d", "0a7c4e01-cf4e-4855-81c1-a26aac9e3554"): True,  # headline:0.40 · US blocks Palestinian President's visa,  || US denies visa to Palestinian President 
    ("62268d53-f9a6-4a17-a921-87ef1f14d60d", "7734e3a1-865c-4f3b-968d-2675417992c5"): False,  # headline:0.13 · US blocks Palestinian President's visa,  || Katchatheevu row resurfaces in Assembly
    ("0bb36f61-5715-4e8d-9756-c1d4813a029a", "f6ba05cf-4dea-44fb-a9b2-cc07bce12519"): False,  # headline:0.16 · Nepal faces risk of another glacial lake || Islamabad faces ultimate Mecca pact test
    ("0bb36f61-5715-4e8d-9756-c1d4813a029a", "2c9d6a75-43d8-4e39-ae44-bf28aaaca917"): False,  # headline:0.13 · Nepal faces risk of another glacial lake || Tata Sons reappoints N Chandrasekaran as
    ("73b823e3-7813-41e1-82d0-e69858233254", "5360257d-79c3-4418-8531-3bbc0ddc368b"): False,  # headline:0.14 · Youth stuck in grill of closed bungalow, || Odisha man beaten to death; set afire af
    ("73b823e3-7813-41e1-82d0-e69858233254", "720ec1b3-6d55-4e19-b876-0ac7bf8baeb9"): False,  # headline:0.12 · Youth stuck in grill of closed bungalow, || Forest Department enhances safety of loc
    ("8497610b-5333-4773-becb-1ac865f403c9", "ad912351-1408-4e47-bdd4-fc328aab1df5"): False,  # headline:0.10 · Twenty-four achievers selected for Shiva || Actor Anant Nag to be honoured with Dada
    ("8497610b-5333-4773-becb-1ac865f403c9", "3dd2255d-22df-43ef-afa9-91f965517f62"): False,  # headline:0.10 · Twenty-four achievers selected for Shiva || Man shoots dead teacher in Bijnor for en
    ("7068e1e8-2398-4c28-a7eb-3a7f1d4f4e70", "457f24df-8b94-4d12-bc34-d322baf8e766"): False,  # headline:0.27 · Rainfall likely in many parts of the sta || Subdued rainfall is likely across southe
    ("7068e1e8-2398-4c28-a7eb-3a7f1d4f4e70", "d09b1a09-996d-4443-aff9-98993e4f0af2"): False,  # headline:0.25 · Rainfall likely in many parts of the sta || Bengaluru likely to receive light rainfa
    ("cb6f9bf7-f6a7-491f-bc8e-8af3996127b6", "465b51e3-5c05-4df2-8aac-d52abf8e92c7"): False,  # headline:0.19 · SBI ATM rules changing from October 1 20 || Registration of Births and Deaths Act to
    ("cb6f9bf7-f6a7-491f-bc8e-8af3996127b6", "356228a6-c497-436c-87c7-3a42fcc0b08c"): False,  # headline:0.18 · SBI ATM rules changing from October 1 20 || Dasara: Kambala set for October 18 and 1
    ("6c4b3e9e-50b6-4adf-901b-9b3167f7ceb1", "888711e4-7041-4f70-a6ad-3283e8b2ffcb"): False,  # headline:0.13 · Farmer commits suicide due to crop loss  || Farmer tests positive for COVID-19 in Ku
    ("6c4b3e9e-50b6-4adf-901b-9b3167f7ceb1", "44bb6029-9e94-47ed-9e3f-8091f63902ae"): False,  # headline:0.12 · Farmer commits suicide due to crop loss  || Rowdy-sheeter violates externment order,
    ("cb535548-a4b1-4568-a9e4-ded3f24c4da5", "01e9abb3-1345-41d8-bfc9-3ddde9f838fd"): False,  # headline:0.18 · State-level selection: Gajendragada stud || School student injured in Idukki
    ("cb535548-a4b1-4568-a9e4-ded3f24c4da5", "02e2a907-9ed6-4a61-b327-e6a816c8e29a"): False,  # headline:0.15 · State-level selection: Gajendragada stud || India face tough selection calls as Afgh
    ("c3190cf0-8ebd-495b-8ac5-6eb48987383d", "1226aeda-59f1-49ee-8453-8baf9f3d5449"): False,  # headline:0.39 · Punjabi boy Naman Dhir selected for Indi || Naman Dhir, Auqib Nabi get maiden ODI ca
    ("c3190cf0-8ebd-495b-8ac5-6eb48987383d", "2e354d1f-127d-40d5-b381-9aebd7a50918"): False,  # headline:0.14 · Punjabi boy Naman Dhir selected for Indi || Gamer Akshaj Shenoy Leads Indian League 
    ("1abf96b3-1822-4735-bb2b-4eea86a0ebf7", "cafbd6e5-e291-48ea-95df-2840fb0ede56"): True,  # headline:0.44 · European Union proposes ban on social me || EU moves to ban social media for under-1
    ("1abf96b3-1822-4735-bb2b-4eea86a0ebf7", "e97bc544-a2ee-4b37-97e6-69c9cfb73260"): False,  # headline:0.26 · European Union proposes ban on social me || Telangana police constable suspended for
    ("d9bb3583-0df8-4252-a0eb-54f95be859f8", "db54ca0e-1cba-484c-ae65-8d7221b69367"): False,  # headline:0.18 · Order issued prohibiting preparation of  || 13 bus stations in Telangana to turn int
    ("d9bb3583-0df8-4252-a0eb-54f95be859f8", "a57d06a0-5580-4199-8076-cb6b569eba1a"): False,  # headline:0.17 · Order issued prohibiting preparation of  || District Judge withdraws order prohibiti
    ("4897713e-9656-4a6d-9028-b242f9f46771", "d11d39cf-379d-4e79-9a71-49df5513acaa"): False,  # headline:0.22 · US Fed raises interest rates, impact on  || How US Fed Rate Hike Will Impact Gold Pr
    ("b787eca8-3470-4da4-a1b7-d76a5e7c12c1", "15c635be-843a-40b8-a869-9e296f7f87b5"): False,  # headline:0.17 · District level kabaddi tournament inaugu || Bengaluru: Tree park inaugurated in Pana
    ("59191a6c-b071-4f9c-b3b3-85023daef921", "9c3c92d6-2388-4cbc-9dbc-61d6c5e5c702"): False,  # headline:0.33 · Asian Games 2026: Indian athletes and me || Athletes Stranded Near Airport As Asian 
    ("ab257fab-a224-4daf-8c67-61c0d9b37554", "5964325b-683f-4684-9264-b57bc1e60941"): False,  # headline:0.41 · Ganesh idol immersion affected by drough || No Ganesh Idol Immersion In Water Bodies
    ("ab257fab-a224-4daf-8c67-61c0d9b37554", "988e98bd-d876-45b9-85dd-143b95657faa"): False,  # headline:0.37 · Ganesh idol immersion affected by drough || 20,000 cops, 19-km route: Hyderabad poli
    ("ab257fab-a224-4daf-8c67-61c0d9b37554", "64ce2caf-f4b3-4fc6-9b37-9523745631d3"): False,  # headline:0.37 · Ganesh idol immersion affected by drough || 6 Minors Drown In Lake Near Hyderabad Du
    ("ab257fab-a224-4daf-8c67-61c0d9b37554", "94175c1e-b980-403a-8156-5230c67f1c21"): False,  # headline:0.35 · Ganesh idol immersion affected by drough || Bharath confirms Ganesh idol immersion t
    ("0cf9df2a-5874-4309-9f96-3660d2665e36", "66591a2e-0820-4b9a-b963-aa5a56a1d730"): False,  # headline:0.27 · Government issues new framework for UPI  || UPI charges row: Chidambaram among 5 Con
    ("913ffc58-084b-4e70-bf92-e171333af091", "77b680c8-f3cd-46dd-abe2-85fa9cd49cab"): False,  # headline:0.21 · Dangerous bacteria found in water at rai || 85% of fuel dispensing nozzles checked a
    ("913ffc58-084b-4e70-bf92-e171333af091", "3e691dfb-8c10-4c47-8f50-d86a23377228"): False,  # headline:0.16 · Dangerous bacteria found in water at rai || Delhi Civic Body Cracks Down On Dangerou
    ("015ec7b9-dbe7-4d51-8587-8859d81592e0", "4dfcf699-851d-4d35-bfc3-39021a8d4ace"): False,  # headline:0.27 · Russian President Vladimir Putin conveys || PM Modi Birthday: From RSS worker to thi
    ("266b38c9-082e-4186-b298-0d4ec36ece8c", "6a610c03-e721-4e86-b590-002bb63c37f7"): True,  # headline:0.44 · Woman found dead in Doddaballapura lodge || 21-year-old woman found dead in lodge at
    ("266b38c9-082e-4186-b298-0d4ec36ece8c", "dce18846-2d0f-497f-b694-2ece18408267"): False,  # headline:0.34 · Woman found dead in Doddaballapura lodge || Tezpur University student found dead in 
    ("5b707f9f-de23-40d1-b7d1-c36a1e870e53", "c87f4dd0-7cc1-4bcc-b9a2-2b83ed63236c"): False,  # headline:0.24 · Chinese satellite that assisted Iran mys || Hyderabad Man Dies Mysteriously In US
    ("5b707f9f-de23-40d1-b7d1-c36a1e870e53", "4ae833b0-af28-48f4-874c-65386e56a858"): False,  # headline:0.20 · Chinese satellite that assisted Iran mys || US acknowledges for first time that it h
    ("494a4c54-0d11-4c60-9199-0a233c98b080", "364c9ca8-7ee3-4d19-9641-3c4bb73272f8"): False,  # headline:0.13 · Lucknow-Kanpur Expressway construction c || Lucknow woman jumps on moving car over d
    ("494a4c54-0d11-4c60-9199-0a233c98b080", "ea2b50bc-eff4-44d7-9058-d16880ac7bec"): False,  # headline:0.13 · Lucknow-Kanpur Expressway construction c || A Yash Thakur identity twist in Lucknow 
    ("a78ed79c-f369-46a6-b1ee-fc1790daeb26", "414c2829-738b-4b80-8817-1a26bd4c223d"): False,  # headline:0.77 · Basavadi Shivasharanara Hindu Samavesha  || Samiti opposes proposed Basavadi Shivash
    ("a78ed79c-f369-46a6-b1ee-fc1790daeb26", "72ca3f53-6bfb-4581-8166-6d530719592d"): False,  # headline:0.14 · Basavadi Shivasharanara Hindu Samavesha  || Cabinet approves two irrigation projects
    ("e540b2e6-b0b3-4fe8-8771-a768a19c2ee7", "a08f8e99-b355-41d3-9833-952b6b5a147a"): False,  # headline:0.39 · Amit Shah to inaugurate Biresthwara Soci || Union Home Minister Amit Shah to inaugur
    ("e540b2e6-b0b3-4fe8-8771-a768a19c2ee7", "816278ac-1dfb-4d25-8b92-af0ada238ffe"): False,  # headline:0.18 · Amit Shah to inaugurate Biresthwara Soci || PM to inaugurate three-day Semicon India
    ("3a87f441-a13f-4f6d-a336-219423d33366", "2a667bb5-a1f4-48e4-88f5-5e3eb2d85b06"): False,  # headline:0.17 · Bomb blast at liquor shop in Chandigarh || ED raids in Patiala, Pune and Chandigarh
    ("3a87f441-a13f-4f6d-a336-219423d33366", "9a32d188-c3f3-4c09-b733-c87d976538ba"): False,  # headline:0.15 · Bomb blast at liquor shop in Chandigarh || Two arrested as Gujarat police bust inte
    ("fda73476-bc04-4607-8a23-e03c10c61a4c", "d31e1f7e-034b-4800-aff5-3c3246e6a146"): True,  # headline:0.70 · Jhiram Naxal Attack: Death penalty for 1 || Death penalty for all 10 convicts in 201
    ("0cdb3ff2-1905-4f75-ba1a-50a87e76c544", "62e97f32-d8b3-4048-bbb3-e51dde92333b"): False,  # headline:0.09 · Sambhaji Brigade activists smear black i || As DJs face flak, Mumbai activists say a
    ("0cdb3ff2-1905-4f75-ba1a-50a87e76c544", "aa7a478a-e6f3-489f-aa59-a9b9c58ff588"): False,  # headline:0.09 · Sambhaji Brigade activists smear black i || CPI(M) general secretary M.A. Baby slams
    ("adfe957b-fd85-4e2a-8f0a-d9227e7495d1", "a54f12c6-a958-4fc9-8d58-658e1cc287c7"): False,  # headline:0.16 · Ensure no drinking water shortage in Ajj || Minister asks gram panchayats around Ben
    ("adfe957b-fd85-4e2a-8f0a-d9227e7495d1", "bd79c42f-f190-4b95-a9d2-4dc4461cc2b5"): False,  # headline:0.14 · Ensure no drinking water shortage in Ajj || SC tells RBI to ensure banks follow rule
    ("fbd4a59e-a66d-4e48-a2c0-3ff0448ea34e", "7f2709ac-5176-4374-8ad2-ae23e925762f"): True,  # headline:0.45 · Government withdraws Parks (Preservation || Karnataka government decides to withdraw
    ("fbd4a59e-a66d-4e48-a2c0-3ff0448ea34e", "54b35dbb-ebdf-4aa4-857d-d9e620cfc854"): False,  # headline:0.23 · Government withdraws Parks (Preservation || Hampshire U-turn on Kuggeleijn signing a
    ("dd4c2db1-cd27-49ef-a3b8-b5df539f27cd", "b2b1162d-d6d0-4c93-9843-e3c8de56a98a"): False,  # headline:0.16 · Free beautician training starts in Hosap || DVC starts issuing flood alerts for part
    ("dd4c2db1-cd27-49ef-a3b8-b5df539f27cd", "b7902cb3-a016-4ffa-aca9-64765706a631"): False,  # headline:0.14 · Free beautician training starts in Hosap || Ernakulam Government Medical College Hos
    ("a38c30e1-da21-4409-948a-56cabdffc12e", "cc606f94-ef4f-44c5-9a39-e7041a05e0f3"): False,  # headline:0.13 · Action taken after cracker factory blast || Mumbai's Cafe Mondegar licence suspended
    ("a38c30e1-da21-4409-948a-56cabdffc12e", "e97bc544-a2ee-4b37-97e6-69c9cfb73260"): False,  # headline:0.13 · Action taken after cracker factory blast || Telangana police constable suspended for
    ("3d86fd33-9333-44de-b131-d314c5d09b27", "0c2e38d1-5f60-4944-8b75-985a4616946b"): False,  # headline:0.14 · Kushalanagar Cooperative Society reports || Maharashtra Cabinet approves 750 crore s
    ("3d86fd33-9333-44de-b131-d314c5d09b27", "05d27648-4c5d-4889-9917-da9be02b7659"): False,  # headline:0.12 · Kushalanagar Cooperative Society reports || Fake alert: MEA denies reports of world 
    ("602c1f4d-ed05-4162-a5ec-dc382b3872fc", "4d75946d-1b59-4f86-bbce-c02ba974b4ce"): False,  # headline:0.31 · Stone pelting during Ganesh festival pro || 2 Dead In 2 Days During Clashes Over Gan
    ("602c1f4d-ed05-4162-a5ec-dc382b3872fc", "88af9c22-da31-4e0c-8348-7ef7f37d3e5b"): False,  # headline:0.20 · Stone pelting during Ganesh festival pro || Six students drown during Ganesh immersi
    ("cc22c8b3-216b-4b61-85b3-b140a9a55cfb", "e9bab9dc-98aa-4a96-a2eb-520cbfcb6c52"): True,  # headline:0.60 · Chennai to get new legislative complex,  || Motor Sports City to be established in T
    ("cc22c8b3-216b-4b61-85b3-b140a9a55cfb", "f6cd8a67-fc84-4468-81a4-88ffbf6fd82e"): True,  # headline:0.27 · Chennai to get new legislative complex,  || ₹1,200-Cr Secretariat, Olympic City, For
    ("45b34adf-4cd0-4aa7-bd7b-d22697ea835b", "4d905763-2353-4f00-8e65-e5b2679f6d6a"): False,  # headline:0.47 · Rahul Gandhi demands withdrawal of UPI t || HT Evening Brief Sept 16: Rahul Gandhi d
    ("17cd5689-f385-486f-9dc8-e03a523a9481", "5451c0a6-d3bd-4764-8b98-5aaea7085315"): False,  # headline:0.13 · Ramanahalli villagers protest against go || Man posing as Naxal to frighten villager
    ("17cd5689-f385-486f-9dc8-e03a523a9481", "78cd659e-4440-49d5-af55-8cb314aef107"): False,  # headline:0.11 · Ramanahalli villagers protest against go || Wild elephants cause scare in Belagavi d
    ("abb9f38e-22bf-4661-aa12-587bf30f8324", "01ea42b8-7bc9-49aa-933a-61aa00aaec75"): False,  # headline:0.16 · Protest in Hosapete demanding payment of || CM announces action plan to resolve pend
    ("abb9f38e-22bf-4661-aa12-587bf30f8324", "b941bd06-8190-4867-8e59-936cc56978fa"): False,  # headline:0.14 · Protest in Hosapete demanding payment of || Jharkhand Congress takes out protest mar
    ("5a7c52f0-29b1-42eb-b52a-62ade4157449", "c57ec1a3-fbdc-4cf2-8e19-ba6c65186f31"): False,  # headline:0.13 · When Kumar Saptarshi Challenged the Shan || Nitish Kumar Reddy withdrawn from Asian 
    ("5a7c52f0-29b1-42eb-b52a-62ade4157449", "ea8518a5-125b-4eda-b4a7-63bdb72a5ba7"): False,  # headline:0.10 · When Kumar Saptarshi Challenged the Shan || Who is Ashish Joshi and what is the cont
    ("404cf56d-a5b2-4a31-979d-7c190dd9b348", "77100cad-7466-4aaa-8f4a-9c588c44dc6c"): False,  # headline:0.13 · Naman Dhir and Aqib Nabi selected for In || Auqib Nabi to play three County Champion
    ("b8e95142-c5a2-443d-bdd2-72f624baa34e", "58105978-1f60-4181-8f6a-3b17d78dc37a"): False,  # headline:0.50 · India Responds to US 100% Tariff Threat  || No basis in international law: China rej
    ("b8e95142-c5a2-443d-bdd2-72f624baa34e", "e705ddf5-936a-496e-a6a3-c1f36bcb6298"): False,  # headline:0.14 · India Responds to US 100% Tariff Threat  || US Indictment Exposes Russian Global Ass
    ("e78081f0-00cc-4844-ac73-31d0d4f43fae", "4dfcf699-851d-4d35-bfc3-39021a8d4ace"): False,  # headline:0.37 · Prime Minister Narendra Modi Celebrates  || PM Modi Birthday: From RSS worker to thi
    ("e78081f0-00cc-4844-ac73-31d0d4f43fae", "a4c52f3b-87e9-406f-bcf0-360b45023987"): True,  # headline:0.25 · Prime Minister Narendra Modi Celebrates  || PM Modi birthday: Wishes pour in from ac
    ("c68e2c9d-b1d7-43ae-a2be-2dd587ba65a6", "1da191b5-bffb-4c02-97a4-82b8658915dd"): False,  # headline:0.17 · Solo sculpture exhibition of Ahmed Kanas || MSME regional conference, exhibition to 
    ("c68e2c9d-b1d7-43ae-a2be-2dd587ba65a6", "9b63767d-0d8d-4c16-b62a-00afc029e563"): False,  # headline:0.00 · Solo sculpture exhibition of Ahmed Kanas || 59-year-old man injured in wild boar att
    ("19a474b3-42e5-4367-8573-eb192cae3f37", "5b97e08e-6d92-4034-979e-b0e41246b8cc"): False,  # headline:0.13 · Forest department continues operation to || Forest officer, associate caught in ACB 
    ("d1529133-785f-4958-94f5-d4dc739002ec", "ac29d4be-84e8-42fe-be1f-6077bec882af"): False,  # headline:0.14 · What does Hamza bin Laden's presence in  || Why does Venus have no moon? New theory 
    ("d1529133-785f-4958-94f5-d4dc739002ec", "ea8518a5-125b-4eda-b4a7-63bdb72a5ba7"): False,  # headline:0.10 · What does Hamza bin Laden's presence in  || Who is Ashish Joshi and what is the cont
    ("2df8151b-a8ba-4452-bc1c-4ba89eb516c9", "dd2c4cd7-7b2e-4252-a606-42ae9a2807de"): False,  # headline:0.39 · New UPI Fee Structure: Who Pays and What || UPI still free, but there's a catch: Who
    ("2df8151b-a8ba-4452-bc1c-4ba89eb516c9", "1333a06c-d2c1-4176-a2a4-28b3a050e4e0"): False,  # headline:0.31 · New UPI Fee Structure: Who Pays and What || End of day consumer pays: Ashneer Grover
    ("c0771d21-c766-4c97-aa2b-c55e3349625a", "54513ed3-827d-48ce-b415-9af75c2f5700"): False,  # headline:0.43 · Son and mother arrested for murdering fa || Father, daughter hacked to death over pr
    ("c0771d21-c766-4c97-aa2b-c55e3349625a", "f2dde99f-b82f-4dad-9040-38b5bb76b186"): False,  # headline:0.26 · Son and mother arrested for murdering fa || Man Arrested for Killing Wife Over Marit
    ("3785a47c-546c-49a7-b9c7-d485a39d124a", "c3f5fab8-65a3-4996-a166-ba4c50d6b1a0"): False,  # headline:0.20 · KPSC scam: IAS officer Gyanendra Kumar G || Civil Police Officer in Kozhikode suspen
    ("3785a47c-546c-49a7-b9c7-d485a39d124a", "c57ec1a3-fbdc-4cf2-8e19-ba6c65186f31"): False,  # headline:0.14 · KPSC scam: IAS officer Gyanendra Kumar G || Nitish Kumar Reddy withdrawn from Asian 
    ("749253d8-453c-4580-b27e-a3f69b0cf906", "54b21d4d-d8f8-4011-a3cd-4c1f2a16c171"): True,  # headline:0.47 · SEMICON India 2026 begins, PM Modi speak || SEMICON India 2026: PM Modi hails India'
    ("58fec24e-e112-4c6b-af4f-d62c3ee0dc37", "b8daea52-bbf9-45e0-9a9f-080f316018b1"): True,  # headline:0.39 · Saurdi Arabia F-15 fighter jet shot down || Houthis claim to have shot down Saudi F-
    ("58fec24e-e112-4c6b-af4f-d62c3ee0dc37", "0548fe49-ffa4-4696-ad18-e5e4ca0d07ac"): False,  # headline:0.12 · Saurdi Arabia F-15 fighter jet shot down || Could China steal F-35 tech through Saud
    ("119e0aa2-37a7-4c7e-a859-354639b03dc9", "e712db7e-8233-4602-8c73-6aeda4fa0c26"): True,  # headline:0.74 · US House passes bill on Russia sanctions || US Congress Passes Russia Sanctions Bill
    ("119e0aa2-37a7-4c7e-a859-354639b03dc9", "98c2af79-5116-487f-9245-e23bf2d2a1d5"): True,  # headline:0.68 · US House passes bill on Russia sanctions || 100% tariffs on India? Russia sanctions 
    ("119e0aa2-37a7-4c7e-a859-354639b03dc9", "25da8dbd-199a-4ea0-8c91-b79aec9f84fd"): False,  # headline:0.45 · US House passes bill on Russia sanctions || Russia sanctions bill advances in US Hou
    ("119e0aa2-37a7-4c7e-a859-354639b03dc9", "f22635f7-a1dc-49ed-956a-86fdd6ff156f"): False,  # headline:0.34 · US House passes bill on Russia sanctions || MEA monitoring developments of Russia sa
    ("ac4b49e3-6057-4302-937c-462eeca654d8", "092d64cf-d00b-4419-af1e-13612eee0454"): False,  # headline:0.20 · Case filed against 6 DJ owners and opera || First legal challenge against UPI MDR fi
    ("ac4b49e3-6057-4302-937c-462eeca654d8", "4cd9b19c-4ec5-4c01-b73f-ccad4c8ece32"): False,  # headline:0.18 · Case filed against 6 DJ owners and opera || Over 15,000 mobile phones recovered; 583
    ("dcfcb6eb-8ce8-4fdb-9138-34e51c8ba530", "1d7353bd-baa2-4b1e-a240-61685f0d01fe"): True,  # headline:0.66 · PVR Cinemas and Forum Mall fined for imp || PVR INOX, Forum Mall staff fined ₹1.25 l
    ("dcfcb6eb-8ce8-4fdb-9138-34e51c8ba530", "76db2a51-45ba-4dd5-8157-e18823c22cfa"): False,  # headline:0.13 · PVR Cinemas and Forum Mall fined for imp || Pakistan players fined for slow over rat
    ("f7138102-f2a7-40e3-b686-b8f30900232a", "5fdaafa3-6f75-49eb-b4cd-25c4a4bc199c"): False,  # headline:0.23 · Karnataka cabinet prepares for coastal m || Rain likely in coastal Andhra, Rayalasee
    ("4ee70373-cae2-4df8-9ebe-dc55569ccf34", "8601010e-3023-481c-a8aa-3d8594e3d920"): False,  # headline:0.09 · BCCI announces schedule for 2027 Women's || BCCI trying to find ways to avoid freque
    ("abd4c84c-dcc5-40fd-af4d-44c4a27e771a", "9b305d91-294f-4a67-ba63-c2a8e30c35a8"): False,  # headline:0.18 · Indian Rupee rises 47 paise against US d || Belagavi: Fire accident toll rises to si
    ("abd4c84c-dcc5-40fd-af4d-44c4a27e771a", "f47582e0-bd8c-449c-b6df-c5fab3609d93"): False,  # headline:0.16 · Indian Rupee rises 47 paise against US d || Karnataka declares 23 more taluks drough
    ("ad58dd48-437f-43c0-9b94-9b5f109ae6a6", "1226aeda-59f1-49ee-8453-8baf9f3d5449"): False,  # headline:0.25 · India squad announced for West Indies se || Naman Dhir, Auqib Nabi get maiden ODI ca
    ("ad58dd48-437f-43c0-9b94-9b5f109ae6a6", "70d8758d-8783-4956-a64b-40826fa4038f"): False,  # headline:0.15 · India squad announced for West Indies se || Bumrah back in India squad for Afghanist
    ("13e310bd-b72a-435c-a95a-924a86c5ce08", "d11d39cf-379d-4e79-9a71-49df5513acaa"): False,  # headline:0.22 · Gold and silver prices crash on MCX || How US Fed Rate Hike Will Impact Gold Pr
    ("13e310bd-b72a-435c-a95a-924a86c5ce08", "d53a0352-d2a2-4666-a2cb-822222ef67d0"): False,  # headline:0.16 · Gold and silver prices crash on MCX || Global oil prices drop 1.2% as Saudi see
    ("98b4b67d-ed73-48b8-9f9d-557af6293eb1", "b8daea52-bbf9-45e0-9a9f-080f316018b1"): True,  # headline:0.43 · Houthi claim downing of Saudi F-15 fight || Houthis claim to have shot down Saudi F-
    ("98b4b67d-ed73-48b8-9f9d-557af6293eb1", "4da7c0e6-205c-4c4d-82d2-3147c79d9038"): False,  # headline:0.11 · Houthi claim downing of Saudi F-15 fight || Youth leader, 13 supporters join TDP ahe
    ("489a0f01-bf0f-49c7-8d1f-50f48b530fb3", "0211fd77-2439-4607-8174-e5c30f82f7ba"): True,  # headline:0.42 · US President Donald Trump expresses hope || Iran war LIVE Updates: Trump says war ne
    ("489a0f01-bf0f-49c7-8d1f-50f48b530fb3", "ca74722f-c61f-45e4-97e0-451ba6a9a437"): False,  # headline:0.27 · US President Donald Trump expresses hope || Trump to meet Gulf leaders at UN over Ir
    ("1a185a0e-da66-4d1f-9f0f-7d8840387f5a", "ad912351-1408-4e47-bdd4-fc328aab1df5"): True,  # headline:0.72 · Anant Nag selected for Dadasaheb Phalke  || Actor Anant Nag to be honoured with Dada
    ("1a185a0e-da66-4d1f-9f0f-7d8840387f5a", "92cd5ab6-fd7b-46c1-829e-1e323c1a8574"): False,  # headline:0.12 · Anant Nag selected for Dadasaheb Phalke  || Meet Sethuraman Panchanathan, first Indi
    ("e203dda0-8193-431c-9b35-e3729196c424", "b4c3ccf5-8386-479f-ae8f-abbb24a0bd55"): True,  # headline:0.36 · No rollback of MDR charges on UPI paymen || No question of rollback: Govt defends UP
    ("e203dda0-8193-431c-9b35-e3729196c424", "40f9fc61-fd73-4b7c-9037-609f5b6ea654"): False,  # headline:0.23 · No rollback of MDR charges on UPI paymen || Parliament Standing Committee didn’t dis
    ("b897fae2-e7e3-48c4-b0d2-de8315e4eb26", "a4c52f3b-87e9-406f-bcf0-360b45023987"): True,  # headline:0.32 · PM Modi's 76th Birthday Celebrated Acros || PM Modi birthday: Wishes pour in from ac
    ("0cc3dbb9-e28e-43c5-a532-47b26fac134f", "dfa67a07-8bb3-44d9-ab0d-150113d540d7"): False,  # headline:0.22 · India Launches Six Month Bridge Course f || KUD to felicitate 13 internationally rec
    ("6ff4df2d-8366-4a18-9d52-2db3166ec88f", "14be06d4-60a9-4114-98f2-0df4f6b10f0f"): False,  # headline:0.10 · Kalya-Oojgal road project initiated unde || Kerala HC raps authorities over road saf
    ("6ff4df2d-8366-4a18-9d52-2db3166ec88f", "63b5999f-b9e6-4c7d-a027-3ab39dc10034"): False,  # headline:0.09 · Kalya-Oojgal road project initiated unde || Launch of expansion of Perunthalaivar Ka
    ("01d0e492-63b0-480a-b706-1e4e03f581a5", "c3569f35-c215-46f8-8063-c02207d53ad6"): False,  # headline:0.16 · Understand the importance of the right t || Folk song workshop held for Pang school 
    ("01d0e492-63b0-480a-b706-1e4e03f581a5", "705d1532-a25d-44d7-af8f-b020f3e4f75d"): False,  # headline:0.14 · Understand the importance of the right t || CPI alleges vote deletions in A.P. SIR
    ("635c86fa-0a01-4171-84d8-10f952ab2b85", "f8b57454-a444-4988-9094-35ee76493a53"): True,  # headline:0.66 · Gold hallmarking charges increased by 67 || Gold hallmarking costlier: Fee up 67% ah
    ("635c86fa-0a01-4171-84d8-10f952ab2b85", "1b8312d6-7718-416b-8dfe-a642996295c2"): False,  # headline:0.12 · Gold hallmarking charges increased by 67 || Influenza, leptospirosis emerge as major
    ("8845423e-57c4-4705-aa6f-2595931ac286", "a08f8e99-b355-41d3-9833-952b6b5a147a"): True,  # headline:0.49 · KLE Hospital, JGMM Medical College inaug || Union Home Minister Amit Shah to inaugur
    ("8845423e-57c4-4705-aa6f-2595931ac286", "b7902cb3-a016-4ffa-aca9-64765706a631"): False,  # headline:0.29 · KLE Hospital, JGMM Medical College inaug || Ernakulam Government Medical College Hos
    ("e8d55848-4a7b-4f70-aaf3-8b50fd0eed3a", "609abbd3-e9e5-4afb-8da7-27aba374ed6c"): False,  # headline:0.18 · IIT Kanpur expects to admit first patien || Puravankara expects ₹2,600 cr revenue fr
    ("e8d55848-4a7b-4f70-aaf3-8b50fd0eed3a", "ede04467-3dca-45f2-9485-083c1f25f9f8"): False,  # headline:0.18 · IIT Kanpur expects to admit first patien || ZEISS opens its first Innovation Hub out
    ("d65be65a-c176-47ed-8263-decfd3c11c28", "54513ed3-827d-48ce-b415-9af75c2f5700"): True,  # headline:0.50 · Father, daughter brutally murdered at Gr || Father, daughter hacked to death over pr
    ("d65be65a-c176-47ed-8263-decfd3c11c28", "f2dde99f-b82f-4dad-9040-38b5bb76b186"): False,  # headline:0.15 · Father, daughter brutally murdered at Gr || Man Arrested for Killing Wife Over Marit
    ("5c560c3c-b182-40cf-9551-4b10bb52f30a", "888711e4-7041-4f70-a6ad-3283e8b2ffcb"): False,  # headline:0.15 · Farmer destroys onion crop due to lack o || Farmer tests positive for COVID-19 in Ku
    ("5c560c3c-b182-40cf-9551-4b10bb52f30a", "f21dd933-49a3-493c-ab6e-e792da378ac8"): False,  # headline:0.12 · Farmer destroys onion crop due to lack o || Burglars decamp with 20 sovereigns of go
    ("a2947ad2-8391-40ff-8911-33879c5c2972", "816278ac-1dfb-4d25-8b92-af0ada238ffe"): True,  # headline:0.52 · PM Modi to inaugurate Semicon India 2026 || PM to inaugurate three-day Semicon India
    ("3c93e12e-bd8f-4f03-aaba-a3ecc57f2fcb", "087c7f3f-19c6-47df-b098-66226df54db7"): True,  # headline:0.45 · United States raises bank interest rates || US Fed hikes interest rates for first ti
    ("3c93e12e-bd8f-4f03-aaba-a3ecc57f2fcb", "cdd5e4a7-d0ea-40e4-bde5-15458bff8ec2"): False,  # headline:0.19 · United States raises bank interest rates || Andhra raises upper age limit for govt j
    ("93f845fa-12d0-49ae-b94e-ba3d0df0fd34", "dabb58a8-fc48-444c-8c4e-8ee52995649d"): True,  # headline:0.77 · Supreme Court expresses concern over dea || SC expresses shock over deaths in relief
    ("93f845fa-12d0-49ae-b94e-ba3d0df0fd34", "3b9962f6-dcb9-4263-a781-b952b89e72c1"): False,  # headline:0.20 · Supreme Court expresses concern over dea || Blood camps held across Belagavi distric
    ("a342e2f8-959f-4e94-9378-c3d769316c1e", "e712db7e-8233-4602-8c73-6aeda4fa0c26"): True,  # headline:0.53 · US Senate passes Russia sanctions bill,  || US Congress Passes Russia Sanctions Bill
    ("a342e2f8-959f-4e94-9378-c3d769316c1e", "98c2af79-5116-487f-9245-e23bf2d2a1d5"): True,  # headline:0.42 · US Senate passes Russia sanctions bill,  || 100% tariffs on India? Russia sanctions 
    ("a3975031-14d3-4d6f-aeeb-3e4fcedea181", "c2bf5468-41ac-4e4c-8684-8d3baf2d15e5"): True,  # headline:0.49 · Demand for establishing an international || North Karnataka associations seek second
    ("a3975031-14d3-4d6f-aeeb-3e4fcedea181", "58105978-1f60-4181-8f6a-3b17d78dc37a"): False,  # headline:0.14 · Demand for establishing an international || No basis in international law: China rej
    ("11a9f716-c71c-4272-bf4f-caedf762cf3d", "356228a6-c497-436c-87c7-3a42fcc0b08c"): False,  # headline:0.12 · Ganesha immersion procession in Maddur,  || Dasara: Kambala set for October 18 and 1
    ("26c685f1-c1f7-4e8d-98e0-c50e5acf114b", "e712db7e-8233-4602-8c73-6aeda4fa0c26"): False,  # headline:0.17 · America deployed weapons in space, Russi || US Congress Passes Russia Sanctions Bill
    ("b2144dd1-91e0-44e1-ab08-83904b6e6f99", "b941bd06-8190-4867-8e59-936cc56978fa"): False,  # headline:0.19 · Jharkhand students protest to stop schoo || Jharkhand Congress takes out protest mar
    ("b2144dd1-91e0-44e1-ab08-83904b6e6f99", "c3569f35-c215-46f8-8063-c02207d53ad6"): False,  # headline:0.19 · Jharkhand students protest to stop schoo || Folk song workshop held for Pang school 
    ("4e6a1a64-ad5c-48d5-9ae7-26fbafc93859", "a36df9bb-ee08-48cb-9e02-8c3eb0532cba"): False,  # headline:0.12 · Annual General Meeting of Heggadagere Mi || Tamil Nadu can unlock ₹1.2 lakh crore in
    ("4e6a1a64-ad5c-48d5-9ae7-26fbafc93859", "aa7a478a-e6f3-489f-aa59-a9b9c58ff588"): False,  # headline:0.10 · Annual General Meeting of Heggadagere Mi || CPI(M) general secretary M.A. Baby slams
    ("16d795c1-b1aa-4ed1-9b49-b10e4b381204", "b140a063-d858-43f7-8705-09ba4c9c20f4"): False,  # headline:0.42 · Four-year-old girl dies in Gauribidanur  || A 23-year-old Bengaluru girl dies suspic
    ("16d795c1-b1aa-4ed1-9b49-b10e4b381204", "a0ce70eb-f765-4450-b77e-97ebc9696c5f"): False,  # headline:0.36 · Four-year-old girl dies in Gauribidanur  || Hair caught in generator, 11-year-old gi
    ("c871769a-6b32-4543-9aa1-c95e15644874", "8dc81e7c-8529-4c1a-ac64-5e292554d284"): False,  # headline:0.24 · ED conducts raids on Gopal Kanda's resid || ED raids residence of wanted ganja suppl
    ("fe0c23e4-3a87-49c0-9f91-ef58744fcfef", "4cd9b19c-4ec5-4c01-b73f-ccad4c8ece32"): False,  # headline:0.39 · Mobile phones banned in Tamil Nadu templ || Over 15,000 mobile phones recovered; 583
    ("fe0c23e4-3a87-49c0-9f91-ef58744fcfef", "b832b120-0e24-42e9-a179-c6f372fe6daf"): False,  # headline:0.28 · Mobile phones banned in Tamil Nadu templ || Madras High Court sets aside order preve
    ("30024f5f-e2e1-457f-bcb4-ab9204f7c2e0", "716ee109-77f0-43ce-a996-a9e1068d63e4"): False,  # headline:0.60 · Vivek Tiwari murder case verdict expecte || Apple executive Vivek Tiwari's killing b
    ("30024f5f-e2e1-457f-bcb4-ab9204f7c2e0", "60c37091-d52e-4b60-84dc-2499d23f8d37"): False,  # headline:0.19 · Vivek Tiwari murder case verdict expecte || Abhimanyu murder case: Court reserves or
    ("983b3f62-d93f-496e-985b-88acfe3f575d", "93bfcd9d-64e3-463f-b38c-c4ea94fbc7ef"): False,  # headline:0.10 · Jammu: Non-bailable warrant against Lash || Drone industry flags over 50,000 illegal
    ("a6abfa0e-a6e6-4a86-a21e-b466b78ad1e0", "c08e0ea1-23b1-4062-a4ae-4802a9831e36"): False,  # headline:0.19 · SFI leaders attempting to reach site of  || YSRCP protests against house arrest of y
    ("a6abfa0e-a6e6-4a86-a21e-b466b78ad1e0", "676c8bb5-95ff-43cf-a29f-3413e33efab3"): False,  # headline:0.13 · SFI leaders attempting to reach site of  || Godavari waters reach Anakapalli in AP, 
    ("6a3bd772-d3e6-4ffd-84f9-e539d4543c9c", "51a895ab-cda2-4235-a9db-309cdde6af16"): False,  # headline:0.24 · Bangladeshi people waved the flag in Sau || BJP chief urges people to hoist national
    ("6a3bd772-d3e6-4ffd-84f9-e539d4543c9c", "0548fe49-ffa4-4696-ad18-e5e4ca0d07ac"): False,  # headline:0.21 · Bangladeshi people waved the flag in Sau || Could China steal F-35 tech through Saud
    ("29a32073-4d38-4433-a770-84bb479c2a68", "d09b1a09-996d-4443-aff9-98993e4f0af2"): False,  # headline:0.11 · Self-declaration mandatory to receive un || Bengaluru likely to receive light rainfa
    ("29a32073-4d38-4433-a770-84bb479c2a68", "3779692c-22aa-46b5-9fe9-28bff44292c8"): False,  # headline:0.09 · Self-declaration mandatory to receive un || India proposes mandatory CCTVs at medica
    ("271894c2-2b21-4dea-b2ab-4ecf63015047", "54513ed3-827d-48ce-b415-9af75c2f5700"): False,  # headline:0.28 · Dispute over 300 crore property belongin || Father, daughter hacked to death over pr
    ("271894c2-2b21-4dea-b2ab-4ecf63015047", "a3d4b687-d386-483a-892c-8bce635a57d2"): False,  # headline:0.20 · Dispute over 300 crore property belongin || Fortis moves Supreme Court against Delhi
}

SILVER_SAME_LANGUAGE: dict[tuple[str, str], bool] = {
    ("71193f64-9820-4a25-a0cc-7174f2eea5c7", "524683e3-bf64-4bd4-a222-d4858e1f0488"): True,  # 0.459 · Rahul Gandhi demands resignation of Gyanesh  || Rahul Gandhi demands resignation of Chief El
    ("88b0e2ba-00df-4ef2-b453-a913d03f4f62", "25fdf7cf-cd53-4def-8921-48254de6b2e2"): False,  # 0.429 · Cyclone Triggers Heavy Rains in Andhra Prade || Heavy Rains Flood Roads and Disrupt Flights 
    ("133535c8-b197-43d5-8580-38cd8ac2098e", "9ee4608b-7db9-48af-9701-1689b776be58"): True,  # 0.461 · Rajya Sabha poll for seat vacated by ex-Trin || Rajya Sabha elections for 11 seats to be hel
    ("9e34a237-1168-4018-b412-9cd5c7f8f97a", "4ed6cd3f-f164-4905-a082-946ad51bb22e"): True,  # 0.48 · US tightens visa rules to curb birth tourism || US restricts visas to curb birth tourism pra
    ("661a70fb-32e9-4592-9bf9-3c76901c8533", "381cda32-3200-4cde-8dd1-076f8d859d0e"): False,  # 0.469 · Morarji Desai Residential School Volleyball  || Morarji School Students Selected for Distric
    ("06e7805b-2de6-4971-9814-67e65014bea0", "c526b2e9-9a02-4182-b5c5-fb8cb0bc4630"): True,  # 0.446 · Nursing student found dead in Bhadradri Koth || Nursing student found dead with injury marks
    ("68820fca-4299-4de2-b25c-8c7d2d23e803", "5e04342e-d19d-4a1a-bd39-5f85fec5e07c"): False,  # 0.427 · Police trace car involved in attempted abduc || Nellore Police Trace Suspects In Attempted M
    ("82d88e37-a0c5-4629-a1d4-ce9acd8c31f7", "3c487cf6-f5b3-442b-8202-2b001c442ce0"): False,  # 0.423 · Man shot dead in Manipur's Tamenglong distri || 17-year-old Naga youth shot dead in Manipur,
    ("c1e068fb-bbc9-441f-b961-ae36b06472c0", "e0e10d2d-4b72-4d22-b8f5-433a2b2699bd"): False,  # 0.489 · Afghan Cyclist Wins Silver Medal at Asian Ga || Mirabai Chanu wins silver medal at Asian Gam
    ("fc642133-95ad-45db-a184-0d8f5f64a8a1", "12854d14-73d9-447e-abff-71a5eede41cd"): False,  # 0.493 · Air quality in Karnataka cities remains mode || Air quality improves in major cities of Karn
    ("11a22f98-bc49-477e-9d42-7e956e1a2266", "49c08728-51e0-4a95-9097-44346a4527d8"): False,  # 0.419 · Indian men's badminton team wins bronze at A || India win bronze in women’s skeet team event
    ("52bee305-a46a-4c9b-a616-abb185cb70ed", "cef7b7e8-88ab-4358-9e37-502b3165bc19"): False,  # 0.44 · Akhilesh Yadav Demands Resignation of Chief  || Raj Thackeray demands resignation of CEC Gya
    ("7fb02dc8-0c5a-453a-aed0-9d2d1308db41", "7c4b770c-f495-40a3-8222-e8f5cdaea88d"): False,  # 0.391 · CJP demands resignation of Chief Election Co || Raijor Dal demands resignation of Chief Elec
    ("82657fbe-1076-4325-a1ea-6b6a89675daa", "35485f42-c0fe-4834-b23a-29c4901a7397"): False,  # 0.431 · WHCA condemns Trump's move to bar CNN, MS NO || Trump bans news outlets CNN, MS NOW, Politic
    ("d85edb58-4cb9-45c2-ba8d-cef6d8ce5bc5", "8b3a2440-4dab-47c7-bd93-49c5c42c1443"): False,  # 0.398 · 72,547 cases settled in Yadgir Lok Adalat || National Lok Adalat resolves thousands of ca
    ("104e7290-15f6-4ded-8de8-7ebc3e5f9c86", "3742358a-8c87-413e-ab81-8e9919b96c1b"): False,  # 0.455 · Donald Trump announces renaming of artificia || Trump and Xi prioritize trade and artificial
    ("6391a977-b7ce-4376-9649-904a4a33ac9a", "0806e710-1176-4ce1-9026-a1deead12786"): False,  # 0.498 · Afghan woman cyclist wins silver medal at As || Roshibina Devi wins silver medal at 20th Asi
    ("cecc7b85-97e5-4371-bf61-b0f8cdd72cfd", "6a70271d-39e4-4e73-ae96-e6a9d6f45ee6"): False,  # 0.448 · Hukkeri Rural Electric Cooperative Society h || D. Salundi Milk Producers Cooperative Societ
    ("61a93c02-ce0c-44bc-9366-c448cb4e9351", "ef9c1c1e-7fbb-4c76-ab9f-14d409a9ced4"): True,  # 0.475 · Akal Takht excommunicates SGPC member Amarji || Akal Takht Expels Akali Dal Leader Amarjit S
    ("862e8e08-a891-491e-96fb-ff3a2497fb72", "d6e3bc3c-2e21-4f39-965b-1926d7820640"): False,  # 0.399 · Deep Depression To Hit Odisha-Andhra Coasts || Deep depression weakens in Odisha after caus
    ("5f312f46-a02e-4756-bcf3-5d591c72864d", "3c0d284a-52f3-4d16-82f8-7f0d11996366"): False,  # 0.398 · MP B.Y. Raghavendra says Ayurveda is helpful || Ayurveda system is helpful for healthy livin
    ("797dd32a-f28d-400c-a543-7ac69fcf12b9", "c78a0aca-f994-4baf-a1be-fbfd2140acd5"): False,  # 0.414 · Man bludgeoned to death by brother over land || Woman, Mother Bludgeoned to Death in Etah
    ("d7c06453-fd29-4f41-8ee9-4ef9c179ee0c", "9507e376-54ab-4539-8089-f6e0d354b37a"): False,  # 0.396 · Teachers' Day celebration program to be held || National Ayurveda Day celebration on Septemb
    ("5dfcfa29-4287-49bf-9b51-94e6d173308f", "1477bef0-753b-4152-9fca-a5ce1c13f015"): False,  # 0.438 · Indian Women Cricket Team Reaches Final at A || India wins first gold medal at Asian Games i
    ("11183aad-0dd6-4a40-aee7-b7e8004a089c", "c44c21dd-ddb1-4149-839d-b00273561444"): False,  # 0.456 · Rahul Gandhi demands resignation of Chief El || Opposition plans impeachment motion against 
    ("3201ba13-f79f-40c6-bb71-b51da568602d", "62195b45-fc38-404a-aaed-a7ff8627f61b"): False,  # 0.42 · 206 cases settled, 2.33 crore rupees recover || 48,678 cases settled, 27.28 crore rupees com
    ("a7256031-9f0e-449f-864d-90ce3980e79c", "ed5a6001-c2b1-4f57-977c-7e247e351e8d"): False,  # 0.396 · Surendra Koli’s brother seeks high-level pro || Surendra Koli dies after twenty years of imp
    ("208a73e4-f1c8-4ab7-a596-c0561798d4c1", "899a906a-eb8b-4f00-91a0-134facd690a6"): False,  # 0.433 · Sports and cultural events for senior citize || State-level sports meet for senior citizens 
    ("ab2d6dbc-89d6-4a37-ac2d-a24ea1ecbed2", "2aaee71a-847a-4fee-b92c-5cdef9d4259d"): False,  # 0.396 · Over 230 motorists caught for drunk driving  || Police officer suspended over alleged drunk 
    ("24ed087b-5be8-4e7b-853e-1668035d78a0", "2028d394-bd22-47e5-a5e4-eaf54a8bf3f6"): False,  # 0.446 · Divya Jyothi Cooperative Society earns net p || Sahara Minority Cooperative Society earns 4.
    ("72d1cc25-4e1a-4618-8653-28eab91396e9", "fac0b435-1106-4646-a4df-94e872be3c92"): True,  # 0.495 · Samrat Choudhary responds to BJP defeat in B || Samrat Chaudhary says public is the master i
    ("888c0245-16d8-4b92-874a-a96d0a4d43a2", "212b3180-783c-4b04-a70b-1cb241092f75"): False,  # 0.407 · Heavy Rain Puts Indrakeeladri On High Alert || Odisha puts 11 districts on high alert as lo
    ("aa58825b-b688-4975-8d1a-34beb27cee85", "7d5a0201-92a1-4597-9456-d5c9e0a17b83"): False,  # 0.59 · Blood Donation Camp Held During Kamalapur Fe || Blood donation camp held in Honnavar
    ("09fe4c12-a5c2-4bfd-ba92-2bbb80e9640b", "0ec279fd-d927-41a0-b640-5852e8812a7d"): False,  # 0.586 · Ganesh festival concludes with grand immersi || Ganesh Festival Concludes With Immersion Pro
    ("92543cca-b86a-47bd-93f9-5425cfaa5d32", "44bd164b-fd42-45e3-a67d-86760e302b94"): False,  # 0.54 · Rahul Gandhi demands resignation of Election || Congress leader Manickam Tagore demands resi
    ("61003a71-d8ff-4282-9531-31bd30d6ae25", "3577053a-9e78-477d-82e1-47b2ff6b7025"): False,  # 0.513 · Hampadevanahalli Cooperative Society Holds A || NGO Housing Society Holds 62nd Annual Genera
    ("598d37f5-05e8-423d-8b0b-c89f4e53289e", "3133e483-6a08-408b-b213-df028647c69a"): False,  # 0.578 · SUCI demands removal of Chief Election Commi || Who is Chief Election Commissioner Gyanesh K
    ("a01ebe9f-99dd-45a3-a110-90d0fb66f4fd", "f8bf8d84-2349-4c53-afc9-7291f77ac5e9"): False,  # 0.507 · IIT Bombay student death case investigation  || Student death at IIT Bombay leads to protest
    ("63fad587-cf66-461d-b48e-8f7b71ec1844", "25d9de34-2cad-4077-8245-94e4a5e8ca60"): False,  # 0.532 · Maruti Cooperative Credit Society earns 2.74 || Basavashree Cooperative Credit Society repor
    ("691fd5ec-edbf-4db5-abff-aad47595a223", "79941d7d-8805-4b61-be8f-6a95452da0b7"): False,  # 0.535 · El Nino active while Cyclone Arnab threatens || Cyclone Arnab: Low Pressure Intensifies Over
    ("dab86d57-5b94-496a-8bfe-1d0abd26d296", "2b87b9e6-78bd-40bf-bf94-9b9602d1f570"): False,  # 0.506 · Roshibina Devi wins silver medal at 2026 Asi || Asian Games: Roshibina Devi reaches semi-fin
    ("6aa98ed6-dd4d-4d4b-afa1-778d9b597908", "52f56a6b-982c-4308-9b5a-811fea8682be"): False,  # 0.513 · Iran increases military strength and issues  || Iran increases price for ceasefire and warns
    ("027e11c6-9f28-4f8f-bb60-1dd91381110d", "60b1f4b1-ef4d-4de3-b912-4e41de54430c"): True,  # 0.589 · Speeding BMW falls off bridge in Mumbai || BMW car falls from Mumbai coastal road bridg
    ("8ee78741-5607-4e1d-833e-91f58cebf9d8", "ffa5674c-18b4-4a66-be60-827b323d77c6"): False,  # 0.501 · IIT Bombay student suicide: Parents begin in || Father of deceased IIT Bombay student threat
    ("44e34f4a-0d9d-4fe0-969d-0cf6db3d88bb", "3bd66278-ef75-431f-84bb-4a79a4240d41"): False,  # 0.589 · Veteran actor Mushtaq Khan dies after battle || Veteran Bengali Actor Mithu Mukherjee Dies A
    ("f7720570-d82b-4c16-a13d-9ad9f826dbdf", "6b6e7ead-d240-40b2-969a-0467736a3bf4"): True,  # 0.563 · Engineering student’s suicide turns out to b || Professor arrested for staging engineering s
    ("6e94f489-a81b-4c86-a5a7-d1094f12163a", "c8881866-d75d-4d79-af45-94e3eac02571"): True,  # 0.565 · Police investigate viral video of woman bein || Minor girl harassed in Samastipur, police la
    ("e8ec1dc9-c66a-44fd-bb0b-898c8141b9fe", "55d209eb-a5e5-49dd-8e90-2408d4a35aed"): True,  # 0.52 · Churches in Dhamtari install signs restricti || Churches in Chhattisgarh restrict entry to C
    ("ee94207c-cb9a-4fee-b375-4986663a1ae9", "a3846c37-98e9-4580-8eb5-d336a1669705"): True,  # 0.6 · Rahul Gandhi Accuses BJP, RSS, and Election  || Rahul Gandhi levels treason charge against E
    ("235fa6cf-0e6f-4ca9-ac87-741180df6cf7", "ea9491cf-0f0d-439e-bad1-b575c2e87da9"): False,  # 0.536 · Channagireshwara Cooperative Society reports || Primary Agricultural Credit Cooperative Soci
    ("77abf1db-2345-40b9-8399-e7fef54c8960", "9490b170-ba88-41de-91c2-6ccbdb23479f"): False,  # 0.563 · Cockroach Janta Party demands resignation of || Congress demands resignation of Chief Electi
    ("7e1cc227-b91a-42fa-9f9a-fcee6ca88075", "7c4051ee-0b8d-4f66-aba9-c332b43586d6"): False,  # 0.52 · Muttanahalli Society earns 7.9 lakh profit || Tungapattina Cooperative Society earns 9 lak
    ("4938a62b-9fc4-4488-84ab-5ea744b496a1", "8b922737-5a03-4f18-8ed2-8991e68965ee"): False,  # 0.525 · Rahul Gandhi demands Chief Election Commissi || D.K. Shivakumar demands resignation of Chief
    ("375b0fd1-e92e-42ef-87a1-eecc9cdbef8b", "40979cc6-4f40-42b0-aa9a-5867cf8db881"): True,  # 0.585 · Karnataka Assembly Rejects Kasturirangan Rep || Karnataka assembly rejects draft notificatio
    ("ae71a315-b358-4a13-ba5b-027802e4d42d", "fb461c31-d61f-4c96-9d12-1028e5596cce"): False,  # 0.53 · Over 400,000 Ganesh Idols Immersed In Bengal || Over 81,000 Ganesh idols immersed across Cyb
    ("f5a60e26-f164-4fd1-8e77-65069d3353ed", "f6d865e3-efe8-4434-8429-bbb3e4414b81"): False,  # 0.571 · Officials seize narcotics worth 10 crore at  || Gold and marijuana worth 29 crore seized at 
    ("a0d5e9cc-f107-4972-b3f7-dae1198ed261", "68445bf6-6075-4205-8396-910665aa77e1"): False,  # 0.505 · Awareness march for voter registration held  || Voter Registration Awareness Rally Held in D
    ("e8a3948c-e73e-4a8c-b75f-483881b426a7", "9e1e1bc0-236d-4a84-9e49-db892791aa2c"): True,  # 0.52 · Calcutta High Court Criticizes Election Comm || Calcutta High Court questions Election Commi
    ("83b6d80b-98fd-4724-a9d0-1b63621695c6", "7c969633-d396-4f47-8115-c2528ef70822"): False,  # 0.501 · Manu Bhaker Named India Flagbearer for Asian || Asian Games Day 4: Manu Bhaker and others in
    ("7d1deca1-86d2-4b65-90a6-e0dec4d07e03", "1466ee34-9e0c-4fef-9429-1eb2b8012ccc"): False,  # 0.568 · Iran Proposes Reopening Strait of Hormuz, Ta || Iran promises to open Strait of Hormuz in se
    ("90d9c8be-ff1c-4d65-ba2e-8b688f4f710c", "9be13dc5-b1d9-475c-847d-dd46cd2424be"): True,  # 0.528 · Karnataka Chief Minister considers shutting  || D.K. Shivakumar considers shutting down Karn
    ("6ff63efe-2310-4047-90a2-13098f2457da", "164660f6-6661-4269-bf4c-d46cc82297fb"): True,  # 0.506 · Rahul Gandhi demands truth from Gyanesh Kuma || Rahul Gandhi demands resignation of Chief El
    ("70bc7b6a-8dbe-4302-9895-8664825024c8", "9d6d2a50-ff3b-4ef0-a89e-d9a816c9b7f6"): True,  # 0.515 · Nine die in sleeper bus fire on Yamuna Expre || Fire in moving sleeper bus kills nine passen
    ("80a0fc7f-8b3e-456a-b3a3-bdc5c1520def", "acfa0958-aa41-4c78-b700-9cc582511e27"): True,  # 0.543 · Karnataka assembly passes resolution opposin || Karnataka Assembly rejects Centre’s 7th draf
    ("2e861d10-66f6-468b-8150-b5cd42332b6f", "5fe9481b-1239-4c59-98d5-69c1da709d46"): False,  # 0.572 · Kalloli school students qualify for district || Yellapur students selected for district-leve
    ("52bee305-a46a-4c9b-a616-abb185cb70ed", "8128520b-78ab-4086-924a-e3171014283f"): False,  # 0.552 · Akhilesh Yadav Demands Resignation of Chief  || Rahul Gandhi demands resignation of Gyanesh 
    ("164660f6-6661-4269-bf4c-d46cc82297fb", "524683e3-bf64-4bd4-a222-d4858e1f0488"): True,  # 0.655 · Rahul Gandhi demands resignation of Chief El || Rahul Gandhi demands resignation of Chief El
    ("ef4b9cfd-48b7-40ea-b222-ba5445f41ed5", "01714ed1-219a-4448-bad3-60aadf9f86bf"): True,  # 0.609 · Nine passengers die after bus catches fire o || Fire on bus at Yamuna Expressway leaves nine
    ("222e1361-6bbd-46ff-81af-5075e69f6d9f", "26e6f023-aa9b-49a1-bf79-0599f94ac2a0"): True,  # 0.651 · Dubai Ruler’s brother dies at 76 || Dubai Ruler's Brother Sheikh Ahmed bin Rashi
    ("7bf27488-8cb4-46b3-aab5-834869c55417", "1ce02fe0-d394-4c57-954d-37b09e3c8469"): False,  # 0.629 · Farmer killed by lightning strike || Two women killed in lightning strike in Kala
    ("77abf1db-2345-40b9-8399-e7fef54c8960", "29ddf16a-29dc-4ac7-87c3-e409cf135419"): False,  # 0.638 · Cockroach Janta Party demands resignation of || Stalin demands resignation of Chief Election
    ("1ec0dd5b-1651-4fbd-abd3-1977ed6902ef", "46324868-322b-4a6a-ab3a-0a3998a20cf8"): True,  # 0.619 · Bangladesh foreign secretary Asad Alan Siam  || Asad Alam Siam named as new Bangladesh High 
    ("69b79403-c12e-44fe-bb7b-81e2cec8128d", "5132921e-f740-4cd0-8045-3f09c7e1786b"): True,  # 0.631 · INDIA alliance plans impeachment motion agai || Congress prepares impeachment motion against
    ("50981cc3-d3cb-4e78-9630-c25309ce8ff1", "d5f77ac1-be9d-4d62-8fd3-a025bd32aaea"): False,  # 0.611 · GIFT Nifty Indicates Negative Open || GIFT Nifty indicates positive opening for Ni
    ("c7cc5734-c61a-47b3-9591-cd75738f13d5", "da553c06-de8b-4d6c-9d4b-a2f931f45acd"): True,  # 0.666 · FSSAI proposes ban on the term paneer for no || FSSAI Proposes Ban on Paneer Label for Subst
    ("abef1ab8-7ac5-4f7f-a320-83457890430b", "a0c187c1-8637-4c0e-9cec-4be9473c8b22"): True,  # 0.603 · Trump winces as B-1 bombers roar during Xi J || B-1 Bombers Fly Over Xi Jinping During Arriv
    ("f6b85658-43e5-48cb-9803-781f0ffe642a", "f7d28224-8342-40a8-ae10-09fc04769578"): True,  # 0.647 · Banks to remain open this Sunday || Public Sector Banks to Remain Open Sunday Be
    ("c78a57da-a3fa-4f4b-a3fc-0654adca373f", "76fbcb93-5dd6-4ba5-ab97-f77ba819eca1"): True,  # 0.618 · BJP MLA demands probe into Rent a Garba Part || Rent Garba Partner Ads Spark Probe Demand Fr
    ("0e009928-4dd7-44b1-846e-f85e98b5212c", "1384ec15-75ea-4da6-bb3f-84eb46f74399"): False,  # 0.749 · Trump Signs Security Deal With Denmark and G || Trump Announces US-Denmark Security Deal Reg
    ("3885278c-0342-47e7-a2f0-cc22cb6b5048", "6c600837-6557-4166-83fd-51db7ecb0cec"): False,  # 0.673 · 6,733 pending cases in Mysuru settled throug || 27,531 cases settled in Lok Adalat in Dharwa
    ("5c0b6d84-5704-49bc-8e05-720cd5c8cd8c", "5ad8e222-9c65-4371-a90e-69e4936dded8"): False,  # 0.633 · Coronation Cooperative Society records 21.31 || Agricultural Credit Cooperative Society reco
    ("11114938-bf9d-4377-9fd8-4a3a6cdd8309", "939bffea-88c7-47f5-b23e-2476c57c103f"): True,  # 0.715 · United States approves 24 billion dollar F-3 || US Approves $24.3 Billion Military Deal With
    ("32656cd1-e472-4a35-b97c-6bf135f6b168", "c311c9a4-9e99-467b-8703-9601a226fb68"): True,  # 0.682 · Wood retires from international cricket afte || Mark Wood retires from international cricket
    ("cf817502-9083-4729-85d5-c41f8cbc575e", "59b980b7-54f7-4327-880b-72afb5ac7b35"): True,  # 0.711 · Five infants die in fire at RIMS hospital in || Fire at RIMS hospital in Adilabad kills thre
    ("a0762f28-9ecd-4c0b-ac73-5fdf9edb827e", "1a75cd6e-d645-4fe2-ae05-bce647e196f7"): False,  # 0.628 · Wild boar hunting: accused arrested || High Court quashes criminal case against fou
    ("42f4ed70-bd6f-4847-ab16-6f4ea768c286", "d1dd400e-b717-4671-af47-3a195c400e20"): True,  # 0.74 · Speeding Car Hits Five People in Greater Noi || Car hits several people in Greater Noida
    ("cccf49ea-cca2-4092-9ea0-cf1d4dce6671", "cb672933-bd55-44b2-82f5-ead651444c4c"): False,  # 0.627 · Ayurveda Health Camp Organized in Kalaburagi || Free Homeopathy Health Camp Organized in Kal
    ("9a80142e-9ed5-40db-b5e6-533802f316b2", "723602c0-e39a-4b3e-a7c6-951c7efc5cf8"): True,  # 0.638 · Priyanka Gandhi demands criminal case agains || Priyanka Gandhi demands criminal action agai
    ("18f20b0a-dac6-4179-8f6a-c195e1c1de0a", "1a26823b-ad9f-434b-ad68-1005a52a0d12"): False,  # 0.692 · 30,000 cops deployed for Ganesh immersion pr || Police deployed in Hyderabad and Mumbai for 
    ("d2134f08-b97b-469e-8574-e92bad37b421", "fe658e99-9ea6-4b64-94cd-0ca253200339"): True,  # 0.661 · Bus catches fire on Yamuna Expressway near G || Nine killed after bus catches fire in Greate
    ("fe3c5278-5307-429e-a1ff-bd2e6b7241cc", "eed4d6a6-d23b-40fb-be83-eecc5dfdbfde"): True,  # 0.706 · Woman falls into boiling sambar and dies in  || Woman dies after falling into boiling sambar
    ("657a071d-40db-40a0-b8da-aead45cb04a7", "b5487471-eeac-4e02-93f6-b1d0db69285c"): True,  # 0.665 · Researchers at RGCB in Keralam develop nanop || Indian Researchers Develop Nanopore Sensors 
    ("e0e7ec2e-0442-486c-a558-0dbdcce1f48f", "52b29492-6dd2-4888-98dd-91e0ad499dbe"): True,  # 0.646 · Nine die as passenger bus catches fire on Ya || At least nine killed as sleeper bus catches 
    ("71193f64-9820-4a25-a0cc-7174f2eea5c7", "c89e8e3c-bf1d-4b86-af04-33e937f9d795"): True,  # 0.66 · Rahul Gandhi demands resignation of Gyanesh  || Rahul Gandhi demands resignation of CEC Gyan
    ("44433812-c15c-4200-aef3-968d0f3f5f36", "06c40b64-d699-4d2a-917b-8d6951c84f35"): True,  # 0.627 · BJP and Congress trade barbs over Modi mimic || BJP Criticizes Congress Over Mimicry of PM M
    ("4e4b7348-34a9-4155-915d-f31aec03c960", "972b2f26-dbf7-4cc8-a17e-09c2cbd0f4ff"): True,  # 0.636 · Italy To Ban Burqas In Schools And Cap Forei || Italy proposes ban on burqas and niqabs in s
    ("51690770-84c8-4dce-b66b-f70dd604da6b", "3dde428c-f031-4302-9d34-5a620d75c314"): False,  # 0.616 · H.D. Kumaraswamy criticizes state government || H.D. Kumaraswamy criticizes state government
    ("a4b0499d-63f6-4021-908a-1edf7738d80b", "1ef7c122-b303-401a-bb6f-e5dfbcd7db98"): True,  # 0.637 · Super El Niño may cause 451,000 additional g || Super El Niño could cause 450,000 deaths in 
    ("f6b85658-43e5-48cb-9803-781f0ffe642a", "4384788e-4afd-4a7f-ab98-676306dd3ce0"): True,  # 0.684 · Banks to remain open this Sunday || All Banks to Remain Open on Sunday Ahead of 
    ("1255c9ae-fc7b-4d78-a310-28f72cb348f9", "940a6f6d-c87a-4d32-966e-533c77680f63"): True,  # 0.681 · Family Alleges Expatriate Murdered in Sharja || Karnataka man murdered in Sharjah with disme
    ("92543cca-b86a-47bd-93f9-5425cfaa5d32", "164660f6-6661-4269-bf4c-d46cc82297fb"): True,  # 0.952 · Rahul Gandhi demands resignation of Election || Rahul Gandhi demands resignation of Chief El
    ("3e72821a-b171-46a8-bbe5-e67a37604b56", "5b073057-f28e-468e-b1dd-1f80e09305b1"): False,  # 0.799 · Current Water Levels of Major Karnataka Dams || Water Levels of Major Dams in Karnataka
    ("38922b05-78cb-45e6-9a99-20e7615182e2", "2f10a0b1-5479-41a0-b172-fb2ad956682c"): True,  # 0.817 · Karnataka bans student selfies and reels on  || Karnataka government bans selfies, reels on 
    ("c313ba21-c3b9-458e-ae07-2505ee1a4515", "6c600837-6557-4166-83fd-51db7ecb0cec"): False,  # 0.763 · 34,542 cases settled at National Lok Adalat  || 27,531 cases settled in Lok Adalat in Dharwa
    ("1cbe0036-6693-47ef-af24-4125588fa569", "4db0e8d6-000e-4c5c-947a-3c3015a6e77e"): True,  # 0.762 · Zelenskyy and Trump to meet in New York ahea || Trump and Zelenskyy set to meet in New York
    ("40f66e02-891c-4b8b-8e6e-e52b6d664d32", "f11eef41-5a66-4a97-b233-0381a88e534c"): False,  # 0.766 · Deep depression in Bay of Bengal expected to || Deep depression in Bay of Bengal may bring h
    ("803f4aa5-76e2-4452-8746-5643bededc97", "96ef8e29-5ce6-42c4-93d4-5a1e23d92ff8"): True,  # 0.845 · IIT Bombay replaces ceiling fans with wall-m || IIT Bombay to replace ceiling fans with wall
    ("06c472e3-ab8c-4c7d-9b24-479b3615db99", "8cc9c28f-4319-424f-8260-a1fd494c913d"): True,  # 0.753 · Rani Mukerji's mother Krishna Mukherjee pass || Bollywood actress Rani Mukherjee's mother Kr
    ("9ee3b860-0c1e-45b4-badb-434e09d589e7", "be5fb1b6-e5a3-443c-9e40-0360b11bc3b7"): False,  # 0.766 · Afghanistan says 3 killed in Pakistani airst || India condemns Pakistani airstrikes on Afgha
    ("4f16dc63-dd96-49be-9cf1-38dabec36283", "051f11ff-443e-45f3-85da-0c14197d9d71"): True,  # 0.755 · Election Commission denies reports of intern || Election Commission denies internal rift ove
    ("11183aad-0dd6-4a40-aee7-b7e8004a089c", "164660f6-6661-4269-bf4c-d46cc82297fb"): True,  # 1.0 · Rahul Gandhi demands resignation of Chief El || Rahul Gandhi demands resignation of Chief El
    ("2ad64248-6465-48fc-8869-e1a609fe8e6b", "c6fbeca6-9e8c-4ec5-ba14-52df8bb58404"): True,  # 0.807 · India tests indigenous KAL long-range strike || Noida firm successfully tests indigenous KAL
    ("e0e7ec2e-0442-486c-a558-0dbdcce1f48f", "617c54ef-60e0-460c-b93f-143d0aa4ecd3"): True,  # 0.829 · Nine die as passenger bus catches fire on Ya || Nine die as sleeper bus catches fire on Yamu
    ("ee94207c-cb9a-4fee-b375-4986663a1ae9", "c019f9a9-dabe-4063-877d-3baaa7a0e6cd"): True,  # 0.783 · Rahul Gandhi Accuses BJP, RSS, and Election  || Rahul Gandhi accuses BJP and Election Commis
    ("8b10a332-263b-4f69-99e8-27ec713d6e94", "ea145d7f-35f3-40a2-ac47-14a0926831e7"): False,  # 0.867 · Youth killed after being hit by government b || Youth dies after being hit by government bus
    ("8dbd18bc-93d1-41cc-afaf-ff5ef76f6366", "e3a54169-93ba-4a29-ae2f-191c8a0d0ed0"): True,  # 0.815 · India wins silver in 4x400 mixed relay || India wins silver medal in mixed 4x400 meter
    ("add78158-dce4-4c66-9844-f604899f7225", "589d2141-cf80-4846-9159-60028134c265"): True,  # 0.812 · Jay Meena wins India's first Asian Games sof || India wins first Asian Games medal in soft t
    ("e5159d23-6e51-4900-b9ff-3402d7def505", "f017e7d7-48ac-40e3-b3d5-233c7932c2e2"): True,  # 0.937 · Mirabai Chanu wins silver medal at Asian Gam || Mirabai Chanu Wins Silver at Asian Games
    ("8a5210e5-a9bd-4575-9a02-f7c66f480397", "641338d8-95eb-4b64-9fac-4b8df19ad538"): True,  # 0.805 · Indian Women Skeet Team Wins Bronze at 2026  || Indian Women Skeet Team Wins First Asian Gam
    ("c7cc5734-c61a-47b3-9591-cd75738f13d5", "7d50d001-b788-48e2-8aa6-bb8e9e1af55b"): True,  # 0.825 · FSSAI proposes ban on the term paneer for no || FSSAI Proposes Ban on Using Term Paneer for 
    ("b569c014-85bf-496d-9b7d-01dddd296a40", "b6b8ce1a-617f-468a-b0e0-49e8b2c99372"): True,  # 0.938 · Seema Kumari Wins Bronze in 10,000m at 2026  || Seema Kumari wins 10,000m bronze medal at As
    ("3a00152e-e2fa-4aa7-878f-59660c0ee2f8", "60a68d73-164f-427c-aed9-ea7827c013e2"): True,  # 0.767 · Satnam Singh and Salman Khan Win Bronze at A || Asian Games Rowers Satnam and Salman Win Bro
    ("70bc7b6a-8dbe-4302-9895-8664825024c8", "617c54ef-60e0-460c-b93f-143d0aa4ecd3"): True,  # 0.923 · Nine die in sleeper bus fire on Yamuna Expre || Nine die as sleeper bus catches fire on Yamu
    ("70bc7b6a-8dbe-4302-9895-8664825024c8", "fa5dd2b3-9343-41f6-a3f2-4530526e6165"): True,  # 0.76 · Nine die in sleeper bus fire on Yamuna Expre || Nine killed in bus fire on Yamuna Expressway
    ("b5d3bef7-a70e-49a0-8ae0-de202af9e2b4", "baab1d0e-1f44-4d12-98cc-76b1bb098d3c"): True,  # 1.0 · Elavenil Valarivan wins two silver medals at || Elavenil Valarivan Wins Two Silver Medals at
    ("06c472e3-ab8c-4c7d-9b24-479b3615db99", "93abc441-1f49-41f2-a090-8034da60ad5b"): True,  # 0.858 · Rani Mukerji's mother Krishna Mukherjee pass || Rani Mukerji Mother Krishna Mukherjee Dies a
    ("1d30db69-b95d-4b00-8d87-7dc2c1f34288", "e4e0ee13-e235-41f3-b378-2796010296f5"): True,  # 0.87 · Mahua Moitra files complaint against Electio || Mahua Moitra files complaint against CEC Gya
    ("4196728b-9a84-49cb-be33-208ad6448a1e", "47fa8e71-08e9-4703-968c-bfdffacf640c"): True,  # 0.766 · President Murmu Presents 72nd National Film  || President Murmu Presents 72nd National Film 
}
