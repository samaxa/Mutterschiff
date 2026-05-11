#%% Import
import pandas as pd
import pypsa
import warnings
warnings.filterwarnings("ignore")
import plotly.graph_objects as go
from IPython.display import Image
import plotly.io as pio
import plotly.offline as pyo
import plotly.graph_objs as go
import matplotlib.pyplot as plt
from scipy import interpolate
import numpy as np
import plotly.io as pio
pio.renderers.default='browser'
import gurobipy
import CoolProp.CoolProp as CP
import math as m
from datetime import datetime, timedelta
import plotly.express as px
#from collections import Counter
#import time
from electrolyzer_GEH import electrolyzer
#from zoneinfo import ZoneInfo
import os
import pickle
from plotly.subplots import make_subplots
import kaleido
import seaborn as sns

#%% User Input

path = '../../Projekt_03_Green_Energy_Hub/MA_Saur_Data/Wasserstofftankstelle_Saur_angepasst/Input/'  # Pfad für den Datenimport
output_path = '../../Projekt_03_Green_Energy_Hub/MA_Saur_Data/Wasserstofftankstelle_Saur_angepasst/Output_test2030/'  # Pfad für Export von Ergebnissen

year = 2030 # Für welches Jahr soll die Simulation durchgeführt werden? Eingabe von 2020 bis 2050 möglich.

length = 365 # Tage, Option zur Verkürzung der Rechendauer durch Verkürzung des Betrachtungszeitraums

start_date = f'{year}-01-01 00:00' # Gewünschter Startzeitpunkt der Simulation; Format: YYYY-MM-DD HH:MM+HH:MM; nur in 15 min Intervallen ändern

PV_P_NOM = 0 # [MWp] Installierte Leistung PV
WIND_P_NOM = 0 # [MW] Installierte Leistung Wind

H2_store_cap = 10.0 # [MWh] Kapazität Wasserstoffspeicher
P_H2_store = 1.039 # [MW] Quelle: Thermodynamic analysis of ﬁlling compressed gaseous hydrogen storage tanks m. = 0.00866 kg/s
el_store_cap = 0.0 # [MWh] Kapazität Batteriespeicher
P_el_store = el_store_cap # [MW] Annahme: Verhältnis Kapazität/Leistung 1:1

#Input für Zapfsäule/Ladesäule
min_share_fueling_point_FCEV = 3 # [%] Minimal zulässiger Anteil an gesamter FCEV-Energie pro Zapfpunkt, damit der Zapfpunkt in der finalen Lastkurve berücksichtigt wird
min_share_fueling_point_FCET = 3 # [%] Minimal zulässiger Anteil an gesamter FCET-Energie pro Zapfpunkt, damit der Zapfpunkt in der finalen Lastkurve berücksichtigt wird
min_share_charging_point = 3 # [%] Minimal zulässiger Anteil an gesamter BEV-Energie pro Ladesäule, damit die Ladesäule in der finalen Lastkurve berücksichtigt wird

# Eingabe von gewünschter Zeitspanne für Plots
start_date_plots = f'{year}-01-01 00:00'
end_date_plots = f'{year}-12-31 00:00'

#%% Inputdaten PV
df_pv_h = pd.read_csv(f'{path}DE_1,5MWp.csv',header=3) # Einlesen der PV-Leistungsdaten aus einer CSV-Datei
df_pv_h = df_pv_h.drop('local_time', axis = 1) # Löschen der Spalte local_time
df_pv_h['time'] = pd.to_datetime(df_pv_h['time']) # Konvertieren der Series time in ein datetime object
df_pv_h = df_pv_h.set_index(df_pv_h['time']) # Setzen der Spalte time als index
df_pv_h = df_pv_h.drop('time', axis = 1) # Löschen der Spalte time (nur index und Leistungswerte bleiben übrig)
df_pv_15min = df_pv_h.resample('15min').interpolate() # Strecken der Stundenwerte auf 15min-Werte mit Interpolation zwischen den Stunden-Leistungswerten, um die 15min-Leistungswerte dazwischen zu erhalten
df_pv_15min_mw = df_pv_15min/1000 # Umrechnen von kWp in MWp
#
# df_pv_15min_mw hat nach resample schon einen Zeitindex
start = pd.Timestamp(f"{year}-01-01 00:00:00")
end   = pd.Timestamp(f"{year}-12-31 23:45:00")
target_index = pd.date_range(start, end, freq="15min")

df_pv_15min_mw = df_pv_15min_mw.reindex(target_index)

# PV: fehlende Werte plausibel zu 0 (oder alternativ interpolieren, je nach Datenqualität)
df_pv_15min_mw["electricity"] = df_pv_15min_mw["electricity"].fillna(0)
#
# df_pv_15min_mw['time_input_year'] = pd.date_range(start=f'{year}-01-01', periods=35037, freq='15T') # Hinzufügen einer neuen Spalte mit den timestamps des Input-Jahres (Variable year); Periode von 35037 weil letzte Stunde des Jahres fehlt, ansonsten wären es 35040 Viertelstunden pro Jahr
# df_pv_15min_mw = df_pv_15min_mw.set_index(df_pv_15min_mw['time_input_year']) # Setzen der Spalte time_input_year als index
# df_pv_15min_mw = df_pv_15min_mw.drop(columns=['time_input_year']) # Löschen der obsoleten weil doppelten Spalte time_input_year
# last_value = df_pv_15min_mw.loc[f'{year}-12-31 23:00:00', 'electricity'] # Hinzufügen der letzten drei Viertelstundenwerte des Jahres, die bei .resample.interpolate verloren gehen
# new_times = [f'{year}-12-31 23:15:00', f'{year}-12-31 23:30:00', f'{year}-12-31 23:45:00'] # Erstellen eines DataFrames mit den neuen Zeilen für 23:15, 23:30 und 23:45 Uhr
# new_rows = pd.DataFrame({'electricity': [last_value, last_value, last_value]}, index=pd.to_datetime(new_times)) # Vereinfachung: Der letzte Viertelstundenwert aus df_pv_15min_mw wird 3 mal kopiert und am Ende wieder eingefügt
# df_pv_15min_mw = pd.concat([df_pv_15min_mw, new_rows]) # Die neuen Zeilen zum DataFrame hinzufügen

#%% Inputdaten WIND

df_wind_h = pd.read_csv(f'{path}DE_5,6MW_Wind.csv', header=3)
df_wind_h = df_wind_h.drop('local_time', axis=1)

df_wind_h['time'] = pd.to_datetime(df_wind_h['time'])
df_wind_h = df_wind_h.set_index('time')          # schöner als set_index(df['time'])
# df_wind_h = df_wind_h.drop('time', axis=1)     # entfällt, weil set_index('time') die Spalte optional droppt
# -> wenn du drop brauchst: set_index('time', drop=True)

df_wind_15min = df_wind_h.resample('15min').interpolate()
df_wind_15min_mw = df_wind_15min / 1000          # kW -> MW (sofern input wirklich kW ist)

# Sauberer Jahresindex (15-min) erzwingen
start = pd.Timestamp(f"{year}-01-01 00:00:00")
end   = pd.Timestamp(f"{year}-12-31 23:45:00")
target_index = pd.date_range(start, end, freq="15min")

df_wind_15min_mw = df_wind_15min_mw.reindex(target_index)

# Wind: fehlende Werte am Rand plausibel zu 0 (oder ffill, siehe unten)
df_wind_15min_mw["electricity"] = df_wind_15min_mw["electricity"].fillna(0)



#
# df_wind_h = pd.read_csv(f'{path}DE_5,6MW_Wind.csv',header=3) # Einlesen der Wind-Leistungsdaten aus einer CSV-Datei
# df_wind_h = df_wind_h.drop('local_time', axis = 1) # Löschen der Spalte local_time
# df_wind_h['time'] = pd.to_datetime(df_wind_h['time']) # Konvertieren der Series time in ein datetime object
# df_wind_h = df_wind_h.set_index(df_wind_h['time']) # Setzen der Spalte time als index
# df_wind_h = df_wind_h.drop('time', axis = 1) # Löschen der Spalte time (nur index und Leistungswerte bleiben übrig)
# df_wind_15min = df_wind_h.resample('15min').interpolate() # Strecken der Stundenwerte auf 15min-Werte mit Interpolation zwischen den Stunden-Leistungswerten, um die 15min-Leistungswerte dazwischen zu erhalten
# df_wind_15min_mw = df_wind_15min/1000 # Umrechnen von kW in MW
# df_wind_15min_mw['time_input_year'] = pd.date_range(start=f'{year}-01-01', periods=35037, freq='15T') # Hinzufügen einer neuen Spalte mit den timestamps des Input-Jahres (Variable year); Periode von 35037 weil letzte Stunde des Jahres fehlt, ansonsten wären es 35040 Viertelstunden pro Jahr
# df_wind_15min_mw = df_wind_15min_mw.set_index(df_wind_15min_mw['time_input_year']) # Setzen der Spalte time_input_year als index
# df_wind_15min_mw = df_wind_15min_mw.drop(columns=['time_input_year']) # Löschen der obsoleten weil doppelten Spalte time_input_year
# last_value = df_wind_15min_mw.loc[f'{year}-12-31 23:00:00', 'electricity'] # Hinzufügen der letzten drei Viertelstundenwerte des Jahres, die bei .resample.interpolate verloren gehen
# new_times = [f'{year}-12-31 23:15:00', f'{year}-12-31 23:30:00', f'{year}-12-31 23:45:00'] # Erstellen eines DataFrames mit den neuen Zeilen für 23:15, 23:30 und 23:45 Uhr
# new_rows = pd.DataFrame({'electricity': [last_value, last_value, last_value]}, index=pd.to_datetime(new_times)) # Vereinfachung: Der letzte Viertelstundenwert aus df_wind_15min_mw wird 3 mal kopiert und am Ende wieder eingefügt
# df_wind_15min_mw = pd.concat([df_wind_15min_mw, new_rows]) # Die neuen Zeilen zum DataFrame hinzufügen

#%% Generierung Inputdaten H2 Load
# DATEN EINLESEN
# Allgemeine Daten
df_monthly_refuel_prob_H2 = pd.read_csv(f'{path}seasonal_refuel_prob.csv', encoding = 'latin1', sep = ';') # Daten für die jährlich verkaufte Menge an Benzin in DE. Quelle: bafa.de
df_rel_refuel_prob_H2 = pd.read_csv(f'{path}rel_refuel_prob.csv', encoding = 'latin1', sep = ';') # Relative Tankwahrscheinlichkeiten nach Wochentag. Quelle: Grüger - Initialinfrastruktur für Wasserstoffmobilität auf Basis von Flotten

# FCEV Daten
df_FCEV_data = pd.read_csv(f'{path}FCEV_data.csv', encoding = 'latin1', sep = ';') # Daten zu FCEVs. Quelle: https://h2.live/en/fcev/
df_PKW_fuel_sources = pd.read_csv(f'{path}PKW_fuel_sources.csv', encoding = 'latin1', sep = ';') # PKW-Bestand in DE nach Kraftstoffart bis 2024. Quelle: kba.de
df_gasoline_consumption = pd.read_csv(f'{path}gasoline_consumption.csv', encoding = 'latin1', sep = ';') # Benzinverbrauch in DE bis 2023. Quelle: bafa.de
df_FCEV_quantity = pd.read_csv(f'{path}FCEV_quantity.csv', encoding = 'latin1', sep = ';') # Prognose der Anzahl von FCEVs aufgeteilt nach Fahrzeugklassen bis 2050. Quellen: Economic competitiveness and environmental implications; für 2050 Quelle: Flexible sector coupling: A climate-friendly fuel supply for road transport

# FCET Daten
df_LKW_km = pd.read_csv(f'{path}km_LKW.csv', encoding = 'latin1', sep = ';') # Daten zur Fahrleistung von LKW. Quelle:https://de.statista.com/statistik/daten/studie/155725/umfrage/fahrleistung-der-lkw-in-deutschland/)
df_n_LKW = pd.read_csv(f'{path}n_LKW.csv', encoding = 'latin1', sep = ';') # LKW-Bestand in DE Quelle: https://de.statista.com/statistik/daten/studie/6961/umfrage/anzahl-der-lkw-in-deutschland/
df_FCET_data = pd.read_csv(f'{path}FCET_data.csv', encoding = 'latin1', sep = ';') # Daten zu FCETs. Quelle: https://www.klimafreundliche-nutzfahrzeuge.de/fahrzeugdatenbank-kategorie/h2-lkw-2/

# Aufbereitung relative Tankwahrscheinlichkeit H2 --> von abgelesenen Stundenwerten auf Viertelstundenwerte
start_date_load = f'{year}-01-01 00:00'
end_date_load = f'{year}-12-31 23:45'
date_range = pd.date_range(start=start_date_load, end=end_date_load, freq='15T') # Viertelstündliche Datumsliste für das oben ausgewählte Jahr
weekdays = date_range.strftime("%a") # Liste der Wochentage als Abkürzungen (Mo, Tue, Wed, usw.)
df_load_H2 = pd.DataFrame({'date': date_range,'weekday': weekdays}) # DataFrame für Berechnung der Wasserstoff-Nachfragekurve mit Spalten für Datum und Wochentag

new_rows = [] # Initialisierung einer Liste für neue Zeilen
start_time = datetime.strptime('00:00', '%H:%M') # Startzeit für die Schleife
for index, row in df_rel_refuel_prob_H2.iterrows(): # Schleife über df_rel_refuel_prob_H2 für Änderung der Stundenwerte für die relative Tankwahrscheinlichkeit in Viertelstundenwerte
    mo_do_value = row['Mo-Do'] / 4 # Werte durch 4 teilen, um aus den Stundenwerten Viertelstundenwerte zu generieren
    fr_value = row['Fr'] / 4
    sa_value = row['Sa'] / 4
    so_value = row['So'] / 4
    
    for i in range(4): # Für jede Stunde werden vier neue Zeilen erstellt und die zuvor geviertelten Werte der Tankwahrscheinlichkeit werden in die vier neuen Reihen der Liste new_rows geschrieben
        current_time = start_time + timedelta(minutes=15 * (index * 4 + i)) 
        new_row = {'Time': current_time.strftime('%H:%M'),'Mon-Thu': mo_do_value,'Fri': fr_value,'Sat': sa_value,'Sun': so_value}
        new_rows.append(new_row)

df_rel_refuel_prob_H2 = pd.DataFrame(new_rows) # Speichern der neuen viertelstündlichen Werte pro Wochentag in die neuen Reihen Mo - So in df_rel_refuel_prob_H2 --> DataFrame für eine Woche fertig

# Berechnung H2-Bedarf für ein Jahr
#Interpolation bzw Extrapolation der benötigten Werte für das gewählte Jahr, falls Daten für das gewählte Jahr nicht vorliegen
def interpolate_value(df, year, column):
    interp_func = interpolate.interp1d(df['year'], df[column], fill_value="extrapolate", kind="slinear") # lineare Interpolation (bzw segmentiert linear) am sinnvollsten, da bei quadratischer zwischen zwei Punkten auch negative Werte möglich (zB bei Anzahl FCEV 2023), negative Anzahl an Autos ist aber unrealistisch und für Rechnung nicht praktikabel
    return interp_func(year)

# Exponentielle Trendlinie (Excel) zur Berechnung der Anzahl an HRSs auf Basis aller gefundener Literaturwerte zu Prognosen der HRS-Anzahl
def calc_n_refuel_stations_year(year):
    n_HRSs = 2e-82 * m.exp(0.0957 * year)
    return n_HRSs

n_refuel_stations_year = calc_n_refuel_stations_year(year)

# FCEV Daten
m_gasoline_year = interpolate_value(df_gasoline_consumption, year, 'gasoline (million tons)') * 1000000 * 1000 # [kg Benzin] Gesamter Benzinverkauf im Jahr
n_PKW_year = interpolate_value(df_PKW_fuel_sources, year, 'Benzin') # Anzahl der Benzin-PKWs im Jahr
n_FCEV_year = interpolate_value(df_FCEV_quantity, year, 'Autos') # Anzahl der Wasserstoff-PKWs im Jahr

# FCET Daten
s_LKW_year = interpolate_value(df_LKW_km, year, 'km') # [km] Fahrleistung von LKW im Jahr
n_LKW_year = interpolate_value(df_n_LKW, year, 'n LKW') # Anzahl der LKW im Jahr
n_FCET_year = interpolate_value(df_FCEV_quantity, year, 'LKW') # Anzahl der Wasserstoff-LKW im Jahr

# # Nur für Kapitel 9.2 Szenarienbetrachtung:
# share_low = 0.25
# share_medium = 0.5
# share_high = 0.75
# n_FCEV_year = interpolate_value(df_PKW_fuel_sources, year, 'Gesamt')*share_high # Anzahl an FCEV an gesamtem PKW Bestand in Abhängigkeit des Marktdiffusionsszenarios
# n_FCET_year = interpolate_value(df_n_LKW, year, 'n LKW')*share_high # Anzahl an FCET an gesamtem LKW Bestand in Abhängigkeit des Marktdiffusionsszenarios

# Berechnung benötigte H2 Masse für FCEV
avg_gas_consumption = m_gasoline_year / n_PKW_year # [kg / PKW] Durchschnittlicher Benzinverbrauch pro PKW
energy_density_gasoline = 11 # [kWh /kg] Energiedichte von Benzin Quelle: https://www.enargus.de/pub/bscw.cgi/d3114-2/*/*/Energiedichte.html?op=Wiki.getwiki
LHV_gasoline = 8.5 # [kWh/l] Heizwert von Benzin Quelle: https://nachhaltigmobil.schule/leistung-energie-verbrauch/
energy_consumption_PKW = avg_gas_consumption * energy_density_gasoline # [kWh/PKW] Durchschnittlicher Energieverbrauch pro PKW
avg_gas_consumption_100km = 7.7  # [l/100km] Durchschnittlicher Benzinverbrauch Quelle: https://de.statista.com/statistik/daten/studie/484054/umfrage/durchschnittsverbrauch-pkw-in-privaten-haushalten-in-deutschland/
energy_consumpiton_gasoline_100km = LHV_gasoline * avg_gas_consumption_100km # [kWh / 100 km] Energieverbrauch von Benzin-PKWs
avg_energy_consumption_FCEV = 1 # [kg H2 / 100 km] Durchschnittlicher Wasserstoffverbrauch von FCEVs Quelle: https://dwv-info.de/aktuelle_meldungen/reichweite-und-effizienz-von-brennstoffzellen-fahrzeugen/
LHV_H2 = 33.33  # [kWh / kg] Heizwert von Wasserstoff Quelle: https://www.pemfc.de/hydrogen.html
energy_consumpiton_FCEV_100km = avg_energy_consumption_FCEV * LHV_H2 # [kWh / 100 km] Energieverbrauch von FCEVs
efficiency_factor = energy_consumpiton_FCEV_100km / energy_consumpiton_gasoline_100km #[] Faktor zwischen Verbrauch FCEV und Benziner über je 100 km bezogen auf Energiegehalt des jeweiligen Kraftstoffes
energy_consumption_per_FCEV = energy_consumption_PKW * efficiency_factor # [kWh/FCEV] Durchschnittlicher Energieverbrauch pro FCEV
energy_consumption_FCEV = energy_consumption_per_FCEV * n_FCEV_year / 1000 # Gesamtenergiebedarf aller FCEVs in MWh
coverage_share_refuel_stations = 1 / n_refuel_stations_year # Anteil der zu modellierenden Wasserstofftankstelle am Markt aller Wasserstofftankstellen in DE
energy_demand_refuel_station_H2 = energy_consumption_FCEV * coverage_share_refuel_stations # Energiebedarf der modellierten Wasserstofftankstelle in MWh
H2_demand_refuel_station_FCEV = energy_demand_refuel_station_H2 * 1000 / LHV_H2 # [kg H2] Wasserstoffbedarf der modellierten Wasserstofftankstelle zur Deckung des Bedarfs von FCEVs

# Berechnung benötigte H2 Masse für FCET
n_km_FCET_year = s_LKW_year * n_FCET_year / n_LKW_year # [km] Fahrleistung FCET im Jahr
avg_H2_consumption_FCET = df_FCET_data['Fuel consumption (H2) combined (kg/100km)'].mean() # [kg/100km] Durchschnittsverbrauch FCET berechnet als Durchschnitt aus den am Markt vorhandenen Fahrzeugen
coverage_share_refuel_stations = 1 / n_refuel_stations_year # Anteil der zu modellierenden Wasserstofftankstelle am Markt aller Wasserstofftankstellen in DE
H2_demand_FCET = n_km_FCET_year * avg_H2_consumption_FCET / 100 # [kg H2] Energiebedarf aller FCET im Jahr
H2_demand_FCET_MWh = H2_demand_FCET * LHV_H2 / 1000 # MWh
H2_demand_refuel_station_FCET = H2_demand_FCET * coverage_share_refuel_stations # [kg H2] H2-Energiebedarf der modellierten Wasserstofftankstelle für FCETs

H2_demand_refuel_station = H2_demand_refuel_station_FCEV + H2_demand_refuel_station_FCET # [kg H2] Wasserstoffbedarf der modellierten Wasserstofftankstelle gesamt

# Berechnung der monatlichen Tankwahrscheinlichkeit und nachgefragten Wasserstoffmenge
# Funktion zur Berechnung der Anzahl der Tage im Monat
def days_in_month(month, year=2050):
    days_in_month_dict = {
        'Jan': 31, 'Feb': 29 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 28, 
        'Mar': 31, 'Apr': 30, 'May': 31, 'Jun': 30, 
        'Jul': 31, 'Aug': 31, 'Sep': 30, 'Oct': 31, 
        'Nov': 30, 'Dec': 31}
    return days_in_month_dict[month]

df_monthly_refuel_prob_H2['avg_consumption_per_day_22'] = df_monthly_refuel_prob_H2.apply(lambda row: row['2022 [t gasoline]'] / days_in_month(row['month']), axis=1) # Berechnung der täglichen Durchschnittsmenge an verkauftem Benzin für 2022
df_monthly_refuel_prob_H2['avg_consumption_per_day_23'] = df_monthly_refuel_prob_H2.apply(lambda row: row['2023 [t gasoline]'] / days_in_month(row['month']), axis=1) # Berechnung der täglichen Durchschnittsmenge an verkauftem Benzin für 2023

