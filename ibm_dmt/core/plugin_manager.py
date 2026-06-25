import importlib
import pkgutil
import inspect
from pathlib import Path
from typing import Optional
from ibm_dmt.core.disaster_module import DisasterModule


class PluginManager:
    _modules: dict[str, DisasterModule] = {}

    def discover_modules(self) -> dict[str, DisasterModule]:
        self._modules = {}
        modules_path = Path(__file__).parent.parent / "modules"
        if not modules_path.exists():
            return self._modules

        for finder, name, is_pkg in pkgutil.iter_modules([str(modules_path)]):
            if not is_pkg:
                continue
            try:
                package = importlib.import_module(f"ibm_dmt.modules.{name}")
                plugin_module = importlib.import_module(f"ibm_dmt.modules.{name}.plugin")
                for attr_name in dir(plugin_module):
                    attr = getattr(plugin_module, attr_name)
                    if (inspect.isclass(attr) and issubclass(attr, DisasterModule)
                            and attr is not DisasterModule):
                        instance = attr()
                        self._modules[instance.name] = instance
            except Exception:
                continue

        return self._modules

    def get_module(self, name: str) -> Optional[DisasterModule]:
        return self._modules.get(name)

    def get_all_modules(self) -> dict[str, DisasterModule]:
        return self._modules
