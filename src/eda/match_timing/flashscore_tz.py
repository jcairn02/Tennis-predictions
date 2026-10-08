"""Event country and time zone for linked matches (link_flashscore.py), so a UTC start time becomes the local
calendar date of the match.

Countries are IOC codes, as in Stage 4's stage4_event_country.csv. Flashscore's own country field (KH in its
head-to-head feeds, ``country`` on head-to-head pages) is a country name ("USA", "United Kingdom",
"South Korea"); FS_COUNTRY maps it to the IOC code. The ITF tournament ids of Stage 0 carry the country
("2023-M-ITF-THA-9A-2023").

Zones (IANA names, read with Python's zoneinfo, which applies each zone's own history of offsets and summer
time):
    * one zone for a country that has one (ZONE);
    * a country spanning several zones (MULTI) needs the city, read from the tournament name (Flashscore's
      "M15 Sumter 2", Stage 0's "Cary CH"): CITY_ZONE. Flashscore's North American ITF names often end in a
      state or province code ("W15 Lakewood, CA"), which settles the zone (US_STATE, CA_PROVINCE; US_SPLIT lists
      the venues of states split between two zones). An unknown city gives no zone (the UTC date is kept);
    * a country with one mainland zone and outlying territories that host events (Spain's Canary Islands,
      Portugal's Madeira and Azores, France's overseas departments, Chile's and Ecuador's islands) uses the
      mainland zone unless the city is a listed exception (EXCEPTIONS).
China is one zone by law (Asia/Shanghai, UTC+8) and its venues keep Beijing time, so it is treated as
single-zone. Kazakhstan had two zones until 1 March 2024 (one since); its cities are looked up and zoneinfo
applies the change.
The city tables were written by hand on 5 Oct 2026 from the tournament names in the data; a venue whose zone was
not certain (a city name shared by two states, with no state code) is left out.
"""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

# ------------------------------------------------------------------------------------------------
# Countries

