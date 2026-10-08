"""B10, arrival debt (final family: signed sum, every member declared -, weight 0.5, no trait): I-059 deep run x short gap x travel (-), I-088 title last
week x first match here (-), I-060 consecutive weeks away x age (-), I-074 jet lag (-). Also the static geography that
B11 (f24) reuses: every event's country, continent and UTC offset on the match day.

Geography (static reference tables, built here from well-known public facts; no result is involved):
    event country   main tour and Challengers: Stage 4's hand-made table (src/eda/predictability_diagnostic/
                    stage4_country.py; 97-100% of their matches), plus SUPPLEMENT below for the 61 event names it leaves
                    blank; ITF: the three-letter code in the tournament id (100%); team events: Olympics, ATP Cup, United
                    Cup, Hopman Cup, World Team Cup and the Davis/Fed/BJK Cup Finals by name and year; other Davis/Fed/BJK
                    ties name two nations and not the venue: the continent is used only when both nations share it, the
                    offset only when their offsets differ by <= 2 hours (their mean); otherwise unknown.
    region          the final family's (rebuttals BOD-R2, BOD-R3): REGION, the body brainstormer's 81-code map with its
                    round-2 extension (EU, ME = Middle East and central Asia, AS, OC, NA, SA, AF), else COUNTRY's
                    continent; French overseas venues by city. Used for I-059's travel, I-060's home region and B11.
    offsets         I-074 uses the family's continent-level proxy: EU and AF +1, ME +4, AS +8, OC +10, NA -6, SA -3,
                    India +5.5, Kazakhstan +6 (BOD-R3), the circular difference east positive. The venue table
                    (COUNTRY standard offsets with DST rules, city keywords for multi-zone countries, US state codes)
                    gives only the sensitivity dz_zone (DST windows approximate: EU 25 Mar-27 Oct, NA 10 Mar-3 Nov,
                    AU/NZ 1 Oct-5 Apr, CL/PY 10 Sep-5 Apr, BR until 2019, UY until 2015; Russia +4 in 2011-14, Turkey +3
                    from Sep 2016, Morocco +1 from Oct 2018, Kazakhstan's east +5 from Mar 2024, Mexico without DST from
                    Oct 2022). The six-continent COUNTRY reading is the sensitivity cont6.
    The player's home region is the region of Stage 0's country (the nation represented, not the residence: a stated
    limitation).

Members (constants fixed in advance, none tuned on outcomes):
    I-059  Run_X = W_X exp(-gap_X / 2) (1 + Trav_X): W = played wins at X's previous event (any level, qualifying
           included); gap = t - t of X's last match there; tau = 2 days (math audit); Trav = 1[the previous event's
           region differs from this one's] (0 when either is unknown; mu = 1 fixed here: travel doubles the debt).
    I-088  1[X won a final (not team, not qualifying) whose lf is at most 9 days before this match's es] x 1[X's first
           match at this event] (MKT-19's primary).
    I-060  Wk_X (1 + 0.05 (age - 28)+) + 0.1 Away_X (alpha, beta fixed by the math audit): Wk = consecutive calendar
           weeks (Monday-start, by t) up to this one in which X played, this week included; Away = weeks since X last
           played in the home region (0 at home; capped at 26; rows of unknown region are skipped).
    I-074  JL_X = (1.5 dZ+ + 1.0 (-dZ)+) (1 - T / (1.0 |dZ|))+ (1 + 0.05 (age - 28)+): dZ = this venue's proxy offset minus
           the previous event's (circular, east positive), T = days since X's last match there (a = 1.5 east, b = 1.0 west,
           c = 1 day per zone, rho = 0.05, fixed here; BOD-15's "a day per zone, east harder").
Block: x = the sum of the members, each clipped at its 99th percentile of |m| and divided by its SD on 2014-2021,
times its declared sign -1; the row carries sign + for that oriented sum (the family writes the members' sign -). Controls (the union of the members' sets): dW, dTrav, dfirst, dtitle, dWk,
dAway, d age, dFat, dFit (21 days), d|dZ|, d exp(-gap/2), sets_14d, the members' missing indicators, the nearest
inputs; eta-mod: the symmetric missing indicators (Std). The family's B10 row lists no sum x eta terms.
"""
from __future__ import annotations

import re
import unicodedata

import numpy as np
import pandas as pd

from src.eda.feature_interactions import common as C
from src.eda.feature_interactions.features import f20_fatigue as F

# ------------------------------------------------------------------------------------------------
# static tables

