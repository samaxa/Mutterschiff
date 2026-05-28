import matplotlib.pyplot as plt
import numpy as np

# =========================================
# Daten
# =========================================

categories = ["GWP", "TAP", "FET", "MRS", "FRS", "PMF"]
scenarios = ["2000", "4000", "6000", "8000"]

# Gesamtwerte
gesamt = np.array([
    [2.764360649, 0.019861126, 2.299132867, 0.082427593, 0.714148353, 0.00851159],
    [2.72860587, 0.018296441, 2.24978955, 0.0778647, 0.70427583, 0.0078624],
    [2.72517626, 0.01783351, 2.23334166, 0.07702016, 0.70082203, 0.0077959],
    [2.71704986, 0.01767111, 2.23334166, 0.07702016, 0.70082203, 0.0077959]
])
# Stromwerte
strommix = np.array([
    [2.65814768, 0.015642965, 2.196100791, 0.072855545, 0.684992302, 0.007140383],
    [2.65814768, 0.01564297, 2.19610079, 0.07285555, 0.6849923, 0.00714038],
    [2.65814768, 0.01564297, 2.19610079, 0.07285555, 0.6849923, 0.00714038],
    [2.65814768, 0.01564297, 2.19610079, 0.07285555, 0.6849923, 0.00714038]
])

# Betriebsstoffwerte
betriebsstoffe = np.array([
    [0.034601763, 0.000158098, 0.004426621, 0.000437326, 0.009387745, 7.13533E-05],
    [0.034601763, 0.0001581, 0.00442662, 0.00043733, 0.00938774, 7.13533E-05],
    [0.034601763, 0.000158098, 0.004426621, 0.000437326, 0.009387745, 7.13533E-05],
    [0.034601763, 0.000158098, 0.004426621, 0.000437326, 0.009387745, 7.13533E-05]
])

# Herstellungswerte
herstellung = np.array([
    [0.07161121, 0.00406006, 0.09860546, 0.00913472, 0.01976831, 0.00129985],
    [0.035856424, 0.00249538, 0.04926214, 0.004571831, 0.009895786, 0.000650663],
    [0.03242681, 0.002032446, 0.03281424, 0.00372729, 0.00644198, 0.00058416],
    [0.02430041, 0.00187004, 0.03281424, 0.00372729, 0.00644198, 0.00058416]
])

# =========================================
# Prozentwerte berechnen
# =========================================

strommix_pct = strommix / gesamt * 100
betriebsstoffe_pct = betriebsstoffe / gesamt * 100
herstellung_pct = herstellung / gesamt * 100

# =========================================
# Plot
# =========================================

fig, ax = plt.subplots(figsize=(12,6))

x = np.arange(len(categories))
width = 0.16

colors = {
    "Strommix": "#1f77b4",
    "Betriebsstoffe": "#ff7f0e",
    "Herstellung": "#2ca02c"
}

for i, scenario in enumerate(scenarios):

    xpos = x + (i - 1.5) * width

    # Strommix
    ax.bar(
        xpos,
        strommix_pct[i],
        width,
        color=colors["Strommix"],
        edgecolor="black",
        linewidth=0.7
    )

    # Betriebsstoffe
    ax.bar(
        xpos,
        betriebsstoffe_pct[i],
        width,
        bottom=strommix_pct[i],
        color=colors["Betriebsstoffe"],
        edgecolor="black",
        linewidth=0.7
    )

    # Herstellung
    ax.bar(
        xpos,
        herstellung_pct[i],
        width,
        bottom=strommix_pct[i] + betriebsstoffe_pct[i],
        color=colors["Herstellung"],
        edgecolor="black",
        linewidth=0.7
    )

    # Betriebsstunden unter Balken
    for j in range(len(categories)):
        ax.text(
            xpos[j],
            -7,
            scenario,
            ha='center',
            va='top',
            rotation=90,
            fontsize=8
        )

# =========================================
# Layout
# =========================================

ax.set_xticks(x)
ax.set_xticklabels(categories, fontsize=12)

ax.set_ylabel("Prozentwert [%]")
ax.set_ylim(0, 105)

ax.set_title("Sensitivitätsanalyse Betriebsstunden")

ax.grid(axis='y', linestyle='--', alpha=0.3)

# Legende
ax.legend(
    handles=[
        plt.Rectangle((0,0),1,1,color=colors["Strommix"], ec="black"),
        plt.Rectangle((0,0),1,1,color=colors["Betriebsstoffe"], ec="black"),
        plt.Rectangle((0,0),1,1,color=colors["Herstellung"], ec="black")
    ],
    labels=["Strommix", "Betriebsstoffe", "Materialien"],
    loc="lower right"
)

plt.tight_layout()
plt.savefig("sensitivitaet_betriebsstunden.svg", bbox_inches="tight")
plt.show()