# -*- coding: utf-8 -*-
"""
Kleine Hilfsbibliothek: xlsx-Datei auf XML-Ebene bearbeiten
============================================================================
Warum nicht openpyxl? openpyxl liest Diagramme und Formen nur unvollständig
ein - beim Speichern gehen in der Rechenübersicht die Phasendiagramme und die
Prozesskette (Formen) verloren. Deshalb werden hier nur die betroffenen
Zellen, Texte und Diagrammreihen direkt im XML geändert; alles andere
(Formatierung, Formeln, Diagramme, Formen) bleibt byte-genau erhalten.
"""
import re
import zipfile
from xml.sax.saxutils import escape


def spalte_zu_zahl(sp):
    n = 0
    for ch in sp:
        n = n * 26 + ord(ch) - 64
    return n


def teile(ref):
    m = re.match(r"([A-Z]+)(\d+)$", ref)
    return m.group(1), int(m.group(2))


class Paket:
    """Alle Dateien der xlsx im Speicher (Name -> Text/Bytes)."""

    def __init__(self, pfad):
        with zipfile.ZipFile(pfad) as z:
            self.namen = z.namelist()
            self.daten = {n: z.read(n) for n in self.namen}
            self.infos = {i.filename: i for i in z.infolist()}

    def text(self, name):
        return self.daten[name].decode("utf-8")

    def setze(self, name, text):
        if name not in self.daten:
            self.namen.append(name)
        self.daten[name] = text.encode("utf-8")

    def entferne(self, name):
        self.namen.remove(name)
        del self.daten[name]

    def speichere(self, pfad):
        with zipfile.ZipFile(pfad, "w", zipfile.ZIP_DEFLATED) as z:
            for n in self.namen:
                z.writestr(n, self.daten[n])


class SharedStrings:
    def __init__(self, paket):
        self.p = paket
        self.xml = paket.text("xl/sharedStrings.xml")
        self.anzahl = len(re.findall(r"<si>", self.xml))
        self.neu = []

    def index(self, text):
        """Neuen String anhängen (vorhandene Strings werden nie verändert,
        weil ein Index von mehreren Zellen genutzt werden kann)."""
        self.neu.append(text)
        return self.anzahl + len(self.neu) - 1

    def schreibe(self):
        zus = "".join(f'<si><t xml:space="preserve">{escape(t)}</t></si>' for t in self.neu)
        gesamt = self.anzahl + len(self.neu)
        xml = self.xml.replace("</sst>", zus + "</sst>")
        xml = re.sub(r'uniqueCount="\d+"', f'uniqueCount="{gesamt}"', xml, count=1)
        xml = re.sub(r' count="\d+"', f' count="{gesamt + 500}"', xml, count=1)
        self.p.setze("xl/sharedStrings.xml", xml)


