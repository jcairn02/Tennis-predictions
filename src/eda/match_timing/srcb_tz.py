"""Time zones for the match-timing links (sources B): an event's IANA zone from its country.

The country comes from the predictability diagnostic's hand-made event table
(data/studies/predictability_diagnostic/stage4_event_country.csv, read through
src/eda/predictability_diagnostic/stage4_country.event_country). That table covers the evaluation
events (Grand Slams, tour level, Challengers / WTA 125 and their qualifying), not ITF or team events.

A country with one civil zone maps straight to it. A country with several (the United States,
Canada, Mexico, Australia, Brazil, Russia, Spain with the Canary Islands, France with its overseas
territories ...) maps through the city in the event's key; a city not listed here leaves the zone
unknown rather than guessed. Zones are IANA names, so daylight saving and historical changes
(Kazakhstan's move to UTC+5 in March 2024, Mexico's end of DST in 2022) come from the tz database.
"""
from __future__ import annotations

import re

# One civil zone (or one zone covering every event city in the table).
IOC_ZONE = {
    "AND": "Europe/Andorra", "ARG": "America/Argentina/Buenos_Aires", "AUT": "Europe/Vienna",
    "AZE": "Asia/Baku", "BEL": "Europe/Brussels", "BIH": "Europe/Sarajevo", "BOL": "America/La_Paz",
    "BRN": "Asia/Bahrain", "BUL": "Europe/Sofia", "CGO": "Africa/Brazzaville", "CHI": "America/Santiago",
    "CHN": "Asia/Shanghai", "CIV": "Africa/Abidjan", "COL": "America/Bogota", "CRO": "Europe/Zagreb",
    "CZE": "Europe/Prague", "DOM": "America/Santo_Domingo", "ECU": "America/Guayaquil", "EGY": "Africa/Cairo",
    "EST": "Europe/Tallinn", "FIN": "Europe/Helsinki", "GBR": "Europe/London", "GEO": "Asia/Tbilisi",
    "GER": "Europe/Berlin", "GRE": "Europe/Athens", "HKG": "Asia/Hong_Kong", "HUN": "Europe/Budapest",
    "IND": "Asia/Kolkata", "IRL": "Europe/Dublin", "ISR": "Asia/Jerusalem", "ITA": "Europe/Rome",
    "JPN": "Asia/Tokyo", "KOR": "Asia/Seoul", "KSA": "Asia/Riyadh", "LAT": "Europe/Riga",
    "LTU": "Europe/Vilnius", "LUX": "Europe/Luxembourg", "MAR": "Africa/Casablanca", "MAS": "Asia/Kuala_Lumpur",
    "MDA": "Europe/Chisinau", "MKD": "Europe/Skopje", "MON": "Europe/Monaco", "NED": "Europe/Amsterdam",
    "NZL": "Pacific/Auckland", "PAK": "Asia/Karachi", "PAN": "America/Panama", "PAR": "America/Asuncion",
    "PER": "America/Lima", "PHI": "Asia/Manila", "POL": "Europe/Warsaw", "POR": "Europe/Lisbon",
    "PUR": "America/Puerto_Rico", "QAT": "Asia/Qatar", "ROU": "Europe/Bucharest", "RSA": "Africa/Johannesburg",
    "RWA": "Africa/Kigali", "SGP": "Asia/Singapore", "SLO": "Europe/Ljubljana", "SMR": "Europe/San_Marino",
    "SRB": "Europe/Belgrade", "SUI": "Europe/Zurich", "SVK": "Europe/Bratislava", "SWE": "Europe/Stockholm",
    "THA": "Asia/Bangkok", "TPE": "Asia/Taipei", "TUN": "Africa/Tunis", "TUR": "Europe/Istanbul",
    "UAE": "Asia/Dubai", "UKR": "Europe/Kyiv", "URU": "America/Montevideo", "UZB": "Asia/Tashkent",
    "VIE": "Asia/Ho_Chi_Minh",
}

