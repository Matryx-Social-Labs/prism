"""Hand-labelled gold clustering for the six largest production events.

Labelled 2026-07-30 by reading all 171 article titles in publication order. The
label is the real-world event a reader would say the article is about, so two
articles share a label iff a reader would expect to find them on one page.

WHY THESE SIX: they are every production event with >=20 members, i.e. the ones
where over-merge is worst. That makes this a REGRESSION SUITE for fusion, not a
representative sample of the corpus. B-cubed recall computed over it is close to
meaningless (almost everything here is over-merged, so recall starts near 1.0);
B-cubed PRECISION, macro purity, and the cluster count are the numbers to watch.
A random-sample set is still needed before anyone claims a headline F1.

THE SCORE OF 0.29 PRECISION IS NOT A SCORE OF THE CURRENT MATCHER. Read this
before using these labels to justify a change.

    tools/score_clustering  (production as STORED)    P=0.2908  purity=0.4842   6 clusters
    tools/scratch --score   (today's find_event)      P=0.8017  purity=0.9223  71 clusters

Same 171 articles, same labels. The difference is that production's rows were
written by code predating the 0.0.79-81 fixes — the embedding script gate, the
article_entities corroboration rule, IDF weighting, entity alias folding. Replayed
through today's matcher those six events become 76, and 110 of the 171 articles
rejoin a story that already exists.

So the over-merge these labels were built to measure is HISTORICAL DAMAGE, not a
live defect, and the fix for it is a re-clustering pass over old rows rather than a
new rule. Today's matcher errs the other way: 71 clusters against 56 real events is
mild FRAGMENTATION. Any change tuned to raise precision here — a tighter window, a
higher similarity floor — pushes the live failure mode further in the direction it
is already wrong. Measure with scratch --score, not score_clustering, before
touching correlation/clustering.py.

Some labels span predicted events on purpose. `courts-police-action` appears in
both event 1 and event 6, `kangana-row` in events 1 and 2, `kharge-shah` in 1 and
2. Those are real FRAGMENTATION — the same story split across clusters — and they
are what gives this set any recall signal at all.

Judgement calls worth knowing about, since a different annotator would differ:
- Distinct legal proceedings are distinct events. The metro-closure plea, the
  internet-shutdown plea and the surveillance plea are separate from the main
  police-action litigation even though all four arise from one protest.
- A roundup that leads on one event is labelled as that event, not as its own
  thing (the nationwide-rain piece leading on the Assam toll is `assam-floods`).
- Opinion and analysis about an event belong to the event.
"""

