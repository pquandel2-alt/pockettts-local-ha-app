"""Deutsche Textnormalisierung fuer TTS-Modelle, die Ziffern schlecht aussprechen (PocketTTS)."""
import re
from num2words import num2words

def _n(n):  # Kardinalzahl
    return num2words(int(n), lang="de")

def _dec(s):  # "12,5" / "0,75" -> "zwoelf Komma fuenf"; Nachkommastellen ziffernweise
    a, b = s.split(",")
    return f"{_n(a)} Komma " + " ".join(_n(c) for c in b)

UNITS = [  # (Regex nach Zahl, Ersatz); Reihenfolge wichtig
    (r"\s*°\s*C\b", " Grad Celsius"), (r"\s*°\s*F\b", " Grad Fahrenheit"), (r"\s*°", " Grad"),
    (r"\s*%", " Prozent"), (r"\s*km/h\b", " Kilometer pro Stunde"), (r"\s*m/s\b", " Meter pro Sekunde"),
    (r"\s*kWh\b", " Kilowattstunden"), (r"\s*kW\b", " Kilowatt"), (r"\s*W\b", " Watt"), (r"\s*V\b", " Volt"),
    (r"\s*hPa\b", " Hektopascal"), (r"\s*mm\b", " Millimeter"), (r"\s*cm\b", " Zentimeter"), (r"\s*km\b", " Kilometer"),
    (r"\s*kg\b", " Kilogramm"), (r"\s*g\b", " Gramm"), (r"\s*ml\b", " Milliliter"), (r"\s*l\b", " Liter"),
    (r"\s*€", " Euro"), (r"\s*EUR\b", " Euro"),
]
_ABK = [(r"\bz\. ?B\.", "zum Beispiel"), (r"\bd\. ?h\.", "das heißt"), (r"\bu\. ?a\.", "unter anderem"), (r"\bggf\.", "gegebenenfalls"),
        (r"\bca\.", "circa"), (r"\bbzw\.", "beziehungsweise"), (r"\busw\.", "und so weiter"), (r"\bNr\.", "Nummer"), (r"\bevtl\.", "eventuell"),
        (r"\bDr\.", "Doktor"), (r"\bProf\.", "Professor"), (r"\bStd\.", "Stunden"), (r"\bMin\.", "Minuten"), (r"\bSek\.", "Sekunden")]

def normalize(text: str) -> str:
    t = re.sub(r"\b(\d{1,3}(?:\.\d{3})+)\b(?!\.\d)", lambda m: m.group(1).replace(".", ""), text)  # Tausenderpunkte zuerst
    for pat, rep in _ABK: t = re.sub(pat, rep, t)
    # Uhrzeit "18 Uhr 35", "18:35 Uhr", "18:35", "9 Uhr 05"
    def clock(h, m): 
        h, m = int(h), int(m); return f"{'ein' if h == 1 else _n(h)} Uhr" + (f" {_n(m)}" if m else "")
    t = re.sub(r"\b([01]?\d|2[0-3])\s*Uhr\s*([0-5]\d)\b", lambda m: clock(m.group(1), m.group(2)), t)
    t = re.sub(r"\b([01]?\d|2[0-3]):([0-5]\d)(?:\s*Uhr)?\b", lambda m: clock(m.group(1), m.group(2)), t)
    # Zahl + Einheit (auch Dezimalzahlen)
    for pat, rep in UNITS:
        t = re.sub(r"(\d+,\d+)" + pat, lambda m, r=rep: _dec(m.group(1)) + r, t)
        t = re.sub(r"(\d+)" + pat, lambda m, r=rep: ("ein" if m.group(1) == "1" else _n(m.group(1))) + r, t)
    # Datum 14.05.2026 / 14.05.
    mon = ["", "Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
    def date(m):
        pre, d, mo, y = m.group(1) or "", int(m.group(2)), int(m.group(3)), m.group(4)
        if not 1 <= mo <= 12 or not 1 <= d <= 31: return m.group(0)
        o = num2words(d, lang="de", to="ordinal")
        if pre: o += "n"                                    # Dativ: "am vierzehnten Mai"
        s = f"{pre}{o} {mon[mo]}"; return s + (f" {num2words(int(y), lang='de', to='year')}" if y else "")
    t = re.sub(r"(?i)\b((?:am|vom|zum|dem|ab|bis)\s+)?(\d{1,2})\.(\d{1,2})\.(\d{4})?", date, t)
    # Dezimalzahlen, dann ganze Zahlen (inkl. Tausenderpunkt "1.250")
    t = re.sub(r"\b(\d+,\d+)\b", lambda m: _dec(m.group(1)), t)
    t = re.sub(r"\b(\d{1,3}(?:\.\d{3})+)\b", lambda m: _n(m.group(1).replace(".", "")), t)
    t = re.sub(r"(?i)\b(habe|hast|hat|haben|habt|gibt es|finde|fand)\s+1\s+(Termin|Eintrag|Kalendereintrag|Alarm|Timer|Wecker)\b", r"\1 einen \2", t)
    t = re.sub(r"\b1\b(?=\s+[A-ZÄÖÜ][a-zäöüß])", "ein", t)          # "1 Termin" -> "ein Termin" (nicht "eins Termin")
    t = re.sub(r"\b(\d+)\b", lambda m: _n(m.group(1)), t)
    return re.sub(r"[ \t]+", " ", t).strip()