ZONE = {   # IOC code -> the country's one zone
    "ALB": "Europe/Tirane", "ALG": "Africa/Algiers", "AND": "Europe/Andorra", "ANG": "Africa/Luanda",
    "ARG": "America/Argentina/Buenos_Aires", "ARM": "Asia/Yerevan", "ARU": "America/Aruba", "AUT": "Europe/Vienna",
    "AZE": "Asia/Baku", "BAH": "America/Nassau", "BRN": "Asia/Bahrain", "BAN": "Asia/Dhaka", "BAR": "America/Barbados",
    "BLR": "Europe/Minsk", "BEL": "Europe/Brussels", "BEN": "Africa/Porto-Novo", "BER": "Atlantic/Bermuda",
    "BOL": "America/La_Paz", "BIH": "Europe/Sarajevo", "BOT": "Africa/Gaborone", "BUL": "Europe/Sofia",
    "BDI": "Africa/Bujumbura", "CAM": "Asia/Phnom_Penh", "CMR": "Africa/Douala", "CHN": "Asia/Shanghai",
    "TPE": "Asia/Taipei", "COL": "America/Bogota", "CGO": "Africa/Brazzaville", "CRC": "America/Costa_Rica",
    "CRO": "Europe/Zagreb", "CUB": "America/Havana", "CUW": "America/Curacao", "CYP": "Asia/Nicosia",
    "CZE": "Europe/Prague", "DEN": "Europe/Copenhagen", "DOM": "America/Santo_Domingo", "EGY": "Africa/Cairo",
    "ESA": "America/El_Salvador", "EST": "Europe/Tallinn", "FIN": "Europe/Helsinki", "GEO": "Asia/Tbilisi",
    "GER": "Europe/Berlin", "GHA": "Africa/Accra", "GBR": "Europe/London", "GRE": "Europe/Athens",
    "GUA": "America/Guatemala", "HAI": "America/Port-au-Prince", "HON": "America/Tegucigalpa",
    "HKG": "Asia/Hong_Kong", "HUN": "Europe/Budapest", "ISL": "Atlantic/Reykjavik", "IND": "Asia/Kolkata",
    "IRI": "Asia/Tehran", "IRQ": "Asia/Baghdad", "IRL": "Europe/Dublin", "ISR": "Asia/Jerusalem", "ITA": "Europe/Rome",
    "CIV": "Africa/Abidjan", "JAM": "America/Jamaica", "JPN": "Asia/Tokyo", "JOR": "Asia/Amman", "KEN": "Africa/Nairobi",
    "KOS": "Europe/Belgrade", "KUW": "Asia/Kuwait", "KGZ": "Asia/Bishkek", "LAT": "Europe/Riga", "LBN": "Asia/Beirut",
    "LIE": "Europe/Vaduz", "LTU": "Europe/Vilnius", "LUX": "Europe/Luxembourg", "MAC": "Asia/Macau",
    "MKD": "Europe/Skopje", "MAD": "Indian/Antananarivo", "MAS": "Asia/Kuala_Lumpur", "MLT": "Europe/Malta",
    "MRI": "Indian/Mauritius", "MDA": "Europe/Chisinau", "MON": "Europe/Monaco", "MGL": "Asia/Ulaanbaatar",
    "MNE": "Europe/Podgorica", "MAR": "Africa/Casablanca", "MOZ": "Africa/Maputo", "NAM": "Africa/Windhoek",
    "NEP": "Asia/Kathmandu", "NED": "Europe/Amsterdam", "NZL": "Pacific/Auckland", "NCA": "America/Managua",
    "NGR": "Africa/Lagos", "NOR": "Europe/Oslo", "OMA": "Asia/Muscat", "PAK": "Asia/Karachi", "PAN": "America/Panama",
    "PAR": "America/Asuncion", "PER": "America/Lima", "PHI": "Asia/Manila", "POL": "Europe/Warsaw",
    "PUR": "America/Puerto_Rico", "QAT": "Asia/Qatar", "ROU": "Europe/Bucharest", "RWA": "Africa/Kigali",
    "SMR": "Europe/San_Marino", "KSA": "Asia/Riyadh", "SEN": "Africa/Dakar", "SRB": "Europe/Belgrade",
    "SGP": "Asia/Singapore", "SVK": "Europe/Bratislava", "SLO": "Europe/Ljubljana", "RSA": "Africa/Johannesburg",
    "KOR": "Asia/Seoul", "SRI": "Asia/Colombo", "SUD": "Africa/Khartoum", "SWE": "Europe/Stockholm",
    "SUI": "Europe/Zurich", "SYR": "Asia/Damascus", "TJK": "Asia/Dushanbe", "TAN": "Africa/Dar_es_Salaam",
    "THA": "Asia/Bangkok", "TOG": "Africa/Lome", "TTO": "America/Port_of_Spain", "TUN": "Africa/Tunis",
    "TUR": "Europe/Istanbul", "TKM": "Asia/Ashgabat", "UGA": "Africa/Kampala", "UKR": "Europe/Kyiv",
    "UAE": "Asia/Dubai", "URU": "America/Montevideo", "UZB": "Asia/Tashkent", "VEN": "America/Caracas",
    "VIE": "Asia/Ho_Chi_Minh", "ZAM": "Africa/Lusaka", "ZIM": "Africa/Harare", "LBA": "Africa/Tripoli",
    "ETH": "Africa/Addis_Ababa", "MLI": "Africa/Bamako", "BUR": "Africa/Ouagadougou", "GAB": "Africa/Libreville",
    "SEY": "Indian/Mahe", "MDV": "Indian/Maldives", "BRU": "Asia/Brunei", "LAO": "Asia/Vientiane",
    "MYA": "Asia/Yangon", "FIJ": "Pacific/Fiji", "SAM": "Pacific/Apia", "GUM": "Pacific/Guam",
    "ISV": "America/St_Thomas", "IVB": "America/Tortola", "CAY": "America/Cayman", "LCA": "America/St_Lucia",
    "GRN": "America/Grenada", "VIN": "America/St_Vincent", "ANT": "America/Antigua", "SKN": "America/St_Kitts",
    "DMA": "America/Dominica", "SUR": "America/Paramaribo", "GUY": "America/Guyana", "BIZ": "America/Belize",
    "DJI": "Africa/Djibouti",
    # overseas territories that Flashscore lists as countries of their own
    "GLP": "America/Guadeloupe", "MTQ": "America/Martinique", "REU": "Indian/Reunion", "NCL": "Pacific/Noumea",
    "PYF": "Pacific/Tahiti", "GUF": "America/Cayenne", "MYT": "Indian/Mayotte", "GIB": "Europe/Gibraltar",
    "FRO": "Atlantic/Faroe",
    # codes in Stage 0's ITF tournament ids that are not current IOC codes
    "GUD": "America/Guadeloupe", "MRN": "America/Martinique", "LIB": "Asia/Beirut",
}
# territories compared as their state when Stage 0's and Flashscore's countries are checked against each other
SAME_COUNTRY = {"GLP": "FRA", "MTQ": "FRA", "REU": "FRA", "NCL": "FRA", "PYF": "FRA", "GUF": "FRA", "MYT": "FRA",
                "GUD": "FRA", "MRN": "FRA", "LIB": "LBN", "GIB": "GBR"}


