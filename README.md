# Mutterschiff
Eigene Python Projekte / Alte Python Projekte

## Python-Umgebung (PC und Laptop)

Die Umgebung selbst (`.venv`) wird **nicht** ins Git hochgeladen – sie enthält
rechnerspezifische Pfade und ist sehr groß. Stattdessen steht in
`requirements.txt`, welche Pakete gebraucht werden. Auf jedem Rechner wird
daraus einmal dieselbe Umgebung gebaut:

1. Repository pullen.
2. `setup_venv.bat` doppelklicken → legt `.venv` im Repo-Ordner an und
   installiert alles.
3. In PyCharm: *Settings → Project → Python Interpreter → Add Interpreter →
   Add Local Interpreter → Existing* → `<Repo>\.venv\Scripts\python.exe`.
4. Bei alten Run-Konfigurationen, die noch auf einen anderen Interpreter
   zeigen: *Run → Edit Configurations…* → Interpreter auf den neuen umstellen
   (oder die Konfiguration löschen, sie wird beim nächsten Start neu angelegt).

Neues Paket gebraucht? In `requirements.txt` eintragen, committen, und auf dem
anderen Rechner nach dem Pull `setup_venv.bat` erneut ausführen.
