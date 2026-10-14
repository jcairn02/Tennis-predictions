"""Venue time zones for the sources-C linker (link_sources_c.py): a UTC start becomes a local match day only through these.

Hand-made tables, kept deliberately narrow (inference, not provider data):
    COUNTRY_TZ   IOC code -> one IANA zone, for countries whose tennis venues share one zone. A few countries with
                 overseas or island zones (ESP, POR, FRA, CHI, ECU, NZL) are given their mainland zone; their island
                 and overseas venues are in CITY_TZ, and a venue the tables cannot place is a mainland one. The error
                 left is the Canaries' or Azores' one hour, which moves a match day only for a match starting
                 within an hour of midnight.
    MULTI_ZONE   countries spanning several zones (USA, CAN, AUS, BRA, MEX, RUS, KAZ, INA): only a city in CITY_TZ
                 places them; otherwise the venue zone is unknown and the caller keeps the UTC day.
    CITY_TZ      (IOC, normalised city) -> zone: every multi-zone venue the sources named, and the island and
                 overseas exceptions.
    COUNTRY_NAMES  country names as the sources write them ("Great Britain", "USA", "Korea Republic") -> IOC.
Zones come from the IANA database through zoneinfo (package tzdata), so daylight saving is applied by date.
"""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from zoneinfo import ZoneInfo

