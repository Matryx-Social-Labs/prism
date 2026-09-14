"""Hand-labelled CLAIM attribution, adjudicated. Gates plan step 5b.

59 extractor claims sampled uniformly (batch Gtkxo4O0NxZm, setseed 0.31). Question
per claim: does the ARTICLE credit these exact words to this speaker? Not whether
the claim is true. Two labellers; kappa 0.32 on the 47 both answered definitely.

WHY THE DISAGREEMENT WAS SYSTEMATIC, NOT NOISE. One labeller skipped 9 and marked
3 unsure; 8 of the 9 skips were Tamil, Hindi or Kannada articles — a language
barrier, not carelessness, but it deflates that labeller's yes-rate (80.9% vs
95.7%). All 7 definite disagreements resolved YES on full context: in each the
speaker is named with "said" 60-220 characters before the quote and the quote is
followed by "he said"/"he added" with no one else introduced between.

TWO PAIRS BOTH LABELLERS GOT WRONG THE SAME WAY, which agreement cannot catch:
  #2   "Das said contesting elections was not currently on the agenda" — correctly
       attributed INDIRECT speech. Both said NO, almost certainly because there are
       no quotation marks. Attribution is right. Whether reported speech should
       DISPLAY as a claim is a product decision, not an attribution error.
  #11  "Shivam, another supporter from Faridabad, ... \"We have brought food\" he told
       HT." Unambiguous. Both said NO; no reason visible in the text.
The one confirmed NO (#38) is narration of Unit 42's research findings, not words
attributed to Unit 42.

RESULT: attribution precision 58/59 = 0.983 (Wilson 95% CI ~[0.91, 1.00]). The
>= 0.95 gate passes. Deferring to both labellers on #2/#11 gives 56/59 = 0.949,
a coin flip against the gate — the entire swing is those two items.
"""

from __future__ import annotations

BATCH = "Gtkxo4O0NxZm"
ADJUDICATED_ON = "2026-09-14"

