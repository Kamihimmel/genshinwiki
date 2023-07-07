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
promote_prop_init = {'critical_hurt': 0.5}
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
    util.download_amber_avatar(path, large_icon if size == 'large' else icon, img_ext, base_dir)
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
skill start
'''


def append_skill_name(cur_skill, skill_dict, index):
    for lang in languages:
        cur_skill[name_lang_mapping[lang]] = skill_dict[lang][index]['name']
        print('append skill %s name: %s' % (lang, cur_skill[name_lang_mapping[lang]]))


def append_skill_image(character, cur_skill, skill_dict, index):
    img_ext = 'png'
    path = 'images/skills/%s-%s' % (character, cur_skill['id'])
    util.download_yatta_image('crawler/yatta/' + path, 'skill', skill_dict['EN'][index]['icon'], img_ext, base_dir)
    cur_skill['imageurl'] = '%s.%s' % (path, img_ext)
    print('append skill image: %s' % path)


def append_skill_desc(cur_skill, skill_dict, index):
    for lang in languages:
        desc = cur_skill['Description' + lang] = util.clean_desc_yatta(skill_dict[lang][index]['description'])
        if skill_dict[lang][index]['maxLevel'] <= 1:
            for k, v in skill_dict[lang][index]['params'].items():
                desc = desc.replace('[%s]' % k, str(util.format_percent_number(v[0]) if '[%s]%%' % k in desc else v[0]))
        cur_skill['Description' + lang] = desc
        print('append skill %s desc: %s' % (lang, cur_skill['Description' + lang]))


def append_skill_attr(cur_skill, skill_dict, index):
    skill_en = skill_dict['EN'][index]
    stype = skill_en['type'].replace(' ', '').lower()
    maxlevel = skill_en['maxLevel']
    if maxlevel <= 1:
        maxlevel = 0
    buffskill = util.is_buff_skill(cur_skill['DescriptionEN'])
    teamskill = util.is_team_skill(cur_skill['DescriptionEN'])
    weaknessbreak = skill_en['weaknessBreak']['one'] if skill_en['weaknessBreak'] is not None \
                                                        and 'one' in skill_en['weaknessBreak'] and \
                                                        skill_en['weaknessBreak']['one'] is not None else 0
    energyregen = skill_en['skillPoints']['base'] if skill_en['skillPoints'] is not None \
                                                     and 'base' in skill_en['skillPoints'] and skill_en['skillPoints'][
                                                         'base'] is not None else 0
    cur_skill['maxlevel'] = maxlevel
    cur_skill['buffskill'] = buffskill
    cur_skill['teamskill'] = teamskill
    cur_skill['weaknessbreak'] = weaknessbreak
    cur_skill['energyregen'] = energyregen
    print('append skill stype: %s, maxlevel: %s, buffskill: %s, teamskill: %s, weaknessbreak: %s, energyregen: %s' % (
        stype, maxlevel, buffskill, teamskill, weaknessbreak, energyregen))


def append_skill_levelmultiplier(cur_skill, skill_dict, index):
    if cur_skill['maxlevel'] == 0:
        return
    skill_en = skill_dict['EN'][index]
    desc = cur_skill['DescriptionEN']
    params = skill_en['params']
    levelmultiplier = []
    for i, multi in params.items():
        percent = ('[%s]%%' % i) in desc
        d = {}
        for j in range(0, len(multi)):
            d[str(j + 1)] = util.format_percent_number(multi[j]) if percent else multi[j]
        levelmultiplier.append(d)
    cur_skill['levelmultiplier'] = levelmultiplier
    print('append skill levelmultiplier, count: %s' % len(levelmultiplier))


def append_skill_tags(cur_skill, skill_dict, index, exist_skill):
    cur_skill['tags'] = exist_skill['tags'] if 'tags' in exist_skill else []


def append_skill_effect(cur_skill, skill_dict, index, exist_skill):
    cur_skill['effect'] = exist_skill['effect'] if 'effect' in exist_skill else []


def compare_skill(s, d):
    if 'id' in s and 'id' in d:
        return s['id'] == d['id']
    return s['ENname'] == d['ENname']


def append_skill(character, data_dict, exist_dict):
    skilldata = []
    skill_dict = {}
    for lang in languages:
        main_skills = data_dict[lang]['traces']['mainSkills']
        skills = []
        for ms in main_skills.values():
            for k, v in ms['skillList'].items():
                v['id'] = k
                skills.append(v)
        skill_dict[lang] = skills
    exist_skills = exist_dict['skilldata']
    for i in range(0, len(skill_dict['EN'])):
        cur_skill = {'id': skill_dict['EN'][i]['id']}
        append_skill_name(cur_skill, skill_dict, i)
        append_skill_image(character, cur_skill, skill_dict, i)
        append_skill_desc(cur_skill, skill_dict, i)
        append_skill_attr(cur_skill, skill_dict, i)
        append_skill_levelmultiplier(cur_skill, skill_dict, i)
        find = list(filter(lambda s: compare_skill(s, cur_skill), exist_skills))
        exist_skill = find[0] if len(find) > 0 else {}
        append_skill_tags(cur_skill, skill_dict, i, exist_skill)
        append_skill_effect(cur_skill, skill_dict, i, exist_skill)
        skilldata.append(cur_skill)
    result['skilldata'] = skilldata
    print('append skilldata, count: %s' % len(skilldata))


'''
skill end
'''

'''
trace start
'''


def append_trace_name_and_desc(cur_trace, trace_dict, index):
    trace_desc = {}
    for lang in languages:
        trace = trace_dict[lang][index]
        if cur_trace['tiny']:
            name = util.clean_desc_yatta(trace['statusList'][0]['name'])
            multiplier = trace['statusList'][0]['value']
            name = name.replace('[1]', str(util.format_percent_number(multiplier) if '[1]%' in name else multiplier))
            desc = ''
            if 'avatarLevelLimit' in trace and trace['avatarLevelLimit'] is not None:
                desc = 'LV%s' % trace['avatarLevelLimit']
            elif 'avatarPromotionLimit' in trace and trace['avatarPromotionLimit'] is not None:
                desc = 'A%s' % trace['avatarPromotionLimit']
        else:
            name = trace['name']
            desc = util.clean_desc_yatta(trace['description'])
            if 'params' in trace and trace['params'] is not None:
                for k, v in trace['params'].items():
                    desc = desc.replace('[%s]' % k,
                                        str(util.format_percent_number(v[0]) if '[%s]%%' % k in desc else v[0]))
        cur_trace[name_lang_mapping[lang]] = name
        print('append trace %s name: %s' % (lang, name))
        trace_desc['Description' + lang] = desc
    for k, v in trace_desc.items():
        cur_trace[k] = v
        print('append trace %s desc: %s' % (k, v))


def append_trace_attr(character, cur_trace, trace_dict, index):
    if cur_trace['tiny']:
        ttype = re.match(r'^(.*?)\s+(increases|decreases).*', cur_trace['ENname']).group(1).lower().replace(' ', '')
        print('append trace ttype: %s' % cur_trace['ttype'])
    else:
        img_ext = 'png'
        path = 'images/skills/%s-%s' % (character, cur_trace['id'])
        util.download_yatta_image('crawler/yatta/' + path, 'skill', trace_dict['EN'][index]['icon'], img_ext, base_dir)
        cur_trace['imageurl'] = '%s.%s' % (path, img_ext)
        print('append trace image: %s' % path)
    cur_trace['stype'] = 'trace'
    cur_trace['buffskill'] = util.is_buff_skill(cur_trace['ENname'])
    cur_trace['teamskill'] = util.is_team_skill(cur_trace['ENname'])
    print('append skill stype: %s, buffskill: %s, teamskill: %s' % (
        cur_trace['stype'], cur_trace['buffskill'], cur_trace['teamskill']))


def append_trace_tags(cur_trace, exist_trace):
    cur_trace['tags'] = exist_trace['tags'] if 'tags' in exist_trace else []


def append_trace_effect(cur_trace, exist_trace):
    cur_trace['effect'] = exist_trace['effect'] if 'effect' in exist_trace else []


def compare_trace(s, d):
    if 'id' in s and 'id' in d:
        return s['id'] == d['id']
    if s['ENname'] == d['ENname']:
        return True
    if 'ttype' in s and 'ttype' in d and s['ttype']:
        return s['ttype'] == d['ttype'] and s['DescriptionEN'] == d['DescriptionEN']
    return False


def append_trace(character, data_dict, exist_dict):
    tracedata = []
    trace_dict = {}
    for lang in languages:
        sub_skills = data_dict[lang]['traces']['subSkills']
        skills = []
        for ss in sub_skills.values():
            skills.append(ss)
        trace_dict[lang] = skills
    exist_traces = exist_dict['tracedata']
    trace_cnt = len(list(trace_dict['EN']))
    for i in range(0, trace_cnt):
        cur_trace = {'id': str(trace_dict['EN'][i]['id']), 'tiny': not trace_dict['EN'][i]['pointType'] == 'Special'}
        append_trace_name_and_desc(cur_trace, trace_dict, i)
        append_trace_attr(character, cur_trace, trace_dict, i)
        find = list(filter(lambda s: compare_trace(s, cur_trace), exist_traces))
        exist_trace = find[0] if len(find) > 0 else {}
        append_trace_tags(cur_trace, exist_trace)
        append_trace_effect(cur_trace, exist_trace)
        tracedata.append(cur_trace)
    result['tracedata'] = tracedata
    print('append tracedata, count: %s' % len(tracedata))


'''
trace end
'''

'''
eidolon start
'''


def append_eidolon_name(cur_eidolon, eidolon_dict, index):
    for lang in languages:
        cur_eidolon[name_lang_mapping[lang]] = eidolon_dict[lang][index]['name'].replace('\\n', ' ')
        print('append eidolon %s name: %s' % (lang, cur_eidolon[name_lang_mapping[lang]]))


def append_eidolon_image(character, cur_eidolon, eidolon_dict, index):
    img_ext = 'png'
    path = 'images/skills/%s-e%s' % (character, cur_eidolon['eidolonnum'])
    util.download_yatta_image('crawler/yatta/' + path, 'skill', eidolon_dict['EN'][index]['icon'], img_ext, base_dir)
    cur_eidolon['imageurl'] = '%s.%s' % (path, img_ext)
    print('append eidolon image: %s' % path)


def append_eidolon_attr(cur_eidolon, eidolon_dict, index):
    for lang in languages:
        desc = util.clean_desc_yatta(eidolon_dict[lang][index]['description'])
        params = eidolon_dict[lang][index]['params']
        if params is not None:
            for i in range(0, len(params)):
                desc = desc.replace('[%s]' % (i + 1),
                                    str(util.format_percent_number(params[i]) if '[%s]%%' % (i + 1) in desc else params[
                                        i]))
        cur_eidolon['Description' + lang] = desc
        print('append eidolon %s desc: %s' % (lang, desc))
    cur_eidolon['stype'] = 'eidolon'
    cur_eidolon['buffskill'] = util.is_buff_skill(cur_eidolon['DescriptionEN'])
    cur_eidolon['teamskill'] = util.is_team_skill(cur_eidolon['DescriptionEN'])
    print('append eidolon stype: %s, buffskill: %s, teamskill: %s' % (
        cur_eidolon['stype'], cur_eidolon['buffskill'], cur_eidolon['teamskill']))


def append_eidolon_tags(cur_eidolon, exist_eidolon):
    cur_eidolon['tags'] = exist_eidolon['tags'] if 'tags' in exist_eidolon else []


def append_eidolon_effect(cur_eidolon, exist_eidolon):
    cur_eidolon['effect'] = exist_eidolon['effect'] if 'effect' in exist_eidolon else []


def compare_eidolon(s, d):
    if 'id' in s and 'id' in d:
        return s['id'] == d['id']
    return s['eidolonnum'] == d['eidolonnum']


def append_eidolon(character, data_dict, exist_dict):
    eidolon = []
    eidolon_dict = {}
    for lang in languages:
        eidolons = []
        for v in data_dict[lang]['eidolons'].values():
            eidolons.append(v)
        eidolon_dict[lang] = eidolons
    exist_eidolons = exist_dict['eidolon']
    eidolon_cnt = len(list(eidolon_dict['EN']))
    for i in range(0, eidolon_cnt):
        cur_eidolon = {'id': str(eidolon_dict['EN'][i]['id']), 'eidolonnum': eidolon_dict['EN'][i]['rank']}
        append_eidolon_name(cur_eidolon, eidolon_dict, i)
        append_eidolon_image(character, cur_eidolon, eidolon_dict, i)
        append_eidolon_attr(cur_eidolon, eidolon_dict, i)
        find = list(filter(lambda s: compare_eidolon(s, cur_eidolon), exist_eidolons))
        exist_eidolon = find[0] if len(find) > 0 else {}
        append_eidolon_tags(cur_eidolon, exist_eidolon)
        append_eidolon_effect(cur_eidolon, exist_eidolon)
        eidolon.append(cur_eidolon)
    result['eidolon'] = eidolon
    print('append eidolon, count: %s' % len(eidolon))


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
        print('response: %s' % res.content)
        data = json.loads(res.content)
        if data is None or 'response' not in data or data['response'] != 200:
            print('fetch failed, please try again')
            exit(1)
        data_dict[lang] = data['data']
    append_name(data_dict)
    append_image(data_dict, result['id'], 'medium')
    append_image(data_dict, result['id'], 'large')
    append_basic(data_dict)
    append_level(data_dict)
    # append_skill(c, data_dict, exist_dict)
    # append_trace(c, data_dict, exist_dict)
    # append_eidolon(c, data_dict, exist_dict)
    with open(base_dir + '/lib/character/' + result['id'] + '.json', 'w', encoding='utf-8') as f:
        f.write(json.dumps(result, ensure_ascii=False, skipkeys=True, indent=4))


if __name__ == '__main__':
    generate_json(sys.argv[1])