class Blatt:
    """Zellen eines Arbeitsblatts setzen, Stil der vorhandenen Zelle bleibt."""

    def __init__(self, paket, name, sst):
        self.p, self.name, self.sst = paket, name, sst
        self.xml = paket.text(name)

    # -- Suchen --
    def _zelle(self, ref):
        return re.search(rf'<c r="{ref}"(?: [^>]*?)?(?:/>|>.*?</c>)', self.xml, re.S)

    def stil(self, ref):
        m = self._zelle(ref)
        if not m:
            return None
        s = re.search(r' s="(\d+)"', m.group(0))
        return s.group(1) if s else None

    def _ersetze_zelle(self, ref, inhalt, attr, stil):
        """inhalt: innerer XML-Text der Zelle, attr: z.B. ' t="s"'."""
        s = self.stil(ref) if stil is None else stil
        s_attr = f' s="{s}"' if s is not None else ""
        neu = f'<c r="{ref}"{s_attr}{attr}>{inhalt}</c>' if inhalt else f'<c r="{ref}"{s_attr}{attr}/>'
        m = self._zelle(ref)
        if m:
            self.xml = self.xml[:m.start()] + neu + self.xml[m.end():]
            return
        sp, zeile = teile(ref)
        mz = re.search(rf'<row r="{zeile}"([^>]*?)(/>|>(.*?)</row>)', self.xml, re.S)
        if not mz:
            self._neue_zeile(zeile, neu)
            return
        if mz.group(2) == "/>":
            ersatz = f'<row r="{zeile}"{mz.group(1)}>{neu}</row>'
            self.xml = self.xml[:mz.start()] + ersatz + self.xml[mz.end():]
            return
        innen = mz.group(3)
        zellen = list(re.finditer(r'<c r="([A-Z]+)\d+"(?: [^>]*?)?(?:/>|>.*?</c>)', innen, re.S))
        pos = len(innen)
        for z in zellen:
            if spalte_zu_zahl(z.group(1)) > spalte_zu_zahl(sp):
                pos = z.start()
                break
        innen = innen[:pos] + neu + innen[pos:]
        kopf = re.sub(r' spans="[^"]*"', "", mz.group(1))
        self.xml = self.xml[:mz.start()] + f'<row r="{zeile}"{kopf}>{innen}</row>' + self.xml[mz.end():]

    def _neue_zeile(self, zeile, zellxml):
        zeilen = list(re.finditer(r'<row r="(\d+)"', self.xml))
        pos = None
        for z in zeilen:
            if int(z.group(1)) > zeile:
                pos = z.start()
                break
        neu = f'<row r="{zeile}">{zellxml}</row>'
        if pos is None:
            pos = self.xml.index("</sheetData>")
        self.xml = self.xml[:pos] + neu + self.xml[pos:]

    # -- Setzen --
    def zahl(self, ref, wert, stil=None):
        self._ersetze_zelle(ref, f"<v>{repr(float(wert))}</v>", "", stil)

    def text(self, ref, text, stil=None):
        self._ersetze_zelle(ref, f"<v>{self.sst.index(text)}</v>", ' t="s"', stil)

    def formel(self, ref, formel, stil=None, ist_text=False):
        attr = ' t="str"' if ist_text else ""
        self._ersetze_zelle(ref, f"<f>{escape(formel)}</f>", attr, stil)

    def leer(self, ref, stil=None):
        self._ersetze_zelle(ref, "", "", stil)

    def ersetze(self, alt, neu, anzahl=1):
        assert self.xml.count(alt) >= 1, f"nicht gefunden in {self.name}: {alt[:80]}"
        self.xml = self.xml.replace(alt, neu, anzahl)

    def speichere(self):
        self.p.setze(self.name, self.xml)


ZELLE = re.compile(r'<c r="([A-Z]+\d+)"([^>]*?)(?:/>|>(.*?)</c>)', re.S)


def _formelzellen_ersetzen(xml, funktion):
    """Jede Zelle einzeln betrachten (Zellen sind nie verschachtelt, deshalb
    endet eine Zelle sicher am ersten </c>). funktion(ref, attr, f_xml)
    liefert das neue Zell-XML oder None (unverändert)."""
    def ersetze(m):
        ref, attr, innen = m.group(1), m.group(2), m.group(3) or ""
        mf = re.match(r"(<f(?: [^>]*)?/>|<f(?: [^>]*)?>.*?</f>)", innen, re.S)
        if not mf:
            return m.group(0)
        neu = funktion(ref, re.sub(r' t="[^"]*"', "", attr), mf.group(1))
        return m.group(0) if neu is None else neu
    return ZELLE.sub(ersetze, xml)


def werte_einsetzen(paket, blatt_dateien, werte):
    """Gespeicherte Ergebnisse (<v>) der Formelzellen setzen.

    blatt_dateien: {Blattname: 'xl/worksheets/sheetN.xml'}
    werte: {Blattname: {Zelle: Wert}} - z. B. aus einer mit LibreOffice
    neu berechneten Kopie. Excel rechnet beim Öffnen ohnehin neu; die Werte
    sind für Vorschauprogramme, die nicht selbst rechnen.
    """
    for blatt, datei in blatt_dateien.items():
        w = werte.get(blatt, {})

        def neu(ref, attr, f):
            if ref not in w or w[ref] is None:
                return None
            v = w[ref]
            if isinstance(v, bool):
                return f'<c r="{ref}"{attr} t="b">{f}<v>{int(v)}</v></c>'
            if isinstance(v, (int, float)):
                return f'<c r="{ref}"{attr}>{f}<v>{repr(float(v))}</v></c>'
            return f'<c r="{ref}"{attr} t="str">{f}<v>{escape(str(v))}</v></c>'

        paket.setze(datei, _formelzellen_ersetzen(paket.text(datei), neu))


def formelwerte_loeschen(paket):
    """Alte gespeicherte Formelergebnisse entfernen (stammen aus der Mappe für
    reines CO2 und wären sonst falsch, bis Excel neu rechnet)."""
    for n in list(paket.namen):
        if n.startswith("xl/worksheets/sheet") and n.endswith(".xml"):
            xml = _formelzellen_ersetzen(paket.text(n), lambda ref, attr, f: f'<c r="{ref}"{attr}>{f}</c>')
            paket.setze(n, xml)