COUNTRY_TZ = {
    "ALB": "Europe/Tirane", "ALG": "Africa/Algiers", "AND": "Europe/Andorra", "ANG": "Africa/Luanda",
    "ARG": "America/Argentina/Buenos_Aires", "ARM": "Asia/Yerevan", "ARU": "America/Aruba", "AUT": "Europe/Vienna",
    "AZE": "Asia/Baku", "BAH": "America/Nassau", "BAN": "Asia/Dhaka", "BAR": "America/Barbados", "BEL": "Europe/Brussels",
    "BEN": "Africa/Porto-Novo", "BER": "Atlantic/Bermuda", "BIH": "Europe/Sarajevo", "BLR": "Europe/Minsk",
    "BOL": "America/La_Paz", "BOT": "Africa/Gaborone", "BRN": "Asia/Bahrain", "BRU": "Asia/Brunei", "BUL": "Europe/Sofia",
    "BUR": "Africa/Ouagadougou", "CAM": "Asia/Phnom_Penh", "CGO": "Africa/Brazzaville", "CHI": "America/Santiago",
    "CHN": "Asia/Shanghai", "CIV": "Africa/Abidjan", "CMR": "Africa/Douala", "COL": "America/Bogota",
    "CRC": "America/Costa_Rica", "CRO": "Europe/Zagreb", "CUB": "America/Havana", "CYP": "Asia/Nicosia",
    "CZE": "Europe/Prague", "DEN": "Europe/Copenhagen", "DOM": "America/Santo_Domingo", "ECU": "America/Guayaquil",
    "EGY": "Africa/Cairo", "ESA": "America/El_Salvador", "ESP": "Europe/Madrid", "EST": "Europe/Tallinn",
    "ETH": "Africa/Addis_Ababa", "FIJ": "Pacific/Fiji", "FIN": "Europe/Helsinki", "FRA": "Europe/Paris",
    "GAB": "Africa/Libreville", "GBR": "Europe/London", "GEO": "Asia/Tbilisi", "GER": "Europe/Berlin",
    "GHA": "Africa/Accra", "GRE": "Europe/Athens", "GUA": "America/Guatemala", "GUD": "America/Guadeloupe",
    "GUM": "Pacific/Guam", "HAI": "America/Port-au-Prince", "HKG": "Asia/Hong_Kong", "HON": "America/Tegucigalpa",
    "HUN": "Europe/Budapest", "IND": "Asia/Kolkata", "IRI": "Asia/Tehran", "IRL": "Europe/Dublin", "IRQ": "Asia/Baghdad",
    "ISL": "Atlantic/Reykjavik", "ISR": "Asia/Jerusalem", "ITA": "Europe/Rome", "JAM": "America/Jamaica",
    "JOR": "Asia/Amman", "JPN": "Asia/Tokyo", "KEN": "Africa/Nairobi", "KGZ": "Asia/Bishkek", "KOR": "Asia/Seoul",
    "KOS": "Europe/Belgrade", "KSA": "Asia/Riyadh", "KUW": "Asia/Kuwait", "LAO": "Asia/Vientiane", "LAT": "Europe/Riga",
    "LBN": "Asia/Beirut", "LIB": "Asia/Beirut", "LIE": "Europe/Vaduz", "LTU": "Europe/Vilnius", "LUX": "Europe/Luxembourg",
    "MAC": "Asia/Macau", "MAD": "Indian/Antananarivo", "MAR": "Africa/Casablanca", "MAS": "Asia/Kuala_Lumpur",
    "MDA": "Europe/Chisinau", "MKD": "Europe/Skopje", "MLT": "Europe/Malta", "MNE": "Europe/Podgorica",
    "MON": "Europe/Monaco", "MRI": "Indian/Mauritius", "MYA": "Asia/Yangon", "NAM": "Africa/Windhoek",
    "NCA": "America/Managua", "NCL": "Pacific/Noumea", "NED": "Europe/Amsterdam", "NEP": "Asia/Kathmandu",
    "NGR": "Africa/Lagos", "NOR": "Europe/Oslo", "NZL": "Pacific/Auckland", "OMA": "Asia/Muscat", "PAK": "Asia/Karachi",
    "PAN": "America/Panama", "PAR": "America/Asuncion", "PER": "America/Lima", "PHI": "Asia/Manila",
    "POL": "Europe/Warsaw", "POR": "Europe/Lisbon", "PUR": "America/Puerto_Rico", "QAT": "Asia/Qatar",
    "REU": "Indian/Reunion", "ROU": "Europe/Bucharest", "RSA": "Africa/Johannesburg", "RWA": "Africa/Kigali",
    "SEN": "Africa/Dakar", "SGP": "Asia/Singapore", "SLO": "Europe/Ljubljana", "SMR": "Europe/San_Marino",
    "SRB": "Europe/Belgrade", "SRI": "Asia/Colombo", "SUI": "Europe/Zurich", "SVK": "Europe/Bratislava",
    "SWE": "Europe/Stockholm", "SYR": "Asia/Damascus", "TAN": "Africa/Dar_es_Salaam", "THA": "Asia/Bangkok",
    "TJK": "Asia/Dushanbe", "TKM": "Asia/Ashgabat", "TOG": "Africa/Lome", "TPE": "Asia/Taipei",
    "TTO": "America/Port_of_Spain", "TUN": "Africa/Tunis", "TUR": "Europe/Istanbul", "UAE": "Asia/Dubai",
    "UGA": "Africa/Kampala", "UKR": "Europe/Kyiv", "URU": "America/Montevideo", "UZB": "Asia/Tashkent",
    "VEN": "America/Caracas", "VIE": "Asia/Ho_Chi_Minh", "ZAM": "Africa/Lusaka", "ZIM": "Africa/Harare",
    # ISO codes some sources write for the same countries
    "SVN": "Europe/Ljubljana", "PRT": "Europe/Lisbon", "URY": "America/Montevideo", "PRY": "America/Asuncion",
    "BHR": "Asia/Bahrain", "SAU": "Asia/Riyadh", "CHL": "America/Santiago", "DEU": "Europe/Berlin",
    "NLD": "Europe/Amsterdam", "CHE": "Europe/Zurich", "GRC": "Europe/Athens", "HRV": "Europe/Zagreb",
    "DNK": "Europe/Copenhagen", "BGR": "Europe/Sofia", "IDN": None, "ARE": "Asia/Dubai",
}
MULTI_ZONE = {"USA", "CAN", "AUS", "BRA", "MEX", "RUS", "KAZ", "INA", "IDN"}