# country code -> (continent, standard UTC offset in hours, DST rule); codes as Stage 0 and the ITF write them
COUNTRY = {
    # Europe
    "ALB": ("EU", 1, "EU"), "AND": ("EU", 1, "EU"), "AUT": ("EU", 1, "EU"), "BEL": ("EU", 1, "EU"),
    "BIH": ("EU", 1, "EU"), "BLR": ("EU", 3, ""), "BUL": ("EU", 2, "EU"), "CRO": ("EU", 1, "EU"),
    "CYP": ("EU", 2, "EU"), "CZE": ("EU", 1, "EU"), "DEN": ("EU", 1, "EU"), "ESP": ("EU", 1, "EU"),
    "EST": ("EU", 2, "EU"), "FIN": ("EU", 2, "EU"), "FRA": ("EU", 1, "EU"), "GBR": ("EU", 0, "EU"),
    "GEO": ("EU", 4, ""), "ARM": ("EU", 4, ""), "AZE": ("EU", 4, ""), "GER": ("EU", 1, "EU"),
    "GRE": ("EU", 2, "EU"), "HUN": ("EU", 1, "EU"), "IRL": ("EU", 0, "EU"), "ISL": ("EU", 0, ""),
    "ISR": ("EU", 2, "EU"), "ITA": ("EU", 1, "EU"), "KOS": ("EU", 1, "EU"), "LAT": ("EU", 2, "EU"),
    "LIE": ("EU", 1, "EU"), "LTU": ("EU", 2, "EU"), "LUX": ("EU", 1, "EU"), "MDA": ("EU", 2, "EU"),
    "MKD": ("EU", 1, "EU"), "MLT": ("EU", 1, "EU"), "MNE": ("EU", 1, "EU"), "MON": ("EU", 1, "EU"),
    "NED": ("EU", 1, "EU"), "NOR": ("EU", 1, "EU"), "POL": ("EU", 1, "EU"), "POR": ("EU", 0, "EU"),
    "ROU": ("EU", 2, "EU"), "RUS": ("EU", 3, "RU"), "SMR": ("EU", 1, "EU"), "SRB": ("EU", 1, "EU"),
    "SLO": ("EU", 1, "EU"), "SUI": ("EU", 1, "EU"), "SVK": ("EU", 1, "EU"), "SWE": ("EU", 1, "EU"),
    "TUR": ("EU", 2, "TR"), "UKR": ("EU", 2, "EU"), "GIB": ("EU", 1, "EU"),
    # Asia
    "BAN": ("AS", 6, ""), "BRN": ("AS", 3, ""), "BRU": ("AS", 8, ""), "CAM": ("AS", 7, ""), "CHN": ("AS", 8, ""),
    "HKG": ("AS", 8, ""), "INA": ("AS", 7, ""), "IND": ("AS", 5.5, ""), "IRI": ("AS", 3.5, ""), "IRQ": ("AS", 3, ""),
    "JOR": ("AS", 2, "EU"), "JPN": ("AS", 9, ""), "KAZ": ("AS", 6, "KZ"), "KGZ": ("AS", 6, ""), "KOR": ("AS", 9, ""),
    "KSA": ("AS", 3, ""), "KUW": ("AS", 3, ""), "LAO": ("AS", 7, ""), "LBN": ("AS", 2, "EU"), "LIB": ("AS", 2, "EU"),
    "MAC": ("AS", 8, ""), "MAS": ("AS", 8, ""), "MGL": ("AS", 8, ""), "MYA": ("AS", 6.5, ""), "NEP": ("AS", 5.75, ""),
    "OMA": ("AS", 4, ""), "PAK": ("AS", 5, ""), "PHI": ("AS", 8, ""), "QAT": ("AS", 3, ""), "SGP": ("AS", 8, ""),
    "SRI": ("AS", 5.5, ""), "SYR": ("AS", 2, "EU"), "THA": ("AS", 7, ""), "TJK": ("AS", 5, ""), "TKM": ("AS", 5, ""),
    "TPE": ("AS", 8, ""), "UAE": ("AS", 4, ""), "UZB": ("AS", 5, ""), "VIE": ("AS", 7, ""),
    # Africa
    "ALG": ("AF", 1, ""), "ANG": ("AF", 1, ""), "BDI": ("AF", 2, ""), "BEN": ("AF", 1, ""), "BOT": ("AF", 2, ""),
    "BUR": ("AF", 0, ""), "CGO": ("AF", 1, ""), "CIV": ("AF", 0, ""), "CMR": ("AF", 1, ""), "COD": ("AF", 1, ""),
    "DJI": ("AF", 3, ""), "EGY": ("AF", 2, ""), "ETH": ("AF", 3, ""), "GAB": ("AF", 1, ""), "GHA": ("AF", 0, ""),
    "KEN": ("AF", 3, ""), "MAD": ("AF", 3, ""), "MAR": ("AF", 0, "MA"), "MLI": ("AF", 0, ""), "MOZ": ("AF", 2, ""),
    "MRI": ("AF", 4, ""), "NAM": ("AF", 2, ""), "NGR": ("AF", 1, ""), "RSA": ("AF", 2, ""), "RWA": ("AF", 2, ""),
    "SEN": ("AF", 0, ""), "SUD": ("AF", 2, ""), "TAN": ("AF", 3, ""), "TOG": ("AF", 0, ""), "TUN": ("AF", 1, ""),
    "UGA": ("AF", 3, ""), "ZAM": ("AF", 2, ""), "ZIM": ("AF", 2, ""),
    # North and Central America, Caribbean
    "BAH": ("NA", -5, "NA"), "BAR": ("NA", -4, ""), "BER": ("NA", -4, "NA"), "CAN": ("NA", -5, "NA"),
    "CRC": ("NA", -6, ""), "CUB": ("NA", -5, "NA"), "DOM": ("NA", -4, ""), "ESA": ("NA", -6, ""),
    "GUA": ("NA", -6, ""), "GUD": ("NA", -4, ""), "HAI": ("NA", -5, "NA"), "HON": ("NA", -6, ""),
    "JAM": ("NA", -5, ""), "MEX": ("NA", -6, "MX"), "MRN": ("NA", -4, ""), "NCA": ("NA", -6, ""),
    "PAN": ("NA", -5, ""), "PUR": ("NA", -4, ""), "TTO": ("NA", -4, ""), "USA": ("NA", -5, "NA"),
    "ARU": ("NA", -4, ""), "AHO": ("NA", -4, ""),
    # South America
    "ARG": ("SA", -3, ""), "BOL": ("SA", -4, ""), "BRA": ("SA", -3, "BR"), "CHI": ("SA", -4, "CL"),
    "COL": ("SA", -5, ""), "ECU": ("SA", -5, ""), "GUY": ("SA", -4, ""), "PAR": ("SA", -4, "CL"),
    "PER": ("SA", -5, ""), "SUR": ("SA", -3, ""), "URU": ("SA", -3, "UY"), "VEN": ("SA", -4, ""),
    # Oceania
    "AUS": ("OC", 10, "AU"), "FIJ": ("OC", 12, ""), "GUM": ("OC", 10, ""), "NZL": ("OC", 12, "AU"),
    "PNG": ("OC", 10, ""), "SAM": ("OC", 13, ""), "TGA": ("OC", 13, ""),
}
ALIASES = {"PRT": "POR", "URY": "URU", "SVN": "SLO", "VNM": "VIE", "PRY": "PAR", "BHR": "BRN", "BWA": "BOT",
           "SAU": "KSA", "GTM": "GUA", "CHL": "CHI", "PRI": "PUR", "COG": "CGO", "SIN": "SGP",
           "IRN": "IRI", "DEU": "GER", "NLD": "NED", "CHE": "SUI", "HRV": "CRO", "GRC": "GRE", "BGR": "BUL",
           "ZAF": "RSA", "MYS": "MAS", "IDN": "INA", "LVA": "LAT", "DNK": "DEN", "TWN": "TPE", "ROM": "ROU"}

