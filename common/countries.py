"""GDELT sourcecountry names → ISO 3166-1 alpha-2.

GDELT labels article origins with country *names*; our sources table uses
ISO2. Only names GDELT actually emits for our queries need to be here —
unknown names count as 'unknown' in coverage, which is honest.
"""

GDELT_COUNTRY_TO_ISO: dict[str, str] = {
    "united states": "US",
    "united kingdom": "GB",
    "india": "IN",
    "china": "CN",
    "russia": "RU",
    "germany": "DE",
    "france": "FR",
    "japan": "JP",
    "canada": "CA",
    "australia": "AU",
    "pakistan": "PK",
    "bangladesh": "BD",
    "sri lanka": "LK",
    "nepal": "NP",
    "singapore": "SG",
    "malaysia": "MY",
    "indonesia": "ID",
    "thailand": "TH",
    "philippines": "PH",
    "vietnam": "VN",
    "south korea": "KR",
    "hong kong": "HK",
    "taiwan": "TW",
    "israel": "IL",
    "iran": "IR",
    "iraq": "IQ",
    "saudi arabia": "SA",
    "united arab emirates": "AE",
    "qatar": "QA",
    "turkey": "TR",
    "egypt": "EG",
    "nigeria": "NG",
    "south africa": "ZA",
    "kenya": "KE",
    "brazil": "BR",
    "mexico": "MX",
    "argentina": "AR",
    "spain": "ES",
    "italy": "IT",
    "netherlands": "NL",
    "switzerland": "CH",
    "sweden": "SE",
    "norway": "NO",
    "poland": "PL",
    "ukraine": "UA",
    "ireland": "IE",
    "new zealand": "NZ",
}


def gdelt_country_to_iso(name: str | None) -> str | None:
    if not name:
        return None
    return GDELT_COUNTRY_TO_ISO.get(name.strip().lower())
