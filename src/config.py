"""
Configuration module for Kommunal Finansiell Riskindikator (KRI).

Contains all API endpoints, weights, design constants, and Swedish labels.
All variable names and comments in English.
All user-facing strings (SWEDISH_LABELS) in Swedish.
"""

from typing import Dict, List

# =============================================================================
# API BASE URLS
# =============================================================================

SCB_API_BASE = "https://api.scb.se/OV0104/v1/doris/sv/ssd/"
KOLADA_API_BASE = "https://api.kolada.se/v2/"

# =============================================================================
# SCB API PATHS (relative to SCB_API_BASE)
# =============================================================================

SCB_API_PATHS = {
    # Variable 1: Long-term debt (balance sheet)
    "balance_sheet": "OE/OE0107/OE0107G/BalansKnN",

    # Variable 3 & 4: Population by age (for dependency ratio and population growth)
    "population": "BE/BE0101/BE0101A/BefolkningNy",

    # Variable 5: Tax base strength
    "tax_base": "OE/OE0101/SkatteKraft",

    # Supplementary: Income statement (annual result)
    "income_statement": "OE/OE0107/OE0107G/ResultKn",

    # Supplementary: Municipal tax rate
    "tax_rate": "OE/OE0101/Komskatter",
}

# Full API URLs for convenience
SCB_API_URLS = {
    key: f"{SCB_API_BASE}{path}"
    for key, path in SCB_API_PATHS.items()
}

# =============================================================================
# KOLADA API ENDPOINTS
# =============================================================================

KOLADA_ENDPOINTS = {
    "kpi_search": "kpi",
    "data": "data/kpi",
    "municipality": "municipality",
}

# Known Kolada KPI IDs for unemployment
KOLADA_UNEMPLOYMENT_KPIS = [
    "N00914",  # Openly unemployed 16-64 years, share (%)
    "N00945",  # Total unemployment 16-64 years, share (%)
]

# =============================================================================
# TIME PERIOD
# =============================================================================

START_YEAR = 2010
END_YEAR = 2024

# For population growth calculation (5-year rolling), need data from 2005
POPULATION_START_YEAR = 2005

# List of all years for API queries
YEARS = list(range(START_YEAR, END_YEAR + 1))
YEARS_STR = [str(y) for y in YEARS]

# Extended years for population (needed for 5-year growth calc)
POPULATION_YEARS = list(range(POPULATION_START_YEAR, END_YEAR + 1))
POPULATION_YEARS_STR = [str(y) for y in POPULATION_YEARS]

# =============================================================================
# KRI WEIGHTS
# =============================================================================

WEIGHTS: Dict[str, float] = {
    "debt": 0.25,
    "unemployment": 0.25,
    "dependency_ratio": 0.20,
    "population_growth": 0.15,
    "tax_base": 0.15,
}

# Verify weights sum to 1.0
assert abs(sum(WEIGHTS.values()) - 1.0) < 0.001, "Weights must sum to 1.0"

# Variable direction: True = high value means high risk
# Variables where high = low risk are inverted (multiplied by -1) before z-score
VARIABLE_DIRECTION = {
    "debt": True,              # High debt = high risk
    "unemployment": True,      # High unemployment = high risk
    "dependency_ratio": True,  # High dependency = high risk
    "population_growth": False,  # High growth = LOW risk (inverted)
    "tax_base": False,         # High tax base = LOW risk (inverted)
}

# =============================================================================
# DESIGN CONSTANTS (Colors)
# =============================================================================

COLORS = {
    # Primary palette
    "primary": "#1B2A4A",       # Dark blue
    "secondary": "#4A6FA5",     # Steel blue
    "accent": "#C4A35A",        # Gold

    # Risk colors
    "low_risk": "#2E7D5B",      # Green
    "medium_risk": "#D4A03C",   # Amber
    "high_risk": "#B94A48",     # Red

    # UI colors
    "background": "#F7F8FA",
    "text_primary": "#1A1A2E",
    "text_secondary": "#6B7280",
    "grid_lines": "#E5E7EB",
    "white": "#FFFFFF",
}

# Risk class color mapping (Swedish labels)
RISK_CLASS_COLORS = {
    "Låg": COLORS["low_risk"],
    "Medel": COLORS["medium_risk"],
    "Hög": COLORS["high_risk"],
}

# =============================================================================
# TYPOGRAPHY
# =============================================================================

TYPOGRAPHY = {
    "font_family": "Source Sans Pro",
    "h1_size": "28px",
    "h2_size": "22px",
    "body_size": "16px",
    "kpi_size": "36px",
    "footnote_size": "12px",
}

# =============================================================================
# SWEDISH LABELS (All user-facing text)
# =============================================================================

