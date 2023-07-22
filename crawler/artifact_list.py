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

data_dict = {}
for lang in languages:
    url = 'https://api.ambr.top/v2/%s/reliquary' % lang
    res = requests.get(url, headers={'User-Agent': ua.random}, timeout=10)
    print('response: %s' % res.content)
    data = json.loads(res.content)
    if data is None or data['response'] != 200:
        print('fetch failed, please try again')
        sys.exit(1)
    data_dict[lang] = data['data']['items']

artifacts = []
for k in data_dict['en']:
    result = {}
    data_en = data_dict['en'][k]
    data_chs = data_dict['chs'][k]
    data_jp = data_dict['jp'][k]
    result['id'] = k
    result['ENname'] = data_en['name']
    result['CNname'] = data_chs['name']
    result['JAname'] = data_jp['name']
    img_ext = 'png'
    path = 'images/artifact/%s' % k
    path = util.download_amber_image(path, 'reliquary/' + data_en['icon'], img_ext, base_dir)
    result['imageurl'] = path
    result['spoiler'] = data_en['beta'] if 'beta' in data_en else False
    result['order'] = data_en['sortOrder']
    print("fetch data for: %s" % result['ENname'])
    artifacts.append(result)

with open(base_dir + '/lib/artifactlist.json', 'w', encoding='utf-8') as f:
    f.write(json.dumps({'data': artifacts}, ensure_ascii=False, skipkeys=True, indent=4))