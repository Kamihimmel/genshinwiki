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

f = open(base_dir + '/lib/base_data.json', 'r', encoding='utf-8')
base_data = json.load(f)
f.close()


def append_name(data_dict):
    for lang in languages:
        result[name_lang_mapping[lang]] = data_dict[lang]['name']
        print('append %s name: %s' % (lang, result[name_lang_mapping[lang]]))


def append_image(data_dict, character_id, size):
    icon = data_dict['en']['icon']
    large_icon = icon.replace('UI_AvatarIcon_', 'UI_Gacha_AvatarImg_')
    img_ext = 'png'
    path = 'images/character/%s%s' % (character_id, '-large' if size == 'large' else '')
    util.download_amber_image(path, large_icon if size == 'large' else icon, img_ext, base_dir)
    result['imagelargeurl' if size == 'large' else 'imageurl'] = '%s.%s' % (path, img_ext)
    print('append image: %s' % path)


def append_basic(data_dict):
    data_en = data_dict['en']
    result['element'] = data_en['element'].lower()
    result['weapon'] = data_en['weaponType'].split('_')[1].lower()
    result['rarity'] = data_en['rank']
    result['birthday'] = data_en['birthday']
    result['release'] = data_en['release']
    print('append element: %s, weapon: %s, rarity: %s, birthday:%s, release: %s' % (
        result['element'], result['weapon'], result['rarity'], result['birthday'], result['release']))


def append_level(data_dict):
    levelup_curve = base_data['levelup_curve_s5'] if data_dict['en']['rank'] == 5 else base_data['levelup_curve_s4']
    promote_count = base_data['promote_count']
    promote_curve = base_data['promote_curve_s5'] if data_dict['en']['rank'] == 5 else base_data['promote_curve_s4']
    upgrade = data_dict['en']['upgrade']
    promote = upgrade['promote']
    prop = upgrade['prop']
    base_props = {}
    for p in prop:
        base_props[p['propType'].replace('FIGHT_PROP_', '').lower()] = p['initValue']
    promote_prop = ''
    last_promote = promote[len(promote) - 1]
    for k in last_promote['addProps'].keys():
        p = k.replace('FIGHT_PROP_', '').lower()
        if p not in base_props:
            promote_prop = p
            break
    if promote_prop.endswith('_add_hurt') and promote != 'physical_add_hurt':
        promote_prop = 'element_add_hurt'

    leveldata = []
    for i in range(0, len(promote)):
        lvl = promote[i]
        max_level = lvl['unlockMaxLevel']
        if i == 0:
            d = {'level': '1'}
            for k, v in base_props.items():
                d[k] = v
            d[promote_prop] = promote_prop_init[promote_prop] if promote_prop in promote_prop_init else 0
            leveldata.append(d)
        max_levels = [str(max_level)]
        if i < len(promote) - 1:
            max_levels.append(str(max_level) + '+')
        for max_level_str in max_levels:
            d = {'level': max_level_str}
            for k, v in base_props.items():
                d[k] = v * levelup_curve[max_level_str]
            d[promote_prop] = promote_count[max_level_str] * promote_curve[promote_prop] + (
                promote_prop_init[promote_prop] if promote_prop in promote_prop_init else 0)
            leveldata.append(d)
    result['leveldata'] = leveldata
    print('append leveldata, count: %s' % len(leveldata))


'''
talent start
'''


def append_talent_name(cur_talent, talent_dict, key):
    for lang in languages:
        cur_talent[name_lang_mapping[lang]] = talent_dict[lang][key]['name']
        print('append talent %s name: %s' % (lang, cur_talent[name_lang_mapping[lang]]))


def append_talent_image(character_id, cur_talent, talent_dict, key):
    img_ext = 'png'
    path = 'images/talent/%s-%s' % (character_id, cur_talent['id'])
    util.download_amber_image(path, talent_dict['en'][key]['icon'], img_ext, base_dir)
    cur_talent['imageurl'] = '%s.%s' % (path, img_ext)
    print('append talent image: %s' % path)


def append_talent_desc(cur_talent, talent_dict, key):
    for lang in languages:
        desc = util.clean_desc_ambr(talent_dict[lang][key]['description'])
        cur_talent[desc_lang_mapping[lang]] = desc
        print('append talent %s desc: %s' % (lang, cur_talent[desc_lang_mapping[lang]]))


def append_talent_attr(cur_talent, talent_dict, key):
    talent_en = talent_dict['en'][key]
    cur_talent['cooldown'] = talent_en['cooldown'] if 'cooldown' in talent_en else 0
    cur_talent['cost'] = talent_en['cost'] if 'cost' in talent_en else 0
    cur_talent['type'] = 'passive' if talent_en['type'] == 2 else 'combat'
    if cur_talent['type'] == 'combat':
        if talent_en['icon'].startswith('Skill_A_'):
            cur_talent['ttype'] = 'A'
        elif talent_en['icon'].startswith('Skill_S_') and talent_en['icon'] != 'Skill_S_Ayaka_02':
            cur_talent['ttype'] = 'E'
        elif talent_en['type'] == 1:
            cur_talent['ttype'] = 'Q'
    if 'ttype' not in cur_talent:
        cur_talent['ttype'] = ''
    print('append talent cooldown: %s, cost: %s, type: %s, ttype: %s' % (
        cur_talent['cooldown'], cur_talent['cost'], cur_talent['type'], cur_talent['ttype']))


