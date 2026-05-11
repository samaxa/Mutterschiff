import pandas as pd

df1 = pd.read_csv("Input_Data/Archiv/2026-01-19-Mehrfamilienhaus-Lastprofile_konventionell_Raumwaerme_cutoff15C.csv")
df2 = pd.read_csv("./Input_Data/2026-01-19-Mehrfamilienhaus-Lastprofile_konventionell.csv")

# Spalte aus df1 in df2 einfügen
df2["Raumwaerme_(kW)"] = df1["Raumwaerme_(kW)"]

df2.to_csv("./Input_Data/2026-01-19-Mehrfamilienhaus-Lastprofile_konventionell.csv", index=False)
