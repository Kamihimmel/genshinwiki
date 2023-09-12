# coding: utf-8

import filetype
import os
import re
import requests
import time

from fake_useragent import UserAgent

amber_icon_url = 'https://api.ambr.top/assets/UI/%s/%s.%s'
dirs = ['', '/lib', '/lib/character', '/lib/weapon', '/lib/artifact', '/images', '/images/character', '/images/talent',
        '/images/constellation', '/images/weapon', '/images/artifact']
ua = UserAgent()


def is_beta(data_dict):
    beta = data_dict['beta'] if 'beta' in data_dict else False
    if not beta and 'release' in data_dict:
        release = data_dict['release']
        beta = release > int(time.time())
    return beta


def is_buff_skill(desc):
    lower_desc = desc.lower()
    return 'extended' in lower_desc \
        or 'extend' in lower_desc \
        or 'increases' in lower_desc \
        or 'increase' in lower_desc \
        or 'gain' in lower_desc \
        or re.match(r'.*\+\d+(\.\d+)?%.*', desc) is not None


def is_team_skill(desc):
    lower_desc = desc.lower()
    return 'all enemies' in lower_desc


def clean_name(name):
    return re.sub(r'\?|!|,|\'|\"', '', name.replace(' ', '-').lower())


def download_amber_image(path, icon, img_type, base_dir):
    path = '%s.%s' % (path, img_type)
    skip = os.getenv('SKIP_IMAGE')
    if not skip or skip != '1':
        with open(base_dir + '/' + path, 'wb') as f:
            url = 'https://api.ambr.top/assets/UI/%s.%s' % (icon, img_type)
            res = requests.get(url, headers={'User-Agent': ua.edge}, timeout=30)
            if res is not None:
                content = res.content
                if content is not None and len(content) > 0 and is_image(content) is not None:
                    f.write(res.content)
    return path


def is_image(obj):
    try:
        buf = filetype.get_bytes(obj)
        if len(buf) == 0:
            return None
        return filetype.image_match(buf)
    except Exception:
        return None


def format_percent_number(num):
    num = float(round(num * 100, 2))
    if num == int(num):
        num = int(num)
    return num


def clean_desc_ambr(desc):
    desc = desc.replace('\\n', ' ')
    return re.sub(r'</?\w+[^>]*?>', '', desc)


def prepare_dirs(source, base_dir):
    for d in dirs:
        path = '%s/crawler/%s%s' % (base_dir, source, d)
        if not os.path.exists(path):
            os.mkdir(path)


def get_props(prop):
    props = {}
    if isinstance(prop, list):
        for p in prop:
            if 'propType' in p:
                name = p['propType'].replace('FIGHT_PROP_', '').lower()
                props[name] = {
                    'init': p['initValue'],
                    'curve': p['type'],
                }
    elif isinstance(prop, dict):
        for k, v in prop.items():
            name = k.replace('FIGHT_PROP_', '').lower()
            props[name] = v
    return props
