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
    url = 'https://api.ambr.top/v2/%s/reliquary' % lang
    res = requests.get(url, headers={'User-Agent': ua.random}, timeout=10)
    print('response: %s' % res.content)
    data = json.loads(res.content)
    if data is None or data['response'] != 200:
        print('fetch failed, please try again')
        sys.exit(1)
    data_dict[lang] = data['data']['items']

with open(base_dir + '/lib/artifactlist.json', 'r', encoding='utf-8', newline='\n') as f:
    exist_list = json.load(f)['data']

artifacts = []
exist_ids = []
for a in exist_list:
    if 'spoiler' in a and not a['spoiler']:
        artifacts.append(a)
        exist_ids.append(a['id'])

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
    path = 'images/artifact/%s' % k
    util.download_amber_image('crawler/ambr/' + path, 'reliquary/' + data_en['icon'], img_ext, base_dir)
    result['imageurl'] = '%s.%s' % (path, img_ext)
    find = list(filter(lambda at: at['id'] == k, exist_list))
    result['spoiler'] = find[0]['spoiler'] if len(find) > 0 else util.is_beta(data_en)
    result['order'] = data_en['sortOrder']
    print("fetch data for: %s" % result['ENname'])
    artifacts.append(result)

with open(base_dir + '/crawler/ambr/lib/artifactlist.json', 'w', encoding='utf-8', newline='\n') as f:
    f.write(json.dumps({'data': artifacts}, ensure_ascii=False, skipkeys=True, indent=4))
