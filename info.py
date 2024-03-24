import json
import math
import os
import re
import uuid
from chunithm.alias import chu_aliastomusicid
import Levenshtein as lev
from chunithm.b30 import get_all_music, get_user_data, get_user_full_data, get_user_info_pic, get_user_team, sunp_to_lmn
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from modules.pjskinfo import get_match_rate_sqrt, string_similar


def search_song(query):
    # 读取数据
    with open('chunithm/music.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    exact_matches = []
    fuzzy_matches = []

    for song in data:
        # 根据需求格式化标题
        title = song['title']
        if song['we_kanji'] and song['we_star']:
            title += f"【{song['we_kanji']}】"

        # 计算精确匹配度
        exact_match_rate = get_match_rate_sqrt(query, title)
        # 计算模糊匹配度
        fuzzy_match_rate = string_similar(query, title)

        if exact_match_rate > 0:
            exact_matches.append((song['id'], title, exact_match_rate))
        elif fuzzy_match_rate > 0:
            fuzzy_matches.append((song['id'], title, fuzzy_match_rate))

    # 分别排序精确匹配和模糊匹配结果
    exact_matches.sort(key=lambda x: x[2], reverse=True)
    fuzzy_matches.sort(key=lambda x: x[2], reverse=True)

    # 组合结果：先取前三个精确匹配（如果存在），然后取模糊匹配
    # 确保不重复添加模糊匹配结果
    results = exact_matches[:3]
    for match in fuzzy_matches:
        if match[0] not in [exact_match[0] for exact_match in exact_matches]:
            results.append(match)
            if len(results) == 10:
                break

    if len(results) == 0:
        return "没有找到捏"
    else:
        return "\n".join([f"{result[0]}: {result[1]}" for result in results])


def song_details(alias):
    resp = chu_aliastomusicid(alias)
    song_id = str(resp['musicid'])
    reverse_difficulty_mapping = {
        "basic": 0,
        "advanced": 1,
        "expert": 2,
        "master": 3,
        "ultima": 4,
    }
    # 读取数据
    with open('chunithm/music.json', 'r', encoding='utf-8') as f:
        data_music = json.load(f)
        
    with open('chunithm/masterdata/musics.json', 'r', encoding='utf-8') as f:
        data_musics = json.load(f)
        
    with open('chunithm/music-ex.json', 'r', encoding='utf-8') as f:
        data_music_ex = json.load(f)
    # 根据id找到歌曲
    song_music = next((song for song in data_music if song["id"] == song_id), None)
    song_musics = next((song for song in data_musics if song["id"] == song_id), None)
    song_music_ex = next((song for song in data_music_ex if song["id"] == song_id), None)

    if not song_music or not song_musics:
        return "没有找到该歌曲", None

    # 格式化标题和难度
    title = song_music['title']
    difficulties = song_musics['difficulties']

    if difficulties['expert'] == 0:
        difficulties['expert'] = song_music["lev_exp"] if "+" in song_music["lev_exp"] else (song_music["lev_exp"] + '.?')
    if difficulties['master'] == 0:
        difficulties['master'] = song_music["lev_mas"] if "+" in song_music["lev_mas"] else (song_music["lev_mas"] + '.?')
    
    original_difficulties = difficulties.copy()  # 复制原始难度
    modified = False  # 标记是否有修改

    for single in difficulties:
        try:
            new_value = sunp_to_lmn.get((int(song_id), reverse_difficulty_mapping[single]))
            if new_value is not None:
                difficulties[single] = new_value
                modified = True
        except KeyError:
            pass

    # 构建原始难度字符串
    original_difficulties_str = f"{song_music['lev_bas']}/{song_music['lev_adv']}/{original_difficulties['expert']}/{original_difficulties['master']}"
    if 'ultima' in original_difficulties and original_difficulties['ultima'] > 0:
        original_difficulties_str += f"/{original_difficulties['ultima']}"

    # 构建修改后的难度字符串
    difficulties_str = f"{song_music['lev_bas']}/{song_music['lev_adv']}/{difficulties['expert']}/{difficulties['master']}"
    if 'ultima' in difficulties and difficulties['ultima'] > 0:
        difficulties_str += f"/{difficulties['ultima']}"

    # 根据是否有修改，构建最终输出字符串
    if modified:
        final_str = f"{original_difficulties_str} (SUN PLUS)\n{difficulties_str} (Luminous)"
    else:
        final_str = original_difficulties_str


    if song_music['we_kanji'] and song_music['we_star']:
        title += f"【{song_music['we_kanji']}】"
        final_str = f"WORLD'S END {'★'*int(int(song_music['we_star'])/2)}"

    info = f"{song_music['id']}: {title}\n"\
        f"匹配度: {round(resp['match'], 4)}\n"\
        f"类型：{song_music['catname']}\n"\
        f"艺术家：{song_music['artist']}\n"

    # 如果song_music_ex不是None，添加版本和上线时间信息
    if song_music_ex is not None:
        date_str = song_music_ex['date_added']
        info += f"版本：{song_music_ex['version'].replace('+', ' PLUS').replace('×', ' LOST')}\n"\
                f"上线时间：{date_str[:4]}/{date_str[4:6]}/{date_str[6:]}\n"

    # 添加难度信息
    info += f"难度：{final_str}\n"

    # 图片地址
    image_url = f"/chunithm/jackets/{song_musics['jaketFile']}"

    return info, image_url


class ChuLevelError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


def group_by_difficulty(tuples_list):
    grouped_dict = {}
    for item in tuples_list:
        # 假设元组的第三个元素是难度值
        difficulty_value = item[2]
        if difficulty_value not in grouped_dict:
            grouped_dict[difficulty_value] = []
        grouped_dict[difficulty_value].append(item)

    # 对每个难度级别内的元组按照level（第二个元素）从大到小排序
    for difficulty in grouped_dict:
        grouped_dict[difficulty] = sorted(grouped_dict[difficulty], key=lambda x: x[1], reverse=True)

    # 对字典的键进行排序，确保从大到小的顺序
    sorted_difficulties = sorted(grouped_dict.keys(), reverse=True)

    # 创建一个新的排序后的字典
    sorted_grouped_dict = {difficulty: grouped_dict[difficulty] for difficulty in sorted_difficulties}
    return sorted_grouped_dict


def get_diff_music(difficult):
    with open('chunithm/music.json', 'r', encoding='utf-8') as f:
        musics = json.load(f)
    levels = {'lev_exp': 2, 'lev_mas': 3, 'lev_ult': 4}
    result = [(music['id'], levels[level]) 
              for music in musics
              for level in levels 
              if music[level] == difficult]
    
    with open('chunithm/masterdata/musics.json', 'r', encoding='utf-8') as f:
        music_list = json.load(f)
    difficulty_map = {'expert': 2, 'master': 3, 'ultima': 4}
    difficulty_value_dict = {}

    for music in music_list:
        for difficulty_name, difficulty_number in difficulty_map.items():
            key = (music['id'], difficulty_number)
            difficulty_value = music['difficulties'].get(difficulty_name, 0)
            difficulty_value_dict[key] = difficulty_value
    id_to_image_map = {music['id']: music['image'] for music in musics}
    
    # 更新 result，添加难度值
    result_with_difficulty = []
    for (music_id, difficulty_number) in result:
        if (int(music_id), difficulty_number) in sunp_to_lmn:
            difficulty_value = sunp_to_lmn[(int(music_id), difficulty_number)]
        else:
            difficulty_value = difficulty_value_dict.get((music_id, difficulty_number), 0)
        result_with_difficulty.append((music_id, difficulty_number, difficulty_value, id_to_image_map.get(music_id)))

    return group_by_difficulty(result_with_difficulty)


def get_difficulty_range(input_value):
    if input_value.endswith("+"):
        base_value = float(input_value[:-1])  # 去掉 "+"，然后转换为浮点数
        return [base_value + 0.5 + i * 0.1 for i in range(5)]  # 生成 base_value + 0.5 到 base_value + 0.9 的列表
    else:
        base_value = float(input_value)
        return [base_value + i * 0.1 for i in range(5)]  # 生成 base_value 到 base_value + 0.4 的列表


def get_rank(score):
    if score >= 1009000:
        return 'SSS+'
    elif 1007500 <= score < 1009000:
        return 'SSS'
    elif 1005000 <= score < 1007500:
        return 'SS+'
    elif 1000000 <= score < 1005000:
        return 'SS'
    elif 990000 <= score < 1000000:
        return 'S+'
    elif 975000 <= score < 990000:
        return 'S'


def gen_single_lev(list, user_music_map=None):
    color = {
        2: (238, 67, 102),
        4: (0, 0, 0),
    }
    singleRank = Image.new("RGBA", (1100, 2500), (0, 0, 0, 0))
    row = 0
    i = 0
    for music in list:
        base_x = 20 + 95 * i
        base_y = 20 + 100 * row
        if music[1] in [2, 4]:
            # 获取底色
            base_color = color.get(music[1], (0, 0, 0))  # 假设music[1]是难度等级
            
            # 底色正方形的位置
            draw = ImageDraw.Draw(singleRank)

            # 绘制底色正方形，稍微大于jacket尺寸
            draw.rectangle([base_x - 5, base_y - 5, base_x + 85, base_y + 85], fill=base_color)

        # 粘贴jacket图片
        jacket = Image.open(f'chunithm/jackets/{music[3]}')
        jacket = jacket.resize((80, 80))
        singleRank.paste(jacket, (base_x, base_y))
        if user_music_map is not None:
            draw = ImageDraw.Draw(singleRank)
            font_style = ImageFont.truetype("fonts/SourceHanSansCN-Bold.otf", 18)
            if (int(music[0]), music[1]) in user_music_map:
                score = user_music_map.get((int(music[0]), music[1]))
                w = int(font_style.getsize(str(score))[0] / 2)
                draw.text((base_x - w + 40, base_y + 70), str(score), fill='#000000',
                        font=font_style, align='right', stroke_width=2, stroke_fill=(255, 255, 255))
                if (srank := get_rank(score)):
                    rank_pic = Image.open(f'pics/chu_{srank}.png')
                    singleRank.paste(rank_pic, (base_x + 8, base_y - 5))
            else:
                overlay = Image.new('RGBA', (80, 80), (0, 0, 0, 55))
                singleRank.paste(overlay, (base_x, base_y), overlay.split()[3])
        i += 1
        if i == 11:
            i = 0
            row += 1
    if i == 0:
        row = row - 1
    singleRank = singleRank.crop((0, 0, 1100, 20 + 100 * (row + 1)))
    return singleRank


def add_background_to_rank_pic(rank_pic, background_path):
    # 打开排名图片和背景图片
    rank_image = rank_pic
    background = Image.open(background_path)

    # 获取排名图片和背景图片的尺寸
    rank_width, rank_height = rank_image.size
    bg_width, bg_height = background.size

    # 计算背景图片等比例缩放的新尺寸
    # 使得背景图片能够覆盖rank_pic的最大面积
    rank_ratio = rank_width / rank_height
    bg_ratio = bg_width / bg_height

    if bg_ratio > rank_ratio:
        # 缩放背景的高度以适应rank_pic的高度
        new_height = rank_height
        new_width = int(new_height * bg_ratio)
    else:
        # 缩放背景的宽度以适应rank_pic的宽度
        new_width = rank_width
        new_height = int(new_width / bg_ratio)

    # 调整背景图片的尺寸
    resized_background = background.resize((new_width, new_height), Image.ANTIALIAS)

    # 计算裁剪背景图片的位置
    x = (new_width - rank_width) // 2
    y = (new_height - rank_height) // 2

    # 裁剪背景图片以适应rank_pic的尺寸
    cropped_background = resized_background.crop((x, y, x + rank_width, y + rank_height))

    # 将rank_pic粘贴到裁剪后的背景图片上
    cropped_background.paste(rank_image, (0, 0), rank_image)

    return cropped_background


def gen_level_rank(diff, userid=None, server='aqua'):
    grouped_dict = get_diff_music(diff)
    if diff.isdigit() or '+' in diff:
        if grouped_dict == {}:
            raise ChuLevelError('没有找到该难度数据，bot仅支持exp, mst, ult')
        all_diff = get_difficulty_range(diff)

        user_music_map = None
        if userid is not None:
            user_music = get_all_music(userid, server)
            user_music_map = {(int(music["musicId"]), int(music["level"])): int(music["scoreMax"]) for music in user_music}
            user_full_data = get_user_full_data(userid, server)
            user_team = get_user_team(userid, server)
        rank_pic = Image.new("RGBA", (1300, 7000), (0, 0, 0, 0))
        draw = ImageDraw.Draw(rank_pic)
        y = 300
        font_style = ImageFont.truetype("fonts/SourceHanSansCN-Bold.otf", 55)
        for level in grouped_dict:
            if level in all_diff:
                draw.text((40, y + 10), str(level), fill=(0, 0, 0), font=font_style)
                single_rank = gen_single_lev(grouped_dict[level], user_music_map)
                rank_pic.paste(single_rank, (170, y), mask=single_rank.split()[3])
                y += single_rank.size[1] + 20
        font_style = ImageFont.truetype("fonts/SourceHanSansCN-Bold.otf", 25)
        draw.text((940, y), 'Generated by Unibot\nDesigned by Watagashi_uni', fill='#00CCBB',
                font=font_style, align='right')
        rank_pic = rank_pic.crop((0, 0, 1300, y + 100))
        
        logo = Image.open('pics/top_main_logo.png')
        logo = logo.resize((int(logo.size[0] / 1.5), int(logo.size[1] / 1.5)))
        if userid is not None:
            rank_pic.paste(logo, (930, 80), logo.split()[3])
            user_nameplate = get_user_info_pic(user_full_data, user_team)
            rank_pic.paste(user_nameplate, (175, 60), user_nameplate.split()[3])
            
        else:
            rank_pic.paste(logo, (530, 80), logo.split()[3])
        background_path = 'pics/lmn.png'
        result_image = add_background_to_rank_pic(rank_pic, background_path)
        result_image.convert('RGB')
        
        if userid is None:
            result_image.save(f'piccache/chu/{diff}.jpg')
            return f'piccache/chu/{diff}.jpg'
        else:
            uuid_name = uuid.uuid4()
            result_image.save(f'piccache/chu_{uuid_name}.jpg')
            return f'piccache/chu_{uuid_name}.jpg'

    else:
        raise ChuLevelError('请正确输入，仅支持14，14+这种格式的难度')


def chu_level_rank(diff, userid=None, server='aqua'):
    if userid is None:
        if os.path.exists(f'piccache/chu/{diff}.jpg'):
            return f'piccache/chu/{diff}.jpg'
        else:
            return gen_level_rank(diff)
    else:
        return gen_level_rank(diff, userid, server)