# event names (Stage 4's key) that Stage 4's table leaves blank, read from the city in the name
SUPPLEMENT = {
    "aachen ch": "GER", "alessandria ch": "ITA", "barcelona": "ESP", "bath ch": "GBR", "belem ch": "BRA",
    "belo horizonte ch": "BRA", "bercuit ch": "BEL", "bytom ch": "POL", "cairo ch": "EGY", "calabasas ch": "USA",
    "caloundra ch": "AUS", "campos do jordao ch": "BRA", "carson ch": "USA", "copenhagen": "DEN",
    "costa do sauipe": "BRA", "courmayeur ch": "ITA", "cremona ch": "ITA", "dallas": "USA", "dortmund ch": "GER",
    "estoril": "POR", "fes": "MAR", "honolulu ch": "USA", "jersey ch": "GBR", "johannesburg": "RSA",
    "kitzbuhel ch": "AUT", "lermontov ch": "RUS", "ljubljana ch": "SLO", "los angeles": "USA", "marrakech ch": "MAR",
    "new haven": "USA", "ojai ch": "USA", "palermo ch": "ITA", "penza ch": "RUS", "pingguo ch": "CHN", "pune": "IND",
    "ponte vedra beach": "USA", "rabat ch": "MAR", "ramat hasharon ch": "ISR", "recife ch": "BRA",
    "reggio emilia ch": "ITA", "reunion island": "FRA", "rhodes ch": "GRE", "rijeka ch": "CRO", "rimini ch": "ITA",
    "salvador ch": "BRA", "san remo ch": "ITA", "san sebastian ch": "ESP", "saransk ch": "RUS", "singapore ch": "SGP",
    "sunrise ch": "USA", "tarragona ch": "ESP", "trani ch": "ITA", "tulsa ch": "USA", "villa allende ch": "ARG",
    "wolfsburg ch": "GER", "wuhai ch": "CHN", "wuhan ch": "CHN", "san jose ch": "USA"}
# the tour finals by year (ATP: London 2009-2020, Turin from 2021; WTA: Doha 2010, Istanbul 2011-13, Singapore 2014-18,
# Shenzhen 2019, Guadalajara 2021, Fort Worth 2022, Cancun 2023, Riyadh 2024)
FINALS = {"atp": [(2009, 2020, "GBR"), (2021, 2099, "ITA")],
          "wta": [(2010, 2010, "QAT"), (2011, 2013, "TUR"), (2014, 2018, "SGP"), (2019, 2019, "CHN"),
                  (2021, 2021, "MEX"), (2022, 2022, "USA"), (2023, 2023, "MEX"), (2024, 2024, "KSA")]}
# team events by name and year; city keywords for the zone are added to the name (see team_venue)
TEAM_EVENTS = [("olympics", {2012: ("GBR", "london"), 2016: ("BRA", "rio"), 2021: ("JPN", "tokyo"),
                             2024: ("FRA", "paris")}),
               ("atp cup", {0: ("AUS", "sydney")}), ("united cup", {0: ("AUS", "sydney")}),
               ("hopman cup", {0: ("AUS", "perth"), 2023: ("FRA", "nice")}), ("dusseldorf", {0: ("GER", "")}),
               ("world team", {0: ("GER", "")}),
               ("laver cup", {2017: ("CZE", ""), 2018: ("USA", "chicago"), 2019: ("SUI", ""), 2021: ("USA", "boston"),
                              2022: ("GBR", ""), 2023: ("CAN", "vancouver"), 2024: ("GER", "")}),
               ("davis cup finals", {0: ("ESP", "")}), ("davis cup fls", {0: ("ESP", "")}),
               ("bjk cup finals", {2021: ("CZE", ""), 2022: ("GBR", ""), 0: ("ESP", "")}),
               ("fed cup finals", {0: ("CZE", "")})]

