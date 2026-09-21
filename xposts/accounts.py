"""The accounts we read. Decided 2026-09-21: the pilot is official bodies only —
the institution speaking in its own name, first-party by construction. Wires
(@ANI, @PTI_News, ~700 posts a day between them) and named journalists are
tiers the schema already carries and the founder adds when the pilot's attach
rate earns their read bill ($0.005 a post, pay-per-use).

Listed = enabled. A handle removed here is disabled in x_accounts on the next
run, never deleted: an old attachment still names its account. Outlets' own
accounts are deliberately absent — they post their own article links, which
RSS already brings in. Every handle here posts in English or Hindi; Kannada
and Tamil handles wait for an embedding that carries same-story signal in
those scripts (correlation/clustering.EMBEDDING_TRUSTED_SCRIPTS).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class AccountSpec:
    handle: str  # without the @, as X's `username`
    name: str
    tier: str = "official"  # official | wire | journalist
    language: str = "en"


ACCOUNTS: list[AccountSpec] = [
    # ── Government of India: the press office and the ministries that make news ──
    AccountSpec("PIB_India", "Press Information Bureau"),
    AccountSpec("PMOIndia", "Prime Minister's Office"),
    AccountSpec("MEAIndia", "Ministry of External Affairs"),
    AccountSpec("HMOIndia", "Ministry of Home Affairs"),
    AccountSpec("FinMinIndia", "Ministry of Finance"),
    AccountSpec("MIB_India", "Ministry of Information and Broadcasting"),
    AccountSpec("MoHFW_INDIA", "Ministry of Health and Family Welfare"),
    AccountSpec("DoT_India", "Department of Telecommunications"),
    AccountSpec("RailMinIndia", "Ministry of Railways"),
    AccountSpec("MoRTHIndia", "Ministry of Road Transport and Highways"),
    AccountSpec("MinOfPower", "Ministry of Power"),
    AccountSpec("EduMinOfIndia", "Ministry of Education"),
    AccountSpec("ECISVEEP", "Election Commission of India"),
    AccountSpec("ISRO", "ISRO"),
    AccountSpec("IndiaMetDept", "India Meteorological Department"),
    AccountSpec("NDRFHQ", "National Disaster Response Force"),
    # ── Defence ──
    AccountSpec("adgpi", "Indian Army"),
    AccountSpec("IAF_MCC", "Indian Air Force"),
    AccountSpec("indiannavy", "Indian Navy"),
    # ── Cyber lens ──
    AccountSpec("IndianCERT", "CERT-In"),
    # ── Markets lens ──
    AccountSpec("RBI", "Reserve Bank of India"),
    # @SEBI_India is the investor-awareness account; the regulator itself posts
    # as @SEBI_updates (SEBI press release, 2025-04-04). The first poll on
    # 2026-09-21 could not resolve SEBI_India — it is an awareness handle X does
    # not return for the lookup — and the allowlist was wrong, not X.
    AccountSpec("SEBI_updates", "SEBI"),
    AccountSpec("NSEIndia", "National Stock Exchange"),
    AccountSpec("BSEIndia", "BSE"),
]

BY_HANDLE = {a.handle.casefold(): a for a in ACCOUNTS}