sum_avg_daily_csmptn_22 = df_monthly_refuel_prob_H2['avg_consumption_per_day_22'].sum() # Summe aller um die Anzahl an Tagen pro Monat korrigierten täglichen Verbräuche an Benzin 2022
sum_avg_daily_csmptn_23 = df_monthly_refuel_prob_H2['avg_consumption_per_day_23'].sum() # Summe aller um die Anzahl an Tagen pro Monat korrigierten täglichen Verbräuche an Benzin 2023

df_monthly_refuel_prob_H2['monthly_share_22'] = df_monthly_refuel_prob_H2['avg_consumption_per_day_22'] / sum_avg_daily_csmptn_22 # [ ] Anteil des jeweiligen Montats am gesamten Benzinverbrauchs des Jahres
df_monthly_refuel_prob_H2['monthly_share_23'] = df_monthly_refuel_prob_H2['avg_consumption_per_day_23'] / sum_avg_daily_csmptn_23 # [ ] Anteil des jeweiligen Montats am gesamten Benzinverbrauchs des Jahres
df_monthly_refuel_prob_H2['monthly_share_avg'] = (df_monthly_refuel_prob_H2['monthly_share_22'] + df_monthly_refuel_prob_H2['monthly_share_23']) / 2 # Saisonale Tankwahrscheinlichkeit (korrigiert um die Anzahl der Tage im Monat) errechnet aus Werten für die Jahre 2022 und 2023 --> bei hinzufügen weiterer Jahre für Faktor 2 entsprechend anpassen
df_monthly_refuel_prob_H2['mass_H2'] = df_monthly_refuel_prob_H2['monthly_share_avg'] * H2_demand_refuel_station # [kg] pro Monat nachgefragte Masse H2 
df_monthly_refuel_prob_H2['mass_FCEV'] = df_monthly_refuel_prob_H2['mass_H2'] * H2_demand_refuel_station_FCEV/H2_demand_refuel_station
df_monthly_refuel_prob_H2['mass_FCET'] = df_monthly_refuel_prob_H2['mass_H2'] * H2_demand_refuel_station_FCET/H2_demand_refuel_station

# Berechnung Tankzeitpunkte und Tankmengen FCEV - Schleife über alle Zeitintervalle des gewählten Jahres
start_date_load = f'{year}-01-01 00:00'
end_date_load = f'{year}-12-31 23:45'
date_range = pd.date_range(start=start_date_load, end=end_date_load, freq='15T') # Viertelstündliche Datumsliste für das oben ausgewählte Jahr
weekdays = date_range.strftime("%a") # Liste der Wochentage als Abkürzungen (Mo, Tue, Wed, usw.)
df_load_H2 = pd.DataFrame({'date': date_range,'weekday': weekdays}) # DataFrame für Berechnung der Wasserstoff-Nachfragekurve mit Spalten für Datum und Wochentag

rel_refuel_prob_values_H2 = [] # Initialisierung einer Liste für die relativen Tankwahrscheinlichkeiten
weekday_to_column = {'Mon': 'Mon-Thu','Tue': 'Mon-Thu','Wed': 'Mon-Thu','Thu': 'Mon-Thu','Fri': 'Fri','Sat': 'Sat','Sun': 'Sun'} # Definition der Wochentage (zB Dienstag gehört zu Montag bis Donnerstag), um die korrekten relativen Tankwahrscheinlichkeiten einzelnen Wochentagen zuordnen zu können

for index, row in df_load_H2.iterrows(): # Iteration über die Zeilen im DataFrame zum Hinzufügen der relativen Tankwahrscheinlichkeiten als neue Spalte --> es wird dabei immer die relative Tankwahrscheinlichkeit mit dem passenden weekday und der passenden time aus df_rel_refuel_prob_H2 extrahiert
    weekday = row['weekday']
    column_name = weekday_to_column.get(weekday[:3])
    time = row['date'].strftime('%H:%M')
    refuel_prob_H2 = df_rel_refuel_prob_H2.loc[df_rel_refuel_prob_H2['Time'] == time, column_name].values[0]
    rel_refuel_prob_values_H2.append(refuel_prob_H2)

df_load_H2['rel_refuel_prob'] = rel_refuel_prob_values_H2 # Speichern der Spalte rel_refuel_prob im neuen DataFrame
df_load_H2['cumulative_prob'] = df_load_H2['rel_refuel_prob'].cumsum() # Berechnung der kumulativen Summe der Wahrscheinlichkeitsverteilung
df_load_H2['cumulative_prob'] /= df_load_H2['cumulative_prob'].iloc[-1] # Normierung, so dass der letzte Wert 1 ist 

# Lastkurve FCEV
#Tankmassen FCEV
m_Tank_avg_FCEV = df_FCEV_data['Tank capacity (kg)'].sum() / df_FCEV_data[df_FCEV_data["Tank capacity (kg)"] != 0].shape[0] # Durchschnittliche Masse H2 [kg] pro Refueling Event (durchschnittliche Tankgröße; Anpassung der tatsächlichen Tankmenge < Tankgröße erfolgt über Normalverteilung) für FCEV
m_RE_min_FCEV = m_Tank_avg_FCEV*0.05 # Annahme: Kleinste Betankungsmenge = 5 % der Tankkapazität
m_RE_max_FCEV = m_Tank_avg_FCEV*0.95 # Annahme: Größte Betankungsmenge = 95 % der Tankkapazität
m_RE_avg_FCEV = (m_RE_min_FCEV + m_RE_max_FCEV) / 2 # Durchschnittliche H2 Masse bei einem Refueling Event (Tankvorgang)
std_dev_H2_FCEV = (m_RE_max_FCEV - m_RE_min_FCEV) / 6  # Standardabweichung für Normalverteilung: 99.7% der Werte liegen innerhalb von 3 Standardabweichungen

# Zuordnung von Tankzeitpunkten und -massen
total_mass_FCEV = 0 # Initialisierung der Variablen und Spalten für Zufallszahlen für Tankvorgänge
df_load_H2['refueling_event_FCEV'] = 0 # 0 --> kein Tankvorgang innerhalb des Betrachtungszeitraums (15 min); 1 --> 1 Tankvorgang usw.
df_load_H2['Mass_H2_FCEV'] = 0 
individual_tank_masses_FCEV = []  # Liste zur Speicherung der einzelnen Tankmassen für den Plot der Normalverteilung --> in 'Mass_H2_FCEV' werden im Falle mehrerer Tankvorgänge im gleichen Zeitfenster akkumulierte Massen gespeichert

for month in range(12): # Schleife über die 12 Monate des Jahres
    num_tank_vorgange = df_monthly_refuel_prob_H2.loc[month, 'mass_FCEV'] / m_RE_avg_FCEV # Berechnung der Anzahl der Tankvorgänge für jeden Monat
    num_tank_vorgange = m.ceil(num_tank_vorgange) # Aufrunden der Anzahl der Tankvorgänge auf die nächste ganze Zahl
    random_numbers = np.random.rand(num_tank_vorgange) # Erzeugung von Zufallszahlen zwischen 0 und 1 für jeden Tankvorgang

    tank_times = [] # Initialisierung Liste für die Speicherung der Zeitpunkte der Tankvorgänge

    for rand_num in random_numbers: # Schleife über die generierten Zufallszahlen
        tank_time = df_load_H2.loc[df_load_H2['cumulative_prob'] >= rand_num, 'date'].iloc[0] # Finden des ersten Zeitpunktes, an dem die kumulative Wahrscheinlichkeit >= Zufallszahl ist
        tank_times.append(tank_time) # Hinzufügen des gefundenen Zeitpunktes zur Liste der Tankzeitpunkte
        df_load_H2.loc[df_load_H2['date'] == tank_time, 'refueling_event_FCEV'] += 1 # Erhöhen der Anzahl der Tankvorgänge zu diesem Zeitpunkt

    tank_masses = np.random.normal(m_RE_avg_FCEV, std_dev_H2_FCEV, len(tank_times)) # Generiert zufällig Tankmassen basierend auf einer Normalverteilung mit dem Mittelwert m_RE_avg_FCEV und der Standardabweichung std_dev_H2_FCEV
    tank_masses = np.clip(tank_masses, m_RE_min_FCEV, m_RE_max_FCEV) # Begrenze die möglichen auszuwählenden Tankmassen auf den Bereich zwischen m_RE_min_FCEV und m_RE_max_FCEV

    individual_tank_masses_FCEV.extend(tank_masses)  # Alle Tankmassen zur Liste hinzufügen

    for time, mass in zip(tank_times, tank_masses):  # Schleife über die Tankzeitpunkte und -massen
        df_load_H2.loc[df_load_H2['date'] == time, 'Mass_H2_FCEV'] += mass # Addiere die Tankmasse zur entsprechenden Zeit im DataFrame df_load_H2
        total_mass_FCEV += mass # Erhöht die Gesamttankmasse um die aktuelle Tankmasse

expected_H2_mass_FCEV = df_monthly_refuel_prob_H2['mass_FCEV'].sum() # Berechnet die erwartete Gesamtmasse an Wasserstoff für das Jahr
total_mass_FCEV, expected_H2_mass_FCEV # Ausgabe der tatsächlichen und erwarteten Gesamtmasse an Wasserstoff

n_fueling_points_FCEV = df_load_H2['refueling_event_FCEV'].max() # Maximal sinnvolle Anzahl an Zapfpunkten für FCEV (entspricht dem höchsten gleichzeitigen Aufkommen von Tankvorgängen)

# Lastkurve FCET
# Tankmassen FCET
m_Tank_avg_FCET = df_FCET_data['Tank capacity (kg)'].sum() / df_FCET_data[df_FCET_data["Tank capacity (kg)"] != 0].shape[0] # Durchschnittliche Masse H2 [kg] pro Refueling Event (durchschnittliche Tankgröße; Anpassung der tatsächlichen Tankmenge < Tankgröße erfolgt über Normalverteilung) für FCET
m_RE_min_FCET = m_Tank_avg_FCET*0.05 # Annahme: Kleinste Betankungsmenge = 5 % der Tankkapazität
m_RE_max_FCET = m_Tank_avg_FCET*0.95 # Annahme: Größte Betankungsmenge = 95 % der Tankkapazität
m_RE_avg_FCET = (m_RE_min_FCET + m_RE_max_FCET) / 2 # Durchschnittliche H2 Masse bei einem Refueling Event (Tankvorgang)
std_dev_H2_FCET = (m_RE_max_FCET - m_RE_min_FCET) / 6  # Standardabweichung für Normalverteilung: 99.7% der Werte liegen innerhalb von 3 Standardabweichungen

# Zuordnung Tankzeitpunkte und -massen
total_mass_FCET = 0 # Initialisierung der Variablen und Spalten für Zufallszahlen für Tankvorgänge
df_load_H2['refueling_event_FCET'] = 0 # 0 --> kein Tankvorgang innerhalb des Betrachtungszeitraums (15 min); 1 --> 1 Tankvorgang usw.
df_load_H2['Mass_H2_FCET'] = 0 
individual_tank_masses_FCET = []  # Liste zur Speicherung der einzelnen Tankmassen für den Plot der Normalverteilung --> in 'Mass_H2_FCEV' werden im Falle mehrerer Tankvorgänge im gleichen Zeitfenster akkumulierte Massen gespeichert

for month in range(12): # Schleife über die 12 Monate des Jahres
    num_tank_vorgange = df_monthly_refuel_prob_H2.loc[month, 'mass_FCET'] / m_RE_avg_FCET # Berechnung der Anzahl der Tankvorgänge für jeden Monat
    num_tank_vorgange = m.ceil(num_tank_vorgange) # Aufrunden der Anzahl der Tankvorgänge auf die nächste ganze Zahl
    random_numbers = np.random.rand(num_tank_vorgange) # Erzeugung von Zufallszahlen zwischen 0 und 1 für jeden Tankvorgang

    tank_times = [] # Initialisierung Liste für die Speicherung der Zeitpunkte der Tankvorgänge

    for rand_num in random_numbers: # Schleife über die generierten Zufallszahlen
        tank_time = df_load_H2.loc[df_load_H2['cumulative_prob'] >= rand_num, 'date'].iloc[0] # Finden des ersten Zeitpunktes, an dem die kumulative Wahrscheinlichkeit >= Zufallszahl ist
        tank_times.append(tank_time) # Hinzufügen des gefundenen Zeitpunktes zur Liste der Tankzeitpunkte
        df_load_H2.loc[df_load_H2['date'] == tank_time, 'refueling_event_FCET'] += 1 # Erhöhen der Anzahl der Tankvorgänge zu diesem Zeitpunkt

    tank_masses = np.random.normal(m_RE_avg_FCET, std_dev_H2_FCET, len(tank_times)) # Generiert zufällig Tankmassen basierend auf einer Normalverteilung mit dem Mittelwert m_RE_avg_FCET und der Standardabweichung std_dev_H2_FCET
    tank_masses = np.clip(tank_masses, m_RE_min_FCET, m_RE_max_FCET) # Begrenze die möglichen auszuwählenden Tankmassen auf den Bereich zwischen m_RE_min_FCET und m_RE_max_FCET

    individual_tank_masses_FCET.extend(tank_masses)  # Alle Tankmassen zur Liste hinzufügen

    for time, mass in zip(tank_times, tank_masses):  # Schleife über die Tankzeitpunkte und -massen
        df_load_H2.loc[df_load_H2['date'] == time, 'Mass_H2_FCET'] += mass # Addiere die Tankmasse zur entsprechenden Zeit im DataFrame df_load_H2
        total_mass_FCET += mass # Erhöht die Gesamttankmasse um die aktuelle Tankmasse

expected_H2_mass_FCET = df_monthly_refuel_prob_H2['mass_FCET'].sum() # Berechnet die erwartete Gesamtmasse an Wasserstoff für das Jahr
total_mass_FCET, expected_H2_mass_FCET # Ausgabe der tatsächlichen und erwarteten Gesamtmasse an Wasserstoff

n_fueling_points_FCET = df_load_H2['refueling_event_FCET'].max() # Maximal sinnvolle Anzahl an Zapfpunkten für FCET (entspricht dem höchsten gleichzeitigen Aufkommen von Tankvorgängen)

df_load_H2['Mass_H2_ges'] = df_load_H2['Mass_H2_FCEV'] + df_load_H2['Mass_H2_FCET']
df_load_H2['Energy (kWh)'] = df_load_H2['Mass_H2_ges'] * 33 # Umrechnung von kg H2 in kWh mit Energiedichte H2 = 33 KWh / kg
df_load_H2['Energy (MWh)'] = df_load_H2['Energy (kWh)'] / 1000 # Umrechnen von kWh in MWh

# Erstellung Nachfragekurve H2
df_load_H2_15min_mw = pd.DataFrame() # Neues DataFrame df_load_el_15min_mw als Inputdaten für pyPSA Netzwerk vorbereiten
df_load_H2_15min_mw['Energy (MWh)'] = df_load_H2['Energy (MWh)'] # Spalte "Energy (MWh) aus df_load_H2 kopieren
df_load_H2_15min_mw['time_input_year'] = pd.date_range(start=f'{year}-01-01 00:00', periods=35040, freq='15T') # Hinzufügen einer neuen Spalte mit den timestamps des Input-Jahres (Variable year); Periode = 35040 Viertelstunden pro Jahr
df_load_H2_15min_mw = df_load_H2_15min_mw.set_index(df_load_H2_15min_mw['time_input_year']) # Setzen der Spalte time_input_year als index
df_load_H2_15min_mw = df_load_H2_15min_mw.drop(columns=['time_input_year']) # Löschen der obsoleten weil doppelten Spalte time_input_year
df_load_H2_15min_mw['P (MW)'] = df_load_H2_15min_mw['Energy (MWh)'] / 0.25

#%% Generierung Inputdaten Electric Charging Station Load 

# DATEN EINLESEN
# BEV Daten
df_BEV_charging_data_Turku = pd.read_csv(f'{path}BEV_charging_data_Turku.csv', encoding = 'latin1', sep = ';') # Datensatz zu Ladevorgägen von BEV in Turku, Finnland: Quelle: https://doi.org/10.5281/zenodo.5721233    
df_BEV_charging_data_Barcelona = pd.read_csv(f'{path}BEV_charging_data_Barcelona.csv', encoding = 'latin1', sep = ';') # Datensatz zu Ladevorgägen von BEV in Barcelona, Spanien: Quelle: https://doi.org/10.5281/zenodo.5721233
df_BEV_charging_data_Korea = pd.read_csv(f'{path}BEV_charging_data_Korea.csv', encoding = 'latin1', sep = ',') # Datensatz zu Ladevorgägen von BEV (in Korea?) Quelle: https://figshare.com/articles/dataset/A_dataset_for_multi-faceted_analysis_of_electric_vehicle_charging_transactions/22495141/1?file=39952252
df_BEV_quantity = pd.read_csv(f'{path}BEV_quantity.csv', encoding = 'latin1', sep = ';') # Datensatz zu Anzahl an BEV --> wird aktuell nicht verwendet, da Berechnung BEV_Load über tatsächlich getankte Energiemengen aus Datensätzen --> nicht wie bei H2_Load Berechnung über Anzahl an KFZ, gefahrene km, Tankgröße etc notwendig
df_BEV_energy_quantities = pd.read_csv(f'{path}BEV_energy_quantities.csv', encoding = 'latin1', sep = ';') # Daten zu benötigten Energiemengen durch BEV aufgeteilt nach Art der Ladeinfrastruktur; Zusammengetragen aus: https://nationale-leitstelle.de/wp-content/uploads/2024/06/Studie-LIS-2025-2030-Neuauflage-2024.pdf

# BEV Daten aufbereiten
allowed_locations = ['public institution', 'public area', 'public parking lot']
df_BEV_charging_data_Korea = df_BEV_charging_data_Korea[df_BEV_charging_data_Korea['Location'].isin(allowed_locations)]
df_BEV_charging_data_Turku['timestamp'] = pd.to_datetime(df_BEV_charging_data_Turku['timestamp'], format='%d/%m/%Y %H.%M') # Konvertieren der Spalte "timestamp" in einen Datetime-Index
df_BEV_charging_data_Barcelona['timestamp'] = pd.to_datetime(df_BEV_charging_data_Barcelona['timestamp'], format='%d/%m/%Y %H.%M') # Konvertieren der Spalte "timestamp" in einen Datetime-Index
df_BEV_charging_data_Korea['timestamp'] = pd.to_datetime(df_BEV_charging_data_Korea['timestamp']) # Konvertieren der Spalte "timestamp" in einen Datetime-Index
df_BEV_charging_data_Barcelona.sort_values(by='timestamp', inplace=True) # Sortieren des DataFrames nach der "timestamp"-Spalte, da in csv-Datei andere Sortierung vorliegt
df_BEV_charging_data_Barcelona.reset_index(drop=True, inplace=True) # Zurücksetzen des Index, um sicherzustellen, dass er aufsteigend bleibt
df_BEV_charging_data_Barcelona = df_BEV_charging_data_Barcelona[df_BEV_charging_data_Barcelona['timestamp'].dt.year != 2018] # Filtern des DataFrame, um nur die Zeilen zu behalten, bei denen das Jahr nicht 2018 ist
df_BEV_charging_data_Korea.sort_values(by='timestamp', inplace=True) # Sortieren des DataFrames nach der "timestamp"-Spalte, da in csv-Datei andere Sortierung vorliegt
df_BEV_charging_data_Korea.reset_index(drop=True, inplace=True) # Zurücksetzen des Index, um sicherzustellen, dass er aufsteigend bleibt
BEV_energy_demand_charging_point_2030 = df_BEV_energy_quantities.loc[5, 'Energiemengen [TWh] 2030'] / df_BEV_energy_quantities.loc[5, 'Ladepunkte 2030'] * 10**9 # [kWh] Prognostizierter Energiebedarf pro Ladesäule 2030
BEV_energy_demand_charging_point_2035 = df_BEV_energy_quantities.loc[5, 'Energiemengen [TWh] 2035'] / df_BEV_energy_quantities.loc[5, 'Ladepunkte 2035'] * 10**9 # [kWh] Prognostizierter Energiebedarf pro Ladesäule 2035
charging_points = 8 # Quelle: https://www.autobahn.de/digitales-innovation/nachhaltigkeit/schnellladeinfrastruktur --> nach SchnellLG Ausbau von HPC Ladepunkten an Raststätten mit 8 Schnellladepunkten (min 200 max 300 kW) pro Standort
BEV_energy_demand_charging_station_2030 = BEV_energy_demand_charging_point_2030 * charging_points # [kWh] Prognostizierter Energiebedarf pro Standort 2030
BEV_energy_demand_charging_station_2035 = BEV_energy_demand_charging_point_2035 * charging_points # [kWh] Prognostizierter Energiebedarf pro Standort 2035
df_BEV_energy_refuel_station = pd.DataFrame({'year': [2030, 2035], 'BEV energy demand [kWh]': [BEV_energy_demand_charging_station_2030, BEV_energy_demand_charging_station_2035]}) # Speichern der berechneten Energiemengen in neuem DataFrame df_BEV_energy_refuel_station

# Berechnung Saisonale Tankwahrscheinlichkeit BEV
df_BEV_charging_data_Turku['Month'] = df_BEV_charging_data_Turku['timestamp'].dt.month # Extrahiere den Monat und das Jahr aus dem Timestamp
df_BEV_charging_data_Barcelona['Month'] = df_BEV_charging_data_Barcelona['timestamp'].dt.month # Extrahiere den Monat und das Jahr aus dem Timestamp
df_BEV_charging_data_Korea['Month'] = df_BEV_charging_data_Korea['timestamp'].dt.month # Extrahiere den Monat und das Jahr aus dem Timestamp
df_BEV_charging_data_Turku['Energy (kWh)'] = df_BEV_charging_data_Turku['Energy (Wh)'] / 1000 # Umrechnung von Wh in kWh
df_BEV_charging_data_Turku = df_BEV_charging_data_Turku[df_BEV_charging_data_Turku['Energy (kWh)'] > 0] # Löschen aller Spalten mit negativen Werten für geladene Energiemengen; Annahme: Diese Daten sind fehlerhaft
df_BEV_charging_data_Barcelona = df_BEV_charging_data_Barcelona[df_BEV_charging_data_Barcelona['Energy (kWh)'] > 0] # Löschen aller Spalten mit negativen Werten für geladene Energiemengen; Annahme: Diese Daten sind fehlerhaft
df_BEV_charging_data_Korea = df_BEV_charging_data_Korea[df_BEV_charging_data_Korea['Energy (kWh)'] > 0] # Löschen aller Spalten mit negativen Werten für geladene Energiemengen; Annahme: Diese Daten sind fehlerhaft