_CITY = {
    "USA": {
        "America/New_York": "new york;flushing meadows;flushing;queens;washington;washington dc;charleston;miami;"
                            "miami gardens;key biscayne;delray beach;boca raton;orlando;lake nona;tampa;sarasota;"
                            "bradenton;naples;fort lauderdale;plantation;weston;palm coast;vero beach;jacksonville;"
                            "ponte vedra beach;ponte vedra;gainesville;tallahassee;wesley chapel;lakewood ranch;"
                            "st petersburg;saint petersburg;atlanta;rome;macon;savannah;winston salem;charlotte;cary;"
                            "raleigh;greensboro;columbus;cincinnati;mason;cleveland;akron;lexington;louisville;"
                            "indianapolis;midland;detroit;ann arbor;newport;new haven;concord;boston;albany;"
                            "philadelphia;pittsburgh;baltimore;spartanburg;sumter;greenville;hilton head;"
                            "hilton head island;knoxville;chattanooga;princeton;stamford;fairfield;hartford;buffalo;"
                            "rochester;syracuse;richmond;norfolk;virginia beach;charlottesville;williamsburg;durham;"
                            "chapel hill;asheville;wilmington;boynton beach;coral gables;sunrise;pompano beach;"
                            "west palm beach;wellington;st augustine;daytona beach;ocala;lakeland;clearwater;largo;"
                            "dunedin;amelia island;columbia;augusta;athens;east lansing;college park;new york city;"
                            "south orange;mahwah;manhasset;port washington;forest hills;east hampton;orange park;"
                            "bethesda;mclean;reston;vienna;fort myers;bonita springs;sanibel;marco island;"
                            "palm beach gardens;jupiter;stuart;tequesta;the villages;winter park;longwood;"
                            "altamonte springs;kissimmee;celebration;daytona;new smyrna beach;tybee island;"
                            "hollywood;aventura;north miami beach;doral;homestead;key west;dothan;bloomfield hills;"
                            "brownsburg;binghamton;notre dame;south bend;carmel in;fishers;west lafayette;"
                            "kalamazoo;grand rapids;lansing;ithaca;new canaan;hamden;storrs;amherst;"
                            "williamstown;pinehurst;wake forest",
        "America/Chicago": "chicago;houston;dallas;fort worth;austin;san antonio;waco;college station;lubbock;"
                           "corpus christi;harlingen;mcallen;memphis;nashville;tulsa;oklahoma city;little rock;"
                           "kansas city;saint louis;st louis;champaign;edwardsville;evanston;winnetka;lake forest;"
                           "shreveport;new orleans;baton rouge;mobile;tupelo;starkville;oxford;huntsville;tuscaloosa;"
                           "auburn;pensacola;des moines;iowa city;omaha;lincoln;minneapolis;milwaukee;madison;"
                           "sioux falls;fargo;wichita;lawrence;springfield;peoria;decatur;plano;frisco;irving;"
                           "arlington;the woodlands;katy;sugar land;beaumont;birmingham;denton;mcKinney;mckinney;"
                           "allen;rockwall;round rock;georgetown;san marcos;new braunfels;tyler;longview;amarillo;"
                           "abilene;midland tx;odessa;laredo;brownsville;rio grande valley;fayetteville;"
                           "bentonville;rogers;conway;jonesboro;murfreesboro;franklin;brentwood;clarksville;"
                           "cookeville;hattiesburg;jackson;gulfport;biloxi;lafayette;lake charles;monroe;"
                           "stillwater;norman;edmond;broken arrow;manhattan;topeka;overland park;leawood;columbia mo;"
                           "joplin;st joseph;cedar rapids;ames;dubuque;davenport;bloomington;normal;urbana;"
                           "carbondale;belleville;naperville;schaumburg;northbrook;highland park;glenview;"
                           "deerfield;hinsdale;oak brook;green bay;appleton;la crosse;eau claire;rochester mn;"
                           "duluth;st paul;saint paul;bismarck;sioux city;grand forks",
        "America/Denver": "denver;aspen;vail;boulder;colorado springs;salt lake city;boise;albuquerque;santa fe;"
                          "el paso;billings;cheyenne;laramie;park city;provo;ogden;fort collins;greenwood village;"
                          "englewood;littleton;castle rock;highlands ranch;lakewood;golden;sun valley;ketchum;"
                          "bozeman;missoula;rapid city;grand junction;steamboat springs;telluride;durango",
        "America/Phoenix": "phoenix;scottsdale;tucson;mesa;tempe;glendale;surprise;chandler;gilbert;peoria az;"
                           "paradise valley;oro valley;sedona;flagstaff",
        "America/Los_Angeles": "los angeles;indian wells;palm springs;palm desert;rancho mirage;la quinta;san diego;"
                               "carlsbad;la jolla;rancho santa fe;stanford;palo alto;san jose;san francisco;berkeley;"
                               "oakland;sacramento;fresno;bakersfield;tiburon;aptos;calabasas;newport beach;irvine;"
                               "laguna niguel;laguna beach;malibu;santa barbara;ojai;claremont;costa mesa;seattle;"
                               "portland;eugene;las vegas;reno;spokane;sunnyvale;citrus heights;napa;granite bay;"
                               "carson;pasadena;santa monica;beverly hills;west hollywood;manhattan beach;"
                               "redondo beach;torrance;long beach;anaheim;fullerton;mission viejo;san clemente;"
                               "coronado;del mar;encinitas;oceanside;escondido;temecula;riverside;thousand oaks;"
                               "westlake village;ventura;santa cruz;monterey;pebble beach;carmel;walnut creek;"
                               "danville;pleasanton;fremont;santa clara;los gatos;saratoga;cupertino;menlo park;"
                               "redwood city;san mateo;burlingame;mill valley;sausalito;sonoma;santa rosa;davis;"
                               "rocklin;roseville;folsom;stockton;modesto;visalia;san luis obispo;santa maria;"
                               "bellevue;kirkland;redmond;tacoma;olympia;vancouver wa;salem;bend;henderson;"
                               "summerlin;lake tahoe;incline village;truckee;yountville;rolling hills estates",
        "Pacific/Honolulu": "honolulu;waikoloa;maui;lahaina;kona;kapalua;wailea;kauai;lihue;hilo;oahu",
        "America/Anchorage": "anchorage;fairbanks",
    },
    "CAN": {
        "America/Toronto": "toronto;montreal;granby;quebec;quebec city;gatineau;ottawa;saguenay;drummondville;"
                           "sherbrooke;rimouski;repentigny;kitchener;waterloo;london;burlington;mississauga;oakville;"
                           "niagara;niagara falls;hamilton;markham;richmond hill;vaughan;thornhill;laval;longueuil;"
                           "blainville;terrebonne;trois rivieres;levis;chicoutimi",
        "America/Vancouver": "vancouver;victoria;kelowna;west vancouver;north vancouver;burnaby;richmond;surrey;"
                             "whistler;nanaimo;penticton;kamloops",
        "America/Edmonton": "calgary;edmonton;red deer;lethbridge;banff;canmore",
        "America/Winnipeg": "winnipeg;brandon",
        "America/Regina": "saskatoon;regina",
        "America/Halifax": "halifax;moncton;fredericton;charlottetown",
        "America/St_Johns": "st johns",
    },
    "AUS": {
        "Australia/Melbourne": "melbourne;traralgon;bendigo;mildura;shepparton;ballarat;geelong;mornington;frankston;"
                               "melbourne park;kooyong;albert park;warrnambool;wodonga;bundoora;"
                               "mornington peninsula;latrobe valley",
        "Australia/Sydney": "sydney;canberra;wollongong;newcastle;port macquarie;tamworth;wagga wagga;albury;"
                            "coffs harbour;bathurst;orange;dubbo;lismore;armidale;homebush;olympic park;"
                            "sydney olympic park;penrith;parramatta;central coast;gosford;nowra;queanbeyan",
        "Australia/Brisbane": "brisbane;gold coast;cairns;townsville;mackay;bundaberg;toowoomba;caloundra;"
                              "sunshine coast;rockhampton;maryborough;ipswich;kooralbyn;hervey bay;gladstone;"
                              "noosa;southport;surfers paradise;tennyson;pat rafter arena",
        "Australia/Adelaide": "adelaide;mount gambier;whyalla;port pirie;memorial drive;playford;playford city",
        "Australia/Perth": "perth;kalgoorlie;bunbury;busselton;mandurah;geraldton",
        "Australia/Hobart": "hobart;launceston;burnie;devonport",
        "Australia/Darwin": "darwin;alice springs",
    },
    "BRA": {
        "America/Sao_Paulo": "sao paulo;rio de janeiro;florianopolis;curitiba;porto alegre;belo horizonte;campinas;"
                             "brasilia;santos;sao jose dos campos;ribeirao preto;guaruja;londrina;maringa;cascavel;"
                             "foz do iguacu;blumenau;joinville;itajai;criciuma;caxias do sul;novo hamburgo;"
                             "santa maria;uberlandia;goiania;barueri;sao leopoldo;piracicaba;sorocaba;"
                             "jaragua do sul;balneario camboriu;camboriu;santo andre;sao bernardo do campo;"
                             "mogi das cruzes;campos do jordao;itu;indaiatuba;jundiai;sao carlos;araraquara;"
                             "bauru;marilia;presidente prudente;rio claro;limeira;americana;atibaia;bragança paulista;"
                             "braganca paulista;vitoria;vila velha;juiz de fora;pocos de caldas;niteroi;"
                             "petropolis;teresopolis;buzios;angra dos reis;anapolis;pelotas;passo fundo;"
                             "chapeco;lages;tubarao;itapema;bombinhas;porto belo;guaratingueta",
        "America/Bahia": "salvador;costa do sauipe;sauipe;ilheus;porto seguro;praia do forte;feira de santana",
        "America/Recife": "recife;joao pessoa;natal;maceio;aracaju;campina grande",
        "America/Fortaleza": "fortaleza;sao luis;teresina;belem",
        "America/Campo_Grande": "campo grande",
        "America/Cuiaba": "cuiaba",
        "America/Manaus": "manaus",
    },
    "MEX": {
        "America/Mexico_City": "mexico city;ciudad de mexico;guadalajara;acapulco;puerto vallarta;san luis potosi;"
                               "queretaro;leon;morelia;cuernavaca;puebla;aguascalientes;irapuato;celaya;metepec;"
                               "toluca;zapopan;oaxaca;veracruz;huatulco;ixtapa;zihuatanejo;pachuca;tlaxcala;"
                               "san miguel de allende;guanajuato;durango;zacatecas;colima;manzanillo;villahermosa;"
                               "tuxtla gutierrez;xalapa;tlalnepantla;naucalpan;nuevo vallarta;nayarit",
        "America/Monterrey": "monterrey;tampico;saltillo;san pedro garza garcia;torreon;nuevo laredo;reynosa;"
                             "ciudad victoria",
        "America/Merida": "merida;campeche",
        "America/Cancun": "cancun;playa del carmen;cozumel;tulum;chetumal",
        "America/Mazatlan": "los cabos;cabo san lucas;san jose del cabo;mazatlan;la paz;culiacan;tepic",
        "America/Tijuana": "tijuana;mexicali;ensenada",
        "America/Chihuahua": "chihuahua",
        "America/Hermosillo": "hermosillo",
        "America/Matamoros": "matamoros",
    },
    "RUS": {
        "Europe/Moscow": "moscow;st petersburg;saint petersburg;kazan;sochi;nizhny novgorod;voronezh;krasnodar;"
                         "rostov;rostov on don;kursk;yaroslavl;tula;kaluga;vologda;cherepovets;kislovodsk;"
                         "pyatigorsk;belgorod;lipetsk;tver;smolensk;ryazan;vladimir;ivanovo;kostroma;"
                         "makhachkala;anapa;gelendzhik;novorossiysk;stavropol",
        "Europe/Samara": "samara;tolyatti;togliatti;izhevsk",
        "Asia/Yekaterinburg": "yekaterinburg;ekaterinburg;ufa;chelyabinsk;perm;tyumen;orenburg",
        "Asia/Omsk": "omsk",
        "Asia/Novosibirsk": "novosibirsk",
        "Asia/Krasnoyarsk": "krasnoyarsk",
        "Asia/Irkutsk": "irkutsk",
        "Asia/Vladivostok": "vladivostok;khabarovsk",
        "Europe/Kaliningrad": "kaliningrad",
        "Europe/Volgograd": "volgograd",
        "Europe/Saratov": "saratov",
    },
    "KAZ": {
        "Asia/Almaty": "almaty;astana;nur sultan;shymkent;karaganda;kokshetau;pavlodar;ust kamenogorsk;taraz;"
                       "kyzylorda;turkestan;burabay;shchuchinsk",
        "Asia/Aqtobe": "aktobe;aqtobe",
        "Asia/Atyrau": "atyrau",
        "Asia/Oral": "uralsk;oral",
        "Asia/Qostanay": "kostanay;qostanay",
        "Asia/Aqtau": "aktau;aqtau",
    },
    "INA": {
        "Asia/Jakarta": "jakarta;bandung;surabaya;semarang;yogyakarta;malang;solo;surakarta;medan;palembang;"
                        "tangerang;bekasi;bogor;depok",
        "Asia/Makassar": "bali;denpasar;nusa dua;makassar;balikpapan;kuta;sanur;jimbaran",
        "Asia/Jayapura": "jayapura",
    },
    # island and overseas exceptions to a country's mainland zone
    "ESP": {"Atlantic/Canary": "gran canaria;las palmas;las palmas de gran canaria;maspalomas;tenerife;"
                               "santa cruz de tenerife;lanzarote;puerto de la cruz;fuerteventura;la palma;arona;"
                               "adeje;costa adeje;telde;san bartolome de tirajana;playa del ingles;puerto del carmen;"
                               "corralejo;los realejos;la laguna;san cristobal de la laguna;arrecife;tias;"
                               "meloneras;costa teguise;teguise;puerto de mogan;mogan"},
    "POR": {"Atlantic/Azores": "azores;ponta delgada;terceira;angra do heroismo",
            "Atlantic/Madeira": "madeira;funchal"},
    "FRA": {"Pacific/Noumea": "noumea;nouvelle caledonie;new caledonia",
            "Indian/Reunion": "reunion;saint denis de la reunion;saint pierre de la reunion;le port;le tampon",
            "America/Guadeloupe": "guadeloupe;le gosier;gosier;pointe a pitre;petit bourg;baie mahault;"
                                  "saint francois",
            "America/Martinique": "martinique;fort de france;le lamentin;schoelcher",
            "Pacific/Tahiti": "tahiti;papeete",
            "America/Cayenne": "cayenne;french guiana",
            "Indian/Mayotte": "mayotte;mamoudzou"},
    "CHI": {"Pacific/Easter": "easter island;hanga roa"},
    "ECU": {"Pacific/Galapagos": "galapagos"},
}
CITY_TZ: dict[tuple[str, str], str] = {}
for _ioc, _zones in _CITY.items():
    for _zone, _cities in _zones.items():
        for _c in _cities.split(";"):
            if _c.strip():
                CITY_TZ[(_ioc, _c.strip().lower())] = _zone
