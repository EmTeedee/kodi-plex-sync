"""Utility class to get configuration values"""
import yaml

__all__ = [
    'cfg_get'
]

with open("config.yml", "r", encoding="utf-8") as ymlfile:
    cfg = yaml.load(ymlfile, Loader=yaml.SafeLoader)

def cfg_get(section, key = None, default = None):
    """Get a configuration value or return default"""
    try:
        if key is None:
            return cfg[section]
        else:
            return cfg[section][key]
    except KeyError:
        return default