df_Turku_monthly = df_BEV_charging_data_Turku.groupby('Month')['Energy (kWh)'].sum().reset_index() # Summieren der Energiemengen pro Monat des DataFrames
df_Barcelona_monthly = df_BEV_charging_data_Barcelona.groupby('Month')['Energy (kWh)'].sum().reset_index() # Summieren der Energiemengen pro Monat des DataFrames
df_Korea_monthly = df_BEV_charging_data_Korea.groupby('Month')['Energy (kWh)'].sum().reset_index() # Summieren der Energiemengen pro Monat des Dataframes
df_monthly_refuel_prob_BEV = pd.merge(df_Turku_monthly, df_Barcelona_monthly, on='Month', how='outer', suffixes=('_Turku', '_Barcelona')) # Zusammenführen der monatlichen Summen aller DataFrames
df_monthly_refuel_prob_BEV = pd.merge(df_monthly_refuel_prob_BEV, df_Korea_monthly, on='Month', how='outer')
df_monthly_refuel_prob_BEV.rename(columns={'Energy (kWh)': 'Energy (kWh)_Korea'}, inplace=True)
df_monthly_refuel_prob_BEV['Energy (kWh)'] = df_monthly_refuel_prob_BEV['Energy (kWh)_Turku'] + df_monthly_refuel_prob_BEV['Energy (kWh)_Barcelona'] + df_monthly_refuel_prob_BEV['Energy (kWh)_Korea'] # Zusammenfügen der Energiemengen beider Städte
df_monthly_refuel_prob_BEV.drop(columns=['Energy (kWh)_Turku', 'Energy (kWh)_Barcelona', 'Energy (kWh)_Korea'], inplace=True) # Entfernen der separaten Spalten, da nur die Gesamtsumme benötigt wird
df_monthly_refuel_prob_BEV['Month'] = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
df_monthly_refuel_prob_BEV['Days in Month'] = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31] # Hinzufügen der Anzahl der Tage für jeden Monat
df_monthly_refuel_prob_BEV['avg daily csmptn (kWh)'] = df_monthly_refuel_prob_BEV['Energy (kWh)'] / df_monthly_refuel_prob_BEV['Days in Month'] # Berechnung der durchschnittlichen täglichen Energieverbrauch in kWh für jeden Monat
sum_avg_daily_csmptn = df_monthly_refuel_prob_BEV['avg daily csmptn (kWh)'].sum()
df_monthly_refuel_prob_BEV['seasonal_refuel_prob'] = (df_monthly_refuel_prob_BEV['avg daily csmptn (kWh)'] / sum_avg_daily_csmptn) # [ ] Berechnung der saisonalen Tankwahrscheinlichkeit aus den um die Anzahl an Tagen pro Monat bereinigten Verbräuchen pro Monat und des Gesamtverbrauchs aller Monate

# Berechnung relative Tankwahrscheinlichkeit pro Tag BEV
df_BEV_charging_data = pd.concat([
    df_BEV_charging_data_Turku[['timestamp', 'Stop time', 'Duration', 'Energy (kWh)']],
    df_BEV_charging_data_Barcelona[['timestamp', 'Stop time', 'Duration', 'Energy (kWh)']],
    df_BEV_charging_data_Korea[['timestamp', 'Stop time', 'Duration', 'Energy (kWh)']]], ignore_index=True)
df_BEV_charging_data.sort_values(by='timestamp', inplace=True) # Sortieren des neuen DataFrames nach der "timestamp"-Spalte, um die Werte chronologisch vorliegen zu haben

df_BEV_charging_data.reset_index(drop=True, inplace=True) # Zurücksetzen des Index nach Umsortierung

# Schleife für die Zählung der Ladevorgänge pro Wochentag und Viertelstundenwert des Tages
quarters = [] # Erstellen einer Liste für die Viertelstundenwerte eines Tages

for hour in range(24):
    for minute in [0, 15, 30, 45]:
        start_time = f"{hour:02d}:{minute:02d}"
        end_time = f"{hour:02d}:{(minute + 15) % 60:02d}"
        if minute == 45:
            end_hour = hour + 1
            end_time = f"{end_hour:02d}:00"
        quarters.append(f"{start_time} - {end_time}")
weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] # Definition der Wochentage
results = [] # Erstellen einer leeren Liste, um die Ergebnisse zu speichern

for day in weekdays: # Durchlaufe jeden Wochentag
    df_day = df_BEV_charging_data[df_BEV_charging_data['timestamp'].dt.strftime('%a') == day] # Filtere die Daten für den aktuellen Wochentag
    df_day['Time'] = pd.cut(df_day['timestamp'].dt.hour * 4 + df_day['timestamp'].dt.minute // 15,
        bins=range(97),right=False,labels=quarters) # Füge eine Spalte für die Viertelstunde des Tages hinzu
    Time_counts = df_day.groupby('Time').size().reindex(quarters, fill_value=0).reset_index(name='n_refuel_events') # Zählen der Anzahl der Tankvorgänge pro Viertelstunde
    Time_counts['day'] = day # Hinzufüge einer Spalte für den Wochentag
    Time_counts = Time_counts[['day', 'Time', 'n_refuel_events']] # Reorganisieren der Spaltenreihenfolge
    results.append(Time_counts) # Hinzufügen der Ergebnisse zur Liste 

df_rel_refuel_prob_BEV = pd.concat(results, ignore_index=True) # Kombinieren aller DataFrames in der Liste zu einem einzigen DataFrame df_rel_refuel_prob_BEV
n_charging_events = df_BEV_charging_data.shape[0] # Zählen der gesamten Anzahl an Ladevorgängen
df_rel_refuel_prob_BEV['rel_refuel_prob'] = (df_rel_refuel_prob_BEV['n_refuel_events'] / n_charging_events)* 100 # [%] Wahrscheinlichkeit, dass ein Ladevorgang in der jeweiligen Viertelstunde der Woche stattfindet

# Aufteilen der Daten in Montag - Donnerstag und Freitag - Sonntag für Plot (in Anlehnung an Grüger)
weekdays_to_merge = ['Mon', 'Tue', 'Wed', 'Thu'] # Filtern der Daten für Montag bis Donnerstag
df_weekdays = df_rel_refuel_prob_BEV[df_rel_refuel_prob_BEV['day'].isin(weekdays_to_merge)]
df_rel_refuel_prob_BEV_mon_thur = df_weekdays.groupby('Time')['rel_refuel_prob'].sum().reset_index() # Gruppieren nach Viertelstunden und berechne die Summe der Wahrscheinlichkeiten für die 4 Tage
num_days = len(weekdays_to_merge) # Berechnen die Anzahl der Wochentage, die zusammengeführt werden (Montag bis Donnerstag = 4 Tage)
df_rel_refuel_prob_BEV_mon_thur['rel_refuel_prob'] = df_rel_refuel_prob_BEV_mon_thur['rel_refuel_prob'] / num_days# Berechnen des Durchschnitts der Wahrscheinlichkeiten
df_rel_refuel_prob_BEV_mon_thur['day'] = 'Mon-Thu' # Hinzufügen einer Spalte 'day' = Monday-Thursday
df_rel_refuel_prob_BEV_mon_thur = df_rel_refuel_prob_BEV_mon_thur[['day', 'Time', 'rel_refuel_prob']] # Reorganisieren der Spaltenreihenfolge
weekends = ['Fri', 'Sat', 'Sun'] # Filtern der Daten für Freitag bis Sonntag
df_weekends = df_rel_refuel_prob_BEV[df_rel_refuel_prob_BEV['day'].isin(weekends)]
df_weekends_grouped = df_weekends[['day', 'Time', 'rel_refuel_prob']] # Gruppieren nach Viertelstunden und beibehalten der Werte für jeden Tag in der gleichen Organisationsstrukutr
df_rel_refuel_prob_BEV_combined = pd.concat([df_rel_refuel_prob_BEV_mon_thur, df_weekends_grouped], ignore_index=True) # Zusammenfügen der DataFrames
df_rel_refuel_prob_BEV_combined = df_rel_refuel_prob_BEV_combined.pivot(index='Time', columns='day', values='rel_refuel_prob') # Aufteilen der Daten für die Wochentage in die einzelnen Spalten "Mon-Thu", "Fri", "Sat", "Sun"
df_rel_refuel_prob_BEV_combined.reset_index(inplace=True) # Zurücksetzen des Index
columns_order = ['Time', 'Mon-Thu', 'Fri', 'Sat', 'Sun'] # Definition der Spaltenreihenfolge
df_rel_refuel_prob_BEV_combined = df_rel_refuel_prob_BEV_combined[columns_order] # Definition der Spaltenreihenfolge
df_rel_refuel_prob_BEV_combined['Time'] = df_rel_refuel_prob_BEV_combined['Time'].str.split(' - ').str[0] # Anpassung der Spalte "Time" anpassen --> nur den ersten Zeitwert beibehalten, um gleiches Zeitformat (HH:MM) zu haben wie beim Code für die Wasserstoffnachrage

# Berechnung BEV-Bedarf für ein Jahr
#Interpolation bzw Extrapolation der benötigten Werte für das gewählte Jahr, falls Daten für das gewählte Jahr nicht vorliegen
def interpolate_value(df, year, column):
    interp_func = interpolate.interp1d(df['year'], df[column], fill_value="extrapolate", kind="slinear") # lineare Interpolation (bzw segmentiert linear) am sinnvollsten, da bei quadratischer zwischen zwei Punkten auch negative Werte möglich (zB bei Anzahl FCEV 2023), negative Anzahl an Autos ist aber unrealistisch und für Rechnung nicht praktikabel
    return interp_func(year)

# BEV Daten
BEV_energy_demand_refuel_station = interpolate_value(df_BEV_energy_refuel_station, year, 'BEV energy demand [kWh]') # [kWh] Interpolierte / Extrapolierte Energiemenge, die im gewählten Jahr zur Deckung des Bedarfs durch BEV an der Tankstelle benötigt wird 

# Berechnung benötigte Energiemenge für BEV
df_monthly_refuel_prob_BEV['Energy demand (kWh)'] = df_monthly_refuel_prob_BEV['seasonal_refuel_prob'] * BEV_energy_demand_refuel_station # [kWh] pro Monat nachgefragte Energiemenge durch BEV 

# Berechnung Ladezeitpunkte und Lade-Energiemengen für BEV - Schleife über alle Zeitintervalle des gewählten Jahres
start_date_load = f'{year}-01-01'
end_date_load = f'{year}-12-31 23:45'
date_range = pd.date_range(start=start_date_load, end=end_date_load, freq='15T') # Viertelstündliche Datumsliste für das oben ausgewählte Jahr
weekdays = date_range.strftime("%a") # Liste der Wochentage als Abkürzungen (Mo, Tue, Wed, usw.)
df_load_BEV = pd.DataFrame({'date': date_range,'weekday': weekdays}) # DataFrame für Berechnung der Wasserstoff-Nachfragekurve mit Spalten für Datum und Wochentag

rel_refuel_prob_values_BEV = [] # Initialisierung einer Liste für die relativen Ladewahrscheinlichkeiten
weekday_to_column = {'Mon': 'Mon-Thu','Tue': 'Mon-Thu','Wed': 'Mon-Thu','Thu': 'Mon-Thu','Fri': 'Fri','Sat': 'Sat','Sun': 'Sun'} # Definition der Wochentage (zB Dienstag gehört zu Montag bis Donnerstag), um die korrekten relativen Ladewahrscheinlichkeiten einzelnen Wochentagen zuordnen zu können

for index, row in df_load_BEV.iterrows(): # Iteration über die Zeilen im DataFrame zum Hinzufügen der relativen Ladewahrscheinlichkeiten als neue Spalte --> es wird dabei immer die relative Ladewahrscheinlichkeit mit dem passenden weekday und der passenden time aus df_rel_refuel_prob_BEV extrahiert
    weekday = row['weekday']
    column_name = weekday_to_column.get(weekday[:3])
    time = row['date'].strftime('%H:%M')
    refuel_prob_BEV = df_rel_refuel_prob_BEV_combined.loc[df_rel_refuel_prob_BEV_combined['Time'] == time, column_name].values[0]
    rel_refuel_prob_values_BEV.append(refuel_prob_BEV)

df_load_BEV['rel_refuel_prob'] = rel_refuel_prob_values_BEV # Speichern der Spalte rel_refuel_prob im neuen DataFrame
df_load_BEV['cumulative_prob'] = df_load_BEV['rel_refuel_prob'].cumsum() # Berechnung der kumulativen Summe der Wahrscheinlichkeitsverteilung
df_load_BEV['cumulative_prob'] /= df_load_BEV['cumulative_prob'].iloc[-1] # Normierung, so dass der letzte Wert 1 ist 
#df_load_BEV['date'] = df_load_BEV['date'].dt.tz_localize('UTC') # Hinzufügen der Zeitzone um dem Format des Elektrolyseur-Codes zu entsprechen; +00:00 ist UTC

# Lastkurve BEV
charge_energy_min = df_BEV_charging_data['Energy (kWh)'].min() # [kWh] Kleinste geladene Energiemenge des Datensatzes
charge_energy_max = df_BEV_charging_data['Energy (kWh)'].max() # [kWh] Größte geladene Energiemenge des Datensatzes
charge_energy_avg = (charge_energy_min + charge_energy_max) / 2 # Durchschnittliche H2 Masse bei einem Refueling Event (Tankvorgang)
std_dev_BEV = (charge_energy_max - charge_energy_min) / 6  # Standardabweichung für Normalverteilung: 99.7% der Werte liegen innerhalb von 3 Standardabweichungen

total_energy = 0 # Initialisierung der Variablen und Spalten für Zufallszahlen für Ladevorgänge
df_load_BEV['refueling_event'] = 0 # 0 --> kein Ladevorgang innerhalb des Betrachtungszeitraums (15 min); 1 --> 1 Ladevorgang usw.
df_load_BEV['Energy (kWh)'] = 0 
individual_tank_energies_BEV = []  # Liste zur Speicherung der einzelnen Ladeenergien für den Plot der Normalverteilung 

for month in range(12): # Schleife über die 12 Monate des Jahres
    num_charge_vorgange = df_monthly_refuel_prob_BEV.loc[month, 'Energy demand (kWh)'] / charge_energy_avg # Berechnung der Anzahl der Ladevorgänge für jeden Monat
    num_charge_vorgange = m.ceil(num_charge_vorgange) # Aufrunden der Anzahl der Ladevorgänge auf die nächste ganze Zahl
    random_numbers = np.random.rand(num_charge_vorgange) # Erzeugung von Zufallszahlen zwischen 0 und 1 für jeden Ladevorgang

    charging_times = [] # Initialisierung Liste für die Speicherung der Zeitpunkte der Ladevorgänge

    for rand_num in random_numbers: # Schleife über die generierten Zufallszahlen
        charge_time = df_load_BEV.loc[df_load_BEV['cumulative_prob'] >= rand_num, 'date'].iloc[0] # Finden des ersten Zeitpunktes, an dem die kumulative Wahrscheinlichkeit >= Zufallszahl ist
        charging_times.append(charge_time) # Hinzufügen des gefundenen Zeitpunktes zur Liste der Ladezeitpunkte
        df_load_BEV.loc[df_load_BEV['date'] == charge_time, 'refueling_event'] += 1 # Erhöhen der Anzahl der Ladevorgänge zu diesem Zeitpunkt

    charge_energies = np.random.normal(charge_energy_avg, std_dev_BEV, len(charging_times)) # Generiert zufällig Energiemengen basierend auf einer Normalverteilung mit dem Mittelwert charge_energy_avg und der Standardabweichung std_dev_BEV
    charge_energies = np.clip(charge_energies, charge_energy_min, charge_energy_max) # Begrenzt die möglichen auszuwählenden Energiemengen auf den Bereich zwischen charge_energy_min und charge_energy_max

    individual_tank_energies_BEV.extend(charge_energies)  # Alle Tankmassen zur Liste hinzufügen

    for time, energy in zip(charging_times, charge_energies):  # Schleife über die Ladezeitpunkte und -energien
        df_load_BEV.loc[df_load_BEV['date'] == time, 'Energy (kWh)'] += energy # Addiere die geladene Energie zur entsprechenden Zeit im DataFrame df_load_BEV
        total_energy += energy # Erhöht die gesamten geladenen Energiemenge um die aktuelle Energiemenge

expected_BEV_energy = df_monthly_refuel_prob_BEV['Energy demand (kWh)'].sum() # Berechnet die erwartete gesamte Energiemenge für das Jahr
total_energy, expected_BEV_energy # Ausgabe der tatsächlichen und erwarteten Energiemengen
df_load_BEV['Energy (MWh)'] = df_load_BEV['Energy (kWh)'] / 1000 # Umrechnen von kW in MW

n_charging_points = df_load_BEV['refueling_event'].max() # Maximal sinnvolle Anzahl an Ladepunkten für BEV (entspricht dem höchsten gleichzeitigen Aufkommen von Ladevorgängen)

df_load_el_15min_mw = pd.DataFrame() # Neues DataFrame df_load_el_15min_mw als Inputdaten für pyPSA Netzwerk vorbereiten
df_load_el_15min_mw['Energy (MWh)'] = df_load_BEV['Energy (MWh)'] # Spalte "Energy (MWh) aus df_load_BEV kopieren
df_load_el_15min_mw['time_input_year'] = pd.date_range(start=f'{year}-01-01', periods=35040, freq='15T') # Hinzufügen einer neuen Spalte mit den timestamps des Input-Jahres (Variable year); Periode = 35040 Viertelstunden pro Jahr
df_load_el_15min_mw = df_load_el_15min_mw.set_index(df_load_el_15min_mw['time_input_year']) # Setzen der Spalte time_input_year als index
df_load_el_15min_mw = df_load_el_15min_mw.drop(columns=['time_input_year']) # Löschen der obsoleten weil doppelten Spalte time_input_year
df_load_el_15min_mw['P (MW)'] = df_load_el_15min_mw['Energy (MWh)'] / 0.25

#%% Für Kapitel 9.1.6: Maximale Anzahl an Zapfpunkten und Tankleistung einstellen für FCEV

Hu_H2_mass = 33.33 # [kWh/kg]

P_max_fueling_point_FCEV = 2 # kg/min Quelle: Linde Datenblatt Mittelwert zwischen den angegebenen Füllleistungen 1 kg / min und 3 kg/min
P_max_fueling_point_FCEV = P_max_fueling_point_FCEV * 60 # kg/h
P_max_fueling_point_FCEV = P_max_fueling_point_FCEV * Hu_H2_mass # kW
P_max_fueling_point_FCEV = P_max_fueling_point_FCEV / 1000 # MW max Leistung pro Zapfpunkt

df_load_H2 = df_load_H2.set_index(df_load_H2['date']) # Setzen der Spalte date als index, damit df_load_H2 und df_load_H2_15_min_mw den gleichen Index haben
df_load_H2_15min_mw['refueling_event_FCEV'] = df_load_H2['refueling_event_FCEV'] # Spalte refuling_event_FCEV kopieren --> für spätere Analyse der Anzahl und Lasten der einzelnen Zapfpunkte

individual_tank_energies_FCEV = [value * Hu_H2_mass for value in individual_tank_masses_FCEV] # [kWh] Umrechnung der einzlenen Tankmassen (kg H2) in Energiemengen

for i in range(1, n_fueling_points_FCEV + 1): # Neue Spalten für die einzelnen Zapfpunkte für FCEV
    df_load_H2_15min_mw[f'Zapfpunkt FCEV {i}'] = 0

tank_energy_index = 0 # Index für die Werte aus individual_tank_energies_FCEV

for idx, row in df_load_H2_15min_mw.iterrows(): # Iteration über df_load_H2_15min_mw: Immer wenn ein refueling event stattfindet, wird ein Wert aus der Liste individual_tank_energies_BEV genommen und der ersten Ladesäule zugewiesen. Falls gleichzeitig zwei RE stattfinden, wird der zweite Wert aus individual_tank_energies_BEV der zweiten Ladesäule zugewiesen usw
    refueling_event = row['refueling_event_FCEV']  # Anzahl der Ladevorgänge

    if refueling_event > 0:
        refueling_event = int(refueling_event)  # Umwandlung in Integer
        tank_energy_index = int(tank_energy_index)  # Umwandlung in Integer
        energies = individual_tank_energies_FCEV[tank_energy_index:tank_energy_index + refueling_event] # Holt die entsprechenden Werte aus der Liste
        for col_idx, energy in enumerate(energies):         # Zuweisung der Werte zu den Spalten 'Zapfpunkt FCEV 1', 'Zapfpunkt FCEV 2', ... zu
            if col_idx < n_fueling_points_FCEV:  # Stellt sicher, dass die Anzahl der Zapfpunkte nicht überschritten wird
                df_load_H2_15min_mw.at[idx, f'Zapfpunkt FCEV {col_idx + 1}'] = energy
        for col_idx in range(refueling_event, n_fueling_points_FCEV): # Setzt den Rest der Zapfpunkte auf 0
            df_load_H2_15min_mw.at[idx, f'Zapfpunkt FCEV {col_idx + 1}'] = 0
        tank_energy_index += refueling_event # Aktualisiere den Index für die Liste
    else:
        for col_idx in range(1, n_fueling_points_FCEV + 1): # Wenn keine Tankvorgang, setze alle Zapfpunkte auf 0
            df_load_H2_15min_mw.at[idx, f'Zapfpunkt FCEV {col_idx}'] = 0

