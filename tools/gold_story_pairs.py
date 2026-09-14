"""Hand-labelled STORY boundaries, pairwise, adjudicated. The v2 gold set.

Two labellers judged 1,147 (seed, candidate) pairs across 123 seeds drawn uniformly
from the corpus (batch yy5J0lJdX00L, 2026-09-07..09; one 27-story second pass,
mwWQawQFPvj6, 2026-09-10). They agreed on 1,111. The 36 they split on were
adjudicated with full context on 2026-09-14 and ratified by the founder, so
unlike tools/gold_stories nothing here is excluded as ambiguous: every judged pair
carries a verdict.

PAIRWISE, NOT GROUPINGS, on purpose. Only seed<->candidate pairs were judged. A
grouping would assert candidate<->candidate pairs nobody looked at — the same
"measured on a slice" error this repo has already paid for. Score exactly the
pairs in PAIRS and nothing else; a story the batch never asked about must not
count as a true negative.

WHAT "SAME STORY" MEANS HERE — the definition the adjudication fixed, so a future
labeller or tool applies the same one:

  SAME      the same real-world happening, however the headline is worded, in
            whatever language; its direct follow-ups ("2,000 detained after the
            attack"); its daily updates when they track ONE thing (a flood toll,
            a film's box-office run, the same day's rain in one city).
  DIFFERENT the same topic, place, organisation or person doing two things; the
            same recurring FORMAT with no arc ("gold price today", two days);
            two vulnerabilities in one product; and ALWAYS a roundup vs any
            single item it lists — merging through roundups is how every
            company on results day becomes one blob.

THE TWO LABELLERS HAD OPPOSITE, COHERENT BIASES, worth knowing when reading any
single-annotator set: one merged by topic (all 7 of their misses were roundups,
a second CVE in the same product, two animals from one forest department); the
other split unfolding stories into per-day snapshots (all 16 of theirs). Neither
was careless. Kappa between them was 0.40 — two opinions, not a gold set, until
adjudicated.

Provenance per pair: "agree" (both said the same), or "adj:<who-said-SAME>" for
the 36 adjudicated, so the disputed class can be isolated in a score.
"""

from __future__ import annotations

BATCHES = ("yy5J0lJdX00L", "mwWQawQFPvj6")
ADJUDICATED_ON = "2026-09-14"