# The IOC code under which ISO-coded sources name these countries
CITY_TZ.update({("IDN", c): z for (i, c), z in list(CITY_TZ.items()) if i == "INA"})

COUNTRY_NAMES = {
    "afghanistan": "AFG", "albania": "ALB", "algeria": "ALG", "andorra": "AND", "angola": "ANG", "argentina": "ARG",
    "armenia": "ARM", "aruba": "ARU", "australia": "AUS", "austria": "AUT", "azerbaijan": "AZE", "bahamas": "BAH",
    "bahrain": "BRN", "bangladesh": "BAN", "barbados": "BAR", "belarus": "BLR", "belgium": "BEL", "benin": "BEN",
    "bermuda": "BER", "bolivia": "BOL", "bosnia and herzegovina": "BIH", "bosnia herzegovina": "BIH",
    "bosnia": "BIH", "botswana": "BOT", "brazil": "BRA", "brunei": "BRU", "bulgaria": "BUL", "burkina faso": "BUR",
    "cambodia": "CAM", "cameroon": "CMR", "canada": "CAN", "chile": "CHI", "china": "CHN", "chinese taipei": "TPE",
    "taiwan": "TPE", "colombia": "COL", "congo": "CGO", "costa rica": "CRC", "croatia": "CRO", "cuba": "CUB",
    "cyprus": "CYP", "czech republic": "CZE", "czechia": "CZE", "denmark": "DEN", "dominican republic": "DOM",
    "dominican rep": "DOM", "ecuador": "ECU", "egypt": "EGY", "el salvador": "ESA", "estonia": "EST",
    "ethiopia": "ETH", "fiji": "FIJ", "finland": "FIN", "france": "FRA", "gabon": "GAB", "georgia": "GEO",
    "germany": "GER", "ghana": "GHA", "great britain": "GBR", "united kingdom": "GBR", "uk": "GBR", "england": "GBR",
    "scotland": "GBR", "wales": "GBR", "northern ireland": "GBR", "greece": "GRE", "guadeloupe": "GUD",
    "guam": "GUM", "guatemala": "GUA", "haiti": "HAI", "honduras": "HON", "hong kong": "HKG",
    "hong kong china": "HKG", "hungary": "HUN", "iceland": "ISL", "india": "IND", "indonesia": "INA", "iran": "IRI",
    "iraq": "IRQ", "ireland": "IRL", "israel": "ISR", "italy": "ITA", "ivory coast": "CIV", "cote d ivoire": "CIV",
    "jamaica": "JAM", "japan": "JPN", "jordan": "JOR", "kazakhstan": "KAZ", "kenya": "KEN", "korea": "KOR",
    "korea republic": "KOR", "south korea": "KOR", "republic of korea": "KOR", "kosovo": "KOS", "kuwait": "KUW",
    "kyrgyzstan": "KGZ", "laos": "LAO", "latvia": "LAT", "lebanon": "LBN", "liechtenstein": "LIE",
    "lithuania": "LTU", "luxembourg": "LUX", "macau": "MAC", "macao": "MAC", "madagascar": "MAD", "malaysia": "MAS",
    "malta": "MLT", "mauritius": "MRI", "mexico": "MEX", "moldova": "MDA", "monaco": "MON", "montenegro": "MNE",
    "morocco": "MAR", "myanmar": "MYA", "namibia": "NAM", "nepal": "NEP", "netherlands": "NED", "holland": "NED",
    "new caledonia": "NCL", "new zealand": "NZL", "nicaragua": "NCA", "nigeria": "NGR", "north macedonia": "MKD",
    "macedonia": "MKD", "norway": "NOR", "oman": "OMA", "pakistan": "PAK", "panama": "PAN", "paraguay": "PAR",
    "peru": "PER", "philippines": "PHI", "poland": "POL", "portugal": "POR", "puerto rico": "PUR", "qatar": "QAT",
    "reunion": "REU", "romania": "ROU", "russia": "RUS", "russian federation": "RUS", "rwanda": "RWA",
    "san marino": "SMR", "saudi arabia": "KSA", "senegal": "SEN", "serbia": "SRB", "singapore": "SGP",
    "slovakia": "SVK", "slovak republic": "SVK", "slovenia": "SLO", "south africa": "RSA", "spain": "ESP",
    "sri lanka": "SRI", "sweden": "SWE", "switzerland": "SUI", "syria": "SYR", "tajikistan": "TJK",
    "tanzania": "TAN", "thailand": "THA", "togo": "TOG", "trinidad and tobago": "TTO", "tunisia": "TUN",
    "turkey": "TUR", "turkiye": "TUR", "turkmenistan": "TKM", "uganda": "UGA", "ukraine": "UKR",
    "united arab emirates": "UAE", "uae": "UAE", "usa": "USA", "united states": "USA", "u s a": "USA",
    "potugal": "POR",  # TDI's spelling of Porto's country
    "united states of america": "USA", "us": "USA", "uruguay": "URU", "uzbekistan": "UZB", "venezuela": "VEN",
    "vietnam": "VIE", "viet nam": "VIE", "zambia": "ZAM", "zimbabwe": "ZIM",
}
# two-letter US state and Canadian province codes, as the WTA calendar writes them ("CA, UNITED STATES")
US_STATES = {
    "America/New_York": "CT DC DE FL GA MA MD ME MI NC NH NJ NY OH PA RI SC VA VT WV",
    "America/Chicago": "AL AR IA IL KS LA MN MO MS ND NE OK SD TN TX WI",
    "America/Denver": "CO MT NM UT WY ID",
    "America/Phoenix": "AZ",
    "America/Los_Angeles": "CA NV OR WA",
    "Pacific/Honolulu": "HI",
}
STATE_TZ = {s: z for z, states in US_STATES.items() for s in states.split()}
# Indiana and Kentucky are split; their tennis venues (Indianapolis, Lexington, Louisville) are Eastern
STATE_TZ.update({"IN": "America/New_York", "KY": "America/New_York"})


