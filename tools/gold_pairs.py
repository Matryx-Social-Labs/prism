"""Hand-labelled SAME-EVENT judgements over a uniformly random sample.

The counterpart to tools/gold_labels, and the one to trust for anything corpus-
level. gold_labels covers the six LARGEST events — picked because over-merge was
worst there — so it cannot support a claim about the corpus. This set starts from
60 news articles drawn uniformly at random in two independent batches
(setseed(0.42), n=25 -> 156 pairs; setseed(0.77), n=35 -> 242 pairs), then pulls a
deliberately over-broad candidate net around each: any shared person/company/org
actor, OR title trigram similarity > 0.18, within the matcher's own 4-day window.
Wider than anything the matcher would accept, so a true sibling it MISSES still
appears here as a pair to judge.

Measured on production 2026-07-31. The two batches agree closely, which is the
best evidence available that the sample is representative:

    batch 1 (156 pairs, 28 pos):  P=0.613  R=0.679
    batch 2 (242 pairs, 33 pos):  P=0.629  R=0.667
    combined (398 pairs, 61 pos): P=0.621  R=0.672

Because they are the same distribution, batch 1 trains and batch 2 tests. That is
the split every threshold here is fitted and reported under.

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

THE ONE VALIDATED SIGNAL SO FAR. An IDF-weighted word cosine over TITLES — not
production's pg_trgm character trigrams, a different feature on the same field —
fitted on batch 1 and frozen at 0.39, then measured on batch 2:

    production cascade (today)     P=0.629  R=0.667  F1=0.647  Cdet=0.260
    title IDF cosine >= 0.39       P=0.944  R=0.515  F1=0.667  Cdet=0.083
    union     (merge if either)    P=0.632  R=0.727  F1=0.676  Cdet=0.269
    intersect (merge if both)      P=1.000  R=0.455  F1=0.625  Cdet=0.074

Fit F1 was 0.723, test 0.692 — a small honest gap, so it transfers. Contrast the
same feature tuned on the BIASED slice: F1 0.427 here.

Intersect makes ZERO false merges in 242 pairs, eliminating all thirteen of
production's. But the two signals are largely redundant: the cosine uniquely
catches 2 true pairs where production uniquely catches 7. So it is a CONFIRMING
signal, not a new source of recall, and the open implementation question is where
to apply it — as a gate on the weakest path (entity overlap) rather than globally.
Answering that needs a per-path breakdown this file does not yet carry. Do not
guess it; measure it.

PAIRWISE MEASUREMENT SYSTEMATICALLY OVER-PREDICTS THE VALUE OF TIGHTENING. This
is the most expensive lesson these labels have taught and it is worth reading
before proposing anything measured on them.

A headline-agreement gate on the entity_overlap path was built on exactly this
data. The attribution was sound: entity_overlap made 22 of the 25 wrong merges at
precision 0.353, while title_time and embedding were 4/4 and url_exact 0.870. The
gate was fitted on the train half, frozen, and measured once on the held-out half:

    production        P=0.629  R=0.667  F1=0.647  Cdet=0.260   13 wrong merges
    with the gate     P=0.833  R=0.606  F1=0.702  Cdet=0.120    4 wrong merges

Then it was replayed through the REAL matcher over 1,428 articles, and it lost:

                            without gate      with gate
    clusters (41 gold)           40               80
    B-cubed recall             0.8227           0.5178
    articles rejoining a
      story that exists          346              124
    events from 1,428 arts       687              903

Predicted recall cost: 9%. Actual: 37%. Four times worse, and it took cluster
count from near-perfect to double.

The cause is compounding, which pairwise scoring cannot see because it has no
state: every rejected merge starts a NEW event, that event becomes a smaller,
wrong candidate for the next article, and the story shatters. A pair scored in
isolation always looks like an independent decision. In a greedy cascade it never
is.

So: any change measured here must be replayed with `tools/scratch --score` before
it is believed. Three changes have now been killed at a higher fidelity level than
the one that endorsed them (proportional corroboration by data, the article-to-
event cosine by review, this gate by replay). The pattern is not bad luck.

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
    ("f1c59dc5-3434-4e9f-9bbe-0802fa637a71", "d936c8ec-80de-425e-8b5a-c4597b0362a0"): False,
    # Trafficking ring used FB ad to lure 2 Karnat  ||  Role of agent under probe in alleged child t
    ("f1c59dc5-3434-4e9f-9bbe-0802fa637a71", "ca79611f-e5c2-4760-9d9e-b9779b43fe20"): False,
    # Trafficking ring used FB ad to lure 2 Karnat  ||  Bengaluru Traffic Police proposes regulated 
    ("f1c59dc5-3434-4e9f-9bbe-0802fa637a71", "1e27d9eb-4afc-4719-998e-02eb0d5e3c28"): False,
    # Trafficking ring used FB ad to lure 2 Karnat  ||  Karnataka steps up drive to reduce trans fat
    ("f1c59dc5-3434-4e9f-9bbe-0802fa637a71", "b4a15be4-cbf1-456f-91c6-434ee95e24de"): False,
    # Trafficking ring used FB ad to lure 2 Karnat  ||  Karnataka steps up drive to reduce trans fat
    ("f1c59dc5-3434-4e9f-9bbe-0802fa637a71", "e2f76709-0250-486d-bad4-9c3fd0c3d872"): False,
    # Trafficking ring used FB ad to lure 2 Karnat  ||  Ousted Venezuelan president Maduro to face U
    ("f1c59dc5-3434-4e9f-9bbe-0802fa637a71", "460fb7a4-47dd-4f99-956b-f7b170b03680"): False,
    # Trafficking ring used FB ad to lure 2 Karnat  ||  Karnataka Police Complaints Authority recomm
    ("f1c59dc5-3434-4e9f-9bbe-0802fa637a71", "e87fc43c-ae3c-40f4-889f-d04f75b8c00a"): False,
    # Trafficking ring used FB ad to lure 2 Karnat  ||  Cyberabad Traffic Police to review U-turns, 
    ("f1c59dc5-3434-4e9f-9bbe-0802fa637a71", "64180cec-36ce-43d9-a870-5d1142114481"): False,
    # Trafficking ring used FB ad to lure 2 Karnat  ||  Monsoon Session of Karnataka Legislature to 
    ("b2fff003-ead1-4857-8705-d3b104511e58", "6a9bd224-617d-406c-8488-4750e2509922"): True,
    # World News Today Live Updates on July 22, 20  ||  Saudi oil tankers bound for China and India 
    ("b2fff003-ead1-4857-8705-d3b104511e58", "08222098-bf4a-4827-b470-cdd04ef61b41"): True,
    # World News Today Live Updates on July 22, 20  ||  Tankers carrying Saudi crude for India, Chin
    ("b2fff003-ead1-4857-8705-d3b104511e58", "18b2722e-d9d8-4248-a42f-ae0fe0350620"): False,
    # World News Today Live Updates on July 22, 20  ||  World News Today Live Updates on July 23, 20
    ("b2fff003-ead1-4857-8705-d3b104511e58", "3f73b159-e92d-48a3-b69f-11349de1cd3c"): True,
    # World News Today Live Updates on July 22, 20  ||  Live: Houthis Attack Saudi Tankers In Red Se
    ("b2fff003-ead1-4857-8705-d3b104511e58", "4ed8c10a-6e6c-45ad-8309-38fc330bb7a7"): False,
    # World News Today Live Updates on July 22, 20  ||  Heavy rain likely in Delhi for next two days
    ("b2fff003-ead1-4857-8705-d3b104511e58", "13c42e2d-d4ec-467d-ade3-290b8cf600fe"): False,
    # World News Today Live Updates on July 22, 20  ||  Brent Tops $95 After Houthis Attack On Saudi
    ("b2fff003-ead1-4857-8705-d3b104511e58", "33177aca-a180-498b-bf29-9166cd245078"): False,
    # World News Today Live Updates on July 22, 20  ||  China "Ready" To Handle Sensitive Issues Wit
    ("b2fff003-ead1-4857-8705-d3b104511e58", "ce998b1e-56b3-40bd-b083-93f3fa3908ee"): False,
    # World News Today Live Updates on July 22, 20  ||  Another oil shock loading for India? How Red
    ("14852602-ecba-4645-b609-c48634c1c2bf", "d15d5b21-9b24-44c8-b42c-7519a4840c6c"): True,
    # APSRTC Outsourced Employees’ Union demands e  ||  APSRTC Outsourced Employees’ Union demands e
    ("14852602-ecba-4645-b609-c48634c1c2bf", "8ded700c-a0f5-4481-8d35-f5d0626ad009"): False,
    # APSRTC Outsourced Employees’ Union demands e  ||  Govt to ensure social security for gig worke
    ("9211fd06-f976-42c6-bf71-6f2cc31118bc", "c0213101-7b71-431a-aebe-72a36cc5bf2f"): False,
    # Bombay high court grants interim relief to d  ||  Bombay High Court refuses interim relief to 
    ("9211fd06-f976-42c6-bf71-6f2cc31118bc", "3a99a966-8444-4fef-a1a9-ef974bd324ae"): False,
    # Bombay high court grants interim relief to d  ||  After Bombay high court's FDA grilling, lawy
    ("9211fd06-f976-42c6-bf71-6f2cc31118bc", "e31a530e-6976-4cc2-a154-413c270e7e44"): False,
    # Bombay high court grants interim relief to d  ||  Delhi High Court grants Sonia, Rahul three w
    ("9211fd06-f976-42c6-bf71-6f2cc31118bc", "afcbec3e-d33f-4bc8-b4ab-4d7f54ef957d"): False,
    # Bombay high court grants interim relief to d  ||  Anti-defection law: Supreme Court ready to h
    ("9211fd06-f976-42c6-bf71-6f2cc31118bc", "1dadac54-a6d1-43fd-b8c3-f58ba86022c9"): False,
    # Bombay high court grants interim relief to d  ||  Bombay high court issues notice to NTA on st
    ("9211fd06-f976-42c6-bf71-6f2cc31118bc", "bed7b2b6-9ba2-4e09-9477-371b8428ddf9"): False,
    # Bombay high court grants interim relief to d  ||  'No role in E20 programme': What Nitin Gadka
    ("9211fd06-f976-42c6-bf71-6f2cc31118bc", "dec6df0a-187d-4065-885f-ee48e48bcc63"): False,
    # Bombay high court grants interim relief to d  ||  'No role in E20 fuel': What Nitin Gadkari cl
    ("9211fd06-f976-42c6-bf71-6f2cc31118bc", "2dc36766-882a-492f-bf88-3ff9525b76f0"): False,
    # Bombay high court grants interim relief to d  ||  Chhattisgarh HC grants relief to Bhupesh Bag
    ("cf09663f-1591-4716-ae3b-32d05304a0bb", "70dc240d-8113-4aa5-8cfc-83320bdd8c76"): False,
    # Bankipur assembly byelection sees low voter   ||  JD(S) alleges large-scale duplication of vot
    ("cf09663f-1591-4716-ae3b-32d05304a0bb", "e4e2611a-4f0b-4922-97a1-6a61914fe334"): False,
    # Bankipur assembly byelection sees low voter   ||  JD(S) alleges large-scale duplication of vot
    ("cf09663f-1591-4716-ae3b-32d05304a0bb", "a9cb8950-cc52-4cf7-aa10-228473204546"): False,
    # Bankipur assembly byelection sees low voter   ||  Ahead of Bankipur Assembly bypoll, Nitin Nab
    ("cf09663f-1591-4716-ae3b-32d05304a0bb", "91014993-b6c1-4a91-b505-2122215c925c"): False,
    # Bankipur assembly byelection sees low voter   ||  EVMs used in Kolathur constituency being ver
    ("cf09663f-1591-4716-ae3b-32d05304a0bb", "5dc06012-0bf0-46c7-bf17-9ca894d370f3"): False,
    # Bankipur assembly byelection sees low voter   ||  PM Modi cancelled Bihar tour realising BJP w
    ("cf09663f-1591-4716-ae3b-32d05304a0bb", "52b3210b-1990-4a08-84d3-a87635798cc2"): False,
    # Bankipur assembly byelection sees low voter   ||  Over 25% SIR enumeration forms not returned 
    ("cf09663f-1591-4716-ae3b-32d05304a0bb", "fb55f426-9be2-4dcd-b62f-302b7adefff5"): False,
    # Bankipur assembly byelection sees low voter   ||  Over 25% SIR enumeration forms not returned 
    ("cf09663f-1591-4716-ae3b-32d05304a0bb", "1b95fb1b-4791-4b65-bb44-fb8f2f77cfa0"): False,
    # Bankipur assembly byelection sees low voter   ||  High drama at Bihar police station as Prasha
    ("d89787c6-31bb-4e9f-934b-1d49a4e722d6", "b1097315-0bc8-4450-96f0-5b4b36ff2d1b"): True,
    # Madhira hi-tech kitchen to serve 44,107 stud  ||  Madhira hi-tech kitchen to serve 44,107 stud
    ("d89787c6-31bb-4e9f-934b-1d49a4e722d6", "8f390c04-a44e-41e3-b720-7d63f6e1f3f8"): False,
    # Madhira hi-tech kitchen to serve 44,107 stud  ||  Telangana school breakfast scheme to cover 2
    ("d89787c6-31bb-4e9f-934b-1d49a4e722d6", "f2fc4475-4dcb-496d-a29f-823908f14015"): False,
    # Madhira hi-tech kitchen to serve 44,107 stud  ||  Telangana school breakfast scheme to cover 2
    ("d89787c6-31bb-4e9f-934b-1d49a4e722d6", "135d47ca-11c3-42a6-848c-084162417c48"): False,
    # Madhira hi-tech kitchen to serve 44,107 stud  ||  Solar plant set up to help SCCL subsidiary A
    ("d89787c6-31bb-4e9f-934b-1d49a4e722d6", "511990b3-e0ad-4895-a53a-5a594dfa9ee4"): False,
    # Madhira hi-tech kitchen to serve 44,107 stud  ||  State fulfils promise, releases ₹6,000 crore
    ("10ba0476-7b56-4287-a00e-6b046b8e1885", "454aa415-8cf0-4dd6-80f6-5d4dd37e24b3"): True,
    # Nara Lokesh distributes land titles to 3,000  ||  Lokesh to distribute 3,000 house site title 
    ("10ba0476-7b56-4287-a00e-6b046b8e1885", "2629eb5e-dbe5-4a0a-bd52-6738c9555d00"): False,
    # Nara Lokesh distributes land titles to 3,000  ||  Row as K’taka to distribute free residency c
    ("10ba0476-7b56-4287-a00e-6b046b8e1885", "0fff9f06-56ce-4c38-adf4-26d7543c1549"): False,
    # Nara Lokesh distributes land titles to 3,000  ||  CJP responds to PM Modi's message, reiterate
    ("10ba0476-7b56-4287-a00e-6b046b8e1885", "560b0b14-eee1-4de0-a36d-a48eb36f5da0"): False,
    # Nara Lokesh distributes land titles to 3,000  ||  Jantar Mantar protest LIVE: Dharmendra Pradh
    ("10ba0476-7b56-4287-a00e-6b046b8e1885", "e3187eeb-363f-4731-92ef-688a702c4b57"): False,
    # Nara Lokesh distributes land titles to 3,000  ||  'Why should PM resign? He is the most popula
    ("10ba0476-7b56-4287-a00e-6b046b8e1885", "e71cb58b-4999-4c57-88ba-8add3d189342"): False,
    # Nara Lokesh distributes land titles to 3,000  ||  Congress, CJP protests LIVE: ‘Owe our studen
    ("10ba0476-7b56-4287-a00e-6b046b8e1885", "39fb2142-f038-40e0-ad1b-8a944340a6b2"): False,
    # Nara Lokesh distributes land titles to 3,000  ||  Telangana gets boost as Centre agrees to pro
    ("10ba0476-7b56-4287-a00e-6b046b8e1885", "d8f784a5-eb41-43dd-8ece-461160ab7fe1"): False,
    # Nara Lokesh distributes land titles to 3,000  ||  Rahul, Priyanka, Akhilesh detained during pr
    ("e18c7603-44af-4316-a86d-968c80003320", "70e0ff6f-b514-4ba9-ace8-f172399ddc8b"): False,
    # BMC’s Rs 1.5crore Innova plan sparks storm i  ||  ‘Garlanding him as if he won war with Pakist
    ("e18c7603-44af-4316-a86d-968c80003320", "81d15049-1c78-4a94-8ac8-f81a77dc81f4"): False,
    # BMC’s Rs 1.5crore Innova plan sparks storm i  ||  Ramchander Rao accuses Congress of ‘sacrific
    ("e18c7603-44af-4316-a86d-968c80003320", "34b77fbb-a445-4b10-8fa5-e74c3b6bc43d"): False,
    # BMC’s Rs 1.5crore Innova plan sparks storm i  ||  RSS distances itself from Hindutva ideologue
    ("e18c7603-44af-4316-a86d-968c80003320", "48af3025-6c7f-4ccc-aca8-6fa89fac3484"): False,
    # BMC’s Rs 1.5crore Innova plan sparks storm i  ||  RSS distances itself from Hindutva ideologue
    ("e18c7603-44af-4316-a86d-968c80003320", "579c4d5e-24dc-497a-81c2-71d2d2f7d712"): False,
    # BMC’s Rs 1.5crore Innova plan sparks storm i  ||  BJP committed to inclusive development of mi
    ("e18c7603-44af-4316-a86d-968c80003320", "93e5e031-ebae-4813-b2fe-2a3d5e5a9a7f"): False,
    # BMC’s Rs 1.5crore Innova plan sparks storm i  ||  BJP committed to inclusive development of mi
    ("e18c7603-44af-4316-a86d-968c80003320", "07fab02c-d87b-444d-9945-4ee212e85440"): False,
    # BMC’s Rs 1.5crore Innova plan sparks storm i  ||  Kharge’s ‘will drag you out’ remark at Shah 
    ("e18c7603-44af-4316-a86d-968c80003320", "04b599d3-c305-4987-a604-0be21c60a022"): False,
    # BMC’s Rs 1.5crore Innova plan sparks storm i  ||  Hindutva ideologue T.G. Mohandas sparks row 
    ("a853de44-1692-4e3e-bc17-86d93734c020", "bac52c71-a942-4dff-b1ce-45152621f877"): False,
    # आज DK-सिद्धा की बैठक, गुरुवार को शपथ... कर्न  ||  नीट के बाद अब गुजरात में BAMS पेपर लीक?: AAP
    ("a853de44-1692-4e3e-bc17-86d93734c020", "8f9c0032-a70d-4478-a361-5c32ca6c892e"): False,
    # आज DK-सिद्धा की बैठक, गुरुवार को शपथ... कर्न  ||  लोकसभा में एंटी पेपर लीक बिल से पहले पीएम मो
    ("a853de44-1692-4e3e-bc17-86d93734c020", "ceeb7586-60b7-429a-a782-444e82f76cc1"): False,
    # आज DK-सिद्धा की बैठक, गुरुवार को शपथ... कर्न  ||  'यह सम्मान नहीं, बर्बादी का जश्न': संसद में 
    ("a853de44-1692-4e3e-bc17-86d93734c020", "7024df64-4805-4e3e-ba61-b54676d39989"): False,
    # आज DK-सिद्धा की बैठक, गुरुवार को शपथ... कर्न  ||  रजत पाटीदार ने नशे के खिलाफ युवाओं को दिया ब
    ("a853de44-1692-4e3e-bc17-86d93734c020", "b323e79c-3a34-43d6-8ad6-f7c9a8610372"): False,
    # आज DK-सिद्धा की बैठक, गुरुवार को शपथ... कर्न  ||  सौरभ दास ने दी प्रदर्शनकारियों पर बड़ी राहत 
    ("a853de44-1692-4e3e-bc17-86d93734c020", "0ff492e0-5695-44b0-9470-55703bafd904"): False,
    # आज DK-सिद्धा की बैठक, गुरुवार को शपथ... कर्न  ||  शायरी वाले हमले से मोदी सरकार की ढाल तक... 4
    ("a853de44-1692-4e3e-bc17-86d93734c020", "3fce9ddf-7475-4fc8-bf7d-41ff0eb31710"): False,
    # आज DK-सिद्धा की बैठक, गुरुवार को शपथ... कर्न  ||  असम में बाढ़ का कहर: PM मोदी ने सांसदों के स
    ("a853de44-1692-4e3e-bc17-86d93734c020", "203ac61a-cb95-4855-bea8-e08067b7793e"): False,
    # आज DK-सिद्धा की बैठक, गुरुवार को शपथ... कर्न  ||  पेपर लीक बिल पर घेराबंदी की तैयारी में विपक्
    ("b30a42a8-1b35-4997-aa3c-4e2de1897f53", "c2b1125a-4d16-4dc4-99c8-6f8292142736"): False,
    # MBBS Admissions 2026: Disability Certificate  ||  Maharashtra govt to minority schools: Don’t 
    ("b30a42a8-1b35-4997-aa3c-4e2de1897f53", "b3132b35-f5db-4a14-aca8-69f2532616c9"): False,
    # MBBS Admissions 2026: Disability Certificate  ||  IIM Ahmedabad PhD Admission Explained: Eligi
    ("ad948607-aa2e-4afd-9cbc-60fc0f8e7194", "030c3fe6-9210-4902-bcb7-930cc228b087"): True,
    # Supreme Court orders all states to release p  ||  Supreme Court orders release of protesters b
    ("ad948607-aa2e-4afd-9cbc-60fc0f8e7194", "855de2b4-5a1c-4608-8f23-47f3fc184408"): True,
    # Supreme Court orders all states to release p  ||  NEET protests: SC bars coercive action again
    ("ad948607-aa2e-4afd-9cbc-60fc0f8e7194", "bec8a18e-9f6a-450f-8067-00cb553c0985"): False,
    # Supreme Court orders all states to release p  ||  Using Facial Scans, Cops Find 2,873 With Cri
    ("ad948607-aa2e-4afd-9cbc-60fc0f8e7194", "1999d0ae-fd34-4f27-9006-6a4841ea85e7"): True,
    # Supreme Court orders all states to release p  ||  Supreme Court moots independent probe into p
    ("ad948607-aa2e-4afd-9cbc-60fc0f8e7194", "df91dbb1-3630-4ccc-9767-35cca29028e4"): False,
    # Supreme Court orders all states to release p  ||  Delhi govt closes NEET protest cases with ca
    ("ad948607-aa2e-4afd-9cbc-60fc0f8e7194", "5fe15293-1a53-4b65-a8fa-beccd629c486"): False,
    # Supreme Court orders all states to release p  ||  Bihar govt relents, to withdraw youth protes
    ("ad948607-aa2e-4afd-9cbc-60fc0f8e7194", "ec25592d-7dc5-4be2-aa9a-6cf5c017562e"): False,
    # Supreme Court orders all states to release p  ||  Pellet guns allowed 'in exceptional cases', 
    ("ad948607-aa2e-4afd-9cbc-60fc0f8e7194", "3383670d-156d-4dbe-8fa7-ac45fc6aca05"): False,
    # Supreme Court orders all states to release p  ||  Fadnavis orders withdrawal of cases against 
    ("cef4714c-b28d-433d-86ec-568ab8ec24ca", "cd4a6c5b-7805-4ade-b7f2-01de691095cf"): True,
    # Arista patches VeloCloud Orchestrator zero-d  ||  Attackers Exploit Arista VeloCloud Orchestra
    ("cef4714c-b28d-433d-86ec-568ab8ec24ca", "e4815ac8-60e6-47d4-93fb-108d2b86c887"): False,
    # Arista patches VeloCloud Orchestrator zero-d  ||  Hackers target US firms in FastJson RCE zero
    ("cef4714c-b28d-433d-86ec-568ab8ec24ca", "b73e1846-220e-42ba-bf41-4046e4fdbfaf"): False,
    # Arista patches VeloCloud Orchestrator zero-d  ||  Cisco FMC Zero-Day Actively Exploited, Stati
    ("cef4714c-b28d-433d-86ec-568ab8ec24ca", "f6505e0e-6537-4d1b-96f4-22ea8eeec5e9"): False,
    # Arista patches VeloCloud Orchestrator zero-d  ||  JFrog Confirms OpenAI Models Exploited Artif
    ("cef4714c-b28d-433d-86ec-568ab8ec24ca", "67487828-044f-485c-8f6f-454d1b89193f"): False,
    # Arista patches VeloCloud Orchestrator zero-d  ||  Clop ransomware targets Windchill, FlexPLM i
    ("cef4714c-b28d-433d-86ec-568ab8ec24ca", "468d83db-1d38-4265-926f-874dd05eb6de"): False,
    # Arista patches VeloCloud Orchestrator zero-d  ||  Coordinated Cyberattack Targets 30+ Minnesot
    ("e5533784-9dca-48bd-9165-d131b4969494", "1b0408ec-ad9d-4339-a3a3-899df1d15fbf"): True,
    # Teachers on census duty finding it tough to   ||  Teachers on census duty finding it tough to 
    ("e5533784-9dca-48bd-9165-d131b4969494", "6b78b2bd-28cf-447b-87dc-c1eb70827541"): False,
    # Teachers on census duty finding it tough to   ||  Unscientific allotment of Plus One batches i
    ("e5533784-9dca-48bd-9165-d131b4969494", "f1398613-bbbf-4259-b8e7-ea643d9bfd7d"): False,
    # Teachers on census duty finding it tough to   ||  Unscientific allotment of Plus One batches i
    ("cde27376-299d-47bb-a2a2-fc1098c0dc0d", "34f45a5b-ff0c-40c3-baf9-1362224133ed"): True,
    # Livingstone's all-round efforts in vain as S  ||  Super Giants dwarf Spirit in Lord's opener
    ("cde27376-299d-47bb-a2a2-fc1098c0dc0d", "c7c73d26-3f9d-4ff3-8298-465cf8c83099"): False,
    # Livingstone's all-round efforts in vain as S  ||  De Klerk, Kelly seal London Spirit's first w
    ("cde27376-299d-47bb-a2a2-fc1098c0dc0d", "4c2dc4e6-dc8d-467a-a9b6-fcdeab4e1b0b"): False,
    # Livingstone's all-round efforts in vain as S  ||  ದಿ ಹಂಡ್ರೆಡ್​ನಲ್ಲಿ ಸಹೋದರರ ಸವಾಲ್: ಕೊನೆಗೂ ಗೆದ್ದ
    ("032666a5-10ff-46b7-9689-94386f11f53d", "c68fad55-ba47-4368-9531-88d4165c977e"): False,
    # No decision yet on ethanol blending beyond E  ||  Parliament washout again; govt reaches out t
    ("032666a5-10ff-46b7-9689-94386f11f53d", "8046a304-06b1-4150-8d35-c8bff94b0618"): False,
    # No decision yet on ethanol blending beyond E  ||  Govt ready for Parliament discussion on pape
    ("032666a5-10ff-46b7-9689-94386f11f53d", "799891df-f461-45fb-a554-827ac7e6f0cf"): False,
    # No decision yet on ethanol blending beyond E  ||  Left MPs visit Jantar Mantar, demand Amit Sh
    ("032666a5-10ff-46b7-9689-94386f11f53d", "920200fa-fef0-4204-8dfc-fd28d891c09e"): False,
    # No decision yet on ethanol blending beyond E  ||  Chaos on Parliament streets amid CJP protest
    ("032666a5-10ff-46b7-9689-94386f11f53d", "cceba8cb-8c55-44ac-b508-dbcfd6da4581"): False,
    # No decision yet on ethanol blending beyond E  ||  Parliament breach: Delhi court grants interi
    ("032666a5-10ff-46b7-9689-94386f11f53d", "5670e8bd-8485-4fb7-9aef-0030f0d5760e"): False,
    # No decision yet on ethanol blending beyond E  ||  NEET paper leak: Lakhs march to Parliament, 
    ("032666a5-10ff-46b7-9689-94386f11f53d", "b3bf3574-b537-4d5f-84c9-8142680d733c"): False,
    # No decision yet on ethanol blending beyond E  ||  'This is gunda gardi': Uttarakhand HC tears 
    ("032666a5-10ff-46b7-9689-94386f11f53d", "b9b24c65-bcae-48f1-b489-b6dc4b6936b9"): False,
    # No decision yet on ethanol blending beyond E  ||  E20 petrol may reduce mileage by up to 5% in
    ("12e2e2c7-d5ac-4646-a5d5-98c0e58ec670", "fda01c67-8a29-41e2-96e7-9262db751bc6"): True,
    # Oil Prices On July 28: Brent Falls Below $88  ||  Oil prices fall to one-week low as hopes of 
    ("12e2e2c7-d5ac-4646-a5d5-98c0e58ec670", "522d9081-bf76-499d-9842-36ad2d86c95e"): False,
    # Oil Prices On July 28: Brent Falls Below $88  ||  Trump Signals Possible Iran Deal, Warns US C
    ("12e2e2c7-d5ac-4646-a5d5-98c0e58ec670", "37b41c1d-09a9-44ce-bb39-9e310d69f52d"): False,
    # Oil Prices On July 28: Brent Falls Below $88  ||  Trump Says "Good Chance" Of Progress In Iran
    ("12e2e2c7-d5ac-4646-a5d5-98c0e58ec670", "1d535915-1e7a-4158-a146-3652c1fa2e9c"): False,
    # Oil Prices On July 28: Brent Falls Below $88  ||  'Oil Dropped, Stocks Rose': Trump Defends Ir
    ("12e2e2c7-d5ac-4646-a5d5-98c0e58ec670", "fcffac11-44da-43fa-85c1-e15073997c39"): False,
    # Oil Prices On July 28: Brent Falls Below $88  ||  Live: Markets Likely To Open Higher As Oil D
    ("12e2e2c7-d5ac-4646-a5d5-98c0e58ec670", "b6c74d1c-7606-441b-8936-0a046718adfc"): False,
    # Oil Prices On July 28: Brent Falls Below $88  ||  Iran's shadow oil billions vanish as trustie
    ("12e2e2c7-d5ac-4646-a5d5-98c0e58ec670", "a6ff30b8-b7ac-4bda-88f8-6a4342672886"): False,
    # Oil Prices On July 28: Brent Falls Below $88  ||  US-Iran war LIVE: Israeli PM Netanyahu arriv
    ("12e2e2c7-d5ac-4646-a5d5-98c0e58ec670", "d2c841d7-efbf-4f5f-8ef3-b430349e873d"): False,
    # Oil Prices On July 28: Brent Falls Below $88  ||  US, Iran pause attacks for second day as cea
    ("36b10690-998c-4889-9ec8-72cb4282dd41", "a7887dd4-4d07-41f6-8186-c90047d6f0fd"): False,
    # Official assaulted during electoral roll rev  ||  Bengaluru: Student part of Freedom Park prot
    ("36b10690-998c-4889-9ec8-72cb4282dd41", "aae71cc2-7447-44dd-971d-92527f6f9154"): False,
    # Official assaulted during electoral roll rev  ||  NEET protest at Bengaluru’s Freedom Park spa
    ("36b10690-998c-4889-9ec8-72cb4282dd41", "239613bf-73b2-473b-8c2d-402eb92e50d2"): False,
    # Official assaulted during electoral roll rev  ||  Special Intensive Revision: AI used to detec
    ("36b10690-998c-4889-9ec8-72cb4282dd41", "4c4f633d-54cf-4ec7-b884-bdcf26d0ea5c"): False,
    # Official assaulted during electoral roll rev  ||  FIR against four persons for dumping garbage
    ("36b10690-998c-4889-9ec8-72cb4282dd41", "0a8b0974-ef21-45fb-9cd3-d006e74c2886"): False,
    # Official assaulted during electoral roll rev  ||  Karnataka High Court questions conduct of Ma
    ("36b10690-998c-4889-9ec8-72cb4282dd41", "72ef9eaf-1d67-4873-81b1-0aaa538bf3be"): False,
    # Official assaulted during electoral roll rev  ||  KGMOA, IMA condemn attempted assault on doct
    ("36b10690-998c-4889-9ec8-72cb4282dd41", "fd37e6c8-109d-4c40-bded-a2f42591480a"): False,
    # Official assaulted during electoral roll rev  ||  Bengaluru East Corporation reviews infra pro
    ("36b10690-998c-4889-9ec8-72cb4282dd41", "568097d2-0fdb-44d5-ad2b-c1a13ad30137"): False,
    # Official assaulted during electoral roll rev  ||  Belagavi: Officers told to include members o
    ("01124df6-5de8-4256-bd5b-8e4098b27b6b", "968e33b5-e068-46bb-b838-f168560eacae"): False,
    # Exam systems must be tech-driven; digital ID  ||  ‘Gaumutra expert’ vs ‘top tech brain’: Open 
    ("01124df6-5de8-4256-bd5b-8e4098b27b6b", "9de03d47-119a-46fd-96ac-77d92ba65739"): True,
    # Exam systems must be tech-driven; digital ID  ||  Rebuilding trust the real challenge, says II
    ("01124df6-5de8-4256-bd5b-8e4098b27b6b", "28619d16-0afe-43fb-9bf5-c7f3f3319987"): True,
    # Exam systems must be tech-driven; digital ID  ||  Human Integrity, Not Tech, Is Main Issue: II
    ("01124df6-5de8-4256-bd5b-8e4098b27b6b", "1227e0db-ebbe-44bb-b457-5b1c34fb4ed9"): True,
    # Exam systems must be tech-driven; digital ID  ||  Trust biggest challenge in preventing paper 
    ("01124df6-5de8-4256-bd5b-8e4098b27b6b", "0762373f-e758-4659-a67d-97031e08696a"): False,
    # Exam systems must be tech-driven; digital ID  ||  Academics slam Priyanka Gandhi’s ‘gaumutra e
    ("01124df6-5de8-4256-bd5b-8e4098b27b6b", "3d827614-2ddc-4990-ad1b-ec64c36e1055"): False,
    # Exam systems must be tech-driven; digital ID  ||  Who's on PM Modi's task force for exam refor
    ("01124df6-5de8-4256-bd5b-8e4098b27b6b", "d1611c01-5c1f-4222-a23b-f3b71541a0f9"): False,
    # Exam systems must be tech-driven; digital ID  ||  'Eye on the future': PM Modi announces task 
    ("01124df6-5de8-4256-bd5b-8e4098b27b6b", "05a2b000-b06e-41e1-83c7-7f376c3dd09c"): False,
    # Exam systems must be tech-driven; digital ID  ||  CPI slams BJP for felicitating Dharmendra Pr
    ("76eb81ba-1452-4894-94e6-8eb400208bc3", "8b691fa2-1e9a-4c6b-a31c-7190fa270d26"): True,
    # Mekedatu dam: Annamalai raises doubts over C  ||  Mekedatu dam: Annamalai raises doubts over C
    ("76eb81ba-1452-4894-94e6-8eb400208bc3", "fda6655e-0892-480c-8b69-7aff263855e7"): False,
    # Mekedatu dam: Annamalai raises doubts over C  ||  Stalin’s remarks over CM Vijay’s ‘inaction’ 
    ("76eb81ba-1452-4894-94e6-8eb400208bc3", "9c213627-d5b8-46ef-8666-5804a869914a"): False,
    # Mekedatu dam: Annamalai raises doubts over C  ||  Mekedatu: Centre cites SC order to say Karna
    ("76eb81ba-1452-4894-94e6-8eb400208bc3", "9df8ad98-afe8-480c-8f7a-e7fbfdc722c4"): False,
    # Mekedatu dam: Annamalai raises doubts over C  ||  Mekedatu: Centre cites SC order to say Karna
    ("76eb81ba-1452-4894-94e6-8eb400208bc3", "898db7c9-846d-4727-aac3-449ee45a42d7"): False,
    # Mekedatu dam: Annamalai raises doubts over C  ||  DMK to stage protest in Thanjavur on August 
    ("76eb81ba-1452-4894-94e6-8eb400208bc3", "81025a65-d8cf-4987-ad17-f11e784d95b3"): False,
    # Mekedatu dam: Annamalai raises doubts over C  ||  A gamble on the Cauvery issue
    ("76eb81ba-1452-4894-94e6-8eb400208bc3", "fca05e1c-544a-4752-a58e-5e1467c621e4"): False,
    # Mekedatu dam: Annamalai raises doubts over C  ||  A gamble on the Cauvery issue
    ("76eb81ba-1452-4894-94e6-8eb400208bc3", "ee56a44f-f0a6-4793-8974-e7cd178bff9c"): False,
    # Mekedatu dam: Annamalai raises doubts over C  ||  Silence looms over Hyderabad Metro Rail Phas
    ("9029bde7-2fbe-4d62-8be0-19b099ea1f08", "9656cc16-5d28-41c1-b99a-13ed2e53b398"): True,
    # CJP की चेतावनी: छात्रों को छेड़ा तो फिर होगा  ||  NEET पेपर लीक मामले में CJP की सरकार को बड़ी
    ("9029bde7-2fbe-4d62-8be0-19b099ea1f08", "6c7123c1-7fbe-4782-9814-44295d39e185"): False,
    # CJP की चेतावनी: छात्रों को छेड़ा तो फिर होगा  ||  पटना छात्र आंदोलन पर बड़ा एक्शन! सैकड़ों गिर
    ("9029bde7-2fbe-4d62-8be0-19b099ea1f08", "de8d41fb-bd4e-4bb3-8edf-8ccb8478ebbd"): False,
    # CJP की चेतावनी: छात्रों को छेड़ा तो फिर होगा  ||  Bihar में छात्र आंदोलन हिंसा के बाद पुलिस का
    ("9029bde7-2fbe-4d62-8be0-19b099ea1f08", "9389b9ba-6dcf-47c6-a6dd-dc64c55b5c71"): True,
    # CJP की चेतावनी: छात्रों को छेड़ा तो फिर होगा  ||  'गारंटी पूरी नहीं की तो फिर सड़क पर उतरेंगे'
    ("9029bde7-2fbe-4d62-8be0-19b099ea1f08", "23dc3edb-d184-4704-8a17-85fb7fb003fe"): False,
    # CJP की चेतावनी: छात्रों को छेड़ा तो फिर होगा  ||  '100% प्योर पेट्रोल चाहिए...', E20 पर बढ़ा ब
    ("9029bde7-2fbe-4d62-8be0-19b099ea1f08", "ea027682-443b-419f-858c-8432af14c77c"): False,
    # CJP की चेतावनी: छात्रों को छेड़ा तो फिर होगा  ||  'मैंने सेवा की': 35 दिन जंतर-मंतर पर छात्रों
    ("9029bde7-2fbe-4d62-8be0-19b099ea1f08", "26c7f645-982b-4907-b274-04e75ab10db0"): False,
    # CJP की चेतावनी: छात्रों को छेड़ा तो फिर होगा  ||  'भारत को नेपाल बनाओगे?', CJP प्रदर्शनकारियों
    ("9029bde7-2fbe-4d62-8be0-19b099ea1f08", "3ebd1e6d-917c-4f3b-aa1d-578c993a51e1"): False,
    # CJP की चेतावनी: छात्रों को छेड़ा तो फिर होगा  ||  E20 और आरक्षण... दो नए ‘आंदोलन’ मोदी सरकार क
    ("3a560150-e19c-4ab1-b6f3-6f527829fbc1", "39a2fff7-5c9b-41e5-911c-842a1af34012"): True,
    # Duckett fires for Rockets as Welsh Fire fizz  ||  Craig wins the Overton battle to seal Rocket
    ("3a560150-e19c-4ab1-b6f3-6f527829fbc1", "f19d4c7d-640c-4d75-a9ad-3f44bda6385c"): False,
    # Duckett fires for Rockets as Welsh Fire fizz  ||  Mooney, Sciver-Brunt lead Welsh Fire thrashi
    ("3a560150-e19c-4ab1-b6f3-6f527829fbc1", "0bbbaa82-5d93-4a84-a84e-070702c8bf9f"): False,
    # Duckett fires for Rockets as Welsh Fire fizz  ||  Ravindra, Ferguson inspire Welsh Fire with K
    ("eeb3a486-7e65-4254-899e-91d1fbc30352", "7c0531e8-3d81-499c-8d73-e2eb5b7a93d6"): False,
    # NYC Mayor Mamdani hires 'tech crew': Here's   ||  Why New York's Zohran Mamdani Cannot Arrest 
    ("eeb3a486-7e65-4254-899e-91d1fbc30352", "f17c9fce-db6e-4226-85cd-77a318b3389b"): False,
    # NYC Mayor Mamdani hires 'tech crew': Here's   ||  Benjamin Netanyahu to be arrested in NYC? Zo
    ("eeb3a486-7e65-4254-899e-91d1fbc30352", "7f440a3c-627b-4a39-8c97-12e29faa4f28"): False,
    # NYC Mayor Mamdani hires 'tech crew': Here's   ||  0%, 100%, then 200%: How Trump's new generic
    ("eeb3a486-7e65-4254-899e-91d1fbc30352", "a452aabc-a5b0-45e5-815a-5b76f66b6a9c"): False,
    # NYC Mayor Mamdani hires 'tech crew': Here's   ||  Lalit Modi says his home will remain London 
    ("eeb3a486-7e65-4254-899e-91d1fbc30352", "f243e820-15fc-49e9-97bb-b61e3c75cab9"): False,
    # NYC Mayor Mamdani hires 'tech crew': Here's   ||  'Will book you in drug case': Mumbai cop thr
    ("eeb3a486-7e65-4254-899e-91d1fbc30352", "57c1fe56-8545-4a93-963b-dc2d2018183c"): False,
    # NYC Mayor Mamdani hires 'tech crew': Here's   ||  Wife can't claim maintenance solely because 
    ("eeb3a486-7e65-4254-899e-91d1fbc30352", "9a116a4b-b7e9-4f82-a444-96ea84d9f699"): False,
    # NYC Mayor Mamdani hires 'tech crew': Here's   ||  Centre uses 40% of annual fertiliser subsidy
    ("eeb3a486-7e65-4254-899e-91d1fbc30352", "9dc9c1de-792d-41d5-910e-eb5b4e341713"): False,
    # NYC Mayor Mamdani hires 'tech crew': Here's   ||  R&amp;B engineer who took up US job 20 years
    ("3c5d2503-26fe-47d9-a22e-a572a1e788dd", "5bd32407-4f60-4b5d-ab85-fa76a0fe9265"): True,
    # Leopard that attacked poultry captured in Fo  ||  Leopard that attacked poultry captured in Fo
    ("3c5d2503-26fe-47d9-a22e-a572a1e788dd", "36d17456-2fca-4e41-a6de-7412fd83d133"): True,
    # Leopard that attacked poultry captured in Fo  ||  Leopard trapped in cage set up by Forest dep
    ("3c5d2503-26fe-47d9-a22e-a572a1e788dd", "558fb8e0-a839-4088-97bf-faf83d735f59"): True,
    # Leopard that attacked poultry captured in Fo  ||  Leopard trapped in cage set up by Forest dep
    ("3c5d2503-26fe-47d9-a22e-a572a1e788dd", "88e02a19-b05f-4638-aa04-5649fa07af06"): False,
    # Leopard that attacked poultry captured in Fo  ||  Tanker lorry operators stage flash strike at
    ("3c5d2503-26fe-47d9-a22e-a572a1e788dd", "25d801af-cc98-466b-966d-9a7d7b031381"): False,
    # Leopard that attacked poultry captured in Fo  ||  Forest dept. begins process to tranquilise a
    ("3c5d2503-26fe-47d9-a22e-a572a1e788dd", "bdbf2b6d-48f8-4f0d-a19e-3420fb8d3896"): False,
    # Leopard that attacked poultry captured in Fo  ||  Forest dept. begins process to tranquilise a
    ("3c5d2503-26fe-47d9-a22e-a572a1e788dd", "2584ea06-2656-4e24-a9b6-b1aa49f80b9d"): False,
    # Leopard that attacked poultry captured in Fo  ||  Forest watcher Murukesan  at Parambikulam Ti
    ("3c5d2503-26fe-47d9-a22e-a572a1e788dd", "9d233223-9f46-4b61-9fb2-b294303ab0d6"): False,
    # Leopard that attacked poultry captured in Fo  ||  Forest watcher Murukesan  at Parambikulam Ti
    ("783d1baa-69f4-4e02-878f-5ef866305480", "deffcbde-f98d-48d7-b845-4ab8c101b2ac"): False,
    # Tenders invited for expansion of internation  ||  Andhra Pradesh govt. invites tenders for imp
    ("783d1baa-69f4-4e02-878f-5ef866305480", "1ce59191-ca56-453a-8e16-05f11e3a958a"): False,
    # Tenders invited for expansion of internation  ||  31 arrested, 97 wanted persons detained in m
    ("783d1baa-69f4-4e02-878f-5ef866305480", "ec4b00ec-7714-4b33-bce4-6f90341a68b2"): False,
    # Tenders invited for expansion of internation  ||  Ministerial aspirants disappointed as Karnat
    ("783d1baa-69f4-4e02-878f-5ef866305480", "0248132a-b142-458c-a9d2-a70fa3b3ff64"): False,
    # Tenders invited for expansion of internation  ||  Hacker Runs Hermes AI Agent Unattended for P
    ("783d1baa-69f4-4e02-878f-5ef866305480", "5e5b2a0b-71e2-442d-8902-870709199976"): False,
    # Tenders invited for expansion of internation  ||  BJP protest march to Kerala Pradesh Congress
    ("783d1baa-69f4-4e02-878f-5ef866305480", "0eedc37f-2342-4f5c-b0b2-f72998d28cea"): False,
    # Tenders invited for expansion of internation  ||  Warangal Airport project gets in-principle n
    ("783d1baa-69f4-4e02-878f-5ef866305480", "9834b462-4c71-43af-8ddb-727e352dfc61"): False,
    # Tenders invited for expansion of internation  ||  No formal bid to shift Parandur airport site
    ("783d1baa-69f4-4e02-878f-5ef866305480", "f65c4e0e-622c-4412-aaf4-e7d4433bc60c"): False,
    # Tenders invited for expansion of internation  ||  Centre weighs easing cross-ownership rules b
    ("d4448fd6-8352-4f23-8f51-3e2d3188a078", "ce1635db-c7be-4b57-b050-0bd305c8b528"): True,
    # Kerala’s power crisis partly due to cancella  ||  Kerala’s power crisis partly due to cancella
    ("d4448fd6-8352-4f23-8f51-3e2d3188a078", "0f9e9572-b8a1-4fa7-9bf8-a20365940f33"): False,
    # Kerala’s power crisis partly due to cancella  ||  Mylatti BESS project to be commissioned in O
    ("d4448fd6-8352-4f23-8f51-3e2d3188a078", "bc834856-b3d2-4965-a65b-76719bb6dcbf"): False,
    # Kerala’s power crisis partly due to cancella  ||  Mylatti BESS project to be commissioned in O
    ("d4448fd6-8352-4f23-8f51-3e2d3188a078", "f1f67a42-6cbf-4f6d-9cb2-f4d9c4980cd9"): False,
    # Kerala’s power crisis partly due to cancella  ||  Rahul Gandhi, Congress MPs detained after ta
    ("d4448fd6-8352-4f23-8f51-3e2d3188a078", "5e5b2a0b-71e2-442d-8902-870709199976"): False,
    # Kerala’s power crisis partly due to cancella  ||  BJP protest march to Kerala Pradesh Congress
    ("d4448fd6-8352-4f23-8f51-3e2d3188a078", "9161e24b-54e7-4c3b-940b-16c646527f0d"): False,
    # Kerala’s power crisis partly due to cancella  ||  Senior CPI(M) leader P K Sreemathi to move p
    ("d4448fd6-8352-4f23-8f51-3e2d3188a078", "ea0e17c8-e278-44b8-947c-919b73e67b67"): False,
    # Kerala’s power crisis partly due to cancella  ||  Court rejects bail for two more CPI(M) activ
    ("d4448fd6-8352-4f23-8f51-3e2d3188a078", "fc24b15c-887f-4f09-99f8-b436b78b602a"): False,
    # Kerala’s power crisis partly due to cancella  ||  Kerala Cabinet nod for framing anti-ragging 
    ("69a2fdda-f2ea-46bd-9f57-e37ab6ca0f52", "a7c906e8-7a85-4bfb-9b6d-694e8584074c"): False,
    # ASEAN’s top diplomats meet in shadow of US-I  ||  Jaishankar to meet Quad counterparts on side
    ("69a2fdda-f2ea-46bd-9f57-e37ab6ca0f52", "2cd476c3-ac54-4b1b-b0d6-92e6e3e81643"): False,
    # ASEAN’s top diplomats meet in shadow of US-I  ||  Trump weighs Iran ceasefire as mediators rac
    ("69a2fdda-f2ea-46bd-9f57-e37ab6ca0f52", "8ba4df4d-d205-4de4-924a-406997c3ba30"): False,
    # ASEAN’s top diplomats meet in shadow of US-I  ||  Iranian official meets mediators in Pakistan
    ("69a2fdda-f2ea-46bd-9f57-e37ab6ca0f52", "5e8d64a1-c71d-44de-882b-f63b28aa7dff"): False,
    # ASEAN’s top diplomats meet in shadow of US-I  ||  Bandar Abbas at US-Iran conflict: Why this c
    ("69a2fdda-f2ea-46bd-9f57-e37ab6ca0f52", "1a25ad6e-5deb-447e-b36f-5e6f98dceca0"): False,
    # ASEAN’s top diplomats meet in shadow of US-I  ||  Centre rebukes DGCA over conflict-of-interes
    ("69a2fdda-f2ea-46bd-9f57-e37ab6ca0f52", "1d25df21-bde4-4b98-925c-dd85bb798d32"): False,
    # ASEAN’s top diplomats meet in shadow of US-I  ||  Kumkis to be deployed to reduce elephant-hum
    ("69a2fdda-f2ea-46bd-9f57-e37ab6ca0f52", "5af0f46e-f6a0-402d-807d-9493a8a0db69"): False,
    # ASEAN’s top diplomats meet in shadow of US-I  ||  US and Iran dig in over the Strait of Hormuz
    ("69a2fdda-f2ea-46bd-9f57-e37ab6ca0f52", "f6a81028-a5bc-4a1a-8534-69f27af48015"): False,
    # ASEAN’s top diplomats meet in shadow of US-I  ||  US Iran war news LIVE: US strikes Iran for 1
    ("2549b7fd-8c57-425c-b1b5-8b332001a21a", "95a9ebec-4372-4986-ac44-4ba0ebe15d30"): False,
    # ಪಶುವೈದ್ಯ ನೇಮಕಾತಿ ಹಗರಣ: ಸಿಬಿಐ ತನಿಖೆಗೆ ಒಪ್ಪಿಸು  ||  ಪಶುವೈದ್ಯ ನೇಮಕಾತಿ ಹಗರಣ:  ಕೆಪಿಎಸ್‌ಸಿ ಕಚೇರಿಗೆ ಆ
    ("2549b7fd-8c57-425c-b1b5-8b332001a21a", "29418936-92c4-4119-9753-caa6aa421136"): False,
    # ಪಶುವೈದ್ಯ ನೇಮಕಾತಿ ಹಗರಣ: ಸಿಬಿಐ ತನಿಖೆಗೆ ಒಪ್ಪಿಸು  ||  ಪಶು ವೈದ್ಯಾಧಿಕಾರಿ ನೇಮಕಾತಿ ಅಕ್ರಮ ತನಿಖೆಗೆ ಎಬಿವಿ
    ("2549b7fd-8c57-425c-b1b5-8b332001a21a", "7f2d24b0-4527-4bf1-8661-a79628f547a7"): False,
    # ಪಶುವೈದ್ಯ ನೇಮಕಾತಿ ಹಗರಣ: ಸಿಬಿಐ ತನಿಖೆಗೆ ಒಪ್ಪಿಸು  ||  ಪಶುವೈದ್ಯರ ನೇಮಕಾತಿಯಲ್ಲಿ ಅಕ್ರಮ ಪ್ರಕರಣ, ತನಿಖೆ C
    ("2549b7fd-8c57-425c-b1b5-8b332001a21a", "35031bfa-d9e5-470b-93dd-490cc965a2ba"): True,
    # ಪಶುವೈದ್ಯ ನೇಮಕಾತಿ ಹಗರಣ: ಸಿಬಿಐ ತನಿಖೆಗೆ ಒಪ್ಪಿಸು  ||  ಕೆಪಿಎಸ್‌ಸಿ: ಸ್ವತಂತ್ರ ತನಿಖೆಗೆ ಬಿಜೆಪಿ ಆಗ್ರಹ
    ("2549b7fd-8c57-425c-b1b5-8b332001a21a", "e9a19f98-7a49-464a-9e0c-fd2df4537873"): False,
    # ಪಶುವೈದ್ಯ ನೇಮಕಾತಿ ಹಗರಣ: ಸಿಬಿಐ ತನಿಖೆಗೆ ಒಪ್ಪಿಸು  ||  ನಾಗಮಂಗಲದಲ್ಲಿ ಕಾರ್ಗಿಲ್ ವಿಜಯೋತ್ಸವ, ಯೋಧರ ತ್ಯಾಗ 
    ("2549b7fd-8c57-425c-b1b5-8b332001a21a", "f6fb5798-90ee-4e0d-b8d6-f89a34f73e12"): False,
    # ಪಶುವೈದ್ಯ ನೇಮಕಾತಿ ಹಗರಣ: ಸಿಬಿಐ ತನಿಖೆಗೆ ಒಪ್ಪಿಸು  ||  ಖಾತೆ ಬದಲಾವಣೆಗೆ CJP ಒಪ್ಪಿಲ್ಲದ್ದಕ್ಕೆ ಪ್ರಧಾನ್ ರ
    ("2549b7fd-8c57-425c-b1b5-8b332001a21a", "6dce4d54-b107-476e-bd28-1eb42a5724c4"): False,
    # ಪಶುವೈದ್ಯ ನೇಮಕಾತಿ ಹಗರಣ: ಸಿಬಿಐ ತನಿಖೆಗೆ ಒಪ್ಪಿಸು  ||  ‘ಕಾವೇರಿ’ ಮುಂದಿನ ನಡೆ ಚರ್ಚೆಗೆ ಭಾನುವಾರ ಸರ್ವಪಕ್ಷ
    ("2549b7fd-8c57-425c-b1b5-8b332001a21a", "27c5866d-a966-4380-95af-693955c90f90"): False,
    # ಪಶುವೈದ್ಯ ನೇಮಕಾತಿ ಹಗರಣ: ಸಿಬಿಐ ತನಿಖೆಗೆ ಒಪ್ಪಿಸು  ||  ಎಂಎಲ್​​​ಸಿ ಸಿಟಿ  ರವಿಗೆ ತಾತ್ಕಾಲಿಕ ರಿಲೀಫ್ ನೀಡಿ
    ("eb573e20-3e62-4abf-b168-cce87653ee96", "93acd836-6fc8-412e-802a-3e5f770814cb"): True,
    # YSRCP misleading unemployed youth on Mega DS  ||  YSRCP misleading unemployed youth on Mega DS
    ("eb573e20-3e62-4abf-b168-cce87653ee96", "1e92dbd8-7b19-4ec0-b5fe-5803bb979783"): True,
    # YSRCP misleading unemployed youth on Mega DS  ||  TDP leader condemns YSRCP’s attempts to poli
    ("eb573e20-3e62-4abf-b168-cce87653ee96", "8e7f830c-9fcf-4f6f-9bb9-dfa438c4d155"): True,
    # YSRCP misleading unemployed youth on Mega DS  ||  Minister accuses YSRCP of misleading public 
    ("eb573e20-3e62-4abf-b168-cce87653ee96", "9748b085-4e1e-428a-8687-485613187044"): True,
    # YSRCP misleading unemployed youth on Mega DS  ||  Minister accuses YSRCP of misleading public 
    ("eb573e20-3e62-4abf-b168-cce87653ee96", "c90910c8-9a16-40ce-9b68-7b295e0c67bc"): False,
    # YSRCP misleading unemployed youth on Mega DS  ||  YSRCP seeks Lokesh’s resignation over allege
    ("eb573e20-3e62-4abf-b168-cce87653ee96", "ea70f417-f9f8-46e5-a34e-660185688b3a"): False,
    # YSRCP misleading unemployed youth on Mega DS  ||  YSRCP will intensify agitation over Mega DSC
    ("eb573e20-3e62-4abf-b168-cce87653ee96", "f9d2b58b-5c00-4486-94c1-dba38513c8fb"): False,
    # YSRCP misleading unemployed youth on Mega DS  ||  YSRCP will intensify agitation over Mega DSC
    ("eb573e20-3e62-4abf-b168-cce87653ee96", "27dfb3ff-1ddf-4334-a7a7-edf8f4841d5c"): False,
    # YSRCP misleading unemployed youth on Mega DS  ||  YSRCP stages protests over DSC 'irregulariti
    ("750b0815-5ded-440b-b3ce-459c24e94f98", "9ddce586-7a45-4adc-a1a7-1dbe72469fa7"): True,
    # TTD plans village-level rollout of Srivari S  ||  TTD plans village-level rollout of Srivari S
    ("750b0815-5ded-440b-b3ce-459c24e94f98", "74954aa5-344a-4dfd-a56d-891de13583bb"): False,
    # TTD plans village-level rollout of Srivari S  ||  Seed Access Road, Steel Bridge to be inaugur
    ("750b0815-5ded-440b-b3ce-459c24e94f98", "65db3af3-69e3-4580-84b8-f49916411c68"): False,
    # TTD plans village-level rollout of Srivari S  ||  Indiscipline will not be tolerated, says TDP
    ("750b0815-5ded-440b-b3ce-459c24e94f98", "1fae357b-c250-4c48-a972-b8877b726727"): False,
    # TTD plans village-level rollout of Srivari S  ||  SC panel member requests CM for allocation o
    ("750b0815-5ded-440b-b3ce-459c24e94f98", "0675eca0-2218-488d-8d3b-6421e636cefa"): False,
    # TTD plans village-level rollout of Srivari S  ||  Degree college for hearing-impaired students
    ("750b0815-5ded-440b-b3ce-459c24e94f98", "2b51aee7-3c34-428d-a18b-01dc61c8aa94"): False,
    # TTD plans village-level rollout of Srivari S  ||  Degree college for hearing-impaired students
    ("750b0815-5ded-440b-b3ce-459c24e94f98", "e19329b8-ab26-428c-a444-c2b82337bda4"): False,
    # TTD plans village-level rollout of Srivari S  ||  Farmers block NH-16 in Ongole seeking remune
    ("750b0815-5ded-440b-b3ce-459c24e94f98", "c6304dbb-1bc0-4202-a0e4-a00330345c12"): False,
    # TTD plans village-level rollout of Srivari S  ||  5K run, beach events and drone show to mark 
    ("282e38a4-6392-4ba4-817d-4105f9a792a8", "0f112c01-888e-4623-921b-ff9abb630075"): True,
    # ANTF likely to be empowered with police stat  ||  ANTF likely to be empowered with police stat
    ("282e38a4-6392-4ba4-817d-4105f9a792a8", "1cf9c838-d877-4954-8401-d0ba4a62a5da"): False,
    # ANTF likely to be empowered with police stat  ||  TN civic polls likely to be deferred to earl
    ("282e38a4-6392-4ba4-817d-4105f9a792a8", "212d5b19-9b41-4bd6-9d0e-523a1f408c05"): False,
    # ANTF likely to be empowered with police stat  ||  Kerala Police to launch joint action plan wi
    ("282e38a4-6392-4ba4-817d-4105f9a792a8", "d0c365c1-8c37-4667-a2bd-151546ad05ed"): False,
    # ANTF likely to be empowered with police stat  ||  Kerala Police to launch joint action plan wi
    ("282e38a4-6392-4ba4-817d-4105f9a792a8", "e2e6f3c1-1d9a-4e96-a7eb-2fcfd1d1f370"): False,
    # ANTF likely to be empowered with police stat  ||  Bihar policeman who fired at protesters with
    ("282e38a4-6392-4ba4-817d-4105f9a792a8", "11568e62-b19d-4511-a9df-a10c308de9b2"): False,
    # ANTF likely to be empowered with police stat  ||  Police warned of stringent action if they fa
    ("282e38a4-6392-4ba4-817d-4105f9a792a8", "46886f3e-a45b-40e7-8d77-7970b0237f5c"): False,
    # ANTF likely to be empowered with police stat  ||  Police warned of stringent action if they fa
    ("282e38a4-6392-4ba4-817d-4105f9a792a8", "3dd5eca3-ea9e-4662-9064-f600e2e9a3ad"): False,
    # ANTF likely to be empowered with police stat  ||  MBBS, BDS application portal to be reopened 
    ("08d10c72-5179-4aa6-b2e8-5dc281af452a", "ecf630f9-a22b-4ccb-8038-5bbe9911b516"): True,
    # NEET: Congress, BJP workers detained during   ||  NEET: Congress, BJP workers detained during 
    ("08d10c72-5179-4aa6-b2e8-5dc281af452a", "6ce28b3d-efdd-4968-8184-8ff8ce90b150"): False,
    # NEET: Congress, BJP workers detained during   ||  Congress, allies take NEET protest to PM’s d
    ("08d10c72-5179-4aa6-b2e8-5dc281af452a", "c19980cf-8739-4bd0-a04e-9807179b8342"): False,
    # NEET: Congress, BJP workers detained during   ||  Clash erupts between BJP & Cong workers in H
    ("08d10c72-5179-4aa6-b2e8-5dc281af452a", "4f5e4208-bbc8-4db8-a97c-731c87f58a41"): False,
    # NEET: Congress, BJP workers detained during   ||  Tamil rapper Arivu detained during bid to pr
    ("08d10c72-5179-4aa6-b2e8-5dc281af452a", "578ae680-12f6-481d-a4f3-de56a5c499eb"): False,
    # NEET: Congress, BJP workers detained during   ||  Tamil rapper Arivu detained during bid to pr
    ("08d10c72-5179-4aa6-b2e8-5dc281af452a", "7f91b316-3852-49b0-996a-44ab74019e2d"): False,
    # NEET: Congress, BJP workers detained during   ||  CJP protest LIVE: Heavy barricading across D
    ("08d10c72-5179-4aa6-b2e8-5dc281af452a", "59d32ee0-9186-40f8-a382-0ac3299bbf77"): False,
    # NEET: Congress, BJP workers detained during   ||  400 NEET protesters detained in Mumbai; Adit
    ("08d10c72-5179-4aa6-b2e8-5dc281af452a", "4f08a76a-90bf-47de-a669-1fc50ef09e49"): False,
    # NEET: Congress, BJP workers detained during   ||  Tensions escalate in Vijayawada as BJP activ
    ("c4ea0959-cf83-4c22-86a2-abca20295f2d", "63b28346-5ed9-4202-81c0-ac06fcfa0bd9"): False,
    # PM मोदी पर CJP प्रमुख अभिजीत दिपके ने की ये   ||  CJP प्रोटेस्ट में PM मोदी के खिलाफ आपत्तिजनक
    ("c4ea0959-cf83-4c22-86a2-abca20295f2d", "8a71e3f0-134e-40b9-8572-5cf1ac572570"): False,
    # PM मोदी पर CJP प्रमुख अभिजीत दिपके ने की ये   ||  PM मोदी की अपील का क्या? सोना खरीदारी पर हैर
    ("c4ea0959-cf83-4c22-86a2-abca20295f2d", "ef58dcc5-423c-4d2c-95d3-3d737c026bb0"): False,
    # PM मोदी पर CJP प्रमुख अभिजीत दिपके ने की ये   ||  'कैमरा नहीं, दिल का एंगल बदलिए', PM मोदी पर 
    ("c4ea0959-cf83-4c22-86a2-abca20295f2d", "865868cc-d372-498d-8757-aa5e952e9ebc"): False,
    # PM मोदी पर CJP प्रमुख अभिजीत दिपके ने की ये   ||  'गलती से हट गया था...', PM मोदी का पोस्ट रिम
    ("c4ea0959-cf83-4c22-86a2-abca20295f2d", "d23f9006-0afb-49f0-8368-dfe85acf6b2b"): False,
    # PM मोदी पर CJP प्रमुख अभिजीत दिपके ने की ये   ||  प्रधानमंत्री के खिलाफ अभद्र टिप्पणी: नोएडा क
    ("c4ea0959-cf83-4c22-86a2-abca20295f2d", "b593def0-ef87-4b6f-8c90-87465b4c22e0"): False,
    # PM मोदी पर CJP प्रमुख अभिजीत दिपके ने की ये   ||  पीएम मोदी पर टिप्पणी करना ट्रांसजेंडर मेकअप 
    ("c4ea0959-cf83-4c22-86a2-abca20295f2d", "ce703cf1-2b5d-4704-80cc-665fdafb9c67"): False,
    # PM मोदी पर CJP प्रमुख अभिजीत दिपके ने की ये   ||  अमेरिका-ईरान तनाव के बीच PM मोदी ने बुलाई अह
    ("c4ea0959-cf83-4c22-86a2-abca20295f2d", "3a570901-7a62-4639-8aee-16e8eac71a34"): False,
    # PM मोदी पर CJP प्रमुख अभिजीत दिपके ने की ये   ||  इंस्टाग्राम पर पीएम मोदी के फॉलोअर्स 10 करोड
    ("cf836e6a-2d12-4c3f-b44d-51b3508de9bc", "2634625e-0852-4240-ae12-386d2f3cc470"): False,
    # Congress holds sit-in protests across Himach  ||  Tear gas on students in Patna, BJP-Congress 
    ("cf836e6a-2d12-4c3f-b44d-51b3508de9bc", "0bb068e8-3fcf-4058-8e5d-09c326e65078"): False,
    # Congress holds sit-in protests across Himach  ||  Parliament stays in deadlock over student pr
    ("cf836e6a-2d12-4c3f-b44d-51b3508de9bc", "bdf2b600-bdcc-40fa-bf1c-92f98fda7f77"): False,
    # Congress holds sit-in protests across Himach  ||  Punjab's 'Business Class' programme sees ove
    ("cf836e6a-2d12-4c3f-b44d-51b3508de9bc", "67c64f3e-74a9-40a6-ac43-ebc177f15da6"): False,
    # Congress holds sit-in protests across Himach  ||  Haryana Congress seeks Murmu’s intervention 
    ("cf836e6a-2d12-4c3f-b44d-51b3508de9bc", "b57ea3ce-fc95-4c63-8697-e76b71314f23"): False,
    # Congress holds sit-in protests across Himach  ||  Address genuine concerns of protesting stude
    ("cf836e6a-2d12-4c3f-b44d-51b3508de9bc", "22eda1a1-b3f2-4a1a-8a88-34b738789b87"): False,
    # Congress holds sit-in protests across Himach  ||  Student bodies to hold ‘Chalo Lok Bhavan’ pr
    ("cf836e6a-2d12-4c3f-b44d-51b3508de9bc", "3f3ea69a-06fd-4cc7-be14-2adee1c836a4"): False,
    # Congress holds sit-in protests across Himach  ||  Student bodies to hold ‘Chalo Lok Bhavan’ pr
    ("cf836e6a-2d12-4c3f-b44d-51b3508de9bc", "2aae2323-0d77-4155-89b5-b0a2ecf92ee1"): False,
    # Congress holds sit-in protests across Himach  ||  IJU condemns attacks on journalists covering
    ("c997fc5b-dda5-4fbf-945d-1f226b52b638", "89d51cc2-19d5-4170-a678-b23b03d8d2e9"): False,
    # ಚಿಕ್ಕದೇವಮ್ಮ ಬೆಟ್ಟದ ರಸ್ತೆಯ ಬಾರ್ ತೆರವುಗೊಳಿಸಲು   ||  ರೀಲ್ಸ್‌ ಬಿಟ್ಟು, ಕಸ ತೆರವುಗೊಳಿಸಿ: ಆರ್.ಅಶೋಕ
    ("c997fc5b-dda5-4fbf-945d-1f226b52b638", "b180f670-886c-40bf-85e9-635d092e790c"): False,
    # ಚಿಕ್ಕದೇವಮ್ಮ ಬೆಟ್ಟದ ರಸ್ತೆಯ ಬಾರ್ ತೆರವುಗೊಳಿಸಲು   ||  ಬೆಂಗಳೂರಿನಲ್ಲಿ ಅಕ್ರಮ ಬಾಂಗ್ಲಾ ವಲಸಿಗರ ಮಾಹಿತಿ ನೀ
    ("c997fc5b-dda5-4fbf-945d-1f226b52b638", "70a952bb-f4d7-4a6b-b751-a52e510dcb5c"): False,
    # ಚಿಕ್ಕದೇವಮ್ಮ ಬೆಟ್ಟದ ರಸ್ತೆಯ ಬಾರ್ ತೆರವುಗೊಳಿಸಲು   ||  40 ಲಕ್ಷ ರೂ ವರದಕ್ಷಿಣೆ, ಸಂಬಳಕ್ಕಾಗಿ ಗಲಾಟೆ: ಚೇಂಬ
    ("c997fc5b-dda5-4fbf-945d-1f226b52b638", "7f86d05f-7e5f-4059-988f-5b64950f3d99"): False,
    # ಚಿಕ್ಕದೇವಮ್ಮ ಬೆಟ್ಟದ ರಸ್ತೆಯ ಬಾರ್ ತೆರವುಗೊಳಿಸಲು   ||  घर लौट रहे थे, रास्ते में मौत से हो गई मुलाक
    ("c997fc5b-dda5-4fbf-945d-1f226b52b638", "e6e1bf68-1c1c-4a8e-b8ed-cead45d0e8a1"): False,
    # ಚಿಕ್ಕದೇವಮ್ಮ ಬೆಟ್ಟದ ರಸ್ತೆಯ ಬಾರ್ ತೆರವುಗೊಳಿಸಲು   ||  Four-storey building tilts in east Delhi's G
    ("9584aee9-5f6a-4972-bcfb-c6942ea5c960", "8d42dc86-58fd-4521-b5b3-f8a6ca0cd343"): True,
    # Gram Panchayats receive 44 e-autos for solid  ||  Gram Panchayats receive 44 e-autos for solid
    ("9584aee9-5f6a-4972-bcfb-c6942ea5c960", "40ce0e78-6fad-4a6d-8257-48ad6b81764e"): False,
    # Gram Panchayats receive 44 e-autos for solid  ||  Comprehensive solid waste management a prior
    ("9584aee9-5f6a-4972-bcfb-c6942ea5c960", "7c76ba05-c3d1-4971-9fc4-92f969a566e8"): False,
    # Gram Panchayats receive 44 e-autos for solid  ||  Comprehensive solid waste management a prior
    ("9584aee9-5f6a-4972-bcfb-c6942ea5c960", "f2ff1e70-bd14-4eef-9e54-7e0d7014035a"): False,
    # Gram Panchayats receive 44 e-autos for solid  ||  Centre urged to develop Buddhist circuit in 
    ("9584aee9-5f6a-4972-bcfb-c6942ea5c960", "e4fb0127-ed6e-49bc-ac4c-558e05b5a9b1"): False,
    # Gram Panchayats receive 44 e-autos for solid  ||  ‘Telugu Mahotsavam’ to be annual  event, say
}


def pair_count() -> int:
    return len(GOLD_PAIRS)


def positive_count() -> int:
    return sum(GOLD_PAIRS.values())