# city keywords inside a multi-zone country: (standard offset, DST rule, continent override or None)
CITY_ZONE = {
    "USA": [(("indian wells", "los angeles", "san diego", "san jose", "stanford", "carlsbad", "la jolla", "newport beach",
              "palo alto", "tiburon", "aptos", "fairfield", "sacramento", "stockton", "napa", "san francisco", "carson",
              "ojai", "calabasas", "las vegas", "berkeley", "rancho", "laguna", "irvine", "costa mesa", "seattle",
              "spokane", "fresno", "oakland", "redding", "bakersfield", "torrance", "malibu", "santa barbara",
              "claremont", "pasadena", "beverly hills", "el dorado", "yuba city", "sunnyvale", "portland or",
              "lakewood ca", "pacific palisades"), -8, "NA"),
            (("denver", "salt lake", "boise", "albuquerque", "santa fe"), -7, "NA"),
            (("phoenix", "tempe", "scottsdale", "tucson"), -7, ""),
            (("houston", "dallas", "austin", "memphis", "chicago", "champaign", "winnetka", "irving", "little rock",
              "tulsa", "tyler", "waco", "baton rouge", "san antonio", "lincoln", "sioux falls", "kansas city",
              "oklahoma", "new orleans", "st louis", "st. louis", "edwardsville", "lubbock", "college station",
              "nashville", "fort worth", "brownsville", "corpus christi", "harlingen", "mcallen", "wichita", "omaha",
              "minneapolis", "milwaukee", "madison", "evanston", "peoria", "shreveport", "lafayette", "hattiesburg",
              "starkville", "fayetteville", "norman", "stillwater", "denton", "frisco", "plano", "mobile",
              "birmingham", "springfield mo", "rochester mn", "bloomington mn", "iowa city", "ames", "lawrence",
              "pensacola"), -6, "NA"),
            (("honolulu", "maui", "lahaina", "kona", "hawaii"), -10, "")],
    "CAN": [(("vancouver", "victoria", "kelowna", "surrey", "burnaby"), -8, "NA"),
            (("calgary", "edmonton", "lethbridge", "red deer"), -7, "NA"),
            (("winnipeg",), -6, "NA"), (("saskatoon", "regina"), -6, "")],
    "MEX": [(("los cabos", "cabo", "mazatlan"), -7, "MX"), (("tijuana",), -8, "MX"), (("hermosillo",), -7, ""),
            (("cancun",), -6, "MQ")],
    "BRA": [(("recife", "salvador", "belem", "fortaleza", "natal", "costa do sauipe", "joao pessoa", "maceio",
              "aracaju", "teresina", "sauipe"), -3, ""), (("manaus",), -4, "")],
    "RUS": [(("tyumen", "yekaterinburg", "ekaterinburg", "ufa", "perm", "chelyabinsk", "orenburg"), 5, "RU"),
            (("samara", "togliatti", "saratov", "astrakhan", "izhevsk"), 4, "RU"), (("kaliningrad",), 2, "RU"),
            (("novosibirsk", "krasnoyarsk", "tomsk", "barnaul"), 7, "RU"), (("omsk",), 6, "RU"),
            (("khabarovsk", "vladivostok"), 10, "RU")],
    "AUS": [(("perth",), 8, ""), (("darwin", "alice springs"), 9.5, ""),
            (("brisbane", "caloundra", "gold coast", "cairns", "townsville", "toowoomba", "mackay", "sunshine coast",
              "bundaberg", "rockhampton", "ipswich", "maryborough"), 10, ""),
            (("adelaide", "playford", "happy valley", "west lakes", "mount gambier", "whyalla"), 9.5, "AU")],
    "KAZ": [(("aktobe", "uralsk", "aktau", "atyrau", "oral"), 5, "")],
    "INA": [(("bali", "denpasar", "nusa dua", "makassar"), 8, "")],
    "ESP": [(("tenerife", "las palmas", "gran canaria", "maspalomas", "lanzarote", "fuerteventura", "la palma"), 0,
             "EU")],
    "POR": [(("madeira", "funchal"), 0, "EU"), (("azores", "ponta delgada"), -1, "EU")],
    "FRA": [(("reunion",), 4, "", "AF"), (("noumea", "caledonia", "caledonie"), 11, "", "OC"),
            (("gosier", "guadeloupe", "pointe a pitre", "baie mahault", "martinique", "fort de france"), -4, "", "NA"),
            (("tahiti", "papeete"), -10, "", "OC"), (("cayenne",), -3, "", "SA")],
}
US_STATE = {**{s: (-5, "NA") for s in "CT DE FL GA IN KY ME MD MA MI NH NJ NY NC OH PA RI SC VT VA WV DC".split()},
            **{s: (-6, "NA") for s in "AL AR IL IA KS LA MN MS MO NE ND OK SD TN TX WI".split()},
            **{s: (-7, "NA") for s in "CO ID MT NM UT WY".split()}, "AZ": (-7, ""),
            **{s: (-8, "NA") for s in "CA NV OR WA".split()}, "HI": (-10, ""), "AK": (-9, "NA")}

