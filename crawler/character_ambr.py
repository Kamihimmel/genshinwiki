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
desc_lang_mapping = {'en': 'DescriptionEN', 'chs': 'DescriptionCN', 'jp': 'DescriptionJP'}
promote_prop_init = {'critical_hurt': 0.5, 'critical': 0.05, 'charge_efficiency': 1}
ua = UserAgent()  # required for non-browser http request, or you will get a response code of 403
result = {}

f = open(base_dir + '/lib/character_base_data.json', 'r', encoding='utf-8')
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
    upgrade = data_dict['en']['upgrade']
    promote = upgrade['promote']
    promote_dict = {}
    for p in promote:
        promote_dict[p['unlockMaxLevel']] = p
    props = util.get_props(upgrade['prop'])
    add_prop_key = util.get_props(promote_dict[40]['addProps']).keys()
    leveldata = []
    d = {'level': '1'}
    for name, value in props.items():
        d[name] = value['init']
    for k in add_prop_key:
        if k not in props:
            d[k] = promote_prop_init[k] if k in promote_prop_init else 0
    leveldata.append(d)
    for i in range(10, 91, 10):
        level = str(i)
        add_props = {}
        if i in promote_dict and i > 20:
            add_props = util.get_props(promote_dict[i]['addProps'])
        d = {'level': level}
        for name, value in props.items():
            d[name] = value['init'] * base_data[level]['curveInfos'][value['curve']]
        for k in add_prop_key:
            if k in props:
                d[k] += add_props[k] if k in add_props else 0
            else:
                d[k] = (add_props[k] if k in add_props else 0) + (promote_prop_init[k] if k in promote_prop_init else 0)
        leveldata.append(d)
        if i in promote_dict and 20 <= i < 90:
            next_promote = {}
            for j in range(i + 10, 91, 10):
                if j in promote_dict:
                    next_promote = promote_dict[j]
                    break
            next_add_props = util.get_props(next_promote['addProps'])
            d = {'level': level + '+'}
            for k, v in leveldata[len(leveldata) - 1].items():
                if k != 'level':
                    d[k] = v + (next_add_props[k] - (add_props[k] if k in add_props else 0))
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
    data_dict = {}
    for lang in languages:
        url = 'https://api.ambr.top/v2/%s/avatar/%s' % (lang, character_id)
        res = requests.get(url, headers={'User-Agent': ua.edge}, timeout=10)
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
