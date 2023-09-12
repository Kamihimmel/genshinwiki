# coding: utf-8

import json
import os
import requests
import sys

import util

from fake_useragent import UserAgent

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # absolute path of repo dir
languages = ['en', 'chs', 'jp']
name_lang_mapping = {'en': 'ENname', 'chs': 'CNname', 'jp': 'JAname'}
ua = UserAgent()  # required for non-browser http request, or you will get a response code of 403
util.prepare_dirs('ambr', base_dir)

data_dict = {}
for lang in languages:
    url = 'https://api.ambr.top/v2/%s/avatar' % lang
    res = requests.get(url, headers={'User-Agent': ua.random}, timeout=10)
    print('response: %s' % res.content)
    data = json.loads(res.content)
    if data is None or data['response'] != 200:
        print('fetch failed, please try again')
        sys.exit(1)
    data_dict[lang] = data['data']['items']

with open(base_dir + '/lib/characterlist.json', 'r', encoding='utf-8', newline='\n') as f:
    exist_list = json.load(f)['data']

characters = []
exist_ids = []
for c in exist_list:
    if 'spoiler' in c and not c['spoiler']:
        characters.append(c)
        exist_ids.append(c['id'])

for k in data_dict['en']:
    if k in exist_ids:
        continue
    result = {}
    data_en = data_dict['en'][k]
    data_chs = data_dict['chs'][k]
    data_jp = data_dict['jp'][k]
    result['id'] = k
    result['ENname'] = data_en['name']
    result['CNname'] = data_chs['name']
    result['JAname'] = data_jp['name']
    img_ext = 'png'
    path = 'images/character/%s' % k
    icon = data_en['icon']
    util.download_amber_image('crawler/ambr/' + path, icon, img_ext, base_dir)
    result['imageurl'] = '%s.%s' % (path, img_ext)
    img_ext = 'png'
    path = 'images/character/%s-large' % k
    large_icon = icon.replace('UI_AvatarIcon_', 'UI_Gacha_AvatarImg_')
    util.download_amber_image('crawler/ambr/' + path, large_icon, img_ext, base_dir)
    result['imagelargeurl'] = '%s.%s' % (path, img_ext)
    result['rarity'] = data_en['rank']
    result['element'] = data_en['element'].lower()
    result['weapon'] = data_en['weaponType'].split('_')[1].lower()
    find = list(filter(lambda ch: ch['id'] == k, exist_list))
    result['spoiler'] = find[0]['spoiler'] if len(find) > 0 else util.is_beta(data_en)
    result['supported'] = find[0]['supported'] if len(find) > 0 else False
    result['order'] = find[0]['order'] if len(find) > 0 else 999
    print("fetch data for: %s" % result['ENname'])
    characters.append(result)

with open(base_dir + '/crawler/ambr/lib/characterlist.json', 'w', encoding='utf-8', newline='\n') as f:
    f.write(json.dumps({'data': characters}, ensure_ascii=False, skipkeys=True, indent=4))