# Entfernen der Zapfpunkte, die einen Anteil von min_share_fueling_point_FCEV unterschreiten
fueling_columns_FCEV = [col for col in df_load_H2_15min_mw.columns if 'Zapfpunkt FCEV' in col] # Filtern der Spalten, die den Begriff 'Zapfpunkt FCEV' im Namen enthalten
fueling_points_FCEV_sum = df_load_H2_15min_mw[fueling_columns_FCEV].sum().sum() # [kWh] Berechnen der Summe aller Werte in den ausgewählten Spalten
df_charging_points_FCEV_sum = pd.DataFrame()
fueling_columns_FCEV = [col for col in df_load_H2_15min_mw.columns if col.startswith('Zapfpunkt FCEV')] # Liste für Spalten, deren Summe berechnet werden soll: Alle Spalten, die mit 'Zapfpunkt FCEV' starten
df_charging_points_FCEV_sum['Zapfpunkt FCEV Nr'] = fueling_columns_FCEV
df_charging_points_FCEV_sum['Sum [kWh]'] = [df_load_H2_15min_mw[col].sum() for col in fueling_columns_FCEV] # Summe Energie [kWh] pro Zapfpunkt
df_charging_points_FCEV_sum['Share [%]'] = df_charging_points_FCEV_sum['Sum [kWh]']/fueling_points_FCEV_sum*100 # Anteil des jeweiligen Zapfpunktes am gesamten Absatz an elektrsicher Energie für FCEV
relevant_fueling_columns_FCEV = df_charging_points_FCEV_sum.loc[df_charging_points_FCEV_sum['Share [%]'] > min_share_fueling_point_FCEV, 'Zapfpunkt FCEV Nr'].tolist() # Wenn 'Share [%] > min_share_fueling_point_FCEV wird der Zapfpunkt zur Liste der zu berücksichtigen Zapfpunkte hinzugefügt
df_load_H2_15min_mw['Energy FCEV (MWh)'] = df_load_H2_15min_mw[relevant_fueling_columns_FCEV].sum(axis=1) / 1000  # [MWh] Summe der Energien der relevanten Ladesäulen --> Neue Nachfragezeitreihe
df_load_H2_15min_mw['P FCEV (MW)'] = df_load_H2_15min_mw['Energy FCEV (MWh)'] / 0.25  # [MW] el Leistung --> Neue Nachfragezeitreihe

# Maximale Anzahl an Zapfsäulen und Tankleistung einstellen für FCET
P_max_fueling_point_FCET = 2 # kg/min Quelle: Linde Datenblatt Mittelwert zwischen den angegebenen Füllleistungen 1 kg / min und 3 kg/min
P_max_fueling_point_FCET = P_max_fueling_point_FCET * 60 # kg/h
P_max_fueling_point_FCET = P_max_fueling_point_FCET * Hu_H2_mass # kW
P_max_fueling_point_FCET = P_max_fueling_point_FCET / 1000 # MW max Leistung pro Zapfpunkt
df_load_H2_15min_mw['refueling_event_FCET'] = df_load_H2['refueling_event_FCET'] # Spalte refuling_event_FCET kopieren --> für spätere Analyse der Anzahl und Lasten der einzelnen Zapfpunkte

individual_tank_energies_FCET = [value * Hu_H2_mass for value in individual_tank_masses_FCET] # [kWh] Umrechnung der einzlenen Tankmassen (kg H2) in Energiemengen

for i in range(1, n_fueling_points_FCET + 1): # Erstellt neue Spalten für die einzelnen Zapfpunkte für FCET
    df_load_H2_15min_mw[f'Zapfpunkt FCET {i}'] = 0

tank_energy_index = 0 # Index für die Werte aus individual_tank_energies_FCET

for idx, row in df_load_H2_15min_mw.iterrows(): # Iteration über die Zeilen des DataFrames: Immer wenn ein refueling event stattfindet, wird ein Wert aus der Liste individual_tank_energies_BEV genommen und der ersten Ladesäule zugewiesen. Falls gleichzeitig zwei RE stattfinden, wird der zweite Wert aus individual_tank_energies_BEV der zweiten Ladesäule zugewiesen usw
    refueling_event = row['refueling_event_FCET']  # Anzahl der Ladevorgänge

    if refueling_event > 0:
        refueling_event = int(refueling_event)  # Umwandlung in Integer
        tank_energy_index = int(tank_energy_index)  # Umwandlung in Integer
        energies = individual_tank_energies_FCET[tank_energy_index:tank_energy_index + refueling_event] # Holt die entsprechenden Werte aus der Liste
        for col_idx, energy in enumerate(energies): # Weisen die Werte den Spalten 'Zapfpunkt FCET 1', 'Zapfpunkt FCET 2', ... zu
            if col_idx < n_fueling_points_FCET:  # Sicherstellen, dass die Anzahl der Zapfpunkte nicht überschritten wird
                df_load_H2_15min_mw.at[idx, f'Zapfpunkt FCET {col_idx + 1}'] = energy
        for col_idx in range(refueling_event, n_fueling_points_FCET): # Setzt den Rest der Zapfpunkte auf 0
            df_load_H2_15min_mw.at[idx, f'Zapfpunkt FCET {col_idx + 1}'] = 0
        tank_energy_index += refueling_event # Aktualisiert den Index für die Liste
    else:
        for col_idx in range(1, n_fueling_points_FCET + 1): # Wenn keine Tankvorgang, setze alle Zapfpunkte auf 0
            df_load_H2_15min_mw.at[idx, f'Zapfpunkt FCET {col_idx}'] = 0

# Entfernen der Zapfpunkte, die einen Anteil von min_share_fueling_point_FCET unterschreiten
fueling_columns_FCET = [col for col in df_load_H2_15min_mw.columns if 'Zapfpunkt FCET' in col] # Filtern der Spalten, die den Begriff 'Zapfpunkt FCET' im Namen enthalten
fueling_points_FCET_sum = df_load_H2_15min_mw[fueling_columns_FCET].sum().sum() # [kWh] Berechnen der Summe aller Werte in den ausgewählten Spalten
df_charging_points_FCET_sum = pd.DataFrame()
fueling_columns_FCET = [col for col in df_load_H2_15min_mw.columns if col.startswith('Zapfpunkt FCET')] # Liste für Spalten, deren Summe berechnet werden soll: Alle Spalten, die mit 'Zapfpunkt FCET' starten
df_charging_points_FCET_sum['Zapfpunkt FCET Nr'] = fueling_columns_FCET
df_charging_points_FCET_sum['Sum [kWh]'] = [df_load_H2_15min_mw[col].sum() for col in fueling_columns_FCET] # Summe Energie [kWh] pro Zapfpunkt
df_charging_points_FCET_sum['Share [%]'] = df_charging_points_FCET_sum['Sum [kWh]']/fueling_points_FCET_sum*100 # Anteil des jeweiligen Zapfpunktes am gesamten Absatz an elektrsicher Energie für FCET
relevant_fueling_columns_FCET = df_charging_points_FCET_sum.loc[df_charging_points_FCET_sum['Share [%]'] > min_share_fueling_point_FCET, 'Zapfpunkt FCET Nr'].tolist() # Wenn 'Share [%] > min_share_fueling_point_FCEV wird der Zapfpunkt zur Liste der zu berücksichtigen Zapfpunkte hinzugefügt
df_load_H2_15min_mw['Energy FCET (MWh)'] = df_load_H2_15min_mw[relevant_fueling_columns_FCET].sum(axis=1) / 1000  # [MWh] Summe der Energien der relevanten Ladesäulen --> Neue Nachfragezeitreihe
df_load_H2_15min_mw['P FCET (MW)'] = df_load_H2_15min_mw['Energy FCET (MWh)'] / 0.25  # [MW] el Leistung --> Neue Nachfragezeitreihe

# Begrenzung max Last durch Anzahl an Zapfsäulen und max Last pro Zapfsäule
# Definition max Last Pel für FCEV
n_fueling_points_FCEV = len(relevant_fueling_columns_FCEV) # Anzahl an Zapfsäulen ergibt sich aus Anzahl an Einträgen in der Liste relevant_fueling_columns_FCEV
P_max_el_load_FCEV = n_fueling_points_FCEV * P_max_fueling_point_FCEV # [MW] max el Last durch FECV an der Tankstelle
df_load_H2_15min_mw['P FCEV (MW)'] = df_load_H2_15min_mw['P FCEV (MW)'].clip(upper=P_max_el_load_FCEV) # Begrenzen der Nachfrage auf P_max_el_load_FCEV
df_load_H2_15min_mw['Energy FCEV (MWh)'] = df_load_H2_15min_mw['P FCEV (MW)'] * 0.25

# Definition max Last Pel für FCET
n_fueling_points_FCET = len(relevant_fueling_columns_FCET) # Anzahl an Zapfsäulen ergibt sich aus Anzahl an Einträgen in der Liste relevant_fueling_columns_FCEV
P_max_el_load_FCET = n_fueling_points_FCET * P_max_fueling_point_FCET # [MW] max el Last durch FECT an der Tankstelle
df_load_H2_15min_mw['P FCET (MW)'] = df_load_H2_15min_mw['P FCET (MW)'].clip(upper=P_max_el_load_FCET) # Begrenzen der Nachfrage auf P_max_el_load_FCET
df_load_H2_15min_mw['Energy FCET (MWh)'] = df_load_H2_15min_mw['P FCET (MW)'] * 0.25

# Zusammenführen der FCEV und FCET Werte
df_load_H2_15min_mw['Energy new (MWh)'] = df_load_H2_15min_mw['Energy FCEV (MWh)'] + df_load_H2_15min_mw['Energy FCET (MWh)']
df_load_H2_15min_mw['P new (MW)'] = df_load_H2_15min_mw['P FCEV (MW)'] + df_load_H2_15min_mw['P FCET (MW)']

filename = 'load_h2_15min_mw.csv'
os.makedirs(output_path, exist_ok=True)
full_path = output_path + filename
df_load_H2_15min_mw.to_csv(full_path, index=True)

#%% Maximale Anzahl an Ladesäulen und Ladeleistung einstellen (BEV)

P_max_charging_point = 0.2 # [MW] max Leistung pro Ladepunkt
df_load_BEV = df_load_BEV.set_index(df_load_BEV['date']) # Setzen der Spalte date als index, damit df_load_BEV und df_load_el_15_min_mw den gleichen Index haben
df_load_el_15min_mw['refueling_event'] = df_load_BEV['refueling_event'] # Spalte refuling_event kopieren --> für spätere Analyse der Anzahl und Lasten der einzelnen Ladesäulen

for i in range(1, n_charging_points + 1): # Erstellt neue Spalten für die einzelnen Ladesäulen
    df_load_el_15min_mw[f'Ladesäule {i}'] = 0

tank_energy_index = 0 # Index für die Werte aus individual_tank_energies_BEV

for idx, row in df_load_el_15min_mw.iterrows(): # Iteriert über die Zeilen des DataFrames: Immer wenn ein refueling event stattfindet, wird ein Wert aus der Liste individual_tank_energies_BEV genommen und der ersten Ladesäule zugewiesen. Falls gleichzeitig zwei RE stattfinden, wird der zweite Wert aus individual_tank_energies_BEV der zweiten Ladesäule zugewiesen usw
    refueling_event = row['refueling_event']  # Anzahl der Ladevorgänge
    if refueling_event > 0:
        refueling_event = int(refueling_event)  # Umwandlung in Integer
        tank_energy_index = int(tank_energy_index)  # Umwandlung in Integer
        energies = individual_tank_energies_BEV[tank_energy_index:tank_energy_index + refueling_event] # Holt die entsprechenden Werte aus der Liste
        for col_idx, energy in enumerate(energies): # Zuweisen der Werte zu den Spalten 'Ladesäule 1', 'Ladesäule 2',..
            if col_idx < n_charging_points:  # Sicherstellen, dass die Anzahl der Ladesäulen nicht überschritten wird
                df_load_el_15min_mw.at[idx, f'Ladesäule {col_idx + 1}'] = energy
        for col_idx in range(refueling_event, n_charging_points): # Setzt den Rest der Ladesäulen auf 0
            df_load_el_15min_mw.at[idx, f'Ladesäule {col_idx + 1}'] = 0
        tank_energy_index += refueling_event # Aktualisiere den Index für die Liste
    else:
        for col_idx in range(1, n_charging_points + 1): # Wenn keine Ladevorgänge, setze alle Ladesäulen auf 0
            df_load_el_15min_mw.at[idx, f'Ladesäule {col_idx}'] = 0

# Entfernen der Ladesäulen, die einen Anteil von min_share_charging_point unterschreiten
charging_columns = [col for col in df_load_el_15min_mw.columns if 'Ladesäule' in col] # Filtern der Spalten, die den Begriff 'Ladesäule' im Namen enthalten
charging_points_sum = df_load_el_15min_mw[charging_columns].sum().sum() # [kWh] Berechnen der Summe aller Werte in den ausgewählten Spalten
df_charging_points_sum = pd.DataFrame()
charging_columns = [col for col in df_load_el_15min_mw.columns if col.startswith('Ladesäule')] # Liste für Spalten, deren Summe berechnet werden soll: Alle Spalten, die mit 'Ladesäule' starten
df_charging_points_sum['Ladesäule Nr'] = charging_columns
df_charging_points_sum['Sum [kWh]'] = [df_load_el_15min_mw[col].sum() for col in charging_columns] # Summe Energie [kWh] pro Ladesäule
df_charging_points_sum['Share [%]'] = df_charging_points_sum['Sum [kWh]']/charging_points_sum*100 # Anteil der jeweilingen Ladesäule am gesamten Absatz an elektrsicher Energie für BEV
relevant_charging_columns = df_charging_points_sum.loc[df_charging_points_sum['Share [%]'] > min_share_charging_point, 'Ladesäule Nr'].tolist() # Wenn 'Share [%] > min_share_charging_point wird die Ladesäule zur Liste der zu berücksichtigen Ladesäulen hinzugefügt
df_load_el_15min_mw['Energy new (MWh)'] = df_load_el_15min_mw[relevant_charging_columns].sum(axis=1) / 1000  # [MWh] Summe der Energien der relevanten Ladesäulen --> Neue Nachfragezeitreihe
df_load_el_15min_mw['P new (MW)'] = df_load_el_15min_mw['Energy new (MWh)'] / 0.25  # [MW] el Leistung --> Neue Nachfragezeitreihe

# Begrenzung max Last durch Anzahl an Zapfsäulen und max Last pro Zapfsäule
n_charging_points = len(relevant_charging_columns) # Anzahl an Ladesäulen ergibt sich aus Anzahl an Einträgen in der Liste relevant_charging_columns
P_max_el_load_BEV = n_charging_points * P_max_charging_point # [MW] max el Last durch BEV an der Ladestation
df_load_el_15min_mw['P new (MW)'] = df_load_el_15min_mw['P new (MW)'].clip(upper=P_max_el_load_BEV) # Begrenzen der Nachfrage auf P_max_el_load_BEV
df_load_el_15min_mw['Energy new (MWh)'] = df_load_el_15min_mw['P new (MW)'] * 0.25

filename = 'BEV_load_el_15min_mw.csv'
os.makedirs(output_path, exist_ok=True)
full_path = output_path + filename
df_load_el_15min_mw.to_csv(full_path, index=True)

#%% Daten H2 - und elctric load wieder einlesen --> Nachfragemodellierung für FCEV, FCET und BEV kann für mehrere Simulationen des gleichen Jahres ausgelassen werden
df_load_H2_15min_mw = pd.read_csv(f'{output_path}load_h2_15min_mw.csv', sep=',', decimal='.')
df_load_H2_15min_mw.set_index('time_input_year', inplace=True)
df_load_H2_15min_mw.index = pd.to_datetime(df_load_H2_15min_mw.index)

df_load_el_15min_mw = pd.read_csv(f'{output_path}BEV_load_el_15min_mw.csv', sep=',', decimal='.')
df_load_el_15min_mw.set_index('time_input_year', inplace=True)
df_load_el_15min_mw.index = pd.to_datetime(df_load_el_15min_mw.index)

#%% Parameter definieren

#Hydrogen
Hu_H2_mass = 33.33 # [kWh/kg] Quelle: https://www.dihk.de/resource/blob/24872/fd2c89df9484cf912199041a9587a3d6/energie-dihk-faktenpapier-wasserstoff-data.pdf
Hu_H2_vol = 2.995 # [kWh/Nm3] Quelle: https://gammel.de/de/lexikon/Heizwert---Brennwert/4838

# Grid
df_electricity_prices_europe = pd.read_csv(f'{path}Strom_Grosshandelspreise_2019.csv', header=0, sep=";", decimal=',') # Quelle: https://www.smard.de/home/downloadcenter/download-marktdaten/?downloadAttributes=%7B%22selectedCategory%22:3,%22selectedSubCategory%22:8,%22selectedRegion%22:%22DE%22,%22selectedFileType%22:%22CSV%22,%22from%22:1546297200000,%22to%22:1577833199999%7D
df_electricity_prices_europe['time_input_year'] = pd.date_range(start=f'{year}-01-01', periods=35040, freq='15T') # Hinzufügen einer neuen Spalte mit den timestamps des Input-Jahres (Variable year); Periode von 35037 weil letzte Stunde des Jahres fehlt, ansonsten wären es 35040 Viertelstunden pro Jahr
df_electricity_prices_europe = df_electricity_prices_europe.set_index(df_electricity_prices_europe['time_input_year'])
df_electricity_prices_europe = df_electricity_prices_europe.drop(columns=['Datum von', 'Datum bis', 'time_input_year'])

concession_fee = 0.11 / 100 * 1000 # [€/MWh] Quelle: https://www.bdew.de/service/daten-und-grafiken/bdew-strompreisanalyse/
KWKG_allocation = 0.28 / 100 * 1000 # [€/MWh] Quelle: https://www.bdew.de/service/daten-und-grafiken/bdew-strompreisanalyse/
StromNEV_allocation = 0.4 / 100 * 1000 # [€/MWh] Quelle: https://www.bdew.de/service/daten-und-grafiken/bdew-strompreisanalyse/
offshore_net_allocation = 0.66 / 100 * 1000 # [€/MWh] Quelle: https://www.bdew.de/service/daten-und-grafiken/bdew-strompreisanalyse/
electricity_tax = 0.05 / 100 * 1000 # [€/MWh] Quelle: https://www.bdew.de/service/daten-und-grafiken/bdew-strompreisanalyse/
df_electricity_prices_europe['Deutschland inkl. tax [€/MWh]'] = df_electricity_prices_europe['Deutschland/Luxemburg [€/MWh] Berechnete Auflösungen'] + concession_fee + KWKG_allocation + StromNEV_allocation + offshore_net_allocation + electricity_tax # Strompreis inkl. Steuern und Abgaben für Industriekunden

mean_value_pre_taxes = df_electricity_prices_europe['Deutschland/Luxemburg [€/MWh] Berechnete Auflösungen'].mean()
mean_value_post_taxes = df_electricity_prices_europe['Deutschland inkl. tax [€/MWh]'].mean()

ELECTRICITY_RATE = df_electricity_prices_europe['Deutschland inkl. tax [€/MWh]'] # €/MWh Annahme: Dynamischer Strompreisvertrag mit Energieversorger --> Preise schwanken abhängig vom Zeitpunkt der Nutzung

taxes_ref_station = 0.4 # Annahme: Steuern und Abgaben: 40%, hängt von Rechtsform des Unternehmens, Umfang der Erlöse ab
INFEED_RATE_PV = -6.47 # [ct/kWh] aktuelle Einspeisevergütung nach EEG für Freiflächenanlagen > 1MW, Quelle: https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/ErneuerbareEnergien/EEG_Foerderung/start.html
INFEED_RATE_PV = INFEED_RATE_PV / 100 * 1000 # [€/MWh]
INFEED_RATE_PV = INFEED_RATE_PV * (1-taxes_ref_station) # Annahme: Steuern und Abgaben: 30%

INFEED_RATE_WIND = -7.33 # [ct/kWh] Durchschnittswert seit Februar 2023; Quelle: https://www.windbranche.de/wirtschaft/eeg-verguetung/eeg-ausschreibungen
INFEED_RATE_WIND = INFEED_RATE_WIND / 100 * 1000 # [€/MWh]
INFEED_RATE_WIND = INFEED_RATE_WIND * (1-taxes_ref_station) # Annahme: Steuern und Abgaben: 30%
H2_rev = -0.0005 # [€/MWh] Annahme; Quelle: hier angeben; noch nicht integriert--> EVTL H2_load ALS NEGATIVEN GENERATOR???

# PV
PV_P_scal = 1.5 # [MWp] - Tatsächliche Leistung der PV-Anlage, welche die Input-Daten bereitstellt. Quelle: https://www.renewables.ninja/
PV_P_PU = df_pv_15min_mw['electricity']/PV_P_scal # Skalierung auf 1 MWp
LIFESPAN_PV = 20  # [Years]

# Wind
WIND_P_scal = 5.6 # [MW] - Tatsächliche Leistung des Windparks, welcher die Input-Daten bereitstellt. Quelle: https://www.renewables.ninja/
WIND_P_PU = df_wind_15min_mw['electricity']/WIND_P_scal # Skalierung auf 1 MW
LIFESPAN_WIND = 20  # [Years]

# Electrolyzer
eta_electrolyzer = 0.7 # Vereinfachung

# Electricity Storage
capital_costs_el_storage_kw = 1527 # [€/kW] Annahmen: Moderates Kostenszenario;für 4hr durchschnittliche Speicherdauer; cost recovery period 30 years; 1$ = 1 €. Quelle: https://www.nrel.gov/docs/fy21osti/78694.pdf
OM_el_storage = 0.5125 # [€/MWh] Kosten für Operation and Maintenance. Annahmen: Moderates Kostenszenario;für 4hr durchschnittliche Speicherdauer; cost recovery period 30 years. Quelle: https://www.nrel.gov/docs/fy21osti/78694.pdf
capital_cost_el_storage_mw = capital_costs_el_storage_kw*1000 # [€/MW]

# H2 Storage
cost_H2_storage_US = 0.17 # [$/kgH2] Annahme: 1€ = 1.06$; Szenario= Possible future LCOS aus der Quelle: https://assets.bbhub.io/professional/sites/24/BNEF-Hydrogen-Economy-Outlook-Key-Messages-30-Mar-2020.pdf
cost_H2_storage_EU = cost_H2_storage_US * (1/1.06) # [€/kgH2]
cost_H2_storage_mwh = cost_H2_storage_EU * (1/Hu_H2_mass) * 1000 # [€/MWh]

# Compressor
eta_compressor_H2_flow = 0.8 # Annahme
p_in = 30e5 # [Pa] Ausgangsdruck aus Elektrolyseurmodell
p_out = 1000e5 # [Pa] Zieldruck Quelle: Grüger - Initialinfrastruktur für Wasserstoffmobilität
T_in = 293.15 # [K]
T_cooling = 323.15 # [K] Annahme
T_max = 135 + 273.15 # [K] Quelle: Reciprocating Compressors, Wert für wasserstoffreiche Gase
dt = 0.25*3600 # s
dt_h = 0.25 # h
dp = 1e5 # [Pa] Druckinkrement
eta_isentrop = 0.88 # Quelle: Reuß - Techno-ökonomische Analyse alternativer Wasserstoffinfrastruktur
eta_mech = 0.95 # Quelle: Reuß - Techno-ökonomische Analyse alternativer Wasserstoffinfrastruktur
k = 1.41 #Isentropenexponent
dp_max = 4 # Maximales Druckverhältnis des Verdichters (bauseitig) Quelle: Krieg Annahme: "Verdichterverhältnis" in Quelle meint Druckverhältnis, da Verdichterverhältnis idR nur im Motorenbereich eingesetzt wird
COP_cooling = 4 # Quelle:Experimental analysis of a PEMFC-based CCP system integrated with adsorption chiller; Table 7 Mittelwert aus Literatur

