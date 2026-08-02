"""Hand-labelled SAME-EVENT judgements over a uniformly random sample.

The counterpart to tools/gold_labels, and the one to trust for anything corpus-
level. gold_labels covers the six LARGEST events — picked because over-merge was
worst there — so it cannot support a claim about the corpus. This set starts from
25 news articles drawn uniformly at random (setseed(0.42)), then pulls a
deliberately over-broad candidate net around each: any shared person/company/org
actor, OR title trigram similarity > 0.18, within the matcher's own 4-day window.
Wider than anything the matcher would accept, so a true sibling it MISSES still
appears here as a pair to judge.

Measured on production 2026-07-31, over these 156 pairs:

    correctly merged   (TP):  19        pairwise precision 0.613
    wrongly merged     (FP):  12        pairwise recall    0.679
    missed merges      (FN):   9
    correctly separate (TN): 116

Two things follow, and the second deleted a planned workstream:

  - Over-merge (12) still slightly outweighs under-merge (9). The biased slice had
    suggested fragmentation was now the live failure; on a random sample it is not.
  - PAIR COMPLETENESS IS 100%: all 28 true pairs appeared in the candidate net. The
    matcher SEES every sibling it fails to merge, so candidate generation is not the
    defect and blocking/LSH would buy nothing. The scoring function is the defect.

The two error shapes want opposite threshold moves, which is why tuning one
threshold keeps trading one for the other:

  over-merge  = same topic, different announcement. Five distinct Bhogapuram
                airport stories fused; two days of one daily roundup column fused.
  under-merge = different outlets phrasing one event. "Bihar government to withdraw
                cases" vs "Bihar withdraws FIRs against NEET protesters".

THE BIASED SLICE CANNOT TRAIN A THRESHOLD FOR THIS ONE. Measured 2026-07-31: an
IDF-weighted title word-cosine tuned on tools/gold_labels' 14,535 pairs picks 0.12
(best F1 0.443 there), and frozen at 0.12 it scores P=0.272 R=1.000 F1=0.427 on
this set — worse than the production cascade it was meant to replace. The two sets
have different negative distributions: every pair in the biased slice sits inside
one of six topically-tight political events, so its hard negatives look nothing
like a random article's neighbourhood.

The same feature tuned ON this set reaches F1 0.739 (P 0.944, R 0.607 at 0.42),
which is a real signal and materially better than production's 0.644 — but that
number is fitted and evaluated on the same 156 pairs and is therefore optimistic.
With 28 positives this set can honestly do one job or the other, not both. Growing
it is the prerequisite for any tuned threshold or learned classifier.

Labelling honesty: 3-4 of the 156 are genuine judgement calls (the Bhogapuram
inauguration build-up, the cricket vice-captaincy story). A second annotator would
differ on those. Do not quote 0.613 to three decimals.
"""