# The final family's regions and offsets (rebuttals BOD-R2, BOD-R3, accepted): the body brainstormer's 81-code map
# (src/eda/feature_interactions/round0/body/counts.py CONTINENT) plus its round-2 extension (round2/body/calc_report.py
# EXTRA), copied here so the builder is self-contained; codes outside it fall back to COUNTRY's continent.
REGION = {
    **{c: "EU" for c in ["AND", "AUT", "AZE", "BEL", "BIH", "BUL", "CRO", "CZE", "ESP", "EST", "FIN", "FRA", "GBR",
                         "GEO", "GER", "GRE", "HUN", "IRL", "ITA", "LAT", "LTU", "LUX", "MDA", "MKD", "MON", "NED",
                         "POL", "POR", "ROU", "RUS", "SLO", "SMR", "SRB", "SUI", "SVK", "SWE", "TUR", "UKR"]},
    **{c: "ME" for c in ["BRN", "ISR", "KSA", "QAT", "UAE", "KAZ", "UZB", "PAK"]},
    **{c: "AS" for c in ["CHN", "HKG", "IND", "JPN", "KOR", "MAS", "PHI", "SGP", "THA", "TPE", "VIE"]},
    **{c: "OC" for c in ["AUS", "NZL"]},
    **{c: "NA" for c in ["USA", "CAN", "MEX", "DOM", "PUR", "PAN"]},
    **{c: "SA" for c in ["ARG", "BOL", "BRA", "CHI", "COL", "ECU", "PAR", "PER", "URU"]},
    **{c: "AF" for c in ["CGO", "CIV", "EGY", "MAR", "RSA", "RWA", "TUN"]},
    # round-2 extension
    **{c: "EU" for c in ["NOR", "DEN", "BLR", "ARM", "MNE", "ALB", "KOS", "CYP", "MLT", "ISL", "LIE", "IRL"]},
    **{c: "NA" for c in ["GUA", "CRC", "ESA", "JAM", "BAR", "TTO", "BAH", "HON", "NCA", "CUB"]},
    **{c: "SA" for c in ["VEN", "COL", "BOL"]}, **{c: "AF" for c in ["NGR", "KEN", "ZIM", "MRI", "ALG", "ZAM"]},
    **{c: "ME" for c in ["IRI", "LBN", "LIB", "JOR", "KUW", "OMA", "KGZ", "TJK"]},
    **{c: "AS" for c in ["INA", "SRI", "NEP", "BAN", "MGL", "MAC"]}, **{c: "OC" for c in ["GUM", "FIJ", "NCL", "TAH"]}}
REGION_OFFSET = {"EU": 1, "AF": 1, "ME": 4, "AS": 8, "OC": 10, "NA": -6, "SA": -3}   # hours, continent-level proxy
COUNTRY_OFFSET = {"IND": 5.5, "KAZ": 6.0}                                           # BOD-R3's two overrides


def region(code, cont_override=None):
    """The final family's region of a venue code (city overrides for French overseas venues win)."""
    if cont_override is not None:
        return cont_override
    if code is None:
        return None
    return REGION.get(code, COUNTRY[code][0] if code in COUNTRY else None)


ITF_CODE = re.compile(r"^\d{4}-[MW]-[A-Z0-9]+-([A-Z]{3})-")
TIE = re.compile(r"\b([A-Z]{3}) vs ([A-Z]{3})\b")
STATE = re.compile(r"\b([A-Z]{2})\b")


def norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z. ]", " ", s.replace("-", " ")).split())


def _code(c):
    if not isinstance(c, str) or not c or c == "<NA>":
        return None
    c = ALIASES.get(c, c)
    return c if c in COUNTRY else None


def _dst_delta(rule: str, day: pd.Timestamp) -> float:
    """Hours added to the standard offset on `day` under an approximate DST rule (see the module docstring)."""
    md = day.month * 100 + day.day
    if rule == "EU":
        return 1.0 if 325 <= md <= 1027 else 0.0
    if rule == "NA":
        return 1.0 if 310 <= md <= 1103 else 0.0
    if rule == "AU":
        return 1.0 if (md >= 1001 or md <= 405) else 0.0
    if rule == "CL":
        return 1.0 if (md >= 910 or md <= 405) else 0.0
    if rule == "BR":
        return 1.0 if (md >= 1015 or md <= 220) and day < pd.Timestamp("2019-02-17") else 0.0
    if rule == "UY":
        return 1.0 if (md >= 1001 or md <= 310) and day < pd.Timestamp("2015-03-08") else 0.0
    if rule == "MX":
        return 1.0 if 401 <= md <= 1028 and day < pd.Timestamp("2022-10-30") else 0.0
    if rule == "MQ":                                       # Cancun: -5 fixed from 1 Feb 2015, before as MX
        return 1.0 if day >= pd.Timestamp("2015-02-01") else _dst_delta("MX", day)
    if rule == "MA":                                       # Morocco: +1 fixed from 28 Oct 2018, before EU-style DST
        return 1.0 if day >= pd.Timestamp("2018-10-28") else _dst_delta("EU", day)
    if rule == "TR":                                       # Turkey: +3 permanent from 7 Sep 2016
        return 1.0 if day >= pd.Timestamp("2016-09-07") else _dst_delta("EU", day)
    if rule == "RU":                                       # Russia: +1 all year 27 Mar 2011 - 26 Oct 2014
        if pd.Timestamp("2011-03-27") <= day < pd.Timestamp("2014-10-26"):
            return 1.0
        return _dst_delta("EU", day) if day < pd.Timestamp("2011-03-27") else 0.0
    if rule == "KZ":                                       # Kazakhstan's east: +5 from 1 Mar 2024
        return -1.0 if day >= pd.Timestamp("2024-03-01") else 0.0
    return 0.0


