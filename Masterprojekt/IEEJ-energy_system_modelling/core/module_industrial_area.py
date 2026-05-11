"""
Industriegebiet – Lastgänge Unternehmen (OOP-Version)

Dieses Modul aggregiert Lastgänge für ausgewählte Unternehmen und erzeugt
CSV- und PNG-Ausgaben. Die prozedurale Logik wurde in eine Klasse
`IndustryLoadAggregator` überführt, die sowohl interaktiv als auch
programmatisch genutzt werden kann.
"""

import os
import collections
from typing import List, Dict, Tuple, Optional

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import MonthLocator, DateFormatter


class IndustryLoadAggregator:
    """Aggregiert Lastgänge für ein Industriegebiet und erzeugt Ausgaben.

    Nutzung:
    - Interaktiv: `IndustryLoadAggregator().run_interactive()`
    - Programmgesteuert: `IndustryLoadAggregator().run(mode_choice="1", selection_indices=[0, 2])`
    """

    # Liste der verfügbaren Unternehmen (Anzeige und Schlüssel zugleich)
    UNTERNEHMEN: List[str] = [
        "Entsorgung: \n5 1/2 Tage Woche, Kein Schichtbetrieb, Anlehnung an Schönmackers Umweltdienste\n",
        "Stahl: \n5 Tage Woche, 3-Schicht-Betrieb, Anlehnung an TecPro\n",
        "Logistik und Lagerung: \n5 Tage Woche, Teilweise Samstag und Sonntag Betrieb, Kein Schichtbetrieb, Anlehnung an CTJ Janssen\n",
        "Schrott- und Metallhandel: \n5 Tage Woche, Kein Schichtbetrieb, Anlehnung an Willi Jenner\n",
        "Lagerung: \n5 Tage Woche, Kein Schichtbetrieb, Anlehnung an Kleine Logistik\n",
        "Büro: \n5 Tage Woche, Kein Schichtbetrieb, Anlehnung an Marvin Wickenhäuser\n",
        "Logistik Lebensmittel: \n6 1/2 Tage Woche, Kein Schichtbetrieb, Anlehnung an CTJ Janssen\n",
        "Stahl: \n7 Tage Woche, 2-Schicht-Betrieb, Anlehnung an TecPro\n",
    ]

    # Zuordnung der Unternehmen zu Spaltennamen/Lastgängen und Jahr
    ZUORDNUNG: Dict[str, Tuple[str, str]] = {
        "Entsorgung: \n5 1/2 Tage Woche, Kein Schichtbetrieb, Anlehnung an Schönmackers Umweltdienste\n": ("Entsorgung", "2017"),
        "Stahl: \n5 Tage Woche, 3-Schicht-Betrieb, Anlehnung an TecPro\n": ("Stahl_1", "2017"),
        "Logistik und Lagerung: \n5 Tage Woche, Teilweise Samstag und Sonntag Betrieb, Kein Schichtbetrieb, Anlehnung an CTJ Janssen\n": ("Logistik und Lagerung", "2017"),
        "Schrott- und Metallhandel: \n5 Tage Woche, Kein Schichtbetrieb, Anlehnung an Willi Jenner\n": ("Schrott Metallhandel", "2017"),
        "Lagerung: \n5 Tage Woche, Kein Schichtbetrieb, Anlehnung an Kleine Logistik\n": ("Lagerung", "2017"),
        "Büro: \n5 Tage Woche, Kein Schichtbetrieb, Anlehnung an Marvin Wickenhäuser\n": ("Buero", "2017"),
        "Logistik Lebensmittel: \n6 1/2 Tage Woche, Kein Schichtbetrieb, Anlehnung an CTJ Janssen\n": ("Logistik Lebensmittel", "2017"),
        "Stahl: \n7 Tage Woche, 2-Schicht-Betrieb, Anlehnung an TecPro\n": ("Stahl_2", "2017"),
    }

    BASISNAME_AUSGABE: str = "Projekt_04_Erzeugter_Gesamtverbrauch_Industriegebiet"

    def __init__(self, base_dir: Optional[str] = None) -> None:
        self.script_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        self.path_standard = os.path.join(self.script_dir,"..","data","inputs", "Projekt_04_Lastgaenge_Industriegebiet.csv")
        self.path_waerme_kaelte = os.path.join(
            self.script_dir,"..","data","inputs",
            "Projekt_04_Lastgaenge_Industriegebiet_und_nPro_Waerme_Kaelte.csv",
        )
        self.mode_choice: str = "1"
        self.mode_name: str = "Ohne_Waerme_Kaelte"
        self.active_path: str = self.path_standard
        self.df_2017: Optional[pd.DataFrame] = None

    # -------------------- Interaktion --------------------
    def run_interactive(self) -> Optional[pd.DataFrame]:
        """Interaktive Ausführung mit Benutzereingaben."""
        print("Welche Daten sollen genutzt werden?")
        print("1) Ohne Wärme/Kälte Stromverbrauch (Nutzung fossiler Energiequellen für Wärme, keine Kälte)")
        print("2) Mit Wärme/Kälte Stromverbrauch (Nutzung reversibler Luftwärmepumpen und Geothermie-Sonden)")
        self.mode_choice = input("Auswahl (1 oder 2): ")
        self._set_mode(self.mode_choice)

        self._print_companies()
        auswahl_input = input(
            "Geben Sie die Nummern der Unternehmen ein, die betrachtet werden sollen. \n(Durch Kommas trennen, Doppelauswahl möglich, Minimal 1 Unternehmen, Maximal 5 Unternehmen, z.B. 1,3,5)\n "
        )
        selection_indices = self._parse_selection(auswahl_input)
        if selection_indices is None:
            return

        self.load_data()
        combined_df = self.aggregate(selection_indices)
        if combined_df is None:
            print("Keine Daten zu extrahieren.")
            return

        csv_path = self.save_csv(combined_df)
        print(f"\nKombinierte Lastgänge gespeichert in: {csv_path}")
        plot_path = self.plot_daily_bar(combined_df)
        #if plot_path:
            #print(f"Balkenplot gespeichert als: {plot_path}")
        return combined_df

    def parse_selection_input(self, auswahl_input: str) -> Optional[List[int]]:
        """Öffentliche Parse-Hilfe für Auswahleingaben (z.B. aus externem Skript)."""
        return self._parse_selection(auswahl_input)

    def run(self, mode_choice: str, selection_indices: List[int]) -> Tuple[Optional[pd.DataFrame], Optional[str], Optional[str]]:
        """Programmgesteuerte Ausführung ohne Eingabeaufforderungen.

        Returns: (combined_df, csv_path, plot_path)
        """
        self._set_mode(mode_choice)
        self.load_data()
        combined_df = self.aggregate(selection_indices)
        if combined_df is None:
            return None, None, None
        csv_path = self.save_csv(combined_df)
        plot_path = self.plot_daily_bar(combined_df)
        return combined_df, csv_path, plot_path

    # -------------------- Modus & Daten --------------------
    def _set_mode(self, choice: str) -> None:
        if choice == "2":
            self.active_path = self.path_waerme_kaelte
            self.mode_name = "Mit_Waerme_Kaelte"
            #print("Modus: Mit Wärme/Kälte ausgewählt.\n")
        else:
            self.active_path = self.path_standard
            self.mode_name = "Ohne_Waerme_Kaelte"
            #print("Modus: Ohne Wärme/Kälte ausgewählt.\n")

    def load_data(self) -> None:
        """Lädt die CSV-Daten für 2017 aus dem aktiven Pfad."""
        self.df_2017 = pd.read_csv(self.active_path, sep=";", decimal=".", header=0)

    # -------------------- Auswahl & Parsing --------------------
    def _print_companies(self) -> None:
        print("Verfügbare Unternehmen:")
        for i, u in enumerate(self.UNTERNEHMEN, 1):
            print(f"{i}. {u}")

    def _parse_selection(self, auswahl_input: str) -> Optional[List[int]]:
        try:
            auswahl_indices = [
                int(x.strip()) - 1 for x in auswahl_input.split(",") if x.strip().isdigit()
            ]
            if len(auswahl_indices) > 5:
                print("Maximal 5 Auswahlen erlaubt.")
                return None
            ausgewahlte_unternehmen = [
                self.UNTERNEHMEN[i] for i in auswahl_indices if 0 <= i < len(self.UNTERNEHMEN)
            ]
            if not ausgewahlte_unternehmen:
                print("Keine gültige Auswahl getroffen. Programm beendet.")
                return None
            print(f"Ausgewählte Unternehmen: {ausgewahlte_unternehmen}")
            return auswahl_indices
        except ValueError:
            print("Ungültige Eingabe. Bitte nur Zahlen und Kommas verwenden.")
            return None

    # -------------------- Aggregation & Ausgabe --------------------
    def aggregate(self, selection_indices: List[int]) -> Optional[pd.DataFrame]:
        if self.df_2017 is None:
            print("Daten wurden nicht geladen.")
            return None

        selected_data: Dict[str, pd.DataFrame] = {}
        unternehmen_counts = collections.defaultdict(int)

        for idx in selection_indices:
            if 0 <= idx < len(self.UNTERNEHMEN):
                u = self.UNTERNEHMEN[idx]
                unternehmen_counts[u] += 1
                key = f"{u}_{unternehmen_counts[u]}"
                lg, year = self.ZUORDNUNG[u]
                if year == "2017":
                    df = self.df_2017[["Time stamp", lg]].copy()
                    df.rename(columns={lg: key}, inplace=True)
                    df[key] = pd.to_numeric(df[key], errors="coerce")
                    selected_data[key] = df

        if not selected_data:
            return None

        combined_df = pd.DataFrame()
        for df in selected_data.values():
            if combined_df.empty:
                combined_df = df
            else:
                combined_df = pd.merge(combined_df, df, on="Time stamp", how="outer")

        # Summe der Lastgänge berechnen
        combined_df["Gesamtlast [kW]"] = combined_df.drop("Time stamp", axis=1).sum(axis=1)
        #print("\nSumme der Lastgänge (kW je 15 Minuten):")
        #print(combined_df[["Time stamp", "Gesamtlast [kW]"]].head(96))

        # Zeitstempel konvertieren für Plot
        combined_df["Time stamp"] = pd.to_datetime(combined_df["Time stamp"], errors="coerce")
        return combined_df

    def save_csv(self, combined_df: pd.DataFrame) -> str:
        combined_df_csv = combined_df.copy()
        combined_df_csv["Time stamp"] = combined_df_csv["Time stamp"].dt.strftime("%d.%m %H:%M")
        import os
        output_dir = "/../data/outputs/industry_area"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(self.script_dir,output_dir, f"{self.BASISNAME_AUSGABE}.csv")
        combined_df_csv[["Time stamp", "Gesamtlast [kW]"]].to_csv(
            output_path, sep=",", decimal=".", index=False
        )
        return output_path

    def plot_daily_bar(self, combined_df: pd.DataFrame) -> Optional[str]:
        try:
            combined_df_plot = combined_df.copy()
            combined_df_plot = (
                combined_df_plot.set_index("Time stamp").resample("D").sum().reset_index()
            )
            plt.figure(figsize=(20, 10))
            plt.bar(combined_df_plot["Time stamp"], combined_df_plot["Gesamtlast [kW]"], width=1)
            plt.xlabel("Zeit")
            plt.ylabel("Tägliche Gesamtlast (kW)")
            plt.title("Tägliche Gesamtlast über das Jahr")
            plt.xticks(rotation=45)
            ax = plt.gca()
            ax.xaxis.set_major_locator(MonthLocator())
            ax.xaxis.set_major_formatter(DateFormatter("%B"))
            plt.xlim(
                combined_df_plot["Time stamp"].min(),
                combined_df_plot["Time stamp"].max(),
            )
            plot_path = os.path.join(self.script_dir, f"{self.BASISNAME_AUSGABE}.png")
            #plt.savefig(plot_path) #falls der plot gespeichert werden soll
            #plt.show() #falls plot angezeigt werden soll
            plt.close()
            return plot_path
        except Exception as e:
            print(f"Fehler beim Erstellen des Plots: {e}")
            return None


if __name__ == "__main__":
    IndustryLoadAggregator().run_interactive()