#%% Anpassung der Netzwerk Inputdaten an Betrachtungsdauer (falls kürzer als ein Jahr)

# Für Variablen Startzeitpunkt der Simulation: Berechnung der Anzahl an 15 min Werten zwischen Start des Jahres und Start des Betrachtungszeitraums der Simulation
start_date_ts = pd.Timestamp(start_date) # Startzeitpunkt der Simulation als Datetime Objekt
n_snapshots = length * 24 * 1 / dt_h # Anzahl an 15 min Werten in Betrachtungszeitraum
time_delta_sim = pd.Timedelta(minutes=15 * (n_snapshots-1)) # Zeitdifferenz zwischen Startzeitpunkt der Simulation und Endzeitpunkt (in Abhängigkeit der Länge des Betrachtungsraumes bzw. n_snapshots)
end_date_ts = start_date_ts + time_delta_sim # Endzeitpunkt der Simulation als Datetime Objekt
PV_P_PU = PV_P_PU.loc[start_date_ts:end_date_ts] # Begrenzen der Serie auf die Betrachtungsdauer
WIND_P_PU = WIND_P_PU.loc[start_date_ts:end_date_ts] # Begrenzen der Serie auf die Betrachtungsdauer
ELECTRICITY_RATE = ELECTRICITY_RATE.loc[start_date_ts:end_date_ts] # Begrenzen der Serie auf die Betrachtungsdauer
df_load_H2_15min_mw = df_load_H2_15min_mw.loc[start_date_ts:end_date_ts] # Begrenzen der Serie auf die Betrachtungsdauer
df_load_el_15min_mw = df_load_el_15min_mw.loc[start_date_ts:end_date_ts] # Begrenzen der Serie auf die Betrachtungsdauer

#%% Für Kapitel 9.1.4 --> Leistung Elektrolyseur in Abhängigkeit der EE Erzeugerleistung einstellen --> setze p_nom=P_NOM_electrolyzer für Link 'electrolyzer' mit statischer Last
ratio_P_elektrolyzer_to_P_EE = 0.4
P_PV = PV_P_PU * PV_P_NOM
peak_PV_production = P_PV.max()
P_Wind = WIND_P_PU * WIND_P_NOM
peak_Wind_production = P_Wind.max()
peak_EE_production = peak_PV_production + peak_Wind_production
P_NOM_electrolyzer = (PV_P_NOM + WIND_P_NOM) * ratio_P_elektrolyzer_to_P_EE

#%% Netzwerk definieren

n = pypsa.Network() # Erstellen des PyPSA-Netzwerks

# start date bei Input definiert
end_date = pd.to_datetime(start_date) + pd.Timedelta(minutes=15 * (n_snapshots - 1))
index = pd.date_range(start=start_date, end=end_date, freq='15min')
n.set_snapshots(index) # Setzen der Anzahl an Snapshots gleich der Anzahl an Elementen in der Zeitreihe
n.snapshot_weightings = pd.Series(0.25, index=n.snapshots)  # Gewichtung für 15 Minuten

# Carrier
n.add("Carrier", "AC")
n.add("Carrier", "wind")
n.add("Carrier", "pv")
n.add("Carrier", "hydrogen")

# Busse
n.add('Bus', 'pv_bus', carrier = "pv") # verbindet pv-Generator, pv-infeed und pv_to_el
n.add('Bus', 'electricity_bus', carrier = "AC") # verbindet pv_to_el, grid (Stromnetz) und electrolyzer
n.add('Bus', 'H2_bus', carrier = "hydrogen") # verbindet electrolyzer, H2_load und H2_storage_bus
n.add('Bus', 'H2_storage_bus', carrier = "hydrogen") # verbindet H2_bus und H2_storage
n.add('Bus', 'el_storage_bus', carrier = "AC") # verbindet electricity_bus und el_storage
n.add('Bus', 'H2_comp_bus', carrier = "hydrogen") # verbindet compressor_h2_flow, H2_load sowie H2_storage_charge und H2_storage_discharge
n.add('Bus', 'wind_bus', carrier = "wind") # verbindet wind-Generator, wind-infeed und wind_to_el

# Generatoren
n.add('Generator', 'pv', bus='pv_bus', carrier = "pv", p_nom=PV_P_NOM, p_max_pu=PV_P_PU) # PV-Anlage, p_nom=PV_P_NOM legt die Anlagenleistung [MWp] fest, mit p_max_pu=PV_P_PU werden die auf 1 MWp skalierten Werte per Unit Leistungswerte der PV-Anlage definiert
n.add('Generator', 'pv_infeed', bus='pv_bus', carrier = "pv", p_nom=PV_P_NOM, p_max_pu=PV_P_PU, marginal_cost=INFEED_RATE_PV, sign=-1) # Einspeisung von Überschussstrom der PV-Anlage (p_nom_extendable=True für keine Obergrenze der Einspeisung, marginal_cost entspricht der Einspeisevergütung, sign=-1 für Leistungsentnahme aus dem Bus)
n.add('Generator', 'wind', bus='wind_bus', carrier = "wind", p_nom=WIND_P_NOM, p_max_pu=WIND_P_PU) # Windkraftanlage, p_nom=WIND_P_NOM legt die Anlagenleistung [MW] fest, mit p_max_pu=WIND_P_PU werden die auf 1 MW skalierten Werte per Unit Leistungswerte der WKA definiert
n.add('Generator', 'wind_infeed', bus='wind_bus', carrier = "wind", p_nom=WIND_P_NOM, p_max_pu=WIND_P_PU, marginal_cost=INFEED_RATE_PV, sign=-1) # Einspeisung von Überschussstrom der PV-Anlage (p_nom_extendable=True für keine Obergrenze der Einspeisung, marginal_cost entspricht der Einspeisevergütung, sign=-1 für Leistungsentnahme aus dem Bus)
n.add('Generator', 'grid', bus='electricity_bus', carrier = "AC", p_nom_extendable=True, marginal_cost=ELECTRICITY_RATE) # Stromnetzanschluss, p_nom_extendable=True für keine Obergrenze bei Netzbezug, marginal_cost=ELECTRICITY_RATE für Berücksichtigung der Kosten des Netzstroms

# Links
n.add('Link', 'pv_to_el', bus0='pv_bus', bus1='electricity_bus', p_nom_extendable=True, marginal_cost=0) # Verbindung pv_bus mit electricity_bus
n.add('Link', 'wind_to_el', bus0='wind_bus', bus1='electricity_bus', p_nom_extendable=True, marginal_cost=0) # Verbindung wind_bus mit electricity_bus
n.add('Link', 'electrolyzer', bus0='electricity_bus', bus1='H2_bus', p_nom_extendable=True, marginal_cost=0, efficiency = 1) # Aus diesem Link heraus wird eine csv exportiert, die als Input für den Elektrolyseur-Code von Sciebo_Original_Saur dient, efficiency = eta_electrolyzer, um eine grobe, vereinfachte Version des Netzes zu berechnen und compressor_el_load sowie richtige Menge an H2-Energie für weitere Berechnungen zu haben
n.add('Link', 'H2_storage_charge', bus0='H2_comp_bus', bus1='H2_storage_bus', p_nom=P_H2_store, marginal_cost=0) # Verbindung H2_bus mit H2_storage_bus zum Laden von H2_storage
n.add('Link', 'H2_storage_discharge', bus0='H2_storage_bus', bus1='H2_comp_bus', p_nom=P_H2_store, marginal_cost=0) # Verbindung H2_storage_bus mit H2_bus zum Entladen von H2_storage
n.add('Link', 'el_storage_charge', bus0='electricity_bus', bus1='el_storage_bus', p_nom=P_el_store, marginal_cost=0) # Verbindung electricity_bus mit el_storage_bus zum Laden von el_storage
n.add('Link', 'el_storage_discharge', bus0='el_storage_bus', bus1='electricity_bus', p_nom=P_el_store, marginal_cost=0) # Verbindung el_storage_bus mit electricity_bus zum Entladen von el_storage
n.add('Link', 'compressor_h2_flow', bus0='H2_bus', bus1='H2_comp_bus', p_nom_extendable=True, marginal_cost=0, efficiency = 1) # Verbindung H2_bus mit H2_comp_bus, zunächst vereinfacht mit statischem Wirkungsgrad = 1 für keinen Verlust von Wasserstoff

# Speicher
n.add('Store', 'el_storage', bus='el_storage_bus', e_nom=el_store_cap, capital_cost=capital_cost_el_storage_mw, marginal_cost=OM_el_storage) # Stromspeicher, Kapazität e_nom kann hier optimiert werden, Leistung muss an den Links el_storage_charge bzw. el_storage_discharge optimiert werden
n.add('Store', 'H2_storage', bus='H2_storage_bus', e_nom=H2_store_cap, marginal_cost=cost_H2_storage_mwh) # Wasserstoffspeicher, Kapazität e_nom kann hier optimiert werden, Leistung muss an den Links H2_storage_charge bzw. H2_storage_discharge optimiert werden

# Lasten
n.add('Load', 'H2_load', bus='H2_comp_bus', p_set = df_load_H2_15min_mw['P new (MW)'] ) # Definieren der H2-Last als df_load_H2_15min_mw
n.add('Load', 'el_charging_station_load', bus='electricity_bus', p_set = df_load_el_15min_mw['P new (MW)'] ) # Definieren der Ladesäulen-Last als df_load_el_15min_mw

n.optimize(solver_name='gurobi', solver_options={"LogFile": "gurobi.log"})

#%% Output Iteration 1
df_res_links_1 = n.links_t.p0
df_res_generators_1 = n.generators_t.p
df_res_loads_1 = n.loads_t.p
df_res_stores_1_E = n.stores_t.e

#%% Vorbereiten der Lastkurve als Input des Elektrolyseur Modells 
df_electrolyzer_input = pd.DataFrame({'time': n.links_t.p0.electrolyzer.index,'P_ac': n.links_t.p0.electrolyzer * (1/eta_electrolyzer)})  # Extrahiert die Zeit und den H2-Leistungsfluss aus dem pyPSA Netzwerk. Zurückrechnung (Division durch Wirkungsgrad eta_electrolyzer, um auf elekrische Leistung (Input) des Elektrolyseurs zu kommen.
df_electrolyzer_input['P_ac'] = df_electrolyzer_input['P_ac'] * 1000 # Umrechnung von MW auf kW, um Format in Elektrolyseur-Code zu entsprechen
df_electrolyzer_input['time'] = pd.to_datetime(df_electrolyzer_input['time']) # Sicherstellen, dass "time" im datetime Format ist
df_electrolyzer_input.set_index('time', inplace=True) # Setzen der Spalte "time" als Index

P_ac_electrolyzer_max = df_electrolyzer_input['P_ac'].max() # Maximale, durch die Lastkurve in "P_ac" geforderte Leistung zur Dimensionierung des Elektrolyseurs
P_ac_electrolyzer_max_round_up = m.ceil(P_ac_electrolyzer_max / 500) * 500 # Aufrunden der Elektrolyseur - Leistung auf den nächsten Wert in der 500er Serie, da die Stacks des Elektrolyseurs jeweils 500 kW haben

df_electrolyzer_input_to_csv = [] # Export der Lastkurve des Elektrolyseurs als csv Datei für die run.py Datei
df_electrolyzer_input = df_electrolyzer_input.reset_index()
df_electrolyzer_input_to_csv = df_electrolyzer_input[['time', 'P_ac']].copy() 

filename = 'Electrolyzer_input.csv'
full_path = path + filename # Vollständigen Pfad zur Speicherung der csv-Datei erstellen
df_electrolyzer_input_to_csv.to_csv(full_path, index=False) # DataFrame als csv-Datei speichern

n_snapshots_electrolyzer = length * 24 * 60 # Anpassung des Betrachtungszeitraums an User-Input (Verkürzung Rechendauer)
n_snapshots_electrolyzer = int(n_snapshots_electrolyzer) # Umwandlung von float auf integer (für .iloc)

#%% Elektrolyseur - Modell aufrufen

# Import der Eingangsleistung
ts = pd.read_csv(f'{path}Electrolyzer_input.csv', sep=',', decimal='.', parse_dates=[0], index_col=0)

start_date = pd.to_datetime(start_date)  # Konvertiere 'start_date' in ein Datum
ts = ts.loc[start_date:]  # Beschränke den DataFrame ab 'start_date'
ts = ts.iloc[:n_snapshots_electrolyzer]  # Begrenze auf die ersten n_snapshots_electrolyzer Zeilen

# Leistungsanpassung

electrolyzer = electrolyzer(P_ac_electrolyzer_max_round_up,"15", "min", "30")  # Elektrolyseur-Größe,Einheit Elektrolyseur,  dt, Einheit zeit, Druck in bar

# Auführen des Elektrolyseurs
ts = electrolyzer.calculate_data_table(ts)
ts.reset_index(inplace=True)
print(ts)

# CSV-Datei
filename = 'Electrolyzer_output.csv'
full_path = output_path + filename
ts.to_csv(full_path, index=False)


# plt.plot( ts['hydrogen production [(Kg/h)/dt]'], linestyle='-', color='b')  # Markierung und Linienstil bestimmen

# plt.title('Effizienz in Abhängigkeit von P_in')  # Titel des Diagramms
# plt.xlabel('P_in')  # Bezeichnung der X-Achse
# plt.ylabel('Effizienz [%]')  # Bezeichnung der Y-Achse
# plt.grid(True)  # Raster anzeigen für eine bessere Lesbarkeit

# plt.show()  # Anzeigen des Diagramms

#%% Elektrolyseur - Daten für pyPSA Netzwerk vorbereiten

df_electrolyzer_15min = pd.read_csv(f'{output_path}Electrolyzer_output.csv')
df_electrolyzer_15min = df_electrolyzer_15min.filter(items=['time', 'P_ac', 'hydrogen production [(Kg/h)/dt]'])
df_electrolyzer_15min['time'] = pd.to_datetime(df_electrolyzer_15min['time']) # Konvertiere die 'time'-Spalte in ein Datetime-Objekt und setze sie als Index
df_electrolyzer_15min.set_index('time', inplace=True)
df_electrolyzer_15min['hydrogen production [Kg/dt]'] = df_electrolyzer_15min['hydrogen production [(Kg/h)/dt]'] * dt_h # Kg/dt Produzierte Masse H2 pro 15 min 
df_electrolyzer_15min['hydrogen production [kWh/dt]'] = df_electrolyzer_15min['hydrogen production [Kg/dt]'] * Hu_H2_mass # [kWh/dt]
df_electrolyzer_15min['E_ac [kWh]'] = df_electrolyzer_15min['P_ac'] * dt_h # [kWh] elektrischer Energieverbrauch des Elektrolyseurs
df_electrolyzer_15min['P H2 [MW]'] = (df_electrolyzer_15min['hydrogen production [kWh/dt]'] / dt_h) / 1000 # [MW] Leistung des Wasserstoffs durch den Elektrolyseur
df_electrolyzer_15min['E_ac [kWh]'] = df_electrolyzer_15min['P_ac'] * dt_h # [kWh] Im Zeitintervall dt genutzte elektrische Energie
df_electrolyzer_15min['P_ac [MW]'] = df_electrolyzer_15min['P_ac'] / 1000 # Umrechnung von kW in MW
df_electrolyzer_15min = df_electrolyzer_15min.drop('hydrogen production [(Kg/h)/dt]', axis=1)
new_order = ['P_ac', 'P_ac [MW]', 'E_ac [kWh]', 'hydrogen production [Kg/dt]', 'hydrogen production [kWh/dt]', 'P H2 [MW]']  # Die neue Reihenfolge der Spalten
df_electrolyzer_15min = df_electrolyzer_15min[new_order]

df_electrolyzer_15min['eta'] = np.where(
    df_electrolyzer_15min['P_ac [MW]'] > 0,
    df_electrolyzer_15min['P H2 [MW]'] / df_electrolyzer_15min['P_ac [MW]'], 0)

#%%
sum_H2_electrolyzer_modell = df_electrolyzer_15min['P H2 [MW]'].sum()
sum_el_electrolyzer_modell = df_electrolyzer_15min['P_ac [MW]'].sum()
eta_electrolyzer_modell = sum_H2_electrolyzer_modell/sum_el_electrolyzer_modell # Wenn für Variable max_ramp zu großer Wert gewählt wird (zweistelliger MW Bereich), sinkt eta_electrolyzer_modell auf ca. 0.57 aufgrund der Aufwärmzeit --> daher setzen von max_ramp auf 1 MW

print('Elektrische Leistung Elektrolyseur = ',df_electrolyzer_15min['P_ac [MW]'].max())
print('Summe P H2 Elektrolyseurmodell = ', sum_H2_electrolyzer_modell)
print('eta = ', eta_electrolyzer_modell)

#%% Kompressormodellierung 
# Wesentliche Gleichungen:
# (Gl.1) 𝑤t,isentrop= ℎ_out(𝑇_out, p_out) − ℎ_in(𝑇_in, p_in) dabei ist h_out die Enthalpie nach der Verdichtung, aber vor der Kühlung; und h_in die Temperatur vor der Verdichtung, aber nach der Kühlung aus der vorigen Stufe. Quelle: Rösler - Modellierung und Implementierung industrieller Prozesse in ein Multiagentensystem
# (Gl.2) 𝑇_out = 𝑇_in(p_in/p_out)^((1−𝜅)/𝜅) Quelle: Rösler - Modellierung und Implementierung industrieller Prozesse in ein Multiagentensystem

def calc_next_T(T_prev, p_prev, p_next, k): # Berechnet die nächste Temperatur (notwendig für Berechnung von wt) anhand der vorigen Temperatur, des vorigen Drucks, des nächsten Drucks und des Isentropenexponenten
    return T_prev*((p_next/p_prev)**((k-1)/k))

results = pd.DataFrame() # DataFrame für Ergebnisse 
df_res_compressor = pd.DataFrame(columns=['wt_stages', 'PH2', 'ms', 'Pmech', 'eta_el', 'Pel', 'Q_ab', 'P_cooling', 'Pel_ges', 'energy_loss_compressor']) # Initialisierung df für Speicherung der Ergebnisse

