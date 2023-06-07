#!/usr/local/bin/python
# coding=utf-8
import sys
import base64
import json

KODI_TMDB_CONFIG = sys.argv[1]

kodi_tmdb_config_str = base64.b64decode(
    KODI_TMDB_CONFIG).decode(encoding='utf-8')
kodi_tmdb_config: dict = json.loads(kodi_tmdb_config_str)


try:
    with open(f'config.json', 'w+', encoding='utf-8') as kodi_tmdb_config_file:
        json.dump(kodi_tmdb_config, kodi_tmdb_config_file)
except:
    pass