# article_id -> the real-world event a reader would say it is about.
#
# Keyed by ARTICLE ID, not by position. The first version of this file indexed
# labels by publication order within a predicted event, which meant the moment a
# repair moved articles between events every index pointed at the wrong article —
# and that happened the first time a repair ran (0.0.81.10). Ground truth about an
# article belongs to the article; nothing that re-clusters can invalidate it.
GOLD: dict[str, str] = {
    "2c8b6e9c-11ca-4c9f-80a6-5e19b6ab2560": "aisa-activists",  # Besides the CJP: Neha and the AISA activists who fasted, m
    "9eb82983-f1eb-4b42-bacf-76030ebb518c": "ambedkar-photo-ripon",  # Ambedkar’s photo should be displayed prominently at Ripon 
    "19abae8a-3f0b-441e-a77b-a3ca1c840f02": "anti-leak-bill",  # ‘We want all parties’: Kiren Rijiju urges participation in
    "970f2c37-4520-4e59-9d38-f87e880dc7d0": "anti-leak-bill",  # Parliament News LIVE Updates: संसद में आज परीक्षा में सुधा
    "f1576063-f6ec-4dd1-adbe-12754a6b7988": "anti-leak-bill",  # रिजिजू ने दिलाई इमरजेंसी की याद, अखिलेश बोले- फिर होगा परि
    "b6464c8c-f903-4bc9-ade2-053edc7a2843": "anti-leak-bill",  # Lok Sabha debates anti-paper leak Bill, Opposition terms i
    "bc931392-ae3f-4754-a6cd-5220f6619005": "anti-leak-bill",  # Young Turks vs Women MPs: Lok Sabha debates stricter anti-
    "ebe30fe9-b23d-4418-9067-a654af663500": "anti-leak-bill",  # Parliament monsoon session highlights: Parliament clears k
    "f0e77f00-8a19-4f3a-98d5-b3a36a1a36ed": "anti-leak-bill",  # एंटी पेपर लीक बिल राज्यसभा में भी पास, अब कानून बनने से एक
    "00a48423-3c74-4a1d-8e98-3dde9be69a6c": "assam-floods",  # 21 killed in a day as flood situation worsens in Assam; 5.
    "492d1666-9bc1-42db-8ed4-0890db18d9f9": "assam-floods",  # Assam flood toll rises: 21 killed in a day; over 5.6 lakh 
    "52926f71-2ffb-4dbf-838c-61771faaea22": "assam-floods",  # 21 dead in a day’s deluge in Assam; total flood toll 31
    "df3e5bb9-85a0-4c29-892d-08dbb380bb0c": "assam-floods",  # Assam flood toll rises to 31; over 5.6 lakh people maroone
    "29f7dbf2-d352-48e4-837f-4030543248f3": "assam-floods",  # Assam floods claim 21 lives in 24 hours, toll rises to 31;
    "f3d4e77b-ed3b-4367-be0e-361944f0bcc5": "assam-floods",  # Assam flood: 31 dead so far, 5.65 lakh affected, govt anno
    "39e6336e-a89f-4393-9868-0d245cbb1f58": "assam-floods",  # Assam floods worsen: 50 dead so far, over 100 reported mis
    "c412c9b4-bac9-4638-b755-4f017aea07d6": "assam-floods",  # 10 more deaths raise Assam flood toll to 41
    "45223b37-fead-4f7c-86b8-ea5023f3dd11": "assam-floods",  # Assam flood situation remains grim as 41 killed so far, ov
    "ff46165c-c00f-465e-86cb-6a703bf9768b": "assam-floods",  # असम में बाढ़ का प्रचंड रूप, एक दिन में 10 लोगों की मौत
    "b1cc19cd-a80c-43ca-8875-1e6ef96eb035": "assam-floods",  # Assam chief secy reviews flood situation, asks all depts t
    "74d79bd8-2857-42be-8661-17b9495eabd4": "assam-floods",  # Assam floods: 41 dead, over 6.5 lakh affected as situation
    "1909b62c-5479-44a3-979e-e65893bdf37f": "assam-floods",  # देशभर में आफत की बारिश: असम में बाढ़ से 41 की मौत,  महाराष
    "45d7ee5d-fd1f-4a78-9a49-6ec6d0f890b3": "assam-floods",  # Some die out of ‘flood curiosity’, State Disaster Manageme
    "4860f490-99f2-44c4-8d29-970e0fe79b2d": "assam-floods",  # Assam flood situation improves even as toll rises to 68 wi
    "977039b8-645f-4c26-87b4-cf8eae6a3630": "assam-floods",  # What is happening in Assam? Floods batter villages, over 4
    "10872948-66af-436a-b4b6-36728ed1fca7": "assam-floods",  # Centre-State government jointly working to provide relief 
    "739bc039-2f5b-4f50-82a7-229ceed8acef": "assam-floods",  # IMD update: Heavy rain expected in Arunachal, Nagaland as 
    "5a25fafa-8686-4067-aa24-03d8f30a596d": "assam-floods",  # Assam floods: Death toll climbs to 80, 2 lakh remain affec
    "bac52c71-a942-4dff-b1ce-45152621f877": "bams-paper-leak",  # नीट के बाद अब गुजरात में BAMS पेपर लीक?: AAP नेता संजय सिं
    "0b386c2a-6ab7-411f-b671-ffe33299ffcd": "bihar-cop-ak47",  # BJP vs Opposition after Bihar cop uses AK-47 in student pr
    "fee582b8-0bd0-4697-81e2-f2b1e8de797f": "black-day-protest",  # Opposition MPs stage 'Black Day' protest over ‘police brut
    "81025a65-d8cf-4987-ad17-f11e784d95b3": "cauvery-cwrc-order",  # A gamble on the Cauvery issue
    "fca05e1c-544a-4752-a58e-5e1467c621e4": "cauvery-cwrc-order",  # A gamble on the Cauvery issue
    "1977b6bc-0a36-4ec0-a65f-befd05e6d046": "cauvery-cwrc-order",  # Cauvery Water Regulation Committee orders Karnataka to rel
    "1dd0fe82-f6a0-4a5d-b420-161115bc4e79": "cauvery-cwrc-order",  # Cauvery Water Regulation Committee orders Karnataka to rel
    "22a61d7b-1493-4ada-bf4d-fb00fabfdc33": "cauvery-cwrc-order",  # Cauvery Water Regulation Committee orders Karnataka to rel
    "cd255b7c-c90d-498f-9457-e1dbe4fb8eb1": "cauvery-cwrc-order",  # Cauvery: BJP warns against water release to ‘appease’ alli
    "b06c50d0-83c9-4895-9b90-b4a7ab8bfde4": "cauvery-cwrc-order",  # Cauvery: BJP warns against water release to ‘appease’ alli
    "91e2b6bc-6ad7-4d50-817a-4935660e72a9": "cauvery-cwrc-order",  # Cauvery: BJP warns against water release to ‘appease’ alli
    "01c0be02-b03e-4383-b284-141bf8adc4f8": "cauvery-cwrc-order",  # Water release based on CWMA instructions, says Minister Ya
    "693b6556-0678-4ad0-a43b-cc429dd97287": "cauvery-cwrc-order",  # Water release based on CWMA instructions, says Minister Ya
    "8ec2eac5-fd69-437e-ae67-84191ded70dc": "cauvery-cwrc-order",  # Karnataka to appeal against CWRC order to release Cauvery 
    "5110751f-cd31-45a6-b5e3-8b847ea3a4cb": "cauvery-cwrc-order",  # Karnataka to appeal against CWRC order to release Cauvery 
    "0ab69ba4-1a29-4c32-bfbd-c20733d2ac89": "cauvery-protests",  # Cauvery: Protests continue, screening of Vijay’s film stal
    "4b335b4d-a4d8-40e6-b1b1-802a99ae8541": "cauvery-protests",  # Cauvery: Protests continue, screening of Vijay’s film stal
    "789ec148-597d-4371-97fe-f1183649595d": "cauvery-protests",  # Karnataka to see Statewide protests Friday over Cauvery re
    "3f3ea69a-06fd-4cc7-be14-2adee1c836a4": "chalo-lok-bhavan",  # Student bodies to hold ‘Chalo Lok Bhavan’ protest on July 
    "22eda1a1-b3f2-4a1a-8a88-34b738789b87": "chalo-lok-bhavan",  # Student bodies to hold ‘Chalo Lok Bhavan’ protest on July 
    "9c269548-a89b-4eeb-a99d-b1dbbe090f97": "channi-faridkot-rally",  # Charanjit Singh Channi Faridkot rally: Former Punjab CM le
    "9000c753-afcf-409e-ac1b-f96102fadf9e": "cjp-fir-withdrawal",  # CJP flags arrests of protesters in Assam, Bengal, Bihar; s
    "831aa885-b941-43a9-8e4f-99f939537ad9": "cjp-fir-withdrawal",  # 'Will be forced to protest again': CJP warns govt, asks it
    "26b1085c-1480-4830-9572-054a9241a72c": "cjp-fir-withdrawal",  # 'Govt breaching deal ... will protest again': CJP gives Ce
    "2f7947c6-26ea-47ac-9f48-0e63b6007dc7": "cjp-fir-withdrawal",  # CJP to protest again? Ashutosh Ranka warns of sit-in if go
    "3f481bcd-e526-467e-9700-85e418ae4a13": "cjp-fir-withdrawal",  # ಎಫ್‌ಐಆರ್ ಹಿಂಪಡೆಯದಿದ್ದರೆ ಮತ್ತೆ ಪ್ರತಿಭಟನೆ: ಸಿಜೆಪಿ ಎಚ್ಚರಿಕೆ
    "91be42b4-7490-422c-b2b4-1c02bfcdb5c7": "cjp-fir-withdrawal",  # CJP flags detention of protestors in States, asks Centre t
    "eb1ec850-27c6-42b6-9528-4868e24e044e": "cjp-fir-withdrawal",  # Agreement being breached, CJP tells govt, threatens to res
    "0020f876-2d04-464c-803e-7c7b39255244": "cjp-fir-withdrawal",  # 'No protester left behind': CJP claims FIR withdrawals in 
    "f20d695a-b3df-41d7-817c-3d73b1157517": "cjp-fir-withdrawal",  # Govt must stop targeting, witch-hunting students: CJP warn
    "bc871d16-4a31-47c9-a210-67f98e685bcb": "cjp-fir-withdrawal",  # Govt must stop targeting, witch-hunting students: CJP warn
    "c1be2b91-6ec5-47de-b4c8-d3c55b74d4b3": "cjp-govt-talks",  # After CJP's Parliament march, govt opens talks, seeks end 
    "52815f3b-5583-497d-986d-566fc0f85d39": "cjp-govt-talks",  # Govt ready to discuss NEET paper leak; CJP won't go to 'an
    "6d9b776d-535d-4f3d-b8aa-d09343c29517": "cjp-govt-talks",  # 'What kept you waiting?': Annamalai questions BJP, Centre 
    "1c200d18-4292-40a0-9520-987184480774": "cjp-govt-talks",  # कुर्सियों से सोफे तक... कॉन्स्टिट्यूशन क्लब की दो बैठकों स
    "b5cc963d-31fa-4b37-a0d1-5ec05b803a5c": "cjp-legal-aid",  # Rs 1cr in aid, legal website: How CJP plans to fight cases
    "920200fa-fef0-4204-8dfc-fd28d891c09e": "cjp-protest-day1",  # Chaos on Parliament streets amid CJP protest echoes in Hou
    "9ce94000-17fc-473a-a7b7-7a00e61b3a26": "cjp-protest-day1",  # 'Police have been absolutely brutal': Capital turns battle
    "e71cb58b-4999-4c57-88ba-8add3d189342": "cjp-protest-day1",  # Congress, CJP protests LIVE: ‘Owe our students more than o
    "cbfe30cd-cf9a-40d4-9110-5de11ea00b47": "cjp-protest-day1",  # ‘This is utterly disgraceful’: Shashi Tharoor slams police
    "dae8bd7d-79f5-4b21-bcd7-36bdab57f177": "cjp-protest-ongoing",  # CJP protest LIVE: CJP claims police parked ‘damaged car’ o
    "ea06ce6f-284e-41a3-8d32-4bec9f8b2fd7": "cjp-protest-ongoing",  # CJP Delhi protest: Students clash with Police as calls for
    "d0d5c70e-400e-4621-9c71-1ee0f62fdec4": "cjp-saakshi",  # All about CJP's 'Saakshi' platform to help collect proofs 
    "4c752d01-9f13-4e8a-abad-134d64270726": "cong-dharna",  # Police forcibly remove Rahul Gandhi, others from Cong-led 
    "3499533d-b5c2-4e0e-9cbf-997374b08eeb": "courts-internet-shutdown",  # Plea against internet shutdown around Jantar Mantar withdr
    "83874086-6449-4c2c-803d-847f79c622ad": "courts-metro-closure",  # SC may hear plea on closure of metro stations if authoriti
    "e5cf2dc0-f6d7-4ac8-886d-e9001dd79bc9": "courts-police-action",  # ‘Don’t waste our time’: CJI Kant declines to take cognisan
    "5b010e28-f729-4210-93ba-6122a4eaaa3f": "courts-police-action",  # ‘Don’t waste our time’: CJI declines urgent listing of pol
    "5e2afe21-bc39-4151-b4f3-509ad2da7a3a": "courts-police-action",  # 'Mere agitation can't justify lathi-charge': SC on July 20
    "a7139499-853b-469d-b052-2d3066e02fb6": "courts-police-action",  # ನೀಟ್ ಪ್ರತಿಭಟನೆ, ಬಂಧಿತ 18 ವರ್ಷದೊಳಗಿನ ವಿದ್ಯಾರ್ಥಿಗಳ ಬಿಡುಗಡೆಗೊ
    "36ac9363-813e-4f41-b473-5afb2655c5d5": "courts-police-action",  # 'Don't waste our time': Supreme Court refuses urgent heari
    "f74df04c-a577-4050-a260-25175594c9c7": "courts-police-action",  # 'Preserve CCTV': Delhi HC on plea alleging police brutalit
    "c1fd6ad3-fed2-4361-9958-bc1e34068e74": "courts-police-action",  # Preserve CCTV footage, videography of police action: HC to
    "52f5af0f-00b3-4a0e-a458-480b61f8f407": "courts-police-action",  # Delhi HC says Jantar Mantar incident not ‘isolated’, issue
    "abb983b5-5619-434a-9a6b-8fbc458c82cb": "courts-police-action",  # HC issues notices in plea seeking SIT probe into police ex
    "b6309163-7cab-4394-8909-825c290a9d48": "courts-police-action",  # Right to peaceful protest guaranteed, agitation cannot jus
    "96123a86-e30c-4948-8622-829b147a60a9": "courts-police-action",  # Delhi protest crackdown: Supreme Court says right to peace
    "4bd7e9da-78fb-4953-b934-5992cfd16dd1": "courts-police-action",  # NEET protest: Merely because there is agitation, there can
    "357238ee-dd13-43bb-9bad-6bef27f32521": "courts-police-action",  # 'Whosoever committed excesses must be taken to task': SC o
    "af8b90f0-a143-417e-a666-ffbcc6957111": "courts-police-action",  # NEET protests: SC says SIT may be set up to probe police e
    "3d07b4c3-17ae-4ad8-841e-9042224a434c": "courts-police-action",  # NEET protests: SC says SIT may be set up to probe police e
    "325dae37-b44b-4ba7-b51b-2dc550faaa80": "courts-police-action",  # NEET protests: SC says SIT may be set up to probe police e
    "3f20d296-1fe6-436a-9d0b-0c03d60c8aff": "courts-police-action",  # SC bars coercive action against student protesters; direct
    "030c3fe6-9210-4902-bcb7-930cc228b087": "courts-police-action",  # Supreme Court orders release of protesters below 18 with n
    "855de2b4-5a1c-4608-8f23-47f3fc184408": "courts-police-action",  # NEET protests: SC bars coercive action against those with 
    "37d61028-babd-45c1-81b1-5d461f7370a9": "courts-police-action",  # Delhi high court says cop’s image can't be tarnished due t
    "b493c97c-f554-4fd6-8190-ff89720cdc23": "courts-surveillance",  # ‘Things have cooled down’: HC junks plea alleging surveill
    "512020d8-c70a-4a2b-bfea-d29c82052769": "courts-surveillance",  # Delhi HC to hear plea against ‘police surveillance’ of Jan
    "80fe0c67-07ee-4dd6-86c8-0526982a044a": "d-raja-communist",  # D. Raja calls for strengthening Communist movement in Indi
    "95d006b2-7076-4839-a125-2c003c842483": "d-raja-communist",  # D. Raja calls for strengthening Communist movement in Indi
    "7f04d11f-6554-43b0-a333-4d9485fdc066": "dmk-neet-abolition",  # DMK president MK Stalin calls for scrapping of NEET examin
    "48d75c12-e09f-410d-a3ae-e136fcd28c71": "dmk-neet-abolition",  # DMK demands abolition of NEET amid student protests
    "2276254a-6f60-4da0-8a47-b9dd6f2c1726": "dmk-neet-abolition",  # Protests are ‘wake-up call’: MK Stalin accuses Centre, dem
    "588cd804-bb7f-46b1-9908-91cde609cffa": "dmk-neet-abolition",  # NEET is creating an atmosphere of fear and anxiety in medi
    "898db7c9-846d-4727-aac3-449ee45a42d7": "dmk-thanjavur-protest",  # DMK to stage protest in Thanjavur on August 3 over Cauvery
    "111883b1-30bc-453e-8553-b5acf3f7b0b9": "e20-town-hall",  # 'All are invited': Kejriwal announces 'National Town Hall 
    "22e9feab-1051-4ff4-882b-b2a48210d7ca": "e20-town-hall",  # AAP to hold ‘National Town Hall Against E20’ on August 1
    "91014993-b6c1-4a91-b505-2122215c925c": "evm-kolathur",  # EVMs used in Kolathur constituency being verified after M.
    "3738f3b8-656c-4a11-b654-c512095e9142": "greta-backs-protest",  # Greta Thunberg says CJP protest 'given us hope', backs Ind
    "430c3a9d-b9e2-4ba4-9c35-8dac741fc230": "gujarat-rainfall",  # Gujarat on high alert as extremely heavy rainfall likely o
    "3e9d65c1-00d1-4ea9-9c3f-d29447734ef9": "hyderabad-solidarity",  # Hyderabad protests back Wangchuk, slam Delhi police crackd
    "e0c52aeb-3c30-4c27-b0ed-4a551ff2a167": "jantar-trafalgar",  # Jantar Mantar in Trafalgar Square
    "bbc33064-998f-43ca-bf7b-10d2396a107a": "junaid-video",  # 'आंखों पर पट्टी बांधकर पूरी रात रखा', जुनैद का वीडियो वायर
    "e3187eeb-363f-4731-92ef-688a702c4b57": "kangana-row",  # 'Why should PM resign? He is the most popular leader in th
    "c7de0b94-c466-4f40-b99d-aa5c6124cd0f": "kangana-row",  # 'Ewwww, who is birthing & raising them?' Kangana calls Gen
    "c2f90ad0-efb2-4c74-b1d0-f246c4f037c0": "kangana-row",  # Kangana Ranaut slams Gen Z CJP protestors for ‘puke induci
    "adbbb1e9-11c7-4aa7-b715-5966c14a5fca": "kangana-row",  # ‘ಇಂಥ ಅಸಹ್ಯ ಎಲ್ಲೂ ನೋಡಿಲ್ಲ’: ಜೆನ್ ಜಿ ಪ್ರತಿಭಟನೆ ವಿರುದ್ಧ ಕಂಗನಾ
    "42e4cda4-22d0-444e-85af-6545e5c5e34f": "kangana-row",  # Cockroaches spreading their filth, who is birthing them?: 
    "f49f90fd-5543-4cce-a847-2341b0a60a02": "kangana-row",  # 'Even her own party doesn't take her seriously, why should
    "ea9def72-0f96-4ef2-bf0a-f637966b5ed5": "kangana-row",  # 'Completely unacceptable': Kangana Ranaut on 'filthy abuse
    "20a585cb-5fbb-44cd-9561-8dbdd59c74c3": "kangana-row",  # 'बोलने का हक सिर्फ तुम्हें नहीं', Gen Z प्रोटेस्ट पर कंगना
    "7c913d53-1846-42be-bc1a-181c05dc5f56": "kangana-row",  # 'कंगना मुझे पसंद थीं, लेकिन उनसे ऐसी उम्मीद नहीं', एक्स्टे
    "5f549732-4cae-4bdb-9af5-58845fe4eeae": "kangana-row",  # 'इनको समझाइए, बेटियों का चरित्र...', कंगना का नाम लिए बिना
    "fc58f44c-b1a8-4fa4-a90d-f70a4daf0edb": "kargil-vijay-diwas",  # Governor Arlekar, party leaders pay tribute to soldiers on
    "c337fc43-a91f-45bd-8747-52d395e68617": "karnataka-drought",  # Ashok slams State govt. over its failure to respond to dro
    "8ef7c00e-bd31-4771-a10a-84dbcc0a880b": "karnataka-proposals",  # Karnataka Chief Minister presents 13 pending proposals,  a
    "b7945dc2-3148-4cc8-b481-164704c52efa": "karnataka-proposals",  # Karnataka Chief Minister presents 13 pending proposals,  a
    "07fab02c-d87b-444d-9945-4ee212e85440": "kharge-shah",  # Kharge’s ‘will drag you out’ remark at Shah sparks fresh f
    "da303cd0-2214-49ea-90ab-3106c2b90ac6": "kharge-shah",  # ‘Has someone stitched your mouth shut?’: Kharge questions 
    "321970bb-1f31-4b60-8e76-34194d41d710": "lamba-slap-video",  # CJP demands ADCP Lamba's suspension after viral slap video
    "18b06660-baaa-46eb-aa97-365c708860bf": "mgu-poster-row",  # Cockroach imagery on conference poster ignites controversy
    "53dfd695-6217-448a-98b5-3a40b41333dd": "mgu-poster-row",  # Cockroach imagery on conference poster ignites controversy
    "cf8094bb-0659-4aca-bfb8-e8789d903283": "mohandas-remark",  # Hindutva ideologue T.G. Mohandas sparks row by stating he 
    "04b599d3-c305-4987-a604-0be21c60a022": "mohandas-remark",  # Hindutva ideologue T.G. Mohandas sparks row by stating he 
    "4001e3c8-3e81-433d-9576-6e71e98ff774": "mohandas-remark",  # 'मैं गोली चलाने का आदेश दे देता', छात्र आंदोलन पर RSS समर्
    "48af3025-6c7f-4ccc-aca8-6fa89fac3484": "mohandas-remark",  # RSS distances itself from Hindutva ideologue T. G Mohandas
    "34b77fbb-a445-4b10-8fa5-e74c3b6bc43d": "mohandas-remark",  # RSS distances itself from Hindutva ideologue T. G Mohandas
    "831bb901-5b0b-4245-9ba2-d1be36a2854b": "mohandas-remark",  # Jantar Mantar protest remarks: DYFI takes out march to T.G
    "e976c386-42ce-4f11-a08e-6a550f12fffe": "mohandas-remark",  # Jantar Mantar protest remarks: DYFI takes out march to T.G
    "df91dbb1-3630-4ccc-9767-35cca29028e4": "neet-cases-closed",  # Delhi govt closes NEET protest cases with caveat: No prote
    "54767eee-d208-47d7-ab88-3d3059bc01e0": "opinion-democracy",  # बधाई हो, हमारे पास फंक्शनिंग डेमोक्रेसी है!
    "c560749e-24e1-4034-9e7f-bae28eb07a32": "opposition-rift",  # अखिलेश और कांग्रेस के वेणुगोपाल में तीखी बहस... NEET आंदोल
    "d7705f3d-9213-4949-a72c-590c62a29c4e": "parliament-adjourn",  # Parliament monsoon session: Lok Sabha, Rajya Sabha adjourn
    "b232e908-30db-442f-929b-b9f185757a7c": "parliament-adjourn",  # Parliament monsoon session LIVE: Lok, Rajya Sabha adjourne
    "b1640027-21c7-4d1c-bd8e-ac643c4d681f": "parliament-adjourn",  # धर्मेंद्र प्रधान का स्वागत, खड़गे का गुस्सा... संसद में दि
    "3ac5cca0-fd27-4674-96d7-3b918de56bef": "police-criminal-ident",  # CJP Protest: पुलिस ने 2,873 आपराधिक पृष्ठभूमि वाले लोगों क
    "8ce58a14-91b9-4439-9f9f-fa631e2cec7a": "pradhan-resignation",  # ‘Dharmendra Pradhan’s resignation is a milestone, but not 
    "eefd41a6-cd67-43f6-9c4a-2d7a5d21ce57": "pradhan-welcome",  # 'Dharmendra Pradhan zindabad': Ex-Union education minister
    "b07d178e-106b-43a8-84d3-4866d50281b3": "pradhan-welcome",  # BJP MPs greet Pradhan with ‘Zindabad’ slogan, Opposition h
    "e9c7b911-7f97-4c2f-b3ca-e2ffcda0089b": "priyanka-rijiju-spat",  # ಪ್ರಲ್ಹಾದ್ ಜೋಶಿ ಕುರಿತು ಸದನದಲ್ಲಿ ಪ್ರಿಯಾಂಕಾ ಗಾಂಧಿ ವಿವಾದಾತ್ಮಕ 
    "54e4c308-d950-4f67-aa23-888cc1c13b85": "priyanka-rijiju-spat",  # ‘Character assassination’: Drama in Parliament as Priyanka
    "574c323c-68d1-45ff-a645-2d4646610dd5": "punjab-paper-leak",  # Punjab CM refutes allegations of paper leak under AAP gove
    "b6723e80-8ce9-4e05-999c-3c6128c55ded": "punjab-paper-leak",  # Has CJP demanded Punjab education minister's resignation a
    "a10d0b9a-a0f2-46da-a8bd-2e4c61cfab8b": "punjab-paper-leak",  # Amid allegations of paper leaks, Punjab edu minister meets
    "9cc00ded-30c6-40ba-85f8-bdcb552bcc6c": "punjab-paper-leak",  # स्वाति मालीवाल का केजरीवाल पर गंभीर आरोप: बोलीं- पंजाब में
    "e3ac4ae1-95ae-45b2-b530-224f856eecc1": "rahul-meets-irfan",  # Rahul Gandhi Meets Mohammad Irfan: राहुल ने की प्रदर्शनकार
    "6cb80b91-a5b4-49cb-b1aa-9e9770bb9c6f": "rahul-meets-irfan",  # राहुल गांधी ने इरफान से की मुलाकात, जंतर-मंतर प्रोटेस्ट के
    "889801c7-642a-4995-97fd-d5a128e0dc5c": "rahul-meets-irfan",  # जंतर-मंतर के स्टार से मिले Rahul Gandhi!
    "19238d48-b51b-4b88-a494-a2357a9cdd3c": "rahul-meets-irfan",  # अनपढ़ हैं, मोबाइल पर टाइप भी नहीं कर पाते लेकिन सेलेब्रिटी
    "475bf480-22a9-41f9-a82e-7e9e3c78c886": "rahul-privilege-notice",  # Rahul Gandhi under fire: Anurag Thakur moves privilege not
    "3371c70f-c89c-41f3-b9ec-f2a5032814ea": "rahul-privilege-notice",  # ರಾಹುಲ್‌ ಗಾಂಧಿ ವಿರುದ್ಧ ಅಸಂಸದೀಯ ಪದಬಳಕೆ ಆರೋಪ: ಕ್ಷಮೆಗೆ ಪಟ್ಟು, 
    "7c7065bf-a0b8-4c4d-9ece-a5976277756c": "sikkim-tunnel",  # Sikkim NHPC tunnel disaster: Search for Malayali geologist
    "f153e87e-e0c7-416b-a934-3934e78f7548": "sikkim-tunnel",  # Sikkim NHPC tunnel disaster: Search for Malayali geologist
    "c05e6910-64f1-4c4f-9f31-d24de4ab1ce5": "tn-medical-seats",  # Tamil Nadu government should explain surrender of 151 supe
    "33a53510-ae94-49f0-853e-db5eae424174": "vanni-arasu-slogan",  # Minister Vanni Arasu mistook NCC slogan ‘Jai Hind, Sriman’
    "26a7adec-74e0-4a85-8ac7-45768b1d8533": "vanni-arasu-slogan",  # T.N. Minister Vanni Arasu mistook NCC slogan ‘Jai Hind, Sr
    "ce54cb3d-c056-4708-b4d4-8be28b9d20bc": "vijay-karnataka-visit",  # Farmers body urge CM Vijay to 'reject' Karnataka CM's invi
    "bdcf52e4-7687-49b7-ba69-2ce1f7ec963b": "vijay-karnataka-visit",  # Karnataka getting ready for Tamil Nadu CM Vijay’s possible
    "2b4eddf9-3bd9-4363-b893-b79dfaa1a6a9": "vijay-karnataka-visit",  # Karnataka getting ready for Tamil Nadu CM Vijay’s possible
    "c9c7874d-4960-404d-9d0d-3f1ae5cd46c4": "vijay-karnataka-visit",  # Farmers demand reciprocal visit by Karnataka CM to delta d
    "955518aa-86ce-4164-b161-b601aa29e74c": "wangchuk-hospital",  # Jantar Mantar CJP Protest LIVE: Nadda, Jitendra Singh visi
    "9983a851-2037-4f81-a06c-da83f0c31898": "wangchuk-hospital",  # Jantar Mantar protest LIVE: Hundreds order food for protes
    "720a55cb-6785-4475-9c76-cf61c3222876": "wangchuk-hospital",  # Promise no legal action against protesters, will end hunge
}


def gold_event_count() -> int:
    """Distinct real-world events across the labelled set."""
    return len(set(GOLD.values()))


def labelled_article_count() -> int:
    return len(GOLD)