# position -> (article_id, speaker, quote_text, attributed, provenance)
CLAIMS: dict[int, tuple[str, str, str, bool, str]] = {
    0: ("ef0c3103-1565-4633-9892-763337ed5c01", "M. Vijay Bhaskar", "A preliminary report has already been submitted to the government and a final [...]", True, "agree"),
    1: ("6ecc2dca-82d3-4e77-9006-96aa41335323", "Anita Dipke", "We were receiving marriage proposals for Abhijeet even before the CJP protest [...]", True, "adj:high"),
    2: ("6ecc2dca-82d3-4e77-9006-96aa41335323", "Saurav Das", "contesting elections was not currently on the organisation's agenda", True, "adj:medium"),
    3: ("20e7f283-89a2-49b7-a50a-d25137b58e4b", "B.C. Janardhan Reddy", "Have you forgotten how people rejected you in the last election? Let us see who [...]", True, "agree"),
    4: ("be510bd7-9134-44ca-8af6-db7c66ad09fb", "Tanvi Kanchan", "Instead of tracking the lock-in expiry and off-load of shares, investors should [...]", True, "agree"),
    5: ("9378ce08-1d63-43c7-8fde-30c6cc5b18fb", "Amit Bhatt", "The quarterly data will speak more. However, given the policy offers in terms of [...]", True, "agree"),
    6: ("9378ce08-1d63-43c7-8fde-30c6cc5b18fb", "Amit Bhatt", "Sustained growth will depend not only on financial incentives, but also on [...]", True, "agree"),
    7: ("f7d357df-fdca-4042-ab23-d8a86481b1f1", "Irfan Razack", "This project marks another significant milestone in the company's continued [...]", True, "adj:high"),
    8: ("6e18687d-236b-4ca5-9e2c-2dee1ea1e43f", "Donald Trump", "மிகவும் நட்புறவான பேச்சுவார்த்தைகள் நடந்து வருகின்றன", True, "tejas-only(skip)"),
    9: ("6e18687d-236b-4ca5-9e2c-2dee1ea1e43f", "Anna Kelly", "அதிபர் டிரம்பின் அனைத்து மூலோபாய இலக்குகளையும் மற்றும் அதற்கும் அப்பாற்பட்ட [...]", True, "tejas-only(skip)"),
    10: ("63a14418-e162-46ef-a8ad-6a5b1fc4ceda", "Usman", "We saw videos of young girls being beaten up. People from our neighborhood asked [...]", True, "adj:high"),
    11: ("63a14418-e162-46ef-a8ad-6a5b1fc4ceda", "Shivam", "We have brought food with us. We were protesting peacefully yesterday. The way the [...]", True, "adj:high"),
    12: ("52b3210b-1990-4a08-84d3-a87635798cc2", "R.V.Karnan", "Some voters having another vote elsewhere might have made a choice to retain that, [...]", True, "agree"),
    13: ("eedbd416-5304-4d7f-8633-2ee8f5625f4d", "Babar Azam", "वह तभी कप्तानी संभालेंगे, जब उन्हें टेस्ट के साथ-साथ वनडे और टी20 तीनों फॉर्मेट की [...]", True, "tejas-only(skip)"),
    14: ("e8206831-8b90-46bc-9bf7-9cbbe41cba0b", "Devdatt Kamat", "There are large-scale reports that ultimately the money has not reached the Trust. [...]", True, "adj:high"),
    15: ("2146e3d2-c998-4168-8893-75efd74a27a6", "Jose Pradeep", "Late-night hospitality services are particularly important for destination [...]", True, "adj:high"),
    16: ("2146e3d2-c998-4168-8893-75efd74a27a6", "Jose Pradeep", "New Year celebrations actually begin at midnight. We request the government to [...]", True, "adj:high"),
    17: ("ad3841dd-05bf-4110-a88c-a20018e507b9", "Nainar Nagenthran", "whenever the Congress assumed power in Karnataka, Cauvery water stopped flowing [...]", True, "agree"),
    18: ("cce4f202-b8dc-4527-9042-6d8b9fb85929", "Srikanth Lakshmanan", "Triple X - expands to triple extortion - but motivations remain unclear", True, "agree"),
    19: ("cce4f202-b8dc-4527-9042-6d8b9fb85929", "Bank of Baroda", "The incident involved compromise of an employee's e-mail account, resulting in [...]", True, "agree"),
    20: ("cce4f202-b8dc-4527-9042-6d8b9fb85929", "Srikanth Lakshmanan", "Email access compromise cannot lead to exfiltration of multi hundred gigabytes of data.", True, "agree"),
    21: ("3cb213c8-e9b4-42e2-bfa6-a560fecdcb2f", "Ananda Mastiholi", "ವ್ಯಸನವೆಂದರೆ ಕೇವಲ ಮಧ್ಯಪಾನ, ಧೂಮಪಾನ ಹಾಗೂ ಗುಟ್ಕಾ ಸೇವಿಸುವುದು ಅಷ್ಟೇ ಅಲ್ಲ. ಕೆಟ್ಟ [...]", True, "tejas-only(skip)"),
    22: ("c46ce442-e9a9-4d0d-a2b0-7238b60fe23f", "Archana Dhawan Bajaj", "Semaglutide should only be used for defined medical indications such as diabetes, [...]", True, "agree"),
    23: ("c46ce442-e9a9-4d0d-a2b0-7238b60fe23f", "Namit Joshi", "Indian pharmaceutical manufacturers adhere strictly to local and international [...]", True, "agree"),
    24: ("19b013c3-c634-48ab-9ab0-a196a226ed84", "Gyanedra Pratap Singh", "As the Director General of the CRPF, I want to assure each one of you that whether [...]", True, "agree"),
    25: ("19b013c3-c634-48ab-9ab0-a196a226ed84", "Jitendra Singh", "only tear gas was used against protestors, adding that no bullets were fired", True, "agree"),
    26: ("60172901-76c6-4727-a67c-3c5b724143b2", "Sanjay Karol", "If a woman is in a domestic setup even prior to marriage, which obviously, to a [...]", True, "tejas-only(unsure)"),
    27: ("c75ebf5b-b19e-40ca-a146-0e8675300196", "Pawan Kumar Sharma", "विश्वविद्यालय जीरो टॉलरेंस नीति के तहत काम कर रहा है और जांच में जो भी दोषी पाए [...]", True, "tejas-only(skip)"),
    28: ("256d52de-9615-4977-a660-52ff14f0eebf", "Anuj Agrawal", "The accused persons are liable to be held guilty for the offence punishable under [...]", True, "agree"),
    29: ("256d52de-9615-4977-a660-52ff14f0eebf", "Anuj Agrawal", "The testimony of PW-4 , who is also the injured, stands on a high pedestal of [...]", True, "agree"),
    30: ("8ce58a14-91b9-4439-9f9f-fa631e2cec7a", "Disha Students' Organisation", "The resignation is a victory for the student-youth movement. But, the movement [...]", True, "agree"),
    31: ("8ce58a14-91b9-4439-9f9f-fa631e2cec7a", "Kavya", "The resignation is a big achievement, but we hope the government maintains the [...]", True, "agree"),
    32: ("8ce58a14-91b9-4439-9f9f-fa631e2cec7a", "Vijay Mallangi", "the resignation was a step in the right direction but should have come much earlier", True, "agree"),
    33: ("8ce58a14-91b9-4439-9f9f-fa631e2cec7a", "Bandru Vimala", "This is not an ordinary matter", True, "agree"),
    34: ("0be6615b-8666-4ea5-857a-60c4f12b2656", "Bharatiya Janata Party", "Friends... wasn't just a message. It was a COMMITMENT. From listening to students' [...]", True, "agree"),
    35: ("0be6615b-8666-4ea5-857a-60c4f12b2656", "Narendra Modi", "Cheating has a higher cost than ever before", True, "agree"),
    36: ("0be6615b-8666-4ea5-857a-60c4f12b2656", "Narendra Modi", "Your hard work deserves protection.", True, "agree"),
    37: ("96062271-ebcc-4efa-9558-890f573ffe16", "Unit 42", "None of this breaks the cryptography.", True, "agree"),
    38: ("96062271-ebcc-4efa-9558-890f573ffe16", "Unit 42", "GitHub enforced the check, while eBay accepted its test assertion until the [...]", False, "adj:medium"),
    39: ("b07d7ab6-9d88-4192-9b80-bddde802c7f2", "Prashant Kishor", "It was an attempt by the people of Bihar to send a message to the BJP's central [...]", True, "agree"),
    40: ("b07d7ab6-9d88-4192-9b80-bddde802c7f2", "Samrat Choudhary", "In the grand festival of democracy, the people have chosen Jan Suraaj in the [...]", True, "agree"),
    41: ("b651bbf6-9873-4e7c-955e-210879962d7b", "South Western Railway official", "ಲೊಂಡಾ ನಿಲ್ದಾಣ ಸಮೀಪ ವಿದ್ಯುತ್ ಮಾರ್ಗ ಸಮಸ್ಯೆಯಾಗಿದೆ. ಹೀಗಾಗಿ, ರೈಲುಗಳನ್ನು ಅಳ್ನಾವರದಲ್ಲಿ [...]", True, "tejas-only(skip)"),
    42: ("9007b82e-674b-45f1-a4ec-0646f54c353b", "Marco Rubio", "We are deeply invested in the region’s success and in cooperating with ASEAN and [...]", True, "agree"),
    43: ("9007b82e-674b-45f1-a4ec-0646f54c353b", "Marco Rubio", "The United States, India, Australia, and Japan share a vision of a free and open [...]", True, "agree"),
    44: ("9007b82e-674b-45f1-a4ec-0646f54c353b", "Sergio Gor", "Our four nations share a common vision", True, "agree"),
    45: ("873558d4-e1f5-4e85-9b99-0e088afc7747", "Aditi Moreshwar Choukhande", "मेरा सिलेक्शन नहीं हुआ...", True, "tejas-only(skip)"),
    46: ("873558d4-e1f5-4e85-9b99-0e088afc7747", "Chetan Chauhan", "जांच पूरी होने के बाद ही आत्महत्या के वास्तविक कारणों की पुष्टि की जाएगी.", True, "tejas-only(skip)"),
    47: ("296c2a06-d7c2-4368-af0c-a57c2a246d4c", "Ashok Borude", "I was proceeding towards Santacruz for patrol duty around 2 am, when I noticed the [...]", True, "agree"),
    48: ("0f697b1d-60ea-4ef2-b496-799702daaef9", "Praveen Karnwal", "Maintenance and a comprehensive overhaul of the bridge had been felt necessary for [...]", True, "agree"),
    49: ("0f697b1d-60ea-4ef2-b496-799702daaef9", "Bhagwan Singh Gusain", "Our markets and businesses will be affected by the closure during Sawan. [...]", True, "agree"),
    50: ("356a4392-2eea-4a1f-9bab-a2714a7d2c2f", "senior forest official", "The tiger that left Tadoba as a young sub-adult towards the end of 2025 has [...]", True, "agree"),
    51: ("356a4392-2eea-4a1f-9bab-a2714a7d2c2f", "senior forest official", "In this case, the tiger is most likely searching for a mate and a suitable [...]", True, "tejas-only(unsure)"),
    52: ("6c1f7778-278d-4d29-9fe5-1ca737c7b2c3", "Suryakiran A.S.", "The five-year construction clause should come into effect only after the Real [...]", True, "agree"),
    53: ("df91dbb1-3630-4ccc-9767-35cca29028e4", "Delhi Government", "No adverse legal action will be taken by any of the Police authorities within NCT [...]", True, "adj:high"),
    54: ("df91dbb1-3630-4ccc-9767-35cca29028e4", "Ashutosh Ranka", "demanded that all criminal cases against protesters be withdrawn and no fresh FIRs [...]", True, "agree"),
    55: ("df91dbb1-3630-4ccc-9767-35cca29028e4", "Saurav Das", "students and volunteers continued to face police action despite the Centre's assurances", True, "agree"),
    56: ("e4c8b05e-fc22-477f-8b95-0962b9c158fb", "V. Anantha Nageswaran", "The answer is to treat water the way we have finally learnt to treat roads and [...]", True, "agree"),
    57: ("e4c8b05e-fc22-477f-8b95-0962b9c158fb", "V. Anantha Nageswaran", "We price water at zero, so we treat it as limitless. So we waste it, and we [...]", True, "agree"),
    58: ("cd4d5149-7c5b-4781-84fb-157af4c8cc0b", "M. Murthy", "ಸಾರ್ವಜನಿಕರ ಜೀವನಾಡಿಯಾಗಿರುವ ಸರ್ಕಾರಿ ಬಸ್ಗಳು ಕೇವಲ ಸಂಚಾರದ ಸಾಧನಗಳಲ್ಲ. ಅವು ರಾಜ್ಯದ [...]", True, "tejas-only(skip)"),
}


def precision() -> float:
    return sum(1 for *_, a, _ in CLAIMS.values() if a) / len(CLAIMS)