# (seed_event_id, candidate_event_id) -> (same_story, provenance)
PAIRS: dict[tuple[str, str], tuple[bool, str]] = {
    # seed: 'Rise of a sporting prodigy': Anand Mahindra hails Anahat Singh on winning [...]
    ("f88f0d25-b1e8-4b6d-853b-be015334a6ec", "148ef86d-022e-43d6-8bc2-38271ed3463e"): (False, "agree"),  # Eight A.P. players selected for National U-19 Chess [...]
    ("f88f0d25-b1e8-4b6d-853b-be015334a6ec", "159e006c-c3f2-4b19-b085-98fe51b0427c"): (False, "agree"),  # Action plan to expand organ transplant services in [...]
    ("f88f0d25-b1e8-4b6d-853b-be015334a6ec", "2d85bc33-56aa-4133-a71c-0219d4ffff2a"): (False, "agree"),  # Woman who stopped Mumbai police van files complaint [...]
    ("f88f0d25-b1e8-4b6d-853b-be015334a6ec", "33194c29-f0ac-4beb-897e-bdbd0fefa24b"): (False, "agree"),  # 'Thank you VVS sir': Iyer credits Laxman after India's [...]
    ("f88f0d25-b1e8-4b6d-853b-be015334a6ec", "37fe3a77-5b7c-4d8e-9d51-2596564ebb6c"): (False, "agree"),  # Suneil Anand, Actor And Son Of Bollywood Legend Dev [...]
    ("f88f0d25-b1e8-4b6d-853b-be015334a6ec", "4748d8a1-71e4-4540-8f1e-ed96daa4ba0f"): (False, "agree"),  # Greta Thunberg says CJP protest 'given us hope', backs [...]
    ("f88f0d25-b1e8-4b6d-853b-be015334a6ec", "526d56a7-20a8-4821-83a6-77fbfc429962"): (False, "agree"),  # Dev Anand's son suneil anand's cremation to be held on [...]
    ("f88f0d25-b1e8-4b6d-853b-be015334a6ec", "7cd631fc-6679-4e33-8b5f-1774144c8a71"): (False, "agree"),  # UAE qualify for 2027 Under-19 Women's T20 World Cup by [...]
    ("f88f0d25-b1e8-4b6d-853b-be015334a6ec", "992bba47-e95e-4710-b05b-ccb06e9b413c"): (False, "agree"),  # ‘Messi is a human being’: Sourav Ganguly defends Leo [...]
    ("f88f0d25-b1e8-4b6d-853b-be015334a6ec", "a5306b34-ef04-4780-b7a8-cb06e82c039b"): (False, "agree"),  # 'Composure isn't the opposite of aggression': Sachin's [...]
    # seed: 'ये सिर्फ दिखावे का बिल', देखें लोकसभा में गौरव गोगोई का सरकार पर वार
    ("218193a0-bde5-42b6-876c-ed4b78311b71", "462e7922-5dd2-4c75-a67b-1ae1735a4478"): (False, "agree"),  # What happened on Day 1 of Pralhad Joshi as education [...]
    ("218193a0-bde5-42b6-876c-ed4b78311b71", "6c2358aa-ddb2-4e7b-a6ee-6e4a2e7727e3"): (False, "agree"),  # Government to set up fast-track courts for paper leak [...]
    ("218193a0-bde5-42b6-876c-ed4b78311b71", "91a936a4-6de1-44c7-ad26-eb04c66a707a"): (False, "agree"),  # Dharmendra Pradhan meets Birla as government agrees to [...]
    ("218193a0-bde5-42b6-876c-ed4b78311b71", "9efb88a5-4a84-4ac8-936f-f433d712ffaf"): (False, "agree"),  # Prahlad Joshi takes charge as education minister
    ("218193a0-bde5-42b6-876c-ed4b78311b71", "a6e8f22d-cf38-437d-bb02-fa33dc16bc56"): (False, "agree"),  # Speaker’s nod to Sena (UBT) MPs’ merger challenged in SC
    ("218193a0-bde5-42b6-876c-ed4b78311b71", "ad377aee-611a-4859-b65f-4cf22c182f32"): (False, "agree"),  # In 1997, Dharmendra Pradhan, then an ABVP leader, led [...]
    ("218193a0-bde5-42b6-876c-ed4b78311b71", "b86b4764-0b19-4611-9d23-8c2714adf8a0"): (False, "agree"),  # 'वो बात से मुकर गए...', राहुल गांधी-जितेंद्र सिंह के [...]
    ("218193a0-bde5-42b6-876c-ed4b78311b71", "d8a913ce-d25f-4ad8-b02f-2555eb01c24c"): (False, "agree"),  # Students are more important than any post: Amit Shah [...]
    ("218193a0-bde5-42b6-876c-ed4b78311b71", "d9887ff1-90d0-4318-af37-39558c78e205"): (False, "agree"),  # Parliament clears anti-paper leak bill for tougher [...]
    ("218193a0-bde5-42b6-876c-ed4b78311b71", "ecb1a011-5232-4d8a-a155-3f1e1f735d93"): (False, "agree"),  # Parliament monsoon session highlights: 'Sadan mein [...]
    # seed: 150 साल का रिकॉर्ड तोड़ेगा अल-नीनो, पड़ेगी भयानक गर्मी, छूटेगा पसीना
    ("8e15b161-6d61-4946-ab82-6f190549307d", "5637cad8-dc68-4d53-9ba3-a64e9bea28c0"): (False, "agree"),  # Scientists detect sharp acceleration in global [...]
    ("8e15b161-6d61-4946-ab82-6f190549307d", "71efd79d-56f5-4bf2-8b63-e0c61608e789"): (False, "agree"),  # अब अल-नीनो का खतरनाक रूप... क्यों अगले कुछ दिन मॉनसून [...]
    ("8e15b161-6d61-4946-ab82-6f190549307d", "81f384ed-56e1-438a-a1f1-bac40d604b81"): (False, "agree"),  # 24 घंटे का वेदर अलर्ट! इन राज्यों में जमकर बरसेंगे बादल
    ("8e15b161-6d61-4946-ab82-6f190549307d", "8ddcf5d1-9f3c-400e-aad9-435afc1a7cf5"): (False, "agree"),  # El Niño may push global warming to 2C or higher in the [...]
    ("8e15b161-6d61-4946-ab82-6f190549307d", "afea08e6-34b4-4236-a0c6-3aafc04b3246"): (False, "agree"),  # 40°C पहुंचा पारा, जापान में पहली बार घोषित हुआ [...]
    ("8e15b161-6d61-4946-ab82-6f190549307d", "e94c7bee-d988-4973-8554-83aef8bd4e27"): (False, "agree"),  # साउथ कोरिया में 42.5°C पहुंचा पारा, इमरजेंसी अलर्ट जारी
    # seed: 3 साल बाद कप्तानी में लौटे बाबर बुरी तरह हुए फ्लॉप
    ("fb90bf47-f090-4aa5-8994-57f2a6f224e4", "7e26ca31-4b44-4e15-ba73-a96856770bc2"): (False, "agree"),  # WI vs PAK: ನಾಯಕತ್ವದಿಂದ ಕೆಳಗಿಳಿದ ಬೆನ್ನಲ್ಲೇ ಶತಕ ಸಿಡಿಸಿದ [...]
    ("fb90bf47-f090-4aa5-8994-57f2a6f224e4", "142a0bcc-6d8d-4f3c-a30a-f6f69945c37d"): (False, "agree"),  # Sammy: 'We didn't pick Lawes just out of our heart'
    ("fb90bf47-f090-4aa5-8994-57f2a6f224e4", "143e70da-dd5d-4238-ba05-79e0ff2dfdd4"): (False, "agree"),  # WI vs PAK: 21 ವರ್ಷಗಳ ಬಳಿಕ 49 ರನ್​ಗಳ ಜೊತೆಯಾಟ!
    ("fb90bf47-f090-4aa5-8994-57f2a6f224e4", "4a1cb805-0429-458a-bf94-5309571de343"): (False, "agree"),  # Unchanged West Indies bat first seeking series sweep, [...]
    ("fb90bf47-f090-4aa5-8994-57f2a6f224e4", "503b491e-6478-443f-8b98-1dee9c769e2c"): (False, "agree"),  # जो IPL में नहीं चमका, वही बुमराह का रिप्लेसमेंट... [...]
    ("fb90bf47-f090-4aa5-8994-57f2a6f224e4", "5d5b3172-da58-4bf4-88a4-746f0f7bc477"): (False, "agree"),  # Babar, Awais hit centuries and Mohammad Ali bags five- [...]
    ("fb90bf47-f090-4aa5-8994-57f2a6f224e4", "ad07c223-b41b-4887-bf78-99b946d22aeb"): (False, "agree"),  # पाकिस्तान क्रिकेट में बड़ा बदलाव, टीम को मिला नया कोच!
    ("fb90bf47-f090-4aa5-8994-57f2a6f224e4", "dd2bff83-16a6-477f-a85b-37bc27bd26fa"): (False, "agree"),  # 5 ಓವರ್, 5 ಮೇಡನ್, 5 ವಿಕೆಟ್​: ಹಿಂದೆಂದೂ ಕಂಡರಿಯದ ವಿಶ್ವ [...]
    ("fb90bf47-f090-4aa5-8994-57f2a6f224e4", "fc1ae27a-1416-4459-ab48-1bc18356cfa2"): (False, "agree"),  # Masood, Imam and Ali make it Pakistan's day
    # seed: 32 ತಂಡಗಳ ಟಿ20 ವಿಶ್ವಕಪ್​ಗೆ ಐಸಿಸಿ ಮಾಸ್ಟರ್ ಪ್ಲ್ಯಾನ್!
    ("fa94526f-4c12-4a28-9b82-798f0625a5f5", "02028be1-422b-42e8-90d3-6618d61eb7db"): (False, "agree"),  # ಮಹಿಳಾ ಏಷ್ಯಾಕಪ್​ ಟೂರ್ನಿಗೆ ಡೇಟ್ ಫಿಕ್ಸ್..!
    ("fa94526f-4c12-4a28-9b82-798f0625a5f5", "0599ca3f-b3d2-459a-9b06-4dbd7580270a"): (False, "agree"),  # टीम इंडिया के असिस्टेंट कोच ने अचानक दिया इस्तीफा
    ("fa94526f-4c12-4a28-9b82-798f0625a5f5", "0b787ba9-9c3e-4c7a-921d-a330c8eacdd7"): (False, "agree"),  # Chapman, Santner star in low-scoring thriller as NZ [...]
    ("fa94526f-4c12-4a28-9b82-798f0625a5f5", "18f85e79-f6a6-473b-88bc-9cf6889baff7"): (False, "agree"),  # ಜಮ್ಷೆಡ್‌ಪುರ ತಂಡದ ವಿಸರ್ಜನೆ: ಮರುಪರಿಶೀಲನೆಗೆ ಆಟಗಾರರ ಮನವಿ
    ("fa94526f-4c12-4a28-9b82-798f0625a5f5", "2a2a7531-97a7-46ef-b7ce-bfb741da0771"): (False, "agree"),  # IPL 2027: ಐಪಿಎಲ್ ಟ್ರೇಡ್ ವಿಂಡೋ: ತೆರೆಮರೆಯ ರಣತಂತ್ರಗಳು
    ("fa94526f-4c12-4a28-9b82-798f0625a5f5", "356e67e2-0894-484d-9900-7f15ab2147f1"): (False, "agree"),  # ಸೀಮಿತ ಓವರ್​ಗಳ ಸರಣಿಗಾಗಿ ಬಾಂಗ್ಲಾ ಪ್ರವಾಸ ಮಾಡಲಿದೆ ಟೀಂ ಇಂಡಿಯಾ
    ("fa94526f-4c12-4a28-9b82-798f0625a5f5", "3e54e8c0-98d6-4a96-b555-ae12670bf1fa"): (False, "agree"),  # Lennox stars again as New Zealand take series lead [...]
    ("fa94526f-4c12-4a28-9b82-798f0625a5f5", "47eba03a-d17f-4d23-b006-3bf112a443d6"): (False, "agree"),  # ಟೀಂ ಇಂಡಿಯಾ ಬಾಂಗ್ಲಾಕ್ಕೆ ಬರಲಿದೆ ಎಂಬ ಭರವಸೆ ಇದೆ; ಬಿಸಿಬಿ [...]
    ("fa94526f-4c12-4a28-9b82-798f0625a5f5", "4d0143f7-849c-4e78-a0ad-ba100d3d15ad"): (False, "agree"),  # West Indies bowl first and pick Hetmyer in the bid for [...]
    ("fa94526f-4c12-4a28-9b82-798f0625a5f5", "7bfab6f0-db73-4987-af9c-cfe0b40617fd"): (False, "agree"),  # Why Saudi Arabia finally joined the US war on Iran: [...]
    # seed: 50 OTT platforms disabled for displaying obscene content, other violations: Govt.
    ("4f6d28fb-4f2c-4977-8ff7-6597a01a106f", "46526919-75e6-492d-9780-285d1e736b07"): (True, "agree"),  # 50 OTT platforms disabled over the last two years | [...]
    ("4f6d28fb-4f2c-4977-8ff7-6597a01a106f", "0c012089-1989-4199-b94d-6a8b4148fd70"): (False, "agree"),  # India mocks sham election in PoK, says cosmetic [...]
    ("4f6d28fb-4f2c-4977-8ff7-6597a01a106f", "3f8542c2-0528-48d7-8c3f-41177a32a2f3"): (False, "agree"),  # India must review safe harbour rules after Russia’s [...]
    ("4f6d28fb-4f2c-4977-8ff7-6597a01a106f", "79ba7c61-7a48-4ce1-a2d5-ccd0c3c92466"): (False, "agree"),  # इन ट्रेनों के टिकट कैंसिलेशन पर ज्यादा चार्ज क्यों? [...]
    ("4f6d28fb-4f2c-4977-8ff7-6597a01a106f", "893d979e-0385-4257-849e-0f4955c16f7c"): (False, "agree"),  # GenZ ने सरकारी वेबसाइट में ढूंढी बड़ी खामी, आधार डेटा [...]
    ("4f6d28fb-4f2c-4977-8ff7-6597a01a106f", "8bc76f00-f0dc-4cd1-b1ed-9412b4cc36ae"): (False, "agree"),  # NHAI issues policy circular on monitoring social media [...]
    ("4f6d28fb-4f2c-4977-8ff7-6597a01a106f", "ae3b6b39-147d-4eaa-8012-13816fd178b8"): (False, "agree"),  # BJP functionary files complaint over morphed video of [...]
    ("4f6d28fb-4f2c-4977-8ff7-6597a01a106f", "af72cf67-e8f8-41c2-aacd-1597be8fe1e5"): (False, "agree"),  # I&B Ministry's Hindi Advisory Committee pushes wider [...]
    ("4f6d28fb-4f2c-4977-8ff7-6597a01a106f", "b8599a6e-6ac2-424c-b041-6dfc9682977b"): (False, "agree"),  # Kavach 4.0 set for major expansion across SCR, ScoR networks
    ("4f6d28fb-4f2c-4977-8ff7-6597a01a106f", "bb8150ed-7b73-45c6-92e0-dd23172b526b"): (False, "agree"),  # BJP seeks Sreelekha Mitra's arrest over PM Modi's [...]
    # seed: APCRDA launches grama sabhas to discuss Amaravati village road plans
    ("cb90219f-9aca-4cce-9267-3b332a511072", "a890925a-9cf9-4bb8-89ab-968e4ca0ff1b"): (False, "agree"),  # Majority of farmers back LPS for Amaravati rail, ring [...]
    ("cb90219f-9aca-4cce-9267-3b332a511072", "ffc2d220-a8d7-4313-afe2-9d3ade032426"): (False, "agree"),  # Expedite Amaravati works without compromising on [...]
    ("cb90219f-9aca-4cce-9267-3b332a511072", "3bdf2a47-6667-4e7f-bbb3-d64cc1588c5d"): (False, "agree"),  # Telangana CM requests Centre for additional works [...]
    ("cb90219f-9aca-4cce-9267-3b332a511072", "4216326a-0c91-4de5-a24e-5f5a3c5de3a2"): (False, "agree"),  # HC orders status quo over Bahadurguda village lands
    ("cb90219f-9aca-4cce-9267-3b332a511072", "4db9740c-8483-495f-bc66-a684b7291e67"): (False, "agree"),  # SC panel member requests CM for allocation of lands to [...]
    ("cb90219f-9aca-4cce-9267-3b332a511072", "91a936a4-6de1-44c7-ad26-eb04c66a707a"): (False, "agree"),  # Dharmendra Pradhan meets Birla as government agrees to [...]
    ("cb90219f-9aca-4cce-9267-3b332a511072", "9e4e1fb6-adce-48eb-92ff-363e4bcc7c80"): (False, "agree"),  # TTD plans village-level rollout of Srivari Seva in [...]
    ("cb90219f-9aca-4cce-9267-3b332a511072", "c8c1e1e3-c45c-461a-bc00-3fb360ffa187"): (False, "agree"),  # Andhra govt approves ₹500 crore worth works to ensure [...]
    # seed: AWS Kiro Flaw Let a Poisoned Web Page Rewrite Its Config and Run Code
    ("a9f85283-3242-4165-9e8e-cdc8540a6b74", "43801769-8cdb-40a3-ab62-9f7e965fdff9"): (False, "agree"),  # अजित पवार की जयंती पर भावुक हुईं सुनेत्रा पवार, देखें PHOTOS
    ("a9f85283-3242-4165-9e8e-cdc8540a6b74", "4ccd9af4-96f6-4729-a341-3ecb6229b30c"): (False, "agree"),  # Copper cables worth ₹78 lakh stolen from BMRCL phase-2 [...]
    ("a9f85283-3242-4165-9e8e-cdc8540a6b74", "5bcb916d-ff49-42d2-8217-4073635ccbb4"): (False, "agree"),  # Kerala’s new late-night bar policy to boost wedding, [...]
    ("a9f85283-3242-4165-9e8e-cdc8540a6b74", "9bebc394-1a03-4479-88ab-cd24faaf6612"): (False, "agree"),  # कानपुर में महिला ने बुजुर्ग से FB पर की दोस्ती, फिर [...]
    ("a9f85283-3242-4165-9e8e-cdc8540a6b74", "c2f1f517-113d-4147-aecb-fce01b5d690a"): (False, "agree"),  # Teacher’s family duped twice in cyberfraud, loses ₹45 [...]
    # seed: Amid power crisis, workplace accidents pose stiff challenge to Kerala State [...]
    ("8021e981-2a68-42dd-85e5-7a0ec51bb92a", "9b720c1b-fcc4-48e8-9269-b50de63f97bd"): (False, "agree"),  # State Electricity Regulatory Commission nod for long- [...]
    ("8021e981-2a68-42dd-85e5-7a0ec51bb92a", "eb909330-ff6d-495f-94ed-d485126d9fc7"): (False, "agree"),  # Hydel storage improves, but rainfall plays havoc with [...]
    ("8021e981-2a68-42dd-85e5-7a0ec51bb92a", "52b273c9-5f4e-44a8-bf58-c88fb54254b4"): (False, "agree"),  # AI Data Centre to consume 26.3 GW electricity by FY32: [...]
    ("8021e981-2a68-42dd-85e5-7a0ec51bb92a", "54c8c3ab-7191-4a0f-905d-50e2f2f3da07"): (False, "agree"),  # Kerala rains: 92% of power connection restored after [...]
    ("8021e981-2a68-42dd-85e5-7a0ec51bb92a", "894f7ebe-085e-4f68-936f-a305ffcc79ae"): (False, "agree"),  # Protests In Punjab Reach Parliament, Become Challenge [...]
    ("8021e981-2a68-42dd-85e5-7a0ec51bb92a", "8be2868c-25bf-4059-8ff2-591c0ed25937"): (False, "agree"),  # Power plant coal stocks shrink amid high electricity demand
    ("8021e981-2a68-42dd-85e5-7a0ec51bb92a", "ad337dfb-9b30-4752-8175-ad9a0335a7ec"): (False, "agree"),  # Tamil Nadu tops road accidents, Uttar Pradesh remains [...]
    ("8021e981-2a68-42dd-85e5-7a0ec51bb92a", "bb9bc3e2-deb5-4e0d-86cb-7f81df03d671"): (False, "agree"),  # Mylatti BESS project to be commissioned in October, [...]
    ("8021e981-2a68-42dd-85e5-7a0ec51bb92a", "c8d9aa31-0003-4d57-aa55-f436d4309e7a"): (False, "agree"),  # Tamil Nadu Today: White Paper on electricity [...]
    ("8021e981-2a68-42dd-85e5-7a0ec51bb92a", "e99a6a37-faf2-47a9-aa3b-caddfbfe4f7d"): (False, "agree"),  # Kerala’s power crisis partly due to cancellation of [...]
    # seed: Anant Raj to demerge data centre business into separate listed entity
    ("6d3ef96c-bf98-425e-8e2c-3f5a9dcd2b5f", "3ab1046c-a7f9-4828-a3f4-338c2ad235c0"): (False, "agree"),  # Vedanta to demerge surplus real estate into Vedanta [...]
    ("6d3ef96c-bf98-425e-8e2c-3f5a9dcd2b5f", "0dd50ce5-7fbf-47bf-a3c7-917dc5c167ea"): (False, "agree"),  # UltraTech Cement net up 17% on strong realisation, [...]
    ("6d3ef96c-bf98-425e-8e2c-3f5a9dcd2b5f", "1d69904f-cf70-45ef-99d0-0e4b2c958645"): (False, "agree"),  # India's data centre capacity may reach 3-3.6 GW by [...]
    ("6d3ef96c-bf98-425e-8e2c-3f5a9dcd2b5f", "232b6523-3cae-4ab5-a66d-1243179c0d4c"): (False, "agree"),  # Two die in separate accidents in Chikkamagaluru
    ("6d3ef96c-bf98-425e-8e2c-3f5a9dcd2b5f", "27d3f763-c105-4130-8d52-a1dbd6e19144"): (False, "agree"),  # Lodha Developers to monetise 150 acres at data centre [...]
    ("6d3ef96c-bf98-425e-8e2c-3f5a9dcd2b5f", "ae89f475-48b9-44f0-bf0e-0f84b98ed2de"): (False, "agree"),  # Data centre row: Left leaders detained en route to Tarluvada
    ("6d3ef96c-bf98-425e-8e2c-3f5a9dcd2b5f", "b26e5b3d-f947-4682-90d0-4fc643422ee6"): (False, "agree"),  # Seven arrested, nearly 48 kg of ganja seized in [...]
    ("6d3ef96c-bf98-425e-8e2c-3f5a9dcd2b5f", "c22d02b1-4bce-4a52-a552-7460467df072"): (False, "agree"),  # Coforge To Set Up Entity In China To Expand Operations
    ("6d3ef96c-bf98-425e-8e2c-3f5a9dcd2b5f", "c279a3f9-07b9-42e8-a4e9-e6eaffb0b2a5"): (False, "agree"),  # Prestige Estates Q1 profit down 19% to ₹236 cr
    # seed: Andhra Pradesh girl selected for world’s first all-girls lunar CubeSat mission
    ("39729783-6191-42c3-9313-f022ed3b1115", "43d19673-51d9-4846-a0e7-fcbabf6bf8c0"): (False, "agree"),  # Nellore all set to distribute 10,000 bicycles to girl [...]
    ("39729783-6191-42c3-9313-f022ed3b1115", "064559c3-5b7c-4f8b-9f4c-eec214228624"): (False, "agree"),  # Lokesh to distribute 3,000 house site title deeds in [...]
    ("39729783-6191-42c3-9313-f022ed3b1115", "07d66550-32a9-492e-86f5-f1b4f5deca65"): (False, "agree"),  # Nara Lokesh distributes land titles to 3,000 residents [...]
    ("39729783-6191-42c3-9313-f022ed3b1115", "1963be9f-706e-4c16-9acf-f721f0a4e90b"): (False, "agree"),  # ‘Telugu Mahotsavam’ to be annual event, says Minister [...]
    ("39729783-6191-42c3-9313-f022ed3b1115", "1bcc5bdc-8aae-44ab-8915-06e6e9c7bcc2"): (False, "agree"),  # Telangana committed to addressing NRIs’ concerns: Jupally
    ("39729783-6191-42c3-9313-f022ed3b1115", "2bd009d4-b9e9-44ad-9edf-ce2f9de976a0"): (False, "agree"),  # Home Minister Anitha seeks apology from Jagan over [...]
    ("39729783-6191-42c3-9313-f022ed3b1115", "58ef0db6-a9a0-45bf-bd44-35be01710b5a"): (False, "agree"),  # Not Selected For Cricket Team, 17-Year-Old Girl Dies [...]
    ("39729783-6191-42c3-9313-f022ed3b1115", "7409903c-a511-4d85-b541-e9fca97c5f4e"): (False, "agree"),  # Prosthetic hand camps to be held in all Andhra Pradesh [...]
    ("39729783-6191-42c3-9313-f022ed3b1115", "8fa2e779-68d5-4b19-80b2-d9e737816b80"): (False, "agree"),  # Andhra Pradesh launches AI-powered flood alert system [...]
    ("39729783-6191-42c3-9313-f022ed3b1115", "96508d70-aabd-4396-aed7-9b0c0f4f99bd"): (False, "agree"),  # TPREL begins construction of ₹5,350 crore hybrid [...]
    # seed: Andhra Pradesh registers six new COVID cases, three each from East Godavari, [...]
    ("a1444e89-7e8d-406c-89a5-81170b9a4dca", "0d670b86-b6a0-46bb-b5dc-e281df53d3fb"): (False, "agree"),  # Nipah: surveillance steps withdrawn in Ramanattukara
    ("a1444e89-7e8d-406c-89a5-81170b9a4dca", "1c5fd833-3fa8-4310-9a16-b29a53667137"): (False, "agree"),  # Ernakulam reports highest number of influenza cases in State
    ("a1444e89-7e8d-406c-89a5-81170b9a4dca", "21a2b95a-924e-4120-8fb5-0b18a362d16d"): (False, "agree"),  # PAV urges govt. to strengthen disease surveillance as [...]
    ("a1444e89-7e8d-406c-89a5-81170b9a4dca", "d46628ca-6e22-459c-8874-606fdecd6150"): (False, "agree"),  # No active COVID clusters in A.P., cases only sporadic, [...]
    ("a1444e89-7e8d-406c-89a5-81170b9a4dca", "01eb542f-0116-4b00-bbbd-1691e79ed8f4"): (False, "agree"),  # BRS alleges delay in TIMS Alwal construction; Congress [...]
    ("a1444e89-7e8d-406c-89a5-81170b9a4dca", "0fc8ec3b-a7de-4be0-8585-306e5dc1514d"): (False, "agree"),  # Food safety drive: six eateries inspected in Kochi
    ("a1444e89-7e8d-406c-89a5-81170b9a4dca", "2cfb4573-fc6d-4592-9a24-f8c0ecfd969b"): (False, "agree"),  # Flood alert sounded along Godavari, Sabari riverbanks [...]
    ("a1444e89-7e8d-406c-89a5-81170b9a4dca", "2fad7ce6-ea45-482a-9db3-5cada275ed26"): (False, "agree"),  # Heavy rainfall forecast in six Telangana districts on [...]
    ("a1444e89-7e8d-406c-89a5-81170b9a4dca", "7409903c-a511-4d85-b541-e9fca97c5f4e"): (False, "agree"),  # Prosthetic hand camps to be held in all Andhra Pradesh [...]
    ("a1444e89-7e8d-406c-89a5-81170b9a4dca", "9aeb8901-7d8c-427a-b133-dce2033a3a96"): (False, "agree"),  # Gram Panchayats receive 44 e-autos for solid waste [...]
    # seed: Andhra Pradesh to draw up action plan against zoonotic diseases
    ("f6b5066d-7707-48ab-b4e3-9747f33a0d04", "159e006c-c3f2-4b19-b085-98fe51b0427c"): (False, "agree"),  # Action plan to expand organ transplant services in [...]
    ("f6b5066d-7707-48ab-b4e3-9747f33a0d04", "2b3c58fa-9076-4ae9-9023-1b519f4a1582"): (False, "agree"),  # Michigan confirms first Cyclospora deaths in US amid [...]
    ("f6b5066d-7707-48ab-b4e3-9747f33a0d04", "582ed964-f31f-4e7e-8ed7-64117fd9f0d9"): (False, "agree"),  # Week-long chlorination drive in Wayanad in view of [...]
    ("f6b5066d-7707-48ab-b4e3-9747f33a0d04", "6616c407-5ad1-4341-93df-1a2a7916c19c"): (False, "agree"),  # Andhra Pradesh govt. invites tenders for [...]
    ("f6b5066d-7707-48ab-b4e3-9747f33a0d04", "6aa9846f-38d9-42ff-939d-ea7ba59ccaae"): (False, "agree"),  # A.P. govt. launches action plan to check fodder [...]
    ("f6b5066d-7707-48ab-b4e3-9747f33a0d04", "7e67c967-d215-4668-9067-9facd595832a"): (False, "agree"),  # FDA Is Investigating Another Cyclospora Parasite Outbreak
    ("f6b5066d-7707-48ab-b4e3-9747f33a0d04", "8a86cec1-3d82-4f73-afae-27162f6bc422"): (False, "agree"),  # Andhra Pradesh Congress condemns lathi-charge on [...]
    ("f6b5066d-7707-48ab-b4e3-9747f33a0d04", "8fa2e779-68d5-4b19-80b2-d9e737816b80"): (False, "agree"),  # Andhra Pradesh launches AI-powered flood alert system [...]
    ("f6b5066d-7707-48ab-b4e3-9747f33a0d04", "c0e5941a-bf3f-4a22-91e0-ceb629170b68"): (False, "agree"),  # Health department urges public to remain vigilant [...]
    ("f6b5066d-7707-48ab-b4e3-9747f33a0d04", "c30ae9c7-f24b-464a-85bf-18d5aa5e807b"): (False, "agree"),  # Andhra Pradesh introduces new grading system to [...]
    # seed: Annamalai University professor secures Indian patent for seaweed-based water [...]
    ("f713bad2-39ab-4aeb-ba55-4914648412df", "af55f6f0-d79f-41cb-9b1e-64d0d0a5a319"): (False, "agree"),  # CUK researchers secure patent for catalyst technology [...]
    ("f713bad2-39ab-4aeb-ba55-4914648412df", "1da4f06e-0fb3-4cac-be57-d95d779618b5"): (False, "agree"),  # Three students from Azim Premji University selected [...]
    ("f713bad2-39ab-4aeb-ba55-4914648412df", "5e35547f-d652-46a9-aee3-9f773f089009"): (False, "agree"),  # TN govt forms expert committee to advise on mitigating [...]
    ("f713bad2-39ab-4aeb-ba55-4914648412df", "67a69067-e47f-45c9-a9c6-a0febe09e75f"): (False, "agree"),  # Annamalai requests the closure of 129 Tasmac retail shops
    ("f713bad2-39ab-4aeb-ba55-4914648412df", "a1ea1062-da0c-42d9-8b50-10eab549a2fb"): (False, "agree"),  # Madanapalle secures ₹1,000 crore infra project to [...]
    ("f713bad2-39ab-4aeb-ba55-4914648412df", "bdaf39b4-6fe7-4399-95d1-e27100ccada7"): (False, "agree"),  # Davangere University to introduce skill-based [...]
    ("f713bad2-39ab-4aeb-ba55-4914648412df", "cc5e7979-4c82-4e06-a7cc-61ba271614d2"): (False, "agree"),  # Tesla's Fight For 5G Tech: Automaker Wins Appeal To [...]
    ("f713bad2-39ab-4aeb-ba55-4914648412df", "da9eaaf2-e311-4741-894a-9cbc00827dc6"): (False, "agree"),  # BITS-Pilani Hyd researchers develop low-energy system [...]
    ("f713bad2-39ab-4aeb-ba55-4914648412df", "feba6359-877c-482e-939f-2a5f53ed9fb0"): (False, "agree"),  # IIT Madras develops new tech for efficient cooling of [...]
    # seed: Assam flood toll rises: 21 killed in a day; over 5.6 lakh affected across 16 [...]
    ("92763a3c-fc95-4028-8670-987a9d875a46", "086fcf0c-6dff-44b5-9b33-a0f3a9822797"): (False, "agree"),  # Heavy rain wreaks havoc across India: Death toll in [...]
    ("92763a3c-fc95-4028-8670-987a9d875a46", "50040fe7-0c1b-4a66-aa85-0b1664f0443b"): (True, "adj:tejas-said-same:high"),  # Assam Floods: Death Count Remains At 68, Over 5 Lakh [...]
    ("92763a3c-fc95-4028-8670-987a9d875a46", "6fb8d354-dcc7-4133-8570-94216b2ef47f"): (True, "adj:tejas-said-same:high"),  # Assam Floods: 10 More Deaths In 24 Hours; Over 6 Lakh [...]
    ("92763a3c-fc95-4028-8670-987a9d875a46", "ee293fc9-404f-4a4a-8274-8fb7707fbc98"): (True, "adj:tejas-said-same:high"),  # 21 Killed In 24 Hours As Flood Situation Worsens In Assam
    ("92763a3c-fc95-4028-8670-987a9d875a46", "0389a002-8109-4d6f-9acd-f7304d352ddd"): (False, "agree"),  # India launches first direct commercial freight train [...]
    ("92763a3c-fc95-4028-8670-987a9d875a46", "1c3cb159-2665-4f98-bb2a-c5a17ce576cc"): (False, "agree"),  # Early July rains caused estimated loss of Rs 170 [...]
    ("92763a3c-fc95-4028-8670-987a9d875a46", "2cb3d189-eeed-43fa-b3a7-5e0d9b82f2a8"): (False, "agree"),  # Why Assam floods: The obvious answer is Brahmaputra, [...]
    ("92763a3c-fc95-4028-8670-987a9d875a46", "2fe5a1a2-42e3-4db4-ba3a-fd16858cbec0"): (False, "agree"),  # Africans, Russians, Ukrainians among 2,089 deported [...]
    ("92763a3c-fc95-4028-8670-987a9d875a46", "83eab5d0-6e0e-4df1-8bc4-cfd82986d449"): (True, "adj:tejas-said-same:high"),  # ಅಸ್ಸಾಂ ಪ್ರವಾಹ: ಮೃತರ ಸಂಖ್ಯೆ 68ಕ್ಕೆ ಏರಿಕೆ, 4.4 ಲಕ್ಷ [...]
    ("92763a3c-fc95-4028-8670-987a9d875a46", "a44bc1a2-024b-4ae5-ad97-3e1b0a46cc9f"): (False, "agree"),  # NEET leak row puts NDA families in spotlight as [...]
    # seed: Attackers Weaponize GitHub Actions Runners to Target cPanel and WHM Servers
    ("364187f6-9c69-4e2c-ad1d-492b372f683e", "2ad98744-8bcd-4bef-b20c-d8fbb75c2549"): (False, "agree"),  # SleeperGem Uses Three Malicious RubyGems Packages to [...]
    ("364187f6-9c69-4e2c-ad1d-492b372f683e", "599fbc6f-0e93-4c2a-8e5e-fc89da358008"): (False, "agree"),  # Two Compromised joyfill npm Packages Run RAT When [...]
    ("364187f6-9c69-4e2c-ad1d-492b372f683e", "175335bc-cef4-4ca6-9703-dbc5e4e6a386"): (False, "agree"),  # Cl0p Affiliates Target Internet-Exposed PTC Windchill [...]
    ("364187f6-9c69-4e2c-ad1d-492b372f683e", "1afc51b5-a00d-4e47-8fee-f28131afaa35"): (False, "agree"),  # Hackers hijack hotel Wi-Fi DNS to steal Microsoft 365 [...]
    ("364187f6-9c69-4e2c-ad1d-492b372f683e", "1ec0732d-2cb3-4c34-8d4c-0fa8c39c95e2"): (False, "agree"),  # Critical ServiceNow AI Platform Flaw Exploited for [...]
    ("364187f6-9c69-4e2c-ad1d-492b372f683e", "3c91d7ae-a3c1-42ff-815a-1b8e637c45b6"): (False, "agree"),  # Amazon Links Debug and Chalk npm Hijack to North [...]
    ("364187f6-9c69-4e2c-ad1d-492b372f683e", "4db42e94-515f-4631-b0bd-73dce8eedf2f"): (False, "agree"),  # GitHub Adds 3-Day Dependabot Cooldown to Limit [...]
    ("364187f6-9c69-4e2c-ad1d-492b372f683e", "4ee8fc82-3d73-41c1-92db-8da1c583f95b"): (False, "agree"),  # FakeGit campaign uses 7,600 GitHub repos to push [...]
    ("364187f6-9c69-4e2c-ad1d-492b372f683e", "9815329b-886a-4f08-a7c8-a9524b9448e8"): (False, "agree"),  # Bing Images Flaws Let Crafted SVGs Run Commands as [...]
    ("364187f6-9c69-4e2c-ad1d-492b372f683e", "b971629d-ae87-4cdd-9600-d02ce912084d"): (False, "agree"),  # N-able Says Attackers Take Over N-central Servers [...]
    # seed: BMC plans software-based random transfers for engineers amid graft allegations
    ("1d36ca66-601b-44e4-a5ef-1b0892cf9f8d", "0599ca3f-b3d2-459a-9b06-4dbd7580270a"): (False, "agree"),  # टीम इंडिया के असिस्टेंट कोच ने अचानक दिया इस्तीफा
    ("1d36ca66-601b-44e4-a5ef-1b0892cf9f8d", "0d388c5e-75d0-47da-a528-239ba1d9652d"): (False, "agree"),  # Delhi saw 11 nights this summer when minimum was above [...]
    ("1d36ca66-601b-44e4-a5ef-1b0892cf9f8d", "150ece1c-ad5f-4b4b-ad46-3f11f8c918d0"): (False, "agree"),  # Maharashtra CET Cell files complaint over viral exam [...]
    ("1d36ca66-601b-44e4-a5ef-1b0892cf9f8d", "1d31cae4-ca28-4f2e-9b79-d5bb75241bec"): (False, "agree"),  # 28,832 apply for Plus One school, course transfers
    ("1d36ca66-601b-44e4-a5ef-1b0892cf9f8d", "22d4d240-0109-463f-9c52-05919856cf63"): (False, "agree"),  # C’garh MGNREGA graft case: Chargesheet filed against 8 [...]
    ("1d36ca66-601b-44e4-a5ef-1b0892cf9f8d", "24e1f2e6-469a-4d76-8ed7-68089c682a78"): (False, "agree"),  # Centre plans performance-based safety norms for two-wheelers
    ("1d36ca66-601b-44e4-a5ef-1b0892cf9f8d", "4e907b42-fd29-4ae0-9559-12ddd04d7b42"): (False, "agree"),  # BMC panel clears SevenHills Hospital lease to Capri [...]
    ("1d36ca66-601b-44e4-a5ef-1b0892cf9f8d", "619390ad-dc87-4503-b764-7a33003d16f2"): (False, "agree"),  # BMC plans AI-powered diagnostics, smart OPDs, and [...]
    ("1d36ca66-601b-44e4-a5ef-1b0892cf9f8d", "8b00529e-73c7-42e9-9cd4-d94559a45b43"): (False, "agree"),  # Students blocking medical seats to face two-year ban [...]
    ("1d36ca66-601b-44e4-a5ef-1b0892cf9f8d", "93b35c52-2643-445d-910f-91988a52fec0"): (False, "agree"),  # BMC seeks approval for appointing consultant to carry [...]
    # seed: Big relief for CJP protesters: Delhi govt drops cases, but there's a key condition
    ("22e469d5-e427-4fc5-a4d4-4237c6779b48", "a60062d0-af2f-4d7b-98b0-070c9d7cf47a"): (True, "agree"),  # No further action against CJP protesters, Delhi govt [...]
    ("22e469d5-e427-4fc5-a4d4-4237c6779b48", "da4bbd00-ed2b-4185-8213-b346225dfa1f"): (True, "agree"),  # No action against CJP protesters: Delhi government
    ("22e469d5-e427-4fc5-a4d4-4237c6779b48", "016fd980-a32e-45f6-aa9f-606abe52332a"): (False, "agree"),  # Avoid central Delhi till end of Parliament session, [...]
    ("22e469d5-e427-4fc5-a4d4-4237c6779b48", "02bd987a-8680-4d3d-8e26-8576f568784f"): (False, "agree"),  # இந்தியாவையும் உலகையும் திரும்பிப் பார்க்க வைத்த சிஜேபி [...]
    ("22e469d5-e427-4fc5-a4d4-4237c6779b48", "08ab45b9-c8a1-4810-a677-8714e7dfe873"): (False, "agree"),  # Double whammy for traffic in Delhi-NCR as youth, [...]
    ("22e469d5-e427-4fc5-a4d4-4237c6779b48", "095ebf63-8da9-478b-a6cd-47887894980e"): (False, "agree"),  # Saurav Das defends viral party, dancing videos amid [...]
    ("22e469d5-e427-4fc5-a4d4-4237c6779b48", "0960b22b-ef41-43f0-bc48-808924331e04"): (False, "agree"),  # Mamaearth's Ghazal Alagh backs CJP protest, urges [...]
    ("22e469d5-e427-4fc5-a4d4-4237c6779b48", "2cb3d189-eeed-43fa-b3a7-5e0d9b82f2a8"): (False, "agree"),  # Why Assam floods: The obvious answer is Brahmaputra, [...]
    ("22e469d5-e427-4fc5-a4d4-4237c6779b48", "98a4af8c-cafb-439c-a5ec-7f4f9d5a67a9"): (False, "agree"),  # After Bihar, Assam Drops Cases, Assures No Action [...]
    ("22e469d5-e427-4fc5-a4d4-4237c6779b48", "a3bdd07c-875b-47f2-b3d2-2c95e7f85dff"): (False, "agree"),  # CJP protest: 6 FIRs by Delhi Police over violence; [...]
    # seed: CFTRI, NABARD join hands to bolster agro-food processing in Kalyana Karnataka
    ("6c429155-6a20-415e-986f-0403927cd848", "39dcadfe-ba4d-4408-809b-badc9e4d4127"): (False, "agree"),  # Mysuru: CFTRI shares best practices on Coffee quality [...]
    ("6c429155-6a20-415e-986f-0403927cd848", "4f17c2b4-3ea0-4023-b170-1aa72d5b7332"): (False, "agree"),  # FDPPI, MYRA join hands to strengthen data protection [...]
    ("6c429155-6a20-415e-986f-0403927cd848", "05138771-bed2-4948-bf23-1591e1734fe2"): (False, "agree"),  # Khan Academy to provide innovative training to [...]
    ("6c429155-6a20-415e-986f-0403927cd848", "0fe74f8e-9e27-4757-9666-81634c0faa89"): (False, "agree"),  # Food kept near drains, use of broken eggs among food [...]
    ("6c429155-6a20-415e-986f-0403927cd848", "259a4cbf-e563-4c00-9a59-8b27d2b1ccbf"): (False, "agree"),  # Drug-free Karnataka by 2028: Mysuru youth urged to [...]
    ("6c429155-6a20-415e-986f-0403927cd848", "4122c08f-0946-46b6-9db1-25ad4362a12a"): (False, "agree"),  # Only 28% rural households saw incomes rise over a [...]
    ("6c429155-6a20-415e-986f-0403927cd848", "5e665adc-3204-4232-92eb-613227c66242"): (False, "agree"),  # NABARD signs MoU with MAHAPREIT to promote green infra [...]
    ("6c429155-6a20-415e-986f-0403927cd848", "67a1867c-260d-40d1-8d84-3dc69a34bd6e"): (False, "agree"),  # NaBFID and UPICON partner to provide advisory services [...]
    ("6c429155-6a20-415e-986f-0403927cd848", "6aa9846f-38d9-42ff-939d-ea7ba59ccaae"): (False, "agree"),  # A.P. govt. launches action plan to check fodder [...]
    ("6c429155-6a20-415e-986f-0403927cd848", "9a77d7c2-217a-44d8-92c2-4cfda5cc819e"): (False, "agree"),  # Anantapur set to become garbage-free with new waste [...]
    # seed: CJP protest triggers digital crackdown: Delhi Police issues notices over [...]
    ("49f9534c-2b60-4429-bc7f-9ef4facb1d60", "2cd84150-b671-485e-a620-8dd2bea48764"): (False, "agree"),  # Delhi Police step up drive to take down posts on protests
    ("49f9534c-2b60-4429-bc7f-9ef4facb1d60", "016fd980-a32e-45f6-aa9f-606abe52332a"): (False, "agree"),  # Avoid central Delhi till end of Parliament session, [...]
    ("49f9534c-2b60-4429-bc7f-9ef4facb1d60", "02bd987a-8680-4d3d-8e26-8576f568784f"): (False, "agree"),  # இந்தியாவையும் உலகையும் திரும்பிப் பார்க்க வைத்த சிஜேபி [...]
    ("49f9534c-2b60-4429-bc7f-9ef4facb1d60", "08ab45b9-c8a1-4810-a677-8714e7dfe873"): (False, "agree"),  # Double whammy for traffic in Delhi-NCR as youth, [...]
    ("49f9534c-2b60-4429-bc7f-9ef4facb1d60", "095ebf63-8da9-478b-a6cd-47887894980e"): (False, "agree"),  # Saurav Das defends viral party, dancing videos amid [...]
    ("49f9534c-2b60-4429-bc7f-9ef4facb1d60", "0960b22b-ef41-43f0-bc48-808924331e04"): (False, "agree"),  # Mamaearth's Ghazal Alagh backs CJP protest, urges [...]
    ("49f9534c-2b60-4429-bc7f-9ef4facb1d60", "0d09c82b-0e49-4418-bdd3-f4cca0990b08"): (False, "agree"),  # Pawar, Kejriwal, other Opposition leaders visit Jantar [...]
    ("49f9534c-2b60-4429-bc7f-9ef4facb1d60", "14152285-5037-4449-b54a-06f5c7848696"): (False, "agree"),  # Delhi protest: M.K. Raghavan seeks judicial probe into [...]
    ("49f9534c-2b60-4429-bc7f-9ef4facb1d60", "3fe63bc9-4a91-4fbc-bc18-5ec3e6dfbf5b"): (False, "agree"),  # SC issues contempt notices to 15 state chief secretaries
    ("49f9534c-2b60-4429-bc7f-9ef4facb1d60", "8d599b1e-3d70-4660-befb-d1abeff1f411"): (False, "agree"),  # 'If someone dies .... ': Police probes alleged chats [...]
    # seed: CWG 2026: ಜಾವೆಲಿನ್ ಥ್ರೋ ಫೈನಲ್​ ಸುತ್ತಿಗೆ ಅರ್ಹತೆ ಪಡೆದ ಮೂವರು ಭಾರತೀಯರು
    ("99e36320-39aa-458c-bd2c-4f9bff8df1bd", "0678f489-ebf0-4d0e-af4e-2e0ea35706bc"): (False, "agree"),  # CWG 2026: ಈ ಕ್ರೀಡೆಗಳಲ್ಲಿ ಭಾರತ ಒಂದೇ ಒಂದು ಪದಕ ಗೆಲ್ಲಲಿಲ್ಲ..!
    ("99e36320-39aa-458c-bd2c-4f9bff8df1bd", "06b69d46-bad2-41e5-9512-767a5bc8890e"): (True, "adj:vijay-said-same:high"),  # भारत की 'जेवलिन तिकड़ी' फाइनल में, नीरज चोपड़ा पदक से [...]
    ("99e36320-39aa-458c-bd2c-4f9bff8df1bd", "1e29c0e0-91ca-4da3-a5a6-69584ddbf088"): (False, "agree"),  # Sarvesh Kushare Scripts History With Silver In Men's [...]
    ("99e36320-39aa-458c-bd2c-4f9bff8df1bd", "26b62d29-ce5e-4db8-9a2a-c12159f1ff8e"): (False, "agree"),  # CWG 2026: बुडिगिना और इमाम अली ने पैरा तैराकी में जगाई [...]
    ("99e36320-39aa-458c-bd2c-4f9bff8df1bd", "2c2f8745-82bb-4fc4-94bc-a27722847c02"): (False, "agree"),  # CWG 2026: How India Can Add 6 More Medals To Official [...]
    ("99e36320-39aa-458c-bd2c-4f9bff8df1bd", "438256ec-f411-4817-b83e-cf73355c282e"): (False, "agree"),  # ಆಹಾರ ವಿಷಯುಕ್ತಗೊಂಡಿದ್ದರಿಂದ ಚಿನ್ನದ ಪದಕ ಕೈತಪ್ಪಿತು: ಸೆಲ್ವ ಪ್ರಭು
    ("99e36320-39aa-458c-bd2c-4f9bff8df1bd", "47d81200-f3a0-4ef8-a0f6-9dca732c1814"): (False, "agree"),  # ಲಾಂಗ್‌ಜಂಪ್‌: ಶ್ರೀಶಂಕರ್‌, ಲೋಕೇಶ್‌ ಫೈನಲ್‌ಗೆ
    ("99e36320-39aa-458c-bd2c-4f9bff8df1bd", "6e37129e-098b-4c20-aecb-0db1531b6852"): (False, "agree"),  # Shoulder surgery, 7 months out, one throw: How Yash [...]
    ("99e36320-39aa-458c-bd2c-4f9bff8df1bd", "6ef8c46a-f9e8-46fe-9b4f-269caf25bb08"): (False, "agree"),  # Indian Weightlifting Coach Praises Government Support [...]
    ("99e36320-39aa-458c-bd2c-4f9bff8df1bd", "856727fc-c685-4604-a7ab-1fcf154d3bf0"): (False, "agree"),  # ಗುರಿಂದರ್‌ವೀರ್ ಸಿಂಗ್ ಕಾಮನ್‌ವೆಲ್ತ್ ಗೇಮ್ಸ್‌ನಲ್ಲಿ ನಿರಾಸೆ [...]
    # seed: Cauvery water received by T.N. in July hits 50-year low
    ("28f88ec4-8960-46b8-b489-303eb7a3bc7f", "e0fbf2ae-74eb-4422-9f1c-6f3f4a53b57c"): (False, "agree"),  # Cauvery water from Kabini to reach Tamil Nadu soon
    ("28f88ec4-8960-46b8-b489-303eb7a3bc7f", "252db0aa-2a51-4620-8475-73ad6af3f296"): (False, "agree"),  # Tamil Nadu terms ‘insufficient’ the release of water [...]
    ("28f88ec4-8960-46b8-b489-303eb7a3bc7f", "4c85c58d-7437-448c-88ea-d99e78e01ee4"): (False, "agree"),  # 72,627 applications received for MBBS, BDS courses
    ("28f88ec4-8960-46b8-b489-303eb7a3bc7f", "5467fc4d-5001-474e-88b3-23f1f6539d93"): (False, "agree"),  # Tamil Nadu CM Vijay writes to PM Modi over Mekedatu project
    ("28f88ec4-8960-46b8-b489-303eb7a3bc7f", "7c3dde04-27a9-455f-9dd0-547a5a345444"): (False, "agree"),  # Water supply disruption in Benglauru on July 31
    ("28f88ec4-8960-46b8-b489-303eb7a3bc7f", "95423eae-2c75-43fe-92b7-202a3c96b23d"): (False, "agree"),  # Water levels in Krishna rise as Maharashtra and [...]
    ("28f88ec4-8960-46b8-b489-303eb7a3bc7f", "957da538-9385-4cb6-8cd5-366d5416999d"): (False, "agree"),  # ಮೇಕೆದಾಟು ಯೋಜನೆ: ಕರ್ನಾಟಕಕ್ಕೆ ತಮಿಳುನಾಡಿನ ಒಪ್ಪಿಗೆ [...]
    ("28f88ec4-8960-46b8-b489-303eb7a3bc7f", "b6c8e960-e86a-46cb-ba4d-ef1f0851391d"): (False, "agree"),  # Over 11,000 applications received for 7,680 affordable [...]
    ("28f88ec4-8960-46b8-b489-303eb7a3bc7f", "b9bc5e2b-524d-4e1f-89dc-b40b6b64cba9"): (False, "agree"),  # Ambedkar’s photo should be displayed prominently at [...]
    ("28f88ec4-8960-46b8-b489-303eb7a3bc7f", "bb81b435-d11e-43d7-9418-17de23e30410"): (False, "agree"),  # Mekedatu: Centre cites SC order to say Karnataka need [...]
    # seed: Chick-fil-A discloses data breach after credential stuffing attacks
    ("b20111bc-8dee-4c4d-9cf3-71d2b584184a", "32998199-5021-4dac-8480-c7099717e0ed"): (False, "agree"),  # TELESHIM Abuses Telegram for C2 in Attacks Against [...]
    ("b20111bc-8dee-4c4d-9cf3-71d2b584184a", "051e7805-4725-4068-8d1b-7465c701c9ce"): (False, "agree"),  # UAC-0145 Uses ClickFix CAPTCHAs to Infect Ukrainian [...]
    ("b20111bc-8dee-4c4d-9cf3-71d2b584184a", "488d279f-5dcf-4b46-a1e6-c33df9061395"): (False, "agree"),  # Exposed Server Reveals AI-Assisted Phishing Toolkit [...]
    ("b20111bc-8dee-4c4d-9cf3-71d2b584184a", "5e990156-5783-48e2-b29d-408b5eff814b"): (False, "agree"),  # Comedian Pranit More breaks down on comeback show [...]
    ("b20111bc-8dee-4c4d-9cf3-71d2b584184a", "7b51441b-900e-46b6-bcd2-c1bf415b7f6a"): (False, "agree"),  # New Agent Data Injection Attack Can Make AI Agents [...]
    ("b20111bc-8dee-4c4d-9cf3-71d2b584184a", "8fbe3d5e-7298-4452-82f1-495b59c0acbd"): (False, "agree"),  # SonicWall SMA Zero-Days Exploited Before Disclosure to [...]
    ("b20111bc-8dee-4c4d-9cf3-71d2b584184a", "db4cf8fa-d1e1-4230-9276-2b1488cce7b7"): (False, "agree"),  # Open-Source Android AI Agents Could Let Invisible [...]
    # seed: Claude Cowork Flaw Could Let AI Agent Escape Its VM and Access Mac Files
    ("e1de8d64-80e3-4f02-b2a9-9320012084e3", "0d2c664d-d04e-4f49-82f6-59fb40e745fd"): (False, "agree"),  # Elon Musk takes ‘crusade’ for Armie Hammer film to [...]
    ("e1de8d64-80e3-4f02-b2a9-9320012084e3", "18247736-5e30-4663-8f9d-23bb0ce38634"): (False, "agree"),  # 1700 रुपये दें और घर ले आएं iPhone, ऐपल लेकर आया अनोखा प्लान
    ("e1de8d64-80e3-4f02-b2a9-9320012084e3", "19bb4fec-699d-4683-8d4d-2f4558b8f44e"): (False, "agree"),  # ChatGPT AgentForger Flaw Could Deploy Rogue Workspace [...]
    ("e1de8d64-80e3-4f02-b2a9-9320012084e3", "1ec0732d-2cb3-4c34-8d4c-0fa8c39c95e2"): (False, "agree"),  # Critical ServiceNow AI Platform Flaw Exploited for [...]
    ("e1de8d64-80e3-4f02-b2a9-9320012084e3", "21441549-5fc1-440a-babb-2956e1675020"): (False, "agree"),  # Critical Rails Flaw Could Let Unauthenticated [...]
    ("e1de8d64-80e3-4f02-b2a9-9320012084e3", "2bc66433-e031-4252-b4fb-eea69f454c54"): (False, "agree"),  # Adobe Acrobat Extension Flaw Let Malicious Sites Read [...]
    ("e1de8d64-80e3-4f02-b2a9-9320012084e3", "345d32a3-0303-4c3b-bc6d-dfee5d75f9d4"): (False, "agree"),  # Good News For iPhone Users: Apple To Launch 'Upgrade' [...]
    ("e1de8d64-80e3-4f02-b2a9-9320012084e3", "39c09b09-4289-44f6-9948-cc84de2ee340"): (False, "agree"),  # Chennai will need second airport within 5-10 years, [...]
    ("e1de8d64-80e3-4f02-b2a9-9320012084e3", "39e2fe27-aeb9-4bc5-b70d-8085d53549ad"): (False, "agree"),  # As users' private chats with Claude appear on Google, [...]
    ("e1de8d64-80e3-4f02-b2a9-9320012084e3", "4403cdb6-7a32-48a1-84e9-b5898f3fdf00"): (False, "agree"),  # n8n Sandbox Escape Lets Workflow Editors Run OS [...]
    # seed: Critical ServiceNow AI Platform Flaw Exploited for Unauthenticated Code Execution
    ("1ec0732d-2cb3-4c34-8d4c-0fa8c39c95e2", "3e8757a6-fadc-40a2-a857-9ba03ed7da81"): (False, "agree"),  # Critical SharePoint RCE CVE-2026-50522 Under Active [...]
    ("1ec0732d-2cb3-4c34-8d4c-0fa8c39c95e2", "053275df-80da-4cb4-9201-cdbbb6e8a436"): (False, "agree"),  # GitHub Cuts Public Bug Bounty Payouts, Moves Top [...]
    ("1ec0732d-2cb3-4c34-8d4c-0fa8c39c95e2", "175335bc-cef4-4ca6-9703-dbc5e4e6a386"): (False, "agree"),  # Cl0p Affiliates Target Internet-Exposed PTC Windchill [...]
    ("1ec0732d-2cb3-4c34-8d4c-0fa8c39c95e2", "1e21dcf0-042f-44d3-9798-3f809a9b36fd"): (False, "agree"),  # WordPress wp2shell Exploitation Grows as Public [...]
    ("1ec0732d-2cb3-4c34-8d4c-0fa8c39c95e2", "21441549-5fc1-440a-babb-2956e1675020"): (False, "agree"),  # Critical Rails Flaw Could Let Unauthenticated [...]
    ("1ec0732d-2cb3-4c34-8d4c-0fa8c39c95e2", "2bc66433-e031-4252-b4fb-eea69f454c54"): (False, "agree"),  # Adobe Acrobat Extension Flaw Let Malicious Sites Read [...]
    ("1ec0732d-2cb3-4c34-8d4c-0fa8c39c95e2", "4403cdb6-7a32-48a1-84e9-b5898f3fdf00"): (False, "agree"),  # n8n Sandbox Escape Lets Workflow Editors Run OS [...]
    ("1ec0732d-2cb3-4c34-8d4c-0fa8c39c95e2", "50480718-6376-428e-810c-f70509d62d34"): (False, "agree"),  # Three Critical VMware Flaws Allow Auth Bypass, Code [...]
    ("1ec0732d-2cb3-4c34-8d4c-0fa8c39c95e2", "56147b89-91b9-422f-b313-896a8ef0386f"): (False, "agree"),  # New ENCFORGE Ransomware Targets AI Model Files in [...]
    ("1ec0732d-2cb3-4c34-8d4c-0fa8c39c95e2", "aa16aa92-60b7-4af1-a6af-56330b2d5bd3"): (False, "agree"),  # Zoom Patches Critical Windows Flaw That Could Enable [...]
    # seed: Cummins, Hazlewood, Lyon return to face Bangladesh
    ("9322e0df-58b6-4167-8447-7acc56c9567e", "9a921dd9-9559-401f-bd91-c376b1c65e1d"): (False, "agree"),  # 'Invigorated' Smith remains vital for uncertain [...]
    ("9322e0df-58b6-4167-8447-7acc56c9567e", "e50c4158-db39-458d-a845-baf1b9e97a17"): (False, "agree"),  # Hazlewood: I'd love to play more with Scotty Boland
    ("9322e0df-58b6-4167-8447-7acc56c9567e", "0b14d6af-a363-49bb-8e8b-d80077b50e68"): (False, "agree"),  # Key on Stokes Ashes return: 'Anything is possible'
    ("9322e0df-58b6-4167-8447-7acc56c9567e", "3756e387-78e2-4dba-a5f9-f49bdb6d78c5"): (False, "agree"),  # Litton Das named Bangladesh's new ODI captain
    ("9322e0df-58b6-4167-8447-7acc56c9567e", "40257fc9-b118-485b-9e22-346eeecad415"): (False, "agree"),  # Cox, Holland lead Leicestershire to thumping win over [...]
    ("9322e0df-58b6-4167-8447-7acc56c9567e", "4d130f4e-610b-4684-8907-d16949ee7803"): (False, "agree"),  # Rahmat Shah leads Afghanistan in five-match ODI series [...]
    ("9322e0df-58b6-4167-8447-7acc56c9567e", "a9376a9a-d41a-4a55-af5d-67cffd9355e8"): (False, "agree"),  # Gaikwad to lead West Zone in 2026-27 domestic season- [...]
    ("9322e0df-58b6-4167-8447-7acc56c9567e", "aa6a75fe-a78e-4066-87b8-11afcf46b688"): (False, "agree"),  # Konstas, Kellaway, Patterson named in CA XI to face [...]
    ("9322e0df-58b6-4167-8447-7acc56c9567e", "dad2906e-0889-40b8-9ca5-4259ec6cdbdd"): (False, "agree"),  # Gritty Salt digs deep as Welsh Fire edge low-scoring tussle
    ("9322e0df-58b6-4167-8447-7acc56c9567e", "eaa1d134-d3b4-4b43-9a9d-04fd6a2f1b43"): (False, "agree"),  # Unchanged Zimbabwe put Bangladesh in to bat
    # seed: Damietta port attack: Egypt rules out accident, says drone strike caused fire [...]
    ("59aea7fc-f3b1-48c2-926f-fe31c3fe8643", "0293868e-c711-474a-9b55-0ece6b3d6832"): (False, "agree"),  # Iran पर हमलों के बाद Trump ने दिए सख्त संकेत!
    ("59aea7fc-f3b1-48c2-926f-fe31c3fe8643", "18a9fd7a-fbd3-432b-b315-bfae6dbc2f3c"): (False, "agree"),  # हूती अटैक से धधक उठे सऊदी के दो ऑयल टैंकर, लाल सागर [...]
    ("59aea7fc-f3b1-48c2-926f-fe31c3fe8643", "25849e53-16df-438f-9085-a651691654c0"): (False, "agree"),  # Over-speeding caused 82,124 road accidents in 2025: Gadkari
    ("59aea7fc-f3b1-48c2-926f-fe31c3fe8643", "47754dc9-b5c3-4979-bfb3-6d8b261fe6c7"): (False, "agree"),  # Another tanker attacked in Strait of Hormuz as US [...]
    ("59aea7fc-f3b1-48c2-926f-fe31c3fe8643", "4bb88ba1-c572-4dd1-bf4c-f0fab1b3182d"): (False, "agree"),  # ಇರಾನ್‌ ಮೇಲೆ ಅಮೆರಿಕ ಮತ್ತೆ ದಾಳಿ
    ("59aea7fc-f3b1-48c2-926f-fe31c3fe8643", "4cb476d4-ee1a-46cb-899d-97c041b11dc6"): (False, "agree"),  # Merchant vessel with 4 Indians struck at Ukraine’s [...]
    ("59aea7fc-f3b1-48c2-926f-fe31c3fe8643", "68c19336-cb65-4295-ad1f-7b10c79c51e0"): (False, "agree"),  # Terrorist kill J&K cop in Anantnag market, first [...]
    ("59aea7fc-f3b1-48c2-926f-fe31c3fe8643", "6f8a6121-4d81-44a2-851c-7048df73bfd8"): (False, "agree"),  # Upbound says hack caused $13 million in fraudulent [...]
    ("59aea7fc-f3b1-48c2-926f-fe31c3fe8643", "797a24c0-1f21-4f69-96c8-c6d91502c0ee"): (False, "agree"),  # Middle East जंग के बीच खुला दूसरा वॉर फ्रंट!
    ("59aea7fc-f3b1-48c2-926f-fe31c3fe8643", "7ce9631e-1da0-49bf-992f-306c12ae86c4"): (False, "agree"),  # Brent crude tops $92, WTI above $85 as Hormuz tensions [...]
    # seed: Data centre row: Left leaders detained en route to Tarluvada
    ("ae89f475-48b9-44f0-bf0e-0f84b98ed2de", "5eac49bd-90a0-4d7c-82b1-4e4757ab9999"): (False, "agree"),  # CITU holds bike rally to mobilise workers for protest [...]
    ("ae89f475-48b9-44f0-bf0e-0f84b98ed2de", "10ceb18a-da14-42d3-a474-518fea6ee133"): (False, "agree"),  # Political leaders urge Centre to approve metro rail [...]
    ("ae89f475-48b9-44f0-bf0e-0f84b98ed2de", "1d69904f-cf70-45ef-99d0-0e4b2c958645"): (False, "agree"),  # India's data centre capacity may reach 3-3.6 GW by [...]
    ("ae89f475-48b9-44f0-bf0e-0f84b98ed2de", "255ae011-8912-40bc-82e3-86206b27bc0a"): (False, "agree"),  # Gaur kills 68-year-old at Kulathupuzha in Kerala
    ("ae89f475-48b9-44f0-bf0e-0f84b98ed2de", "27d3f763-c105-4130-8d52-a1dbd6e19144"): (False, "agree"),  # Lodha Developers to monetise 150 acres at data centre [...]
    ("ae89f475-48b9-44f0-bf0e-0f84b98ed2de", "35d294b4-e274-4f46-9416-99fc7eeb402c"): (False, "agree"),  # Farmers breach Baldota factory premises during protest [...]
    ("ae89f475-48b9-44f0-bf0e-0f84b98ed2de", "3f9298cc-1937-43b0-8ce9-ddcbbbdfcb7f"): (False, "agree"),  # CITU call for a halt to evictions of street vendors in [...]
    ("ae89f475-48b9-44f0-bf0e-0f84b98ed2de", "52b273c9-5f4e-44a8-bf58-c88fb54254b4"): (False, "agree"),  # AI Data Centre to consume 26.3 GW electricity by FY32: [...]
    ("ae89f475-48b9-44f0-bf0e-0f84b98ed2de", "84e73830-0753-46ac-8e1b-c172cd4cc3ac"): (False, "agree"),  # Cong. stages protest in Srikakulam over India-U.S. farm deal
    ("ae89f475-48b9-44f0-bf0e-0f84b98ed2de", "8cee71f4-a664-461c-be74-13e0fb8f8532"): (False, "agree"),  # Rahul, Priyanka, Akhilesh detained during protest [...]
    # seed: Delhi weather: Rain brings relief from humidity, IMD forecasts more showers [...]
    ("ef56360c-35d8-41dd-9f8d-1e9848565a07", "c7060901-cc08-4bd3-8742-25c3ee17cff3"): (True, "agree"),  # Rain lashes Delhi, Noida; IMD issues 'orange' alert [...]
    ("ef56360c-35d8-41dd-9f8d-1e9848565a07", "03473938-d3dd-4e6d-b6b2-2450c3cad53a"): (False, "agree"),  # 2020 Delhi riots: Court reserves order against Tahir [...]
    ("ef56360c-35d8-41dd-9f8d-1e9848565a07", "04204680-bf39-4fbf-93cf-2519299b6ad5"): (True, "adj:tejas-said-same:medium"),  # Delhi rains: Airport issues advisory as IMD forecasts [...]
    ("ef56360c-35d8-41dd-9f8d-1e9848565a07", "071bd286-8d5c-4601-ac82-5ce17bef7142"): (False, "agree"),  # ‘Integral part of society, shouldn't be ostracised’: [...]
    ("ef56360c-35d8-41dd-9f8d-1e9848565a07", "08f815b9-6d4d-4d1e-a568-9299fa9eddba"): (False, "agree"),  # CJI on police excess, pellet gun claims and message [...]
    ("ef56360c-35d8-41dd-9f8d-1e9848565a07", "097d4f9b-d726-47a2-8490-6c5efaa82488"): (False, "agree"),  # Weather Update: नोएडा-गाजियाबाद समेत दिल्ली-NCR में [...]
    ("ef56360c-35d8-41dd-9f8d-1e9848565a07", "0d8821f4-4f3c-42a7-90c1-587edffa1899"): (False, "agree"),  # Sikkim NHPC tunnel collapse: 12 dead, up to 15 workers [...]
    ("ef56360c-35d8-41dd-9f8d-1e9848565a07", "195e4eee-f969-4b74-8026-8577d4b2cc1c"): (False, "agree"),  # Delhi Rains: Indira Gandhi Airport issues passenger [...]
    ("ef56360c-35d8-41dd-9f8d-1e9848565a07", "48132067-4fde-4640-9987-17d6074ee30e"): (False, "agree"),  # Heavy rain likely in Delhi for next two days, battered [...]
    ("ef56360c-35d8-41dd-9f8d-1e9848565a07", "821a96e7-9f27-4bc1-862a-65bf71c5b92a"): (True, "adj:vijay-said-same:medium"),  # Rain lashes Delhi, IMD issues orange alert across city
    # seed: Drought-like scenario in 457 Telangana mandals; El Nino keeps water levels in [...]
    ("4f0b8706-7777-4bda-a543-eadf1ec16af1", "154e35a6-7182-42cd-95df-4d7650c12ff2"): (False, "agree"),  # Hydel generation taken up at Jurala with flood from [...]
    ("4f0b8706-7777-4bda-a543-eadf1ec16af1", "166893a6-da34-4494-b9a5-2fe5388e6bd4"): (False, "agree"),  # ರಸ್ತೆ ನಿರ್ಮಾಣಕ್ಕೆ ಭೂಸ್ವಾಧೀನ, ಎಕರೆಗೆ ₹2.60 ಕೋಟಿ ಪರಿಹಾರ [...]
    ("4f0b8706-7777-4bda-a543-eadf1ec16af1", "268794ed-e6d0-4188-b4db-795ed8a1310b"): (False, "agree"),  # 13 boats seized for illegal sand mining in Rajamahendravaram
    ("4f0b8706-7777-4bda-a543-eadf1ec16af1", "28f88ec4-8960-46b8-b489-303eb7a3bc7f"): (False, "agree"),  # Cauvery water received by T.N. in July hits 50-year low
    ("4f0b8706-7777-4bda-a543-eadf1ec16af1", "3010282c-b161-4565-94e1-d2e3f912d64f"): (False, "agree"),  # Eviction looms over 258 shop owners at Vijayawada’s [...]
    ("4f0b8706-7777-4bda-a543-eadf1ec16af1", "48f52b8e-5613-4ba5-ae36-7886e4acf0db"): (False, "agree"),  # BJP leaders visit drought-hit areas in Shivamogga
    ("4f0b8706-7777-4bda-a543-eadf1ec16af1", "52d00871-0c39-4285-8343-115df6da552b"): (False, "agree"),  # El Nino impact likely to intensify in coming months: [...]
    ("4f0b8706-7777-4bda-a543-eadf1ec16af1", "5794e914-b5da-4bff-8e59-581f4825a7ff"): (False, "agree"),  # Amazon fires dropped to record low in 2025 after 2024 [...]
    ("4f0b8706-7777-4bda-a543-eadf1ec16af1", "5d874531-c3d9-4d97-946a-0ca15a33b806"): (False, "agree"),  # Telangana steps up El Nino preparedness, urges crop [...]
    ("4f0b8706-7777-4bda-a543-eadf1ec16af1", "667d8afb-9b1c-4767-b7ef-b7788275b3ed"): (False, "agree"),  # As Pampa runs shallow, cherished tradition of Arnmula [...]
    # seed: Dysphoria IoT Botnet Adds Blockchain C2 and Victim Relays After JackSkid Disruption
    ("211f67a7-3da7-41e1-b844-6abb1fb566b8", "033f89bf-3559-4c54-99f4-356c70678d4c"): (False, "agree"),  # TuxBot v3 Evolution Shows Signs of LLM-Assisted IoT [...]
    ("211f67a7-3da7-41e1-b844-6abb1fb566b8", "7b806acf-535f-46de-a278-285a8c4340dd"): (False, "agree"),  # New NadMesh Botnet Hunts Exposed AI Services for Cloud [...]
    ("211f67a7-3da7-41e1-b844-6abb1fb566b8", "30eadccb-be3a-42ad-801c-6a5ac1f587d2"): (False, "agree"),  # Tengu Botnet Reboots Compromised Linux Devices When [...]
    ("211f67a7-3da7-41e1-b844-6abb1fb566b8", "4e350e5e-f913-4868-bf4e-cfa64d05b5f4"): (False, "agree"),  # Nimbus Manticore Deploys NightLedger and Turns Victim [...]
    ("211f67a7-3da7-41e1-b844-6abb1fb566b8", "7c3dde04-27a9-455f-9dd0-547a5a345444"): (False, "agree"),  # Water supply disruption in Benglauru on July 31
    ("211f67a7-3da7-41e1-b844-6abb1fb566b8", "9c3bdc4a-74cb-4138-b406-d7213e1ccc2c"): (False, "agree"),  # Coldcard Hardware Wallet Flaw Linked to $70 Million [...]
    ("211f67a7-3da7-41e1-b844-6abb1fb566b8", "aa16aa92-60b7-4af1-a6af-56330b2d5bd3"): (False, "agree"),  # Zoom Patches Critical Windows Flaw That Could Enable [...]
    ("211f67a7-3da7-41e1-b844-6abb1fb566b8", "c1390ce5-963c-44e0-bc63-350fb35dd49f"): (False, "agree"),  # Chinese Threat Actor Uses Leaked DarkSword Kit to [...]
    ("211f67a7-3da7-41e1-b844-6abb1fb566b8", "e374a6d2-12f8-4a3f-980d-56e18905eb71"): (False, "agree"),  # Gig workers’ strike cause partial disruption of services
    ("211f67a7-3da7-41e1-b844-6abb1fb566b8", "f3105e6c-7066-488e-9d7d-e523a3537820"): (False, "agree"),  # A.P. CM to launch blockchain-based land records system [...]
    # seed: ED conducts raids in ISIS-inspired 2022 Coimbatore car bomb blast case
    ("103b5245-170f-44c3-ada8-34e35b398436", "c125fc27-6cb5-4c91-bea4-f94e0ee2ea87"): (False, "agree"),  # ED raids in Bengaluru in ISIS radicalisation case
    ("103b5245-170f-44c3-ada8-34e35b398436", "2ffd11e0-b9fc-462d-abb1-b463b9480317"): (False, "agree"),  # ED raids Hyderabad, Chennai in ketamine trafficking [...]
    ("103b5245-170f-44c3-ada8-34e35b398436", "ba5695ed-021c-495e-8441-d451f86d69ab"): (False, "agree"),  # Telangana ACB raids 15 locations linked to DE of [...]
    ("103b5245-170f-44c3-ada8-34e35b398436", "04eab63d-69a8-489f-a675-128a5ef8f8d8"): (False, "agree"),  # NIA to take over Nagaland IED blast case that killed [...]
    ("103b5245-170f-44c3-ada8-34e35b398436", "0e1359ea-55d4-4c38-8616-094cfbe31293"): (False, "agree"),  # Delhi HC agrees to hear PIL seeking probe into [...]
    ("103b5245-170f-44c3-ada8-34e35b398436", "3abd8a01-a1fe-4e7b-b841-afd7e3abb5a4"): (False, "agree"),  # Only 1 active local terrorist left in J&K; hunt on for [...]
    ("103b5245-170f-44c3-ada8-34e35b398436", "7ef93a46-819e-47fd-81bf-8680c3d99185"): (False, "agree"),  # No legal aid to accused, SC orders fresh trial in [...]
    ("103b5245-170f-44c3-ada8-34e35b398436", "82a9a243-7189-44c0-9583-4c0807eb8780"): (False, "agree"),  # Umar Khalid moves High Court against bail rejection in [...]
    ("103b5245-170f-44c3-ada8-34e35b398436", "c5fd2202-c45d-4581-afb9-b9629649b541"): (False, "agree"),  # Family of four among five killed after car rams into [...]
    ("103b5245-170f-44c3-ada8-34e35b398436", "e2fecb63-d054-45f9-9f4e-d63ee0f1a1ab"): (False, "agree"),  # Bengaluru: ED uncovers $35 million crypto OTC scam; [...]
    # seed: Eight A.P. players selected for National U-19 Chess Championship
    ("148ef86d-022e-43d6-8bc2-38271ed3463e", "7f6f2dd2-7680-4774-8cbd-61496f271e75"): (False, "agree"),  # Vizag players shine at State-level carrom tournament
    ("148ef86d-022e-43d6-8bc2-38271ed3463e", "1abd27fc-1a51-454a-85b7-99af4b76cb31"): (False, "agree"),  # After Arjuna Awardee calls out Indian calendar, AICF [...]
    ("148ef86d-022e-43d6-8bc2-38271ed3463e", "1da4f06e-0fb3-4cac-be57-d95d779618b5"): (False, "agree"),  # Three students from Azim Premji University selected [...]
    ("148ef86d-022e-43d6-8bc2-38271ed3463e", "4ff212cc-d747-4e2e-8ee6-dd9fef16f47f"): (False, "agree"),  # VMRDA plans to set up organic plaza in Visakhapatnam
    ("148ef86d-022e-43d6-8bc2-38271ed3463e", "58ef0db6-a9a0-45bf-bd44-35be01710b5a"): (False, "agree"),  # Not Selected For Cricket Team, 17-Year-Old Girl Dies [...]
    ("148ef86d-022e-43d6-8bc2-38271ed3463e", "6b82590a-d301-48b0-952c-c9896309b5d4"): (False, "agree"),  # Kuldeep signs up with Yorkshire for County [...]
    ("148ef86d-022e-43d6-8bc2-38271ed3463e", "72176d6f-b692-4174-a962-1170e256b37d"): (False, "agree"),  # 21,522 candidates to appear for AP TET in Visakhapatnam
    ("148ef86d-022e-43d6-8bc2-38271ed3463e", "8a101a87-a313-4099-86ca-f4a49e2bf060"): (False, "agree"),  # Mysuru students qualify for Seoul robotic championship
    ("148ef86d-022e-43d6-8bc2-38271ed3463e", "9cd17458-532a-499e-8c5f-b0b042b4b6f2"): (False, "agree"),  # ಮಧುಗಿರಿ ಕುಂಚಿಟಿಗ ಒಕ್ಕಲಿಗ ಸಂಘಕ್ಕೆ ಪಿ.ಎನ್.ರಾಜಶೇಖರ್‌ ಪುನರಾಯ್ಕೆ
    ("148ef86d-022e-43d6-8bc2-38271ed3463e", "b6ccbacb-4078-4952-b1be-2719cc54b959"): (False, "agree"),  # Playing in ‘unsanctioned’ hockey tournaments does not [...]
    # seed: Expert panel recommends El Nino mitigation measures with ₹803 crore to [...]
    ("9d236dbc-baf4-4a48-8f5f-46bd07f77ed3", "5d874531-c3d9-4d97-946a-0ca15a33b806"): (False, "agree"),  # Telangana steps up El Nino preparedness, urges crop [...]
    ("9d236dbc-baf4-4a48-8f5f-46bd07f77ed3", "81462ac3-ca24-4cda-9447-81c9ed85ec9b"): (False, "agree"),  # Telangana preparing plans to meet El Nino affect: Bhatti
    ("9d236dbc-baf4-4a48-8f5f-46bd07f77ed3", "be750b01-7d5a-46a9-9891-492b0d24af73"): (False, "agree"),  # Telangana prepares action plan to tackle El Nino: [...]
    ("9d236dbc-baf4-4a48-8f5f-46bd07f77ed3", "0d12dad2-9695-4819-891b-c60b90414684"): (False, "agree"),  # Procedure bypassed in leasing of State Urdu Academy’s [...]
    ("9d236dbc-baf4-4a48-8f5f-46bd07f77ed3", "15ab93e0-7b2c-4431-bde3-0e89ecd36584"): (False, "agree"),  # Chittoor district implements fodder security measures [...]
    ("9d236dbc-baf4-4a48-8f5f-46bd07f77ed3", "15eb59b4-6fba-47df-984d-25bd1bd5956c"): (False, "agree"),  # Bandi challenges Revanth to back Gen Z push with [...]
    ("9d236dbc-baf4-4a48-8f5f-46bd07f77ed3", "365372c3-83e6-43c3-ab35-ebe4eda87194"): (False, "agree"),  # Nurses protest, demand withdrawal of T.N. government’s [...]
    ("9d236dbc-baf4-4a48-8f5f-46bd07f77ed3", "5e35547f-d652-46a9-aee3-9f773f089009"): (False, "agree"),  # TN govt forms expert committee to advise on mitigating [...]
    ("9d236dbc-baf4-4a48-8f5f-46bd07f77ed3", "5f5c0e00-1624-4a74-a072-d4ab678706a2"): (False, "agree"),  # Expedite water conservation under ‘Telangana [...]
    ("9d236dbc-baf4-4a48-8f5f-46bd07f77ed3", "821d4273-4144-4d81-b4aa-c4113c6427e0"): (False, "agree"),  # Naidu directs comprehensive support for farmers in [...]
    # seed: FSSAI Bans Dabur From Selling Food Products With 'Misleading' 100% Claims
    ("acd695a4-8fa3-48d8-810a-0e2b4e30980f", "76b62065-9fcf-49b1-b702-5e66b3aeefa8"): (False, "agree"),  # Which Dabur products are banned from using [...]
    ("acd695a4-8fa3-48d8-810a-0e2b4e30980f", "9faf6331-4474-44eb-8992-0bf2654343d5"): (False, "agree"),  # Mumbai's Cricket Club Of India Canteen Loses License [...]
    ("acd695a4-8fa3-48d8-810a-0e2b4e30980f", "d7faf9ff-5c3a-48e7-93e7-0945b7832cdd"): (True, "agree"),  # No '100%' Tag On Honey, Coconut Oil: Food Regulator's [...]
    ("acd695a4-8fa3-48d8-810a-0e2b4e30980f", "02d3560a-1a26-4108-9873-aedde30ae67e"): (False, "agree"),  # Sale of chicken to be suspended in Tamil Nadu from [...]
    ("acd695a4-8fa3-48d8-810a-0e2b4e30980f", "0fe74f8e-9e27-4757-9666-81634c0faa89"): (False, "agree"),  # Food kept near drains, use of broken eggs among food [...]
    ("acd695a4-8fa3-48d8-810a-0e2b4e30980f", "50dd6b2d-157d-466b-9fbd-f319295d9ffd"): (False, "agree"),  # ECB relief as last-minute Hundred deals swerve [...]
    ("acd695a4-8fa3-48d8-810a-0e2b4e30980f", "58cceefd-8058-4b43-a518-20d741edd0c3"): (False, "agree"),  # Minister accuses YSRCP of misleading public over [...]
    ("acd695a4-8fa3-48d8-810a-0e2b4e30980f", "bce3a1dd-a16a-4917-b604-805d32edef22"): (False, "agree"),  # FSSAI Gives Firms Like Pepsi, Red Bull, Monster 90 [...]
    ("acd695a4-8fa3-48d8-810a-0e2b4e30980f", "d4fc649f-ba3b-416a-9e25-476854bbfb94"): (False, "agree"),  # 400 kg of gutkha products seized, one held
    ("acd695a4-8fa3-48d8-810a-0e2b4e30980f", "f6f8a9e1-27e6-44a8-bd22-49633b1abb86"): (False, "agree"),  # Flavoured rum, whisky? FSSAI tightens rules for [...]
    # seed: Five SCR employees receive safety awards
    ("2b765b2b-3087-4817-ad19-6415dd67f8e4", "09c10dc6-0e43-44ef-af67-7168884ad3d3"): (False, "agree"),  # Resolve service issues of Waltair Division employees [...]
    ("2b765b2b-3087-4817-ad19-6415dd67f8e4", "16ae8966-ba1b-4f58-9408-f9b093278f0a"): (False, "agree"),  # Kochi metro Phase II: KMRL awards ₹91.6-crore contract [...]
    ("2b765b2b-3087-4817-ad19-6415dd67f8e4", "17ef2c7c-6205-4ac3-8137-c0662c017b55"): (False, "agree"),  # Hyderabad Metro Rail Additional MD calls for station- [...]
    ("2b765b2b-3087-4817-ad19-6415dd67f8e4", "1b5d79f0-b414-45a0-8d06-2d0db17944ab"): (False, "agree"),  # Malnad districts receive heavy rain
    ("2b765b2b-3087-4817-ad19-6415dd67f8e4", "34aae9d8-ad30-44c3-ab6f-54a27a7f6ba2"): (False, "agree"),  # FACT employees stage protest in Kochi
    ("2b765b2b-3087-4817-ad19-6415dd67f8e4", "3eccf89c-e5aa-454d-938c-831d83b3ee06"): (False, "agree"),  # Southern Railway begins construction of new FOBs, [...]
    ("2b765b2b-3087-4817-ad19-6415dd67f8e4", "45f4942c-8aed-4bb5-b4e1-1e09a471f053"): (False, "agree"),  # Kishan Reddy opens Komuravelli Railway station, [...]
    ("2b765b2b-3087-4817-ad19-6415dd67f8e4", "9874762f-9c33-4745-b330-89919f50ff25"): (False, "agree"),  # Employees health scheme continues to face hiccups
    ("2b765b2b-3087-4817-ad19-6415dd67f8e4", "9cab6caf-0f84-4af5-8991-093df01cc305"): (False, "agree"),  # Hyderabad Traffic Police gears up for Ujjaini [...]
    ("2b765b2b-3087-4817-ad19-6415dd67f8e4", "acef882e-ca0c-4498-b3e9-4f3a7cc40649"): (False, "agree"),  # SCR urged to expand Neredmet Railway Station for [...]
    # seed: Five-member expert team inspects proposed sewage treatment plant sites
    ("ed67d226-5f2f-42d1-8e73-9dabfa2559fb", "09aa8e4d-ea97-4e7d-bd82-2a81ae15b125"): (False, "agree"),  # Tenders annulled for proposed industrial corridor
    ("ed67d226-5f2f-42d1-8e73-9dabfa2559fb", "0a471b1b-f433-4150-84d7-b07e838e6c0f"): (False, "agree"),  # Kerala earmarks ₹15 crore for road safety under [...]
    ("ed67d226-5f2f-42d1-8e73-9dabfa2559fb", "302732bd-7aed-46b6-ae00-479f60af9166"): (False, "agree"),  # Akhil Marar severs ties with Twenty20, levels [...]
    ("ed67d226-5f2f-42d1-8e73-9dabfa2559fb", "35013477-ac4f-44f8-acae-0cacab6e42f6"): (False, "agree"),  # Expert team to visit Kalladi debris slip site in [...]
    ("ed67d226-5f2f-42d1-8e73-9dabfa2559fb", "4c62177d-2b74-4282-bdbd-a1c7e93af523"): (False, "agree"),  # Kodiyathur panchayat member dies in accident
    ("ed67d226-5f2f-42d1-8e73-9dabfa2559fb", "51e98274-df19-4fb4-845d-b8695bcab573"): (False, "agree"),  # Idukki district administration plans to set up CSTP [...]
    ("ed67d226-5f2f-42d1-8e73-9dabfa2559fb", "87660c40-a186-45dd-af23-c74927ee6545"): (False, "agree"),  # Railway revises redevelopment deadlines for ERS, ERN [...]
    ("ed67d226-5f2f-42d1-8e73-9dabfa2559fb", "93e5e9f8-8044-4215-a19c-6462ac56396b"): (False, "agree"),  # Broadway in Kochi gears up for Onam amid lingering [...]
    ("ed67d226-5f2f-42d1-8e73-9dabfa2559fb", "9b3f8175-af35-4c14-924b-d5a72a07941a"): (False, "agree"),  # Heavy silt in Pazhassi dam disrupts drinking water treatment
    ("ed67d226-5f2f-42d1-8e73-9dabfa2559fb", "9f9b0bc0-295e-476b-b132-a289aad5520d"): (False, "agree"),  # Supreme Court committee inspects KBR National Park, [...]
    # seed: Fresh supply of retail space in malls down 57% in Jan-Mar across top 7 cities: [...]
    ("2a1a02e9-b607-4223-b801-da9a24819fc5", "53dc964d-ce05-4fde-9779-9e6a3e8a6b9a"): (False, "agree"),  # Apartment sales in Bengaluru rise 16% in Jan-Jun to [...]
    ("2a1a02e9-b607-4223-b801-da9a24819fc5", "1ab87fbe-ee75-4c84-9adb-6ae6b6d291ea"): (False, "agree"),  # Delhi NCR, Chennai lead industrial warehousing leasing [...]
    ("2a1a02e9-b607-4223-b801-da9a24819fc5", "1d69904f-cf70-45ef-99d0-0e4b2c958645"): (False, "agree"),  # India's data centre capacity may reach 3-3.6 GW by [...]
    ("2a1a02e9-b607-4223-b801-da9a24819fc5", "3be2d375-d8f8-46e6-91d4-e4a250ae2ad8"): (False, "agree"),  # Mumbai's Rs 10 crore-plus home market scales a record [...]
    ("2a1a02e9-b607-4223-b801-da9a24819fc5", "40a2d2b7-0cc4-41e8-aaa1-a23a42323da0"): (False, "agree"),  # Bengaluru Home Sales Surge 16% But Hyderabad Slips 3% [...]
    ("2a1a02e9-b607-4223-b801-da9a24819fc5", "533d0d5e-e025-43dd-a741-4ce6e678591c"): (False, "agree"),  # IN-SPACe approval now must for planned space objects [...]
    ("2a1a02e9-b607-4223-b801-da9a24819fc5", "6874a9aa-64cf-44ff-84a2-f791e2b82847"): (False, "agree"),  # Trump tells oil companies to ‘get retail prices down [...]
    ("2a1a02e9-b607-4223-b801-da9a24819fc5", "cafbca9d-5a73-450c-b8b1-7fa0cbf8f68f"): (False, "agree"),  # Record 2.73 lakh register for NEET-PG 2026; exam to be [...]
    ("2a1a02e9-b607-4223-b801-da9a24819fc5", "dcdea86a-1270-4faf-9627-8865d07c8200"): (False, "agree"),  # Jobs grow in tier-2 cities as India's top talent moves [...]
    # seed: Gold Price Today: Gold Falls Below Rs 1.45 Lakh On MCX As Middle East Tensions [...]
    ("f746abde-b04f-4194-898f-4a9b09571e8b", "68f2ce19-d32d-488f-a80d-6dcfe7d08ae1"): (False, "agree"),  # Gold Jumps To Rs 1.44 Lakh On MCX, Silver Gains By Rs [...]
    ("f746abde-b04f-4194-898f-4a9b09571e8b", "6b02478e-ad08-4148-81f6-a3a5d3c8a6f7"): (False, "agree"),  # चांदी में बड़ा बदलाव, हाई से अब 1.95 लाख सस्ती, सोने [...]
    ("f746abde-b04f-4194-898f-4a9b09571e8b", "c87e148f-518d-4748-889a-df4d4709cf94"): (False, "agree"),  # Gold Rate Today: Check 24K, 22K Gold Prices In Mumbai, [...]
    ("f746abde-b04f-4194-898f-4a9b09571e8b", "fca26160-0d3f-42ec-b705-1bdfda7698c7"): (False, "agree"),  # इधर बिखर रहा शेयर बाजार, उधर सोना-चांदी के दाम में [...]
    ("f746abde-b04f-4194-898f-4a9b09571e8b", "0e898b02-afea-49e3-aa5e-ad355538b3e6"): (False, "agree"),  # US Stock Market Today: Dow Zooms 600 Points As Oil [...]
    ("f746abde-b04f-4194-898f-4a9b09571e8b", "0ecb63b0-14f7-4a97-afde-5c7ec0e90d6b"): (False, "agree"),  # Brent Tops $95 After Houthis Attack On Saudi Tankers [...]
    ("f746abde-b04f-4194-898f-4a9b09571e8b", "222ae9b3-fbbf-45d3-8201-4102e24aaf1b"): (False, "agree"),  # Tensions escalate in Vijayawada as BJP activists march [...]
    ("f746abde-b04f-4194-898f-4a9b09571e8b", "2407c7f5-a6be-4e8c-8ac1-59f675722b3f"): (False, "agree"),  # Nikkei, Kospi Sink As Investors Brace For US Fed Rate [...]
    ("f746abde-b04f-4194-898f-4a9b09571e8b", "42b04623-2fc1-4515-9088-95aa7695dd14"): (False, "agree"),  # Meesho's Growth Cart Has A Profit Problem, Says [...]
    ("f746abde-b04f-4194-898f-4a9b09571e8b", "56b2999e-c90b-4ae2-9dd4-c5e571de884b"): (False, "agree"),  # चांदी दो दिन में ₹7700 महंगी, सोना भी उछला, देखें शाम का रेट
    # seed: Gold Rate Today: Check 24K, 22K Gold Prices In Mumbai, Delhi, Chennai, [...]
    ("c87e148f-518d-4748-889a-df4d4709cf94", "f746abde-b04f-4194-898f-4a9b09571e8b"): (False, "agree"),  # Gold Price Today: Gold Falls Below Rs 1.45 Lakh On MCX [...]
    ("c87e148f-518d-4748-889a-df4d4709cf94", "10816a52-73f5-4bed-8e6f-b583086d1055"): (False, "agree"),  # Petrol, Diesel Prices On July 23: Check New Fuel Rates [...]
    ("c87e148f-518d-4748-889a-df4d4709cf94", "1b8c2c7b-596f-4e1c-96cb-916dcfa195f9"): (False, "agree"),  # Live: Markets Likely To Open In Green
    ("c87e148f-518d-4748-889a-df4d4709cf94", "2781df0f-2ee4-4444-9a41-595c0ee0286b"): (False, "agree"),  # Three held for allegedly pledging fake gold ornaments
    ("c87e148f-518d-4748-889a-df4d4709cf94", "56b2999e-c90b-4ae2-9dd4-c5e571de884b"): (False, "agree"),  # चांदी दो दिन में ₹7700 महंगी, सोना भी उछला, देखें शाम का रेट
    ("c87e148f-518d-4748-889a-df4d4709cf94", "68f2ce19-d32d-488f-a80d-6dcfe7d08ae1"): (False, "agree"),  # Gold Jumps To Rs 1.44 Lakh On MCX, Silver Gains By Rs [...]
    ("c87e148f-518d-4748-889a-df4d4709cf94", "6a76a8fc-3a9d-4bde-8493-93970a81bc22"): (False, "agree"),  # Gold ornaments, bronze objects stolen from temple
    ("c87e148f-518d-4748-889a-df4d4709cf94", "a51fa6c9-1c90-4f4c-b539-378c0d6b4ddf"): (False, "agree"),  # Live: Markets Likely To Open Higher As Oil Drops Below [...]
    ("c87e148f-518d-4748-889a-df4d4709cf94", "b72cca0e-93b0-45d8-a2ff-d8eea7797dce"): (False, "agree"),  # Sharmila Survived Abuse Over Dowry, Today She Is CWG [...]
    # seed: Golden Chickens Resurfaces With Four New Malware Families and Modular Implants
    ("a70e00ca-139a-49d0-b306-596d626eea3b", "10bab346-98eb-44bf-abe9-2734e400559e"): (False, "agree"),  # Prahlad Joshi's 2022 NEET exam remark resurfaces as he [...]
    ("a70e00ca-139a-49d0-b306-596d626eea3b", "175335bc-cef4-4ca6-9703-dbc5e4e6a386"): (False, "agree"),  # Cl0p Affiliates Target Internet-Exposed PTC Windchill [...]
    ("a70e00ca-139a-49d0-b306-596d626eea3b", "1ec0732d-2cb3-4c34-8d4c-0fa8c39c95e2"): (False, "agree"),  # Critical ServiceNow AI Platform Flaw Exploited for [...]
    ("a70e00ca-139a-49d0-b306-596d626eea3b", "2ad98744-8bcd-4bef-b20c-d8fbb75c2549"): (False, "agree"),  # SleeperGem Uses Three Malicious RubyGems Packages to [...]
    ("a70e00ca-139a-49d0-b306-596d626eea3b", "2f702ae0-e76f-4488-a601-ee83ca4493c0"): (False, "agree"),  # HollowGraph Malware Hides C2 and Stolen Files in [...]
    ("a70e00ca-139a-49d0-b306-596d626eea3b", "32998199-5021-4dac-8480-c7099717e0ed"): (False, "agree"),  # TELESHIM Abuses Telegram for C2 in Attacks Against [...]
    ("a70e00ca-139a-49d0-b306-596d626eea3b", "6f8d85a1-2647-4feb-87a8-293eb7529c25"): (False, "agree"),  # Lee, Bouchier make it four in four for Brave
    ("a70e00ca-139a-49d0-b306-596d626eea3b", "8ade35de-69b1-48b0-954e-e5ad08991720"): (False, "agree"),  # New Zealand bowl with Mitchell injured; West Indies [...]
    ("a70e00ca-139a-49d0-b306-596d626eea3b", "9ecf626a-8a27-4c1a-9f83-f42ab61523dc"): (False, "agree"),  # Hyderabad’s Golden Bonam offered to Goddess Kanaka [...]
    ("a70e00ca-139a-49d0-b306-596d626eea3b", "c1390ce5-963c-44e0-bc63-350fb35dd49f"): (False, "agree"),  # Chinese Threat Actor Uses Leaked DarkSword Kit to [...]
    # seed: Government distributes science kits to enhance learning in schools
    ("ff09f44c-fda9-4a23-b97a-661fd055159b", "1f427fbb-5c7b-48c2-b869-ffc7b56d533c"): (False, "agree"),  # SP distributes hearing aids to special school students
    ("ff09f44c-fda9-4a23-b97a-661fd055159b", "39729783-6191-42c3-9313-f022ed3b1115"): (False, "agree"),  # Andhra Pradesh girl selected for world’s first all- [...]
    ("ff09f44c-fda9-4a23-b97a-661fd055159b", "43d19673-51d9-4846-a0e7-fcbabf6bf8c0"): (False, "agree"),  # Nellore all set to distribute 10,000 bicycles to girl [...]
    ("ff09f44c-fda9-4a23-b97a-661fd055159b", "58cceefd-8058-4b43-a518-20d741edd0c3"): (False, "agree"),  # Minister accuses YSRCP of misleading public over [...]
    ("ff09f44c-fda9-4a23-b97a-661fd055159b", "63296b7a-b2d6-468f-858d-ebba08bef5f3"): (False, "agree"),  # ಬಿಸಿಯೂಟ ಯೋಜನೆಯಲ್ಲಿ ವಿತರಿಸುವ ಮೊಟ್ಟೆಗಳ ಖರೀದಿ ದರ [...]
    ("ff09f44c-fda9-4a23-b97a-661fd055159b", "64cb8c14-2b9a-4d54-bd94-0550b9de6ab2"): (False, "agree"),  # Telangana to sponsor annual foreign study tours for [...]
    ("ff09f44c-fda9-4a23-b97a-661fd055159b", "883c52b8-85d6-4050-9a01-4535ccf0863d"): (False, "agree"),  # Minister Bindhu Krishna to inaugurate scheme to [...]
    ("ff09f44c-fda9-4a23-b97a-661fd055159b", "896f1e12-fa93-40a5-b5ed-96b4a7607986"): (False, "agree"),  # ಚಾಮರಾಜನಗರದಲ್ಲಿ ಕಾನೂನು ಅರಿವು-ನೆರವು ಕಾರ್ಯಾಗಾರ ಆ.4 ರಂದು
    ("ff09f44c-fda9-4a23-b97a-661fd055159b", "90b86113-ede5-4c0d-9a72-8bb18b594113"): (False, "agree"),  # Maharashtra issues order on safe food in schools
    ("ff09f44c-fda9-4a23-b97a-661fd055159b", "a8372ebd-5cec-45f0-9c2e-4a6f1594e46b"): (False, "agree"),  # Kerala govt. launches Digital Square programme to [...]
    # seed: HDFC Bank ADRs Slip Into Red As Internal Probe Pulls Up Top Brass For [...]
    ("aa29443f-1733-4ec4-b07f-fd9a2a804a67", "10362e12-3d10-420d-b062-25c048d5ae84"): (False, "agree"),  # 10% Drop In Seven Sessions: Here's Why HDFC Bank Share [...]
    ("aa29443f-1733-4ec4-b07f-fd9a2a804a67", "62239970-0ec2-4651-a70c-e6c1716a6386"): (False, "agree"),  # BEL To Canara Bank - Check HDFC Securities' New [...]
    ("aa29443f-1733-4ec4-b07f-fd9a2a804a67", "0201f4e4-0aad-4ee9-bd7d-0e3777660c3e"): (False, "agree"),  # भारत में जल्द आ रहे हैं प्लास्टिक के नोट, सरकार ने दी [...]
    ("aa29443f-1733-4ec4-b07f-fd9a2a804a67", "1c11952a-ed29-4b5e-b0c9-169d1ae3ba23"): (False, "agree"),  # राम मंदिर ट्रस्ट की बैठक, श्रद्धालुओं की सुविधा और [...]
    ("aa29443f-1733-4ec4-b07f-fd9a2a804a67", "1f19955b-f206-4d5c-a46b-89aad7578c38"): (False, "agree"),  # Okayed trials for polymer notes for ₹10, 20; no plan [...]
    ("aa29443f-1733-4ec4-b07f-fd9a2a804a67", "22196fb8-21e8-4bc9-b9dd-63cff5c62e4a"): (False, "agree"),  # Bengaluru: Homemaker alleges ₹2.5 crore fraud by [...]
    ("aa29443f-1733-4ec4-b07f-fd9a2a804a67", "26f1a782-cf04-4ef9-8ca2-38e4dfaa094e"): (False, "agree"),  # ತಳಮಟ್ಟದಲ್ಲಿ ಕಾಂಗ್ರೆಸ್ ಸಂಘಟನೆ ಬಲಪಡಿಸಿ - ಎಐಸಿಸಿ ವೀಕ್ಷಕ [...]
    ("aa29443f-1733-4ec4-b07f-fd9a2a804a67", "746f2f84-7b20-490f-a4b1-f6a6f1913596"): (False, "agree"),  # Gates Foundation Review Details Epstein Interactions, [...]
    ("aa29443f-1733-4ec4-b07f-fd9a2a804a67", "79abea19-9aa2-4619-b5fe-7557b42c13a0"): (False, "agree"),  # 'Beat the policemen': Injured cops recount mob assault [...]
    ("aa29443f-1733-4ec4-b07f-fd9a2a804a67", "bd252363-d4c0-4541-acd7-d52dfa65eeeb"): (False, "agree"),  # Bajaj Auto to TVS Motor: Check HDFC Securities' Latest [...]
    # seed: Hashmatullah Shahidi resigns as Afghanistan's ODI captain
    ("11166757-4c0a-468d-9258-3f22321fd1c5", "2c0cdb1e-ca92-4dbf-be3b-cb111130b7d9"): (False, "agree"),  # Feroza, Amin, Sandhu shine as Pakistan go 1-0 up [...]
    ("11166757-4c0a-468d-9258-3f22321fd1c5", "3756e387-78e2-4dba-a5f9-f49bdb6d78c5"): (False, "agree"),  # Litton Das named Bangladesh's new ODI captain
    ("11166757-4c0a-468d-9258-3f22321fd1c5", "3f4aed34-c20d-4c68-870f-b9472155d6dd"): (False, "agree"),  # Duleep Trophy: Kishan to captain East Zone; [...]
    ("11166757-4c0a-468d-9258-3f22321fd1c5", "4d130f4e-610b-4684-8907-d16949ee7803"): (False, "agree"),  # Rahmat Shah leads Afghanistan in five-match ODI series [...]
    ("11166757-4c0a-468d-9258-3f22321fd1c5", "5c3a08ae-4bce-44bd-8b37-4976cfd689dc"): (False, "agree"),  # Iyer: Need to 'adapt as soon as possible' after [...]
    ("11166757-4c0a-468d-9258-3f22321fd1c5", "8f7de710-2987-4ab9-9027-93b528779554"): (False, "agree"),  # Shane McDermott appointed Afghanistan assistant and [...]
    ("11166757-4c0a-468d-9258-3f22321fd1c5", "92047787-5136-4687-8b2b-47506bcd39cf"): (False, "agree"),  # Rohit in the spotlight with series on the line at Lord's
    ("11166757-4c0a-468d-9258-3f22321fd1c5", "a11f1a01-0578-437d-a17d-e044fae18dbb"): (False, "agree"),  # Rahane announces retirement from international cricket [...]
    ("11166757-4c0a-468d-9258-3f22321fd1c5", "d592376a-5937-4fc5-9841-b6b7e3fec324"): (False, "agree"),  # Future India captain? Selector explains why [...]
    ("11166757-4c0a-468d-9258-3f22321fd1c5", "f5415780-d8b4-4b2f-ba63-b10d3b698467"): (False, "agree"),  # Afghanistan to host India for T20I series in Delhi
    # seed: Head constable’s swift action saves man’s life in Nalgonda district
    ("380558f9-59c6-4f3f-98a3-d54cd4286b04", "874281ad-8724-499a-ab72-ada130e968c7"): (False, "agree"),  # Head constable suspended for neglecting emergency [...]
    ("380558f9-59c6-4f3f-98a3-d54cd4286b04", "e03baac2-34b8-482e-b358-0cc538745db4"): (False, "agree"),  # Police constable found dead
    ("380558f9-59c6-4f3f-98a3-d54cd4286b04", "5e8d76fe-4cb4-486a-95fc-9fd815068462"): (False, "agree"),  # Couple allegedly attempt suicide in ambulance in front [...]
    ("380558f9-59c6-4f3f-98a3-d54cd4286b04", "8bff4d46-ffd5-44f4-bf71-15fbe0f3c588"): (False, "agree"),  # ‘We did not want to give up’: Doctor recalls 30-minute [...]
    ("380558f9-59c6-4f3f-98a3-d54cd4286b04", "ce6a6c78-ab5e-4280-b77f-dd0e8cf731ee"): (False, "agree"),  # Protest breaks out during police constable recruitment [...]
    ("380558f9-59c6-4f3f-98a3-d54cd4286b04", "f27cbef3-4699-4b4e-bfb4-9ccff843cbf0"): (False, "agree"),  # Man sentenced to life for murder over debt dispute in [...]
    ("380558f9-59c6-4f3f-98a3-d54cd4286b04", "f4b3b6fb-32bf-420e-a85f-a465421160ed"): (False, "agree"),  # Telangana DCA seizes 113 abortion kits from medical [...]
    ("380558f9-59c6-4f3f-98a3-d54cd4286b04", "f55fa420-53a8-48f2-abfd-6edb390c55be"): (False, "agree"),  # Elderly man, distraught over delay in issue of Aadhaar [...]
    # seed: Health Minister orders audit to curb medical oxygen procurement costs
    ("0d1b970d-54a1-4923-8281-f5516749c5f8", "159e006c-c3f2-4b19-b085-98fe51b0427c"): (False, "agree"),  # Action plan to expand organ transplant services in [...]
    ("0d1b970d-54a1-4923-8281-f5516749c5f8", "288ec841-b74b-412e-9647-d00a5300bc19"): (False, "agree"),  # Minister visits six-year-old girl undergoing cancer [...]
    ("0d1b970d-54a1-4923-8281-f5516749c5f8", "674dca02-b681-4f89-8e2c-0a68a230cf2f"): (False, "agree"),  # Health Minister orders 10-year review into medicine [...]
    ("0d1b970d-54a1-4923-8281-f5516749c5f8", "18c96365-0759-4e49-910a-3b98a6427cd9"): (False, "agree"),  # NHA de-empanels over 2,000 hospitals in fraud [...]
    ("0d1b970d-54a1-4923-8281-f5516749c5f8", "21a2b95a-924e-4120-8fb5-0b18a362d16d"): (False, "agree"),  # PAV urges govt. to strengthen disease surveillance as [...]
    ("0d1b970d-54a1-4923-8281-f5516749c5f8", "2cfb4573-fc6d-4592-9a24-f8c0ecfd969b"): (False, "agree"),  # Flood alert sounded along Godavari, Sabari riverbanks [...]
    ("0d1b970d-54a1-4923-8281-f5516749c5f8", "335d92fb-6c35-46aa-a20d-61c37ecba3ce"): (False, "agree"),  # TN govt to expand scope of CM health insurance scheme: [...]
    ("0d1b970d-54a1-4923-8281-f5516749c5f8", "b0a6c9ed-14ed-4569-8568-976913a85ce8"): (False, "agree"),  # AP Govt launches subsidised rice at ₹52/kg to curb [...]
    ("0d1b970d-54a1-4923-8281-f5516749c5f8", "b81b85fb-8db4-4ab2-8657-693feedc3cb9"): (False, "agree"),  # Praja Arogya Vedika seeks reforms in public healthcare
    ("0d1b970d-54a1-4923-8281-f5516749c5f8", "c30ae9c7-f24b-464a-85bf-18d5aa5e807b"): (False, "agree"),  # Andhra Pradesh introduces new grading system to [...]
    # seed: Heavy rain in Maharashtra leads to slight increase in water levels in Krishna
    ("3de5434d-68be-403b-9e46-81c97e2cd97e", "3526a777-6e9b-48cc-aed5-547897c14500"): (False, "agree"),  # Reduced rainfall in Maharashtra, Belagavi leads to [...]
    ("3de5434d-68be-403b-9e46-81c97e2cd97e", "95423eae-2c75-43fe-92b7-202a3c96b23d"): (False, "agree"),  # Water levels in Krishna rise as Maharashtra and [...]
    ("3de5434d-68be-403b-9e46-81c97e2cd97e", "03faab3f-9b66-4cc8-a99c-330744cac19f"): (False, "agree"),  # Kerala rains: Heavy rainfall continues in Idukki, dam [...]
    ("3de5434d-68be-403b-9e46-81c97e2cd97e", "85416f62-b182-4029-a0fd-4ea23b57dc5b"): (False, "agree"),  # Rain causes slight disruptions to Sabarimala [...]
    ("3de5434d-68be-403b-9e46-81c97e2cd97e", "8620a580-166f-41d8-b40f-2bd33bd46d7b"): (False, "agree"),  # Water release for crops from Almatti dam begins
    ("3de5434d-68be-403b-9e46-81c97e2cd97e", "d45a1391-6799-4f0c-af73-42e3feda445d"): (False, "agree"),  # KRS dam breaches 100 feet mark as rain drenches south [...]
    ("3de5434d-68be-403b-9e46-81c97e2cd97e", "d69c376e-b496-47a7-9638-5cab84cc04f0"): (False, "agree"),  # Outflow from Almatti increased to around 1.1 lakh cusecs
    ("3de5434d-68be-403b-9e46-81c97e2cd97e", "df0c0959-8bab-49d9-81b6-43068e4c78cb"): (False, "agree"),  # KRS, Kabini water levels continue to rise amid heavy inflows
    # seed: Hindu daughters not entitled to equal share in ancestral property if they had [...]
    ("fa0a1268-0a60-4ccb-8a39-e716283f2ce7", "2d70e2e6-5363-445c-a2b9-07b49d441faf"): (False, "agree"),  # Madras High Court to hear PIL on Karur Devadanam land issue
    ("fa0a1268-0a60-4ccb-8a39-e716283f2ce7", "16f673d1-6091-4e33-aff9-4f6a60c6f2b3"): (False, "agree"),  # "21 Students Died, And BJP Garlanded Dharmendra [...]
    ("fa0a1268-0a60-4ccb-8a39-e716283f2ce7", "1b882ec1-b4f5-4353-bb98-4a86f3d7d545"): (False, "agree"),  # Encroachments demolished to provide easy access to [...]
    ("fa0a1268-0a60-4ccb-8a39-e716283f2ce7", "22f7633c-c24c-427a-b81e-b938de5a86d5"): (False, "agree"),  # Tamil Nadu Today: Supreme Court stays order banning [...]
    ("fa0a1268-0a60-4ccb-8a39-e716283f2ce7", "241818a1-a012-4782-9a8c-74cfa6d0ddd0"): (False, "agree"),  # ‘ವಿಜಯ್​​ಗೆ ತ್ರಿಷಾ ಮಧ್ಯರಾತ್ರಿ ಸಿಗ್ತಾರೆ, ಮುಂದೆ ಡಿಸಿಎಂ [...]
    ("fa0a1268-0a60-4ccb-8a39-e716283f2ce7", "2ac72877-9d99-4826-9024-ff96b39888fb"): (False, "agree"),  # Tamil Nadu Today: Private schools ordered to display fees
    ("fa0a1268-0a60-4ccb-8a39-e716283f2ce7", "467a1d7f-1ca2-4526-905c-8434b0a8497e"): (False, "agree"),  # Madras High Court to take up Vice-Chancellor [...]
    ("fa0a1268-0a60-4ccb-8a39-e716283f2ce7", "4c21cddf-6004-46b0-99d7-15e869743e01"): (False, "agree"),  # '2 வேளைதான் சாப்பாடு'- 23 ஆண்டுகளாக காணாமல் போன [...]
    ("fa0a1268-0a60-4ccb-8a39-e716283f2ce7", "8630a895-906d-421b-849e-32f525d50a7e"): (False, "agree"),  # Adult unmarried daughter can claim financial support [...]
    ("fa0a1268-0a60-4ccb-8a39-e716283f2ce7", "868f7377-b5c8-4f56-96e4-7eab4bc1cbe3"): (False, "agree"),  # Lack of evidence: SC quashes Pocso case against woman
    # seed: IIT-Hyderabad, Crimson Energy launch nuclear technology orientation programme
    ("ad6ed995-861b-4ceb-8331-a1763cfeccb7", "06195141-75eb-42d0-809d-b15d6980ab8f"): (False, "agree"),  # IIITDM Kurnool tops India’s 5G Use Case Labs Ranking by DoT
    ("ad6ed995-861b-4ceb-8331-a1763cfeccb7", "0b658771-570a-48ef-977f-d6a628662c7a"): (False, "agree"),  # Kakatiya University to set up second incubation centre [...]
    ("ad6ed995-861b-4ceb-8331-a1763cfeccb7", "24052bc8-7191-4aa2-98a7-db4410011079"): (False, "agree"),  # India on track to meet 2030 renewable energy target: [...]
    ("ad6ed995-861b-4ceb-8331-a1763cfeccb7", "25a6edea-099d-4718-a776-dde3841f5871"): (False, "agree"),  # THG Publishing and RV College of Engineering sign MoU [...]
    ("ad6ed995-861b-4ceb-8331-a1763cfeccb7", "5794f7a2-4e4f-4b5d-b3d8-5e71ff13552d"): (False, "agree"),  # Zen Tech gets ₹177.5 cr worth order for upgradation & [...]
    ("ad6ed995-861b-4ceb-8331-a1763cfeccb7", "582fb4e6-55b6-4987-8ac9-caa1e090512c"): (False, "agree"),  # US Announces Landmark Nuclear Deal With Saudi Arabia
    ("ad6ed995-861b-4ceb-8331-a1763cfeccb7", "632bf820-607f-4462-a514-e2f462416518"): (False, "agree"),  # Rajya Sabha MP moves Supreme Court against use of [...]
    ("ad6ed995-861b-4ceb-8331-a1763cfeccb7", "95b8f0e9-3672-4219-a0fe-a35ab0dfd782"): (False, "agree"),  # IIT Delhi Opens Enrollment For Online Data Science And [...]
    ("ad6ed995-861b-4ceb-8331-a1763cfeccb7", "96508d70-aabd-4396-aed7-9b0c0f4f99bd"): (False, "agree"),  # TPREL begins construction of ₹5,350 crore hybrid [...]
    ("ad6ed995-861b-4ceb-8331-a1763cfeccb7", "b107892a-3daa-4822-9f3a-73a0a682f1f8"): (False, "agree"),  # Social Alpha ropes in NITI Aayog, Tata Power to launch [...]
    # seed: India-origin cricketer Reddy handed 8-year ban by ICC for corruption
    ("70165b28-e514-4814-ac82-08a4c878f93d", "82f88ecd-d42e-4324-9332-942773929a93"): (True, "agree"),  # ಕ್ರಿಕೆಟ್‌ನಿಂದ ಅಖಿಲೇಶ್ ರೆಡ್ಡಿಗೆ 8 ವರ್ಷಗಳ ನಿಷೇಧ!
    ("70165b28-e514-4814-ac82-08a4c878f93d", "1c15f05f-b2d8-4ed7-86b5-b7bc004f4f2e"): (False, "agree"),  # Draft of SLC constitution handed over to sports minister
    ("70165b28-e514-4814-ac82-08a4c878f93d", "1d99b849-0a10-481d-85b8-dfa7cf599068"): (True, "agree"),  # USA player Akhilesh Reddy banned for eight years
    ("70165b28-e514-4814-ac82-08a4c878f93d", "22c1772a-6b7b-4aef-9470-ab9dffe07246"): (False, "agree"),  # 26-year-old Indian-origin woman shot dead in Toronto [...]
    ("70165b28-e514-4814-ac82-08a4c878f93d", "29059250-16fe-42b7-940d-ffa28998150e"): (False, "agree"),  # Abbas, Shahzad handed a demerit point each for [...]
    ("70165b28-e514-4814-ac82-08a4c878f93d", "33c71414-6870-4ac9-8f2d-1da314008df3"): (False, "agree"),  # IPL’s business value soars to $20.6 billion, RCB most [...]
    ("70165b28-e514-4814-ac82-08a4c878f93d", "56ba4523-fc02-413d-84cf-f2264fd21221"): (False, "agree"),  # Nothing can shame people unfazed by Ram temple [...]
    ("70165b28-e514-4814-ac82-08a4c878f93d", "6e498487-d817-4212-9767-0ecbbfa6ff59"): (False, "agree"),  # Tribunal sets aside most of the FEMA violation charges [...]
    ("70165b28-e514-4814-ac82-08a4c878f93d", "856fbf92-648c-4e29-9f9d-391c9aba918f"): (False, "agree"),  # Key defends Flintoff from 'disrespectful' criticism
    ("70165b28-e514-4814-ac82-08a4c878f93d", "8b00529e-73c7-42e9-9cd4-d94559a45b43"): (False, "agree"),  # Students blocking medical seats to face two-year ban [...]
    # seed: Indian WhatsApp Account Closure: बिना चेतावनी बंद हुए कई व्हाट्सएप अकाउंट, [...]
    ("5441dae4-8a47-437b-84bd-759a1c759d5b", "11dc4684-dae0-4fed-8404-0f4b91d3d245"): (True, "adj:tejas-said-same:medium"),  # WhatsApp Account Recovery: अचानक रिव्यू में चला गया है [...]
    ("5441dae4-8a47-437b-84bd-759a1c759d5b", "37742a63-ee6d-4f96-a05d-631ec954ea34"): (True, "adj:tejas-said-same:high"),  # WhatsApp puts multiple accounts, including in India, [...]
    ("5441dae4-8a47-437b-84bd-759a1c759d5b", "4d648c2e-3575-4ea7-9f10-24109b5b43b2"): (False, "agree"),  # We want withdrawal of FIRs, not just closure: CJP's [...]
    ("5441dae4-8a47-437b-84bd-759a1c759d5b", "67a69067-e47f-45c9-a9c6-a0febe09e75f"): (False, "agree"),  # Annamalai requests the closure of 129 Tasmac retail shops
    ("5441dae4-8a47-437b-84bd-759a1c759d5b", "6943e1db-3d05-4e1e-b18a-7523e05e625f"): (True, "adj:tejas-said-same:high"),  # WhatsApp reacts as multiple accounts, including in [...]
    ("5441dae4-8a47-437b-84bd-759a1c759d5b", "6dc58927-0ae1-4c3e-b91c-d0a434bccb53"): (False, "agree"),  # VISA: भारतीय छात्रों को 54 दिन के भीतर क्यों लौटना [...]
    ("5441dae4-8a47-437b-84bd-759a1c759d5b", "ac8a5bb2-ba6b-409e-a5da-b813b9a22a93"): (False, "agree"),  # Case booked against bank manager for diverting funds [...]
    ("5441dae4-8a47-437b-84bd-759a1c759d5b", "baf4115a-e109-4480-8354-166a028c2f66"): (False, "agree"),  # ಭಾರತದಲ್ಲಿ ಕೌಂಟ್‌ಡೌನ್‌ ಶುರು: ಏಕಾಏಕಿ ನೂರಾರು ವಾಟ್ಸಾಪ್‌ [...]
    ("5441dae4-8a47-437b-84bd-759a1c759d5b", "c0001032-176b-4d64-b69e-580581833f53"): (False, "agree"),  # PM-SYM pension scheme: Women outnumber men, account [...]
    # seed: India’s dengue burden grows more complex as multiple virus strains circulate [...]
    ("fbb3901b-9da7-48ab-bd39-6a6651aa903d", "c2958b17-8aa9-4704-a1a0-e732500c62fa"): (False, "agree"),  # Malaria, dengue, leptospirosis killed 99 people in [...]
    ("fbb3901b-9da7-48ab-bd39-6a6651aa903d", "d37c9697-9e12-4a48-99a3-7ce51ac9c8ad"): (False, "agree"),  # Takeda’s QDENGA approved in India, can be given [...]
    ("fbb3901b-9da7-48ab-bd39-6a6651aa903d", "13bae184-c5d7-4661-97d2-d5500611eb9a"): (False, "agree"),  # Chandipura Virus Outbreak Claims 22 Young Lives in [...]
    ("fbb3901b-9da7-48ab-bd39-6a6651aa903d", "2f4c2325-a24c-47b1-a655-3524cbdc72ab"): (False, "agree"),  # HC refuses to stay HPV vaccine administration
    ("fbb3901b-9da7-48ab-bd39-6a6651aa903d", "4b4232ea-7a1f-4895-a0fb-a3144ea52d21"): (False, "agree"),  # ICMR hands over three homegrown medical technologies [...]
    ("fbb3901b-9da7-48ab-bd39-6a6651aa903d", "6943e1db-3d05-4e1e-b18a-7523e05e625f"): (False, "agree"),  # WhatsApp reacts as multiple accounts, including in [...]
    ("fbb3901b-9da7-48ab-bd39-6a6651aa903d", "9da50968-dc14-4232-b9f1-81b2b7279aca"): (False, "agree"),  # 'அரசுப் பள்ளிகளில் வாரம் ஒருமுறை சிக்கன் பிரியாணி': [...]
    ("fbb3901b-9da7-48ab-bd39-6a6651aa903d", "a6d43fd4-0733-45ad-880e-b3e856520857"): (False, "agree"),  # Malaria, dengue cases more than doubled in July in [...]
    ("fbb3901b-9da7-48ab-bd39-6a6651aa903d", "d46628ca-6e22-459c-8874-606fdecd6150"): (False, "agree"),  # No active COVID clusters in A.P., cases only sporadic, [...]
    ("fbb3901b-9da7-48ab-bd39-6a6651aa903d", "ea67d94a-0e38-4ccb-868f-0c6dd740660d"): (False, "agree"),  # India approves its first dengue vaccine Qdenga: How it [...]
    # seed: J&K: Terrorists kill Amarnath Yatra security personnel in Anantnag attack
    ("df2c5f3f-d744-420c-b46c-4defb5f6287f", "ce85db85-ca18-4ec8-99d6-10765f959a26"): (True, "agree"),  # Policeman killed in terror attack in Anantnag, Jammu [...]
    ("df2c5f3f-d744-420c-b46c-4defb5f6287f", "68c19336-cb65-4295-ad1f-7b10c79c51e0"): (True, "adj:tejas-said-same:high"),  # Terrorist kill J&K cop in Anantnag market, first [...]
    ("df2c5f3f-d744-420c-b46c-4defb5f6287f", "73a7f63f-88c2-456b-8dfa-0e87aa483a83"): (True, "adj:tejas-said-same:high"),  # Over 2,000 Detained Across J&K After Cop Killed In [...]
    ("df2c5f3f-d744-420c-b46c-4defb5f6287f", "07a8ae1a-23f7-46c0-921e-71cfe50ef29e"): (False, "agree"),  # VIDEO: कांस्टेबल आशिक हुसैन की जान लेने वाले दोनों [...]
    ("df2c5f3f-d744-420c-b46c-4defb5f6287f", "3abd8a01-a1fe-4e7b-b841-afd7e3abb5a4"): (False, "agree"),  # Only 1 active local terrorist left in J&K; hunt on for [...]
    ("df2c5f3f-d744-420c-b46c-4defb5f6287f", "5a58981a-390a-4dd3-b45a-87650e14b38c"): (False, "agree"),  # Mehbooba faces heat over Jantar Mantar comment, oppn [...]
    ("df2c5f3f-d744-420c-b46c-4defb5f6287f", "8ae226d8-6e6e-4c30-8592-425914097735"): (True, "adj:tejas-said-same:high"),  # अनंतनाग में आतंकी हमला!: पुलिस दल पर फायरिंग, गोली [...]
    ("df2c5f3f-d744-420c-b46c-4defb5f6287f", "99348d47-8c92-4fd8-ad96-72bf453cc922"): (False, "agree"),  # Migrant workers stay put, easing fears for Valley’s [...]
    ("df2c5f3f-d744-420c-b46c-4defb5f6287f", "d13c779a-7de6-4295-8ef6-e2359c7c5a5a"): (False, "agree"),  # 39 Amarnath pilgrims injured in road accident in Kashmir
    ("df2c5f3f-d744-420c-b46c-4defb5f6287f", "e10921a2-e98d-4e03-a38c-92753d5c5018"): (True, "adj:tejas-said-same:high"),  # J&K cop Aashiq Hussain Qureshi killed in terror attack
    # seed: Jana Nayagan Day 5: Thalapathy Vijay's final film nears Rs 150 cr India gross
    ("5e82eb16-dd75-4b3e-9b1e-eebfd824e3cb", "36ed2be9-9f75-47e6-9829-10f84527d15c"): (True, "adj:vijay-said-same:medium"),  # Vijay's Jana Nayagan crosses Rs 300 crore worldwide on [...]
    ("5e82eb16-dd75-4b3e-9b1e-eebfd824e3cb", "c0dcb797-4ecd-4658-af69-1028b9796cab"): (False, "agree"),  # Jana Nayagan hits theatres after delays, sparks [...]
    ("5e82eb16-dd75-4b3e-9b1e-eebfd824e3cb", "d2522761-7176-4e2a-92c7-eb3a1c0de2ff"): (False, "agree"),  # Jana Nayagan box office collections day 6: Vijay's [...]
    ("5e82eb16-dd75-4b3e-9b1e-eebfd824e3cb", "dc6a7b16-d479-4045-b066-1bab2af27eef"): (False, "agree"),  # Jana Nayagan box office day 12: Vijay’s film slows [...]
    ("5e82eb16-dd75-4b3e-9b1e-eebfd824e3cb", "3778c303-9d31-4a0d-82af-ad5496c0c2ba"): (False, "agree"),  # Jana Nayagan Advance Booking: Vijay's Film Surpasses [...]
    ("5e82eb16-dd75-4b3e-9b1e-eebfd824e3cb", "382fde02-32c6-4aa0-99b6-2f44d2737c8c"): (False, "agree"),  # Mysuru: Student groups decry police crackdown on [...]
    ("5e82eb16-dd75-4b3e-9b1e-eebfd824e3cb", "58621b44-6b81-4ae9-bd85-82dbc510ddd0"): (False, "agree"),  # ಪಲಿಮಾರು ಗ್ರಾಮ ಪಂಚಾಯಿತಿ ವ್ಯಾಪ್ತಿಯ ಗ್ರಾಮಸ್ಥರ ಅಹವಾಲು [...]
    ("5e82eb16-dd75-4b3e-9b1e-eebfd824e3cb", "7ddcdd61-865d-4974-82aa-a901e4b482a8"): (False, "agree"),  # Piracy fails to dampen advance bookings for Chief [...]
    ("5e82eb16-dd75-4b3e-9b1e-eebfd824e3cb", "7efe9aad-9a72-450d-8f6f-a7f4613434b7"): (False, "agree"),  # Jana Nayagan Box Office Update
    ("5e82eb16-dd75-4b3e-9b1e-eebfd824e3cb", "a2c6547f-1586-4248-8953-db36a4c2b803"): (False, "agree"),  # ಎ ಸರ್ಟಿಫಿಕೇಟ್ ಸಿನಿಮಾಗೆ ಮಕ್ಕಳನ್ನು ಕರೆತಂದ ಪೋಷಕರು; ‘ಜನ [...]
    # seed: KSH Automotive donates library racks, TV sets to welfare hostels in Sri Sathya [...]
    ("64a5168a-3a67-483d-9f76-639e0b79cb78", "51074c44-0d77-4945-ba18-a0b12a4b6b09"): (False, "agree"),  # A.P. government, Kia Motors sign MoU for ₹12 crore ITI [...]
    ("64a5168a-3a67-483d-9f76-639e0b79cb78", "5b41dcab-092f-4381-b2f9-febd8aa9cc2d"): (False, "agree"),  # Government launches subsidised fine rice distribution [...]
    ("64a5168a-3a67-483d-9f76-639e0b79cb78", "164e5185-0bce-4cdd-959d-d3e7776b3966"): (False, "agree"),  # 50 students in Vizianagaram to get scholarships on Aug. 15
    ("64a5168a-3a67-483d-9f76-639e0b79cb78", "33e7a5d0-1933-44d4-aa67-ae4fdd5ae9a2"): (False, "agree"),  # Police committed to making Sri Sathya Sai a crime-free [...]
    ("64a5168a-3a67-483d-9f76-639e0b79cb78", "574b3d7f-864d-44af-9e6c-724f5912ea63"): (False, "agree"),  # Kalaburagi: Central University of Karnataka faculty [...]
    ("64a5168a-3a67-483d-9f76-639e0b79cb78", "5c0ac27e-1238-489a-a5db-7b40487b6091"): (False, "agree"),  # Eluru Collector urges citizens to share feedback on [...]
    ("64a5168a-3a67-483d-9f76-639e0b79cb78", "9885c728-25cd-4783-bd87-f6f15c374e3f"): (False, "agree"),  # Police in decoy take valuables from Kukatpally [...]
    ("64a5168a-3a67-483d-9f76-639e0b79cb78", "ae53f752-c287-4b30-8705-746a4cd3e07b"): (False, "agree"),  # Farmer ends life due to crop loss, mounting debts in [...]
    ("64a5168a-3a67-483d-9f76-639e0b79cb78", "b60221c9-8c60-45d4-8810-0934eb080e6a"): (False, "agree"),  # Sharanabasaveshwar Sangha offers free education to 10 [...]
    ("64a5168a-3a67-483d-9f76-639e0b79cb78", "b6e1efd4-6ada-4992-85dd-e6f13af4b7cc"): (False, "agree"),  # SIR: Karnataka introduces doorstep delivery of caste [...]
    # seed: Kalaburagi artist showcases Surpur paintings at Rashtrapati Bhavan
    ("b4e7e8c7-89d0-4115-9e3e-27c41e664c62", "0494506f-558f-4444-81cd-bf39eca42f6f"): (False, "agree"),  # Haryana Congress seeks Murmu’s intervention on ‘paper leaks’
    ("b4e7e8c7-89d0-4115-9e3e-27c41e664c62", "065d94d0-385a-4a45-ae4f-d524f38ff9c0"): (False, "agree"),  # President Murmu arrives in North Macedonia; first [...]
    ("b4e7e8c7-89d0-4115-9e3e-27c41e664c62", "0d3b84b8-aabe-4ca6-bda5-058b9c893913"): (False, "agree"),  # Patil Puttappa award conferred on R.K. Patil
    ("b4e7e8c7-89d0-4115-9e3e-27c41e664c62", "3038b2f3-cb0c-4b79-a250-3d3df0b2d70d"): (False, "agree"),  # Man hacked to death in Kalaburagi
    ("b4e7e8c7-89d0-4115-9e3e-27c41e664c62", "32165c78-7159-4dd7-bb5b-4149fee53fca"): (False, "agree"),  # Kerala University to establish Ganapati Sastri Chair
    ("b4e7e8c7-89d0-4115-9e3e-27c41e664c62", "41348513-9bfa-49a0-bf39-e4f094cbc478"): (False, "agree"),  # AIIMS & Safdarjung residents seek Prez intervention in [...]
    ("b4e7e8c7-89d0-4115-9e3e-27c41e664c62", "44c7bb34-5e67-4479-9cb0-6e765ac655af"): (False, "agree"),  # India, Uzbekistan see strong potential in rare earth [...]
    ("b4e7e8c7-89d0-4115-9e3e-27c41e664c62", "462e7922-5dd2-4c75-a67b-1ae1735a4478"): (False, "agree"),  # What happened on Day 1 of Pralhad Joshi as education [...]
    ("b4e7e8c7-89d0-4115-9e3e-27c41e664c62", "7511c129-abdc-4416-96f5-99625cfdd59e"): (False, "agree"),  # SIT formed to look into allegations against Art of [...]
    ("b4e7e8c7-89d0-4115-9e3e-27c41e664c62", "856b61a1-1a73-477c-8019-96e0697979a2"): (False, "agree"),  # Student bodies to hold ‘Chalo Lok Bhavan’ protest on July 23
    # seed: Kent sneak home to send Joe Denly off with win
    ("5cb2dfc1-c7c9-4537-ac4b-273df5367880", "6c745b3f-4f88-4341-9a29-f9108e8f2325"): (False, "agree"),  # Joe Denly to retire from professional cricket at end [...]
    ("5cb2dfc1-c7c9-4537-ac4b-273df5367880", "72bac6da-7915-4a3c-96df-05503e0e9630"): (False, "agree"),  # Finch, Benjamin clinch Kent win over Northants
    ("5cb2dfc1-c7c9-4537-ac4b-273df5367880", "95c9f26c-40c2-410b-b93b-b6c0ffa88e12"): (False, "adj:tejas-said-same:high"),  # Kent sneak home in another tight run chase
    ("5cb2dfc1-c7c9-4537-ac4b-273df5367880", "127cce2f-f78a-4a09-a36d-791a170fc330"): (False, "agree"),  # Srikakulam to send 737 buses to Bhogapuram airport [...]
    ("5cb2dfc1-c7c9-4537-ac4b-273df5367880", "5eef6b84-c8d7-48b4-a5ee-c3b820d3d416"): (False, "agree"),  # Nelson, Gohar lead Middlesex past Yorkshire
    ("5cb2dfc1-c7c9-4537-ac4b-273df5367880", "6a46ff3e-a226-4244-9d18-c3b4779bc93b"): (False, "agree"),  # Hameed, McCann star as Notts hunt down Somerset
    ("5cb2dfc1-c7c9-4537-ac4b-273df5367880", "77c9d195-a921-47d2-8182-805ddbcc5c0a"): (False, "agree"),  # Goldsworthy century, Theedom's four tames Bears
    ("5cb2dfc1-c7c9-4537-ac4b-273df5367880", "7bea212b-ab88-439b-8f27-a7e4f11f44c6"): (False, "agree"),  # Joey Evison agrees Sussex switch
    ("5cb2dfc1-c7c9-4537-ac4b-273df5367880", "9add589d-a42a-4477-8c37-3e6b43eafd48"): (False, "agree"),  # Hurst, Stanley pull strings on Lancashire's Farington bow
    ("5cb2dfc1-c7c9-4537-ac4b-273df5367880", "a2108635-4f31-410d-892c-64f8b1a5e0d1"): (False, "agree"),  # Bean's counter secures tight Yorkshire win in Neath
    # seed: Kumkis to be deployed to reduce elephant-human conflict in Manyam
    ("a53765c2-31d2-444e-9457-aa22dd844796", "464d1b11-fe55-489a-8f78-feff3f6e4d9e"): (False, "agree"),  # जानिए कैसे दो हाथियों की जोड़ी संभालेगी दो राज्यों की सरहद
    ("a53765c2-31d2-444e-9457-aa22dd844796", "605d4958-90ce-4827-a237-93f1d4a16a43"): (False, "agree"),  # Kerala government to install 60 km of solar fencing in [...]
    ("a53765c2-31d2-444e-9457-aa22dd844796", "d8925bb0-e003-4098-8938-682b1ff4f12c"): (False, "agree"),  # Local bodies identified as human-wildlife conflict [...]
    ("a53765c2-31d2-444e-9457-aa22dd844796", "0e136012-e0ea-4e9b-b04b-bc882b96f8e0"): (False, "agree"),  # A.P. to get four female tigers from Maharashtra and [...]
    ("a53765c2-31d2-444e-9457-aa22dd844796", "1963be9f-706e-4c16-9acf-f721f0a4e90b"): (False, "agree"),  # ‘Telugu Mahotsavam’ to be annual event, says Minister [...]
    ("a53765c2-31d2-444e-9457-aa22dd844796", "288ec841-b74b-412e-9647-d00a5300bc19"): (False, "agree"),  # Minister visits six-year-old girl undergoing cancer [...]
    ("a53765c2-31d2-444e-9457-aa22dd844796", "3fda782f-6882-4df8-ad51-0c55d6032abd"): (False, "agree"),  # A.P. Deputy CM Pawan Kalyan stresses awareness drive [...]
    ("a53765c2-31d2-444e-9457-aa22dd844796", "6fa078c6-fb7b-46ec-af2d-4c58adcb83b6"): (False, "agree"),  # Forest dept. begins process to tranquilise and capture [...]
    ("a53765c2-31d2-444e-9457-aa22dd844796", "be886ced-81dd-4b72-b512-09943cb77023"): (False, "agree"),  # Human-wildlife conflict escalates across Kannur
    ("a53765c2-31d2-444e-9457-aa22dd844796", "cdce0e8c-13d8-432b-b946-66fd241ecb3d"): (False, "agree"),  # Heavy Security Deployed At Jantar Mantar As CJP [...]
    # seed: Leopard that attacked poultry captured in Forest dept cage in Kerala’s Thrissur
    ("16714d9f-6115-456e-a7d0-6e201b5b88b5", "255ae011-8912-40bc-82e3-86206b27bc0a"): (False, "agree"),  # Gaur kills 68-year-old at Kulathupuzha in Kerala
    ("16714d9f-6115-456e-a7d0-6e201b5b88b5", "47754dc9-b5c3-4979-bfb3-6d8b261fe6c7"): (False, "agree"),  # Another tanker attacked in Strait of Hormuz as US [...]
    ("16714d9f-6115-456e-a7d0-6e201b5b88b5", "605d4958-90ce-4827-a237-93f1d4a16a43"): (False, "agree"),  # Kerala government to install 60 km of solar fencing in [...]
    ("16714d9f-6115-456e-a7d0-6e201b5b88b5", "6fa078c6-fb7b-46ec-af2d-4c58adcb83b6"): (False, "adj:tejas-said-same:high"),  # Forest dept. begins process to tranquilise and capture [...]
    ("16714d9f-6115-456e-a7d0-6e201b5b88b5", "71c3dcef-3ba1-4cf1-a1ae-45ea02600e78"): (False, "agree"),  # Drones, CCTV cameras deployed to trace tiger after [...]
    ("16714d9f-6115-456e-a7d0-6e201b5b88b5", "b3df1d46-2884-418b-9e47-acf208bf4de8"): (False, "agree"),  # Live fence against wild boar claims farmer’s life near [...]
    ("16714d9f-6115-456e-a7d0-6e201b5b88b5", "c08cdd68-741e-401f-880e-c512ece2ee91"): (False, "agree"),  # BJP protests not informing Thrissur MP Suresh Gopi [...]
    ("16714d9f-6115-456e-a7d0-6e201b5b88b5", "d3b16534-d748-4e19-9582-bf26ad7f5fe3"): (False, "agree"),  # Kasimedu fishermen urge CM Vijay to retrieve 7 boats [...]
    ("16714d9f-6115-456e-a7d0-6e201b5b88b5", "f5fb1b17-a8b7-4bd4-b27d-3ea8b47ae1fc"): (False, "agree"),  # Three arrested for poaching in Vellore
    ("16714d9f-6115-456e-a7d0-6e201b5b88b5", "f999ad4b-c170-4513-92ce-20dde214ce14"): (False, "agree"),  # Karnataka govt officer attacked for excluding [...]
    # seed: Lopes Cabral's Stunning Strike Against Argentina Voted Best Goal Of WC 2026
    ("f61c4d73-d5a4-4a86-bd40-629aa33a7c05", "06726a0a-f739-4850-aa1d-eedd3adefdaa"): (False, "agree"),  # 'I'm sorry': Why Argentina's assistant coach [...]
    ("f61c4d73-d5a4-4a86-bd40-629aa33a7c05", "0d3f5280-5128-4d49-aa42-9d65a42f8c1d"): (False, "agree"),  # Sooryavanshi stays confident amid 'several ups and downs'
    ("f61c4d73-d5a4-4a86-bd40-629aa33a7c05", "17a5e56b-551e-4af6-8e22-4784a3e55bca"): (False, "agree"),  # Sooryavanshi the star as India complete 3-0 sweep
    ("f61c4d73-d5a4-4a86-bd40-629aa33a7c05", "20a45197-1513-4997-80a1-b846e9e33edc"): (False, "agree"),  # 'Busy planting seeds of hate': FIFA backs Trump- [...]
    ("f61c4d73-d5a4-4a86-bd40-629aa33a7c05", "29ef53e0-06c2-4378-a620-c2e48f9258cf"): (False, "agree"),  # Post Pradhan’s resignation, protestors in Chennai say [...]
    ("f61c4d73-d5a4-4a86-bd40-629aa33a7c05", "346a437b-ab74-4097-9b00-dfabc2134221"): (False, "agree"),  # World Cup rights row: Wales withdraw support for [...]
    ("f61c4d73-d5a4-4a86-bd40-629aa33a7c05", "3b6d6d9d-cb06-4498-8808-84cd7c16c916"): (False, "agree"),  # Ravindra, Ferguson inspire Welsh Fire with Kiwi verve
    ("f61c4d73-d5a4-4a86-bd40-629aa33a7c05", "45d8ad13-e18d-479a-8ce6-6b4d1ff90341"): (False, "agree"),  # How South African legend inspired Collins Saliboko’s [...]
    ("f61c4d73-d5a4-4a86-bd40-629aa33a7c05", "6273411b-6cde-4fbf-b345-44d1e6113fd7"): (False, "agree"),  # Thousands Remain In Spain's Ceuta After Moroccan Border Rush
    ("f61c4d73-d5a4-4a86-bd40-629aa33a7c05", "6b561be5-a06a-464b-aff2-8a11f8e3d26f"): (False, "agree"),  # सेउटा में विदेश से आकर फंसे 800 नाबालिग बच्चे, मां-बाप लापता
    # seed: M&M Financial Q1 Review: Brokerages Raise Target Prices After Beat
    ("dcb4c1c6-a6bd-4acf-967b-daf852774e72", "590594f2-310b-43bc-92a4-a6f6a7d44de1"): (False, "agree"),  # TVS Motor's Margin Story Has Changed. Brokerages Think [...]
    ("dcb4c1c6-a6bd-4acf-967b-daf852774e72", "e1796a55-3198-4d7e-86bd-3f87926f865b"): (False, "agree"),  # Nestlé India's Q1 Blowout: Morgan Stanley Eyes Near- [...]
    ("dcb4c1c6-a6bd-4acf-967b-daf852774e72", "1b490d60-0d2d-4754-bd71-e92d0725cb2a"): (False, "agree"),  # Equitas SFB Q1 Results: Lender Swings To Profit As NII [...]
    ("dcb4c1c6-a6bd-4acf-967b-daf852774e72", "276bae65-5994-411e-baa8-bc7203f7d16b"): (False, "agree"),  # Citi Taps Bank Of America's Rohan Sen As Head Of Tech [...]
    ("dcb4c1c6-a6bd-4acf-967b-daf852774e72", "38d74cbe-cdf4-4775-a930-51cc39bfca56"): (False, "agree"),  # Bajaj Auto Shares Hit Fresh 52-Week High After Q1 [...]
    ("dcb4c1c6-a6bd-4acf-967b-daf852774e72", "62239970-0ec2-4651-a70c-e6c1716a6386"): (False, "agree"),  # BEL To Canara Bank - Check HDFC Securities' New [...]
    ("dcb4c1c6-a6bd-4acf-967b-daf852774e72", "8976bb39-c493-41bd-b07f-778bad7a233a"): (False, "agree"),  # ED questions accused in Valappad financial fraud case
    ("dcb4c1c6-a6bd-4acf-967b-daf852774e72", "9bba809a-70b4-42c0-bb7a-c45e9773ba80"): (False, "agree"),  # Sona Comstar's Denso Deal Opens A Bigger EV [...]
    ("dcb4c1c6-a6bd-4acf-967b-daf852774e72", "a7377c50-44e1-40df-88eb-d23bac4d5f8b"): (False, "agree"),  # TSMC to Raise Chip Prices by 10 Percent Next Year: Report
    ("dcb4c1c6-a6bd-4acf-967b-daf852774e72", "a978b964-2d2a-49de-aa05-ffda8927e93f"): (False, "agree"),  # Bandhan Bank Shares Fall Over 10% After Q1 Result Even [...]
    # seed: Madras University Syndicate extends term of Registrar by two years, clears [...]
    ("44caf586-c1e7-4c4a-b33a-e9c0330a9e2e", "41004ece-10a4-4065-af72-de55edd0c93c"): (False, "agree"),  # Kerala University Syndicate explores PSC recruitment [...]
    ("44caf586-c1e7-4c4a-b33a-e9c0330a9e2e", "adb91941-fa3d-4ad9-8672-65b1735ee860"): (False, "agree"),  # Kannur University Syndicate orders probe into K-Reap [...]
    ("44caf586-c1e7-4c4a-b33a-e9c0330a9e2e", "04e3af91-9d85-49ad-b399-bb0520cabb76"): (False, "agree"),  # T.N. in the process of identifying site to build AI [...]
    ("44caf586-c1e7-4c4a-b33a-e9c0330a9e2e", "0b68a4c2-9a7d-49ab-8280-d37602634033"): (False, "agree"),  # Trust biggest challenge in preventing paper leaks, [...]
    ("44caf586-c1e7-4c4a-b33a-e9c0330a9e2e", "1fa1ad37-7d67-4e89-bb1f-5842710f0073"): (False, "agree"),  # ಆನ್‌ಲೈನ್‌ನಲ್ಲಿ ನೀಟ್ ಪರೀಕ್ಷೆ:ನಿಲೇಕಣಿ ಸಲಹೆ [...]
    ("44caf586-c1e7-4c4a-b33a-e9c0330a9e2e", "461e11e6-448c-49ba-9406-4cff91162a24"): (False, "agree"),  # Maharashtra doctors announce boycott after GR nod to [...]
    ("44caf586-c1e7-4c4a-b33a-e9c0330a9e2e", "467a1d7f-1ca2-4526-905c-8434b0a8497e"): (False, "agree"),  # Madras High Court to take up Vice-Chancellor [...]
    ("44caf586-c1e7-4c4a-b33a-e9c0330a9e2e", "4b8bac03-3849-43d9-8864-67202ae7137b"): (False, "agree"),  # Central Information Commission directs IITs to form [...]
    ("44caf586-c1e7-4c4a-b33a-e9c0330a9e2e", "5e35547f-d652-46a9-aee3-9f773f089009"): (False, "agree"),  # TN govt forms expert committee to advise on mitigating [...]
    ("44caf586-c1e7-4c4a-b33a-e9c0330a9e2e", "73f5a3c1-0a03-4a07-8805-fbb667e06ef3"): (False, "agree"),  # Five-star Seales extends Pakistan's overseas woes in [...]
    # seed: Molineux's spin strangle maintains Brave's perfect start
    ("3bfff362-b296-4ff6-83f8-5e652981a8ef", "10c7ee9c-13bf-4ec4-8e1e-7b0a30d067d4"): (False, "agree"),  # Craig wins the Overton battle to seal Rockets win
    ("3bfff362-b296-4ff6-83f8-5e652981a8ef", "07acb754-96d8-40d4-bf17-04ad4b45194b"): (False, "agree"),  # Dunkley, Sciver-Brunt fly as Rockets eclipse Sunrisers
    ("3bfff362-b296-4ff6-83f8-5e652981a8ef", "3f45dd49-1889-4aea-af29-a136ee957888"): (False, "agree"),  # Issy Wong, Jemimah Rodrigues carry Brave to second win
    ("3bfff362-b296-4ff6-83f8-5e652981a8ef", "5f7d2d4f-f509-4235-9e7f-c7fe6626cf1c"): (False, "agree"),  # Captain Willey takes Northants into final with scrappy [...]
    ("3bfff362-b296-4ff6-83f8-5e652981a8ef", "6f8d85a1-2647-4feb-87a8-293eb7529c25"): (False, "agree"),  # Lee, Bouchier make it four in four for Brave
    ("3bfff362-b296-4ff6-83f8-5e652981a8ef", "8d1f7ca9-76cf-4e3b-8331-1a6b8a86b8e8"): (False, "agree"),  # Will West Indies turn to Hetmyer to tackle their spin woes?
    ("3bfff362-b296-4ff6-83f8-5e652981a8ef", "9d0e6858-dffa-4710-89a8-0c88de8abd40"): (False, "agree"),  # Welsh Fire ruin Southern Brave's perfect start
    ("3bfff362-b296-4ff6-83f8-5e652981a8ef", "b31afb7b-aca6-4513-82c6-1b41caafedce"): (False, "agree"),  # Libby upstages De Caires as Worcestershire end [...]
    ("3bfff362-b296-4ff6-83f8-5e652981a8ef", "b921ce5a-aaff-4e8d-b05f-cc316dbf727b"): (False, "agree"),  # Livingstone's all-round efforts in vain as Super [...]
    ("3bfff362-b296-4ff6-83f8-5e652981a8ef", "cf1657d1-e2e9-4f49-9491-c63c3a95ad25"): (False, "agree"),  # Dunkley, Gardner end Super Giants' perfect start
    # seed: More Chinese investment good for wider relationship, says India’s envoy to China
    ("f59d4c14-f75a-411f-ab41-3ec6786654ac", "433ea28c-6ec2-4020-9bf1-5b7306c4abb3"): (False, "agree"),  # Border peace prerequisite for normal ties, Jaishankar [...]
    ("f59d4c14-f75a-411f-ab41-3ec6786654ac", "68a97fbf-0e7e-450c-8ea2-866ef349290e"): (False, "agree"),  # Quad backs peace, stability amid fresh Philippines- [...]
    ("f59d4c14-f75a-411f-ab41-3ec6786654ac", "7b865c52-a87e-41f1-b8f4-09360686aa68"): (False, "agree"),  # China "Ready" To Handle Sensitive Issues With India, [...]
    ("f59d4c14-f75a-411f-ab41-3ec6786654ac", "1dd83a17-a4e4-4105-9e50-383ab60b1e53"): (False, "agree"),  # US Iran war news LIVE: US strikes Iran for 11th [...]
    ("f59d4c14-f75a-411f-ab41-3ec6786654ac", "345d32a3-0303-4c3b-bc6d-dfee5d75f9d4"): (False, "agree"),  # Good News For iPhone Users: Apple To Launch 'Upgrade' [...]
    ("f59d4c14-f75a-411f-ab41-3ec6786654ac", "8c36d668-4f4c-455e-af72-010aa1ea3a20"): (False, "agree"),  # India summons Russian envoy, protests hit that killed [...]
    ("f59d4c14-f75a-411f-ab41-3ec6786654ac", "9ea4b562-dadd-458f-a3d9-c5af21a41d5a"): (False, "agree"),  # India, U.S. note ‘substantial progress’ on trade deal [...]
    ("f59d4c14-f75a-411f-ab41-3ec6786654ac", "be8b7fe4-ea75-4ff7-b660-41612822550e"): (False, "agree"),  # Relationship ending without marriage doesn't amount to [...]
    ("f59d4c14-f75a-411f-ab41-3ec6786654ac", "c0c54cb0-3783-4fa0-a882-db35df86ce53"): (False, "agree"),  # नेपाल के PM का यू-टर्न, भारत और चीन के राजदूतों से [...]
    ("f59d4c14-f75a-411f-ab41-3ec6786654ac", "c2c7bdc9-a8af-45ed-a67c-4d3d5917c3ad"): (False, "agree"),  # NSA Ajit Doval holds talks with Saudi foreign minister [...]
    # seed: Mounting losses force farmers in Karnataka’s Kolar district to chop down mango trees
    ("879da918-6a07-4460-b0a3-6bf2902a836d", "80ddc870-80ea-4a05-b837-fb3aabdf565e"): (False, "agree"),  # Lemon farmers in Nellore urged to take crop insurance [...]
    ("879da918-6a07-4460-b0a3-6bf2902a836d", "ae53f752-c287-4b30-8705-746a4cd3e07b"): (False, "agree"),  # Farmer ends life due to crop loss, mounting debts in [...]
    ("879da918-6a07-4460-b0a3-6bf2902a836d", "15d32d75-9d3a-48a1-bcb5-a84c36da55a7"): (False, "agree"),  # Remove hazardous trees near schools, says Kerala Minister
    ("879da918-6a07-4460-b0a3-6bf2902a836d", "345003d5-61ac-4264-8845-cdfe03847f20"): (False, "agree"),  # Madanapalle tomato prices remain higher
    ("879da918-6a07-4460-b0a3-6bf2902a836d", "3d8cd1f9-25ea-4de0-a58f-e758b37f18b6"): (False, "agree"),  # Iran’s $23 billion oil cushion: Can Trump’s sanctions [...]
    ("879da918-6a07-4460-b0a3-6bf2902a836d", "77e79ad5-d40e-417e-9795-aad47bd0ad57"): (False, "agree"),  # ವಕೀಲರ ಭವನಕ್ಕೆ ಜಾಗ ಮಂಜೂರು, ₹20 ಲಕ್ಷ ಅನುದಾನ ಭರವಸೆ
    ("879da918-6a07-4460-b0a3-6bf2902a836d", "81f361bb-143d-4e50-a864-359a1256ae9f"): (False, "agree"),  # Weak Southwest monsoon hits farmers in Nilgiris
    ("879da918-6a07-4460-b0a3-6bf2902a836d", "84c5527f-5a5e-4355-9789-5be1c724a221"): (False, "agree"),  # Kollam district administration cracks down on illegal [...]
    ("879da918-6a07-4460-b0a3-6bf2902a836d", "84ed99fe-057f-4cf9-96db-90b2525c3f41"): (False, "agree"),  # Ladakh’s organic push faces first big test after [...]
    ("879da918-6a07-4460-b0a3-6bf2902a836d", "a001837c-410a-44a9-b0c1-aeeff8c2b4c7"): (False, "agree"),  # ಚಿಕ್ಕಮಗಳೂರು ಬೆಳೆ ವಿಮಾ ಯೋಜನೆಗೆ ಜುಲೈ 31 ಕೊನೆಯ ದಿನ
    # seed: Mumbai estate agent held for duping cancer patient of Rs 40 lakh
    ("597af7c6-8b65-4a0e-999f-960e20421e71", "2022a00a-ba0a-4194-a99d-7f73384cb09c"): (False, "agree"),  # 10 investors duped of Rs 1.2 crore in forex trading [...]
    ("597af7c6-8b65-4a0e-999f-960e20421e71", "31770c5e-20b1-4471-9386-1156a978c524"): (False, "agree"),  # Bengaluru: Delivery agent held for stripping inside [...]
    ("597af7c6-8b65-4a0e-999f-960e20421e71", "45d76cc7-6d65-4dcb-a979-1c151dbc90c8"): (False, "agree"),  # PSI arrested for conniving with conman who [...]
    ("597af7c6-8b65-4a0e-999f-960e20421e71", "56ccb911-04e1-408f-8b3a-0c050a3e2f19"): (False, "agree"),  # Ambulance with patient stranded for 50 minutes in Gzb [...]
    ("597af7c6-8b65-4a0e-999f-960e20421e71", "64c5bd9c-ee7f-4ef7-91b6-151c475e3edc"): (False, "agree"),  # Mumbai man loses ₹1.64 crore to scammers, mistakes [...]
    ("597af7c6-8b65-4a0e-999f-960e20421e71", "8a05c9cb-fe16-4ba3-85b7-eabc5762b256"): (False, "agree"),  # Wife wins tax battle over husband’s Rs 80 lakh [...]
    ("597af7c6-8b65-4a0e-999f-960e20421e71", "c4c8690d-1643-42bc-8ff6-8eeb6b9403c5"): (False, "agree"),  # Who Is Patrick Yaroch? FBI Agent Held Over Alleged $1 [...]
    ("597af7c6-8b65-4a0e-999f-960e20421e71", "cafbca9d-5a73-450c-b8b1-7fa0cbf8f68f"): (False, "agree"),  # Record 2.73 lakh register for NEET-PG 2026; exam to be [...]
    ("597af7c6-8b65-4a0e-999f-960e20421e71", "cb46090d-eb3e-49db-a1aa-882f20c251d1"): (False, "agree"),  # Medical college assault case: Patient's family lodge [...]
    ("597af7c6-8b65-4a0e-999f-960e20421e71", "dca4394d-a1a6-4482-8792-09427683f6fe"): (False, "agree"),  # Bombay high court grants interim relief to developer [...]
    # seed: NDA govt. committed to protecting A.P. farmers’ interests, says Agriculture [...]
    ("fe0460ed-c98c-40a9-a82e-5518b59c8bc0", "5f92127f-e4cf-4167-bd6d-c046df4e9327"): (False, "agree"),  # Centre, Andhra Pradesh announce relief package for [...]
    ("fe0460ed-c98c-40a9-a82e-5518b59c8bc0", "33cb0135-df34-4613-9f78-b2cdd359e526"): (False, "agree"),  # CM seeks Centre’s support for aquaculture, tobacco [...]
    ("fe0460ed-c98c-40a9-a82e-5518b59c8bc0", "33e7a5d0-1933-44d4-aa67-ae4fdd5ae9a2"): (False, "agree"),  # Police committed to making Sri Sathya Sai a crime-free [...]
    ("fe0460ed-c98c-40a9-a82e-5518b59c8bc0", "46866a04-fc9c-429e-aaf2-92add296cf9f"): (False, "agree"),  # AP records 400% surge in renewable energy capacity [...]
    ("fe0460ed-c98c-40a9-a82e-5518b59c8bc0", "52d00871-0c39-4285-8343-115df6da552b"): (False, "agree"),  # El Nino impact likely to intensify in coming months: [...]
    ("fe0460ed-c98c-40a9-a82e-5518b59c8bc0", "5f141db2-7f7c-4d2f-9068-4ccbd30c7664"): (False, "agree"),  # Govt. allocates ₹641 cr. for Vamsadhara phase-2 project
    ("fe0460ed-c98c-40a9-a82e-5518b59c8bc0", "65432286-4db7-40ce-89b4-76afdf368f9b"): (False, "agree"),  # As TVK government prepares its first agriculture [...]
    ("fe0460ed-c98c-40a9-a82e-5518b59c8bc0", "73db057a-567d-43fe-a9fa-f1871235b584"): (False, "agree"),  # Farmers block NH-16 in Ongole seeking remunerative [...]
    ("fe0460ed-c98c-40a9-a82e-5518b59c8bc0", "940ba6d6-5869-4bbe-9544-39b94845af7b"): (False, "agree"),  # "100% Committed To Discussing NEET": Dharmendra Pradhan
    ("fe0460ed-c98c-40a9-a82e-5518b59c8bc0", "a62b3c33-d77f-4c80-b19d-835665a9eb5e"): (False, "agree"),  # Andhra fishermen asked not to venture into sea as [...]
    # seed: Nandi hills Monsoon Marathon: Vehicle movement likely to be restricted on [...]
    ("7674f7a3-b21a-412f-8c39-d6e2c828f26b", "c1ef2696-de8a-40e7-b947-4c8890e2cdda"): (False, "agree"),  # HIV awareness quiz, marathon to be held in Ernakulam
    ("7674f7a3-b21a-412f-8c39-d6e2c828f26b", "61e5bed1-b19f-4121-a091-8a2360b21e4b"): (False, "agree"),  # Govt moots mandatory vehicle-to-vehicle communication [...]
    ("7674f7a3-b21a-412f-8c39-d6e2c828f26b", "6e74e1ea-dde5-4a5a-8c94-39cf18fe7b21"): (False, "agree"),  # Centre tells SC fresh tribunal reforms Bill likely in [...]
    ("7674f7a3-b21a-412f-8c39-d6e2c828f26b", "79c8f641-be89-47e4-b342-f29e5316d7a6"): (False, "agree"),  # Nandyal’s Catch the Rain works find mention in Modi’s [...]
    ("7674f7a3-b21a-412f-8c39-d6e2c828f26b", "8c2c6a04-a468-4e01-ac37-9b5a52a794e2"): (False, "agree"),  # Seed Access Road, Steel Bridge to be inaugurated in August
    ("7674f7a3-b21a-412f-8c39-d6e2c828f26b", "9d8a8631-94af-4edf-a1d5-bb072d53e4cb"): (False, "agree"),  # Karnataka rain: Holiday declared in Joida, Dandeli taluks
    ("7674f7a3-b21a-412f-8c39-d6e2c828f26b", "b358e859-76c5-4be1-923a-1aac143441de"): (False, "agree"),  # Monsoon Session of Karnataka Legislature to begin on [...]
    ("7674f7a3-b21a-412f-8c39-d6e2c828f26b", "d75cbb56-f7fa-4561-b2c5-014055997fb1"): (False, "agree"),  # Holiday declared in Kannur
    ("7674f7a3-b21a-412f-8c39-d6e2c828f26b", "f802debe-fbdc-4c6d-ab18-dc17ad68cf33"): (False, "agree"),  # Karnataka: Vehicle price hike from August 1 to [...]
    # seed: Odisha man held with over 6 kg marijuana at Cherlapalli railway station
    ("0c4f8491-da18-4ff3-980d-91a6c3fb54d7", "4332b2c6-f112-49a5-b7bc-a1fab33758be"): (False, "agree"),  # Hindi name board at Coimbatore North railway station [...]
    ("0c4f8491-da18-4ff3-980d-91a6c3fb54d7", "05f545bb-b60c-4be9-a961-1cbf3abc68bb"): (False, "agree"),  # चोरी की रकम के साथ मनीष को मंदिर से बाहर ले जाता था [...]
    ("0c4f8491-da18-4ff3-980d-91a6c3fb54d7", "0a50f9ae-2c31-409c-8d93-e74b002335dd"): (False, "agree"),  # Pak woman escapes Nepal jail, enters India illegally; [...]
    ("0c4f8491-da18-4ff3-980d-91a6c3fb54d7", "1e8f6cad-a010-4ef8-9653-ee7effdb4de5"): (False, "agree"),  # बालिका गृह की जाली तोड़ दूसरी मंजिल से दुपट्टों के [...]
    ("0c4f8491-da18-4ff3-980d-91a6c3fb54d7", "3f07260c-796f-475e-9520-b901e2b07f50"): (False, "agree"),  # Excise officials seize over 119 kg ganja in separate [...]
    ("0c4f8491-da18-4ff3-980d-91a6c3fb54d7", "45f4942c-8aed-4bb5-b4e1-1e09a471f053"): (False, "agree"),  # Kishan Reddy opens Komuravelli Railway station, [...]
    ("0c4f8491-da18-4ff3-980d-91a6c3fb54d7", "7f2a27ea-d04a-4bb3-9f1e-cbe149f16f17"): (False, "agree"),  # Excise STF seizes jaggery worth ₹2.5 lakh meant for [...]
    ("0c4f8491-da18-4ff3-980d-91a6c3fb54d7", "8805aaeb-3afa-4e9e-8437-835646facf42"): (False, "agree"),  # Man held from Rajasthan in Delhi fraud case
    ("0c4f8491-da18-4ff3-980d-91a6c3fb54d7", "b26e5b3d-f947-4682-90d0-4fc643422ee6"): (False, "agree"),  # Seven arrested, nearly 48 kg of ganja seized in [...]
    ("0c4f8491-da18-4ff3-980d-91a6c3fb54d7", "cd001737-3c3a-4f54-a519-cf872f4d73c1"): (False, "agree"),  # Crackdown on illegal parking outside Kerala’s Kottayam [...]
    # seed: OpenAI Says Its AI Models Escaped Sandbox, Targeted Hugging Face to Cheat Benchmark
    ("a15afe1c-2adf-4f84-9ad1-54298ea91915", "9f547fa0-4299-4f4a-9205-40f8edc86800"): (False, "agree"),  # OpenAI's rogue AI agent that hacked world's biggest [...]
    ("a15afe1c-2adf-4f84-9ad1-54298ea91915", "1f70d001-95df-435d-9419-1e6a11809c8f"): (True, "adj:vijay-said-same:high"),  # World's Largest AI Model Repository Hugging Face [...]
    ("a15afe1c-2adf-4f84-9ad1-54298ea91915", "d680f446-e35b-4500-b836-35d10751c4ea"): (True, "adj:vijay-said-same:high"),  # OpenAI Says Its Models Accidentally Hacked Hugging Face
    ("a15afe1c-2adf-4f84-9ad1-54298ea91915", "85a42e3e-e677-4e0b-b6b7-0cbcca82cec1"): (False, "agree"),  # OpenAI’s GPT-Red Automates Prompt Injection Testing to [...]
    ("a15afe1c-2adf-4f84-9ad1-54298ea91915", "90888080-7026-4448-97a3-5b5024935b09"): (False, "agree"),  # BJP forced Pradhan to resign as Gen Z targeted Modi’s [...]
    ("a15afe1c-2adf-4f84-9ad1-54298ea91915", "9716c4f0-ebe0-4e87-81f6-0086db3c6623"): (False, "agree"),  # World Applied Anthropology Congress concludes at ICRISAT
    ("a15afe1c-2adf-4f84-9ad1-54298ea91915", "abf2cf6b-10cb-41cc-bbc8-e42dd6f135b1"): (False, "agree"),  # NVIDIA Forms 37-Member Open Secure AI Alliance and [...]
    ("a15afe1c-2adf-4f84-9ad1-54298ea91915", "b56c2182-26f1-4bd0-8f31-3b6c83856094"): (False, "agree"),  # OpenAI confirms ChatGPT is down worldwide
    ("a15afe1c-2adf-4f84-9ad1-54298ea91915", "d2723985-8a3c-4004-851e-587ee5863719"): (False, "agree"),  # OpenAI's Sam Altman says AI is now at 'singularity' [...]
    ("a15afe1c-2adf-4f84-9ad1-54298ea91915", "d77e8a9e-0f16-4683-b665-a9b57cb46457"): (False, "agree"),  # क्या एआई को लेकर सच हो रही आशंका?: ओपनएआई के मॉडल ने [...]
    # seed: Put drone policy on hold until inclusive and transparent review, BJP MP urges [...]
    ("c23ae7f0-bb69-4859-9364-0d372aa23ccc", "00633308-c97f-453c-910e-7d33f84c271c"): (False, "agree"),  # ರಾಹುಲ್‌ ಗಾಂಧಿ ವಿರುದ್ಧ ಅಸಂಸದೀಯ ಪದಬಳಕೆ ಆರೋಪ: ಕ್ಷಮೆಗೆ [...]
    ("c23ae7f0-bb69-4859-9364-0d372aa23ccc", "0214e2a8-8467-44de-a26a-1c520550c1eb"): (False, "agree"),  # स्पीकर ने कांग्रेस-बीजेपी को सदन में दिया बोलने का [...]
    ("c23ae7f0-bb69-4859-9364-0d372aa23ccc", "2bd009d4-b9e9-44ad-9edf-ce2f9de976a0"): (False, "agree"),  # Home Minister Anitha seeks apology from Jagan over [...]
    ("c23ae7f0-bb69-4859-9364-0d372aa23ccc", "4b25fce9-7a39-45de-91d9-e087fd28266a"): (False, "agree"),  # DSS demands transparent probe into alleged NEET paper leak
    ("c23ae7f0-bb69-4859-9364-0d372aa23ccc", "5dca689c-eab6-4a68-8a53-5cb8a5b2f1b2"): (False, "agree"),  # IAF chief calls for faster development, induction of [...]
    ("c23ae7f0-bb69-4859-9364-0d372aa23ccc", "61f0d591-9e92-420e-90ca-1f5d60c62849"): (False, "agree"),  # Mumbai’s Film City to be redeveloped
    ("c23ae7f0-bb69-4859-9364-0d372aa23ccc", "674dca02-b681-4f89-8e2c-0a68a230cf2f"): (False, "agree"),  # Health Minister orders 10-year review into medicine [...]
    ("c23ae7f0-bb69-4859-9364-0d372aa23ccc", "6943e1db-3d05-4e1e-b18a-7523e05e625f"): (False, "agree"),  # WhatsApp reacts as multiple accounts, including in [...]
    ("c23ae7f0-bb69-4859-9364-0d372aa23ccc", "7e2a95f6-ecf6-4f4f-ae9f-ef92eed30538"): (False, "agree"),  # Bombay HC seeks govt response to PM’s call for clay [...]
    ("c23ae7f0-bb69-4859-9364-0d372aa23ccc", "8eac4b36-e253-4a81-9792-f5d115dc6d40"): (False, "agree"),  # Minister Eshwar Khandre asks Karnataka BJP to get [...]
    # seed: Q1 Report Card: BofA Notes Strong 12% Nifty Earnings Growth Despite Isolated [...]
    ("363fd2e2-b6fd-4a3d-a6eb-0f8aedcb7227", "af362aca-dc88-4214-8f0e-ccda829023f7"): (False, "agree"),  # NTPC Green Shares Jump Nearly 6% After Strong Q1 [...]
    ("363fd2e2-b6fd-4a3d-a6eb-0f8aedcb7227", "24e68724-6a0d-470a-944e-fea7161cde32"): (False, "agree"),  # LIVE: GIFT Nifty Points To Gap-Down Open For Nifty, [...]
    ("363fd2e2-b6fd-4a3d-a6eb-0f8aedcb7227", "3482c856-ca5e-4fc1-90c5-0af7c304381d"): (False, "agree"),  # Q1 Results Today: Infosys, Indigo, Cipla, PVR Inox [...]
    ("363fd2e2-b6fd-4a3d-a6eb-0f8aedcb7227", "3ff253ad-b547-4cd5-8628-ab2143329d76"): (False, "agree"),  # Q1 Earnings Today: Adani Green, BPCL, IndusInd Bank, [...]
    ("363fd2e2-b6fd-4a3d-a6eb-0f8aedcb7227", "59af569f-95ed-493f-b028-9a7f1f2473d8"): (False, "agree"),  # Waaree Renewable Drops Over 6% As Q1 Margin Declines [...]
    ("363fd2e2-b6fd-4a3d-a6eb-0f8aedcb7227", "6ef76f44-9b95-49e5-8d05-9504ea5615a2"): (False, "agree"),  # Hudco Sees Strong Loan Growth, Targets Rs 65,000-Crore [...]
    ("363fd2e2-b6fd-4a3d-a6eb-0f8aedcb7227", "8b038bc3-bb92-4825-93ce-1aea0eca5121"): (False, "agree"),  # India's growth remains strong, but trade barriers [...]
    ("363fd2e2-b6fd-4a3d-a6eb-0f8aedcb7227", "9099aa0d-eacc-47ea-aee6-0889ee9c1e65"): (False, "agree"),  # Coforge Q1 Results: Net Profit Falls 15%, Revenue [...]
    ("363fd2e2-b6fd-4a3d-a6eb-0f8aedcb7227", "949eec85-06ad-4fc9-9041-288bec156e9d"): (False, "agree"),  # Radico Khaitan Q1 Results: Net Profit Rises 76%, [...]
    # seed: Q1 Results Today: HUL, L&T, Suzlon Energy Among 70+ Companies Announcing Earnings
    ("dc1981d5-72e2-4e4e-93b9-b75a46f61853", "3482c856-ca5e-4fc1-90c5-0af7c304381d"): (False, "agree"),  # Q1 Results Today: Infosys, Indigo, Cipla, PVR Inox [...]
    ("dc1981d5-72e2-4e4e-93b9-b75a46f61853", "50f5a5b5-77b8-47c2-83c2-e88cb2a75c81"): (False, "adj:tejas-said-same:high"),  # HUL Q1 Results: Net Profit Drops 3% To Rs 2,673 Crore, [...]
    ("dc1981d5-72e2-4e4e-93b9-b75a46f61853", "b7b76b93-6609-4bff-b7ea-1b66cdf874c1"): (False, "adj:tejas-said-same:high"),  # Suzlon Energy Q1 Results Today: Time, Dividend News, [...]
    ("dc1981d5-72e2-4e4e-93b9-b75a46f61853", "f96e8535-7066-4ab0-85b8-03c53a493f1c"): (False, "adj:tejas-said-same:high"),  # Suzlon Energy Q1 Results: Revenue Climbs 22%, But [...]
    ("dc1981d5-72e2-4e4e-93b9-b75a46f61853", "3ff253ad-b547-4cd5-8628-ab2143329d76"): (False, "agree"),  # Q1 Earnings Today: Adani Green, BPCL, IndusInd Bank, [...]
    ("dc1981d5-72e2-4e4e-93b9-b75a46f61853", "a8591f4e-256d-41c3-a839-0d8818fe5521"): (False, "adj:tejas-said-same:high"),  # HUL Q1 Results Explained: Five Pressure Points Behind [...]
    # seed: Right to walk safely: SC orders Centre to ensure pedestrian walkways, [...]
    ("78713a26-d04c-4277-9f1d-5c404f131543", "026b20d6-64a1-4a46-a2b5-07bd671ea738"): (True, "adj:vijay-said-same:high"),  # ರಸ್ತೆ ಇರುವಲ್ಲೆಲ್ಲ ಪಾದಚಾರಿ ಮಾರ್ಗ ಬೇಕು: ಸುಪ್ರೀಂ ಕೋರ್ಟ್
    ("78713a26-d04c-4277-9f1d-5c404f131543", "0b68a4c2-9a7d-49ab-8280-d37602634033"): (False, "agree"),  # Trust biggest challenge in preventing paper leaks, [...]
    ("78713a26-d04c-4277-9f1d-5c404f131543", "1b882ec1-b4f5-4353-bb98-4a86f3d7d545"): (False, "agree"),  # Encroachments demolished to provide easy access to [...]
    ("78713a26-d04c-4277-9f1d-5c404f131543", "43c141a0-e786-4ad9-891f-8a9df2fe724d"): (False, "agree"),  # Supreme Court upholds removal of commercial activity [...]
    ("78713a26-d04c-4277-9f1d-5c404f131543", "47d48bfd-a019-4134-bace-a09bdb567283"): (False, "agree"),  # ಕಟ್ಟಡ ತ್ಯಾಜ್ಯ ಎಲ್ಲೆಂದರಲ್ಲಿ ಎಸೆದು ಮಾಲಿನ್ಯ ಮಾಡೀರೀ ಜೋಕೆ, [...]
    ("78713a26-d04c-4277-9f1d-5c404f131543", "50252966-b753-46c5-b243-dee207ba5be0"): (False, "agree"),  # 'We're right on our way' - Jangoo gung-ho about West [...]
    ("78713a26-d04c-4277-9f1d-5c404f131543", "7ca2cb74-42d1-42a9-88f4-bb2574754116"): (False, "agree"),  # NEET row: Right to peaceful protest guaranteed, says [...]
    ("78713a26-d04c-4277-9f1d-5c404f131543", "82e65bd3-517c-451b-8593-153a19f5a668"): (False, "agree"),  # ‘How is database secured'? SC says will see what [...]
    ("78713a26-d04c-4277-9f1d-5c404f131543", "a6e8f22d-cf38-437d-bb02-fa33dc16bc56"): (False, "agree"),  # Speaker’s nod to Sena (UBT) MPs’ merger challenged in SC
    ("78713a26-d04c-4277-9f1d-5c404f131543", "be2b03c6-3431-4b2c-87ca-4ea32bc40f05"): (False, "agree"),  # Officials emphasise sustainable public transport [...]
    # seed: Round-the-clock water supply to Belagavi to resume, says commissioner
    ("a1819226-d6c4-472a-98a0-fee6acc0846b", "3526a777-6e9b-48cc-aed5-547897c14500"): (False, "agree"),  # Reduced rainfall in Maharashtra, Belagavi leads to [...]
    ("a1819226-d6c4-472a-98a0-fee6acc0846b", "3de5434d-68be-403b-9e46-81c97e2cd97e"): (False, "agree"),  # Heavy rain in Maharashtra leads to slight increase in [...]
    ("a1819226-d6c4-472a-98a0-fee6acc0846b", "5c93e0a6-9cf9-48aa-bb0d-3d5810048fbe"): (False, "agree"),  # Water supply to be disrupted for 24 hours in parts of [...]
    ("a1819226-d6c4-472a-98a0-fee6acc0846b", "67f03571-9ee8-478b-8650-852cbb420c74"): (False, "agree"),  # Kannada organisations seek action against BCC for [...]
    ("a1819226-d6c4-472a-98a0-fee6acc0846b", "7c3dde04-27a9-455f-9dd0-547a5a345444"): (False, "agree"),  # Water supply disruption in Benglauru on July 31
    ("a1819226-d6c4-472a-98a0-fee6acc0846b", "8620a580-166f-41d8-b40f-2bd33bd46d7b"): (False, "agree"),  # Water release for crops from Almatti dam begins
    ("a1819226-d6c4-472a-98a0-fee6acc0846b", "95423eae-2c75-43fe-92b7-202a3c96b23d"): (False, "agree"),  # Water levels in Krishna rise as Maharashtra and [...]
    ("a1819226-d6c4-472a-98a0-fee6acc0846b", "a1ea1062-da0c-42d9-8b50-10eab549a2fb"): (False, "agree"),  # Madanapalle secures ₹1,000 crore infra project to [...]
    ("a1819226-d6c4-472a-98a0-fee6acc0846b", "b2ec57b5-7889-4e26-abed-2b11bab036f4"): (False, "agree"),  # Interruption in water supply on August 5
    ("a1819226-d6c4-472a-98a0-fee6acc0846b", "d69c376e-b496-47a7-9638-5cab84cc04f0"): (False, "agree"),  # Outflow from Almatti increased to around 1.1 lakh cusecs
    # seed: Rowles 201 crushes England U19s before Basson wreaks havoc
    ("c36c3ff1-e17f-4a17-820c-e04e90a5e359", "608093c3-0e98-48a5-bd5e-5b494dcb7d5e"): (False, "agree"),  # England bowl; Kishan in for unwell Rahul
    ("c36c3ff1-e17f-4a17-820c-e04e90a5e359", "086fcf0c-6dff-44b5-9b33-a0f3a9822797"): (False, "agree"),  # Heavy rain wreaks havoc across India: Death toll in [...]
    ("c36c3ff1-e17f-4a17-820c-e04e90a5e359", "26ed01a3-18bd-4880-bd6f-2775629f1774"): (False, "agree"),  # Glamorgan's Welsh youngsters hit statement tons to [...]
    ("c36c3ff1-e17f-4a17-820c-e04e90a5e359", "35478a20-3886-4b95-b032-b81d85534602"): (False, "agree"),  # 22 killed as heavy rain wreaks havoc across Kashmir, [...]
    ("c36c3ff1-e17f-4a17-820c-e04e90a5e359", "4e1e0d63-e324-4d7a-a72b-f8a4b796377f"): (False, "agree"),  # England need urgent ODI turnaround as India eye series [...]
    ("c36c3ff1-e17f-4a17-820c-e04e90a5e359", "582c3287-40b8-4dfc-b777-639d94e7c395"): (False, "agree"),  # Joe Root happy to sacrifice ton for victory
    ("c36c3ff1-e17f-4a17-820c-e04e90a5e359", "5f7d2d4f-f509-4235-9e7f-c7fe6626cf1c"): (False, "agree"),  # Captain Willey takes Northants into final with scrappy [...]
    ("c36c3ff1-e17f-4a17-820c-e04e90a5e359", "6c745b3f-4f88-4341-9a29-f9108e8f2325"): (False, "agree"),  # Joe Denly to retire from professional cricket at end [...]
    ("c36c3ff1-e17f-4a17-820c-e04e90a5e359", "78f1ba4b-3cab-4545-bf7d-469311b997f2"): (False, "agree"),  # CA boss Greenberg 'open' to England-Australia Test in India
    ("c36c3ff1-e17f-4a17-820c-e04e90a5e359", "7f224abc-72c7-4872-8498-5f9b31da03e8"): (False, "agree"),  # Duckett 141 trumps Rohit 138 in Lord's run-fest
    # seed: Saurav Das defends viral party, dancing videos amid CJP backlash: ‘Language of [...]
    ("095ebf63-8da9-478b-a6cd-47887894980e", "24ec70a8-7362-49dd-9480-515d69774bd5"): (False, "agree"),  # 'CJP' के जश्न वाले वीडियो वायरल, जानिए देखकर क्या बोले [...]
    ("095ebf63-8da9-478b-a6cd-47887894980e", "43c141a0-e786-4ad9-891f-8a9df2fe724d"): (False, "agree"),  # Supreme Court upholds removal of commercial activity [...]
    ("095ebf63-8da9-478b-a6cd-47887894980e", "4d648c2e-3575-4ea7-9f10-24109b5b43b2"): (False, "agree"),  # We want withdrawal of FIRs, not just closure: CJP's [...]
    ("095ebf63-8da9-478b-a6cd-47887894980e", "4fb01c9f-526b-4522-bb65-c3e74e27dced"): (False, "agree"),  # Cockroach Janta Party protests | Collection of The [...]
    ("095ebf63-8da9-478b-a6cd-47887894980e", "6aa91264-963c-49a6-b8e4-c8aaf03b40fa"): (True, "adj:vijay-said-same:high"),  # 'Uncles and aunties can keep complaining': CJP party [...]
    ("095ebf63-8da9-478b-a6cd-47887894980e", "6b4cd43f-db6c-4e49-b8e4-d51bc8ecfd3f"): (False, "agree"),  # CJP protesters continue sit-in at Jantar Mantar; more [...]
    ("095ebf63-8da9-478b-a6cd-47887894980e", "6bc90c20-2bb0-49e1-acc0-21b22c5abbdf"): (False, "agree"),  # Sonam Wangchuk hails Vande Bharat Express as he [...]
    ("095ebf63-8da9-478b-a6cd-47887894980e", "8a61dfa2-4037-4b8d-9eb8-361966f48cd4"): (False, "agree"),  # CJP's Saurav Das on criticism for abusive slogans: [...]
    ("095ebf63-8da9-478b-a6cd-47887894980e", "a275df34-62a8-45dc-aeaf-9b44123c88f3"): (False, "agree"),  # CJP flags arrests of protesters in Assam, Bengal, [...]
    ("095ebf63-8da9-478b-a6cd-47887894980e", "ae00749c-0da9-4628-ba23-b4527c693fda"): (False, "agree"),  # States can withdraw FIRs against student protesters [...]
    # seed: Spider Man Brand New Day: कैसी रही 'स्पाइडर मैन- ब्रांड न्यू डे' की शुरुआत? [...]
    ("6b83708a-cc12-435c-bc8e-5435865eecf2", "20bb9610-762a-4e02-8525-827d9bd2f356"): (False, "agree"),  # ಸ್ಪೈಡರ್ ಮ್ಯಾನ್; 8 ಸೆಕೆಂಡ್‌ಗಳ ಚುಂಬನ ದೃಶ್ಯಕ್ಕೆ ಕತ್ತರಿ [...]
    ("6b83708a-cc12-435c-bc8e-5435865eecf2", "8ce26c4b-21ff-4829-8ffc-9847a790dd89"): (True, "adj:tejas-said-same:medium"),  # ₹300 ಕೋಟಿ ಗಳಿಸಿದ ‘ಸ್ಪೈಡರ್‌ ಮ್ಯಾನ್‌’
    ("6b83708a-cc12-435c-bc8e-5435865eecf2", "b497f823-1f5c-4177-9795-b9aea59cd285"): (False, "agree"),  # Spider-Man Brand New Day Theories: Sadie Sink’s [...]
    ("6b83708a-cc12-435c-bc8e-5435865eecf2", "26a31f25-6b2e-45e3-8e15-672b650eb10e"): (False, "agree"),  # Jana Nayagan: 5 दिन के बाद ‘जन नायकन’ की कमाई में [...]
    ("6b83708a-cc12-435c-bc8e-5435865eecf2", "5d3542db-5478-47f2-b807-f4602beb19f5"): (False, "agree"),  # ‘ಸ್ಪೈಡರ್ ಮ್ಯಾನ್’ ಹೊಸ ಚಿತ್ರಕ್ಕೆ ಸೆನ್ಸಾರ್ ಕತ್ತರಿ: 8 [...]
    ("6b83708a-cc12-435c-bc8e-5435865eecf2", "5e5cd0d9-8fa0-475b-ba04-06ab609cc0dd"): (False, "agree"),  # Spider-Man: Brand New Day Gets CBFC UA 13+ Certificate [...]
    ("6b83708a-cc12-435c-bc8e-5435865eecf2", "74d174ef-fed4-41c2-ab39-05cae903ec3b"): (False, "agree"),  # Quote of the day by Chris Evans: ‘All you really have [...]
    ("6b83708a-cc12-435c-bc8e-5435865eecf2", "f4c1dc44-1686-4664-8513-2038b05b8fa0"): (False, "agree"),  # Box Office: ‘द ओडिसी’ ने पार किया 150 करोड़ का आंकड़ा, [...]
    # seed: Supreme Court declines urgent listing of plea against police action during CJP [...]
    ("68ff78c5-452e-4c14-970b-07651ee29ef8", "613ee07d-8da9-4533-b9de-873ec21f1d5b"): (True, "agree"),  # ‘Don’t waste our time’: CJI declines urgent listing of [...]
    ("68ff78c5-452e-4c14-970b-07651ee29ef8", "2b278555-c181-43fc-a2d6-3c309be08a7b"): (False, "agree"),  # ನೀಟ್ ಪ್ರತಿಭಟನೆ, ಬಂಧಿತ 18 ವರ್ಷದೊಳಗಿನ ವಿದ್ಯಾರ್ಥಿಗಳ [...]
    ("68ff78c5-452e-4c14-970b-07651ee29ef8", "460bdb43-2628-41b7-9fdc-45d4889c0080"): (True, "agree"),  # CJP protest: 'Don't waste our time,' says CJI Surya [...]
    ("68ff78c5-452e-4c14-970b-07651ee29ef8", "ddd63ff6-9a01-4e23-986b-e4c0973f0b51"): (True, "agree"),  # ‘Don’t waste our time’: CJI Kant declines to take [...]
    ("68ff78c5-452e-4c14-970b-07651ee29ef8", "08f815b9-6d4d-4d1e-a568-9299fa9eddba"): (False, "agree"),  # CJI on police excess, pellet gun claims and message [...]
    ("68ff78c5-452e-4c14-970b-07651ee29ef8", "2528fb9e-b63b-495e-aabb-366359257fe4"): (True, "agree"),  # 'Don't want to watch videos': SC declines urgent [...]
    ("68ff78c5-452e-4c14-970b-07651ee29ef8", "51807914-8099-434f-859e-d5a5ef3880be"): (False, "agree"),  # Fadnavis orders withdrawal of cases against youths [...]
    ("68ff78c5-452e-4c14-970b-07651ee29ef8", "57b83751-90a1-4825-ad4b-db8bf0c8ff70"): (False, "agree"),  # Saurav Das’ single-word reaction to Supreme Court’s [...]
    ("68ff78c5-452e-4c14-970b-07651ee29ef8", "9b1a7750-0044-4401-87d9-13ad4e6dfa40"): (False, "agree"),  # ‘पैलेट गन, इलेक्ट्रिक बैटन और वकीलों पर हमला…’ पुलिस [...]
    ("68ff78c5-452e-4c14-970b-07651ee29ef8", "da4bbd00-ed2b-4185-8213-b346225dfa1f"): (False, "agree"),  # No action against CJP protesters: Delhi government
    # seed: T.N. in the process of identifying site to build AI City around Chennai: IT Minister
    ("04e3af91-9d85-49ad-b399-bb0520cabb76", "476e6984-a842-409b-bc7c-ac5043dfe955"): (False, "agree"),  # Govt. will take steps to create employment [...]
    ("04e3af91-9d85-49ad-b399-bb0520cabb76", "1edb23a4-a952-49c8-96d1-ea9617d4e42d"): (False, "agree"),  # CS wants comprehensive action plan to further [...]
    ("04e3af91-9d85-49ad-b399-bb0520cabb76", "46526919-75e6-492d-9780-285d1e736b07"): (False, "agree"),  # 50 OTT platforms disabled over the last two years | [...]
    ("04e3af91-9d85-49ad-b399-bb0520cabb76", "501cd2d7-8681-469a-b4b2-78c109f552f1"): (False, "agree"),  # Visakhapatnam airport commercial operations to shift [...]
    ("04e3af91-9d85-49ad-b399-bb0520cabb76", "56d0d18e-95d0-4333-866c-25c09e6cdd95"): (False, "agree"),  # Country’s ethos should reflect in curriculum of [...]
    ("04e3af91-9d85-49ad-b399-bb0520cabb76", "61f0d591-9e92-420e-90ca-1f5d60c62849"): (False, "agree"),  # Mumbai’s Film City to be redeveloped
    ("04e3af91-9d85-49ad-b399-bb0520cabb76", "628d4261-1878-4569-9383-f386961ef89e"): (False, "agree"),  # AI-powered software on the anvil to fast-track [...]
    ("04e3af91-9d85-49ad-b399-bb0520cabb76", "6ef10358-2c99-40e4-8d01-0158ae383c70"): (False, "agree"),  # Google Launches Gemini 3.5 Flash Cyber AI to Find and [...]
    ("04e3af91-9d85-49ad-b399-bb0520cabb76", "8307c0ec-8c4f-4c6d-b577-c86e944fa7c1"): (False, "agree"),  # Govt plans an AI matchmaker for jobs, skill demand [...]
    ("04e3af91-9d85-49ad-b399-bb0520cabb76", "9c928bd4-1810-471a-a8a5-ff772f481f32"): (False, "agree"),  # McCullum pledges to 'be around for the Hundred' in [...]
    # seed: TDB decides to stop procurement of ghee from outside for Sabarimala temple
    ("95eaf3cd-8213-41ae-bdd6-70bd1683edd2", "309c9768-c70f-4524-aad5-e583e284dc38"): (False, "agree"),  # Sabarimala ghee supply: No lapses on Milma’s side, [...]
    ("95eaf3cd-8213-41ae-bdd6-70bd1683edd2", "5405b17b-878a-4d71-b714-97e809d8476d"): (False, "agree"),  # Kerala HC approves appointment of Kandararu [...]
    ("95eaf3cd-8213-41ae-bdd6-70bd1683edd2", "0a471b1b-f433-4150-84d7-b07e838e6c0f"): (False, "agree"),  # Kerala earmarks ₹15 crore for road safety under [...]
    ("95eaf3cd-8213-41ae-bdd6-70bd1683edd2", "22647437-481a-4d86-9c30-795048bc9c9c"): (False, "agree"),  # Kerala HC extends stay on coercive action against former DGP
    ("95eaf3cd-8213-41ae-bdd6-70bd1683edd2", "32c17925-4f78-4999-b059-00df006dd705"): (False, "agree"),  # Fix minimum and maximum prices for milk, industry [...]
    ("95eaf3cd-8213-41ae-bdd6-70bd1683edd2", "674dca02-b681-4f89-8e2c-0a68a230cf2f"): (False, "agree"),  # Health Minister orders 10-year review into medicine [...]
    ("95eaf3cd-8213-41ae-bdd6-70bd1683edd2", "989e3727-5eb8-423e-9352-a7eddd22a190"): (False, "agree"),  # IIT Madras Develops Cooling Design To Stop Electronics [...]
    ("95eaf3cd-8213-41ae-bdd6-70bd1683edd2", "a7973dcc-bd12-4f3b-abac-290a06b72238"): (False, "agree"),  # Greens decry delay in remediation of Kuzhikandam creek [...]
    ("95eaf3cd-8213-41ae-bdd6-70bd1683edd2", "ba2ac5ba-5567-4812-a98f-bc2825a0671f"): (False, "agree"),  # Kerala Congress urges Centre to take steps for a new [...]
    ("95eaf3cd-8213-41ae-bdd6-70bd1683edd2", "bfb315eb-aa5e-4621-b515-af25b424993f"): (False, "agree"),  # Microsoft to stop Exchange 2016 / 2019 security [...]
    # seed: Telangana government to set up dashboard to provide information on progress, [...]
    ("bf906b04-afed-422f-b4e5-3cfaea778b64", "1edb23a4-a952-49c8-96d1-ea9617d4e42d"): (False, "agree"),  # CS wants comprehensive action plan to further [...]
    ("bf906b04-afed-422f-b4e5-3cfaea778b64", "c7525b64-b278-475e-a9a3-609ca7873a2f"): (False, "agree"),  # Coalition government delivering progress and [...]
    ("bf906b04-afed-422f-b4e5-3cfaea778b64", "0d12dad2-9695-4819-891b-c60b90414684"): (False, "agree"),  # Procedure bypassed in leasing of State Urdu Academy’s [...]
    ("bf906b04-afed-422f-b4e5-3cfaea778b64", "15eb59b4-6fba-47df-984d-25bd1bd5956c"): (False, "agree"),  # Bandi challenges Revanth to back Gen Z push with [...]
    ("bf906b04-afed-422f-b4e5-3cfaea778b64", "1a394db8-2a78-4832-80f2-bf33fc80f2b7"): (False, "agree"),  # Hyderabad emerges as GCC powerhouse, attracts 197 [...]
    ("bf906b04-afed-422f-b4e5-3cfaea778b64", "1b882ec1-b4f5-4353-bb98-4a86f3d7d545"): (False, "agree"),  # Encroachments demolished to provide easy access to [...]
    ("bf906b04-afed-422f-b4e5-3cfaea778b64", "3bdf2a47-6667-4e7f-bbb3-d64cc1588c5d"): (False, "agree"),  # Telangana CM requests Centre for additional works [...]
    ("bf906b04-afed-422f-b4e5-3cfaea778b64", "3ef2fe25-5afc-4b6a-8681-fb95ecd781d5"): (False, "agree"),  # Tamil Nadu Budget to promise new vision for the State, [...]
    ("bf906b04-afed-422f-b4e5-3cfaea778b64", "90f2efb1-0b35-46cc-9a46-19bf86de8df0"): (False, "agree"),  # Mechanism to be set up to provide timely information, [...]
    ("bf906b04-afed-422f-b4e5-3cfaea778b64", "bdaf39b4-6fe7-4399-95d1-e27100ccada7"): (False, "agree"),  # Davangere University to introduce skill-based [...]
    # seed: The Bonus Market Update: सेंसेक्स 500 अंक से अधिक लुढ़का, निफ्टी 24,050 के नीचे
    ("4726cc60-d1d7-45da-a736-1257ffa65e92", "713d2ad1-078f-4611-8eea-584ac55d1f7d"): (False, "agree"),  # जापान से PAK तक, शेयर बाजारों में कल मचा था हाहाकार, [...]
    ("4726cc60-d1d7-45da-a736-1257ffa65e92", "0201f4e4-0aad-4ee9-bd7d-0e3777660c3e"): (False, "agree"),  # भारत में जल्द आ रहे हैं प्लास्टिक के नोट, सरकार ने दी [...]
    ("4726cc60-d1d7-45da-a736-1257ffa65e92", "0c21cc74-6383-4b63-8ac0-561da867dc48"): (False, "agree"),  # ट्रंप का एक सिग्नल... फिर शेयर बाजार में गदर, सेंसेक्स [...]
    ("4726cc60-d1d7-45da-a736-1257ffa65e92", "13beffa5-0bee-4ca0-af1c-e7c72bc148a6"): (False, "agree"),  # From lake to market: the women behind Wular’s water [...]
    ("4726cc60-d1d7-45da-a736-1257ffa65e92", "1c11952a-ed29-4b5e-b0c9-169d1ae3ba23"): (False, "agree"),  # राम मंदिर ट्रस्ट की बैठक, श्रद्धालुओं की सुविधा और [...]
    ("4726cc60-d1d7-45da-a736-1257ffa65e92", "1f19955b-f206-4d5c-a46b-89aad7578c38"): (False, "agree"),  # Okayed trials for polymer notes for ₹10, 20; no plan [...]
    ("4726cc60-d1d7-45da-a736-1257ffa65e92", "3be2d375-d8f8-46e6-91d4-e4a250ae2ad8"): (False, "agree"),  # Mumbai's Rs 10 crore-plus home market scales a record [...]
    ("4726cc60-d1d7-45da-a736-1257ffa65e92", "534e46f6-8587-4475-8619-b02eebc1f9e9"): (False, "agree"),  # कभी ग्रीन... तो कभी रेड, आज कन्फ्यूज क्यों है शेयर बाजार?
    ("4726cc60-d1d7-45da-a736-1257ffa65e92", "73cd2f7d-37c0-420d-b72a-736128e14570"): (False, "agree"),  # Europe’s biggest tech firm is offering employees [...]
    ("4726cc60-d1d7-45da-a736-1257ffa65e92", "7efe9aad-9a72-450d-8f6f-a7f4613434b7"): (False, "agree"),  # Jana Nayagan Box Office Update
    # seed: Three Critical VMware Flaws Allow Auth Bypass, Code Execution, and VM Escape
    ("50480718-6376-428e-810c-f70509d62d34", "1ec0732d-2cb3-4c34-8d4c-0fa8c39c95e2"): (False, "agree"),  # Critical ServiceNow AI Platform Flaw Exploited for [...]
    ("50480718-6376-428e-810c-f70509d62d34", "22bdb685-0d51-4840-adee-b869cc4eaf9e"): (False, "agree"),  # Cisco FMC Zero-Day Actively Exploited, Static [...]
    ("50480718-6376-428e-810c-f70509d62d34", "3e8757a6-fadc-40a2-a857-9ba03ed7da81"): (False, "agree"),  # Critical SharePoint RCE CVE-2026-50522 Under Active [...]
    ("50480718-6376-428e-810c-f70509d62d34", "4403cdb6-7a32-48a1-84e9-b5898f3fdf00"): (False, "agree"),  # n8n Sandbox Escape Lets Workflow Editors Run OS [...]
    ("50480718-6376-428e-810c-f70509d62d34", "aa16aa92-60b7-4af1-a6af-56330b2d5bd3"): (False, "agree"),  # Zoom Patches Critical Windows Flaw That Could Enable [...]
    ("50480718-6376-428e-810c-f70509d62d34", "b934d0fe-ed31-42d1-bb4a-9c1161764959"): (False, "agree"),  # Phase-I work on new bypass nears completion
    ("50480718-6376-428e-810c-f70509d62d34", "de4eaf74-37f6-45b4-bf93-212c1dbcfd56"): (False, "agree"),  # Critical OpenWrt DHCPv6 Flaw Could Let Unauthenticated [...]
    ("50480718-6376-428e-810c-f70509d62d34", "e0ddc29d-0413-40eb-87f1-536421e1ec91"): (False, "agree"),  # Critical NGINX Vulnerability Can Crash Workers and May [...]
    ("50480718-6376-428e-810c-f70509d62d34", "f29da7b4-dbf4-4e84-accb-6a5464f995ea"): (False, "agree"),  # Hugging Face Diffusers Flaws Could Let Model [...]
    # seed: Tusker electrocuted by illegal fence near Coimbatore; two arrested
    ("f5e683d4-a463-43b8-8bfe-b3b8f91c4089", "67004e97-e1a7-4d2a-98d9-71706bf1deab"): (False, "agree"),  # Two workers killed in explosion at illegal fireworks [...]
    ("f5e683d4-a463-43b8-8bfe-b3b8f91c4089", "b3df1d46-2884-418b-9e47-acf208bf4de8"): (False, "agree"),  # Live fence against wild boar claims farmer’s life near [...]
    ("f5e683d4-a463-43b8-8bfe-b3b8f91c4089", "04e3af91-9d85-49ad-b399-bb0520cabb76"): (False, "agree"),  # T.N. in the process of identifying site to build AI [...]
    ("f5e683d4-a463-43b8-8bfe-b3b8f91c4089", "4332b2c6-f112-49a5-b7bc-a1fab33758be"): (False, "agree"),  # Hindi name board at Coimbatore North railway station [...]
    ("f5e683d4-a463-43b8-8bfe-b3b8f91c4089", "476e6984-a842-409b-bc7c-ac5043dfe955"): (False, "agree"),  # Govt. will take steps to create employment [...]
    ("f5e683d4-a463-43b8-8bfe-b3b8f91c4089", "65f2ef89-a65b-4177-85e6-b7655b185e47"): (False, "agree"),  # Ivory missing from eight dead wild elephants of [...]
    ("f5e683d4-a463-43b8-8bfe-b3b8f91c4089", "ae53f752-c287-4b30-8705-746a4cd3e07b"): (False, "agree"),  # Farmer ends life due to crop loss, mounting debts in [...]
    ("f5e683d4-a463-43b8-8bfe-b3b8f91c4089", "c1798ce2-7a6c-4d17-90a8-a9c11be5122f"): (False, "agree"),  # Chennai consumers express shock over exorbitant bi- [...]
    ("f5e683d4-a463-43b8-8bfe-b3b8f91c4089", "c5fd2202-c45d-4581-afb9-b9629649b541"): (False, "agree"),  # Family of four among five killed after car rams into [...]
    ("f5e683d4-a463-43b8-8bfe-b3b8f91c4089", "c8d9aa31-0003-4d57-aa55-f436d4309e7a"): (False, "agree"),  # Tamil Nadu Today: White Paper on electricity [...]
    # seed: Two arrested for printing fake ₹500 notes in Bengaluru; counterfeit currency, [...]
    ("4907d841-bb4f-4eb7-9f6d-f4db04b28f65", "d90bbf10-71e9-4ad1-bd63-a812b035e57e"): (False, "agree"),  # Cash Management firm under probe for allegedly [...]
    ("4907d841-bb4f-4eb7-9f6d-f4db04b28f65", "55cad8f8-3cb4-4879-b8f4-ccbb9506e848"): (False, "agree"),  # Six drug peddlers arrested in Tiruvannamalai
    ("4907d841-bb4f-4eb7-9f6d-f4db04b28f65", "b26e5b3d-f947-4682-90d0-4fc643422ee6"): (False, "agree"),  # Seven arrested, nearly 48 kg of ganja seized in [...]
    ("4907d841-bb4f-4eb7-9f6d-f4db04b28f65", "b27bb8ce-93bd-43a3-a3cb-b566deaa5b84"): (False, "agree"),  # Two red sanders operatives from Tamil Nadu arrested, [...]
    ("4907d841-bb4f-4eb7-9f6d-f4db04b28f65", "b8e33640-e17b-4dd3-8897-81048d8cce1e"): (False, "agree"),  # Cyber police recovers Rs 1.1 crore out of Rs 7.9 crore [...]
    ("4907d841-bb4f-4eb7-9f6d-f4db04b28f65", "d27bf37e-bfcc-4375-a43d-da4a07325451"): (False, "agree"),  # Uttarakhand: Fake medicines, packaging material seized [...]
    ("4907d841-bb4f-4eb7-9f6d-f4db04b28f65", "dfe20171-7f1c-4ea2-b957-70c245aa2eda"): (False, "agree"),  # Kerala sandalwood theft racket busted; CCB arrests [...]
    ("4907d841-bb4f-4eb7-9f6d-f4db04b28f65", "e1eaa971-cff6-47ab-99fd-371fbc8ed226"): (False, "agree"),  # NEET: Congress, BJP workers detained during rival [...]
    ("4907d841-bb4f-4eb7-9f6d-f4db04b28f65", "e2fecb63-d054-45f9-9f4e-d63ee0f1a1ab"): (False, "agree"),  # Bengaluru: ED uncovers $35 million crypto OTC scam; [...]
    # seed: US-Iran talks: Where negotiations stand as military pause enters third day
    ("89587a20-6aa8-40ce-8bd7-83792283c83f", "1b4137a9-7bdf-4e8b-9c98-2d5d1fd9b146"): (True, "adj:tejas-said-same:high"),  # US, Iran pause attacks for second day as ceasefire [...]
    ("89587a20-6aa8-40ce-8bd7-83792283c83f", "3a18782f-8c12-4aff-adee-5e772073dad5"): (False, "agree"),  # Top US commander Bradley Cooper's warning changed [...]
    ("89587a20-6aa8-40ce-8bd7-83792283c83f", "15b0b82c-4af0-4c80-a80c-2ce6cac58507"): (False, "agree"),  # Trump says Gulf leaders' input weighed heavily in [...]
    ("89587a20-6aa8-40ce-8bd7-83792283c83f", "334a8ef9-0c8f-448b-9dfd-9fe9c29518db"): (True, "adj:tejas-said-same:medium"),  # 'ईरान से फ्रेंडली बातचीत जारी', चुनावी रैली बोले [...]
    ("89587a20-6aa8-40ce-8bd7-83792283c83f", "540595e2-772d-46f4-809c-4cfa5dac58c7"): (False, "agree"),  # Trump warns of ‘very strong military action’ against [...]
    ("89587a20-6aa8-40ce-8bd7-83792283c83f", "8c136873-20e4-4a0d-a3b8-ff74629005c7"): (False, "agree"),  # Oil prices fall to one-week low as hopes of US-Iran [...]
    ("89587a20-6aa8-40ce-8bd7-83792283c83f", "8ecaf4d0-4631-4073-804a-318159827504"): (False, "agree"),  # Saudi Aramco Abqaiq oil facility on fire: Riyadh [...]
    ("89587a20-6aa8-40ce-8bd7-83792283c83f", "9f9d085d-b3f2-4e0a-8fa3-4bacd60731db"): (False, "agree"),  # US Military Launches 11th Consecutive Night Of Strikes [...]
    ("89587a20-6aa8-40ce-8bd7-83792283c83f", "a96a20a3-c345-4445-9af1-9cd45e7dda0d"): (False, "agree"),  # 'Oil Dropped, Stocks Rose': Trump Defends Iran Pause, [...]
    ("89587a20-6aa8-40ce-8bd7-83792283c83f", "b798f41b-621c-4344-b1cf-995014427797"): (False, "agree"),  # Trump plays down prospects of Iran talks amid Red Sea threat
    # seed: Ubuntu snap-confine Flaw Could Give Local Users Root on Default Desktop Installs
    ("29ec6d70-ac09-4ae5-97a8-fd6ec5d222f2", "aa16aa92-60b7-4af1-a6af-56330b2d5bd3"): (False, "agree"),  # Zoom Patches Critical Windows Flaw That Could Enable [...]
    ("29ec6d70-ac09-4ae5-97a8-fd6ec5d222f2", "21441549-5fc1-440a-babb-2956e1675020"): (False, "agree"),  # Critical Rails Flaw Could Let Unauthenticated [...]
    ("29ec6d70-ac09-4ae5-97a8-fd6ec5d222f2", "4403cdb6-7a32-48a1-84e9-b5898f3fdf00"): (False, "agree"),  # n8n Sandbox Escape Lets Workflow Editors Run OS [...]
    ("29ec6d70-ac09-4ae5-97a8-fd6ec5d222f2", "50480718-6376-428e-810c-f70509d62d34"): (False, "agree"),  # Three Critical VMware Flaws Allow Auth Bypass, Code [...]
    ("29ec6d70-ac09-4ae5-97a8-fd6ec5d222f2", "693c8c17-408d-4996-8c62-694236b9c6d9"): (False, "agree"),  # Root and Trescothick could sub in as England Test [...]
    ("29ec6d70-ac09-4ae5-97a8-fd6ec5d222f2", "b0d52bfa-2cf0-4ba9-90b7-ef7c2a069361"): (False, "agree"),  # Qilin Ransomware Attackers Exploit PAN-OS [...]
    ("29ec6d70-ac09-4ae5-97a8-fd6ec5d222f2", "b1087ea5-866d-48ff-97ad-5ec52c231f97"): (False, "agree"),  # Hindu outfit installs Shivling near mosque in West Bengal
    ("29ec6d70-ac09-4ae5-97a8-fd6ec5d222f2", "de4eaf74-37f6-45b4-bf93-212c1dbcfd56"): (False, "agree"),  # Critical OpenWrt DHCPv6 Flaw Could Let Unauthenticated [...]
    ("29ec6d70-ac09-4ae5-97a8-fd6ec5d222f2", "f440cca0-a544-4838-ae30-03f7f6429d63"): (False, "agree"),  # Jeff Bezos ex-wife MacKenzie Scott helped write a [...]
    # seed: Veteran Congress leader Karuthodi Radhakrishnan passes away at 83
    ("8beccb11-ce25-4ae8-b795-6d596e87c402", "92dff880-f4fb-4173-a1e4-0c0a16227d89"): (False, "agree"),  # Former Shivamogga MLA passes away
    ("8beccb11-ce25-4ae8-b795-6d596e87c402", "01202979-d3d3-4774-91f3-510cb0b18f77"): (False, "agree"),  # Opposition sharpens attack on Kerala CM, accuses him [...]
    ("8beccb11-ce25-4ae8-b795-6d596e87c402", "03a2b4a6-069c-4014-b12e-7201c1927e50"): (False, "agree"),  # NEET protest at Bengaluru’s Freedom Park sparks [...]
    ("8beccb11-ce25-4ae8-b795-6d596e87c402", "12e39337-90c9-46b4-88e6-45acf02f8ce5"): (False, "agree"),  # Who Was Pavala Shyamala? Veteran Telugu Actor Passes [...]
    ("8beccb11-ce25-4ae8-b795-6d596e87c402", "5d11469e-b6fe-40ad-9ba9-b96bb2df778f"): (False, "agree"),  # Madhya Pradesh Assembly passes UCC Bill amid Congress [...]
    ("8beccb11-ce25-4ae8-b795-6d596e87c402", "5f62decb-17b8-4aea-83e3-5313d883a8b4"): (False, "agree"),  # ₹10,120 crore given away to 42,70,842 mothers under [...]
    ("8beccb11-ce25-4ae8-b795-6d596e87c402", "a1f2f8ec-d87f-4b41-901a-425346f21d85"): (False, "agree"),  # Former Karnataka Chief Minister Siddaramaiah announces [...]
    ("8beccb11-ce25-4ae8-b795-6d596e87c402", "a780a0cc-9fd0-435d-ba1a-e9265723e54d"): (False, "agree"),  # Ramesan Paleri, chairman of Kerala-based Uralungal [...]
    ("8beccb11-ce25-4ae8-b795-6d596e87c402", "b6106e67-598e-404d-b305-938938e876e0"): (False, "agree"),  # Educationist, former governor D Y Patil passes away at [...]
    ("8beccb11-ce25-4ae8-b795-6d596e87c402", "b7c106af-00fb-43c5-82d1-107d724096d6"): (False, "agree"),  # Governor Arlekar, CM Vijay pay tributes to [...]
    # seed: Why did Todd Blanche scrap Trump's $1.8 billion ‘anti-weaponization fund’ [...]
    ("60547055-df86-4e44-970c-89e5d4f84b34", "3566c85f-364f-48da-b316-859c0a9ff2f2"): (False, "agree"),  # Former FBI chief James Comey seeks dismissal of [...]
    ("60547055-df86-4e44-970c-89e5d4f84b34", "054db755-2e65-4aca-ab75-de4b5bfd45bb"): (False, "agree"),  # BJP slams Telangana govt over 'family register', [...]
    ("60547055-df86-4e44-970c-89e5d4f84b34", "28145426-4ea3-4e8c-ba7b-0694eb04be00"): (False, "agree"),  # Pete Hegseth Estimates Iran War Has Cost $37.5 Billion [...]
    ("60547055-df86-4e44-970c-89e5d4f84b34", "3d8cd1f9-25ea-4de0-a58f-e758b37f18b6"): (False, "agree"),  # Iran’s $23 billion oil cushion: Can Trump’s sanctions [...]
    ("60547055-df86-4e44-970c-89e5d4f84b34", "6953016b-b9b5-499e-bf01-7fc045683959"): (False, "agree"),  # US signals fresh 10% to 12.5% tariffs on dozens of [...]
    ("60547055-df86-4e44-970c-89e5d4f84b34", "781bf26d-7eff-4df9-bae9-6a54b09237b3"): (False, "agree"),  # Vasconcelos leads the fight as Northants scrap for [...]
    ("60547055-df86-4e44-970c-89e5d4f84b34", "a7c20efd-916b-4736-9581-04998803efc3"): (False, "agree"),  # ईरान जंग में US का भारी नुकसान, अब तक 3 लाख करोड़ से [...]
    ("60547055-df86-4e44-970c-89e5d4f84b34", "ab444c5c-673e-4e33-a1be-d5a669aaa042"): (False, "agree"),  # Trump approves Saudi nuclear agreement, opens door to [...]
    ("60547055-df86-4e44-970c-89e5d4f84b34", "abdc9ad8-0eae-44bf-9997-9de18033e96d"): (False, "agree"),  # US Senator introduces Bill to suspend new H-1B visas [...]
    ("60547055-df86-4e44-970c-89e5d4f84b34", "bd5cdb06-b528-46f8-a235-1cdf175679cf"): (False, "agree"),  # Zelensky To Meet US Senators Today As Russia Sanctions [...]
    # seed: Why over 250 landless beneficiaries of Kerala’s Arippa Bhoosamaram are trapped [...]
    ("492908b4-39d1-4419-b374-0bccb612471b", "0233d002-f9db-4439-932c-9379449fcf32"): (False, "agree"),  # Parliament stays in deadlock over student protests, [...]
    ("492908b4-39d1-4419-b374-0bccb612471b", "2c451f51-6b72-407b-93c4-a3a80c99cdff"): (False, "agree"),  # Maharashtra releases first list of 553 beneficiaries [...]
    ("492908b4-39d1-4419-b374-0bccb612471b", "2d70e2e6-5363-445c-a2b9-07b49d441faf"): (False, "agree"),  # Madras High Court to hear PIL on Karur Devadanam land issue
    ("492908b4-39d1-4419-b374-0bccb612471b", "6096a108-8b09-4af6-adb0-7229776190c9"): (False, "agree"),  # Encroachment on government land on the rise in [...]
    ("492908b4-39d1-4419-b374-0bccb612471b", "71e4bf7c-0ed4-491a-b9c2-8c0b7ac7e6f5"): (False, "agree"),  # Parliament Set To Resume Today Amid Deadlock Over CJP [...]
    ("492908b4-39d1-4419-b374-0bccb612471b", "af71d6d8-693b-41fc-b28c-c26780e5ca9a"): (False, "agree"),  # FIR against 19 for illegal registration of trust [...]
    ("492908b4-39d1-4419-b374-0bccb612471b", "bdb4d537-e4b1-4610-a73f-bab79a017d29"): (False, "agree"),  # 20 Workers Die In Sikkim Tunnel Collapse, Efforts On [...]
    ("492908b4-39d1-4419-b374-0bccb612471b", "c0c7d4a5-35b5-4b7b-b4f4-a3b7083229d2"): (False, "agree"),  # Land row: Karnataka HC directs State govt. not to [...]
    ("492908b4-39d1-4419-b374-0bccb612471b", "c52b20f1-f531-4097-89cf-f96750b80fb2"): (False, "agree"),  # Hunger strike against laterite quarry in Kannur [...]
    ("492908b4-39d1-4419-b374-0bccb612471b", "f42686c4-1951-4923-beb1-2621344df83f"): (False, "agree"),  # Maharashtra begins rollout of Farmer Loan Waiver [...]
    # seed: Woman who stopped Mumbai police van files complaint against online abuse
    ("2d85bc33-56aa-4133-a71c-0219d4ffff2a", "2f85738d-204a-4986-890a-3dd395408340"): (False, "agree"),  # Woman in viral pic files police complaint over death deaths
    ("2d85bc33-56aa-4133-a71c-0219d4ffff2a", "a3a7e293-4a03-4595-a875-6e8c11480d55"): (True, "adj:vijay-said-same:high"),  # 'I will identify each one of them': Mumbai model who [...]
    ("2d85bc33-56aa-4133-a71c-0219d4ffff2a", "456b4acd-076c-4f7f-8a37-9efcb0f880f8"): (False, "agree"),  # Supreme Court rejects review plea against relief to [...]
    ("2d85bc33-56aa-4133-a71c-0219d4ffff2a", "a6e8f22d-cf38-437d-bb02-fa33dc16bc56"): (False, "agree"),  # Speaker’s nod to Sena (UBT) MPs’ merger challenged in SC
    ("2d85bc33-56aa-4133-a71c-0219d4ffff2a", "ae3b6b39-147d-4eaa-8012-13816fd178b8"): (False, "agree"),  # BJP functionary files complaint over morphed video of [...]
    ("2d85bc33-56aa-4133-a71c-0219d4ffff2a", "b1ab90a0-2a93-4a8f-ac33-140fcf0bfa72"): (False, "agree"),  # No FIR against Noida teen booked over 'abusive' video [...]
    ("2d85bc33-56aa-4133-a71c-0219d4ffff2a", "b5e913ff-dd78-4af2-bcc4-b067526c86a6"): (False, "agree"),  # Kirti Kulhari loses Rs 2.4 lakh to cyber fraud; files [...]
    ("2d85bc33-56aa-4133-a71c-0219d4ffff2a", "b86b4764-0b19-4611-9d23-8c2714adf8a0"): (False, "agree"),  # 'वो बात से मुकर गए...', राहुल गांधी-जितेंद्र सिंह के [...]
    ("2d85bc33-56aa-4133-a71c-0219d4ffff2a", "bbc2a9a9-f6f2-4c3c-8718-8a87da868332"): (False, "agree"),  # Protesters gather at Shivaji Park in Mumbai; around [...]
    ("2d85bc33-56aa-4133-a71c-0219d4ffff2a", "db8f07df-760a-4431-89a6-36d3b33f8c8f"): (False, "agree"),  # 'Arrest Dipke immediately': Faizan Ansari files police [...]
    # seed: World's Largest AI Model Repository Hugging Face Breached by Autonomous AI Agent
    ("1f70d001-95df-435d-9419-1e6a11809c8f", "9f547fa0-4299-4f4a-9205-40f8edc86800"): (True, "adj:vijay-said-same:high"),  # OpenAI's rogue AI agent that hacked world's biggest [...]
    ("1f70d001-95df-435d-9419-1e6a11809c8f", "a15afe1c-2adf-4f84-9ad1-54298ea91915"): (True, "adj:vijay-said-same:high"),  # OpenAI Says Its AI Models Escaped Sandbox, Targeted [...]
    ("1f70d001-95df-435d-9419-1e6a11809c8f", "56147b89-91b9-422f-b313-896a8ef0386f"): (False, "agree"),  # New ENCFORGE Ransomware Targets AI Model Files in [...]
    ("1f70d001-95df-435d-9419-1e6a11809c8f", "f29da7b4-dbf4-4e84-accb-6a5464f995ea"): (False, "adj:tejas-said-same:high"),  # Hugging Face Diffusers Flaws Could Let Model [...]
    ("1f70d001-95df-435d-9419-1e6a11809c8f", "34e2c66f-5710-485b-9ec9-331e034cef9a"): (False, "agree"),  # World’s largest camera captures over 500,000 galaxies [...]
    ("1f70d001-95df-435d-9419-1e6a11809c8f", "abf2cf6b-10cb-41cc-bbc8-e42dd6f135b1"): (False, "agree"),  # NVIDIA Forms 37-Member Open Secure AI Alliance and [...]
    ("1f70d001-95df-435d-9419-1e6a11809c8f", "c70c1c13-66ce-4054-a822-ea1605682202"): (False, "agree"),  # Slopsquatting, Phantom Domains, and HalluSquatting Are [...]
    ("1f70d001-95df-435d-9419-1e6a11809c8f", "d2723985-8a3c-4004-851e-587ee5863719"): (False, "agree"),  # OpenAI's Sam Altman says AI is now at 'singularity' [...]
    ("1f70d001-95df-435d-9419-1e6a11809c8f", "d680f446-e35b-4500-b836-35d10751c4ea"): (True, "adj:vijay-said-same:high"),  # OpenAI Says Its Models Accidentally Hacked Hugging Face
    # seed: World’s largest camera captures over 500,000 galaxies in one photo of universe
    ("34e2c66f-5710-485b-9ec9-331e034cef9a", "10d9f398-6dc0-4d7f-9713-33d3a3620ddc"): (False, "agree"),  # Honor Confirms Robot Phone Camera Details Ahead of [...]
    ("34e2c66f-5710-485b-9ec9-331e034cef9a", "1f70d001-95df-435d-9419-1e6a11809c8f"): (False, "agree"),  # World's Largest AI Model Repository Hugging Face [...]
    ("34e2c66f-5710-485b-9ec9-331e034cef9a", "2020d184-38b1-417a-9d1e-c98b2c1d2af1"): (False, "agree"),  # Scientists survey Mount Ararat glacier above 5,000m [...]
    ("34e2c66f-5710-485b-9ec9-331e034cef9a", "72a9abe6-15b6-4505-b198-fd766a0f5884"): (False, "agree"),  # Data Centre Battle: Nvidia Reveals Specs Of Vera CPU, [...]
    ("34e2c66f-5710-485b-9ec9-331e034cef9a", "792b7346-90d9-4a32-8146-033c563dcb22"): (False, "agree"),  # Kafir screenshot case in Kerala: SIT names DYFI leader [...]
    ("34e2c66f-5710-485b-9ec9-331e034cef9a", "9be64831-cf13-4903-99bd-93a8522bc041"): (False, "agree"),  # Scientists discover strange Milky Way planetary system [...]
    ("34e2c66f-5710-485b-9ec9-331e034cef9a", "9eb00e86-9640-4033-8028-6023c4e0d644"): (False, "agree"),  # Two traffic police personnel caught on camera taking [...]
    ("34e2c66f-5710-485b-9ec9-331e034cef9a", "adcb0468-7b19-47a7-83c3-3947439faf58"): (False, "agree"),  # What makes Skyroot’s Vikram-1 launch unique? | Explained
    ("34e2c66f-5710-485b-9ec9-331e034cef9a", "e0037e4f-199b-47be-b89f-1af1cc07a39e"): (False, "agree"),  # Faridabad school teacher stabbed to death by masked [...]
    ("34e2c66f-5710-485b-9ec9-331e034cef9a", "f39fce10-2bf0-4e8b-85e0-8d8e2d8369e1"): (False, "agree"),  # Photo exhibition, PIB workshop mark 12 years of NDA [...]
    # seed: कौन हैं AUS टीम में एंट्री पाने वाले भारतीय नील पटेल?
    ("e1f01804-84db-4d6f-9a74-4d91d15ffb83", "0599ca3f-b3d2-459a-9b06-4dbd7580270a"): (False, "agree"),  # टीम इंडिया के असिस्टेंट कोच ने अचानक दिया इस्तीफा
    ("e1f01804-84db-4d6f-9a74-4d91d15ffb83", "188b10f8-4414-48a3-8901-a29b0dd5aa0c"): (False, "agree"),  # श्रेयस ने जारी रखी धोनी वाली परंपरा, सीरीज जीत इन्हें [...]
    ("e1f01804-84db-4d6f-9a74-4d91d15ffb83", "386e5033-f24b-47cd-a873-6c018b1e3a6b"): (False, "agree"),  # Australia could put India A four-day series ahead of ODIs
    ("e1f01804-84db-4d6f-9a74-4d91d15ffb83", "45c7df50-e56b-4bc8-afcd-19557421bf80"): (False, "agree"),  # 'अब रैट रेस का हिस्सा नहीं बनूंगा...', संजू सैमसन का [...]
    ("e1f01804-84db-4d6f-9a74-4d91d15ffb83", "503b491e-6478-443f-8b98-1dee9c769e2c"): (False, "agree"),  # जो IPL में नहीं चमका, वही बुमराह का रिप्लेसमेंट... [...]
    ("e1f01804-84db-4d6f-9a74-4d91d15ffb83", "7499396e-8ce5-4d65-9076-5559d1c4f38b"): (False, "agree"),  # Pakistan Batter Surpasses Harmanpreet Kaur In ICC [...]
    ("e1f01804-84db-4d6f-9a74-4d91d15ffb83", "8cb26a91-e131-4518-8aa3-c38cf2932bae"): (False, "agree"),  # Adam Zampa joins Queensland, BBL club remains unknown
    ("e1f01804-84db-4d6f-9a74-4d91d15ffb83", "a870868f-5e07-4dd7-a6d0-188c0cd7f126"): (False, "agree"),  # Rohit Reacts As India Coach, Released By BCCI, Shares [...]
    ("e1f01804-84db-4d6f-9a74-4d91d15ffb83", "c559e32e-454e-4dd1-a1de-c7922d0a6bb4"): (False, "agree"),  # दलीप ट्रॉफी 2026: स्टार खिलाड़ियों के बीच होगी जंग
    ("e1f01804-84db-4d6f-9a74-4d91d15ffb83", "f399c7d2-e02f-4431-9280-0a008b2de40e"): (False, "agree"),  # कैंसर ने छीन ली थी पिता की आवाज... पर्ची पर लिखे शब्द [...]
    # seed: जापान से PAK तक, शेयर बाजारों में कल मचा था हाहाकार, आज क्या होगा?
    ("713d2ad1-078f-4611-8eea-584ac55d1f7d", "0c21cc74-6383-4b63-8ac0-561da867dc48"): (False, "agree"),  # ट्रंप का एक सिग्नल... फिर शेयर बाजार में गदर, सेंसेक्स [...]
    ("713d2ad1-078f-4611-8eea-584ac55d1f7d", "4726cc60-d1d7-45da-a736-1257ffa65e92"): (False, "agree"),  # The Bonus Market Update: सेंसेक्स 500 अंक से अधिक [...]
    ("713d2ad1-078f-4611-8eea-584ac55d1f7d", "534e46f6-8587-4475-8619-b02eebc1f9e9"): (False, "agree"),  # कभी ग्रीन... तो कभी रेड, आज कन्फ्यूज क्यों है शेयर बाजार?
    ("713d2ad1-078f-4611-8eea-584ac55d1f7d", "5c462c2b-2a9a-4074-aaa9-4ea1955d8c2e"): (False, "agree"),  # A plant-source Vitamin D3 looks to light-up Fermenta [...]
    ("713d2ad1-078f-4611-8eea-584ac55d1f7d", "954be3bd-7b5f-4e49-8ffa-034df3574e23"): (False, "agree"),  # Caliber Mining & Logistics IPO Allotment Today: Check [...]
    ("713d2ad1-078f-4611-8eea-584ac55d1f7d", "ec86f39f-5608-47ad-af25-6d2848683677"): (False, "agree"),  # अचानक क्रैश हुआ इस देश का शेयर बाजार, इस वजह से मचा हाहाकार
    ("713d2ad1-078f-4611-8eea-584ac55d1f7d", "fca26160-0d3f-42ec-b705-1bdfda7698c7"): (False, "agree"),  # इधर बिखर रहा शेयर बाजार, उधर सोना-चांदी के दाम में [...]
    # seed: ट्रंप के नए टैरिफ पर अमेरिका में बवाल! 25 राज्यों ने किया केस
    ("ab28210a-8916-4ccd-b43b-53b9fcffbd96", "01fca328-732f-4825-b76b-18063db3cc84"): (False, "agree"),  # US Tariff Row: ट्रंप की नई टैरिफ नीति के खिलाफ 25 [...]
    ("ab28210a-8916-4ccd-b43b-53b9fcffbd96", "a34d4074-beb6-41f5-b90d-187631904e3d"): (True, "adj:vijay-said-same:high"),  # 25 US states sue Trump over fresh tariffs on 60 [...]
    ("ab28210a-8916-4ccd-b43b-53b9fcffbd96", "0d0b38a2-3947-41ee-86f2-95fb9d34edea"): (False, "agree"),  # ट्रंप देने जा रहे 200% टैरिफ वाली चोट, लेकिन इसमें भी [...]
    ("ab28210a-8916-4ccd-b43b-53b9fcffbd96", "3566c85f-364f-48da-b316-859c0a9ff2f2"): (False, "agree"),  # Former FBI chief James Comey seeks dismissal of [...]
    ("ab28210a-8916-4ccd-b43b-53b9fcffbd96", "4cad7042-94d9-4631-a8e5-d239d53af665"): (False, "agree"),  # US: जेनेरिक दवाओं पर 200% तक टैरिफ लगाने जा रहे ट्रंप, [...]
    ("ab28210a-8916-4ccd-b43b-53b9fcffbd96", "4d1a310a-7d71-455d-ace0-68636df0ec74"): (False, "agree"),  # ಇರಾನ್ ಯುದ್ಧದಿಂದ ಹಿಂದೆ ಸರಿಯುವಂತೆ ಟ್ರಂಪ್‌ಗೆ ಸೌದಿ ಅರೇಬಿಯಾ [...]
    ("ab28210a-8916-4ccd-b43b-53b9fcffbd96", "6874a9aa-64cf-44ff-84a2-f791e2b82847"): (False, "agree"),  # Trump tells oil companies to ‘get retail prices down [...]
    ("ab28210a-8916-4ccd-b43b-53b9fcffbd96", "ff2a8503-f98c-452c-86d5-e840d77da4a6"): (False, "agree"),  # ट्रंप ने कनाडा पर ठोका कितना टैरिफ? देखें दुनिया आजतक में
    # seed: नेपाल के PM का यू-टर्न, भारत और चीन के राजदूतों से करेंगे मुलाकात
    ("c0c54cb0-3783-4fa0-a882-db35df86ce53", "27e6d690-3f6e-419a-8dcb-e636233bee44"): (False, "agree"),  # India coordinates with Ukrainian authorities in search [...]
    ("c0c54cb0-3783-4fa0-a882-db35df86ce53", "433ea28c-6ec2-4020-9bf1-5b7306c4abb3"): (False, "agree"),  # Border peace prerequisite for normal ties, Jaishankar [...]
    ("c0c54cb0-3783-4fa0-a882-db35df86ce53", "90f2efb1-0b35-46cc-9a46-19bf86de8df0"): (False, "agree"),  # Mechanism to be set up to provide timely information, [...]
    ("c0c54cb0-3783-4fa0-a882-db35df86ce53", "9dc3d5ac-ee7b-4c85-ba28-5dd515b0e971"): (False, "agree"),  # Parliament Monsoon Session LIVE: दोनों सदनों की [...]
    ("c0c54cb0-3783-4fa0-a882-db35df86ce53", "a0f78299-2d73-4ee3-9233-05549b220d0c"): (False, "agree"),  # क्वाड बैठक: भारत ने दोहराई स्वतंत्र हिंद-प्रशांत [...]
    ("c0c54cb0-3783-4fa0-a882-db35df86ce53", "b4e345f2-0430-414a-892f-39aea1970851"): (False, "agree"),  # Centre raises windfall tax on petrol, diesel and ATF [...]
    ("c0c54cb0-3783-4fa0-a882-db35df86ce53", "bf5e1a7b-1d5a-480f-ac5c-778e0418209d"): (False, "agree"),  # सोनम वांगचुक और जेपी नड्डा के बीच एक घंटे चली बैठक... [...]
    ("c0c54cb0-3783-4fa0-a882-db35df86ce53", "d4fc69b4-f966-49b1-aa8f-10a2c7d4a4b8"): (False, "agree"),  # PM Modi reviews West Asia conflict impact in CCS meet
    ("c0c54cb0-3783-4fa0-a882-db35df86ce53", "ec00b7fc-10be-46a0-8dee-6c055c0faf98"): (False, "agree"),  # FCRA बिल में क्या है? विदेशी फंड वाले NGO पर कसेगा [...]
    ("c0c54cb0-3783-4fa0-a882-db35df86ce53", "f59d4c14-f75a-411f-ab41-3ec6786654ac"): (False, "agree"),  # More Chinese investment good for wider relationship, [...]
    # seed: पटना में AISA के छात्रों ने जेपी गोलंबर पर किया प्रदर्शन
    ("ee345f67-8fff-41a3-9cf0-bf79e9c3bb6b", "4151eaae-9335-4738-9a22-91247b7524ea"): (False, "agree"),  # CJP प्रोटेस्ट की आंच पटना पहुंची... थानाध्यक्ष का सिर [...]
    ("ee345f67-8fff-41a3-9cf0-bf79e9c3bb6b", "1b9ae226-2c7a-460a-9723-22e0e2a151d3"): (False, "agree"),  # प्रदर्शन के बीच हिरासत में अखिलेश, पुलिस बस का VIDEO
    ("ee345f67-8fff-41a3-9cf0-bf79e9c3bb6b", "205edb7f-e8d5-4595-b63c-a83da51ce43e"): (False, "agree"),  # हिंसा के हर चेहरे की तलाश, बिहार पुलिस ने जारी किए 400 [...]
    ("ee345f67-8fff-41a3-9cf0-bf79e9c3bb6b", "4826a1c1-a6dc-480f-a72d-5ebae94e236f"): (False, "agree"),  # 'भीड़ बेकाबू थी, वॉर्निंग के बाद किया बल प्रयोग', संसद [...]
    ("ee345f67-8fff-41a3-9cf0-bf79e9c3bb6b", "51875f10-90fd-4e1e-91dd-81626aaf71cd"): (False, "agree"),  # जंतर-मंतर के पास फ‍िर भ‍िड़े प्रदर्शनकारी छात्र और [...]
    ("ee345f67-8fff-41a3-9cf0-bf79e9c3bb6b", "80b2830c-f424-4695-a536-c14cd4b9e2d7"): (False, "agree"),  # 'बिहार में पाकिस्तान मॉडल...', BJP का कांग्रेस के [...]
    ("ee345f67-8fff-41a3-9cf0-bf79e9c3bb6b", "a9c7fa1a-2acb-4852-92a1-a17afd9f14fd"): (False, "agree"),  # AISA alleges crackdown on student protesters, seeks [...]
    ("ee345f67-8fff-41a3-9cf0-bf79e9c3bb6b", "b86b4764-0b19-4611-9d23-8c2714adf8a0"): (False, "agree"),  # 'वो बात से मुकर गए...', राहुल गांधी-जितेंद्र सिंह के [...]
    ("ee345f67-8fff-41a3-9cf0-bf79e9c3bb6b", "d3d229c6-81fc-4a11-8b79-cc21f5708675"): (False, "agree"),  # Bihar govt relents, to withdraw youth protest-linked [...]
    ("ee345f67-8fff-41a3-9cf0-bf79e9c3bb6b", "d9b8070a-e762-4617-9210-d953b06fcce6"): (False, "agree"),  # ‘Chalo Lok Bhavan’ protest in Hyderabad calls for [...]
    # seed: पाकिस्तानी आवाम को बड़ा झटका, पेट्रोल और डीजल फिर हुआ महंगा
    ("d4735e0e-0875-4d0b-986e-98b83c3cbd5c", "1b624940-fc05-48e4-b29b-63ae9f8c618e"): (False, "agree"),  # ‘Mujahideen trained by us in the past hang around our [...]
    ("d4735e0e-0875-4d0b-986e-98b83c3cbd5c", "1dd83a17-a4e4-4105-9e50-383ab60b1e53"): (False, "agree"),  # US Iran war news LIVE: US strikes Iran for 11th [...]
    ("d4735e0e-0875-4d0b-986e-98b83c3cbd5c", "1fea457a-a24d-42e3-bb65-54d31a7b90cf"): (False, "agree"),  # Sharif’s PML-N wins 9 out of 13 seats in first phase [...]
    ("d4735e0e-0875-4d0b-986e-98b83c3cbd5c", "310a5033-0c7e-4456-a9c6-5acd5a8ac238"): (False, "agree"),  # PoK में जीती शहबाज शरीफ की पार्टी, क्या बड़े भाई को [...]
    ("d4735e0e-0875-4d0b-986e-98b83c3cbd5c", "334a8ef9-0c8f-448b-9dfd-9fe9c29518db"): (False, "agree"),  # 'ईरान से फ्रेंडली बातचीत जारी', चुनावी रैली बोले [...]
    ("d4735e0e-0875-4d0b-986e-98b83c3cbd5c", "8219c92f-0199-4941-9d25-0ec90e029104"): (False, "agree"),  # दोबारा युद्ध से पाकिस्तान-बांग्लादेश को लगा ये एक [...]
    ("d4735e0e-0875-4d0b-986e-98b83c3cbd5c", "87da23ce-f0ef-4a88-a1fc-7637536c63ce"): (False, "agree"),  # Govt says no assessment of share of vehicles [...]
    ("d4735e0e-0875-4d0b-986e-98b83c3cbd5c", "9cebb421-7848-4b73-bb1b-c21b5bc96ce4"): (False, "agree"),  # LPG, बैंक से तत्काल रेल टिकट तक... देश में 1 अगस्त से [...]
    ("d4735e0e-0875-4d0b-986e-98b83c3cbd5c", "dfd87835-c805-4d5c-91e5-2d6df2f3a133"): (False, "agree"),  # 'तैयार रहें... $120 के पार जाएगा तेल', विदेश से आई [...]
    ("d4735e0e-0875-4d0b-986e-98b83c3cbd5c", "ea89f061-f5fa-4d7d-a856-beaf3a6a3520"): (False, "agree"),  # Petrol-Diesel Prices:: सरकार ने बढ़ाया पेट्रोल-डीजल और [...]
    # seed: पुलिस ने जुलूस में दिखाए घायल, जेल के गेट पर आरोपी उतारने लगे पट्टियां
    ("21424fe2-4433-46e5-969a-73a545bfece0", "81dc849e-2659-4471-84ad-c880391d0ae5"): (False, "agree"),  # पुल‍िस ने फर्जी प्लास्टर बांधे आरोपियों का न‍िकाला [...]
    ("21424fe2-4433-46e5-969a-73a545bfece0", "c3f8fe9e-931e-4482-92f6-5d4c20da621c"): (False, "agree"),  # फर्जी पुलिस अफसर का 'असली' दबदबा? महिला CO संग आरोपी [...]
    ("21424fe2-4433-46e5-969a-73a545bfece0", "c41d5c45-800a-47ff-b168-965844766148"): (False, "agree"),  # बलिया में युवक की पीठ में घोंपा चाकू, उसी हालत में [...]
    ("21424fe2-4433-46e5-969a-73a545bfece0", "c4e1ff66-1d9b-490b-b450-1bdb4bc65602"): (False, "agree"),  # कांवड़ियों ने पुलिस जीप से निकालकर दौड़ा-दौड़ाकर लाठी [...]
    ("21424fe2-4433-46e5-969a-73a545bfece0", "c887af64-3a20-4e21-8cd3-94abd6f82f79"): (False, "agree"),  # Sooryavanshi, Mayank help India end T20I losing streak
    ("21424fe2-4433-46e5-969a-73a545bfece0", "ce6f38a2-b45f-446e-80ff-66deae95a792"): (False, "agree"),  # VIDEO: गोलियों की बौछार, सड़क पर आतंक… PoK से [...]
    # seed: बिंद्यारानी ने जीता ब्रॉन्ज, कॉमनवेल्थ गेम्स में भारत को छठा मेडल
    ("59ca0c08-940d-48a0-9b16-9654a635fd82", "26b62d29-ce5e-4db8-9a2a-c12159f1ff8e"): (False, "agree"),  # CWG 2026: बुडिगिना और इमाम अली ने पैरा तैराकी में जगाई [...]
    ("59ca0c08-940d-48a0-9b16-9654a635fd82", "f3b09bee-db0b-496f-893c-45db40d2547b"): (False, "agree"),  # Commonwealth Games:ವೇಟ್‌ಲಿಫ್ಟಿಂಗ್‌ನಲ್ಲಿ ಬೆಳ್ಳಿ ಗೆದ್ದ [...]
    ("59ca0c08-940d-48a0-9b16-9654a635fd82", "f6dbcb01-9fad-42ce-b523-e8132fd57747"): (False, "agree"),  # CWG: Gyaneshwari wins silver as India claims 4th [...]
    ("59ca0c08-940d-48a0-9b16-9654a635fd82", "87b2609d-8d1b-4769-b767-f27d83e75d7b"): (False, "agree"),  # 20 ವರ್ಷಗಳ ಕಾಯುವಿಕೆಗೆ ಅಂತ್ಯ: ಚಿನ್ನದ ಪದಕಕ್ಕೆ ಮುತ್ತಿಟ್ಟ [...]
    ("59ca0c08-940d-48a0-9b16-9654a635fd82", "a6045848-6a69-45c8-8713-95325cc206b0"): (False, "agree"),  # CWG से पहले मुसीबत, भारत‍ीय बॉक्स‍िंग टीम का सामान 'गायब'
    ("59ca0c08-940d-48a0-9b16-9654a635fd82", "baef91f0-4fae-4a68-a1bd-5b8281c1a9f0"): (False, "agree"),  # Valluri Ajaya Babu Wins Silver Medal In Men''s 79kg [...]
    ("59ca0c08-940d-48a0-9b16-9654a635fd82", "e93ea4ad-ba73-4b50-bdfc-c391b69d88e3"): (False, "agree"),  # CWG: शर्मिला धनखड़ ने रचा इतिहास, पैरा शॉट पुट में [...]
    # seed: यूक्रेन से भिड़ने वाला था ईरान! 3 ठिकानों पर हमले का प्लान, 'माफी' से टली नई जंग
    ("3ff92b69-6f8c-4d13-aa7e-10c66d2e984b", "192902b6-fbff-4749-a2d6-f77a84ed0a57"): (False, "agree"),  # यूक्रेन ने रूसी ट्रकों को ड्रोन से मारा, सप्लाई लाइन [...]
    ("3ff92b69-6f8c-4d13-aa7e-10c66d2e984b", "20c8d650-5eb3-495a-93c0-71c5250a82ce"): (False, "agree"),  # BBC wins court approval to subpoena Trump's inner [...]
    ("3ff92b69-6f8c-4d13-aa7e-10c66d2e984b", "2451a340-71b4-4166-a046-615ad25db3aa"): (False, "agree"),  # 'अमेरिका हमें नही पढ़ाएगा युद्ध और शांति का पाठ...', [...]
    ("3ff92b69-6f8c-4d13-aa7e-10c66d2e984b", "3a18782f-8c12-4aff-adee-5e772073dad5"): (False, "agree"),  # Top US commander Bradley Cooper's warning changed [...]
    ("3ff92b69-6f8c-4d13-aa7e-10c66d2e984b", "405b58a9-1c69-4f08-bdfb-41da1cb9aa63"): (False, "agree"),  # ईरान से जुड़े जहाज पर यूक्रेनी हमला, खतरे में दुन‍िया [...]
    ("3ff92b69-6f8c-4d13-aa7e-10c66d2e984b", "4bb88ba1-c572-4dd1-bf4c-f0fab1b3182d"): (False, "agree"),  # ಇರಾನ್‌ ಮೇಲೆ ಅಮೆರಿಕ ಮತ್ತೆ ದಾಳಿ
    ("3ff92b69-6f8c-4d13-aa7e-10c66d2e984b", "6a534c92-fe42-4cec-a87c-163bd6b9d867"): (False, "agree"),  # यूक्रेन ने रूस के अंदर की 1200 KM लंबी डीप स्ट्राइक, [...]
    ("3ff92b69-6f8c-4d13-aa7e-10c66d2e984b", "992d779a-388a-4633-a3e1-54f91f0b7b7e"): (False, "agree"),  # Oil prices touch six week high as Strait of Hormuz is [...]
    ("3ff92b69-6f8c-4d13-aa7e-10c66d2e984b", "a43e4460-ab9c-44f3-a8ce-7a1e2d8b6874"): (False, "agree"),  # ईरान पर करारी चोट, US ने एयरक्राफ्ट हैंगर और ड्रोन [...]
    ("3ff92b69-6f8c-4d13-aa7e-10c66d2e984b", "a45ba293-2ca4-49fb-8571-5e52b5fd0308"): (False, "agree"),  # 'நட்புறவான பேச்சுவார்த்தை' நடப்பதாக கூறும் டிரம்ப்; [...]
    # seed: सरकार ने की सोनम वांगचुक से बातचीत की पहल, जेपी नड्डा-जितेंद्र सिंह ने की मुलाकात
    ("3ca63045-54db-4f32-b464-01118a56bebf", "48a19b47-89f8-4d81-bb1a-4c6f8e6fcd95"): (False, "agree"),  # 'लाखों युवाओं का भविष्य तो बर्बाद हो गया', पेपर लीक पर [...]
    ("3ca63045-54db-4f32-b464-01118a56bebf", "522f034a-e5d3-43ae-8a13-a33d36fd31fa"): (False, "agree"),  # 'अनशन तोड़ें, हमारी लड़ाई जारी रहेगी', दिपके की [...]
    ("3ca63045-54db-4f32-b464-01118a56bebf", "872e3f8b-01ca-4939-98e4-72a3157d796b"): (False, "agree"),  # Sonam से मेदांता अस्पताल में मिले 2 केंद्रीय मंत्री!
    ("3ca63045-54db-4f32-b464-01118a56bebf", "87aa85a1-c580-470a-bc60-83e74552128d"): (False, "agree"),  # CJP protest LIVE: CJP claims police parked ‘damaged [...]
    ("3ca63045-54db-4f32-b464-01118a56bebf", "8b861941-65fa-47a7-a24f-d16d0d07ba2d"): (False, "agree"),  # 'गांधी का रास्ता आज भी प्रासंगिक', राजघाट पर बापू को [...]
    ("3ca63045-54db-4f32-b464-01118a56bebf", "a08d4689-af81-439b-b25f-a36922546433"): (False, "agree"),  # 'मैं अब भी जिंदा हूं...', सोनम वांगचुक ने अस्पताल से [...]
    ("3ca63045-54db-4f32-b464-01118a56bebf", "b9a14cd0-cecc-4eaf-af8b-628b95b40dc6"): (True, "adj:tejas-said-same:high"),  # Union Ministers Nadda, Jitendra Singh meet Wangchuk at [...]
    ("3ca63045-54db-4f32-b464-01118a56bebf", "ba1ff34d-aa7c-4154-b06e-e42ada094642"): (False, "agree"),  # Will end fast if young protesters spared punitive [...]
    ("3ca63045-54db-4f32-b464-01118a56bebf", "bf5e1a7b-1d5a-480f-ac5c-778e0418209d"): (False, "agree"),  # सोनम वांगचुक और जेपी नड्डा के बीच एक घंटे चली बैठक... [...]
    ("3ca63045-54db-4f32-b464-01118a56bebf", "d95bc9a0-9b39-4dc8-8ff7-47648db6a3dc"): (False, "agree"),  # सफदरजंग अस्पताल से डिस्चार्ज हुए वांगचुक, आगे के इलाज [...]
    # seed: सैमसंग का बड़ा धमाका, स्क्रीन मोड़ने वाले तीन फ़ोन लॉन्च, जानें फीचर्स
    ("117d0e83-b6e8-4bce-a4bb-adcb270a4f68", "415c9a91-cc7e-46bf-92cb-bcc17a7619ee"): (True, "agree"),  # Samsung का सबसे बड़ा धमाका: Galaxy Z Fold 8 Ultra, Z [...]
    ("117d0e83-b6e8-4bce-a4bb-adcb270a4f68", "bce89d32-0fd5-4f64-b13d-5851bf2c77d4"): (False, "agree"),  # Samsung का आज बड़ा इवेंट, फोल्ड, फ्लिप और वॉच होगी लॉन्च
    ("117d0e83-b6e8-4bce-a4bb-adcb270a4f68", "c35bef3c-8f9a-4a5c-93a2-3c4b902f66bd"): (False, "agree"),  # कैमरा, माइक, स्पीकर और AI के साथ सैमसंग ने लॉन्च किया [...]
    ("117d0e83-b6e8-4bce-a4bb-adcb270a4f68", "0071a8d4-d88a-45bc-b016-a7afa6ab72da"): (False, "agree"),  # 6 साल बाद Vivo S सीरीज कर रही कमबैक, भारत में इस दिन [...]
    ("117d0e83-b6e8-4bce-a4bb-adcb270a4f68", "6a48796f-e59b-40a0-ada5-58e62b154114"): (False, "agree"),  # 7 साल बाद Vivo ला रहा इस सीरीज का फोन, मिलेगी 7000mAh [...]
    ("117d0e83-b6e8-4bce-a4bb-adcb270a4f68", "7606e41e-01da-43e7-adc6-2cfe27fca923"): (False, "agree"),  # Masters’ Union launches PGP in Sustainability and [...]
    ("117d0e83-b6e8-4bce-a4bb-adcb270a4f68", "972a8e93-5251-44e6-a959-8f98e4b0a107"): (False, "agree"),  # Samsung Galaxy Unpacked July 2026 Event Roundup: [...]
    # seed: பழனி முருகன் கோவில் மடத்தின் நில முறைகேடு வழக்கில் என்ன நடந்தது?பின்னணி விவரம்
    ("a1edfbbd-ffaf-4436-b5f0-0562aa00b983", "a560c094-064e-47a8-89a6-ef8b8105833c"): (False, "agree"),  # 'हिसाब लेकर रहेंगे', कनॉट प्लेस से पुलिस वैन पर हमले [...]
    ("a1edfbbd-ffaf-4436-b5f0-0562aa00b983", "da624f4e-c9a9-42fa-b6ca-915718738c4f"): (False, "agree"),  # 'ரூ.10,000 கடனால் கொத்தடிமை ஆனேன்': நாமக்கல் அருகே [...]
    # seed: ಅತ್ತ ತಮಿಳುನಾಡಿಗೆ ಕಾವೇರಿ ನೀರು ಬಿಡುವಂತೆ CWRC ಸೂಚನೆ: ಇತ್ತ ಸಂಧಾನ ಸೂತ್ರಕ್ಕೆ [...]
    ("39abff88-13be-485a-987a-30924a698281", "447fa769-0a81-4e98-a07c-5b9991c9813a"): (False, "agree"),  # ತಮಿಳುನಾಡಿಗೆ ಕಾವೇರಿ ನೀರು ಬಿಡಲು CWRC ಆದೇಶ: ಕಾಂಗ್ರೆಸ್ [...]
    ("39abff88-13be-485a-987a-30924a698281", "cdcc0513-47e3-4ea9-9751-dd597f6a1acc"): (False, "agree"),  # Mandya Protest: ತಮಿಳುನಾಡಿಗೆ ನೀರು ಹರಿಸಲು CWRC ಆದೇಶ [...]
    ("39abff88-13be-485a-987a-30924a698281", "32dfe63f-056a-4950-a3e7-dc3ed4067c9e"): (False, "agree"),  # KFCC Meeting On Cauvery Dispute: ಕಾವೇರಿ ನೀರು ವಿವಾದ; [...]
    ("39abff88-13be-485a-987a-30924a698281", "5a0d013c-6fd3-4615-a399-e220d8b2ee81"): (False, "agree"),  # Farmers oppose CWRC’s direction of release of water to [...]
    ("39abff88-13be-485a-987a-30924a698281", "5aa42b7c-3939-49b0-908e-c1967413be77"): (False, "agree"),  # ಆಲಮೇಲದಲ್ಲಿ ಬಣಜಿಗ ಸಮಾಜದ ಸಮಾವೇಶ ಆ. 2ರಂದು
    ("39abff88-13be-485a-987a-30924a698281", "91456068-eb82-4ac8-b943-969ba7230c09"): (False, "agree"),  # Ministerial aspirants disappointed as Karnataka [...]
    ("39abff88-13be-485a-987a-30924a698281", "b17a2a95-c2ab-4b52-91ac-e019a985e6bb"): (False, "agree"),  # ರಾಹುಲ್ ಸಭೆ ಅಂತ್ಯ, ಬೆಂಗಳೂರಿನತ್ತ ಡಿಕೆಶಿ: ಸಂಪುಟ ವಿಸ್ತರಣೆ [...]
    ("39abff88-13be-485a-987a-30924a698281", "d47b8d57-565c-4753-ac12-9349a08f0ba8"): (False, "agree"),  # ಕಾವೇರಿ ಆಘಾತ: ತಮಿಳುನಾಡಿಗೆ ದಿನಕ್ಕೆ 3,500 ಕ್ಯುಸೆಕ್ ನೀರು [...]
    ("39abff88-13be-485a-987a-30924a698281", "e78b7ab7-6884-49c8-84ce-7aa5a76e8141"): (False, "agree"),  # ತಮಿಳುನಾಡಲ್ಲಿ ವ್ಯರ್ಥವಾಗಿ ಸಮುದ್ರ ಸೇರುತ್ತಿರುವ ಕಾವೇರಿ [...]
    ("39abff88-13be-485a-987a-30924a698281", "fd2ec2e8-c31f-42ea-866b-044f6cd1c963"): (False, "agree"),  # ಕೈತಪ್ಪಿದ ಸಚಿವ ಸ್ಥಾನ: ರೆಬೆಲ್ಸ್​​ ಸಭೆಯಲ್ಲಿ ಅಪ್ಪಾಜಿ [...]
    # seed: ಎ ಸರ್ಟಿಫಿಕೇಟ್ ಸಿನಿಮಾಗೆ ಮಕ್ಕಳನ್ನು ಕರೆತಂದ ಪೋಷಕರು; ‘ಜನ ನಾಯಗನ್’ ಪ್ರದರ್ಶನ ಬಂದ್
    ("a2c6547f-1586-4248-8953-db36a4c2b803", "05576bb4-9f95-4e58-9fdf-a4f5059a372c"): (False, "agree"),  # ಜೋಗ ಜಲಪಾತದ ವೀಕ್ಷಣೆಗೆ ಜನಸಾಗರ; ಪ್ರವಾಸಿಗರ ಸುರಕ್ಷತೆಗೆ ಆದ್ಯತೆ
    ("a2c6547f-1586-4248-8953-db36a4c2b803", "0c903786-86ee-41c3-86cd-e8138e2d9c24"): (False, "agree"),  # Coaching centre tutor held by Belagavi police
    ("a2c6547f-1586-4248-8953-db36a4c2b803", "28e206c8-ae44-4857-9b65-52c7d428291f"): (False, "agree"),  # 10 acres of encroached Kerala government land in [...]
    ("a2c6547f-1586-4248-8953-db36a4c2b803", "32dfe63f-056a-4950-a3e7-dc3ed4067c9e"): (False, "agree"),  # KFCC Meeting On Cauvery Dispute: ಕಾವೇರಿ ನೀರು ವಿವಾದ; [...]
    ("a2c6547f-1586-4248-8953-db36a4c2b803", "4af6f3bd-5ef9-4ff8-9bec-d3f0c21c9532"): (False, "agree"),  # ವಿಜಯ್ ಅವರೇ ಬಲವಂತವಾಗಿ ನೀರು ಪಡೆಯಬೇಡಿ: ಪ್ರಥಮ್
    ("a2c6547f-1586-4248-8953-db36a4c2b803", "5d3542db-5478-47f2-b807-f4602beb19f5"): (False, "agree"),  # ‘ಸ್ಪೈಡರ್ ಮ್ಯಾನ್’ ಹೊಸ ಚಿತ್ರಕ್ಕೆ ಸೆನ್ಸಾರ್ ಕತ್ತರಿ: 8 [...]
    ("a2c6547f-1586-4248-8953-db36a4c2b803", "5e82eb16-dd75-4b3e-9b1e-eebfd824e3cb"): (False, "agree"),  # Jana Nayagan Day 5: Thalapathy Vijay's final film [...]
    ("a2c6547f-1586-4248-8953-db36a4c2b803", "a2f64750-9563-4ae2-ba8e-645f7b520106"): (False, "agree"),  # 23 अप्रैल की जगह 23 मार्च की बच्चे की DOB, HC ने लगाया [...]
    ("a2c6547f-1586-4248-8953-db36a4c2b803", "a57e5a85-ecc1-4573-8683-23128cdb3d91"): (False, "agree"),  # Students encouraged to file complaint if engineering [...]
    ("a2c6547f-1586-4248-8953-db36a4c2b803", "fa358e44-a763-4536-b090-ef02b8b04e7d"): (False, "agree"),  # ಜೂನಿಯರ್ ಎನ್‌ಟಿಆರ್‌ ಹೆಗಲಿಗೆ ಗಾಯ: 6-8 ವಾರ ವಿಶ್ರಾಂತಿಗೆ [...]
    # seed: ಕನಕಗಿರಿ ಬರ ಪೀಡಿತ ತಾಲ್ಲೂಕು ಘೋಷಣೆಗೆ ಆಗ್ರಹಿಸಿ ಬಿಜೆಪಿ ಪ್ರತಿಭಟನೆ
    ("c5424edd-c3d9-4630-a8cb-6e4c32ae1e7a", "3ecdc74c-6ef3-45af-91a6-50a3a9e3989d"): (False, "agree"),  # ಬಳ್ಳಾರಿಯಲ್ಲಿ ಬರ ಪರಿಹಾರಕ್ಕೆ ಬಿಜೆಪಿ ರೈತ ಮೋರ್ಚಾದಿಂದ [...]
    ("c5424edd-c3d9-4630-a8cb-6e4c32ae1e7a", "53ecd381-b890-47a9-b971-24bad4474b95"): (False, "agree"),  # Ashok slams State govt. over its failure to respond to [...]
    ("c5424edd-c3d9-4630-a8cb-6e4c32ae1e7a", "54be9e50-ca25-437e-9842-727f60492246"): (False, "agree"),  # ತಂದೆ ಜೊತೆ ಸಚಿವರಾಗಿದ್ದವರ ಸಂಪುಟದಲ್ಲಿ ಪುತ್ರ ಸಚಿವ
    ("c5424edd-c3d9-4630-a8cb-6e4c32ae1e7a", "556bd6f1-d422-45e3-aa81-e6a04b08afe7"): (False, "agree"),  # ಹೊಸಪೇಟೆ| ಖಜಾನೆ ಖಾಲಿ ಆಗಿರುವುದಕ್ಕೆ ಸರ್ಕಾರ ಬರ ಪರಿಹಾರ [...]
    ("c5424edd-c3d9-4630-a8cb-6e4c32ae1e7a", "7410c0ed-e54b-4152-8f58-ede2fa84e43b"): (False, "agree"),  # ಮುಂಡರಗಿ ತಾಲ್ಲೂಕನ್ನು ಬರಪೀಡಿತ ಎಂದು ಘೋಷಿಸಲು ರೈತರ ಆಗ್ರಹ
    ("c5424edd-c3d9-4630-a8cb-6e4c32ae1e7a", "adb2b7dc-f92b-4087-9d4a-502811066ca4"): (False, "agree"),  # ₹10 ಸಾವಿರ ಕೋಟಿ ಬಿಡುಗಡೆಗೆ ಆಗ್ರಹ, ಬಿಜೆಪಿ ಶಾಸಕ ಸುರೇಶ್‌ಗೌಡ [...]
    ("c5424edd-c3d9-4630-a8cb-6e4c32ae1e7a", "b17a2a95-c2ab-4b52-91ac-e019a985e6bb"): (False, "agree"),  # ರಾಹುಲ್ ಸಭೆ ಅಂತ್ಯ, ಬೆಂಗಳೂರಿನತ್ತ ಡಿಕೆಶಿ: ಸಂಪುಟ ವಿಸ್ತರಣೆ [...]
    ("c5424edd-c3d9-4630-a8cb-6e4c32ae1e7a", "da568102-01c3-4291-86f1-5e2ec40ec2e4"): (False, "agree"),  # Karnataka getting ready for Tamil Nadu CM Vijay’s [...]
    ("c5424edd-c3d9-4630-a8cb-6e4c32ae1e7a", "eabca1cc-e28b-448b-a292-f02337a47e31"): (False, "agree"),  # Meeting with MPs in Delhi ‘major success’: Karnataka [...]
    ("c5424edd-c3d9-4630-a8cb-6e4c32ae1e7a", "f8c4210a-10f5-4d77-a3a4-4f01a9fb6e4c"): (False, "agree"),  # ಬರ ಘೋಷಣೆಗೆ ಆಗ್ರಹಿಸಿ ಕೊಪ್ಪಳದಲ್ಲಿ ಬಿಜೆಪಿ ಧರಣಿ
    # seed: ಕಾಮನ್ ವೆಲ್ತ್ ಕ್ರೀಡಾಕೂಟ: ಶಾಟ್‌ಪಟ್‌ನಲ್ಲಿ ಮೈಸೂರಿನ ಶಿಲ್ಪಾಗೆ ಕಂಚು
    ("a0b19efb-991f-424a-868a-41368929202a", "87b2609d-8d1b-4769-b767-f27d83e75d7b"): (False, "agree"),  # 20 ವರ್ಷಗಳ ಕಾಯುವಿಕೆಗೆ ಅಂತ್ಯ: ಚಿನ್ನದ ಪದಕಕ್ಕೆ ಮುತ್ತಿಟ್ಟ [...]
    ("a0b19efb-991f-424a-868a-41368929202a", "255d7919-e11a-4663-b7bc-23cf454ce235"): (False, "agree"),  # ಹೊಸಹಳ್ಳಿ ಬೆಟ್ಟ, ಕಾಗಿಹರೆಗೆ ಪ್ರವಾಸಿ ವಾಹನಗಳಿಗೆ ಅರಣ್ಯ [...]
    ("a0b19efb-991f-424a-868a-41368929202a", "3df67ad5-d3fa-45e5-ab92-4ee03b5f6910"): (False, "agree"),  # ಹೂವಿನಹಡಗಲಿ ರೈತರಿಂದ ಕಾಲುವೆ ಸ್ವಚ್ಛತೆ ಶ್ರಮದಾನ
    ("a0b19efb-991f-424a-868a-41368929202a", "438256ec-f411-4817-b83e-cf73355c282e"): (False, "agree"),  # ಆಹಾರ ವಿಷಯುಕ್ತಗೊಂಡಿದ್ದರಿಂದ ಚಿನ್ನದ ಪದಕ ಕೈತಪ್ಪಿತು: ಸೆಲ್ವ ಪ್ರಭು
    ("a0b19efb-991f-424a-868a-41368929202a", "5942722f-7328-4277-af11-efab0168ab71"): (False, "agree"),  # Andhra businessman fires 3 rounds after badminton team [...]
    ("a0b19efb-991f-424a-868a-41368929202a", "63d8a78c-ac2f-4fa4-be47-338dcbf43224"): (False, "agree"),  # ಗಾಣಿಗ ಸಮುದಾಯದ ಮಕ್ಕಳಿಗೆ ಪುರಸ್ಕಾರ, ಶಾಸಕ ಶರತ್ ಬಚ್ಚೇಗೌಡ ಭರವಸೆ
    ("a0b19efb-991f-424a-868a-41368929202a", "c9b30ab6-6147-49c2-bb5b-b97a8f3497a2"): (False, "agree"),  # ಲಿಫ್ಟರ್‌ಗಳಿಗೆ ಮಾಂಡವೀಯ ಶ್ಲಾಘನೆ
    ("a0b19efb-991f-424a-868a-41368929202a", "d6159e3d-8907-4e1b-89ef-2ec2310885f4"): (False, "agree"),  # ಭಟ್ಕಳ ವಿದ್ಯಾಂಜಲಿ ಶಾಲೆಯ ವಿದ್ಯಾರ್ಥಿಗಳಿಂದ [...]
    ("a0b19efb-991f-424a-868a-41368929202a", "d886235c-da64-40c2-9ec5-93bc2fbf6da2"): (False, "agree"),  # ಹಟ್ಟಿ ವಲಯ ಮಟ್ಟದ ಕ್ರೀಡಾಕೂಟಕ್ಕೆ ಚಾಲನೆ, ಪ್ರತಿಭೆ [...]
    # seed: ಗುಟ್ಕಾ ತಿನ್ನುವುದನ್ನು ತ್ಯಜಿಸುವೆ ಎಂದ ಶಾಸಕ ಅಶೋಕ ಮನಗೂಳಿ
    ("cf2c3b71-cf09-433e-acd1-18bd101c40c0", "35f3d046-69e4-4cd5-9f62-9d698e3f223f"): (False, "agree"),  # ಡ್ರಗ್ಸ್ ಮಾಫಿಯಾಗೆ ಕಡಿವಾಣ ಅಗತ್ಯ ಶಾಸಕ ಅಶೋಕ ಮನಗೂಳಿ ಹೇಳಿಕೆ
    ("cf2c3b71-cf09-433e-acd1-18bd101c40c0", "15c595e1-2ace-4c58-a70b-62da4968945c"): (False, "agree"),  # ಗೌರಿಬಿದನೂರು: ‘ಡ್ರಗ್ಸ್ ಬೇಡ ಬ್ರೋ’ ಅಭಿಯಾನಕ್ಕೆ ಚಾಲನೆ
    ("cf2c3b71-cf09-433e-acd1-18bd101c40c0", "20157383-1438-43d8-b02a-7d3019e5d0aa"): (False, "agree"),  # ಜಾಹೀರಾತು ನಂಬಿ ಯುವಜನತೆ ಮಾದಕ ವ್ಯಸನಗಳ ಮೊರೆ ಹೋಗದಿರಿ
    ("cf2c3b71-cf09-433e-acd1-18bd101c40c0", "3010282c-b161-4565-94e1-d2e3f912d64f"): (False, "agree"),  # Eviction looms over 258 shop owners at Vijayawada’s [...]
    ("cf2c3b71-cf09-433e-acd1-18bd101c40c0", "589e6466-e5f5-452a-b883-e4587ad64f80"): (False, "agree"),  # ತರೀಕೆರೆ ಮಾದರ ಮಹಾಸಭಾದ ತಾಲ್ಲೂಕು ಅಧ್ಯಕ್ಷರಾಗಿ ಅಣ್ಣಯ್ಯ ನೇಮಕ
    ("cf2c3b71-cf09-433e-acd1-18bd101c40c0", "65e2546e-7371-4f7b-9f99-9346c171d933"): (False, "agree"),  # Police recruitment drive launched for 7,437 posts [...]
    ("cf2c3b71-cf09-433e-acd1-18bd101c40c0", "8aee2255-307c-4916-93d4-43ab63ae401c"): (False, "agree"),  # ಚಿತ್ರದುರ್ಗದಲ್ಲಿ ಆಗಸ್ಟ್‌ 1ರಂದು ವ್ಯಸನ ಮುಕ್ತ ದಿನ ಆಚರಣೆ
    ("cf2c3b71-cf09-433e-acd1-18bd101c40c0", "a27e9d95-e008-4409-bf4d-911e1a186efe"): (False, "agree"),  # ಮೂಡಲಗಿ ಅರಭಾವಿಯಲ್ಲಿ ವ್ಯಸನ ಮುಕ್ತ ದಿನಾಚರಣೆ ಆಚರಣೆ
    ("cf2c3b71-cf09-433e-acd1-18bd101c40c0", "a8a5e90a-6d30-41e8-8782-7aad2119111a"): (False, "agree"),  # ಗೋಕಾಕದಲ್ಲಿ ವ್ಯಸನ ಮುಕ್ತಿ ಜಾಗೃತಿ ಅಭಿಯಾನ, ಸಿಪಿಐ ಬ್ಯಾಕೂಡ ಕರೆ
    # seed: ಗೃಹಜ್ಯೋತಿ ಪರಿಷ್ಕರಣೆಗೆ ಸಾರ್ವಜನಿಕರು ಸಹಕರಿಸಿ: ಶೌಕತ್ ಅಲಿ
    ("724692f8-20de-4ef6-8dec-71b5545cae3b", "012b49b6-d357-4a64-8a1f-266ce544c83a"): (False, "agree"),  # ರಾಣೆಬೆನ್ನೂರು ಸುತ್ತಮುತ್ತಲಿನ ಪ್ರದೇಶಗಳಲ್ಲಿ ಇಂದು ವಿದ್ಯುತ್‌ [...]
    ("724692f8-20de-4ef6-8dec-71b5545cae3b", "05b639af-b95b-4a5a-bd51-57ccf45f0d4d"): (False, "agree"),  # ಹುಬ್ಬಳ್ಳಿ ವಿವಿಧೆಡೆ ವಿದ್ಯುತ್‌ ವ್ಯತ್ಯಯ ನಾಳೆ ಬೆಳಿಗ್ಗೆ [...]
    ("724692f8-20de-4ef6-8dec-71b5545cae3b", "2ac5553e-4eb1-4cba-ab80-e7734ff376dc"): (False, "agree"),  # ಮಂಗಳೂರು, ಮೂಡುಬಿದಿರೆ ಹಾಗೂ ಜೆಪ್ಪು ಪ್ರದೇಶಗಳಲ್ಲಿ ವಿದ್ಯುತ್‌ [...]
    ("724692f8-20de-4ef6-8dec-71b5545cae3b", "54877539-2889-4376-87b3-804923a1ae97"): (False, "agree"),  # ಏತ ನೀರಾವರಿ ಯೋಜನೆಗಳ ವೈಫಲ್ಯದ ಹಿನ್ನೆಲೆಯಲ್ಲಿ ಇಂಜಿನಿಯರ್ [...]
    ("724692f8-20de-4ef6-8dec-71b5545cae3b", "964862e0-f80a-4b96-bbe1-bd6cdf2ff99e"): (False, "agree"),  # ಬಳಕೆಯಲ್ಲಿ ಇಲ್ಲದ ವಿದ್ಯುತ್ ಕಂಬ, ಪರಿವರ್ತಕ ತೆರವು ಕಾರ್ಯಾಚರಣೆ
    # seed: ತಿಪಟೂರು ರೈಲು ನಿಲ್ದಾಣದಲ್ಲಿ ಕಾಮಗಾರಿಯಿಂದ ಕೆಲವು ರೈಲುಗಳ ಸಂಚಾರ ನಿಯಂತ್ರಣ
    ("7fce92b8-eb5d-4565-89d7-54491d5b2dd8", "024f3d2b-bf9c-4963-b443-2df56bfbb493"): (False, "agree"),  # ಪಶ್ಚಿಮ ಘಟ್ಟ | ಹಳಿ ದುರಸ್ತಿ ಕಾರ್ಯ ಪೂರ್ಣ: ರೈಲು ಸಂಚಾರ ಪುನಾರಂಭ
    ("7fce92b8-eb5d-4565-89d7-54491d5b2dd8", "1025d13a-a87f-4dee-a104-e5884ab0409c"): (False, "agree"),  # South Western Railway records highest-ever freight [...]
    ("7fce92b8-eb5d-4565-89d7-54491d5b2dd8", "3728915a-3a69-4f9e-ba5e-54ba588169a4"): (False, "agree"),  # ಪೀಣ್ಯ ಮೇಲ್ಸೇತುವೆ: ವಾಹನ ಸಂಚಾರ ನಿಷೇಧ
    ("7fce92b8-eb5d-4565-89d7-54491d5b2dd8", "689e0600-c842-4bd1-a53f-a4b9b8707eec"): (False, "agree"),  # ಗಾಂಧಿ ಶಿಲ್ಪ ಬಜಾರ್ ಮೇಳ ಇಂದಿನಿಂದ ಜೆಎಸ್‌ಎಸ್ ಅರ್ಬನ್‌ ಹಾತ್‌ನಲ್ಲಿ
    ("7fce92b8-eb5d-4565-89d7-54491d5b2dd8", "7071dafc-38ed-4ed1-81d2-37aa676c3873"): (False, "agree"),  # Night train services on Bengaluru-Mangaluru- [...]
    ("7fce92b8-eb5d-4565-89d7-54491d5b2dd8", "bb16f2e7-4099-4cad-a40c-6990d853ca25"): (False, "agree"),  # ಮಾರುಕಟ್ಟೆ ಪ್ರದೇಶಗಳಲ್ಲಿ ಪಾದಚಾರಿ ಮಾರ್ಗಗಳ ಒತ್ತುವರಿ ತೆರವು
    ("7fce92b8-eb5d-4565-89d7-54491d5b2dd8", "c65de3ef-e22c-4f72-bdf5-56f5dfd9fdbd"): (False, "agree"),  # Adhesive gel pack found with food in Mysuru-Chennai [...]
    ("7fce92b8-eb5d-4565-89d7-54491d5b2dd8", "cd7035f1-64b7-4927-a056-5e1d401388ef"): (False, "agree"),  # ಸಿಂಗಪುರದಿಂದ ಅಕ್ರಮವಾಗಿ ಸಾಗಿಸುತ್ತಿದ್ದ ₹2.87 ಕೋಟಿ ಮೌಲ್ಯದ [...]
    ("7fce92b8-eb5d-4565-89d7-54491d5b2dd8", "fa3b1445-6740-4149-a28d-a0160561bb14"): (False, "agree"),  # ಪೀಣ್ಯ ಮೇಲ್ಸೇತುವೆ ಸಂಚಾರ ನಿರ್ಬಂಧ: ಪರ್ಯಾಯ ಮಾರ್ಗ ಹೀಗಿದೆ
    # seed: ತೊಗರಿ, ಹತ್ತಿ ವಿಮೆ ಜುಲೈ 31 ಕೊನೆ ದಿನ ಕಲಬುರಗಿ
    ("7df24ddc-0f86-44b8-998f-52221e7173f1", "61e9369f-855d-4206-be47-45434e09cd53"): (False, "agree"),  # ಬೆಳೆವಿಮೆ ಜಾಗೃತಿ ಜಾಥಾ: ತಹಶೀಲ್ದಾರ್‌ ಚಾಲನೆ, ರೈತರಿಗೆ [...]
    ("7df24ddc-0f86-44b8-998f-52221e7173f1", "3fda782f-6882-4df8-ad51-0c55d6032abd"): (False, "agree"),  # A.P. Deputy CM Pawan Kalyan stresses awareness drive [...]
    ("7df24ddc-0f86-44b8-998f-52221e7173f1", "5bfaab60-a44a-4ade-bee5-74fac368484e"): (False, "agree"),  # यूपी कैबिनेट की बड़ी बैठक, 21 से अधिक फैसलों पर लग [...]
    ("7df24ddc-0f86-44b8-998f-52221e7173f1", "77bdee6e-8aa5-4b65-af17-397d1df76b7e"): (False, "agree"),  # Farmers in Villupuram urged to enroll under crop [...]
    ("7df24ddc-0f86-44b8-998f-52221e7173f1", "821d4273-4144-4d81-b4aa-c4113c6427e0"): (False, "agree"),  # Naidu directs comprehensive support for farmers in [...]
    ("7df24ddc-0f86-44b8-998f-52221e7173f1", "a001837c-410a-44a9-b0c1-aeeff8c2b4c7"): (False, "agree"),  # ಚಿಕ್ಕಮಗಳೂರು ಬೆಳೆ ವಿಮಾ ಯೋಜನೆಗೆ ಜುಲೈ 31 ಕೊನೆಯ ದಿನ
    ("7df24ddc-0f86-44b8-998f-52221e7173f1", "b27ab95b-4a5f-4349-9d8e-4da3571528a6"): (False, "agree"),  # ಬೆಂಗಳೂರು: ಬೆಳೆ ವಿಮೆ ಮಾಹಿತಿ ರಥಕ್ಕೆ ಜಿಲ್ಲಾ ಪಂಚಾಯಿತಿ [...]
    ("7df24ddc-0f86-44b8-998f-52221e7173f1", "b31fe789-8847-42b0-b965-f0331c7c7b59"): (False, "agree"),  # ರಾಮನಗರದಲ್ಲಿ ಬೆಳೆ ವಿಮೆ ಯೋಜನೆಗೆ ನೋಂದಣಿ ಪ್ರಾರಂಭ
    ("7df24ddc-0f86-44b8-998f-52221e7173f1", "e11d7fc7-ce4c-489b-9f79-5b610baa2b00"): (False, "agree"),  # ಬೆಳೆ ವಿಮೆ ನೋಂದಣಿ ಅವಧಿ ವಿಸ್ತರಣೆಗೆ ಚಿಕ್ಕಮಗಳೂರು [...]
    # seed: ಪೇಟಿಎಂ ಪೇಮೆಂಟ್ಸ್ ಬ್ಯಾಂಕ್ ಮುಚ್ಚಲು ದೆಹಲಿ ಹೈಕೋರ್ಟ್ ಆದೇಶ
    ("38d1fc33-8358-44e9-b110-2f5fc65e18b9", "0201f4e4-0aad-4ee9-bd7d-0e3777660c3e"): (False, "agree"),  # भारत में जल्द आ रहे हैं प्लास्टिक के नोट, सरकार ने दी [...]
    ("38d1fc33-8358-44e9-b110-2f5fc65e18b9", "0d0b79a4-5256-40e8-99cf-fca468c8ca09"): (False, "agree"),  # ಐದು ವರ್ಷಗಳಿಂದ ಬಾರದ ಪಿಂಚಣಿ: ವೃದ್ಧೆಯ ಪರದಾಟ, ಬ್ಯಾಂಕ್ [...]
    ("38d1fc33-8358-44e9-b110-2f5fc65e18b9", "1c11952a-ed29-4b5e-b0c9-169d1ae3ba23"): (False, "agree"),  # राम मंदिर ट्रस्ट की बैठक, श्रद्धालुओं की सुविधा और [...]
    ("38d1fc33-8358-44e9-b110-2f5fc65e18b9", "1f19955b-f206-4d5c-a46b-89aad7578c38"): (False, "agree"),  # Okayed trials for polymer notes for ₹10, 20; no plan [...]
    ("38d1fc33-8358-44e9-b110-2f5fc65e18b9", "22196fb8-21e8-4bc9-b9dd-63cff5c62e4a"): (False, "agree"),  # Bengaluru: Homemaker alleges ₹2.5 crore fraud by [...]
    ("38d1fc33-8358-44e9-b110-2f5fc65e18b9", "26f1a782-cf04-4ef9-8ca2-38e4dfaa094e"): (False, "agree"),  # ತಳಮಟ್ಟದಲ್ಲಿ ಕಾಂಗ್ರೆಸ್ ಸಂಘಟನೆ ಬಲಪಡಿಸಿ - ಎಐಸಿಸಿ ವೀಕ್ಷಕ [...]
    ("38d1fc33-8358-44e9-b110-2f5fc65e18b9", "791302b3-69b9-446c-869c-411731bb231a"): (False, "agree"),  # 14 ಬಿಲಿಯನ್ ಡಾಲರ್ ಮಾರಾಟ
    ("38d1fc33-8358-44e9-b110-2f5fc65e18b9", "b7c79b03-5302-494a-b70f-90249867923a"): (False, "agree"),  # ಬೆಂಗಳೂರಿನ ಕೆಲ ವಾರ್ಡ್‌ಗಳಲ್ಲಿ ಮತದಾರರ ಪರಿಷ್ಕರಣೆ ಅಮಾನತು
    ("38d1fc33-8358-44e9-b110-2f5fc65e18b9", "f49de8f0-84f5-49d8-af4d-fe76846e4aea"): (False, "agree"),  # ಹೈಕೋರ್ಟ್ ಆದೇಶ ಉಲ್ಲಂಘಿಸಿ ಬ್ಯಾನರ್: ತೆರವಿಗೆ ಆಗ್ರಹ
    ("38d1fc33-8358-44e9-b110-2f5fc65e18b9", "f83811e0-9725-418c-8ad3-ad32abfd27fa"): (False, "agree"),  # ಪೆಲೆಟ್ ಗನ್‌ ಬಳಕೆಗೆ ನಿಷೇಧ ಕೋರಿ ಸುಪ್ರೀಂ ಮೆಟ್ಟಿಲೇರಿದ [...]
    # seed: ಫೇಸ್​ಬುಕ್​​ನಿಂದ ಪ್ರಧಾನಿ ಮೋದಿ ವೀಡಿಯೊ ಡಿಲೀಟ್: ತಾಂತ್ರಿಕ ದೋಷ ಎಂದು ಸರ್ಕಾರಕ್ಕೆ ಮೆಟಾ [...]
    ("a1c75095-228e-434a-83bc-ecd7c442a752", "0b68a4c2-9a7d-49ab-8280-d37602634033"): (False, "agree"),  # Trust biggest challenge in preventing paper leaks, [...]
    ("a1c75095-228e-434a-83bc-ecd7c442a752", "1a540436-0db9-439c-a046-4798fb4f3ee5"): (False, "agree"),  # CJP प्रोटेस्ट: पीएम मोदी का फेसबुक वीडियो हटाने पर [...]
    ("a1c75095-228e-434a-83bc-ecd7c442a752", "206c1c57-f66a-40c4-8f94-2a53a2042059"): (False, "agree"),  # Nandan Nilekani to lead exam reforms: Amid Gen-Z ire, [...]
    ("a1c75095-228e-434a-83bc-ecd7c442a752", "53b93c88-b1ff-4595-a0aa-de22da30ba16"): (False, "agree"),  # पीएम मोदी का वीडियो हटाने को लेकर सरकार सख्त, मेटा से [...]
    ("a1c75095-228e-434a-83bc-ecd7c442a752", "6dfe3081-a639-41c3-8e73-a2aee23afa1e"): (False, "agree"),  # ಮೋದಿ ವಿಡಿಯೋ ಡಿಲೀಟ್, ಮೆಟಾ ಸಂಸ್ಥೆಯ ಗ್ಲೋಬಲ್ ಪಬ್ಲಿಕ್ [...]
    ("a1c75095-228e-434a-83bc-ecd7c442a752", "86be1081-661f-4930-87fe-1c6951b6335c"): (False, "agree"),  # 'गलती से हट गया था...', PM मोदी का पोस्ट रिमूव होने पर [...]
    ("a1c75095-228e-434a-83bc-ecd7c442a752", "a6e8f22d-cf38-437d-bb02-fa33dc16bc56"): (False, "agree"),  # Speaker’s nod to Sena (UBT) MPs’ merger challenged in SC
    ("a1c75095-228e-434a-83bc-ecd7c442a752", "b86b4764-0b19-4611-9d23-8c2714adf8a0"): (False, "agree"),  # 'वो बात से मुकर गए...', राहुल गांधी-जितेंद्र सिंह के [...]
    ("a1c75095-228e-434a-83bc-ecd7c442a752", "e0155f1b-6978-4513-abfd-828dcc95ddf3"): (False, "agree"),  # 'कितने भी कानून बना लो, पेपर लीक नहीं रुकेगा': रामगोपाल यादव
    ("a1c75095-228e-434a-83bc-ecd7c442a752", "eb25830f-9a18-40e1-8f76-685854eb6fe7"): (False, "agree"),  # ಕ್ಷಮೆಯಾಚಿಸಲು ಸಿದ್ಧ: ಮೆಟಾ
    # seed: ಮಳೆಗಾಗಿ ಚಕ್ರಬಸವಣ್ಣನಿಗೆ ಹೊಸಹಳ್ಳಿ ಗ್ರಾಮಸ್ಥರಿಂದ ವಿಶೇಷ ಪೂಜೆ
    ("dda71da6-91a2-4f47-a2d7-dda9e99be5a0", "03ad04f5-cb24-4961-ab46-deae377691b2"): (False, "agree"),  # Man gets 10 years rigorous imprisonment for murdering [...]
    ("dda71da6-91a2-4f47-a2d7-dda9e99be5a0", "22196fb8-21e8-4bc9-b9dd-63cff5c62e4a"): (False, "agree"),  # Bengaluru: Homemaker alleges ₹2.5 crore fraud by [...]
    ("dda71da6-91a2-4f47-a2d7-dda9e99be5a0", "2eadb092-db31-410c-94e1-7913742030e2"): (False, "agree"),  # ಯುಜಿಡಿ ಸಹಾಯಕರ ಕಾಯಂಗೆ ಅಧಿಸೂಚನೆ: ಮಾಜಿ ಸಿಎಂ ಸಿದ್ದರಾಮಯ್ಯಗೆ [...]
    ("dda71da6-91a2-4f47-a2d7-dda9e99be5a0", "46f19a69-adea-4b8d-878a-a1ceb466b60f"): (False, "agree"),  # Eligible beneficiaries should not be deprived of [...]
    ("dda71da6-91a2-4f47-a2d7-dda9e99be5a0", "57f92d98-6b08-47a6-8598-771e59f3a3a3"): (False, "agree"),  # Chamundeshwari Vardhanti Mahotsav: ನಾಡದೇವಿ [...]
    ("dda71da6-91a2-4f47-a2d7-dda9e99be5a0", "9bf8133b-e344-4ccb-a40c-f86fd37822a0"): (False, "agree"),  # ಚಿಲವಾರು ಬಂಡಿ ಏತ ನೀರಾವರಿಯಿಂದ ಕೆರೆಗಳಿಗೆ ನೀರು ಹರಿಸಲಾಗಿದೆ
    ("dda71da6-91a2-4f47-a2d7-dda9e99be5a0", "a4bb1c50-5d26-4319-a1e8-7c0c6ed0c0c9"): (False, "agree"),  # ಬಳ್ಳಾರಿ ಜೆಡಿಎಸ್‌ನಿಂದ ಮಳೆಗಾಗಿ ವರುಣಯಾಗ ಪೂಜೆ
    ("dda71da6-91a2-4f47-a2d7-dda9e99be5a0", "d6dda365-61a6-4cfe-9cce-1917dad73852"): (False, "agree"),  # ಕಾರಟಗಿ ಅರಳಳ್ಳಿ ರಾಜರಾಜೇಶ್ವರಿ ಮಠದಲ್ಲಿ ಶರಣೋತ್ಸವ ನಾಳೆ
    ("dda71da6-91a2-4f47-a2d7-dda9e99be5a0", "e1cd4f33-eee4-4094-ac01-73eaa05fc109"): (False, "agree"),  # ಹಾವೇರಿ: ನ್ಯಾಯಬೆಲೆ ಅಂಗಡಿಯಲ್ಲಿ ಸಿನಿಮಾ ಟಿಕೆಟ್ ಮಾರಾಟ
    ("dda71da6-91a2-4f47-a2d7-dda9e99be5a0", "f8c4210a-10f5-4d77-a3a4-4f01a9fb6e4c"): (False, "agree"),  # ಬರ ಘೋಷಣೆಗೆ ಆಗ್ರಹಿಸಿ ಕೊಪ್ಪಳದಲ್ಲಿ ಬಿಜೆಪಿ ಧರಣಿ
    # seed: ಮಹಿಳೆಯರ ಸಬಲೀಕರಣಕ್ಕೆ ಜ್ಞಾನವಿಕಾಸ ಕೇಂದ್ರಗಳ ಸ್ಥಾಪನೆ
    ("3e0ef365-33a1-4395-a6eb-8ae8ababc381", "293539c1-c155-4166-9743-b79ed3fc0fe7"): (False, "agree"),  # 'ವ್ಯಸನ ಮುಕ್ತ ವಿಕಸಿತ ಭಾರತ' ಜಾಗೃತಿ ಜಾಥಾ ಆ.9ಕ್ಕೆ
    ("3e0ef365-33a1-4395-a6eb-8ae8ababc381", "6589eb0f-7e35-432b-a036-14db6ac9d001"): (False, "agree"),  # ಧರ್ಮಸ್ಥಳ ಗ್ರಾಮಾಭಿವೃದ್ಧಿ ಯೋಜನೆಯ ಮದ್ಯವರ್ಜನ ಶಿಬಿರ ಉದ್ಘಾಟನೆ
    ("3e0ef365-33a1-4395-a6eb-8ae8ababc381", "67e470b2-c361-4128-83b0-cbbac6c442c2"): (False, "agree"),  # ಧರ್ಮಸ್ಥಳ ಗ್ರಾಮಾಭಿವೃದ್ಧಿ ಯೋಜನೆ ಒಕ್ಕೂಟ ಪದಗ್ರಹಣ
    ("3e0ef365-33a1-4395-a6eb-8ae8ababc381", "d298fa5d-9933-4d7d-8f21-b041648a376f"): (False, "agree"),  # ಶುಲ್ಕರಹಿತ ‘ಡಿಜಿ ಪೇ’ ಸೇವೆ ಪಡೆಯಿರಿ ಎಂದು ತೀರ್ಥಹಳ್ಳಿಯಲ್ಲಿ ಘೋಷಣೆ
    ("3e0ef365-33a1-4395-a6eb-8ae8ababc381", "f96878d3-050e-4626-b37d-cc00437140d4"): (False, "agree"),  # ದೊಡ್ಡಹುಲ್ಲೂರಿನಲ್ಲಿ ಸ್ಕೊಡ್ವೆಸ್ ಸಂಸ್ಥೆಯಿಂದ ಜೀವನಶಕ್ತಿ [...]
    # seed: ಮೆಟ್ರೊ ಕ್ರೇನ್ ಏರಿ ಕೆಳಗಿಳಿಯಲು ಕೂಲಿ ಕಾರ್ಮಿಕ ಪರದಾಟ
    ("6e3bd48d-f9fe-418a-a307-0227174b9d3b", "a74ea304-dac1-485b-b49b-8c91ced9b992"): (False, "agree"),  # ಬೆಂಗಳೂರಲ್ಲಿ ರಾತ್ರೋರಾತ್ರಿ ಮೆಟ್ರೋ ಕ್ರೇನ್ ಏರಿ [...]
    ("6e3bd48d-f9fe-418a-a307-0227174b9d3b", "0b96a671-4bd6-411e-9d3b-854643e3f682"): (False, "agree"),  # ಮೆಟ್ರೊ ಹಳಿಗೆ ಹಾರಿದ ವ್ಯಕ್ತಿ ಸಾವು: ಹಳದಿ ಮಾರ್ಗದಲ್ಲಿ ಸಂಚಾರ [...]
    ("6e3bd48d-f9fe-418a-a307-0227174b9d3b", "1460597a-8549-4f2a-a7f3-08d1a51cc1a8"): (False, "agree"),  # ಸ್ನಾನದ ದೃಶ್ಯ ಸೆರೆ: ಬೆಂಗಳೂರಿನಲ್ಲಿ ಆರೋಪಿ ಮಂಜುನಾಥ್ ಬಂಧನ
    ("6e3bd48d-f9fe-418a-a307-0227174b9d3b", "1c8205ab-8810-423e-8366-20fdc8084c79"): (False, "agree"),  # Four youngsters drown in Sri Ram Sagar Project [...]
    ("6e3bd48d-f9fe-418a-a307-0227174b9d3b", "44dc72f7-d176-425f-9ace-81786c805b2e"): (False, "agree"),  # Passenger dies after jumping in front of Bengaluru [...]
    ("6e3bd48d-f9fe-418a-a307-0227174b9d3b", "658519f4-d30b-4190-a00b-dcf5aa804e22"): (False, "agree"),  # धधक रहा अल्जीरिया, 172 जगह लगी जंगल की आग... 42 अब भी बेकाबू
    ("6e3bd48d-f9fe-418a-a307-0227174b9d3b", "b235a9f7-ae84-47ee-bb89-6d23ffbd28ea"): (False, "agree"),  # VIDEO: स्कूल से घर जा रही चौथी क्लास की बच्ची नाले में [...]
    ("6e3bd48d-f9fe-418a-a307-0227174b9d3b", "bba5ad25-d3a1-455d-b22b-520239586652"): (False, "agree"),  # Nandi Hill cable car: Forest clearance pending, but [...]
    ("6e3bd48d-f9fe-418a-a307-0227174b9d3b", "ce3a10f5-58b7-4bdf-aa05-8e9c377c30e3"): (False, "agree"),  # ಹೊಸಪೇಟೆ | ಎರೆಬೂತ (ಹೆಬ್ಬಕ) ಸಂರಕ್ಷಣೆಗೆ ಅರಣ್ಯ ಇಲಾಖೆ ಬದ್ಧ: [...]
    # seed: ಮೊಟ್ಟೆ ಅನುದಾನ ಹೆಚ್ಚಳಕ್ಕೆ ಒತ್ತಾಯಿಸಿ ಅಂಗನವಾಡಿ ಕಾರ್ಯಕರ್ತೆಯರ ಪ್ರತಿಭಟನೆ
    ("0f0f1d01-8baf-4c85-9bc0-d6dbc2ddca13", "63296b7a-b2d6-468f-858d-ebba08bef5f3"): (False, "agree"),  # ಬಿಸಿಯೂಟ ಯೋಜನೆಯಲ್ಲಿ ವಿತರಿಸುವ ಮೊಟ್ಟೆಗಳ ಖರೀದಿ ದರ [...]
    ("0f0f1d01-8baf-4c85-9bc0-d6dbc2ddca13", "6e1bdf43-898a-470f-a5a4-474e69b15c31"): (False, "agree"),  # ಕುಮಟಾದ ಅಳ್ವೆಕೋಡಿ ಶಾಲಾ ಕೊಠಡಿಗಳ ಅನುದಾನ ಬಿಡುಗಡೆ ಮಧು ಬಂಗಾರಪ್ಪ
    ("0f0f1d01-8baf-4c85-9bc0-d6dbc2ddca13", "778b5416-6550-44db-b4f7-450be7115d38"): (False, "agree"),  # Friendship Day observed with tree conservation drive [...]
    ("0f0f1d01-8baf-4c85-9bc0-d6dbc2ddca13", "79cdab99-508d-4139-ace7-fc772e5a8600"): (False, "agree"),  # ರಿಯಾಯಿತಿ ಬೆಲೆಯಲ್ಲಿ ಎಮ್ಮೆ ವಿತರಣೆಗೆ ಕೋಮುಲ್ ಯೋಜನೆ
    ("0f0f1d01-8baf-4c85-9bc0-d6dbc2ddca13", "e052ef38-2b04-43d3-8f59-56be217c457d"): (False, "agree"),  # ದಾಂಡೇಲಿ ಪೌರಕಾರ್ಮಿಕರಿಗೆ 5ನೇ ತಾರೀಖಿನೊಳಗೆ ವೇತನ ಪಾವತಿಸಲು ಮನವಿ
    ("0f0f1d01-8baf-4c85-9bc0-d6dbc2ddca13", "e53eadca-adf4-41bb-b353-5d4d1e819c70"): (False, "agree"),  # ಅರ್ಹರು ಅನ್ನಭಾಗ್ಯ ಯೋಜನೆಯಿಂದ ವಂಚಿತರಾಗದಂತೆ ಕ್ರಮ ವಹಿಸಿ
    # seed: ಶಿರ್ವದಲ್ಲಿ ಬಹುಭಾಷಾ ಸಿನಿಮಾ ಉತ್ಸವ ಜುಲೈ 31ರಿಂದ ಆಗಸ್ಟ್ 2ರವರೆಗೆ
    ("eb7849e2-d896-48b3-a102-fa08c6edf632", "0f8ab262-5f01-4ec3-bebc-90f9fc33c744"): (False, "agree"),  # ಕೊಪ್ಪಳ ಬಹದ್ದೂರ್‌ ಬಂಡಿ ಗ್ರಾಮದಲ್ಲಿ ಸಾಂಸ್ಕೃತಿಕ ಸೌರಭ ಕಾರ್ಯಕ್ರಮ
    ("eb7849e2-d896-48b3-a102-fa08c6edf632", "5f1cd43d-d239-407b-9466-517d502722fa"): (False, "agree"),  # ಸಿರುಗುಪ್ಪದಲ್ಲಿ ಶ್ರೀಶೈಲ ಶ್ರೀಗಳಿಂದ ಪ್ರವಚನ, ಇಷ್ಟಲಿಂಗ ಮಹಾಪೂಜೆ
    ("eb7849e2-d896-48b3-a102-fa08c6edf632", "689e0600-c842-4bd1-a53f-a4b9b8707eec"): (False, "agree"),  # ಗಾಂಧಿ ಶಿಲ್ಪ ಬಜಾರ್ ಮೇಳ ಇಂದಿನಿಂದ ಜೆಎಸ್‌ಎಸ್ ಅರ್ಬನ್‌ ಹಾತ್‌ನಲ್ಲಿ
    ("eb7849e2-d896-48b3-a102-fa08c6edf632", "cb74f65b-9841-4c69-bdfa-adc795be95ec"): (False, "agree"),  # ಸ್ಪರ್ಧಾತ್ಮಕ ಪರೀಕ್ಷೆಗಳಿಗೆ ಉಚಿತ ಕಾರ್ಯಾಗಾರ ಆ.7ರಂದು
    ("eb7849e2-d896-48b3-a102-fa08c6edf632", "f34df0f0-b119-457a-93c1-e65fe3a7af02"): (False, "agree"),  # ಸಂಸ್ಕಾರ ಭಾರತಿ ಸಂಸ್ಥೆಯಿಂದ ಐವರಿಗೆ ಗುರುವಂದನೆ ಕಾರ್ಯಕ್ರಮ
    # seed: ಹೊಸಪೇಟೆ| ಖಜಾನೆ ಖಾಲಿ ಆಗಿರುವುದಕ್ಕೆ ಸರ್ಕಾರ ಬರ ಪರಿಹಾರ ನೀಡುತ್ತಿಲ್ಲ:ಆರ್.ಅಶೋಕ
    ("556bd6f1-d422-45e3-aa81-e6a04b08afe7", "42c52ff6-f158-43cd-936e-33b310cdb084"): (False, "agree"),  # Decision on declaring drought by August end, Chief [...]
    ("556bd6f1-d422-45e3-aa81-e6a04b08afe7", "4f1fb469-5dec-4af4-b7e3-88333aafd6b5"): (False, "agree"),  # ಮೈಸೂರು, ಚಾಮರಾಜನಗರ ಜಿಲ್ಲೆಯನ್ನು ಬರಪೀಡಿತ ಎಂದು ಘೋಷಿಸಲು ಒತ್ತಾಯ
    ("556bd6f1-d422-45e3-aa81-e6a04b08afe7", "63ec588f-f31b-475f-90f7-6be53565d611"): (False, "agree"),  # 'ರೈತರ ಬಗ್ಗೆ ಕಾಳಜಿಯಿದ್ದರೆ ನೆರವಿಗೆ ಬರಲಿ' - ಜೆಡಿಎಸ್ ಆಗ್ರಹ
    ("556bd6f1-d422-45e3-aa81-e6a04b08afe7", "7ff823b3-1ec6-4dc5-ac21-15ecf0ad2726"): (False, "agree"),  # ಕೇರಳದಲ್ಲಿ ಮಳೆ ಅವಘಡ: ಮೃತರ ಸಂಖ್ಯೆ 15ಕ್ಕೆ ಏರಿಕೆ
    ("556bd6f1-d422-45e3-aa81-e6a04b08afe7", "90134eeb-7ebc-4237-a96f-e15d822edac6"): (False, "agree"),  # Toxic gases slow rescue ops in South Sikkim tunnel [...]
    ("556bd6f1-d422-45e3-aa81-e6a04b08afe7", "92763a3c-fc95-4028-8670-987a9d875a46"): (False, "agree"),  # Assam flood toll rises: 21 killed in a day; over 5.6 [...]
    ("556bd6f1-d422-45e3-aa81-e6a04b08afe7", "92d06a84-bd82-4484-b439-5a86d45c403f"): (False, "agree"),  # ರೈತರ ವಿವಿಧ ಬೇಡಿಕೆ ಈಡೇರಿಸಲು ಆಗ್ರಹಿಸಿ ಟ್ರ್ಯಾಕ್ಟರ್ ಜಾಥಾ, ಧರಣಿ
    ("556bd6f1-d422-45e3-aa81-e6a04b08afe7", "adb2b7dc-f92b-4087-9d4a-502811066ca4"): (False, "agree"),  # ₹10 ಸಾವಿರ ಕೋಟಿ ಬಿಡುಗಡೆಗೆ ಆಗ್ರಹ, ಬಿಜೆಪಿ ಶಾಸಕ ಸುರೇಶ್‌ಗೌಡ [...]
    ("556bd6f1-d422-45e3-aa81-e6a04b08afe7", "c5424edd-c3d9-4630-a8cb-6e4c32ae1e7a"): (False, "agree"),  # ಕನಕಗಿರಿ ಬರ ಪೀಡಿತ ತಾಲ್ಲೂಕು ಘೋಷಣೆಗೆ ಆಗ್ರಹಿಸಿ ಬಿಜೆಪಿ ಪ್ರತಿಭಟನೆ
    ("556bd6f1-d422-45e3-aa81-e6a04b08afe7", "c9ee0e27-2838-4189-8461-e20143b25f27"): (False, "agree"),  # 8 dead, 8 missing in Kerala as major towns flooded [...]
    # seed: ‘We did not want to give up’: Doctor recalls 30-minute CPR that revived former [...]
    ("8bff4d46-ffd5-44f4-bf71-15fbe0f3c588", "0e1eb5f9-1008-4d6c-bc3f-ced285a6c1fb"): (True, "adj:vijay-said-same:high"),  # ಸಾವಿನ ದವಡೆಯಿಂದ ಮಾಜಿ ಶಾಸಕನ ರಕ್ಷಣೆ: ಸತತ 9 ಬಾರಿ CPR ನೀಡಿ [...]
    ("8bff4d46-ffd5-44f4-bf71-15fbe0f3c588", "be8b2d7a-0ed0-48cb-a1d8-5a07bb935065"): (False, "agree"),  # BJP welcomes Telangana High Court order on HYDRAA [...]
    ("8bff4d46-ffd5-44f4-bf71-15fbe0f3c588", "01eb542f-0116-4b00-bbbd-1691e79ed8f4"): (False, "agree"),  # BRS alleges delay in TIMS Alwal construction; Congress [...]
    ("8bff4d46-ffd5-44f4-bf71-15fbe0f3c588", "0531dbda-0fce-486f-b9df-92c8f453fb07"): (False, "agree"),  # Sexual assault-accused trainee IPS officer found unconscious
    ("8bff4d46-ffd5-44f4-bf71-15fbe0f3c588", "054db755-2e65-4aca-ab75-de4b5bfd45bb"): (False, "agree"),  # BJP slams Telangana govt over 'family register', [...]
    ("8bff4d46-ffd5-44f4-bf71-15fbe0f3c588", "1bcc5bdc-8aae-44ab-8915-06e6e9c7bcc2"): (False, "agree"),  # Telangana committed to addressing NRIs’ concerns: Jupally
    ("8bff4d46-ffd5-44f4-bf71-15fbe0f3c588", "380558f9-59c6-4f3f-98a3-d54cd4286b04"): (False, "agree"),  # Head constable’s swift action saves man’s life in [...]
    ("8bff4d46-ffd5-44f4-bf71-15fbe0f3c588", "7ab1b2aa-6ae0-4a92-9046-069c43999294"): (False, "agree"),  # Sciver-Brunt doesn't 'want to give up bowling just [...]
    ("8bff4d46-ffd5-44f4-bf71-15fbe0f3c588", "92dff880-f4fb-4173-a1e4-0c0a16227d89"): (False, "agree"),  # Former Shivamogga MLA passes away
    ("8bff4d46-ffd5-44f4-bf71-15fbe0f3c588", "9ffd8fcb-51ff-41e7-9ed0-68561de7eeb3"): (False, "agree"),  # 'No excuses if you want to play for India': The [...]
}


def pairs(include_adjudicated: bool = True) -> dict[tuple[str, str], bool]:
    """The scorable pairs. `include_adjudicated=False` scores only the 1,111 both
    labellers agreed on — useful to check a result does not hinge on adjudication."""
    return {k: v for k, (v, prov) in PAIRS.items()
            if include_adjudicated or prov == "agree"}


def positives() -> int:
    return sum(1 for v, _ in PAIRS.values() if v)