def venue_zone(code, name: str, raw: str):
    """(standard offset, DST rule, continent) of a venue in country `code`, refined by city keywords or a US state."""
    if code is None:
        return (np.nan, "", None)
    cont, off, rule = COUNTRY[code]
    for entry in CITY_ZONE.get(code, []):
        keys, o, r = entry[0], entry[1], entry[2]
        if any(k in name for k in keys):
            return (o, r, entry[3] if len(entry) > 3 else cont)
    if code == "USA" and isinstance(raw, str):
        for tok in STATE.findall(raw):
            if tok in US_STATE:
                o, r = US_STATE[tok]
                return (o, r, cont)
    return (off, rule, cont)


def _team_venue(name: str, raw: str, year: int):
    for key, table in TEAM_EVENTS:
        if key in name:
            code, city = table.get(year, table.get(0, (None, "")))
            if code is None:
                return None, None, np.nan, "", None
            o, r, cont = venue_zone(code, city, "")
            return code, cont, o, r, region(code, cont if cont != COUNTRY[code][0] else None)
    m = TIE.search(str(raw))
    if m:
        a, b = _code(m.group(1)), _code(m.group(2))
        if a and b:
            ca, cb = COUNTRY[a], COUNTRY[b]
            cont = ca[0] if ca[0] == cb[0] else None
            o = (ca[1] + cb[1]) / 2 if abs(ca[1] - cb[1]) <= 2 else np.nan
            ra, rb = region(a), region(b)
            return None, cont, o, "", (ra if ra == rb else None)
    return None, None, np.nan, "", None


def event_table(H: pd.DataFrame) -> pd.DataFrame:
    """One row per tournament id in H: country (venue code or None), continent, standard offset and DST rule."""
    from src.eda.predictability_diagnostic import stage4_country as SC
    ev = H.drop_duplicates("tournament_id")[["tournament_id", "tour", "level", "tournament_name", "tyear"]].copy()
    ev = ev.rename(columns={"tyear": "year"}).reset_index(drop=True)
    ev["tournament_id"] = ev["tournament_id"].astype(str)
    s4 = SC.event_country(ev).astype("object").to_numpy()
    keys = ev["tournament_name"].map(SC.event_key).to_numpy()
    rows = []
    for i, r in enumerate(ev.itertuples(index=False)):
        name, raw = norm(r.tournament_name), str(r.tournament_name)
        code = _code(s4[i]) if isinstance(s4[i], str) else None
        if code is None and keys[i] in SUPPLEMENT:
            code = SUPPLEMENT[keys[i]]
        if code is None and "finals" in name and r.level == "FIN":
            code = next((c for lo, hi, c in FINALS.get(r.tour, []) if lo <= r.year <= hi), None)
        if code is None and r.level == "ITF":
            m = ITF_CODE.match(r.tournament_id)
            code = _code(m.group(1)) if m else None
        if r.level == "TEAM" and code is None:
            code, cont, o, rule, reg = _team_venue(name, raw, int(r.year))
        else:
            o, rule, cont = venue_zone(code, name, raw)
            reg = region(code, cont if (code in COUNTRY and cont != COUNTRY[code][0]) else None)
        proxy = COUNTRY_OFFSET.get(code, REGION_OFFSET.get(reg, np.nan)) if reg is not None else np.nan
        rows.append((r.tournament_id, code, cont, o, rule, reg, proxy))
    return pd.DataFrame(rows, columns=["tournament_id", "country", "continent", "utc_std", "dst", "region", "proxy_off"])


def geo(H: pd.DataFrame) -> None:
    """Per history row: venue continent (H["cont"], None when unknown) and UTC offset on the match day (H["utc"])."""
    if "utc" in H.columns:
        return
    E = event_table(H).set_index("tournament_id")
    tid = H["tournament_id"].astype(str)
    H["cont"] = tid.map(E["region"]).to_numpy()                   # the family's region (BOD-R2)
    H["cont6"] = tid.map(E["continent"]).to_numpy()               # the six-continent reading (a sensitivity)
    H["utc_proxy"] = tid.map(E["proxy_off"]).to_numpy(float)      # the family's continent-level offset (BOD-R3)
    std = tid.map(E["utc_std"]).to_numpy(float)
    rule = tid.map(E["dst"]).fillna("").to_numpy()
    days = pd.to_datetime(H["t"].to_numpy(), unit="D")
    # vectorised DST: evaluate each (rule, day) pair once
    key = pd.Series(list(zip(rule, days.normalize())))
    uniq = {k: _dst_delta(k[0], k[1]) if k[0] else 0.0 for k in set(key)}
    H["utc"] = std + key.map(uniq).to_numpy(float)                # the venue zone with DST (a sensitivity)