# (seed_article_id, candidate_article_id) -> same real-world event?
GOLD_PAIRS: dict[tuple[str, str], bool] = {
    ("22e8dd74-6e34-42e7-ae69-ff68d05ea55d", "7314e8f3-d3e5-4c7a-8ae5-ab83ce29bbd1"): False,
    # Water supply to be disrupted for 24 hours in p  ||  Water supply disruption in Benglauru on July 3
    ("22e8dd74-6e34-42e7-ae69-ff68d05ea55d", "92c5adb7-d678-4916-8cb4-f4530f088fb6"): False,
    # Water supply to be disrupted for 24 hours in p  ||  Water supply disruption in Benglauru on July 3
    ("22e8dd74-6e34-42e7-ae69-ff68d05ea55d", "484e4e11-2eb8-4e6a-9c33-29cf03131b0f"): False,
    # Water supply to be disrupted for 24 hours in p  ||  Evening rains drench multiple parts of Hyderab
    ("22e8dd74-6e34-42e7-ae69-ff68d05ea55d", "c035c270-6b2c-49b8-8c75-05a1efde229b"): False,
    # Water supply to be disrupted for 24 hours in p  ||  Evening rains drench multiple parts of Hyderab
    ("22e8dd74-6e34-42e7-ae69-ff68d05ea55d", "7a2eb009-4d60-4d9a-948a-e06de20c8169"): False,
    # Water supply to be disrupted for 24 hours in p  ||  Cockroach Janta Party plans peaceful march in 
    ("22e8dd74-6e34-42e7-ae69-ff68d05ea55d", "c492c7fb-a444-46fc-a469-af9fa24286bf"): False,
    # Water supply to be disrupted for 24 hours in p  ||  Cockroach Janta Party plans peaceful march in 
    ("22e8dd74-6e34-42e7-ae69-ff68d05ea55d", "f547b076-c96e-4264-a028-b3badf515300"): False,
    # Water supply to be disrupted for 24 hours in p  ||  BMC announces 15% water cut for 20 hours in pa
    ("22e8dd74-6e34-42e7-ae69-ff68d05ea55d", "2a7ae9d3-80f7-44c0-8d02-c24b3522a78f"): False,
    # Water supply to be disrupted for 24 hours in p  ||  Suspected drug peddler rams car into policemen
    ("3bfc2428-4ee6-49b0-9aef-470cd6aeb987", "b518d451-24fb-40fc-a0ef-8d6ea78c350e"): True,
    # Bihar government to withdraw cases lodged agai  ||  Bihar withdraws FIRs against NEET paper leak p
    ("3bfc2428-4ee6-49b0-9aef-470cd6aeb987", "5fe15293-1a53-4b65-a8fa-beccd629c486"): True,
    # Bihar government to withdraw cases lodged agai  ||  Bihar govt relents, to withdraw youth protest-
    ("3bfc2428-4ee6-49b0-9aef-470cd6aeb987", "cfd7e843-2ac0-4176-91bd-a4e6ee0af463"): False,
    # Bihar government to withdraw cases lodged agai  ||  Assam to drop CJP protest cases, release detai
    ("3bfc2428-4ee6-49b0-9aef-470cd6aeb987", "06224b53-af2e-45d2-aed9-0cbb280d1be5"): False,
    # Bihar government to withdraw cases lodged agai  ||  Assam to withdraw cases against CJP protesters
    ("3bfc2428-4ee6-49b0-9aef-470cd6aeb987", "b11646ff-3385-46d6-a612-16d0cd75c266"): False,
    # Bihar government to withdraw cases lodged agai  ||  After Bihar, Assam withdraws cases against pro
    ("3bfc2428-4ee6-49b0-9aef-470cd6aeb987", "bab013b8-ac21-4d25-824d-b8f5622559d9"): False,
    # Bihar government to withdraw cases lodged agai  ||  No action against CJP protesters: Delhi govern
    ("3bfc2428-4ee6-49b0-9aef-470cd6aeb987", "2e1a64b1-cc38-407b-b701-4051f0d0a5a4"): False,
    # Bihar government to withdraw cases lodged agai  ||  Tushar Gandhi urges Kerala to quash cases file
    ("3bfc2428-4ee6-49b0-9aef-470cd6aeb987", "3dc53d02-6e20-4ece-8a39-bfb63ecba115"): False,
    # Bihar government to withdraw cases lodged agai  ||  Cauvery row: Farmers in Mysuru threaten to ste
    ("8e724b21-90bf-4de6-a538-43c734404cf8", "11987bf5-6d68-46c5-84ef-d8a7c0429a95"): False,
    # Bhogapuram airport to be gateway of Global And  ||  Bhogapuram airport set to take flight on triba
    ("8e724b21-90bf-4de6-a538-43c734404cf8", "31b4ad2e-cca8-4031-9eb4-1742667606d4"): False,
    # Bhogapuram airport to be gateway of Global And  ||  Routes to Bhogapuram airport mapped on Google 
    ("8e724b21-90bf-4de6-a538-43c734404cf8", "e1e93017-1251-4a26-bc97-aa6b862cb0b0"): False,
    # Bhogapuram airport to be gateway of Global And  ||  Routes to Bhogapuram airport mapped on Google 
    ("8e724b21-90bf-4de6-a538-43c734404cf8", "1b784a26-259c-4e1c-b7ef-5828b986255a"): False,
    # Bhogapuram airport to be gateway of Global And  ||  Six-day campaign under way ahead of Bhogapuram
    ("8e724b21-90bf-4de6-a538-43c734404cf8", "f29553d7-3251-478e-aab6-2a8e57a46ec7"): False,
    # Bhogapuram airport to be gateway of Global And  ||  Six-day campaign under way ahead of Bhogapuram
    ("8e724b21-90bf-4de6-a538-43c734404cf8", "5989955b-6b25-4917-9211-bf9b230d5fa9"): False,
    # Bhogapuram airport to be gateway of Global And  ||  Two lakh people to be mobilised for Bhogapuram
    ("8e724b21-90bf-4de6-a538-43c734404cf8", "c45dcba3-d3ce-413f-bdbf-826c53cb6f67"): False,
    # Bhogapuram airport to be gateway of Global And  ||  Two lakh people to be mobilised for Bhogapuram
    ("8e724b21-90bf-4de6-a538-43c734404cf8", "e4fb0127-ed6e-49bc-ac4c-558e05b5a9b1"): False,
    # Bhogapuram airport to be gateway of Global And  ||  ‘Telugu Mahotsavam’ to be annual  event, says 
    ("fc8d70d9-dde1-41b6-985a-9918483c208d", "4793f698-6e12-41cd-8e3f-53508004d64a"): True,
    # KPSC veterinary officer recruitment row: Two F  ||  KPSC veterinary officer recruitment row: Two F
    ("fc8d70d9-dde1-41b6-985a-9918483c208d", "4d5e015f-1b19-4fd5-b32a-d7de8fd21123"): False,
    # KPSC veterinary officer recruitment row: Two F  ||  Ex-KPSC chief now faces probe in veterinary of
    ("fc8d70d9-dde1-41b6-985a-9918483c208d", "678b5e62-8814-415e-9861-4879a02f60db"): False,
    # KPSC veterinary officer recruitment row: Two F  ||  KPSC temporarily stays veterinary officer sele
    ("fc8d70d9-dde1-41b6-985a-9918483c208d", "902c32d1-185b-4df7-8f72-70c6f2179bcc"): False,
    # KPSC veterinary officer recruitment row: Two F  ||  Chhattisgarh public service commission ex-Chai
    ("fc8d70d9-dde1-41b6-985a-9918483c208d", "91a32e6c-51aa-4a58-bd7e-0ad711c79c5a"): False,
    # KPSC veterinary officer recruitment row: Two F  ||  Two foreign nationals arrested in ₹20 lakh fak
    ("fc8d70d9-dde1-41b6-985a-9918483c208d", "65f2e945-bd6b-4d05-9d9c-c9105ea2c55b"): False,
    # KPSC veterinary officer recruitment row: Two F  ||  T’gana: Police launch search for IPS trainee o
    ("fc8d70d9-dde1-41b6-985a-9918483c208d", "bcae3554-bdbd-4df6-988a-5004f02a4418"): False,
    # KPSC veterinary officer recruitment row: Two F  ||  FIR in alleged KPSC scam: OMR answer sheet tam
    ("fc8d70d9-dde1-41b6-985a-9918483c208d", "766610db-f865-47b2-9c14-1a25f4a6b221"): False,
    # KPSC veterinary officer recruitment row: Two F  ||  Four booked for cheating pharma firm manager o
    ("e2d90dd9-e25d-443d-bed2-0918f8efeb7e", "642b65c3-10ba-48c4-8d5b-69866672f902"): True,
    # Sabarimala gold theft case: SIT arrests former  ||  Sabarimala gold theft case: SIT arrests former
    ("e2d90dd9-e25d-443d-bed2-0918f8efeb7e", "a1e819cc-2147-4bc1-a0d7-117db1f1c283"): True,
    # Sabarimala gold theft case: SIT arrests former  ||  Sabarimala gold theft case: SIT detains former
    ("e2d90dd9-e25d-443d-bed2-0918f8efeb7e", "e63747a3-f1c7-4cc7-8160-4626999fe864"): True,
    # Sabarimala gold theft case: SIT arrests former  ||  Sabarimala gold theft case: SIT detains former
    ("e2d90dd9-e25d-443d-bed2-0918f8efeb7e", "e4988eb9-d4cd-4aa8-880a-9ac2dbff6bca"): False,
    # Sabarimala gold theft case: SIT arrests former  ||  Ex-TDB chief fears arrest, alleges political v
    ("e2d90dd9-e25d-443d-bed2-0918f8efeb7e", "36d50101-c160-465b-aef7-511e0cfe5a2d"): False,
    # Sabarimala gold theft case: SIT arrests former  ||  Land scam: TDP presses for arrest of former Sp
    ("e2d90dd9-e25d-443d-bed2-0918f8efeb7e", "762e484c-36b2-45ca-8549-524575d70e7b"): False,
    # Sabarimala gold theft case: SIT arrests former  ||  Sabarimala gold loss case probe continuing ver
    ("e2d90dd9-e25d-443d-bed2-0918f8efeb7e", "d86f562e-23a8-4f9d-ae7f-0adacbddb637"): False,
    # Sabarimala gold theft case: SIT arrests former  ||  Kerala sandalwood theft racket busted; CCB arr
    ("e2d90dd9-e25d-443d-bed2-0918f8efeb7e", "cd6f5230-38b0-4b79-acaa-c798618a6dc6"): False,
    # Sabarimala gold theft case: SIT arrests former  ||  SIT formed to probe land grab charges against 
    ("67a0507f-37d2-4063-b9b3-615a46186042", "dc3727d9-75c2-4813-8828-b238b41d383b"): True,
    # Kerala Women’s Commission asks police to act s  ||  Kerala Women’s Commission asks police to act s
    ("67a0507f-37d2-4063-b9b3-615a46186042", "024f7162-cd55-4273-a6aa-53dd865df864"): False,
    # Kerala Women’s Commission asks police to act s  ||  Swapna, 5 others named accused in Kerala’s Wad
    ("67a0507f-37d2-4063-b9b3-615a46186042", "1b3bbc81-cdf8-4c0b-a9aa-ab3d03257c75"): False,
    # Kerala Women’s Commission asks police to act s  ||  Swapna, 5 others named accused in Kerala’s Wad
    ("67a0507f-37d2-4063-b9b3-615a46186042", "084bbf9e-5219-456c-abb2-470538ded9bb"): False,
    # Kerala Women’s Commission asks police to act s  ||  Kerala Police Officers’ Association comprising
    ("67a0507f-37d2-4063-b9b3-615a46186042", "17d09544-ed73-4d28-a026-0b72deb8bc1c"): False,
    # Kerala Women’s Commission asks police to act s  ||  Kerala Police Officers’ Association comprising
    ("67a0507f-37d2-4063-b9b3-615a46186042", "3cfcd393-d184-473d-8a46-878e38d9a95f"): False,
    # Kerala Women’s Commission asks police to act s  ||  Why wasn’t child sexual abuse content reported
    ("67a0507f-37d2-4063-b9b3-615a46186042", "2cd160a7-7630-49ac-89a2-b9069c338936"): False,
    # Kerala Women’s Commission asks police to act s  ||  Anil Akkara seeks transfer of all Vigilance fi
    ("67a0507f-37d2-4063-b9b3-615a46186042", "c46360c8-2f7b-4315-be52-51c10c7cc0fd"): False,
    # Kerala Women’s Commission asks police to act s  ||  Anil Akkara seeks transfer of all Vigilance fi
    ("772989c6-d229-4929-9e2a-0d993ec9a4ef", "925fcbef-ec28-469f-92bd-a026cf13a530"): False,
    # IIT Delhi Roommates Built a ₹565 Crore Startup  ||  MoU signed to boost innovation in medical robo
    ("9c3d44df-a4b6-4321-959a-77252d488803", "c71493d5-ea25-46d1-9a7d-2952a9cd032d"): True,
    # Trump approves nuclear agreement that may allo  ||  Trump approves Saudi nuclear agreement, opens 
    ("9c3d44df-a4b6-4321-959a-77252d488803", "083bd3bc-7834-4044-9cd5-1357a9b5a639"): True,
    # Trump approves nuclear agreement that may allo  ||  Trump clears Saudi Arabia nuclear agreement: A
    ("9c3d44df-a4b6-4321-959a-77252d488803", "8e183a82-5fd5-4665-9f48-5912c57deb5e"): True,
    # Trump approves nuclear agreement that may allo  ||  Trump's Saudi Nuclear Pact Opens Door To Urani
    ("9c3d44df-a4b6-4321-959a-77252d488803", "07ce4336-8a7b-4200-ba09-0c6ab45b137c"): True,
    # Trump approves nuclear agreement that may allo  ||  US, Saudi Arabia sign civil nuclear deal pavin
    ("9c3d44df-a4b6-4321-959a-77252d488803", "9d471d23-8245-4b26-8033-301e926c180f"): True,
    # Trump approves nuclear agreement that may allo  ||  US Announces Landmark Nuclear Deal With Saudi 
    ("9c3d44df-a4b6-4321-959a-77252d488803", "461fe173-b503-457a-9e5b-b7cb2c447495"): True,
    # Trump approves nuclear agreement that may allo  ||  From oil to atoms: Donald Trump to open nuclea
    ("9c3d44df-a4b6-4321-959a-77252d488803", "c4e2e7cf-ae1d-4625-8baa-9f30616b0674"): False,
    # Trump approves nuclear agreement that may allo  ||  US House approves $95 billion Iran war budget,
    ("9c3d44df-a4b6-4321-959a-77252d488803", "deba1f6c-c248-4dd4-b455-7a70e6e52446"): False,
    # Trump approves nuclear agreement that may allo  ||  Why is a US-Saudi nuclear pact causing alarm i
    ("47d335d4-d917-440f-811a-5bfff9407c48", "d59ab03a-74bf-4576-849f-291902211610"): True,
    # Kala Utsav-2026 held at KV School  ||  Kala Utsav-2026 held at KV School
    ("47d335d4-d917-440f-811a-5bfff9407c48", "b0944004-f7e9-4bc8-abfa-73cec0a9a44b"): False,
    # Kala Utsav-2026 held at KV School  ||  Ravi Mohan divorce case: Court rejects Rs 40 l
    ("06809d03-6ca1-4e49-9f1a-db0e9a991d59", "d658817d-5398-49e8-9f8e-14e6686f3a8c"): False,
    # Bezos, Saverin may join Amit Bhatia-led Liverp  ||  Tamil Nadu signs investment MoUs in GCC, advan
    ("06809d03-6ca1-4e49-9f1a-db0e9a991d59", "1dd8afdd-7572-41d4-b270-2591931017c7"): False,
    # Bezos, Saverin may join Amit Bhatia-led Liverp  ||  Jeff Bezos ex-wife MacKenzie Scott helped writ
    ("3edf773d-5c2b-4edf-8f35-2d5a2214e9b8", "86b65887-7797-4f17-8248-ce0c75d5d948"): False,
    # Neighbours’ dispute turns fatal, youth hacked   ||  Kerala govt. promises to correct deficiencies 
    ("3edf773d-5c2b-4edf-8f35-2d5a2214e9b8", "b84152ab-697e-45b5-ac90-9eeaedc055f3"): False,
    # Neighbours’ dispute turns fatal, youth hacked   ||  Man hacked to death in Kalaburagi
    ("3edf773d-5c2b-4edf-8f35-2d5a2214e9b8", "c20a1485-6036-4fc1-ae33-4bae3b106af9"): False,
    # Neighbours’ dispute turns fatal, youth hacked   ||  Man hacked to death in Kalaburagi
    ("3edf773d-5c2b-4edf-8f35-2d5a2214e9b8", "1ce59191-ca56-453a-8e16-05f11e3a958a"): False,
    # Neighbours’ dispute turns fatal, youth hacked   ||  31 arrested, 97 wanted persons detained in mas
    ("3edf773d-5c2b-4edf-8f35-2d5a2214e9b8", "158cd6cb-5ca7-4f2c-8aee-029b1ac534b4"): False,
    # Neighbours’ dispute turns fatal, youth hacked   ||  Pier anglers in Kerala’s Thiruvananthapuram aw
    ("3edf773d-5c2b-4edf-8f35-2d5a2214e9b8", "0d30bfe6-fc31-4957-820e-c4e349807c75"): False,
    # Neighbours’ dispute turns fatal, youth hacked   ||  Thiruvananthapuram Corporation council in Kera
    ("3edf773d-5c2b-4edf-8f35-2d5a2214e9b8", "12c672b5-65a5-46bc-adb8-41d31dfc4d6d"): False,
    # Neighbours’ dispute turns fatal, youth hacked   ||  Kerala HC declines to suspend sentence of two 
    ("3edf773d-5c2b-4edf-8f35-2d5a2214e9b8", "a3e2ddcb-e771-410a-996c-592a9c06620c"): False,
    # Neighbours’ dispute turns fatal, youth hacked   ||  Two die in separate accidents in Chikkamagalur
    ("9815cfed-6373-4ffc-b3c0-777cde47787d", "e0620cbf-066d-437e-9f94-e9d357a425b6"): True,
    # Madras High Court strikes down order granting   ||  Madras High Court strikes down order granting 
    ("9815cfed-6373-4ffc-b3c0-777cde47787d", "8ac1c4bb-a85a-4987-84d9-97c9f6b5b43c"): True,
    # Madras High Court strikes down order granting   ||  Madras High Court cancels govt jobs for Karur 
    ("9815cfed-6373-4ffc-b3c0-777cde47787d", "a3a61129-ecbf-4472-b229-293b5ec67a37"): True,
    # Madras High Court strikes down order granting   ||  Setback for Vijay-led TVK govt! Madras HC sets
    ("9815cfed-6373-4ffc-b3c0-777cde47787d", "2d64f477-9edc-49ae-8c21-d2618db912b2"): False,
    # Madras High Court strikes down order granting   ||  Tamil Nadu CM Vijay to distribute govt. job ap
    ("9815cfed-6373-4ffc-b3c0-777cde47787d", "e867125b-f7d4-43e9-a876-3a54c29840ab"): False,
    # Madras High Court strikes down order granting   ||  Tamil Nadu CM Vijay to distribute govt. job ap
    ("9815cfed-6373-4ffc-b3c0-777cde47787d", "0f636310-16cc-4f3a-b450-b78b9c28710e"): True,
    # Madras High Court strikes down order granting   ||  'Could open floodgates': Why HC quashed Vijay 
    ("9815cfed-6373-4ffc-b3c0-777cde47787d", "6ead88ea-8c48-4fda-a6d8-68ca68778a32"): False,
    # Madras High Court strikes down order granting   ||  Madras High Court to hear PIL on Karur Devadan
    ("9815cfed-6373-4ffc-b3c0-777cde47787d", "78425d11-7b87-49ee-a45a-2f24e51beb2e"): False,
    # Madras High Court strikes down order granting   ||  Karnataka High Court strikes down Health Secur
    ("b8ddc8f9-b087-4666-a808-07867a98a6be", "eda6caba-2f36-4f00-a03d-9db72b25c0bb"): True,
    # Heavy rain brings cheer to farmers but disrupt  ||  Heavy rains disrupt normal life, raise water l
    ("b8ddc8f9-b087-4666-a808-07867a98a6be", "75f0dac7-6976-476d-b23a-ce04dd7778f6"): True,
    # Heavy rain brings cheer to farmers but disrupt  ||  North Telangana drenched as heavy rain continu
    ("b8ddc8f9-b087-4666-a808-07867a98a6be", "2c7c8d79-683b-4fe0-8d06-e2fcae53ce18"): False,
    # Heavy rain brings cheer to farmers but disrupt  ||  Heavy rain lashes Telangana districts; red ale
    ("b8ddc8f9-b087-4666-a808-07867a98a6be", "62ef74dd-1f58-4ae5-837e-12096d2e3d15"): False,
    # Heavy rain brings cheer to farmers but disrupt  ||  Heavy rainfall forecast in 10 Telangana distri
    ("b8ddc8f9-b087-4666-a808-07867a98a6be", "6874424f-dabb-4d8e-b29d-ce2bf1dfd816"): False,
    # Heavy rain brings cheer to farmers but disrupt  ||  Heavy to very heavy rain forecast for nine Tel
    ("b8ddc8f9-b087-4666-a808-07867a98a6be", "ed62742b-f9a9-486c-be1a-8728d0413219"): False,
    # Heavy rain brings cheer to farmers but disrupt  ||  Heavy rainfall forecast in 10 Telangana distri
    ("b8ddc8f9-b087-4666-a808-07867a98a6be", "5d110557-d1eb-4fcf-8400-38b49324b21d"): False,
    # Heavy rain brings cheer to farmers but disrupt  ||  Heavy rainfall forecast in six Telangana distr
    ("b8ddc8f9-b087-4666-a808-07867a98a6be", "bd6c8ac6-2cb8-4c00-824a-ab9e91d4e4a2"): False,
    # Heavy rain brings cheer to farmers but disrupt  ||  Heavy rainfall forecast in six Telangana distr
    ("296b3aef-0613-41c9-8f1d-f75bb006fafc", "f1f301d4-698f-4adf-a615-a60f7764aade"): False,
    # ಗುಳೆ ತಡೆಗೆ ಉದ್ಯೋಗ ನೀಡಿ: ಸಚಿವ ಈಶ್ವರ ಬಿ. ಖಂಡ್ರೆ   ||  ಅನಿವಾರ್ಯವಿದ್ದರಷ್ಟೇ ಕೊಳವೆಬಾವಿ ಕೊರೆಸಿ- ಸಚಿವ ಈಶ್ವ
    ("263c83a2-7043-4eb3-b093-9a0c31285f0c", "b1fe0305-5275-4936-9b16-02a59ba8c257"): False,
    # CJI on police excess, pellet gun claims and me  ||  Pellet guns and the price of protest: Experts 
    ("263c83a2-7043-4eb3-b093-9a0c31285f0c", "bff4181d-298d-459c-96a6-9aca8c980688"): False,
    # CJI on police excess, pellet gun claims and me  ||  Demand for MSP, reforms: Protesting farmers br
    ("263c83a2-7043-4eb3-b093-9a0c31285f0c", "b6309163-7cab-4394-8909-825c290a9d48"): False,
    # CJI on police excess, pellet gun claims and me  ||  Right to peaceful protest guaranteed, agitatio
    ("263c83a2-7043-4eb3-b093-9a0c31285f0c", "15cbd532-bcf0-44ad-b906-6de93480f1bb"): False,
    # CJI on police excess, pellet gun claims and me  ||  CJP protests: SC mulls independent probe into 
    ("263c83a2-7043-4eb3-b093-9a0c31285f0c", "f6c86bfd-edbc-4258-8f4d-c8ba760b354a"): False,
    # CJI on police excess, pellet gun claims and me  ||  Delhi govt's CJP stir order: What it means for
    ("263c83a2-7043-4eb3-b093-9a0c31285f0c", "e3e9ed91-3f87-4066-8466-890c3424e0d7"): False,
    # CJI on police excess, pellet gun claims and me  ||  Jantar Mantar not closed for protests, Delhi P
    ("263c83a2-7043-4eb3-b093-9a0c31285f0c", "80bfe4e2-e083-43fb-b4a2-600451120d86"): False,
    # CJI on police excess, pellet gun claims and me  ||  RAF fired pellet gun at protesters on the dire
    ("263c83a2-7043-4eb3-b093-9a0c31285f0c", "325dae37-b44b-4ba7-b51b-2dc550faaa80"): False,
    # CJI on police excess, pellet gun claims and me  ||  NEET protests: SC says SIT may be set up to pr
    ("ca976756-cadb-437d-807e-5a044bc8595c", "8cace450-7426-4014-9a99-083f12d7e42d"): False,
    # Police nab youth with methamphetamine  ||  City police busts online loan app racket
    ("ca976756-cadb-437d-807e-5a044bc8595c", "ca1b7c01-7637-4366-8651-ba0d3ca919af"): False,
    # Police nab youth with methamphetamine  ||  City police busts online loan app racket
    ("ca976756-cadb-437d-807e-5a044bc8595c", "1ce59191-ca56-453a-8e16-05f11e3a958a"): False,
    # Police nab youth with methamphetamine  ||  31 arrested, 97 wanted persons detained in mas
    ("ca976756-cadb-437d-807e-5a044bc8595c", "6cfd077b-e7a4-4c6c-a337-bcf5a5170616"): False,
    # Police nab youth with methamphetamine  ||  One more teacher arrested in connection with M
    ("ca976756-cadb-437d-807e-5a044bc8595c", "77717b9e-e547-48cf-aa2d-3f7f017726fd"): False,
    # Police nab youth with methamphetamine  ||  One more teacher arrested in connection with M
    ("3f1f4ed1-64e7-4c5f-9141-3f99c7b33017", "d7c3c06a-babd-42fb-838d-0c6c6530e5e3"): True,
    # 'Fictional, unfounded': BJP dismisses report o  ||  Reports claiming Pradhan quit after CJP reject
    ("3f1f4ed1-64e7-4c5f-9141-3f99c7b33017", "a6d94656-a7e1-431e-a9d8-852abae547cf"): True,
    # 'Fictional, unfounded': BJP dismisses report o  ||  Centre Offered To Change Dharmendra Pradhan's 
    ("3f1f4ed1-64e7-4c5f-9141-3f99c7b33017", "ce986f52-fbb7-4223-9f8d-346d3faeb94a"): False,
    # 'Fictional, unfounded': BJP dismisses report o  ||  BJP forced Pradhan to resign as Gen Z targeted
    ("3f1f4ed1-64e7-4c5f-9141-3f99c7b33017", "6b04c45e-3015-4225-a8a8-fd5521c2a628"): False,
    # 'Fictional, unfounded': BJP dismisses report o  ||  Follow example of Dharmendra Pradhan, resign f
    ("3f1f4ed1-64e7-4c5f-9141-3f99c7b33017", "ba014e73-f07f-4e7f-80dc-d5abe202f2bb"): False,
    # 'Fictional, unfounded': BJP dismisses report o  ||  'Celebrating destruction of children's futures
    ("3f1f4ed1-64e7-4c5f-9141-3f99c7b33017", "53ba206d-3656-4304-88e0-cda55cb788f0"): False,
    # 'Fictional, unfounded': BJP dismisses report o  ||  Dharmendra Pradhan tenders resignation as Unio
    ("3f1f4ed1-64e7-4c5f-9141-3f99c7b33017", "05a2b000-b06e-41e1-83c7-7f376c3dd09c"): False,
    # 'Fictional, unfounded': BJP dismisses report o  ||  CPI slams BJP for felicitating Dharmendra Prad
    ("3f1f4ed1-64e7-4c5f-9141-3f99c7b33017", "1d063e4f-2623-4c7e-8805-4e0e3bb9624a"): False,
    # 'Fictional, unfounded': BJP dismisses report o  ||  CPI slams BJP for felicitating Dharmendra Prad
    ("bc931392-ae3f-4754-a6cd-5220f6619005", "6570e410-2ef8-4ea6-8fa7-be71ab69f234"): True,
    # Young Turks vs Women MPs: Lok Sabha debates st  ||  Centre, Oppn clash as Lok Sabha debates new an
    ("bc931392-ae3f-4754-a6cd-5220f6619005", "b6464c8c-f903-4bc9-ade2-053edc7a2843"): True,
    # Young Turks vs Women MPs: Lok Sabha debates st  ||  Lok Sabha debates anti-paper leak Bill, Opposi
    ("bc931392-ae3f-4754-a6cd-5220f6619005", "0aa1eac5-b4b5-4090-8760-415b088bb2fc"): False,
    # Young Turks vs Women MPs: Lok Sabha debates st  ||  PM Modi back with a selfie video, hails passin
    ("bc931392-ae3f-4754-a6cd-5220f6619005", "b232e908-30db-442f-929b-b9f185757a7c"): False,
    # Young Turks vs Women MPs: Lok Sabha debates st  ||  Parliament monsoon session LIVE: Lok, Rajya Sa
    ("bc931392-ae3f-4754-a6cd-5220f6619005", "df35ffd4-d890-4e85-b967-8d9d7e4a7d29"): False,
    # Young Turks vs Women MPs: Lok Sabha debates st  ||  Odisha med PG exam question paper ‘shared on W
    ("bc931392-ae3f-4754-a6cd-5220f6619005", "73726a90-845a-4133-b019-37b0201ef7af"): False,
    # Young Turks vs Women MPs: Lok Sabha debates st  ||  Govt introduces bill to penalise paper leak in
    ("bc931392-ae3f-4754-a6cd-5220f6619005", "44715466-2860-4aa5-ba94-5d4fb3dc9cc8"): False,
    # Young Turks vs Women MPs: Lok Sabha debates st  ||  Parliament Monsoon Session Day 9 highlights: R
    ("bc931392-ae3f-4754-a6cd-5220f6619005", "47de547d-541a-4e3a-bf1f-5a22f792b302"): False,
    # Young Turks vs Women MPs: Lok Sabha debates st  ||  'Modiji clocked it': BJP MP's Gen Z-style prai
    ("ee542169-4836-4dd9-b538-53604e2352bf", "0f71e6b5-efe1-4483-a029-9164039cf852"): True,
    # Duleep Trophy: Kishan to captain East Zone; So  ||  Future India captain? Selector explains why So
    ("ee542169-4836-4dd9-b538-53604e2352bf", "fbeec930-bfcb-489c-899e-fea23dc1ab10"): False,
    # Duleep Trophy: Kishan to captain East Zone; So  ||  Sooryavanshi the star as India complete 3-0 sw
    ("ee542169-4836-4dd9-b538-53604e2352bf", "8c7d6778-da2d-4735-8a1d-35692ff33e20"): False,
    # Duleep Trophy: Kishan to captain East Zone; So  ||  Laxman: 'Very, very mature knock' from Sooryav
    ("ee542169-4836-4dd9-b538-53604e2352bf", "a07c550a-2c38-4038-86af-8a26eae2157c"): False,
    # Duleep Trophy: Kishan to captain East Zone; So  ||  'I don't focus on what's happening outside' - 
    ("ee542169-4836-4dd9-b538-53604e2352bf", "0306dbd5-b28c-478d-80cf-bceabca57169"): False,
    # Duleep Trophy: Kishan to captain East Zone; So  ||  Kishan and Tilak's blazing knocks help India s
    ("ee542169-4836-4dd9-b538-53604e2352bf", "7bd42a5c-8716-4a36-8344-4c8ffe3968b3"): False,
    # Duleep Trophy: Kishan to captain East Zone; So  ||  वैभव के उप-कप्तान बनने पर भड़के हर्षा भोगले, द
    ("ee542169-4836-4dd9-b538-53604e2352bf", "a9ee19de-b8b8-4034-9b57-15caaea73e1a"): False,
    # Duleep Trophy: Kishan to captain East Zone; So  ||  ಭಟ್ಕಳ ವಿದ್ಯಾಂಜಲಿ ಶಾಲೆಯ ವಿದ್ಯಾರ್ಥಿಗಳಿಂದ ಅಥ್ಲೆಟಿ
    ("5f838f44-528b-4e5f-8a3e-dda2cd097870", "91a32e6c-51aa-4a58-bd7e-0ad711c79c5a"): False,
    # U.S. firm Sonatype to add 100 seats in Hyderab  ||  Two foreign nationals arrested in ₹20 lakh fak
    ("5f838f44-528b-4e5f-8a3e-dda2cd097870", "e487e58a-364c-4eb9-8e12-af40f8af654e"): False,
    # U.S. firm Sonatype to add 100 seats in Hyderab  ||  Hyderabad’s Golden Bonam offered to Goddess Ka
    ("5f838f44-528b-4e5f-8a3e-dda2cd097870", "f7c435c6-760b-4eaf-85f9-218b2dc96974"): False,
    # U.S. firm Sonatype to add 100 seats in Hyderab  ||  Hyderabad-based Olectra becomes first company 
    ("5f838f44-528b-4e5f-8a3e-dda2cd097870", "22e8dd74-6e34-42e7-ae69-ff68d05ea55d"): False,
    # U.S. firm Sonatype to add 100 seats in Hyderab  ||  Water supply to be disrupted for 24 hours in p
    ("5f838f44-528b-4e5f-8a3e-dda2cd097870", "fe0dcf2d-afe7-4121-a5f7-8f69ceb17237"): False,
    # U.S. firm Sonatype to add 100 seats in Hyderab  ||  Food grains for three months to be distributed
    ("5f838f44-528b-4e5f-8a3e-dda2cd097870", "24982625-ba61-45c2-a19a-60594534037b"): False,
    # U.S. firm Sonatype to add 100 seats in Hyderab  ||  Two teenagers killed as lorry hits scooter in 
    ("5f838f44-528b-4e5f-8a3e-dda2cd097870", "b0bce14b-e797-465e-a174-1d7e40147c89"): False,
    # U.S. firm Sonatype to add 100 seats in Hyderab  ||  Over 11,000 applications received for 7,680 af
    ("5f838f44-528b-4e5f-8a3e-dda2cd097870", "ef9772fe-941c-42cf-a622-a6100b243ae1"): False,
    # U.S. firm Sonatype to add 100 seats in Hyderab  ||  Over 11,000 applications received for 7,680 af
    ("f8f98004-4373-4c98-9152-6be23f885364", "b4a046ff-bbbe-4d37-b064-af114b12139b"): True,
    # MoU signed to establish 1,000 Mee Marts across  ||  MoU signed to establish 1,000 Mee Marts across
    ("f8f98004-4373-4c98-9152-6be23f885364", "583d2963-c94f-444a-b23e-3ad01d5e3784"): False,
    # MoU signed to establish 1,000 Mee Marts across  ||  CPI(M) urges people to question MLAs on poll p
    ("f8f98004-4373-4c98-9152-6be23f885364", "a3c4b415-81cd-407a-8526-0c27f989e9df"): False,
    # MoU signed to establish 1,000 Mee Marts across  ||  CPI(M) urges people to question MLAs on poll p
    ("f8f98004-4373-4c98-9152-6be23f885364", "4aa250e9-ea6f-4d64-9418-b51a29638724"): False,
    # MoU signed to establish 1,000 Mee Marts across  ||  Andhra Pradesh to draw up action plan against 
    ("f8f98004-4373-4c98-9152-6be23f885364", "93749c6a-bd0d-49ef-973c-2c385b660062"): False,
    # MoU signed to establish 1,000 Mee Marts across  ||  Andhra Pradesh to draw up action plan against 
    ("f8f98004-4373-4c98-9152-6be23f885364", "936d2850-422d-46f6-875c-802b850d62f2"): False,
    # MoU signed to establish 1,000 Mee Marts across  ||  Depression in the Bay may bring isolated heavy
    ("f8f98004-4373-4c98-9152-6be23f885364", "5d304333-af56-4bb3-a074-4d3b1a8fb8a2"): False,
    # MoU signed to establish 1,000 Mee Marts across  ||  Andhra Pradesh introduces new grading system t
    ("f8f98004-4373-4c98-9152-6be23f885364", "8a491df9-0f6f-48e7-9b30-e0aade03979c"): False,
    # MoU signed to establish 1,000 Mee Marts across  ||  Andhra Pradesh introduces new grading system t
    ("10bb65f4-2ca2-4c35-a93d-2a547f9e4325", "63766317-831e-42bd-8bc7-f3cc29049edd"): True,
    # Asian stocks trade in green: Kospi adds 6%, Ni  ||  Asian Markets Today: South Korea's Kospi Jumps
    ("10bb65f4-2ca2-4c35-a93d-2a547f9e4325", "c15e57b2-b014-4655-89aa-ce680e0ac891"): False,
    # Asian stocks trade in green: Kospi adds 6%, Ni  ||  Plea moved in SC over HC refusal to probe Adan
    ("66b5bda3-2a12-4945-8d40-318e2e05b7bb", "167fc46c-2d9a-4b0b-a6c9-079bce918392"): True,
    # Bindyarani Devi Wins Bronze: India Add Another  ||  CWG: Bindyarani Devi wins bronze; India claims
    ("66b5bda3-2a12-4945-8d40-318e2e05b7bb", "d44a5143-f692-4698-9d75-a6ada3d74660"): False,
    # Bindyarani Devi Wins Bronze: India Add Another  ||  Valluri Ajaya Babu Wins Silver Medal In Men''s
    ("66b5bda3-2a12-4945-8d40-318e2e05b7bb", "8aed8d2f-080a-4b81-ba67-ce347d0e5f77"): False,
    # Bindyarani Devi Wins Bronze: India Add Another  ||  CWG: Gyaneshwari wins silver as India claims 4
    ("66b5bda3-2a12-4945-8d40-318e2e05b7bb", "a671c85c-f95e-4041-be3b-e71417643337"): False,
    # Bindyarani Devi Wins Bronze: India Add Another  ||  CWG Live: 5 Indians Begin Heated Medal Hunt Af
    ("66b5bda3-2a12-4945-8d40-318e2e05b7bb", "416927f5-a6fc-4202-8e17-e2603e6686c2"): False,
    # Bindyarani Devi Wins Bronze: India Add Another  ||  Gyaneshwari Clinches Silver In Weightlifting, 
    ("66b5bda3-2a12-4945-8d40-318e2e05b7bb", "f3072445-a8b8-4f5c-bdbc-5dd48950b8f7"): False,
    # Bindyarani Devi Wins Bronze: India Add Another  ||  CWG: Ajaya Babu wins silver in 79kg weightlift
    ("66b5bda3-2a12-4945-8d40-318e2e05b7bb", "4d6aae34-48b6-4774-8396-3fefdcf75146"): False,
    # Bindyarani Devi Wins Bronze: India Add Another  ||  CWG 2026 India’s medal tally: Complete list of
    ("66b5bda3-2a12-4945-8d40-318e2e05b7bb", "3650b90f-c63c-4117-a716-a22be313aa72"): False,
    # Bindyarani Devi Wins Bronze: India Add Another  ||  CWG 2026 medal table: Where does India stand a
    ("796b62d0-f00f-46aa-8bb5-29b8b294553f", "a07511e9-4ee5-4e7e-b276-0bdaa83eb1ae"): False,
    # Tamil Nadu Today: Speaker sends notices to fou  ||  Tamil Nadu Today: Ammonia gas leak toll rises 
    ("796b62d0-f00f-46aa-8bb5-29b8b294553f", "3d922aef-76d7-4c37-9097-e8177a819edf"): False,
    # Tamil Nadu Today: Speaker sends notices to fou  ||  Tamil Nadu Today: Private schools ordered to d
    ("796b62d0-f00f-46aa-8bb5-29b8b294553f", "ac7a195e-6a5d-4c30-a458-f72420ccf4c2"): False,
    # Tamil Nadu Today: Speaker sends notices to fou  ||  Tamil Nadu Today: Three men arrested in case o
    ("796b62d0-f00f-46aa-8bb5-29b8b294553f", "810beee6-f2d8-41f4-b602-ff408581020d"): False,
    # Tamil Nadu Today: Speaker sends notices to fou  ||  Tamil Nadu Today: DMK MLA Anitha Radhakrishnan
    ("796b62d0-f00f-46aa-8bb5-29b8b294553f", "a29630f6-940e-4834-aebd-e83c802f89c6"): False,
    # Tamil Nadu Today: Speaker sends notices to fou  ||  Tamil Nadu Today: C. Vijayabaskar joins TVK
    ("796b62d0-f00f-46aa-8bb5-29b8b294553f", "28e0160d-acfc-45f3-a139-90089b72e086"): False,
    # Tamil Nadu Today: Speaker sends notices to fou  ||  Tamil Nadu Today: Population Census exercise b
    ("796b62d0-f00f-46aa-8bb5-29b8b294553f", "c4a294cd-012c-4804-b6d2-ce05f34ac9c1"): False,
    # Tamil Nadu Today: Speaker sends notices to fou  ||  Tamil Nadu Today: Government job for kin of 32
    ("796b62d0-f00f-46aa-8bb5-29b8b294553f", "3e6bbcec-3718-4140-8d87-afc6c270b8a6"): False,
    # Tamil Nadu Today: Speaker sends notices to fou  ||  Tamil Nadu Today: Supreme Court stays order ba
}


def pair_count() -> int:
    return len(GOLD_PAIRS)


def positive_count() -> int:
    return sum(GOLD_PAIRS.values())
