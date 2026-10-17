import unittest
from pockettts_app.german_norm import normalize as n

CASES = {
 "Im Wohnzimmer beträgt die Temperatur 21 Grad.": "Im Wohnzimmer beträgt die Temperatur einundzwanzig Grad.",
 "Es ist 18 Uhr 35.": "Es ist achtzehn Uhr fünfunddreißig.",
 "Es ist 18:35 Uhr.": "Es ist achtzehn Uhr fünfunddreißig.",
 "Es ist 9 Uhr.": "Es ist neun Uhr.",
 "Die Temperatur beträgt 12,5 Grad und die Luftfeuchtigkeit liegt bei 65 Prozent.": "Die Temperatur beträgt zwölf Komma fünf Grad und die Luftfeuchtigkeit liegt bei fünfundsechzig Prozent.",
 "Draußen sind 7 °C bei 65 %.": "Draußen sind sieben Grad Celsius bei fünfundsechzig Prozent.",
 "Der Verbrauch liegt bei 1.250 W.": "Der Verbrauch liegt bei eintausendzweihundertfünfzig Watt.",
 "Noch 3 Fenster sind offen.": "Noch drei Fenster sind offen.",
 "Das ist z. B. wichtig.": "Das ist zum Beispiel wichtig.",
 "Am 14.05.2026 kommt Besuch.": "Am vierzehnten Mai zweitausendsechsundzwanzig kommt Besuch.",
 "Die Waschmaschine ist fertig.": "Die Waschmaschine ist fertig.",
 "Ich habe 1 Termin gefunden.": "Ich habe einen Termin gefunden.",
 "Noch 1 Fenster ist offen.": "Noch ein Fenster ist offen.",
 "Der Wecker klingelt um 1:15 Uhr.": "Der Wecker klingelt um ein Uhr fünfzehn.",
 "am 18.10. um 09:00 Uhr": "am achtzehnten Oktober um neun Uhr",
 "Es ist 1 Grad kalt.": "Es ist ein Grad kalt.",
 "Draußen ist es 1 °C.": "Draußen ist es ein Grad Celsius.",
}
UNCHANGED = [   # normale Saetze duerfen nicht veraendert werden
 "Guten Morgen! Schön, dass du da bist.", "Welche Fenster sind aktuell geöffnet?", "Hallo, wie geht's dir?",
 "Das Licht im Flur wurde eingeschaltet.", "Die Haustür ist verriegelt; die Garage ist offen.", "Möchtest du eine weitere Benachrichtigung erhalten?",
 "Okay… ich schaue nach!",
]

class Norm(unittest.TestCase):
    def test_cases(self):
        for src, want in CASES.items():
            with self.subTest(src): self.assertEqual(n(src), want)
    def test_unchanged(self):
        for src in UNCHANGED:
            with self.subTest(src): self.assertEqual(n(src), src)
    def test_empty_and_whitespace(self):
        self.assertEqual(n(""), ""); self.assertEqual(n("  Hallo   Welt  "), "Hallo Welt")
    def test_long_text_keeps_punctuation(self):
        t = "Heute ist es sonnig. Morgen wird es regnen! Brauchst du einen Schirm, oder bleibst du lieber drinnen?"
        self.assertEqual(n(t), t)
    def test_multiple_numbers(self):
        self.assertEqual(n("Im Wohnzimmer sind 21 Grad, im Bad 24 Grad."), "Im Wohnzimmer sind einundzwanzig Grad, im Bad vierundzwanzig Grad.")

if __name__ == "__main__": unittest.main()
