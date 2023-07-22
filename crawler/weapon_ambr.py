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
promote_prop_init = {'critical_hurt': 0.5, 'critical': 0.05}
ua = UserAgent()  # required for non-browser http request, or you will get a response code of 403
result = {}

f = open(base_dir + '/lib/weapon_base_data.json', 'r', encoding='utf-8')
base_data = json.load(f)
f.close()


def append_name(data_dict):
    for lang in languages:
        result[name_lang_mapping[lang]] = data_dict[lang]['name']
        print('append %s name: %s' % (lang, result[name_lang_mapping[lang]]))


def append_desc(data_dict):
    for lang in languages:
        result[desc_lang_mapping[lang]] = data_dict[lang]['description']
        print('append %s desc: %s' % (lang, result[desc_lang_mapping[lang]]))


def append_image(data_dict, weapon_id):
    icon = data_dict['en']['icon']
    img_ext = 'png'
    path = 'images/weapon/%s' % weapon_id
    util.download_amber_image(path, icon, img_ext, base_dir)
    result['imageurl'] = '%s.%s' % (path, img_ext)
    print('append image: %s' % path)


def append_basic(data_dict):
    data_en = data_dict['en']
    result['type'] = data_en['type'].lower()
    result['rarity'] = data_en['rank']
    print('type: %s, rarity: %s' % (result['type'], result['rarity']))


def append_level(data_dict):
    upgrade = data_dict['en']['upgrade']
    promote = upgrade['promote']
    promote_dict = {}
    for p in promote:
        promote_dict[p['unlockMaxLevel']] = p
    props = util.get_props(upgrade['prop'])
    leveldata = []
    d = {'level': '1'}
    for name, value in props.items():
        d[name] = value['init']
    leveldata.append(d)
    for i in range(5, 91, 5):
        level = str(i)
        add_props = {}
        if i in promote_dict and i > 20:
            add_props = util.get_props(promote_dict[i]['addProps'])
        d = {'level': level}
        for name, value in props.items():
            d[name] = value['init'] * base_data[level]['curveInfos'][value['curve']] + (
                add_props[name] if name in add_props else 0)
        leveldata.append(d)
    result['leveldata'] = leveldata
    print('append leveldata, count: %s' % len(leveldata))


def append_refinement(data_dict):
    refinement = {}
    for lang in languages:
        if 'affix' in data_dict[lang] and data_dict[lang]['affix'] is not None:
            for k, v in data_dict[lang]['affix'].items():
                upgrade = {}
                for uk, uv in v['upgrade'].items():
                    upgrade[uk] = util.clean_desc_ambr(uv)
                r = {
                    'id': k,
                    'name': v['name'],
                    'upgrade': upgrade
                }
                refinement[lang] = r
                break
            print('append %s refinement: %s' % (lang, refinement[lang]['upgrade']['0']))
    result['refinement'] = refinement


# main function
def generate_json(weapon_id):
    util.prepare_dirs('ambr', base_dir)
    result['id'] = weapon_id
    with open(base_dir + '/lib/weaponlist.json', 'r', encoding='utf-8') as f:
        weapon_info = json.load(f)
        weapon = list(filter(lambda i: i['id'] == weapon_id, weapon_info['data']))[0]['ENname']
    print('generate lib json from ambr for: %s %s' % (weapon_id, weapon))
    data_dict = {}
    for lang in languages:
        url = 'https://api.ambr.top/v2/%s/weapon/%s' % (lang, weapon_id)
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
    append_level(data_dict)
    append_refinement(data_dict)
    with open(base_dir + '/lib/weapon/' + result['id'] + '.json', 'w', encoding='utf-8') as f:
        f.write(json.dumps(result, ensure_ascii=False, skipkeys=True, indent=4))


if __name__ == '__main__':
    generate_json(sys.argv[1])
