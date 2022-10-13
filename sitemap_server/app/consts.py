#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path

SERVICE_NAME = "sitemap_server"
VERSION = 'v1'

ROOT_DIR = Path(__name__).parent.parent.absolute()

ENV_FILE = ROOT_DIR / ".env"
LOGS_DIR = ROOT_DIR / 'logs'
FONTS_DIR = ROOT_DIR / 'fonts'

d_site = {
    '1': 'Epool',
    '2': 'RUpool',
    'f': 'AquaMarket',
    'i': 'Azuro',
    'c': 'eBolgarka',
    '4': 'eFontan',
    '6': 'eGazon',
    '8': 'eKamin',
    'j': 'eLustra',
    'b': 'eMozaika',
    '5': 'eNasos',
    '9': 'eParilka',
    'k': 'eSkazka',
    'l': 'eStairs',
    'e': 'eVanna',
    'a': 'eVoda',
    '3': 'eVozduh',
    '7': 'LubluTeplo',
    'd': 'Pavilions',
    'h': 'Poolmagic',
    'g': 'Super-Spa',
}

list_subdomain = [
    'www',
    'spb',
    'vgd',
    'voronezh',
    'ekb',
    'kazan',
    'knr',
    'nn',
    'rostov',
    'samara',
    'saratov',
    'belgorod',
    'kaluga',
    'yaroslavl',
    'lipeck',
    'stavropol',
    'tula',
    'nrsk',
    'ryazan',
    'sochi',
    'tambov',
    'perm',
    'bryansk',
    'izhevsk',
    'ufa',
    'chel',
    'm'
]

