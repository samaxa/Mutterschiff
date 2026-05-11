import pypsaheat as ph
import importlib.metadata as md

print(md.version("pypsaheat"))
print(ph.__file__)

import pypsaheat, os, datetime

path = pypsaheat.__file__
mtime = os.path.getmtime(path)

print("pypsaheat file:", path)
print("Last modified:",
      datetime.datetime.fromtimestamp(mtime))