SWEDISH_LABELS: Dict[str, str] = {
    # Core variables
    "debt_per_capita": "Skuld per capita",
    "unemployment": "Arbetslöshet",
    "dependency_ratio": "Försörjningskvot",
    "population_growth": "Befolkningstillväxt",
    "tax_base": "Skattekraft",

    # KRI output
    "kri_score": "KRI Poäng",
    "rank": "Rang",
    "risk_class": "Riskklass",

    # Risk classes
    "low_risk": "Låg",
    "medium_risk": "Medel",
    "high_risk": "Hög",

    # General terms
    "municipality": "Kommun",
    "year": "År",
    "national_average": "Rikssnitt",
    "population": "Befolkning",

    # Supplementary variables
    "annual_result": "Årets resultat",
    "tax_rate": "Kommunalskattesats",
    "equity_ratio": "Soliditet",

    # Units
    "kr": "kr",
    "percent": "%",
    "per_capita": "per capita",
    "tkr": "tkr",

    # Page titles
    "national_overview": "Riksöversikt",
    "risk_decomposition": "Riskdekomposition",
    "municipality_analysis": "Kommunanalys",

    # KPI card titles
    "average_kri": "Genomsnittligt KRI",
    "high_risk_count": "Högrisk kommuner",
    "median_debt": "Medianskuld per capita",
    "population_change": "Befolkningsförändring",

    # Table headers
    "top_highest_risk": "Topp 15 högst risk",
    "top_lowest_risk": "Topp 15 lägst risk",
    "similar_municipalities": "10 mest liknande kommuner",

    # Sidebar labels
    "select_year": "Välj år",
    "filter_risk_class": "Filtrera riskklass",
    "select_municipality": "Välj kommun",
    "compare_municipalities": "Jämför kommuner",

    # Buttons
    "download_data": "Ladda ner data",
    "download_pdf": "Ladda ner rapport",

    # Data quality
    "data_quality": "Datakvalitet",
    "complete": "Komplett",
    "interpolated": "Interpolerad",
    "missing": "Saknas",
    "flagged": "Flaggad",

    # Chart labels
    "kri_score_axis": "KRI Poäng",
    "municipality_count": "Antal kommuner",
    "contribution": "Bidrag",

    # Messages
    "data_source": "Källa: SCB, Arbetsförmedlingen",
    "last_updated": "Senast uppdaterad",
}

# =============================================================================
# BALANCE SHEET POST CODES (for SCB BalansKnN table)
# =============================================================================

# Balance sheet item codes for extracting specific posts
BALANCE_SHEET_POSTS = {
    "long_term_liabilities": "T03K",  # Långfristiga skulder
    "total_assets": "S1TK",           # Summa tillgångar
    "equity": "T02E",                 # Eget kapital
}

# =============================================================================
# MUNICIPALITY CODES (All 290 Swedish municipalities)
# =============================================================================