def append_talent_levelmultiplier(cur_talent, talent_dict, key):
    talent_en = talent_dict['en'][key]
    promote = talent_en['promote'] if 'promote' in talent_en else {}
    cur_talent['maxlevel'] = len(promote)
    print('append talent maxlevel: %s' % cur_talent['maxlevel'])
    levelmultiplier = []
    for lv, p in promote.items():
        d = {'level': p['level']}
        for lang in languages:
            d[desc_lang_mapping[lang]] = talent_dict[lang][key]['promote'][lv]['description']
        d['params'] = p['params']
        levelmultiplier.append(d)
    cur_talent['levelmultiplier'] = levelmultiplier
    print('append talent levelmultiplier, count: %s' % len(levelmultiplier))


def append_talent(character_id, data_dict):
    talentdata = []
    talent_dict = {}
    for lang in languages:
        talent_dict[lang] = data_dict[lang]['talent']
    for k in talent_dict['en'].keys():
        cur_talent = {'id': k}
        append_talent_name(cur_talent, talent_dict, k)
        append_talent_image(character_id, cur_talent, talent_dict, k)
        append_talent_desc(cur_talent, talent_dict, k)
        append_talent_attr(cur_talent, talent_dict, k)
        append_talent_levelmultiplier(cur_talent, talent_dict, k)
        talentdata.append(cur_talent)
    result['talentdata'] = talentdata
    print('append talentdata, count: %s' % len(talentdata))


'''
talent end
'''

'''
eidolon start
'''


def append_constellation_name(cur_constellation, constellation_dict, key):
    for lang in languages:
        cur_constellation[name_lang_mapping[lang]] = constellation_dict[lang][key]['name']
        print('append constellation %s name: %s' % (lang, cur_constellation[name_lang_mapping[lang]]))


def append_constellation_image(character_id, cur_constellation, constellation_dict, key):
    img_ext = 'png'
    path = 'images/constellation/%s-c%s' % (character_id, cur_constellation['level'])
    util.download_amber_image(path, constellation_dict['en'][key]['icon'], img_ext, base_dir)
    cur_constellation['imageurl'] = '%s.%s' % (path, img_ext)
    print('append constellation image: %s' % path)


def append_constellation_desc(cur_constellation, constellation_dict, key):
    for lang in languages:
        desc = util.clean_desc_ambr(constellation_dict[lang][key]['description'])
        cur_constellation[desc_lang_mapping[lang]] = desc
        print('append desc %s name: %s' % (lang, cur_constellation[desc_lang_mapping[lang]]))


def append_constellation(character_id, data_dict):
    constellation = []
    constellation_dict = {}
    for lang in languages:
        constellation_dict[lang] = data_dict[lang]['constellation']
    for k in constellation_dict['en'].keys():
        cur_constellation = {'level': int(k) + 1}
        append_constellation_name(cur_constellation, constellation_dict, k)
        append_constellation_image(character_id, cur_constellation, constellation_dict, k)
        append_constellation_desc(cur_constellation, constellation_dict, k)
        constellation.append(cur_constellation)
    result['constellation'] = constellation
    print('append constellation, count: %s' % len(constellation))


'''
eidolon end
'''


# main function
def generate_json(character_id):
    util.prepare_dirs('ambr', base_dir)
    result['id'] = character_id
    with open(base_dir + '/lib/characterlist.json', 'r', encoding='utf-8') as f:
        character_info = json.load(f)
        character = list(filter(lambda i: i['id'] == character_id, character_info['data']))[0]['ENname']
    print('generate lib json from ambr for: %s %s' % (character_id, character))
    c = character.lower().replace('-', '')
    data_dict = {}
    for lang in languages:
        url = 'https://api.ambr.top/v2/%s/avatar/%s' % (lang, character_id)
        res = requests.get(url, headers={'User-Agent': ua.random}, timeout=10)
        if res is None or res.content is None:
            print('fetch failed, please try again')
            exit(1)
        data = json.loads(res.content)
        if data is None or 'response' not in data or data['response'] != 200:
            print('fetch error, please try again')
            exit(1)
        data_dict[lang] = data['data']
    append_name(data_dict)
    append_image(data_dict, result['id'], 'medium')
    append_image(data_dict, result['id'], 'large')
    append_basic(data_dict)
    append_level(data_dict)
    append_talent(character_id, data_dict)
    append_constellation(character_id, data_dict)
    with open(base_dir + '/lib/character/' + result['id'] + '.json', 'w', encoding='utf-8') as f:
        f.write(json.dumps(result, ensure_ascii=False, skipkeys=True, indent=4))


if __name__ == '__main__':
    generate_json(sys.argv[1])