def arrival(H: pd.DataFrame) -> None:
    """Per history row, from the player's STRICTLY earlier rows only (own order; safe by construction):
    seg (event segment), first (first row at this event), on_n (played matches already at this event), pe_last (the
    previous event's last row, -1 if none), gap (t - t[pe_last]), w_prev (played wins at the previous event),
    title_lf (lf of a won final there, NaN if none), trav (1[continent changed], NaN if unknown), dz (UTC change,
    east positive, NaN if unknown), wk (consecutive played weeks up to this one), away (weeks since the last match on
    the home continent, NaN if unknown), prev_surface (surface at the previous event's last row)."""
    if "wk" in H.columns:
        return
    geo(H)
    n = len(H)
    pid = H["pid"].to_numpy()
    tid = H["tournament_id"].astype(str).to_numpy()
    new_seg = np.r_[True, (pid[1:] != pid[:-1]) | (tid[1:] != tid[:-1])]
    seg = np.cumsum(new_seg) - 1
    H["seg"], H["first"] = seg, new_seg.astype(float)
    played = H["played"].to_numpy(bool)
    won = H["won"].to_numpy(bool)
    pw = pd.Series((played & won).astype(float))
    pc = pd.Series(played.astype(float))
    H["on_n"] = (pc.groupby(seg).cumsum() - pc).to_numpy()
    seg_first = pd.Series(np.arange(n)).groupby(seg).transform("min").to_numpy()
    seg_last = pd.Series(np.arange(n)).groupby(seg).transform("max").to_numpy()
    # previous segment of the same player: its last row
    prev_last = np.where(seg_first > 0, seg_first - 1, -1)
    prev_last = np.where((prev_last >= 0) & (pid[np.maximum(prev_last, 0)] == pid), prev_last, -1)
    H["pe_last"] = prev_last
    t = H["t"].to_numpy(float)
    ok = prev_last >= 0
    pl = np.maximum(prev_last, 0)
    H["gap"] = np.where(ok, t - t[pl], np.nan)
    wins_seg = pw.groupby(seg).sum()
    H["w_prev"] = np.where(ok, wins_seg.reindex(seg[pl]).to_numpy(), 0.0)
    final_won = (H["round"].astype(str).to_numpy() == "F") & won & played & ~H["qualifying"].to_numpy(bool) \
        & (H["level"].astype(str).to_numpy() != "TEAM")
    lf = H["lf"].to_numpy(float)
    title_seg = pd.Series(np.where(final_won, lf, np.nan)).groupby(seg).max()
    H["title_lf"] = np.where(ok, title_seg.reindex(seg[pl]).to_numpy(), np.nan)
    cont = H["cont"].to_numpy(object)
    known = np.array([isinstance(c, str) for c in cont])
    H["trav"] = np.where(ok & known & known[pl], (cont != cont[pl]).astype(float), np.nan)
    def circ(d):                                                   # into (-12, 12], east positive
        return ((d + 12.0) % 24.0) - 12.0
    up = H["utc_proxy"].to_numpy(float)
    H["dz"] = np.where(ok, circ(up - up[pl]), np.nan)              # the family's jet-lag input
    uz = H["utc"].to_numpy(float)
    H["dz_zone"] = np.where(ok, circ(uz - uz[pl]), np.nan)
    surf = H["surface"].astype(str).to_numpy()
    H["prev_surface"] = np.where(ok, surf[pl], None)
    _weeks(H, pid, t, played, cont, known)