# Complete list of all 290 municipality codes and names
# Format: {code: name}
MUNICIPALITIES: Dict[str, str] = {
    "0114": "Upplands Väsby",
    "0115": "Vallentuna",
    "0117": "Österåker",
    "0120": "Värmdö",
    "0123": "Järfälla",
    "0125": "Ekerö",
    "0126": "Huddinge",
    "0127": "Botkyrka",
    "0128": "Salem",
    "0136": "Haninge",
    "0138": "Tyresö",
    "0139": "Upplands-Bro",
    "0140": "Nykvarn",
    "0160": "Täby",
    "0162": "Danderyd",
    "0163": "Sollentuna",
    "0180": "Stockholm",
    "0181": "Södertälje",
    "0182": "Nacka",
    "0183": "Sundbyberg",
    "0184": "Solna",
    "0186": "Lidingö",
    "0187": "Vaxholm",
    "0188": "Norrtälje",
    "0191": "Sigtuna",
    "0192": "Nynäshamn",
    "0305": "Håbo",
    "0319": "Älvkarleby",
    "0330": "Knivsta",
    "0331": "Heby",
    "0360": "Tierp",
    "0380": "Uppsala",
    "0381": "Enköping",
    "0382": "Östhammar",
    "0428": "Vingåker",
    "0461": "Gnesta",
    "0480": "Nyköping",
    "0481": "Oxelösund",
    "0482": "Flen",
    "0483": "Katrineholm",
    "0484": "Eskilstuna",
    "0486": "Strängnäs",
    "0488": "Trosa",
    "0509": "Ödeshög",
    "0512": "Ydre",
    "0513": "Kinda",
    "0560": "Boxholm",
    "0561": "Åtvidaberg",
    "0562": "Finspång",
    "0563": "Valdemarsvik",
    "0580": "Linköping",
    "0581": "Norrköping",
    "0582": "Söderköping",
    "0583": "Motala",
    "0584": "Vadstena",
    "0586": "Mjölby",
    "0604": "Aneby",
    "0617": "Gnosjö",
    "0642": "Mullsjö",
    "0643": "Habo",
    "0662": "Gislaved",
    "0665": "Vaggeryd",
    "0680": "Jönköping",
    "0682": "Nässjö",
    "0683": "Värnamo",
    "0684": "Sävsjö",
    "0685": "Vetlanda",
    "0686": "Eksjö",
    "0687": "Tranås",
    "0760": "Uppvidinge",
    "0761": "Lessebo",
    "0763": "Tingsryd",
    "0764": "Alvesta",
    "0765": "Älmhult",
    "0767": "Markaryd",
    "0780": "Växjö",
    "0781": "Ljungby",
    "0821": "Högsby",
    "0834": "Torsås",
    "0840": "Mörbylånga",
    "0860": "Hultsfred",
    "0861": "Mönsterås",
    "0862": "Emmaboda",
    "0880": "Kalmar",
    "0881": "Nybro",
    "0882": "Oskarshamn",
    "0883": "Västervik",
    "0884": "Vimmerby",
    "0885": "Borgholm",
    "0980": "Gotland",
    "1060": "Olofström",
    "1080": "Karlskrona",
    "1081": "Ronneby",
    "1082": "Karlshamn",
    "1083": "Sölvesborg",
    "1214": "Svalöv",
    "1230": "Staffanstorp",
    "1231": "Burlöv",
    "1233": "Vellinge",
    "1256": "Östra Göinge",
    "1257": "Örkelljunga",
    "1260": "Bjuv",
    "1261": "Kävlinge",
    "1262": "Lomma",
    "1263": "Svedala",
    "1264": "Skurup",
    "1265": "Sjöbo",
    "1266": "Hörby",
    "1267": "Höör",
    "1270": "Tomelilla",
    "1272": "Bromölla",
    "1273": "Osby",
    "1275": "Perstorp",
    "1276": "Klippan",
    "1277": "Åstorp",
    "1278": "Båstad",
    "1280": "Malmö",
    "1281": "Lund",
    "1282": "Landskrona",
    "1283": "Helsingborg",
    "1284": "Höganäs",
    "1285": "Eslöv",
    "1286": "Ystad",
    "1287": "Trelleborg",
    "1290": "Kristianstad",
    "1291": "Simrishamn",
    "1292": "Ängelholm",
    "1293": "Hässleholm",
    "1315": "Hylte",
    "1380": "Halmstad",
    "1381": "Laholm",
    "1382": "Falkenberg",
    "1383": "Varberg",
    "1384": "Kungsbacka",
    "1401": "Härryda",
    "1402": "Partille",
    "1407": "Öckerö",
    "1415": "Stenungsund",
    "1419": "Tjörn",
    "1421": "Orust",
    "1427": "Sotenäs",
    "1430": "Munkedal",
    "1435": "Tanum",
    "1438": "Dals-Ed",
    "1439": "Färgelanda",
    "1440": "Ale",
    "1441": "Lerum",
    "1442": "Vårgårda",
    "1443": "Bollebygd",
    "1444": "Grästorp",
    "1445": "Essunga",
    "1446": "Karlsborg",
    "1447": "Gullspång",
    "1452": "Tranemo",
    "1460": "Bengtsfors",
    "1461": "Mellerud",
    "1462": "Lilla Edet",
    "1463": "Mark",
    "1465": "Svenljunga",
    "1466": "Herrljunga",
    "1470": "Vara",
    "1471": "Götene",
    "1472": "Tibro",
    "1473": "Töreboda",
    "1480": "Göteborg",
    "1481": "Mölndal",
    "1482": "Kungälv",
    "1484": "Lysekil",
    "1485": "Uddevalla",
    "1486": "Strömstad",
    "1487": "Vänersborg",
    "1488": "Trollhättan",
    "1489": "Alingsås",
    "1490": "Borås",
    "1491": "Ulricehamn",
    "1492": "Åmål",
    "1493": "Mariestad",
    "1494": "Lidköping",
    "1495": "Skara",
    "1496": "Skövde",
    "1497": "Hjo",
    "1498": "Tidaholm",
    "1499": "Falköping",
    "1715": "Kil",
    "1730": "Eda",
    "1737": "Torsby",
    "1760": "Storfors",
    "1761": "Hammarö",
    "1762": "Munkfors",
    "1763": "Forshaga",
    "1764": "Grums",
    "1765": "Årjäng",
    "1766": "Sunne",
    "1780": "Karlstad",
    "1781": "Kristinehamn",
    "1782": "Filipstad",
    "1783": "Hagfors",
    "1784": "Arvika",
    "1785": "Säffle",
    "1814": "Lekeberg",
    "1860": "Laxå",
    "1861": "Hallsberg",
    "1862": "Degerfors",
    "1863": "Hällefors",
    "1864": "Ljusnarsberg",
    "1880": "Örebro",
    "1881": "Kumla",
    "1882": "Askersund",
    "1883": "Karlskoga",
    "1884": "Nora",
    "1885": "Lindesberg",
    "1904": "Skinnskatteberg",
    "1907": "Surahammar",
    "1960": "Kungsör",
    "1961": "Hallstahammar",
    "1962": "Norberg",
    "1980": "Västerås",
    "1981": "Sala",
    "1982": "Fagersta",
    "1983": "Köping",
    "1984": "Arboga",
    "2021": "Vansbro",
    "2023": "Malung-Sälen",
    "2026": "Gagnef",
    "2029": "Leksand",
    "2031": "Rättvik",
    "2034": "Orsa",
    "2039": "Älvdalen",
    "2061": "Smedjebacken",
    "2062": "Mora",
    "2080": "Falun",
    "2081": "Borlänge",
    "2082": "Säter",
    "2083": "Hedemora",
    "2084": "Avesta",
    "2085": "Ludvika",
    "2101": "Ockelbo",
    "2104": "Hofors",
    "2121": "Ovanåker",
    "2132": "Nordanstig",
    "2161": "Ljusdal",
    "2180": "Gävle",
    "2181": "Sandviken",
    "2182": "Söderhamn",
    "2183": "Bollnäs",
    "2184": "Hudiksvall",
    "2260": "Ånge",
    "2262": "Timrå",
    "2280": "Härnösand",
    "2281": "Sundsvall",
    "2282": "Kramfors",
    "2283": "Sollefteå",
    "2284": "Örnsköldsvik",
    "2303": "Ragunda",
    "2305": "Bräcke",
    "2309": "Krokom",
    "2313": "Strömsund",
    "2321": "Åre",
    "2326": "Berg",
    "2361": "Härjedalen",
    "2380": "Östersund",
    "2401": "Nordmaling",
    "2403": "Bjurholm",
    "2404": "Vindeln",
    "2409": "Robertsfors",
    "2417": "Norsjö",
    "2418": "Malå",
    "2421": "Storuman",
    "2422": "Sorsele",
    "2425": "Dorotea",
    "2460": "Vännäs",
    "2462": "Vilhelmina",
    "2463": "Åsele",
    "2480": "Umeå",
    "2481": "Lycksele",
    "2482": "Skellefteå",
    "2505": "Arvidsjaur",
    "2506": "Arjeplog",
    "2510": "Jokkmokk",
    "2513": "Överkalix",
    "2514": "Kalix",
    "2518": "Övertorneå",
    "2521": "Pajala",
    "2523": "Gällivare",
    "2560": "Älvsbyn",
    "2580": "Luleå",
    "2581": "Piteå",
    "2582": "Boden",
    "2583": "Haparanda",
    "2584": "Kiruna",
}

