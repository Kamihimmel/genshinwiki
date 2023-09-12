# coding: utf-8

import json
import os
import re
import requests
import sys

import util

from fake_useragent import UserAgent

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # absolute path of repo dir
languages = ['en', 'chs', 'jp']
name_lang_mapping = {'en': 'ENname', 'chs': 'CNname', 'jp': 'JAname'}
desc_lang_mapping = {'en': 'DescriptionEN', 'chs': 'DescriptionCN', 'jp': 'DescriptionJP'}
ua = UserAgent()  # required for non-browser http request, or you will get a response code of 403
result = {}


def append_name(data_dict):
    for lang in languages:
        result[name_lang_mapping[lang]] = data_dict[lang]['name']
        print('append %s name: %s' % (lang, result[name_lang_mapping[lang]]))


def append_desc(data_dict):
    for lang in languages:
        result[desc_lang_mapping[lang]] = data_dict[lang]['description']
        print('append %s desc: %s' % (lang, result[desc_lang_mapping[lang]]))


def append_image(data_dict, artifact_id):
    icon = data_dict['en']['icon']
    img_ext = 'png'
    path = 'images/artifact/%s' % artifact_id
    util.download_amber_image('crawler/ambr/' + path, 'reliquary/' + icon, img_ext, base_dir)
    result['imageurl'] = '%s.%s' % (path, img_ext)
    print('append image: %s' % path)


def append_basic(data_dict):
    data_en = data_dict['en']
    result['level'] = data_en['levelList']
    print('level: %s' % result['level'])


def append_skill(data_dict):
    skill = {}
    keys = list(data_dict['en']['affixList'].keys())
    suit_effect = {}
    if data_dict['en']['name'].startswith('Prayers for ') and len(keys) == 1:
        suit_effect['1'] = keys[0]
    else:
        suit_effect['2'] = keys[0]
    if len(keys) > 1:
        suit_effect['4'] = keys[1]
    for k, v in suit_effect.items():
        skill[k] = {}
        for lang in languages:
            skill[k][desc_lang_mapping[lang]] = data_dict[lang]['affixList'][v]
    result['skill'] = skill
    print('append skill, count: %s' % len(skill))


def append_suit(artifact_id, data_dict):
    suit = {}
    suit_dict = {}
    for lang in languages:
        for k, v in data_dict[lang]['suit'].items():
            suit_dict[lang] = v
    for k in data_dict['en']['suit'].keys():
        suit_name = k.replace('EQUIP_', '').lower()
        suit[suit_name] = {}
        for lang in languages:
            suit[suit_name][name_lang_mapping[lang]] = data_dict[lang]['suit'][k]['name']
        for lang in languages:
            suit[suit_name][desc_lang_mapping[lang]] = data_dict[lang]['suit'][k]['description']
        icon = data_dict['en']['suit'][k]['icon']
        img_ext = 'png'
        path = 'images/artifact/%s-%s' % (artifact_id, suit_name)
        util.download_amber_image('crawler/ambr/' + path, 'reliquary/' + icon, img_ext, base_dir)
        suit[suit_name]['imageurl'] = '%s.%s' % (path, img_ext)
        print('append suit image: %s' % path)
        suit[suit_name]['maxLevel'] = data_dict['en']['suit'][k]['maxLevel']
    print('append suit: %s' % len(suit))
    result['suit'] = suit


# main function
def generate_json(artifact_id):
    util.prepare_dirs('ambr', base_dir)
    result['id'] = artifact_id
    with open(base_dir + '/lib/artifactlist.json', 'r', encoding='utf-8', newline='\n') as f:
        artifact_info = json.load(f)
        artifact = list(filter(lambda i: i['id'] == artifact_id, artifact_info['data']))[0]['ENname']
    print('generate lib json from ambr for: %s %s' % (artifact_id, artifact))
    data_dict = {}
    for lang in languages:
        url = 'https://api.ambr.top/v2/%s/reliquary/%s' % (lang, artifact_id)
        res = requests.get(url, headers={'User-Agent': ua.edge}, timeout=30)
        if res is None or res.content is None:
            print('fetch failed, please try again')
            exit(1)
        data = json.loads(res.content)
        if data is None or 'response' not in data or data['response'] != 200:
            print('fetch error, please try again')
            exit(1)
        data_dict[lang] = data['data']
    append_name(data_dict)
    append_image(data_dict, result['id'])
    append_basic(data_dict)
    append_skill(data_dict)
    append_suit(artifact_id, data_dict)
    with open(base_dir + '/crawler/ambr/lib/artifact/' + result['id'] + '.json', 'w', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(result, ensure_ascii=False, skipkeys=True, indent=4))


if __name__ == '__main__':
    generate_json(sys.argv[1])
