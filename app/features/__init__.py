import importlib
import pkgutil

# Automatically import all models in the features package
packet = __name__
for loader, name, is_pkg in pkgutil.walk_packages(__path__, packet + "."):
    importlib.import_module(name)