def same_country(a, b) -> bool | None:
    """Whether two IOC codes name the same country (territories as their state); None if either is missing."""
    if not isinstance(a, str) or not isinstance(b, str) or not a or not b:
        return None
    return SAME_COUNTRY.get(a, a) == SAME_COUNTRY.get(b, b)
MULTI = {"USA", "CAN", "AUS", "RUS", "BRA", "MEX", "KAZ", "INA"}
MAINLAND = {"ESP": "Europe/Madrid", "POR": "Europe/Lisbon", "FRA": "Europe/Paris", "CHI": "America/Santiago",
            "ECU": "America/Guayaquil"}

FS_COUNTRY = {   # Flashscore country name -> IOC code
    "albania": "ALB", "algeria": "ALG", "andorra": "AND", "angola": "ANG", "argentina": "ARG", "armenia": "ARM",
    "aruba": "ARU", "australia": "AUS", "austria": "AUT", "azerbaijan": "AZE", "bahamas": "BAH", "bahrain": "BRN",
    "bangladesh": "BAN", "barbados": "BAR", "belarus": "BLR", "belgium": "BEL", "benin": "BEN", "bermuda": "BER",
    "bolivia": "BOL", "bosnia and herzegovina": "BIH", "botswana": "BOT", "brazil": "BRA", "bulgaria": "BUL",
    "burundi": "BDI", "cambodia": "CAM", "cameroon": "CMR", "canada": "CAN", "chile": "CHI", "china": "CHN",
    "chinese taipei": "TPE", "taiwan": "TPE", "colombia": "COL", "congo": "CGO", "republic of the congo": "CGO",
    "costa rica": "CRC", "croatia": "CRO", "cuba": "CUB", "curacao": "CUW", "cyprus": "CYP", "czech republic": "CZE",
    "czechia": "CZE", "denmark": "DEN", "dominican republic": "DOM", "ecuador": "ECU", "egypt": "EGY",
    "el salvador": "ESA", "estonia": "EST", "finland": "FIN", "france": "FRA", "georgia": "GEO", "germany": "GER",
    "ghana": "GHA", "united kingdom": "GBR", "great britain": "GBR", "england": "GBR", "scotland": "GBR",
    "wales": "GBR", "northern ireland": "GBR", "greece": "GRE", "guatemala": "GUA", "haiti": "HAI", "honduras": "HON",
    "hong kong": "HKG", "hungary": "HUN", "iceland": "ISL", "india": "IND", "indonesia": "INA", "iran": "IRI",
    "iraq": "IRQ", "ireland": "IRL", "israel": "ISR", "italy": "ITA", "ivory coast": "CIV", "cote d ivoire": "CIV",
    "jamaica": "JAM", "japan": "JPN", "jordan": "JOR", "kazakhstan": "KAZ", "kenya": "KEN", "kosovo": "KOS",
    "kuwait": "KUW", "kyrgyzstan": "KGZ", "latvia": "LAT", "lebanon": "LBN", "liechtenstein": "LIE",
    "lithuania": "LTU", "luxembourg": "LUX", "macao": "MAC", "macau": "MAC", "north macedonia": "MKD",
    "macedonia": "MKD", "madagascar": "MAD", "malaysia": "MAS", "malta": "MLT", "mauritius": "MRI", "mexico": "MEX",
    "moldova": "MDA", "monaco": "MON", "mongolia": "MGL", "montenegro": "MNE", "morocco": "MAR", "mozambique": "MOZ",
    "namibia": "NAM", "nepal": "NEP", "netherlands": "NED", "new zealand": "NZL", "nicaragua": "NCA",
    "nigeria": "NGR", "norway": "NOR", "oman": "OMA", "pakistan": "PAK", "panama": "PAN", "paraguay": "PAR",
    "peru": "PER", "philippines": "PHI", "poland": "POL", "portugal": "POR", "puerto rico": "PUR", "qatar": "QAT",
    "romania": "ROU", "russia": "RUS", "rwanda": "RWA", "san marino": "SMR", "saudi arabia": "KSA", "senegal": "SEN",
    "serbia": "SRB", "singapore": "SGP", "slovakia": "SVK", "slovenia": "SLO", "south africa": "RSA",
    "south korea": "KOR", "korea republic": "KOR", "spain": "ESP", "sri lanka": "SRI", "sudan": "SUD",
    "sweden": "SWE", "switzerland": "SUI", "syria": "SYR", "tajikistan": "TJK", "tanzania": "TAN", "thailand": "THA",
    "togo": "TOG", "trinidad and tobago": "TTO", "tunisia": "TUN", "turkey": "TUR", "turkiye": "TUR",
    "turkmenistan": "TKM", "uganda": "UGA", "ukraine": "UKR", "united arab emirates": "UAE", "usa": "USA",
    "united states": "USA", "uruguay": "URU", "uzbekistan": "UZB", "venezuela": "VEN", "vietnam": "VIE",
    "zambia": "ZAM", "zimbabwe": "ZIM", "libya": "LBA", "ethiopia": "ETH", "mali": "MLI", "burkina faso": "BUR",
    "gabon": "GAB", "seychelles": "SEY", "maldives": "MDV", "brunei": "BRU", "laos": "LAO", "myanmar": "MYA",
    "fiji": "FIJ", "samoa": "SAM", "guam": "GUM", "us virgin islands": "ISV", "british virgin islands": "IVB",
    "cayman islands": "CAY", "saint lucia": "LCA", "grenada": "GRN", "suriname": "SUR", "guyana": "GUY",
    "belize": "BIZ", "djibouti": "DJI", "guadeloupe": "GLP", "martinique": "MTQ", "reunion": "REU",
    "new caledonia": "NCL", "french polynesia": "PYF", "tahiti": "PYF", "french guiana": "GUF", "mayotte": "MYT",
    "gibraltar": "GIB", "faroe islands": "FRO",
}