for PH2 in df_electrolyzer_15min['P H2 [MW]']: # Schleife über alle Werte in 'df_electrolyzer_15min'
    p_current = p_in # Initialisierung der Parameter für Berechnung der Kompressorstufen
    T_current = T_in
    stages = 0
    p_values = [p_in]
    T_values = [T_in]
    
    # Hauptschleife zur Berechnung der Kompressorstufen. Kriterium zum Erstellen einer neuen Stufe ist das Erreichen einer maximal zulässigen Gastemperatur T_max bei der Verdichtung
    while p_current < p_out: # Erhöhe den Druck in kleineren Schritten dp, um die maximale Temperatur t_max genau zu treffen, solange der Druck den Endruck p_out noch nicht erreicht hat
        dp = 1e5  # [Pa] Druck-Inkrement
        p_next = min(p_current + dp, p_out) # Begrenzt p_next auf p_out
        T_next = calc_next_T(T_current, p_current, p_next, k) # Berechnet die nächste Temperatur nach der oben definierten Formel
    
        if T_next > T_max: # Bei Überschreitung der Maximaltemperatur T_max: Druckanpassung von p_next, um T_max nicht zu überschreiten
            T_next = T_max # T_next wird auf T_max zurückgesetzt 
            p_next = p_current * (T_max / T_current) ** (k / (k - 1)) # p_next wird mit der umgestelleten Temperaturgleichung (Gl.2) berechnet (vereinfachte Annahme)
            stages += 1  # Erstellung einer neuen Stufe, da T_max erreicht wurde
            p_values.append(p_next) # Speicherung des Drucks für Stufenanfang bzw. -ende in der Liste p_values
            T_values.append(T_next) # Speicherung der Temperatur für Stufenanfang bzw. -ende in der Liste T_values
            p_current = p_next # Druckinkrementierung wird fortgesetzt
            T_current = T_cooling # Rücksetzung der Temperatur auf Gastemperatur nach Kühlung
        else:
            p_current = p_next # Falls T_max nicht überschritten wird, wird Druckinkrementierung fortgesetzt
            T_current = T_next # Falls T_max nicht überschritten wird, wird die Berechnung von T_next fortgesetzt
            if p_current == p_out:  # Endbedingung, falls genauer Enddruck erreicht wird
                p_values.append(p_current) # Speicherung des Enddruck in der Liste p_values
                T_values.append(T_current) # Speicherung der Endtemperatur in der Liste T_values
    
    if p_values[-1] != p_out:     # Füge letzte Stufe hinzu, falls nicht schon geschehen
        stages += 1
        p_values.append(p_out)
        T_next = calc_next_T(T_current, p_current, p_out, k)
        T_values.append(T_next)
    
    df_compressor = pd.DataFrame({'Stufe': range(0, len(p_values)),'Druck [Pa]': p_values,'Temperatur [K]': T_values}) # Speicherung der Ergebnisse in einem neuen DataFrame
    
    for i in df_compressor.index: # Auslesen der massenspezifischen Enthalpien des Wasserstoffs am Ende der Druckerhöhung jeder Stufe vor der Kühlung aus der Stoffdatenbank CoolProp
        T = df_compressor.loc[i, 'Temperatur [K]'] # Temperatur in K
        P = df_compressor.loc[i, 'Druck [Pa]'] # Druck in Pa
        H = CP.PropsSI('H', 'P', P, 'T', T, 'Hydrogen') # Auslesen der Werte für Enthalpie bei gegebenem Druck und Temperatur aus der Datenbank
        df_compressor.loc[i, 'm. Enthalpie_pre_cooling [J/kg]'] = H # Hinzufügen des berechneten Werts zur neuen Spalte im DataFrame
    
    df_compressor['m. Enthalpie_post_cooling [J/kg]'] = 0.0 # Einfügen einer neuen Spalte "m. Enthalpie_post_cooling [J/kg]"; wird benötigt um Gl.1 anzuwenden
    df_compressor.loc[0, 'm. Enthalpie_post_cooling [J/kg]'] = df_compressor.loc[0, 'm. Enthalpie_pre_cooling [J/kg]'] # Übernehmen des Wertes aus "Enthalpie_pre_cooling [J/kg]" für die erste Zeile, da hier nicht gekühlt wird (Annahme)
    
    for i in df_compressor.index[1:]: # Berechnung der m. Enthalpie nach dem Kühlen für jede weitere Stufe; startet bei Index 1 bzw. überspringt den ersten Eintrag
        P = df_compressor.loc[i, 'Druck [Pa]']  # Druck in Pa aus der Spalte "Druck [Pa]" in df_compressor
        T = T_cooling  # Konstante Temperatur nach dem Kühlen
        H_post_cooling = CP.PropsSI('H', 'P', P, 'T', T, 'Hydrogen') # Auslesen der Werte für Enthalpie bei gegebenem Druck und Temperatur aus der Datenbank
        df_compressor.loc[i, 'm. Enthalpie_post_cooling [J/kg]'] = H_post_cooling # Hinzufügen der berechneten Werte zur neuen Spalte im DataFrame
    
    df_compressor['wt [J/kg]'] = 0.0 # Erstellen einer neuen Spalte für technische Arbeit der Verdichtung
    df_compressor.loc[0, 'wt [J/kg]'] = 0 # Setzen des ersten Wertes der Spalte "wt [J/kg]" auf 0
    
    for i in range(1, len(df_compressor)): # Berechnung von "wt [J/kg]" für alle weiteren Zeilen mit Gl.1
        h_pre_cooling_current = df_compressor.loc[i, 'm. Enthalpie_pre_cooling [J/kg]'] # Enthalpie vor Kühlung aus der aktuellen Zeile
        h_post_cooling_previous = df_compressor.loc[i-1, 'm. Enthalpie_post_cooling [J/kg]'] # Enthalpie nach Kühlung aus der Zeile darüber
        df_compressor.loc[i, 'wt [J/kg]'] = h_pre_cooling_current - h_post_cooling_previous # Berechnung von "wt [J/kg]" als Differenz der beiden Enthalpien

    wt_stages = df_compressor['wt [J/kg]'].sum() # Summe der technischen Arbeit aller Verdichterstufen 
    ms = PH2 / (Hu_H2_mass*10**(-3)) / 3600 # [kg/s]
    Pmech = ms*(wt_stages/(eta_isentrop*eta_mech)) # [W] Mechanische Leistung Verdichter. Quelle Formel: Rösler
   
    if Pmech > 0: # if Schleife um Werte mit Pmech = 0 auszuschließen, da log (0) nicht zulässig
        eta_el = (8e-05 * m.log10(Pmech) ** 4) - (0.0015 * m.log10(Pmech) ** 3) + (0.0061 * m.log10(Pmech) ** 2) + (0.0311 * m.log10(Pmech)) + 0.7617 # eta_el in Abhängigkeit des Logarithmus der mechanischen Leistung. Quelle: Reuß-Dissertation und Rösler
    else:
        eta_el = 0  # im Falle von Pmech=0
    
    if eta_el > 0:  # Überprüfe, ob eta_el > oder = 0 ist, um Nan Werte für Pel auszuschließen
        Pel = Pmech/eta_el
    else:
        Pel = 0  # Pel auf 0 setzen, wenn eta_el == 0
    Q_ab = 0.0  # Q_ab --> Summe der Enthalpiedifferenzen des Gases vor und nach der Kühlung
    for i in range(1, len(df_compressor) - 1):  # Iteriere über alle Zeilen außer der ersten und der letzten
        h_pre_cooling = df_compressor.loc[i, 'm. Enthalpie_pre_cooling [J/kg]']  # Wert der aktuellen Zeile, Spalte m. Enthalpie_pre_cooling
        h_post_cooling = df_compressor.loc[i, 'm. Enthalpie_post_cooling [J/kg]']  # Wert der aktuellen Zeile, Spalte m. Enthalpie_post_cooling
        Q_ab += h_pre_cooling - h_post_cooling  # Addiere die Differenz zur Summe
    
    P_cooling = Q_ab/COP_cooling * ms # [W] Abwärmeleistung in Abhängigkeit des COP der Kühlung (vereinfachte Annahme)
    Pel_ges = Pel/1e6+P_cooling/1e6 # [MW] Gesamte Eletkrische Leistung Verdichter enspricht der Summe aus Leistung für Verdichtung und Leistung für Kühlung. Literatur (Stenzel-Skript) sagt 12% für Verdichtung von 1 bar auf 350 bar
    
    if PH2 > 0: # Überprüfung, ob PH2 > oder = 0 ist, um Nan Werte für energy_loss_compressor auszuschließen
        energy_loss_compressor = (Pel_ges/PH2)*100 # [%] Verhältnis Verdichterleistung/H2-Leistung
    else:
        energy_loss_compressor = 0
    
    df_res_compressor.loc[len(df_res_compressor)] = {'wt_stages': wt_stages, 'PH2': PH2, 'ms':ms, 'Pmech': Pmech, 'eta_el': eta_el, 'Pel': Pel, 'Q_ab': Q_ab, 'P_cooling': P_cooling, 'Pel_ges': Pel_ges, 'energy_loss_compressor': energy_loss_compressor} # Speichern der Ergebnisse der Kompressorberechnung für einen snapshot in df_res_compressor

    p_current = p_in # Zurücksetzen der Parameter für den nächsten Durchlauf (Druck, Temperatur usw muss wieder die Eingangsgrößen haben für nächsten Durchlauf der Schleife)
    T_current = T_in
    stages = 0
    p_values = [p_in]
    T_values = [T_in]

# Berechnung der Summen und Durchschnittswerte über einjährigen Betrieb
wt_stages_a=df_res_compressor['wt_stages'].sum # [J/kg] Summe der technischen Arbeit des Kompressors über ein Jahr
ms_mean=df_res_compressor['ms'].mean() # [kg/s] Mittelwert des Massenstroms des produzierten Wasserstoffs über ein Jahr
Pmech_mean=df_res_compressor['Pmech'].mean() # [W] Mittelwert der mechanischen Leistung des Kompressors über ein Jahr
eta_el_mean=df_res_compressor['eta_el'].mean() # [] Mittelwert des elektrischen Wirkungsgrades des Kompressors über ein Jahr
P_el_mean=df_res_compressor['Pel'].mean() # [W] Mittelwert der elektrischen Leistung des Kompressors (ohne Kühlung) über ein Jahr
Q_ab_mean=df_res_compressor['Q_ab'].mean() # [W] Mittelwert der Abwärmeleistung des Kompressors über ein Jahr
P_cooling_mean=df_res_compressor['P_cooling'].mean() # [W] Mittelwert der elektrischen Leistung zum Kühlen des Kompressors über ein Jahr
Pel_ges_mean=df_res_compressor['Pel_ges'].mean() # [MW] Mittelwert der gesamten elektrischen Leistung des Kompressors (Kompression und Kühlung) über ein Jahr
energy_loss_compressor_mean = df_res_compressor.loc[df_res_compressor['energy_loss_compressor'] > 0,'energy_loss_compressor'].mean() # [%] Mittelwert der Verhältnisses aller Verdichterleistungen/alle H2-Leistungen über ein Jahr

end_date = pd.to_datetime(start_date) + pd.Timedelta(minutes=15 * (n_snapshots - 1))
index = pd.date_range(start=start_date, end=end_date, freq='15min')
df_res_compressor['time'] = index
df_res_compressor['time'] = pd.to_datetime(df_res_compressor['time']) # Konvertieren der Series time in ein datetime object
df_res_compressor = df_res_compressor.set_index(df_res_compressor['time']) # Setzen der Spalte time als index
df_res_compressor = df_res_compressor.drop(columns=['time']) # Löschen der obsoleten weil doppelten Spalte time
sum_PH2_iteration_1 = df_res_loads_1['H2_load'].sum()
sum_PH2_compressor_model = df_res_compressor['PH2'].sum()
scal_factor_comp = sum_PH2_iteration_1/sum_PH2_compressor_model # Skalierungsfaktor zur Berücksichtigung der tatsächlichen H2-Nachfrage sum_PH2_iteration_1 ggü. der geringeren im Kompressormodell berechneten H2 Menge sum_PH2_compressor_model
df_res_compressor['Pel_ges'] = df_res_compressor['Pel_ges']*scal_factor_comp # Skalierte elektrische Last des Kompressors --> die vorherige Last bezog sich auf die geringere H2-Erzeugungsmenge aus dem Elektrolyseur-Modell
df_electrolyzer_15min['P_ac [MW]'] = df_electrolyzer_15min['P_ac [MW]'] * (1-eta_electrolyzer) # Zurückrechnung der erzeugten elektrischen Lastkurve des Elektrolyseurs mit eta_electrolyzer. So ist P_ac [MW] gleich 0,3 * P H2 [MW] und als elektrischer Verlust zu betrachten, der am electricity_bus anfällt

#%% Iteration 2 --> Notwendig, um mit den Pel_ges-Werten aus df_res_compressor aus Iteration 1 den Stromverbrauch compressor_el_load dem Neztwerk zu implementieren
n = pypsa.Network() # Erstellen des PyPSA-Netzwerks

# start date bei Input definiert
end_date = pd.to_datetime(start_date) + pd.Timedelta(minutes=15 * (n_snapshots - 1))
index = pd.date_range(start=start_date, end=end_date, freq='15min')
n.set_snapshots(index) # Setzen der Anzahl an Snapshots gleich der Anzahl an Elementen in der Zeitreihe
n.snapshot_weightings = pd.Series(0.25, index=n.snapshots)  # Gewichtung für 15 Minuten

# Busse
n.add('Bus', 'pv_bus') # verbindet pv-Generator, pv-infeed und pv_to_el
n.add('Bus', 'electricity_bus') # verbindet pv_to_el, grid (Stromnetz) und electrolyzer
n.add('Bus', 'H2_bus') # verbindet electrolyzer, H2_load und H2_storage_bus
n.add('Bus', 'H2_storage_bus') # verbindet H2_bus und H2_storage
n.add('Bus', 'el_storage_bus') # verbindet electricity_bus und el_storage
n.add('Bus', 'H2_comp_bus') # verbindet compressor_h2_flow, H2_load sowie H2_storage_charge und H2_storage_discharge
n.add('Bus', 'wind_bus') # verbindet wind-Generator, wind-infeed und wind_to_el

#Generatoren
n.add('Generator', 'pv', bus='pv_bus', p_nom=PV_P_NOM, p_max_pu=PV_P_PU) # PV-Anlage, p_nom=PV_P_NOM legt die Anlagenleistung [MWp] fest, mit p_max_pu=PV_P_PU werden die auf 1 MWp skalierten Werte per Unit Leistungswerte der PV-Anlage definiert
n.add('Generator', 'pv_infeed', bus='pv_bus', p_nom=PV_P_NOM, p_max_pu=PV_P_PU, marginal_cost=INFEED_RATE_PV, sign=-1) # Einspeisung von Überschussstrom der PV-Anlage (p_nom_extendable=True für keine Obergrenze der Einspeisung, marginal_cost entspricht der Einspeisevergütung, sign=-1 für Leistungsentnahme aus dem Bus)
n.add('Generator', 'wind', bus='wind_bus', p_nom=WIND_P_NOM, p_max_pu=WIND_P_PU) # Windkraftanlage, p_nom=WIND_P_NOM legt die Anlagenleistung [MW] fest, mit p_max_pu=WIND_P_PU werden die auf 1 MW skalierten Werte per Unit Leistungswerte der WKA definiert
n.add('Generator', 'wind_infeed', bus='wind_bus', p_nom=WIND_P_NOM, p_max_pu=WIND_P_PU, marginal_cost=INFEED_RATE_PV, sign=-1) # Einspeisung von Überschussstrom der PV-Anlage (p_nom_extendable=True für keine Obergrenze der Einspeisung, marginal_cost entspricht der Einspeisevergütung, sign=-1 für Leistungsentnahme aus dem Bus)
n.add('Generator', 'grid', bus='electricity_bus', p_nom_extendable=True, marginal_cost=ELECTRICITY_RATE) # Stromnetzanschluss, p_nom_extendable=True für keine Obergrenze bei Netzbezug, marginal_cost=ELECTRICITY_RATE für Berücksichtigung der Kosten des Netzstroms

# Links
n.add('Link', 'pv_to_el', bus0='pv_bus', bus1='electricity_bus', p_nom_extendable=True, marginal_cost=0) # Verbindung pv_bus mit electricity_bus
n.add('Link', 'wind_to_el', bus0='wind_bus', bus1='electricity_bus', p_nom_extendable=True, marginal_cost=0) # Verbindung wind_bus mit electricity_bus
n.add('Link', 'electrolyzer', bus0='electricity_bus', bus1='H2_bus', p_nom_extendable=True, marginal_cost=0, efficiency = 1) # Aus diesem Link heraus wird eine csv exportiert, die als Input für den Elektrolyseur-Code von Sciebo_Original_Saur dient, efficiency = eta_electrolyzer, um eine grobe, vereinfachte Version des Netzes zu berechnen und compressor_el_load sowie richtige Menge an H2-Energie für weitere Berechnungen zu haben
n.add('Link', 'H2_storage_charge', bus0='H2_comp_bus', bus1='H2_storage_bus', p_nom=P_H2_store, marginal_cost=0) # Verbindung H2_bus mit H2_storage_bus zum Laden von H2_storage
n.add('Link', 'H2_storage_discharge', bus0='H2_storage_bus', bus1='H2_comp_bus', p_nom=P_H2_store, marginal_cost=0) # Verbindung H2_storage_bus mit H2_bus zum Entladen von H2_storage
n.add('Link', 'el_storage_charge', bus0='electricity_bus', bus1='el_storage_bus', p_nom=P_el_store, marginal_cost=0) # Verbindung electricity_bus mit el_storage_bus zum Laden von el_storage
n.add('Link', 'el_storage_discharge', bus0='el_storage_bus', bus1='electricity_bus', p_nom=P_el_store, marginal_cost=0) # Verbindung el_storage_bus mit electricity_bus zum Entladen von el_storage
n.add('Link', 'compressor_h2_flow', bus0='H2_bus', bus1='H2_comp_bus', p_nom_extendable=True, marginal_cost=0, efficiency = 1) # Verbindung H2_bus mit H2_comp_bus, zunächst vereinfacht mit statischem Wirkungsgrad = 1 für keinen Verlust von Wasserstoff

# Speicher
n.add('Store', 'el_storage', bus='el_storage_bus', e_nom=el_store_cap, capital_cost=capital_cost_el_storage_mw, marginal_cost=OM_el_storage) # Stromspeicher, Kapazität e_nom kann hier optimiert werden, Leistung muss an den Links el_storage_charge bzw. el_storage_discharge optimiert werden
n.add('Store', 'H2_storage', bus='H2_storage_bus', e_nom=H2_store_cap, marginal_cost=cost_H2_storage_mwh) # Wasserstoffspeicher, Kapazität e_nom kann hier optimiert werden, Leistung muss an den Links H2_storage_charge bzw. H2_storage_discharge optimiert werden

# Lasten
n.add('Load', 'H2_load', bus='H2_comp_bus', p_set = df_load_H2_15min_mw['P new (MW)']) # Definieren der H2-Last als df_load_H2_15min_mw
n.add('Load', 'el_charging_station_load', bus='electricity_bus', p_set = df_load_el_15min_mw['P new (MW)']) # Definieren der Ladesäulen-Last als df_load_el_15min_mw
n.add('Load', 'compressor_el_load', bus='electricity_bus', p_set = df_res_compressor['Pel_ges']) # Definieren des Kompressor-Lastgangs als Spalte Pel_ges aus der Kompressormedellierung aus Iteration 1
n.add('Load', 'electrolyzer_el_load', bus='electricity_bus', p_set = df_electrolyzer_15min['P_ac [MW]']) # Definieren des Elektolyseur-Lastgangs als Spalte Pel_ac [MW] aus der dem Elektrolyseur Modell

# Durchführen der Netzwerkoptimierung
n.optimize(solver_name='gurobi', solver_options={"LogFile": "gurobi.log"})

#%% Output Iteration 2
df_res_links_2 = n.links_t.p0
df_res_generators_2 = n.generators_t.p
df_res_loads_2 = n.loads_t.p

#%% Sankey Diagramm vorbereiten für Plot mit sankeymatic.com

df_sankey_2 = pd.concat([df_res_generators_2, df_res_links_2, df_res_loads_2, df_electrolyzer_15min['P_ac [MW]'], df_electrolyzer_15min['P H2 [MW]']], axis=1) # Zusammenfügen aller relevanten dataframes

# Überprüfung von Größen und Zusammenhängen
sum_electrolyzer_iteration_2 = df_res_links_2['electrolyzer'].sum()
sum_electrolyzer_el_load_iteration_2 = df_electrolyzer_15min['P_ac [MW]'].sum()
sum_electrolyzer_h2_load_iteration_2 = df_electrolyzer_15min['P H2 [MW]'].sum()
sum_load_h2_2 = df_res_loads_2['H2_load'].sum() 
sum_load_el_electrolyzer_2 = df_res_loads_2['electrolyzer_el_load'].sum()
sum_load_el_electrolyzer_2 = df_electrolyzer_15min['P_ac [MW]'].sum()
eta_electrolyzer_real = sum_load_h2_2 / sum_load_el_electrolyzer_2
sum_compressor_el_load_model = df_res_compressor['Pel_ges'].sum()
sum_compressor_el_load_iteration_2 = df_res_loads_2['compressor_el_load'].sum()
sum_compressor_h2_load_iteration_2 = df_res_compressor['PH2'].sum()

for column in df_sankey_2.columns: # Schleife über alle Spaltennamen in df_sankey_2
    df_sankey_2['E ' + column + ' [MWh]'] = df_sankey_2[column] * 0.25 # Neue Spalte erstellen mit dem Namen 'E ' + alter Spaltenname
df_sankey_2 = df_sankey_2[[col for col in df_sankey_2.columns if col.startswith('E')]]
df_res_stores_2_E = n.stores_t.e
df_sankey_2 = pd.concat([df_sankey_2, df_res_stores_2_E], axis=1)
df_sankey_2_sum = pd.DataFrame({
    'name': df_sankey_2.columns,  # Spaltennamen von df_sankey_2
    'E sum': df_sankey_2.sum()})   # Summen der jeweiligen Spalten

E_electrolyzer_losses_2 = df_sankey_2_sum.loc["E electrolyzer_el_load [MWh]", "E sum"]
E_compressor_losses_2 = df_sankey_2_sum.loc["E compressor_el_load [MWh]", "E sum"]
E_compressor_el_load = df_sankey_2_sum.loc["E compressor_el_load [MWh]", "E sum"]
E_H2 = df_sankey_2_sum.loc["E electrolyzer [MWh]", "E sum"]

# Löschen der nicht benötigten Spalten
df_sankey_2_sum = df_sankey_2_sum[df_sankey_2_sum['name'] != 'E pv [MWh]']
df_sankey_2_sum = df_sankey_2_sum[df_sankey_2_sum['name'] != 'E wind [MWh]']
df_sankey_2_sum = df_sankey_2_sum[df_sankey_2_sum['name'] != 'E H2_storage_charge [MWh]']
df_sankey_2_sum = df_sankey_2_sum[df_sankey_2_sum['name'] != 'E H2_storage_discharge [MWh]']
df_sankey_2_sum = df_sankey_2_sum[df_sankey_2_sum['name'] != 'E el_storage_charge [MWh]']
df_sankey_2_sum = df_sankey_2_sum[df_sankey_2_sum['name'] != 'E el_storage_discharge [MWh]']
df_sankey_2_sum = df_sankey_2_sum[df_sankey_2_sum['name'] != 'el_storage']
df_sankey_2_sum = df_sankey_2_sum[df_sankey_2_sum['name'] != 'H2_storage']
df_sankey_2_sum = df_sankey_2_sum[df_sankey_2_sum['name'] != 'E P_ac [MW] [MWh]']
df_sankey_2_sum = df_sankey_2_sum[df_sankey_2_sum['name'] != 'E P H2 [MW] [MWh]']

# Initialisieren der Spalten für Sankey Diagramm
df_sankey_2_sum.rename(columns={'E sum': 'Value'}, inplace=True)
df_sankey_2_sum['Source'] = np.nan
df_sankey_2_sum['Target'] = np.nan

# Füllen der neuen Spalten für Sankey Diagramm
df_sankey_2_sum.loc[df_sankey_2_sum['name'] == 'E pv_infeed [MWh]', ['Source', 'Target']] = ['PV', 'Netzeinspeisung']
df_sankey_2_sum.loc[df_sankey_2_sum['name'] == 'E wind_infeed [MWh]', ['Source', 'Target']] = ['Wind', 'Netzeinspeisung']
df_sankey_2_sum.loc[df_sankey_2_sum['name'] == 'E grid [MWh]', ['Source', 'Target']] = ['Netz', 'Tankstelle']
df_sankey_2_sum.loc[df_sankey_2_sum['name'] == 'E pv_to_el [MWh]', ['Source', 'Target']] = ['PV', 'Tankstelle']
df_sankey_2_sum.loc[df_sankey_2_sum['name'] == 'E wind_to_el [MWh]', ['Source', 'Target']] = ['Wind', 'Tankstelle']
df_sankey_2_sum.loc[df_sankey_2_sum['name'] == 'E electrolyzer [MWh]', ['Source', 'Target']] = ['Elektrolyseur', 'H2 Bus']
df_sankey_2_sum.loc[df_sankey_2_sum['name'] == 'E electrolyzer [MWh]', 'Value'] += E_compressor_losses_2
df_sankey_2_sum.loc[df_sankey_2_sum['name'] == 'E electrolyzer_el_load [MWh]', ['Source', 'Target']] = ['Tankstelle', 'Elektrolyseur']
df_sankey_2_sum.loc[df_sankey_2_sum['name'] == 'E electrolyzer_el_load [MWh]', 'Value'] += E_compressor_losses_2 + E_H2
df_sankey_2_sum.loc[df_sankey_2_sum['name'] == 'E compressor_h2_flow [MWh]', ['Source', 'Target']] = ['H2 Bus', 'H2 HD Bus']
df_sankey_2_sum.loc[df_sankey_2_sum['name'] == 'E compressor_el_load [MWh]', ['Source', 'Target']] = ['H2 Bus', 'Kompressor Verbrauch (el)']
df_sankey_2_sum.loc[df_sankey_2_sum['name'] == 'E H2_load [MWh]', ['Source', 'Target']] = ['H2 HD Bus', 'H2 Zapfsäule']
df_sankey_2_sum.loc[df_sankey_2_sum['name'] == 'E el_charging_station_load [MWh]', ['Source', 'Target']] = ['Tankstelle', 'E-Ladesäule']
df_sankey_2_sum.loc[df_sankey_2_sum['name'] == 'E el_charging_station_load [MWh]', ['Source', 'Target']] = ['Tankstelle', 'E-Ladesäule']

