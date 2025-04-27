import json
from pathlib import Path

class PresetManager:
    def __init__(self, preset_file='presets.json'):
        self.preset_file = Path(preset_file)
        self.presets = self._load_presets()
    
    def _load_presets(self):
        try:
            with open(self.preset_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def save_preset(self, name, values):
        self.presets[name] = values
        self._save_to_file()
        return name
    
    def load_preset(self, name):
        return self.presets.get(name)
    
    def _save_to_file(self):
        with open(self.preset_file, 'w') as f:
            json.dump(self.presets, f, indent=4)
    
    def get_preset_names(self):
        return list(self.presets.keys()) 