def fold(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", s.replace("&", " and ")).split())


@lru_cache(maxsize=None)
def ioc_of_fs_country(name) -> str | None:
    """Flashscore's country name as an IOC code; None for "World", "Europe", "Asia" and unknown names."""
    if not isinstance(name, str) or not name.strip():
        return None
    return FS_COUNTRY.get(fold(name))


ITF_ID = re.compile(r"^\d{4}-[MW]-[A-Z0-9]+-([A-Z]{3})-")
ITF_ID_CODES = {"SIN": "SGP"}


@lru_cache(maxsize=None)
def itf_country(tournament_id) -> str | None:
    """The three-letter country of an ITF tournament id in Stage 0 ("2010-M-FU-BRA-34A-2009" -> BRA)."""
    m = ITF_ID.match(str(tournament_id or ""))
    return ITF_ID_CODES.get(m.group(1), m.group(1)) if m else None


# ------------------------------------------------------------------------------------------------
# Cities

LEVEL_PREFIX = re.compile(r"^(?:[MWJ]\d{2,3}(?:\+H)?|ITF|ATP|WTA|CH|Challenger)\s+", re.I)
TRAILING = re.compile(r"(?:\s+(?:\d+k?|[ivx]+|h|ch|challenger|125|wta|atp|itf|masters|open|cup|classic|trophy|"
                      r"championships?|international|indoor|indoors|tennis|men|women|ladies|pro|series|"
                      r"qualification|qualifying))+$")
REGION = re.compile(r"(?:,\s*|\s)([A-Z]{2})(?=\s|$|\$|\d|,)")


@lru_cache(maxsize=None)
def city_key(name) -> str:
    """A tournament name reduced to its city: level prefix, region code, edition number and generic words
    removed ("W15 Monastir 11" -> "monastir", "W75+H Vero Beach, FL 2" -> "vero beach", "Cary CH" -> "cary",
    "Indian Wells Masters" -> "indian wells", "US Open" -> "us", "Australian Open" -> "australian")."""
    t = LEVEL_PREFIX.sub("", str(name or "").strip())
    t = re.sub(r"\(.*?\)", " ", t).split(",")[0].split(" - ")[0]
    t = fold(re.sub(r"\$\s*\d+\s*[kK]?", " ", t.replace("+H", " ")))
    prev = None
    while prev != t:
        prev = t
        t = TRAILING.sub("", t).strip()
    return t


@lru_cache(maxsize=None)
def region_of(name) -> str | None:
    """The two-letter state or province code of a North American name: Flashscore's "W15 Lakewood, CA",
    Stage 0's "Troy AL $25K" or "Macon GA $50K". Only codes of US states or Canadian provinces count."""
    for m in REGION.finditer(str(name or "")):
        if m.group(1) in US_STATE or m.group(1) in CA_PROVINCE:
            return m.group(1)
    return None


NY, CHI, DEN, PHX, LA, DET, IND = ("America/New_York", "America/Chicago", "America/Denver", "America/Phoenix",
                                   "America/Los_Angeles", "America/Detroit", "America/Indiana/Indianapolis")
US_STATE = {   # the state's zone where one zone covers its tennis venues; US_SPLIT lists the exceptions
    "AL": CHI, "AK": "America/Anchorage", "AZ": PHX, "AR": CHI, "CA": LA, "CO": DEN, "CT": NY, "DE": NY, "DC": NY,
    "FL": NY, "GA": NY, "HI": "Pacific/Honolulu", "IL": CHI, "IN": IND, "IA": CHI, "KS": CHI, "KY": NY, "LA": CHI,
    "ME": NY, "MD": NY, "MA": NY, "MI": DET, "MN": CHI, "MS": CHI, "MO": CHI, "MT": DEN, "NE": CHI, "NV": LA, "NH": NY,
    "NJ": NY, "NM": DEN, "NY": NY, "NC": NY, "ND": CHI, "OH": NY, "OK": CHI, "OR": LA, "PA": NY, "RI": NY, "SC": NY,
    "SD": CHI, "TN": CHI, "TX": CHI, "UT": DEN, "VT": NY, "VA": NY, "WA": LA, "WV": NY, "WI": CHI, "WY": DEN,
    "PR": "America/Puerto_Rico"}
US_SPLIT = {   # (city, state) where the state's usual zone is wrong
    ("pensacola", "FL"): CHI, ("niceville", "FL"): CHI, ("fort walton beach", "FL"): CHI, ("panama city", "FL"): CHI,
    ("destin", "FL"): CHI, ("evansville", "IN"): CHI, ("knoxville", "TN"): NY, ("chattanooga", "TN"): NY,
    ("johnson city", "TN"): NY, ("el paso", "TX"): DEN, ("bowling green", "KY"): CHI, ("paducah", "KY"): CHI,
    ("rapid city", "SD"): DEN}
CA_PROVINCE = {"BC": "America/Vancouver", "AB": "America/Edmonton", "SK": "America/Regina", "MB": "America/Winnipeg",
               "ON": "America/Toronto", "QC": "America/Toronto", "NB": "America/Moncton", "NS": "America/Halifax",
               "PE": "America/Halifax", "NL": "America/St_Johns"}


def _zones(spec: dict[str, str]) -> dict[str, str]:
    out = {}
    for zone, cities in spec.items():
        for c in cities.split(";"):
            c = c.strip()
            if c:
                assert c not in out, c
                out[c] = zone
    return out


CITY_ZONE: dict[str, dict[str, str]] = {   # IOC -> city key -> zone, for the countries in MULTI
    "USA": _zones({
        NY: "us;miami;cincinnati;charleston;washington;winston salem;charlottesville;tallahassee;orlando;"
            "naples;lexington;delray beach;columbus;newport;atlanta;sarasota;vero beach;boca raton;knoxville;savannah;"
            "cleveland;sunrise;new haven;cary;palm coast;orange park;weston;pittsburgh;binghamton;plantation;macon;"
            "indian harbour beach;ithaca;tampa;sumter;bonita springs;buffalo;rome;rome us;new york;bethany beach;"
            "innisbrook;landisville;zephyrhills;daytona beach;osprey;williamsburg;hilton head island;hilton head;"
            "bradenton;rock hill;wesley chapel;clemson;gainesville;louisville;palm harbor;south bend;captiva island;"
            "bronx;raleigh;charlotte;amelia island;boynton;boynton beach;port st lucie;ponte vedra;ponte vedra beach;"
            "boston;clearwater;nicholasville;credit one bank invitational;ashland;key biscayne;fort lauderdale;"
            "jupiter;west palm beach;lakeland;ocala;jacksonville;durham;greensboro;wilmington;norfolk;"
            "virginia beach;richmond;baltimore;philadelphia;princeton;albany;syracuse;hartford;dayton;akron;toledo;"
            "mason",
        CHI: "houston;champaign;dallas;austin;memphis;little rock;pensacola;wichita;tyler;tulsa;harlingen;"
             "edwardsville;norman;chicago;decatur;winnetka;waco;pelham;fayetteville;dothan;birmingham;niceville;"
             "jackson;irving;huntsville;evansville;lincoln;godfrey;mansfield;southaven;lubbock;sioux falls;edmond;"
             "fort worth;spring;oklahoma city;baton rouge;brownsville;joplin;new braunfels;kansas;kansas city;"
             "iowa city;grapevine;fort walton beach;san antonio;mobile;montgomery;tuscaloosa;starkville;"
             "hattiesburg;new orleans;shreveport;college station;corpus christi;mcallen;st louis;omaha;des moines;"
             "minneapolis;madison;milwaukee;peoria;nashville;murfreesboro;clarksville",
        DEN: "albuquerque;colorado springs;el paso;denver;boulder;salt lake city;las cruces",
        PHX: "phoenix;tucson;surprise;scottsdale;tempe;mesa;chandler",
        LA: "indian wells;san diego;las vegas;los angeles;tiburon;rancho santa fe;sacramento;bakersfield;aptos;"
            "san jose;calabasas;fairfield;stanford;claremont;redding;berkeley;templeton;stockton;newport beach;"
            "costa mesa;arcadia;laguna niguel;carlsbad;irvine;fountain valley;long beach;malibu;san rafael;yakima;"
            "napa;rancho mirage;san francisco;carson;chico;burlingame;ojai;kirkland;seattle;palm springs;la jolla;"
            "oakland;fresno;santa barbara;pasadena;beverly hills;el cajon;pleasanton",
        DET: "east lansing;bloomfield hills;ann arbor;midland;grand rapids;kalamazoo;detroit",
        IND: "indianapolis;carmel;west lafayette",
        "Pacific/Honolulu": "honolulu;maui hawaii;maui;hawaii;waikoloa;kona",
    }),
    "CAN": _zones({
        "America/Toronto": "toronto;montreal;granby;drummondville;quebec city;quebec;saguenay;rimouski;gatineau;"
                           "sherbrooke;trois rivieres;laval;waterloo;saint augustin;saint augustin de desmaures;"
                           "brossard;victoriaville;markham;mississauga;ottawa;kitchener;oakville;repentigny;"
                           "chicoutimi;blainville;terrebonne",
        "America/Vancouver": "vancouver;victoria;kelowna;west vancouver;burnaby",
        "America/Edmonton": "calgary;edmonton",
        "America/Regina": "saskatoon;regina",
        "America/Winnipeg": "winnipeg",
        "America/Moncton": "fredericton;moncton;saint john",
        "America/Halifax": "halifax",
    }),
    "AUS": _zones({
        "Australia/Melbourne": "australian;melbourne;traralgon;bendigo;swan hill;mildura;kooyong;wodonga;geelong;"
                               "the summer set;mornington;ballarat;shepparton;warrnambool;sale;morwell;frankston",
        "Australia/Sydney": "sydney;canberra;tweed heads;wagga wagga;tamworth;albury;wollongong;newcastle;orange;"
                            "bathurst;port macquarie;coffs harbour",
        "Australia/Brisbane": "brisbane;cairns;caloundra;ipswich;bundaberg;carrara;gold coast;rockhampton;"
                              "toowoomba;townsville;mackay;sunshine coast;kawana;noosa",
        "Australia/Adelaide": "adelaide;playford;happy valley;port pirie;west lakes adelaide;west lakes;salisbury;"
                              "world tennis challenge;a day at the drive;mount gambier;glenelg",
        "Australia/Hobart": "hobart;burnie;launceston;devonport",
        "Australia/Perth": "perth;esperance;kalgoorlie;margaret river;busselton;mandurah",
        "Australia/Darwin": "darwin;alice springs",
    }),
    "RUS": _zones({
        "Europe/Moscow": "moscow;st petersburg;saint petersburg;kazan;penza;yoshkar ola;saransk;lermontov;khimki;"
                         "sochi;krasnodar;rostov;voronezh;nizhny novgorod;tula;kursk;nalchik;vladikavkaz;"
                         "makhachkala;yaroslavl;tver;kaluga;ryazan;lipetsk;belgorod;cheboksary;kirov",
        "Europe/Samara": "samara;togliatti;tolyatti;izhevsk",
        "Asia/Yekaterinburg": "tyumen;khanty mansiysk;yekaterinburg;ekaterinburg;chelyabinsk;ufa;perm;orenburg;"
                              "surgut;magnitogorsk",
        "Asia/Novokuznetsk": "novokuznetsk;kemerovo",
        "Asia/Novosibirsk": "novosibirsk",
        "Asia/Omsk": "omsk",
        "Asia/Krasnoyarsk": "krasnoyarsk",
        "Asia/Irkutsk": "irkutsk",
        "Asia/Vladivostok": "vladivostok;khabarovsk",
        "Europe/Kaliningrad": "kaliningrad",
    }),
    "BRA": _zones({
        "America/Sao_Paulo": "sao paulo;rio de janeiro;campinas;florianopolis;santos;brasilia;curitiba;porto alegre;"
                             "sao leopoldo;piracicaba;ribeirao preto;blumenau;itajai;mogi das cruzes;vacaria;"
                             "campos do jordao;maringa;sao jose do rio preto;challenger tour finals;lajeado;"
                             "sao jose dos campos;joinville;criciuma;rio quente;rio claro;belo horizonte;londrina;leme;"
                             "sao joao da boa vista;rio do sul;aparecida de goiania;americana;gramado;barueri;"
                             "santa cruz do sul;riviera de sao lourenco;jundiai;caxias do sul;juiz de fora;"
                             "santa maria;foz do iguacu;blumenau gaspar;pelotas;lorena;sao jose do rio prieto;"
                             "divinopolis;lins;lages;fernandopolis;olimpia;goiania;guaruja;sorocaba;bauru;"
                             "uberlandia;vitoria;niteroi;itu",
        "America/Belem": "belem",
        "America/Bahia": "costa do sauipe;feira de santana;salvador;salvador de bahia",
        "America/Recife": "recife",
        "America/Maceio": "maceio",
        "America/Fortaleza": "fortaleza;sao luis;natal;joao pessoa;teresina",
        "America/Cuiaba": "cuiaba",
        "America/Campo_Grande": "campo grande",
        "America/Manaus": "manaus",
    }),
    "MEX": _zones({
        "America/Mexico_City": "acapulco;huamantla;guadalajara;zapopan;san luis potosi;mexico city;morelos;leon;"
                               "puerto vallarta;morelia;manzanillo;puebla;irapuato;celaya;metepec;xalapa;veracruz;"
                               "cordoba;aguascalientes;ixtapa;tehuacan;villahermosa;tabasco;queretaro;zacatecas;"
                               "cuernavaca;toluca;oaxaca;pachuca;tlaxcala",
        "America/Cancun": "cancun;quintana roo;playa del carmen;cozumel",
        "America/Monterrey": "monterrey;tampico;victoria;ciudad victoria;saltillo;san pedro garza garcia",
        "America/Merida": "merida",
        "America/Mazatlan": "los cabos;mazatlan;cabo san lucas",
        "America/Chihuahua": "chihuahua",
        "America/Tijuana": "tijuana;ensenada",
        "America/Hermosillo": "hermosillo",
    }),
    "KAZ": _zones({
        "Asia/Almaty": "astana;nur sultan;shymkent;almaty;ust kamenogorsk;oskemen;karaganda;taraz;pavlodar",
        "Asia/Aqtobe": "aktobe",
        "Asia/Aqtau": "aktau",
        "Asia/Atyrau": "atyrau",
        "Asia/Oral": "oral;uralsk",
        "Asia/Qostanay": "kostanay",
        "Asia/Qyzylorda": "kyzylorda",
    }),
    "INA": _zones({
        "Asia/Jakarta": "jakarta;bandung;surabaya;semarang;yogyakarta;palembang;medan",
        "Asia/Makassar": "bali;balikpapan;tarakan;denpasar;makassar;nusa dua",
        "Asia/Jayapura": "jayapura",
    }),
}
EXCEPTIONS: dict[str, dict[str, str]] = {   # IOC -> city key -> zone, for MAINLAND countries' outlying territories
    "ESP": _zones({"Atlantic/Canary": "tenerife;telde;gran canaria;las palmas de gran canaria;las palmas;"
                                      "puerto de la cruz;san bartolome de tirajana;san bartolome;puerto del carmen;"
                                      "maspalomas;gran canaria maspalomas;maspalomas gran canaria;lanzarote;"
                                      "fuerteventura;arona;adeje;costa adeje;santa cruz de tenerife;la laguna;"
                                      "meloneras;playa de las americas"}),
    "POR": _zones({"Atlantic/Madeira": "funchal;madeira", "Atlantic/Azores": "ponta delgada;azores"}),
    "FRA": _zones({"America/Guadeloupe": "petit bourg;gosier;le gosier;saint martin;baie mahault;guadeloupe",
                   "America/Martinique": "le lamentin;fort de france;martinique",
                   "America/Cayenne": "cayenne", "Indian/Reunion": "le tampon;reunion",
                   "Pacific/Noumea": "noumea;new caledonia", "Pacific/Tahiti": "papeete;tahiti"}),
    "CHI": _zones({"America/Punta_Arenas": "punta arenas", "Pacific/Easter": "easter island"}),
    "ECU": _zones({"Pacific/Galapagos": "galapagos"}),
}


FIXED_VENUE = {   # (Stage 0 tournament name, season) -> zone, for events whose country the tables cannot give
    ("olympics", 2012): "Europe/London", ("london olympics", 2012): "Europe/London",
    ("olympics", 2016): "America/Sao_Paulo", ("rio olympics", 2016): "America/Sao_Paulo",
    ("olympics", 2021): "Asia/Tokyo", ("tokyo olympics", 2021): "Asia/Tokyo",
    ("olympics", 2024): "Europe/Paris", ("paris olympics", 2024): "Europe/Paris",
    ("laver cup", 2017): "Europe/Prague", ("laver cup", 2018): "America/Chicago", ("laver cup", 2019): "Europe/Zurich",
    ("laver cup", 2021): "America/New_York", ("laver cup", 2022): "Europe/London",
    ("laver cup", 2023): "America/Vancouver", ("laver cup", 2024): "Europe/Berlin",
    ("laver cup", 2025): "America/Los_Angeles",
    ("atp cup", 2021): "Australia/Melbourne", ("atp cup", 2022): "Australia/Sydney",
}


def fixed_venue(name, season) -> str | None:
    """The zone of a one-venue event of a given season (Olympics, Laver Cup, the 2021-22 ATP Cup)."""
    try:
        return FIXED_VENUE.get((fold(re.sub(r"\d+", " ", str(name or ""))), int(season)))
    except (TypeError, ValueError):
        return None


def zone_of(ioc, names: list) -> tuple[str | None, str]:
    """(zone, basis) for an event country and its tournament names (tried in order)."""
    if not isinstance(ioc, str) or not ioc:
        return None, "country unknown"
    if ioc in ZONE:
        return ZONE[ioc], "country"
    places = []
    for n in names:
        if isinstance(n, str) and n:
            city, region = city_key(n), region_of(n)
            if region and city.endswith(" " + region.lower()):
                city = city[:-3]
            places.append((city, region))
    if ioc in MAINLAND:
        for city, _ in places:
            if city in EXCEPTIONS.get(ioc, {}):
                return EXCEPTIONS[ioc][city], "city (outlying territory)"
        return MAINLAND[ioc], "country (mainland)"
    if ioc in MULTI:
        table = CITY_ZONE.get(ioc, {})
        for city, region in places:
            if ioc == "USA" and region in US_STATE:
                return US_SPLIT.get((city, region), US_STATE[region]), "city (state code)"
            if ioc == "CAN" and region in CA_PROVINCE:
                return CA_PROVINCE[region], "city (province code)"
            if city in table:
                return table[city], "city"
        return None, f"city not known ({ioc}, several zones)"
    return None, f"country without a zone in the table ({ioc})"