new_row = {'name': 'E Elektrolyseur Verluste [MWh]','Value': E_electrolyzer_losses_2,'Source': 'Elektrolyseur','Target': 'Elektrolyseur Verluste'}
new_row_df = pd.DataFrame([new_row])
df_sankey_2_sum = pd.concat([df_sankey_2_sum, new_row_df], ignore_index=True)

# Vorbereiten und Export als txt Datei
df_sankey_2_sum.drop(columns=['name'], inplace=True)
df_sankey_2_sum.set_index('Source', inplace=True)
df_sankey_2_sum = df_sankey_2_sum[['Value','Target']]
df_sankey_2_sum.sort_index(inplace=True)
df_sankey_2_sum['Value'] = df_sankey_2_sum['Value'].round(2)
filename = 'sankey_2_output.txt'
full_path = output_path + filename

with open(full_path, 'w') as file: # Iteriert über jede Zeile im DataFrame
    for index, row in df_sankey_2_sum.iterrows(): # Umwandeln des Index und der Werte der Zeile in Zeichenketten, dabei wird die Spalte 'Value' in eckige Klammern gesetzt
        row_list = list(row.values)
        row_list[0] = f'[{row_list[0]}]' # Setzen des Wertes der Spalte 'Value' in eckige Klammern
        line = ' '.join(map(str, [index] + row_list)) # Verknüpfe den Index und die Zeilenwerte
        file.write(line + '\n')  # Schreibt die Zeile in die Textdatei und füge einen Zeilenumbruch hinzu
        
#%% Analyse der Energieflüsse
df_energy_sources = pd.concat([df_res_links_2['pv_to_el'], df_res_links_2['wind_to_el'], df_res_generators_2['grid'], df_res_loads_2['H2_load'], df_res_loads_2['el_charging_station_load']], axis=1) 
df_energy_sources['green H2'] = 0 # Initialisiere die neuen Spalten mit 0
df_energy_sources['yellow H2'] = 0
df_energy_sources['green electricity'] = 0
df_energy_sources['yellow electricity'] = 0

for i, row in df_energy_sources.iterrows():
    pv_wind_sum = row['pv_to_el'] + row['wind_to_el']
    total_energy = pv_wind_sum + row['grid']
    
    if row['H2_load'] == 0 and row['el_charging_station_load'] == 0:
        pass  # keine Aktion erforderlich, da alle Werte bereits 0 sind
        
    elif row['H2_load'] > 0 and row['el_charging_station_load'] == 0: # Berechnungen für 'green H2' und 'yellow H2'
        df_energy_sources.at[i, 'green H2'] = (pv_wind_sum / total_energy) * row['H2_load']
        df_energy_sources.at[i, 'yellow H2'] = (row['grid'] / total_energy) * row['H2_load']
        
    elif row['H2_load'] == 0 and row['el_charging_station_load'] > 0:  # Berechnungen für 'green electricity' und 'yellow electricity'
        df_energy_sources.at[i, 'green electricity'] = (pv_wind_sum / total_energy) * row['el_charging_station_load']
        df_energy_sources.at[i, 'yellow electricity'] = (row['grid'] / total_energy) * row['el_charging_station_load']
        
    elif row['H2_load'] > 0 and row['el_charging_station_load'] > 0: # Berechnungen für alle vier neuen Spalten
        df_energy_sources.at[i, 'green H2'] = (pv_wind_sum / total_energy) * row['H2_load']
        df_energy_sources.at[i, 'yellow H2'] = (row['grid'] / total_energy) * row['H2_load']
        df_energy_sources.at[i, 'green electricity'] = (pv_wind_sum / total_energy) * row['el_charging_station_load']
        df_energy_sources.at[i, 'yellow electricity'] = (row['grid'] / total_energy) * row['el_charging_station_load']

# Test, ob Summen gleich geblieben sind:
sum_H2_load_energy_sources = df_energy_sources['H2_load'].sum()*dt_h
sum_el_charging_station_load_energy_sources = df_energy_sources['el_charging_station_load'].sum()*dt_h
sum_green_H2_energy_sources = df_energy_sources['green H2'].sum()*dt_h
sum_yellow_H2_energy_sources = df_energy_sources['yellow H2'].sum()*dt_h
sum_green_electricity_energy_sources = df_energy_sources['green electricity'].sum()*dt_h
sum_yellow_electricity_energy_sources = df_energy_sources['yellow electricity'].sum()*dt_h
sum_H2_green_yellow = sum_green_H2_energy_sources + sum_yellow_H2_energy_sources
sum_electricity_green_yellow = sum_green_electricity_energy_sources + sum_yellow_electricity_energy_sources

#%% Analyse des Batteriespeichers für Kapitel 9.1.3

charging_power_H2 = n.links_t.p0['H2_storage_charge']
discharging_power_H2 = -n.links_t.p1['H2_storage_discharge']
energy_H2_store = n.stores_t.e['H2_storage']

pv_generation = n.generators_t.p["pv"]
pv_to_el_flow = n.links_t.p0["pv_to_el"]
pv_infeed_flow = n.generators_t.p["pv_infeed"]

wind_generation = n.generators_t.p["wind"]
wind_to_el_flow = n.links_t.p0["wind_to_el"]
wind_infeed_flow = n.generators_t.p["wind_infeed"]

charging_power_BESS = n.links_t.p0["el_storage_charge"]  # [MW] Positive Werte
discharging_power_BESS = -n.links_t.p1["el_storage_discharge"]  # [MW] Negative Werte

total_charge_energy_BESS = charging_power_BESS.sum()*dt_h # [MWh]
total_discharge_energy_BESS = discharging_power_BESS.sum()*dt_h # [MWh]

total_energy_flow_BESS = total_charge_energy_BESS + total_discharge_energy_BESS # [MWh]
total_cycles_BESS = total_energy_flow_BESS / (el_store_cap*2) # [MWh]

total_load = n.loads_t.p["el_charging_station_load"] + n.loads_t.p["compressor_el_load"] + n.loads_t.p["electrolyzer_el_load"] # MW
avg_total_load = total_load.sum()/(4*24*365) # MW
supply_time_BESS = el_store_cap / avg_total_load # h

#%% Analyse des Wasserstoffspeichers für 9.1.5

charging_power_H2 = n.links_t.p0["H2_storage_charge"]  # [MW] Positive Werte
discharging_power_H2 = -n.links_t.p1["H2_storage_discharge"]  # [MW] Negative Werte

total_charge_energy_H2 = charging_power_H2.sum()*dt_h # [MWh]
total_discharge_energy_H2 = discharging_power_H2.sum()*dt_h # [MWh]

total_energy_flow_H2 = total_charge_energy_H2 + total_discharge_energy_H2 # [MWh]
total_cycles_H2 = total_energy_flow_H2 / (H2_store_cap*2) # n

h2_load = n.loads_t.p["H2_load"] # MW
avg_h2_load = h2_load.sum()/(4*24*365) # MW
supply_time_H2store = H2_store_cap / avg_h2_load # h