# Countries whose events span zones: (regex on the event key, zone), first match wins. Event keys are
# stage4_country.event_key(): lower-case ASCII, digits removed ('winston salem ch').
CITY_ZONE = {
    "USA": [
        (r"honolulu|lahaina|maui", "Pacific/Honolulu"),
        (r"phoenix|tempe", "America/Phoenix"),
        (r"aptos|carlsbad|indian wells|napa|newport beach|palo alto|sacramento|san diego|san francisco|"
         r"san jose|stanford|stockton|tiburon|fairfield|las vegas", "America/Los_Angeles"),
        (r"austin|baton rouge|champaign|chicago|dallas|fort worth|houston|irving|lincoln|little rock|memphis|"
         r"san antonio|sioux falls|tyler|waco|winnetka", "America/Chicago"),
        (r"ann arbor|bloomfield hills|midland", "America/Detroit"),
        (r"indianapolis|brownsburg", "America/Indiana/Indianapolis"),
        (r"atlanta|binghamton|bradenton|cary|charleston|charlottesville|cincinnati|cleveland|columbus|concord|"
         r"delray beach|knoxville|lexington|miami|new haven|new york|us open|newport|orlando|rome|sarasota|"
         r"savannah|sumter|tallahassee|washington|winston salem", "America/New_York"),
    ],
    "CAN": [
        (r"vancouver", "America/Vancouver"),
        (r"calgary", "America/Edmonton"),
        (r"winnipeg", "America/Winnipeg"),
        (r"toronto|montreal|canada masters|gatineau|granby|drummondville|quebec|rimouski", "America/Toronto"),
    ],
    "MEX": [
        (r"cancun", "America/Cancun"),
        (r"los cabos", "America/Mazatlan"),
        (r"monterrey", "America/Monterrey"),
        (r"merida", "America/Merida"),
        (r"puerto vallarta", "America/Bahia_Banderas"),
        (r"acapulco|aguascalientes|cuernavaca|guadalajara|leon|manzanillo|metepec|mexico city|morelia|morelos|"
         r"puebla|queretaro|san luis potosi|tampico", "America/Mexico_City"),
    ],
    "AUS": [
        (r"brisbane", "Australia/Brisbane"),
        (r"adelaide|playford|west lakes|happy valley", "Australia/Adelaide"),
        (r"hobart|launceston|burnie", "Australia/Hobart"),
        (r"sydney|canberra", "Australia/Sydney"),
        (r"australian open|melbourne|gippsland|grampians|great ocean road|murray river|phillip island|"
         r"yarra valley|traralgon|bendigo", "Australia/Melbourne"),
    ],
    "BRA": [
        (r"salvador|sauipe", "America/Bahia"),
        (r"rio de janeiro|sao paulo|campinas|curitiba|florianopolis|blumenau|itajai|porto alegre|potro alegre|"
         r"sao leopoldo|santos|sao jose do rio preto|piracicaba|brasilia|rio quente|challenger tour finals",
         "America/Sao_Paulo"),
    ],
    "KAZ": [(r"almaty|astana|nur sultan|shymkent", "Asia/Almaty")],
    "RUS": [
        (r"tyumen", "Asia/Yekaterinburg"),
        (r"moscow|st petersburg|kazan", "Europe/Moscow"),
    ],
    "ESP": [
        (r"las palmas|maspalomas|tenerife", "Atlantic/Canary"),
        (r".", "Europe/Madrid"),
    ],
    "FRA": [
        (r"noumea", "Pacific/Noumea"),
        (r"reunion", "Indian/Reunion"),
        (r"le gosier", "America/Guadeloupe"),
        (r".", "Europe/Paris"),
    ],
}


def zone_for(country, event_key: str) -> str | None:
    """IANA zone of an event in ``country`` (IOC code) whose key is ``event_key``; None if unknowable."""
    if not isinstance(country, str) or not country:
        return None
    rules = CITY_ZONE.get(country)
    if rules is None:
        return IOC_ZONE.get(country)
    for pattern, zone in rules:
        if re.search(pattern, event_key or ""):
            return zone
    return None
