import pandas as pd

src_path = r"C:\Users\sarah\Documents\GitHub\EMM_Projekt_Gruppe4\Durchlauferhitzer_WW\Input_Data_clean\2026-01-24-Mehrfamilienhaus-Strom_Lastprofile.csv"
dst_path = r"C:\Users\sarah\Documents\GitHub\EMM_Projekt_Gruppe4\Durchlauferhitzer_WW\Input_Data_clean\2026-01-19-Mehrfamilienhaus-Lastprofile_zukunftsfuehrend_clean.csv"

time_col = "Zeit (TT-MM hh:mm)"

# CSVs laden (OHNE parse_dates!)
df_src = pd.read_csv(src_path)
df_dst = pd.read_csv(dst_path)

# Zeitspalte parsen
df_src[time_col] = pd.to_datetime(df_src[time_col], format="%d-%m %H:%M")
df_dst[time_col] = pd.to_datetime(df_dst[time_col], format="%d-%m %H:%M")

# Zeit als Index
df_src = df_src.set_index(time_col)
df_dst = df_dst.set_index(time_col)

# Stromspalte übernehmen (sauber über Zeitindex)
df_dst["Strom_gesamt_(kW)"] = df_src["Strom gesamt (kW)"].reindex(df_dst.index)

# Zurückschreiben
df_dst.reset_index().to_csv(dst_path, index=False)

print("✅ Strom_gesamt_(kW) erfolgreich kopiert.")