def norm_place(text) -> str:
    """Lower-case ASCII words: 'Nürnberg' -> 'nurnberg', 'Saint-Malo' -> 'saint malo', 'St. Petersburg' -> 'st petersburg'."""
    if text is None:
        return ""
    s = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s.replace("'", ""))
    return " ".join(s.split())


def country_code(text) -> str | None:
    """An IOC code from a country name or code as a source writes it; None when it cannot be read."""
    s = norm_place(text)
    if not s:
        return None
    if s in COUNTRY_NAMES:
        return COUNTRY_NAMES[s]
    up = s.upper().replace(" ", "")
    if len(up) == 3 and (up in COUNTRY_TZ or up in MULTI_ZONE):
        return up
    if s.endswith("united states") or s.startswith("united states") or s.startswith("usa"):
        return "USA"
    return None


def zone_for(country: str | None, city: str | None = None) -> str | None:
    """The venue's IANA zone from its IOC country and city; None when they do not settle it."""
    if not country:
        return None
    c = norm_place(city)
    if c:
        hit = CITY_TZ.get((country, c))
        if hit:
            return hit
        # 'saint petersburg' / 'st petersburg', 'nur-sultan' / 'nur sultan' are normalised already; try the first word
        # pair and the bare first word for names such as 'new york city' or 'indian wells california'
        words = c.split()
        for k in (3, 2, 1):
            if len(words) > k:
                hit = CITY_TZ.get((country, " ".join(words[:k])))
                if hit:
                    return hit
    if country in MULTI_ZONE:
        return None
    return COUNTRY_TZ.get(country)


@lru_cache(maxsize=None)
def zoneinfo(name: str) -> ZoneInfo:
    return ZoneInfo(name)
