# sources.py
# -------------------------------------------------------------------------
# Each source is one RSS feed.
#   financial_only=True  -> a dedicated economy/business feed; keep every item.
#   financial_only=False -> a general news feed; keep only items that match the
#                           finance keywords below (cuts sport/crime/culture).
#
# VERIFIED in 2026: the two Gazeta.uz economy feeds resolve and return an
#   economy column, so the bot is useful on day one even if nothing else works.
# UNVERIFIED: the rest are the standard feed URLs for Uzbek outlets that publish
#   RSS. If one 404s or is empty, the bot SKIPS it and lists it at the bottom of
#   your daily message, so you can fix or delete the line. Adding/removing a
#   source is a one-line edit here. No code changes needed.
# -------------------------------------------------------------------------

SOURCES = [
    # --- Dedicated economy feeds (kept in full) ---
    {"name": "Gazeta.uz · Economy (EN)", "url": "https://www.gazeta.uz/en/rss/?section=economy", "financial_only": True},
    {"name": "Gazeta.uz · Economy (RU)", "url": "https://www.gazeta.uz/ru/rss/?section=economy", "financial_only": True},

    # --- General feeds (keyword-filtered to finance/economy) ---
    {"name": "Gazeta.uz · All (EN)",     "url": "https://www.gazeta.uz/en/rss/",                 "financial_only": False},
    {"name": "Kun.uz (UZ)",              "url": "https://kun.uz/uz/rss",                         "financial_only": False},
    {"name": "Kun.uz (RU)",              "url": "https://kun.uz/ru/rss",                         "financial_only": False},
    {"name": "Daryo.uz",                 "url": "https://daryo.uz/feed",                         "financial_only": False},
    {"name": "Xabar.uz",                 "url": "https://xabar.uz/rss",                          "financial_only": False},
    {"name": "UzDaily (EN)",             "url": "https://www.uzdaily.uz/en/rss",                 "financial_only": False},
    {"name": "UzReport",                 "url": "https://uzreport.news/rss",                     "financial_only": False},
    {"name": "Podrobno.uz",              "url": "https://podrobno.uz/rss/",                      "financial_only": False},
]

# Coarse pre-filter (Uzbek / Russian / English). The model does the final
# relevance call, so this list can be generous; it only needs to drop the
# obvious non-financial noise from general feeds. Match is case-insensitive
# substring on title + summary, so stems ("inflyatsiya", "инфляц") catch
# multiple word forms.
FINANCE_KEYWORDS = [
    # English
    "econom", "inflation", "gdp", "budget", "fiscal", "monetary", "deficit",
    "surplus", "tax", "vat", "duty", "tariff", "subsid", "bank", "central bank",
    "currency", "exchange rate", "soum", "som ", "uzs", "devalu", "interest rate",
    "key rate", "invest", "loan", "credit", "debt", "bond", "eurobond", "stock",
    "share", "equity", "market", "stock exchange", "trade", "export", "import",
    "remittance", "fdi", "ipo", "privati", "tender", "mortgage", "fintech",
    "crypto", "gold", "oil", "gas", "energy price", "imf", "world bank", "ebrd",
    "adb", "fitch", "moody", "s&p", "revenue", "sovereign", "treasury", "audit",
    # Russian
    "эконом", "инфляц", "ввп", "бюджет", "фискальн", "монетарн", "дефицит",
    "профицит", "налог", "ндс", "пошлин", "тариф", "субсид", "банк", "центробанк",
    "цб ", "валют", "курс", "сум", "девальвац", "ставка", "инвестиц", "кредит",
    "долг", "облигац", "еврооблигац", "акци", "рынок", "биржа", "торгов",
    "экспорт", "импорт", "перевод", "пии", "приватизац", "тендер", "ипотек",
    "финтех", "криптовалют", "золото", "нефть", "газ", "доход", "казначейств",
    # Uzbek
    "iqtisod", "inflyatsiya", "yaim", "byudjet", "fiskal", "monetar", "taqchil",
    "soliq", "qqs", "boj", "tarif", "subsidiya", "bank", "markaziy bank",
    "valyuta", "kurs", "so'm", "som", "devalvatsiya", "stavka", "investitsiya",
    "kredit", "qarz", "obligatsiya", "aksiya", "bozor", "birja", "savdo",
    "eksport", "import", "pul o'tkazma", "xususiylashtirish", "tender",
    "ipoteka", "fintex", "kriptovalyuta", "oltin", "neft", "gaz", "daromad",
]