def _weeks(H, pid, t, played, cont, known) -> None:
    from src.eda.predictability_diagnostic import stage4_country as SC
    week = ((t + 3) // 7).astype(int)                      # Monday-start weeks (1970-01-01 was a Thursday)
    home = SC.player_country(H["country"]).map(lambda c: region(_code(c)) if _code(c) else None).to_numpy(object)
    pid_l, wk_l, pl_l, ct_l, kn_l, hm_l = pid.tolist(), week.tolist(), played.tolist(), cont.tolist(), \
        known.tolist(), home.tolist()
    n = len(pid_l)
    wk_out, away_out = [1.0] * n, [np.nan] * n
    prev_p, run, run_week, last_home_week = -1, 0, None, None
    for i in range(n):
        p, w = pid_l[i], wk_l[i]
        if p != prev_p:
            run, run_week, last_home_week = 0, None, None
        # weeks: the run ending at the previous played week, extended to this week
        if run_week is None:
            cur = 1
        elif run_week == w:
            cur = run
        elif run_week == w - 1:
            cur = run + 1
        else:
            cur = 1
        wk_out[i] = float(cur)
        h = hm_l[i]
        if kn_l[i] and isinstance(h, str):
            if ct_l[i] == h:
                away_out[i] = 0.0
            else:
                away_out[i] = float(min(w - last_home_week, 26)) if last_home_week is not None else 26.0
        if pl_l[i]:
            run, run_week = cur, w
            if kn_l[i] and isinstance(h, str) and ct_l[i] == h:
                last_home_week = w
        prev_p = p
    H["wk"], H["away"] = wk_out, away_out


# ------------------------------------------------------------------------------------------------
# B10

TAU_RUN, MU_TRAV, TITLE_DAYS = 2.0, 1.0, 9.0
ALPHA_WK, BETA_AWAY, AGE_KNEE = 0.05, 0.1, 28.0
JL_EAST, JL_WEST, JL_DAYS_PER_ZONE, JL_RHO = 1.5, 1.0, 1.0, 0.05


def per_row_b10(H: pd.DataFrame) -> dict:
    arrival(H)
    gap = H["gap"].to_numpy(float)
    trav = H["trav"].to_numpy(float)
    run = H["w_prev"].to_numpy(float) * np.exp(-np.nan_to_num(gap, nan=1e9) / TAU_RUN) * (1 + MU_TRAV * np.nan_to_num(trav))
    title = (np.isfinite(H["title_lf"].to_numpy(float))
             & (H["es"].to_numpy(float) - H["title_lf"].to_numpy(float) <= TITLE_DAYS)).astype(float)
    dz = H["dz"].to_numpy(float)
    az = np.abs(dz)
    with np.errstate(invalid="ignore", divide="ignore"):
        fade = np.where(az > 1e-9, np.maximum(1 - np.nan_to_num(gap, nan=1e9) / (JL_DAYS_PER_ZONE * az), 0), 0.0)
    jl0 = np.where(np.isfinite(dz), (JL_EAST * np.maximum(dz, 0) + JL_WEST * np.maximum(-dz, 0)) * fade, np.nan)
    fat3, _ = F.fat(H)
    fit21, _ = F.fat(H, 21.0)
    decay = np.where(np.isfinite(gap), np.exp(-np.nan_to_num(gap) / TAU_RUN), 0.0)
    return {"run": run, "trav": trav, "wprev": H["w_prev"].to_numpy(float), "first": H["first"].to_numpy(float),
            "decay": decay,
            "title": title, "t88": title * H["first"].to_numpy(float), "wk": H["wk"].to_numpy(float),
            "away": H["away"].to_numpy(float), "jl0": jl0, "dzabs": az, "fat": fat3, "fit": fit21}


def prepare_b10(P: pd.DataFrame, L: pd.DataFrame) -> dict:
    H = F.history(P, L)
    out = {}
    for k, v in per_row_b10(H).items():
        out[f"bd10_{k}_a"], out[f"bd10_{k}_b"] = F.at_model(P, H, v)
    return out


def _agefac(P, side):
    return 1 + ALPHA_WK * np.maximum(F.col(P, f"age_{side}") - AGE_KNEE, 0)


def b10_members(P: pd.DataFrame) -> dict:
    g = lambda k: F.ab(P, f"bd10_{k}")                                   # noqa: E731
    run, t88, wk, away, jl0 = g("run"), g("t88"), g("wk"), g("away"), g("jl0")
    m60 = [wk[i] * _agefac(P, s) + BETA_AWAY * away[i] for i, s in enumerate("ab")]
    m74 = [jl0[i] * (1 + JL_RHO * np.maximum(F.col(P, f"age_{s}") - AGE_KNEE, 0)) for i, s in enumerate("ab")]
    return {"I-059": run[0] - run[1], "I-088": t88[0] - t88[1], "I-060": m60[0] - m60[1], "I-074": m74[0] - m74[1]}


def combine_b10(P: pd.DataFrame) -> dict:
    M = b10_members(P)
    x = F.block(P, [(M[k], -1) for k in ("I-059", "I-088", "I-060", "I-074")])
    g = lambda k: F.ab(P, f"bd10_{k}")                                   # noqa: E731
    d = lambda k, fill=0.0: np.nan_to_num(g(k)[0], nan=fill) - np.nan_to_num(g(k)[1], nan=fill)  # noqa: E731
    named = {"wprev_a-b": d("wprev"), "decay_a-b": d("decay"), "trav_a-b": d("trav"), "first_a-b": d("first"),
             "title_a-b": d("title"),
             "wk_a-b": d("wk"), "away_a-b": d("away"), "in_age": F.col(P, "in_age"), "fat_a-b": d("fat"),
             "fit21_a-b": d("fit"), "dzabs_a-b": d("dzabs"), "in_sets_14d": F.col(P, "in_sets_14d"),
             "trav_missing_a-b": F.miss_diff(*g("trav")), "away_missing_a-b": F.miss_diff(*g("away")),
             "dz_missing_a-b": F.miss_diff(*g("dzabs"))}
    ctrl, names = F.controls(P, named, x, F.NEAREST.get("B10"))
    # the family's B10 controls: component differences, sets_14d, Std (missingness: the differences above and these)
    mods = np.column_stack([F.centre(P, F.sym_miss(*g("trav"))), F.centre(P, F.sym_miss(*g("away"))),
                            F.centre(P, F.sym_miss(*g("dzabs")))])
    return {"x": x, "controls": ctrl, "control_names": names, "eta_mod_controls": mods,
            "tabpfn": {f"bd10_{k.replace('-', '')}": (v, "diff", None) for k, v in M.items()}}


HYPOTHESES = [
    {"hid": "B10", "master": "I-059+I-088+I-060+I-074", "kind": "W", "sign": "+", "weight": 0.5, "trait": "none",
     "deployment": "diff", "prepare": prepare_b10, "combine": combine_b10, "family": "11/14/16",
     "members": {"I-059": "-", "I-088": "-", "I-060": "-", "I-074": "-"}},
]