# List of just municipality codes for API queries
MUNICIPALITY_CODES: List[str] = list(MUNICIPALITIES.keys())

# Total number of municipalities (for validation)
NUM_MUNICIPALITIES = 290

# Verify we have all 290 municipalities
assert len(MUNICIPALITIES) == NUM_MUNICIPALITIES, f"Expected {NUM_MUNICIPALITIES} municipalities, got {len(MUNICIPALITIES)}"

# =============================================================================
# SPECIAL CASE MUNICIPALITIES
# =============================================================================

# Municipalities with special handling requirements
SPECIAL_CASES = {
    "0980": {
        "name": "Gotland",
        "note": "Region Gotland has both municipal and regional responsibilities. "
                "SCB estimates 65% relates to municipal activities.",
        "adjustment_factor": 0.65,
    },
    "0330": {
        "name": "Knivsta",
        "note": "Municipality formed in 2003, separated from Uppsala. "
                "Limited historical data before 2003.",
        "formed_year": 2003,
    },
    "0331": {
        "name": "Heby",
        "note": "Changed county in 2007 (from Västmanland to Uppsala). "
                "Some time series may have breaks.",
        "county_change_year": 2007,
    },
}

# =============================================================================
# DATA CACHE SETTINGS
# =============================================================================

CACHE_DIR = "data/cache"
RAW_DIR = "data/raw"
PROCESSED_DIR = "data/processed"
GEO_DIR = "data/geo"

# Cache expiry in days
CACHE_EXPIRY_DAYS = 7

# =============================================================================
# API REQUEST SETTINGS
# =============================================================================

# Retry settings for API calls
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 2  # Exponential backoff: 1s, 2s, 4s
REQUEST_TIMEOUT = 30  # seconds

# Rate limiting (SCB API is generous but be polite)
REQUEST_DELAY = 0.5  # seconds between requests