# #%% Plots
# # Doppeltes Diagramm Leistung von PV- und Windkraft & Kapazitätsfaktor PV und Wind
# # Diagramm 1: Leistung von PV- und Windkraft
#
# df_pv_15min_mw = df_pv_15min_mw.reset_index()  # Index zurücksetzen, um auf Spalte "time" zurückgreifen zu können
# df_wind_15min_mw = df_wind_15min_mw.reset_index()  # Index zurücksetzen, um auf Spalte "time" zurückgreifen zu können
#
# avg_pv = df_pv_15min_mw['electricity'].mean()
# avg_wind = df_wind_15min_mw['electricity'].mean()
#
# fig1 = go.Figure()
#
# fig1.add_trace(
#     go.Scatter(
#         x=df_wind_15min_mw['index'],
#         y=df_wind_15min_mw['electricity'],
#         mode='lines',
#         fill='tozeroy',
#         line=dict(color="#d7471f"),
#         name='Wind'))
#
# fig1.add_trace(
#     go.Scatter(
#         x=df_pv_15min_mw['index'],
#         y=df_pv_15min_mw['electricity'],
#         mode='lines',
#         fill='tozeroy',
#         line=dict(color="#901b6e"),
#         name='Photovoltaik'))
#
# fig1.add_trace(
#     go.Scatter(
#         x=[df_pv_15min_mw['index'].min(), df_pv_15min_mw['index'].max()],
#         y=[avg_pv, avg_pv],
#         mode="lines",
#         line=dict(color="black", width=3, dash="dot"),
#         name="Durchschnittliche PV-Leistung"))
#
# fig1.add_trace(
#     go.Scatter(
#         x=[df_wind_15min_mw['index'].min(), df_wind_15min_mw['index'].max()],
#         y=[avg_wind, avg_wind],
#         mode="lines",
#         line=dict(color="black", width=3, dash="dash"),
#         name="Durchschnittliche WKA-Leistung"))
#
# # Diagramm 2: Kapazitätsfaktor PV und Wind
# months = ['Jan', 'Feb', 'Mrz', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez']
# pv_capacity_factor = [4.4, 11.89, 13.14, 20.04, 20.57, 23.37, 22.5, 20.09, 17.56, 10.68, 5.87, 4.09]
# wind_capacity_factor = [40.46, 40.28, 48.02, 27.73, 21.97, 24.66, 17.56, 23.71, 29.63, 39.69, 37.82, 47.46]
#
# df2 = pd.DataFrame({
#     'Monat': months * 2,
#     'Kapazitätsfaktor (%)': pv_capacity_factor + wind_capacity_factor,
#     'Energiequelle': ['Photovoltaik'] * 12 + ['Wind'] * 12})
#
# fig2 = go.Figure()
#
# fig2.add_trace(
#     go.Scatter(
#         x=months,
#         y=wind_capacity_factor,
#         mode='lines',
#         line=dict(color="#d7471f"),
#         name='Wind'))
#
# fig2.add_trace(
#     go.Scatter(
#         x=months,
#         y=pv_capacity_factor,
#         mode='lines',
#         line=dict(color="#901b6e"),
#         name='PV'))
#
# fig = make_subplots(
#     rows=2, cols=1,
#     subplot_titles=[""],
#     shared_xaxes=True,
#     vertical_spacing=0.1)
#
# for trace in fig1.data:
#     fig.add_trace(trace, row=1, col=1)
#
# for trace in fig2.data:
#     fig.add_trace(trace, row=2, col=1)
#
# fig.update_layout(
#     title='',
#     width=1000,
#     height=800,
#     template="simple_white",
#     showlegend=True,
#     legend=dict(
#         orientation="h",
#         yanchor="bottom",
#         y=1.1,
#         xanchor="center",
#         x=0.5))
#
# fig.update_xaxes(title_text="", row=1, col=1)
# fig.update_yaxes(title_text="P in MW", row=1, col=1)
# fig.update_yaxes(title_text="Kapazitätsfaktor in %", row=2, col=1)
#
# fig.show()
#
# filename = 'EE_WIND_P_Kap.png'
# full_path = os.path.join(output_path, filename)
# fig.write_image(full_path, format='png', scale=3)
#
# # Wasserstoff-Lastkurve
#
# df_load_H2_15min_mw = df_load_H2_15min_mw.reset_index() # Index zurücksetzen, um auf Spalte "time" zurückgreifen zu können
#
# df_filtered = df_load_H2_15min_mw[(df_load_H2_15min_mw['time_input_year'] >= start_date_plots) & (df_load_H2_15min_mw['time_input_year'] <= end_date_plots)]
#
# fig = go.Figure()
#
# fig.add_trace(go.Scatter(
#     x=df_filtered['time_input_year'],
#     y=df_filtered['P (MW)'],
#     mode='lines',
#     name='Leistung H<sub>2</sub>',
#     line=dict(color='#00008b')))  # Dunkelblau
#
# fig.update_layout(
#     title='',
#     xaxis_title='Datum / Uhrzeit',
#     yaxis_title='P H<sub>2</sub> in MW',
#     width=1000,
#     height=600,
#     template="simple_white",
#     legend_title="Legende",
#     xaxis=dict(
#         tickformat='%Y-%m-%d %H:%M',
#         tickmode='auto',
#         nticks=5,
#         showgrid=True,
#         range=[start_date_plots, end_date_plots]),
#     yaxis=dict(
#         showgrid=True,
#         range=[0, None]))
#
# pio.show(fig)
#
# filename = 'Wasserstoff_Lastkurve.png'
# full_path = os.path.join(output_path, filename)
# fig.write_image(full_path, format='png', scale=3)
#
# # Masse Tankvorgänge FCEV - Normalverteilung
#
# data = np.array(individual_tank_masses_FCEV)
#
# # Erstelle einen Plot mit der Dichtefunktion
# plt.figure(figsize=(10, 6))
# sns.histplot(data, kde=True, bins=30, stat="density", label="Datenverteilung", color="blue")
#
# # Plot-Anpassungen
# plt.title("", fontsize=14)
# plt.xlabel("Wasserstoffmasse in kg pro Tankvorgang für FCEV", fontsize=12)
# plt.ylabel("Wahrscheinlichkeitsdichte", fontsize=12)
# #plt.legend()
# plt.grid()
# plt.tight_layout()
#
# filename = 'Normalverteilung_Tankmassen_FCEV.png'
# full_path = os.path.join(output_path, filename)
# plt.savefig(full_path, format='png', dpi=300)
# plt.show()
# plt.close()
#
# # Masse Tankvorgänge FCET - Normalverteilung
#
# data = np.array(individual_tank_masses_FCET)
#
# # Erstelle einen Plot mit der Dichtefunktion
# plt.figure(figsize=(10, 6))
# sns.histplot(data, kde=True, bins=30, stat="density", label="Datenverteilung", color="blue")
#
# # Plot-Anpassungen
# plt.title("", fontsize=14)
# plt.xlabel("Wasserstoffmasse in kg pro Tankvorgang für FCET", fontsize=12)
# plt.ylabel("Wahrscheinlichkeitsdichte", fontsize=12)
# #plt.legend()
# plt.grid()
# plt.tight_layout()
#
# filename = 'Normalverteilung_Tankmassen_FCET.png'
# full_path = os.path.join(output_path, filename)
# plt.savefig(full_path, format='png', dpi=300)
# plt.show()
# plt.close()
#
# # Energie Ladevorgänge BEV - Normalverteilung
#
# data = np.array(individual_tank_energies_BEV)
#
# # Erstelle einen Plot mit der Dichtefunktion
# plt.figure(figsize=(10, 6))
# sns.histplot(data, kde=True, bins=30, stat="density", label="Datenverteilung", color="blue")
#
# # Plot-Anpassungen
# plt.title("", fontsize=14)
# plt.xlabel("Energie in kWh pro Ladevorgang", fontsize=12)
# plt.ylabel("Wahrscheinlichkeitsdichte", fontsize=12)
# #plt.legend()
# plt.grid()
# plt.tight_layout()
#
# filename = 'Normalverteilung_Ladeenergie_BEV.png'
# full_path = os.path.join(output_path, filename)
# plt.savefig(full_path, format='png', dpi=300)
# plt.show()
# plt.close()
#
# # Balkendiagramm Saisonale Tankwahrscheinlichkeit FCEV
#
# fig = px.bar(df_monthly_refuel_prob_BEV,
#               x=['Jan','Feb','Mrz','Apr','Mai','Jun','Jul','Aug','Sep','Okt','Nov','Dez',],
#               y=[7.233, 8.231, 8.182, 8.141, 8.176, 9.386, 8.681, 8.950, 8.239, 8.404, 8.349, 8.029], #Daten aus Excel H2-Nachfrage
#               labels={'seasonal_refuel_prob': 'Seasonal Refuel Probability (%)'},
#               title='Seasonal Refuel Probability by Month',
#               color_discrete_sequence=['#00008b'])
#
# fig.update_traces(width=0.9)  # Balkenbreite auf 50% des Standardwerts reduzieren
#
# fig.update_traces(
#     marker_line_color='black',  # Farbe der Umrandung
#     marker_line_width=1.5)       # Breite der Umrandung
#
# fig.update_layout(
#     title='',
#     xaxis_title='',
#     yaxis_title='Saisonale Tankwahrscheinlichkeit in %',
#     width=550,
#     height=400,
#     template="simple_white",
#     legend_title="Legende",
#     xaxis=dict(
#         tickformat='%Y-%m-%d %H:%M',
#         tickmode='auto',
#         nticks=20,
#         showgrid=True,),
#     yaxis=dict(showgrid=True))
#
# fig.show()
#
# filename = 'Saisonale_Tankwahrscheinlichkeit_FCEV.png'
# full_path = os.path.join(output_path, filename)
# fig.write_image(full_path, format='png', scale=3)
#
# # Balkendiagramm Saisonale Tankwahrscheinlichkeit BEV
# fig = px.bar(df_monthly_refuel_prob_BEV,
#               x=['Jan','Feb','Mrz','Apr','Mai','Jun','Jul','Aug','Sep','Okt','Nov','Dez',],
#               y=df_monthly_refuel_prob_BEV['seasonal_refuel_prob']*100,
#               labels={'seasonal_refuel_prob': 'Seasonal Refuel Probability (%)'},
#               title='Seasonal Refuel Probability by Month',
#               color_discrete_sequence=['#00008b'])
#
# fig.update_traces(width=0.9)  # Balkenbreite auf 50% des Standardwerts reduzieren
#
# fig.update_traces(
#     marker_line_color='black',  # Farbe der Umrandung
#     marker_line_width=1.5)       # Breite der Umrandung
#
# fig.update_layout(
#     title='',
#     xaxis_title='',
#     yaxis_title='Saisonale Tankwahrscheinlichkeit in %',
#     width=550,
#     height=400,
#     template="simple_white",
#     legend_title="Legende",
#     xaxis=dict(
#         tickformat='%Y-%m-%d %H:%M',
#         tickmode='auto',
#         nticks=20,
#         showgrid=True,),
#     yaxis=dict(showgrid=True))
#
# fig.show()
#
# filename = 'Saisonale_Tankwahrscheinlichkeit_BEV.png'
# full_path = os.path.join(output_path, filename)
# fig.write_image(full_path, format='png', scale=3)
#
# # Diagramm der relativen Tankwahrscheinlichkeiten für BEV
#
# df_rel_refuel_prob_BEV_combined_plt = df_rel_refuel_prob_BEV_combined.copy()
# row_00 = df_rel_refuel_prob_BEV_combined_plt[df_rel_refuel_prob_BEV_combined_plt['Time'] == '00:00']
# row_24 = row_00.copy()
# row_24['Time'] = '24:00'
# df_rel_refuel_prob_BEV_combined_plt = pd.concat([df_rel_refuel_prob_BEV_combined_plt, row_24], ignore_index=True)
#
# mon_thu_sum=df_rel_refuel_prob_BEV_combined_plt['Mon-Thu'].sum()*4
# fri_sum=df_rel_refuel_prob_BEV_combined_plt['Fri'].sum()
# sat_sum=df_rel_refuel_prob_BEV_combined_plt['Sat'].sum()
# sun_sum=df_rel_refuel_prob_BEV_combined_plt['Sun'].sum()
# sum_sum=mon_thu_sum+fri_sum+sat_sum+sun_sum
#
# fig = px.line(
#     df_rel_refuel_prob_BEV_combined_plt,
#     x='Time',
#     y=['Mon-Thu', 'Fri', 'Sat', 'Sun'],
#     title='Tankwahrscheinlichkeit nach Wochentagen',
#     labels={'Time': 'Viertelstunde', 'rel_refuel_prob': 'Tankwahrscheinlichkeit'})
#
# fig.update_layout(
#     title='',
#     xaxis_title='',
#     yaxis_title='Anteil der Ladevorgänge in %',
#     width=1000,
#     height=600,
#     template="simple_white",
#     legend_title="",
#     xaxis=dict(
#         tickformat='%H:%M',
#         tickmode='auto',
#         dtick="3600000",
#         nticks=13,
#         showgrid=True,
#         range=["00:00", "24:00"]),
#     yaxis=dict(showgrid=True),
#     legend=dict(
#         orientation="h",  # Horizontale Ausrichtung
#         x=0.5,  # Horizontale Position (Mitte)
#         y=-0.15,  # Vertikale Position (oberhalb des Plots)
#         xanchor="center",  # Legende zentrieren
#         yanchor="bottom"   # Legende knapp oberhalb des Plots positionieren
#     ))
#
# fig['data'][0]['line']['color']="#901b6e"  # lila
# fig['data'][1]['line']['color']="#d7471f"  # orange
# fig['data'][2]['line']['color']="#1c1c1c"  # graphitschwarz
# fig['data'][3]['line']['color']="#00008b"  # dunkelblau
#
# fig['data'][0]['name'] = "Mo-Do"
# fig['data'][1]['name'] = "Fr"
# fig['data'][2]['name'] = "Sa"
# fig['data'][3]['name'] = "So"
#
# fig.show()
#
# filename = 'Relative_Ladewahrscheinlichkeit_BEV.png'
# full_path = os.path.join(output_path, filename)
# fig.write_image(full_path, format='png', scale=3)
#
# # Diagramm der BEV-Lastkurve
#
# df_load_el_15min_mw = df_load_el_15min_mw.reset_index() # Index zurücksetzen, um auf Spalte "time" zurückgreifen zu können
#
# df_filtered = df_load_el_15min_mw[(df_load_el_15min_mw['time_input_year'] >= start_date_plots) & (df_load_el_15min_mw['time_input_year'] <= end_date_plots)]
#
# fig = go.Figure()
#
# fig.add_trace(go.Scatter(
#     x=df_filtered['time_input_year'],
#     y=df_filtered['P (MW)'],
#     mode='lines',
#     name='el. Leistung',
#     line=dict(color='#00008b')))  # Dunkelblau
#
# fig.update_layout(
#     title='',
#     xaxis_title='Datum / Uhrzeit',
#     yaxis_title='P<sub>el</sub> in MW',
#     width=1000,
#     height=600,
#     template="simple_white",
#     legend_title="Legende",
#     xaxis=dict(
#         tickformat='%Y-%m-%d %H:%M',
#         tickmode='auto',
#         nticks=5,
#         showgrid=True,
#         range=[start_date_plots, end_date_plots]),
#     yaxis=dict(
#         showgrid=True,
#         range=[0, None]))
#
# pio.show(fig)
#
# filename = 'BEV_Lastkurve.png'
# full_path = os.path.join(output_path, filename)
# fig.write_image(full_path, format='png', scale=3)
#
# # Elektrolyseur - Lastkurve
#
# df_electrolyzer_15min = df_electrolyzer_15min.reset_index() # Index zurücksetzen, um auf Spalte "time" zurückgreifen zu können
#
# df_filtered = df_electrolyzer_15min[(df_electrolyzer_15min['time'] >= start_date_plots) & (df_electrolyzer_15min['time'] <= end_date_plots)]
# y_max = df_filtered['P_ac [MW]'].max() * 1.1  # 10% Puffer hinzufügen
#
# fig = go.Figure()
# fig.add_trace(go.Scatter(
#     x=df_electrolyzer_15min['time'],
#     y=df_electrolyzer_15min['P_ac [MW]'],
#     mode='lines',
#     name='P elektrisch [MW]',
#     line=dict(color='#00008b')))
#
# fig.update_layout(
#     title='',
#     template="simple_white",
#     xaxis_title='Datum / Uhrzeit',
#     yaxis_title='Leistung in MW',
#     xaxis=dict(
#         tickformat='%Y-%m-%d %H:%M',
#         tickmode='auto',
#         nticks=5,
#         showgrid=True,
#         range=[start_date_plots, end_date_plots]),
#     yaxis=dict(
#         title='Leistung in MW',
#         showgrid=True,
#         range=[0, y_max]),
#     )
#
# pio.show(fig)
#
# filename = 'Lastkurve_Elektrolyseur.png'
# full_path = os.path.join(output_path, filename)
# fig.write_image(full_path, format='png', scale=3)
#
# # Elektrolyseur - H2-Produktion
# df_filtered = df_electrolyzer_15min[(df_electrolyzer_15min['time'] >= start_date_plots) & (df_electrolyzer_15min['time'] <= end_date_plots)]
#
# fig = go.Figure()
#
# fig.add_trace(go.Scatter(
#     x=df_electrolyzer_15min['time'],
#     y=df_electrolyzer_15min['hydrogen production [Kg/dt]'],
#     mode='lines',
#     name='H<sub>2</sub> production',
#     line=dict(color='#00008b')))
#
# fig.update_layout(
#     title='Wasserstoffproduktion Elektrolyseur',
#     xaxis_title='Datum / Uhrzeit',
#     yaxis_title='H<sub>2</sub> [kg/15min]',
#     xaxis=dict(
#         tickformat='%Y-%m-%d %H:%M',
#         tickmode='auto',
#         nticks=7,
#         showgrid=True,
#         range=[start_date_plots, end_date_plots]),
#         width=1000,
#         height=600,
#         template="simple_white",
#         legend_title="Legende",)
#
# pio.show(fig)
#
# filename = 'Wasserstoffproduktion_Elektrolyseur.png'
# full_path = os.path.join(output_path, filename)
# fig.write_image(full_path, format='png', scale=3)
#
# # Balkendiagramm Energiemengen Herkunft
# # Summen der Energiemengen berechnen
# E_pv = df_res_links_2["pv_to_el"] * dt_h
# pv_sum = E_pv.sum()
# E_pv_infeed = df_res_generators_2["pv_infeed"] * dt_h
# pv_infeed_sum = E_pv_infeed.sum()
# E_wind = df_res_links_2["wind_to_el"] * dt_h
# wind_sum = E_wind.sum()
# E_wind_infeed = df_res_generators_2["wind_infeed"] * dt_h
# wind_infeed_sum = E_wind_infeed.sum()
# E_grid = df_res_generators_2["grid"] * dt_h
# grid_sum = E_grid.sum()
# df_bar_energy = pd.DataFrame({'Energiequelle': ['Eigenverbrauch', 'Einspeisung', 'Eigenverbrauch', 'Einspeisung', 'Eigenverbrauch'],
#                               'Energie [MWh]': [pv_sum, pv_infeed_sum, wind_sum, wind_infeed_sum, grid_sum],
#                               'Quelle': ['PV', 'PV', 'Wind', 'Wind', 'Netz']})
#
# fig = px.bar(df_bar_energy,
#               x='Quelle',
#               y='Energie [MWh]',
#               color='Energiequelle',
#               template='simple_white',
#               title='<b>Energieverbrauch und -herkunft für die Tankstelle</b><br><sup>Energie in MWh<sup>',
#               text=df_bar_energy['Energie [MWh]'].round(1),
#               width=1000,
#               height=600,
#               color_discrete_map={'Eigenverbrauch': "#c60c0f", 'Einspeisung': "#901b6e"}
#               )
#
# fig.update_xaxes(tickfont=dict(size=12), title_text='')
# fig.update_yaxes(tickfont=dict(size=12), title_text='')
# fig.update_traces(width=0.5)
# fig.update_layout(
#     yaxis_tickformat = '.',
#     legend_title="Legende")
#
# fig.show()
#
# filename = 'Balkendiagramm_Energiemengen_Herkunft.png'
# full_path = os.path.join(output_path, filename)
# fig.write_image(full_path, format='png', scale=3)
#
# # Diagramm zur Leistung der einzelnen Generatoren
#
# df_res_generators_2 = df_res_generators_2.reset_index() # Index zurücksetzen, um auf Spalte "time" zurückgreifen zu können
#
# df_filtered = df_res_generators_2[(df_res_generators_2['snapshot'] >= start_date_plots) & (df_res_generators_2['snapshot'] <= end_date_plots)]
#
# x_values = df_res_generators_2['snapshot']
# y_values = ['pv',
#             'pv_infeed',
#             'wind',
#             'wind_infeed',
#             'grid']
#
# custom_labels = {
#     'pv':'PV (Eigenverbrauch)',
#     'pv_infeed':'PV (Einspeisung)',
#     'wind': 'Wind (Eigenverbrauch)',
#     'wind_infeed': 'Wind (Einspeisung)',
#     'grid': 'Netzbezug'}
#
# avg_pv = df_res_generators_2['pv'].mean()
# avg_wind = df_res_generators_2['wind'].mean()
# time = df_res_generators_2['snapshot'].min()
#
# fig = px.line(df_res_generators_2, x = x_values, y = y_values)
#
# fig['data'][0]['line']['color'] = "#c60c0f"  # rot
# fig['data'][1]['line']['color'] = "#d7471f"  # orange
# fig['data'][2]['line']['color'] = "#901b6e"  # lila
# fig['data'][3]['line']['color'] = "#00008b"  # dunkelblau
# fig['data'][4]['line']['color'] = "#696969"  # grau
#
# fig['data'][0]['name'] = custom_labels['pv']
# fig['data'][1]['name'] = custom_labels['pv_infeed']
# fig['data'][2]['name'] = custom_labels['wind']
# fig['data'][3]['name'] = custom_labels['wind_infeed']
# fig['data'][4]['name'] = custom_labels['grid']
#
# fig.update_layout(
#     title = 'Leistung Generatoren',
#     width = 1000,
#     height = 600,
#     xaxis_title = 'Datum / Uhrzeit',
#     yaxis_title = 'P [MW]',
#     template="simple_white",
#     legend_title="Legende",
#     xaxis=dict(
#         tickformat='%Y-%m-%d %H:%M',
#         tickmode='auto',
#         nticks=7,
#         showgrid=True,
#         range=[start_date_plots, end_date_plots]))
#
# fig.add_trace(
#     go.Scatter(
#         x=[df_res_generators_2['snapshot'].min(), df_res_generators_2['snapshot'].max()],
#         y=[avg_pv, avg_pv],
#         mode="lines",
#         line=dict(color="black", width=3, dash="dot"),
#         name="Durchschnittliche PV-Leistung"))
#
# fig.add_trace(
#     go.Scatter(
#         x=[df_res_generators_2['snapshot'].min(), df_res_generators_2['snapshot'].max()],
#         y=[avg_wind, avg_wind],
#         mode="lines",
#         line=dict(color="black", width=3, dash="dash"),
#         name="Durchschnittliche WKA-Leistung"))
#
# fig.show()
#
# filename = 'Liniendiagramm_Leistung_Generatoren.png'
# full_path = os.path.join(output_path, filename)
# fig.write_image(full_path, format='png', scale=3)
#
# # Diagramm zur Leistung der einzelnen Links
#
# df_res_links_2 = df_res_links_2.reset_index() # Index zurücksetzen, um auf Spalte "time" zurückgreifen zu können
#
# df_filtered = df_res_links_2[(df_res_links_2['snapshot'] >= start_date_plots) & (df_res_links_2['snapshot'] <= end_date_plots)]
#
# x_values = df_res_links_2['snapshot']
# y_values = ['pv_to_el',
#             'wind_to_el',
#             'electrolyzer',
#             'compressor_h2_flow']
#
# custom_labels = {
#     'pv_to_el': 'PV',
#     'wind_to_el': 'Wind',
#     'electrolyzer': 'Elektrolyseur',
#     'compressor_h2_flow': 'Kompressor'}
#
# avg_electrolyzer = df_res_links_2['electrolyzer'].mean()
# time = df_res_links_2.index.min()
#
# fig = px.line(df_res_links_2, x=x_values, y=y_values)
#
# fig['data'][0]['line']['color'] = "#c60c0f"  # rot
# fig['data'][1]['line']['color'] = "#d7471f"  # orange
# fig['data'][2]['line']['color'] = "#901b6e"  # lila
# fig['data'][3]['line']['color'] = "#00008b"  # dunkelblau
#
# fig['data'][0]['name'] = custom_labels['pv_to_el']
# fig['data'][1]['name'] = custom_labels['wind_to_el']
# fig['data'][2]['name'] = custom_labels['electrolyzer']
# fig['data'][3]['name'] = custom_labels['compressor_h2_flow']
#
# fig.update_layout(
#     title='Leistung Links',
#     width=1000,
#     height=600,
#     xaxis_title='Datum / Uhrzeit',
#     yaxis_title='P [MW]',
#     template="simple_white",
#     legend_title="Legende",
#     xaxis=dict(
#         tickformat='%Y-%m-%d %H:%M',
#         tickmode='auto',
#         nticks=7,
#         showgrid=True,
#         range=[start_date_plots, end_date_plots]))
#
# fig.add_trace(
#     go.Scatter(
#         x=[df_res_links_2['snapshot'].min(), df_res_links_2['snapshot'].max()],
#         y=[avg_electrolyzer, avg_electrolyzer],
#         mode="lines",
#         line=dict(color="black", width=3, dash="dot"),
#         name="Durchschnittliche Elektrolyseur-Leistung"))
#
# fig.show()
#
# filename = 'Liniendiagramm_Leistung_Links.png'
# full_path = os.path.join(output_path, filename)
# fig.write_image(full_path, format='png', scale=3)
#
# # Diagramm zu Speicherfüllständen
#
# df_res_stores_2_E = n.stores_t.e
# df_res_stores_2_E = df_res_stores_2_E.reset_index() # Index zurücksetzen, um auf Spalte "snapshot" zurückgreifen zu können
#
# x_values = df_res_stores_2_E['snapshot']
# fig = px.line(df_res_stores_2_E, x = x_values, y = 'el_storage')
#
# custom_labels = {
#     'el_storage': 'Batteriespeicher',
#     'H2_storage': 'Wasserstoffspeicher'}
#
# avg_el = df_res_stores_2_E['el_storage'].mean()
# avg_h2 = df_res_stores_2_E['H2_storage'].mean()
# time = df_res_stores_2_E['snapshot'].min()
#
# fig = px.line(df_res_stores_2_E, x=df_res_stores_2_E['snapshot'], y=['el_storage', 'H2_storage'])
#
# fig['data'][0]['line']['color']="#901b6e"  # lila
# fig['data'][1]['line']['color']="#d7471f"  #orange
#
# fig['data'][0]['name'] = custom_labels['el_storage']
# fig['data'][1]['name'] = custom_labels['H2_storage']
#
# fig.update_layout(
#     title = '',
#     width = 1000,
#     height = 600,
#     xaxis_title = 'Datum / Uhrzeit',
#     yaxis_title = 'Energie in MWh',
#     template="simple_white",
#     legend_title="Legende",
#     xaxis=dict(
#         tickformat='%Y-%m-%d %H:%M',
#         tickmode='auto',
#         nticks=7,
#         showgrid=True,
#         range=[start_date_plots, end_date_plots]))
#
# fig.add_trace(
#     go.Scatter(
#         x=[df_res_stores_2_E['snapshot'].min(), df_res_stores_2_E['snapshot'].max()],
#         y=[avg_el, avg_el],
#         mode="lines",
#         line=dict(color="black", width=3, dash="dot"),
#         name="Durchschnitt Batteriespeicher"))
#
# fig.add_trace(
#     go.Scatter(
#         x=[df_res_stores_2_E['snapshot'].min(), df_res_stores_2_E['snapshot'].max()],
#         y=[avg_h2, avg_h2],
#         mode="lines",
#         line=dict(color="black", width=3, dash="dash"),
#         name="Durchschnitt Wasserstoffspeicher"))
#
# fig.show()
#
# filename = 'Liniendiagramm_Speicherfüllstände.png'
# full_path = os.path.join(output_path, filename)
# fig.write_image(full_path, format='png', scale=3)
#
# # Diagramm Last
#
# df_res_loads_2 = df_res_loads_2.reset_index() # Index zurücksetzen, um auf Spalte "snapshot" zurückgreifen zu können
#
# x_values = df_res_loads_2['snapshot']
# fig = px.line(df_res_loads_2, x = x_values, y = 'H2_load')
#
# custom_labels = {
#     'H2_load': 'H<sub>2</sub>-Last',
#     'el_charging_station_load': 'el. Last Ladesäulen',
#     'compressor_el_load': 'el. Last Kompressor',
#     'electrolyzer_el_load': 'el. Last Elektrolyseur'}
#
# avg_elektrolyzer = df_res_loads_2['electrolyzer_el_load'].mean()
# time = df_res_loads_2['snapshot'].min()
#
# fig = px.line(df_res_loads_2, x=df_res_loads_2['snapshot'], y=['H2_load', 'el_charging_station_load', 'compressor_el_load', 'electrolyzer_el_load'])
#
# fig['data'][0]['line']['color']="#901b6e"  # lila
# fig['data'][1]['line']['color']="#d7471f"  #orange
# fig['data'][2]['line']['color']="#c60c0f"  # rot
# fig['data'][3]['line']['color']="#00008b"  # dunkelblau
#
# fig['data'][0]['name'] = custom_labels['H2_load']
# fig['data'][1]['name'] = custom_labels['el_charging_station_load']
# fig['data'][2]['name'] = custom_labels['compressor_el_load']
# fig['data'][3]['name'] = custom_labels['electrolyzer_el_load']
#
# fig.update_layout(
#     title = 'Lasten',
#     width = 1000,
#     height = 600,
#     xaxis_title = 'Datum / Uhrzeit',
#     yaxis_title = 'P [MW]',
#     template="simple_white",
#     legend_title="Legende",
#     xaxis=dict(
#         tickformat='%Y-%m-%d %H:%M',
#         tickmode='auto',
#         nticks=7,
#         showgrid=True,
#         range=[start_date_plots, end_date_plots]),
#     yaxis=dict(showgrid=True))
#
# fig.add_trace(
#     go.Scatter(
#         x=[df_res_loads_2['snapshot'].min(), df_res_loads_2['snapshot'].max()],
#         y=[avg_elektrolyzer, avg_elektrolyzer],
#         mode="lines",
#         line=dict(color="black", width=3, dash="dot"),
#         name="Durchschnitt Elektrolyseur"))
#
# fig.show()
#
# filename = 'Liniendiagramm_Lasten.png'
# full_path = os.path.join(output_path, filename)
# fig.write_image(full_path, format='png', scale=3)
#
# # Balkendiagramm Kompressorstufen Energie
# x_labels = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
# y_values1 = [1, 3.12, 6.97, 15.55, 34.72, 77.51, 173.04, 386.29, 862.36, 1000]  # Werte für Gruppe 1
# y_values2 = [30, 93.63, 209.02, 466.61, 1000, "", "", "", "", ""]   # Werte für Gruppe 2
#
# # Erstellen der Balken
# fig = go.Figure(data=[
#     go.Bar(
#         name='Eingangsdruck 1 bar',  # Name für die Legende
#         x=x_labels,
#         y=y_values1,
#         marker=dict(color='blue', line=dict(color='black', width=1.5)),
#         width=0.4  # Balkenbreite
#     ),
#     go.Bar(
#         name='Eingangsdruck 30 bar',  # Name für die Legende
#         x=x_labels,
#         y=y_values2,
#         marker=dict(color='red', line=dict(color='black', width=1.5)),
#         width=0.4  # Balkenbreite
#     )
# ])
#
# # Layout-Einstellungen
# fig.update_layout(
#     barmode='group',  # Gruppierte Balken
#     title='',
#     xaxis_title='Verdichterstufe',
#     yaxis_title='Enddruck pro Stufe in bar',
#     template="simple_white",
#     width=800,
#     height=500,
#     legend_title="",
#     legend=dict(
#         x=0,
#         y=1,
#         xanchor='left',
#         yanchor='top'),
#     xaxis=dict(
#         nticks=11,
#         ))
#
# # Diagramm anzeigen
# fig.show()
#
# filename = 'Kompressorstufen_Balkendiagramm.png'
# full_path = os.path.join(output_path, filename)
# fig.write_image(full_path, format='png', scale=3)
#
# # Balkendiagramm Verteilung Energiemengen an Zapfsäule FCEV
# df_charging_points_FCEV_sum['Nr'] = range(1, len(df_charging_points_FCEV_sum) + 1)
#
# fig = px.bar(df_charging_points_FCEV_sum,
#               x=df_charging_points_FCEV_sum['Nr'],
#               y=df_charging_points_FCEV_sum['Share [%]'],
#               labels={'Share [%]': 'Anteil Zapfsäule an abgegebenem H<sub>2'},
#               title='Nutzungsanteil der Zapfsäulen',
#               color_discrete_sequence=['#00008b'])
#
# fig.update_traces(width=0.9)  # Balkenbreite auf 50% des Standardwerts reduzieren
#
# fig.update_traces(
#     marker_line_color='black',  # Farbe der Umrandung
#     marker_line_width=1.5)       # Breite der Umrandung
#
# fig.update_layout(
#     title='',
#     xaxis_title='FCEV Zapfsäule Nr',
#     yaxis_title='Anteil an H<sub>2</sub> pro Zapfsäule in %',
#     width=550,
#     height=400,
#     template="simple_white",
#     legend_title="Legende",
#     xaxis=dict(
#         tickformat='%Y-%m-%d %H:%M',
#         tickmode='auto',
#         nticks=25,
#         showgrid=True,),
#     yaxis=dict(showgrid=True))
#
# fig.show()
#
# filename = 'Anteil_H2_pro_Zapfsäule_FCEV.png'
# full_path = os.path.join(output_path, filename)
# fig.write_image(full_path, format='png', scale=3)
#
# # Balkendiagramm Verteilung Energiemengen an Zapfsäule FCET
# df_charging_points_FCET_sum['Nr'] = range(1, len(df_charging_points_FCET_sum) + 1)
#
# fig = px.bar(df_charging_points_FCET_sum,
#               x=df_charging_points_FCET_sum['Nr'],
#               y=df_charging_points_FCET_sum['Share [%]'],
#               labels={'Share [%]': 'Anteil Zapfsäule an abgegebenem H<sub>2'},
#               title='Nutzungsanteil der Zapfsäulen',
#               color_discrete_sequence=['#00008b'])
#
# fig.update_traces(width=0.9)  # Balkenbreite auf 50% des Standardwerts reduzieren
#
# fig.update_traces(
#     marker_line_color='black',  # Farbe der Umrandung
#     marker_line_width=1.5)       # Breite der Umrandung
#
# fig.update_layout(
#     title='',
#     xaxis_title='FCET Zapfsäule Nr',
#     yaxis_title='Anteil an H<sub>2</sub> pro Zapfsäule in %',
#     width=550,
#     height=400,
#     template="simple_white",
#     legend_title="Legende",
#     xaxis=dict(
#         tickformat='%Y-%m-%d %H:%M',
#         tickmode='auto',
#         nticks=20,
#         showgrid=True,),
#     yaxis=dict(showgrid=True))
#
# fig.show()
#
# filename = 'Anteil_H2_pro_Zapfsäule_FCET.png'
# full_path = os.path.join(output_path, filename)
# fig.write_image(full_path, format='png', scale=3)
#
# # Balkendiagramm Verteilung Energiemengen an Zapfsäule BEV
# df_charging_points_sum['Nr'] = range(1, len(df_charging_points_sum) + 1)
#
# fig = px.bar(df_charging_points_sum,
#               x=df_charging_points_sum['Nr'],
#               y=df_charging_points_sum['Share [%]'],
#               labels={'Share [%]': 'Anteil Ladesäule an abgegebener Energie'},
#               title='Nutzungsanteil der Ladesäulen',
#               color_discrete_sequence=['#00008b'])
#
# fig.update_traces(width=0.9)  # Balkenbreite auf 50% des Standardwerts reduzieren
#
# fig.update_traces(
#     marker_line_color='black',  # Farbe der Umrandung
#     marker_line_width=1.5)       # Breite der Umrandung
#
# fig.update_layout(
#     title='',
#     xaxis_title='Ladesäule Nr',
#     yaxis_title='Anteil an Energie pro Ladesäule in %',
#     width=550,
#     height=400,
#     template="simple_white",
#     legend_title="Legende",
#     xaxis=dict(
#         tickformat='%Y-%m-%d %H:%M',
#         tickmode='auto',
#         nticks=10,
#         showgrid=True,),
#     yaxis=dict(showgrid=True))
#
# fig.show()
#
# filename = 'Anteil_Energie_pro_Ladesäule.png'
# full_path = os.path.join(output_path, filename)
# fig.write_image(full_path, format='png', scale=3)

print(f"Anzahl FCEV im Jahr {year}: {n_FCEV_year:,.0f}".replace(",", "."))
print(f"Anzahl FCET im Jahr {year}: {n_FCET_year:,.0f}".replace(",", "."))
print(f"Anzahl FCEV-Tankvorgänge im Jahr {year}: {df_load_H2['refueling_event_FCEV'].sum():,.0f}".replace(",", "."))
print(f"Anzahl FCET-Tankvorgänge im Jahr {year}: {df_load_H2['refueling_event_FCET'].sum():,.0f}".replace(",", "."))
print(f"Anzahl BEV-Ladevorgänge im Jahr {year}: {df_load_BEV['refueling_event'].sum():,.0f}".replace(",", "."))