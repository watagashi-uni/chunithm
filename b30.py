from datetime import datetime
import hashlib
import os
import uuid
import pymysql
from modules.mysql_config import *
import numpy as np
from chunithm.chuniapi import aime_to_userid, call_chuniapi, get_chuni_asset, get_trophy_by_id
import ujson as json
import traceback
from PIL import Image, ImageFont, ImageDraw, ImageFilter
from modules.config import env
from modules.sk import recordname


server_name = {
    'aqua': 'Sam Aqua',
    'na': 'Nageki',
    'rin': 'Rin Aqua'
}


def process_user_music_list(user_music_list):
    processed_list = []

    for item in user_music_list:
        detail_list = item["userMusicDetailList"]
        processed_list.extend(detail_list)

    return processed_list


def truncate_two_decimal_places(number):
    if int(number) == 0:
        return 0
    str_number = str(number + 0.00000002)
    decimal_index = str_number.find('.')
    if decimal_index != -1:
        str_number = str_number[:decimal_index + 3]  # 保留两位小数
    return float(str_number)


def get_all_music(userid, server):
    uuid_str = str(uuid.uuid4())
    next_index = "0"
    user_music_list = []

    while int(next_index) != -1:
        params = {
            "userId": userid,
            "nextIndex": next_index,
            "maxCount": "300"
        }

        response = call_chuniapi(uuid_str, 'GetUserMusicApi', params, server)
        json_data = response.json()

        user_music_list += json_data["userMusicList"]
        next_index = json_data["nextIndex"]

    return process_user_music_list(user_music_list)


def get_user_data(userid, server):
    params = {
        "userId": userid,
        "segaIdAuthKey": ""
    }
    response = call_chuniapi(str(uuid.uuid4()), 'GetUserPreviewApi', params, server)
    return response.json()
    
def get_user_full_data(userid, server):
    params = {
        "userId": userid
    }
    response = call_chuniapi(str(uuid.uuid4()), 'GetUserDataApi', params, server)
    return response.json()

def get_user_team(userid, server):
    current_date = datetime.now()
    formatted_date = current_date.strftime("%Y-%m-%d")
    params = {
        "userId": userid,
        "playDate": formatted_date
    }
    response = call_chuniapi(str(uuid.uuid4()), 'GetUserTeamApi', params, server)
    return response.json()


def get_user_recent(userid, server):
    params = {
        "userId": userid
    }
    response = call_chuniapi(str(uuid.uuid4()), 'GetUserRecentRatingApi', params, server)
    return response.json()


def calculate_rating(constant, score):
    if constant == 0:
        return 0
    if score >= 1009000:
        return constant + 2.15
    elif 1007500 <= score < 1009000:
        return constant + 2.0 + 0.15 * (score - 1007500) / 1500
    elif 1005000 <= score < 1007500:
        return constant + 1.5 + 0.5 * (score - 1005000) / 2500
    elif 1000000 <= score < 1005000:
        return constant + 1.0 + 0.5 * (score - 1000000) / 5000
    elif 975000 <= score < 1000000:
        return constant + (score - 975000) / 25000
    elif 925000 <= score < 975000:
        return constant - 3.0 + 3.0 * (score - 925000) / 50000
    elif 900000 <= score < 925000:
        return constant - 5.0 + 2.0 * (score - 900000) / 25000
    elif 800000 <= score < 900000:
        return (constant - 5.0) / 2 + (constant - 5.0) / 2 * (score - 800000) / 100000
    elif 500000 <= score < 800000:
        return ((constant - 5.0) / 2) * (score - 500000) / 300000
    else:
        return 0

lmn_to_lmnp = {
    (2477, 3): 15.0, # sølips 15.1-15.0
    (1079, 3): 15.1, # X7124 15.0-15.1
    (2398, 3): 14.8, # neu 14.9-14.8
    (2532, 3): 14.7, # Spasmodic 14.8-14.7
    (2537, 3): 14.9, # GIGA BLAST 14.8-14.9
    (2354, 3): 14.7, # 月の光 14.8-14.7
    (2485, 3): 14.9, # Singularity 14.8-14.9
    (2239, 3): 14.8, # ホーリーサンバランド 14.7-14.8
    (2230, 3): 14.8, # #SUP3RORBITAL 14.7-14.8
    (331,  4): 14.7, # 猛進ソリストライフ！ ULT 14.6-14.7
    (2456, 3): 14.4, # Vibes 2k20 14.5-14.4
    (173,  3): 14.5, # Halcyon 14.4-14.5
    (722,  3): 14.5, # CITRUS MONSTER 14.4-14.5
    (2480, 3): 14.6, # GEOMETRIC DANCE 14.4-14.6
    (2184, 2): 14.5, # ENDYMION EXP 14.4-14.5
    (2525, 3): 14.5, # 本物のヒーローとの戦い 14.3-14.5
    (2395, 3): 13.7, # 酔いどれ知らず 13.5-13.7
    (210,  3): 12.6, # アスノヨゾラ哨戒班 13.0-12.6
    (2311, 3): 14.5, # †大闘士＝クライン・フォーゲル・シュピール＝えりか† 14.6-14.5
    (2488, 3): 14.7, # Yorugao 14.5-14.7
    (2507, 3): 14.2, # 星界ちゃんと可不ちゃんのおつかい合騒曲 14.4-14.2
    (141,  3): 14.6, # 閃鋼のブリューナク 14.5-14.6
    (2540, 3): 14.4, # Love's Theme of BADASS ～バッド・アス 愛のテーマ～ 14.2-14.4
    (2466, 3): 14.3, # Λlteration 14.2-14.3
    (2528, 3): 14.0, # Blow My Mind 14.1-14.0
    (2450, 3): 13.9, # セガサターン起動音[H.][Remix] 13.8-13.9
    (2457, 3): 14.1, # 《真紅》 ～ Pavane Pour La Flamme 13.8-14.1
    (462,  4): 13.5, # 物凄い勢いでけーねが物凄いうた ULT 13.8-13.5
    (2477, 2): 13.6, # sølips EXP 13.5-13.6
    (2566, 3): 11.5, # 少女PastQ 11.8-11.5
    (2574, 3): 13.4, # lucky omen 13.7-13.4
    (2501, 3): 13.0, # 海に化ける 13.2-13.0
    (99,   3): 13.0, # 言ノ葉カルマ 12.6-13.0
    (2508, 3): 13.5, # リレイアウター 13.3-13.5
    (2449, 3): 13.0, # ばかみたい【Taxi Driver Edition】 12.7-13.0
    (2480, 2): 12.4, # GEOMETRIC DANCE EXP 13.4-12.4
    (2444, 2): 12.5, # Cult future EXP 13.4-12.5
    (851,  3): 12.8, # 《理想》 ～ Cloudland 12.5-12.8
    (53,   3): 13.5, # Teriqma 13.0-13.5
    (2481, 3): 13.6, # Love Cheat! 13.4-13.6
    (2094, 3): 13.0, # Limits 12.9-13.0
    (96,   3): 12.9, # チルノのパーフェクトさんすう教室 12.5-12.9
    (2500, 3): 12.7, # 不可解 12.4-12.7
    (2493, 3): 12.7, # マツケンサンバII 12.9-12,7
    (2556, 2): 12.6, # Mutation EXP 12.8-12.6
    (2451, 3): 12.5, # スン(マイル)フラワー〜Sun(Mile)Flower 12.0-12.5
    (2478, 3): 12.0, # 茉子の日常 11.6-12.0
    (444,  3): 12.0, # エレクトロサチュレイタ 11.7-12.0
    (2497, 3): 11.9, # アイデン貞貞メルトダウン 12.1-11.9
    (2483, 3): 11.9, # 未来への咆哮 12.0-11.9
    (2274, 3): 11.9, # クリーパー 12.3-11.9
    (2467, 2): 11.9, # Regulus EXP 12.1-11.9
    (2456, 2): 11.8, # Vibes 2k20 EXP 12.0-11.8
    (2253, 2): 11.0, # レッド・ルーラー EXP 10.9-11.0
    (2435, 3): 11.0, # 異星にいこうね 10.4-11.0
}


def parse_chara_id_to_chara_and_trans(chara_id):
    return str(chara_id)[0: len(str(chara_id)) - 1].zfill(4), str(chara_id)[-1].zfill(2)


def create_rating_image(number):
    """
    根据给定的数字和等级，创建一个评分图片。
    :param number: 整数，将被除以100来得到要显示的评分数字。
    :return: 一个带有透明背景的PIL图像对象，其中数字在高度上居中。
    """
    if number <= 399:
        level='green'
    elif number <= 699:
        level='orange'
    elif number <= 999:
        level='red'
    elif number <= 1199:
        level='purple'
    elif number <= 1324:
        level='bronze'
    elif number <= 1449:
        level='silver'
    elif number <= 1524:
        level='gold'
    elif number <= 1599:
        level='platinum'
    else:
        level='rainbow'


     # 将输入的整数转换为xx.xx格式的字符串
    number /= 100
    formatted_number = f"{number:.2f}"  # 保留两位小数，但不在整数部分填充0
    
    # 评分图片存储的目录
    rating_dir = 'chunithm/assets/rating'
    
    # 分割格式化后的数字为整数部分和小数部分
    integer_part, decimal_part = formatted_number.split('.')
    
    # 创建列表存储对应的图片文件名
    image_files = []
    
    # 添加整数部分的数字图片文件名，对于小于10的数字不添加前导零
    for digit in integer_part:
        image_files.append(f'rating_{level}_{int(digit):02d}.png')
    
    # 添加小数点图片文件名
    image_files.append(f'rating_{level}_comma.png')
    
    # 添加小数部分的数字图片文件名，确保每个数字都是两位数
    for digit in decimal_part:
        image_files.append(f'rating_{level}_{int(digit):02d}.png')
    
    # 加载图片并计算总宽度和最大高度
    images = [Image.open(os.path.join(rating_dir, file)).convert("RGBA") for file in image_files]
    total_width = sum(img.width for img in images)
    max_height = max(img.height for img in images)
    
    # 创建新图像
    result_image = Image.new('RGBA', (total_width, max_height), (0, 0, 0, 0))
    
    # 粘贴数字到新图像，确保高度上居中
    current_width = 0
    for i, img in enumerate(images):
        # 通过索引判断当前是否为小数点图片
        if image_files[i].endswith('_comma.png'):
            # 小数点位置稍低
            offset_y = max_height - img.height
        else:
            # 数字居中
            offset_y = (max_height - img.height) // 2
        result_image.paste(img, (current_width, offset_y), img)
        current_width += img.width
    
    # 返回最终的图片
    return result_image


def get_user_info_pic(user_full_data, team_data, qqnum, userid, server):
    img = get_chuni_asset(f'namePlate/CHU_UI_NamePlate_{int(user_full_data["userData"]["nameplateId"]):08d}.png')
    if img is None:
        img = get_chuni_asset('namePlate/CHU_UI_NamePlate_00000001.png')
    img = img.convert("RGBA")
    chara1, chara2 = parse_chara_id_to_chara_and_trans(user_full_data["userData"]["characterId"])
    nameplate = Image.open('pics/chu_nameplate.png')
    img.paste(nameplate, (0, 0), nameplate.split()[3])
    ddsImage = get_chuni_asset(f'ddsImage/CHU_UI_Character_{chara1}_{chara2}_02.png')
    if ddsImage is None:
        ddsImage = get_chuni_asset('ddsImage/CHU_UI_Character_0000_00_02.png')
    ddsImage = ddsImage.resize((82, 82))
    try:
        img.paste(ddsImage, (471, 89), ddsImage.split()[3])
    except IndexError:
        img.paste(ddsImage, (471, 89))
    rating = create_rating_image(int(user_full_data["userData"]["playerRating"]))
    rating = rating.resize((int(rating.size[0] / 1.25), int(rating.size[1] / 1.25)))
    img.paste(rating, (222, 147), rating.split()[3])
    draw = ImageDraw.Draw(img)
    font_style = ImageFont.truetype("fonts/SourceHanSansCN-Bold.otf", 30)
    draw.text((184, 100), str(user_full_data["userData"]["level"]), fill=(0, 0, 0), font=font_style)
    if not recordname(qqnum, f'chuni_{server}{userid}', user_full_data["userData"]["userName"]):
        user_full_data["userData"]["userName"] = ''
    font_style = ImageFont.truetype("fonts/ヒラギノ角ゴ ( Hira Kaku) Pro W6.otf", 30)
    draw.text((228, 107), str(user_full_data["userData"]["userName"]), fill=(0, 0, 0), font=font_style)

    if (reincarnationNum := int(user_full_data["userData"]["reincarnationNum"])) != 0:
        reincarnation_star = Image.open('pics/chu_reincarnation.png')
        reincarnation_star = reincarnation_star.resize((34, 34))
        img.paste(reincarnation_star, (148, 85), reincarnation_star.split()[3])
        font_style = ImageFont.truetype("fonts/YuGothicUI-Semibold.ttf", 16)
        text_width = font_style.getsize(str(reincarnationNum))
        draw.text((int(165 - text_width[0] / 2), 91), str(reincarnationNum), fill=(0, 0, 0), font=font_style)
    
    print("trophyId", user_full_data["userData"]["trophyId"])
    trophy_data = get_trophy_by_id(user_full_data["userData"]["trophyId"])
    if trophy_data is not None:

        id, version, trophy_name, explain_text, rarity = trophy_data

        trophy_rarity_to_color = [
            'normal', 'bronze', 'silver', 'gold', 'gold', 'platina', 'platina', 'rainbow', 'ongeki', 'staff', 'ongeki', 'maimai'
        ]
        trophy_pic = Image.open(f'chunithm/assets/trophy/{trophy_rarity_to_color[rarity]}.png')
        img.paste(trophy_pic, (145, 46), trophy_pic.split()[3])
        font_style = ImageFont.truetype("fonts/KOZGOPRO-BOLD.OTF", 23)
        left_bound = 157
        right_bound = 547

        # 计算文本大小
        text_width, text_height = draw.textsize(trophy_name, font=font_style)

        # 确定文本的x坐标和宽度
        if text_width < right_bound - left_bound:
            # 如果文本没有超过边界，则居中显示
            x = left_bound + (right_bound - left_bound - text_width) // 2
            text_to_draw = trophy_name
        else:
            # 如果文本超过边界，对齐到左边界并截断超出部分
            x = left_bound
            # 计算可以显示的文本长度
            while text_width > right_bound - left_bound:
                trophy_name = trophy_name[:-1]
                text_width, text_height = draw.textsize(trophy_name, font=font_style)
            text_to_draw = trophy_name

        # 绘制文本
        draw.text((x, 54), text_to_draw, fill=(0, 0, 0), font=font_style)

    if 'teamRank' in team_data:
        if int(team_data['teamRank']) <= 10:
            team_pic = Image.open('chunithm/assets/team/rainbow.png')
        elif int(team_data['teamRank']) <= 40:
            team_pic = Image.open('chunithm/assets/team/gold.png')
        elif int(team_data['teamRank']) <= 70:
            team_pic = Image.open('chunithm/assets/team/silver.png')
        else:
            team_pic = Image.open('chunithm/assets/team/common.png')
        img.paste(team_pic, (0, 0), team_pic.split()[3])
        font_style = ImageFont.truetype("fonts/KOZGOPRO-BOLD.OTF", 18)
        if not recordname(qqnum, f'team_{server}{userid}', team_data['teamName']):
            team_data['teamName'] = 'CHUNITHM'
        draw.text((240, 19), team_data['teamName'], fill=(0, 0, 0, 180), font=font_style)
        draw.text((238, 17), team_data['teamName'], fill=(255, 255, 255), font=font_style)

    return img


def process_r10(userid, server, version='2.20', sort=True):
    difficulty_mapping = {
        "0": "basic",
        "1": "advanced",
        "2": "expert",
        "3": "master",
        "4": "ultima",
    }

    # 读取歌曲信息
    with open("chunithm/masterdata/musics.json", "r", encoding='utf-8') as f:
        musics = json.load(f)
    with open('chunithm/masterdata/musics_local.json', 'r', encoding='utf-8') as f:
        sdhd_music_data = json.load(f)
    music_info = {music['id']: music for music in musics}
    sdhd_music_info = {music['id']: music for music in sdhd_music_data}
    # 解析用户数据
    user_data = get_user_recent(userid, server)  # assuming user_input is your provided user data
    rating_list = []

    if user_data["userRecentRatingList"] == []:
        return rating_list
    # 遍历用户数据，计算rating，并构造需要的数据结构
    for record in user_data["userRecentRatingList"]:
        music_id = record["musicId"]
        difficult_id = record["difficultId"]
        score = int(record["score"])
        isdeleted = False
        try:
            music = music_info[music_id]
        except KeyError:
            try:
                music = sdhd_music_info[music_id]
                isdeleted = True
            except KeyError:
                continue
        try:
            difficulty_level = difficulty_mapping[difficult_id]
        except KeyError:
            continue
        if difficulty_level in music['difficulties']:
            difficulty = music['difficulties'][difficulty_level]
            if version == '2.25':
                difficulty = lmn_to_lmnp.get((int(music_id), int(difficult_id)), difficulty)
            
            rating = calculate_rating(difficulty, score)
            rating_list.append({
                'musicName': music['name'],
                'jacketFile': music['jaketFile'],
                'playLevel': difficulty,
                'musicDifficulty': difficulty_level,
                'score': score,
                'rating': rating,
                'isdeleted': isdeleted,
            })

    # 将rating_list按照rating降序排序
    if sort:
        rating_list.sort(key=lambda x: x['rating'], reverse=True)
    return rating_list


def process_b30(userid, server, version='2.20'):
    # 获取用户数据
    user_data = get_all_music(userid, server)
    # 读取音乐数据
    with open('chunithm/masterdata/musics.json', 'r', encoding='utf-8') as f:
        music_data = json.load(f)
    
    with open('chunithm/masterdata/musics_local.json', 'r', encoding='utf-8') as f:
        sdhd_music_data = json.load(f)

    # 创建一个字典，以便于从 musicId 找到对应的音乐信息
    music_dict = {music['id']: music for music in music_data}
    sdhd_music_dict = {music['id']: music for music in sdhd_music_data}
    # 存储计算出的 rating
    ratings = []

    for data in user_data:
        music_id = str(data['musicId'])
        level_index = int(data['level'])
        level_dict = {0: "basic", 1: "advanced", 2: "expert", 3: "master", 4: "ultima"}
        isdeleted = False
        try:
            music_info = music_dict[music_id]
        except KeyError:
            try:
                music_info = sdhd_music_dict[music_id]
                isdeleted = True
            except KeyError:
                continue
        music_name = music_info['name']
        jacket_file = music_info['jaketFile']
        try:
            difficulty = music_info['difficulties'][level_dict[level_index]]
            if version == '2.25':
                difficulty = lmn_to_lmnp.get((int(music_id), int(level_index)), difficulty)
        except KeyError:
            continue
        score = int(data['scoreMax'])
        rating = calculate_rating(difficulty, score)

        ratings.append({
            'musicName': music_name,
            'jacketFile': jacket_file,
            'playLevel': difficulty,
            'musicDifficulty': level_dict[level_index],
            'score': score,
            'rating': rating,
            'isFullCombo': data['isFullCombo'],
            'isAllJustice': data['isAllJustice'],
            'isdeleted': isdeleted,
        })

    ratings.sort(key=lambda x: x['rating'], reverse=True)
    
    return ratings


class BanState(Exception):
    def __init__(self, reason, msg):
        # 调用基类的构造函数，将原因和解决方案组合成一条消息
        super().__init__(f"banned")
        # 存储原因和解决方案
        self.reason = reason
        self.msg = msg


def chunib30(userid, server='aqua', version='2.15', qqnum='未知'):
    user_full_data = get_user_full_data(userid, server)
    if user_full_data['userData']['lastDataVersion'].startswith('2.25'):
        version = '2.25'
    if version == '2.15':
        pic = Image.open('pics/chub30sunp.png')
    elif version == '2.20':
        pic = Image.open('pics/chub30lmn.png')
    elif version == '2.25':
        pic = Image.open('pics/chub30lmnp.png')
    draw = ImageDraw.Draw(pic)

    user_team = get_user_team(userid, server)
    
    shadow = Image.new("RGBA", (320, 130), (0, 0, 0, 0))
    shadow.paste(Image.new("RGBA", (280, 105), (0, 0, 0, 50)), (5, 5))
    shadow = shadow.filter(ImageFilter.GaussianBlur(3))

    ratings = process_b30(userid, server, version)
    # ratings = [{'musicName': 'SINister Evolution', 'jacketFile': 'CHU_UI_Jacket_2038.dds', 'playLevel': 14.8, 'musicDifficulty': 'master', 'score': 1008040, 'rating': 16.854}, {'musicName': '月の光', 'jacketFile': 'CHU_UI_Jacket_2354.dds', 'playLevel': 14.8, 'musicDifficulty': 'master', 'score': 1007929, 'rating': 16.8429}, {'musicName': '腐れ外道とチョコレゐト', 'jacketFile': 'CHU_UI_Jacket_0118.dds', 'playLevel': 14.7, 'musicDifficulty': 'ultima', 'score': 1008139, 'rating': 16.7639}, {'musicName': 'Last Celebration', 'jacketFile': 'CHU_UI_Jacket_0994.dds', 'playLevel': 14.7, 'musicDifficulty': 'master', 'score': 1007768, 'rating': 16.7268}, {'musicName': '[CRYSTAL_ACCESS]', 'jacketFile': 'CHU_UI_Jacket_1094.dds', 'playLevel': 14.6, 'musicDifficulty': 'master', 'score': 1008204, 'rating': 16.6704}, {'musicName': 'IMPACT', 'jacketFile': 'CHU_UI_Jacket_2135.dds', 'playLevel': 14.5, 'musicDifficulty': 'master', 'score': 1008261, 'rating': 16.5761}, {'musicName': 'AXION', 'jacketFile': 'CHU_UI_Jacket_0863.dds', 'playLevel': 14.6, 'musicDifficulty': 'master', 'score': 1006946, 'rating': 16.4892}, {'musicName': 'POTENTIAL', 'jacketFile': 'CHU_UI_Jacket_2161.dds', 'playLevel': 14.3, 'musicDifficulty': 'expert', 'score': 1009823, 'rating': 16.45}, {'musicName': 'X7124', 'jacketFile': 'CHU_UI_Jacket_1079.dds', 'playLevel': 14.4, 'musicDifficulty': 'expert', 'score': 1007994, 'rating': 16.449399999999997}, {'musicName': "DA'AT -The First Seeker of Souls-", 'jacketFile': 'CHU_UI_Jacket_2241.dds', 'playLevel': 14.6, 'musicDifficulty': 'expert', 'score': 1006734, 'rating': 16.446800000000003}, {'musicName': 'のぼれ！すすめ！高い塔', 'jacketFile': 'CHU_UI_Jacket_0448.dds', 'playLevel': 14.3, 'musicDifficulty': 'master', 'score': 1007988, 'rating': 16.3488}, {'musicName': 'サドマミホリック', 'jacketFile': 'CHU_UI_Jacket_0628.dds', 'playLevel': 14.2, 'musicDifficulty': 'master', 'score': 1008416, 'rating': 16.2916}, {'musicName': 'Jade Star', 'jacketFile': 'CHU_UI_Jacket_0966.dds', 'playLevel': 14.2, 'musicDifficulty': 'master', 'score': 1008359, 'rating': 16.285899999999998}, {'musicName': 'U&iVERSE -銀河鸞翔-', 'jacketFile': 'CHU_UI_Jacket_2326.dds', 'playLevel': 14.4, 'musicDifficulty': 'master', 'score': 1006782, 'rating': 16.2564}, {'musicName': 'グラ ウンドスライダー協奏曲第一番「風唄」', 'jacketFile': 'CHU_UI_Jacket_2279.dds', 'playLevel': 14.1, 'musicDifficulty': 'expert', 'score': 1009496, 'rating': 16.25}, {'musicName': 'レータイス パークEx', 'jacketFile': 'CHU_UI_Jacket_0980.dds', 'playLevel': 14.2, 'musicDifficulty': 'master', 'score': 1007745, 'rating': 16.2245}, {'musicName': 'Elemental Creation', 'jacketFile': 'CHU_UI_Jacket_0232.dds', 'playLevel': 14.5, 'musicDifficulty': 'master', 'score': 1006070, 'rating': 16.214}, {'musicName': 'Insane Gamemode', 'jacketFile': 'CHU_UI_Jacket_1015.dds', 'playLevel': 14.4, 'musicDifficulty': 'master', 'score': 1006556, 'rating': 16.2112}, {'musicName': 'Name of oath', 'jacketFile': 'CHU_UI_Jacket_0389.dds', 'playLevel': 14.5, 'musicDifficulty': 'master', 'score': 1006045, 'rating': 16.209}, {'musicName': '真千年女王', 'jacketFile': 'CHU_UI_Jacket_1092.dds', 'playLevel': 14.8, 'musicDifficulty': 'master', 'score': 1004047, 'rating': 16.2047}, {'musicName': 'エンドマークに希望と涙を添えて', 'jacketFile': 'CHU_UI_Jacket_0103.dds', 'playLevel': 14.8, 'musicDifficulty': 'master', 'score': 1003759, 'rating': 16.175900000000002}, {'musicName': 'ヒバナ', 'jacketFile': 'CHU_UI_Jacket_0818.dds', 'playLevel': 14.0, 'musicDifficulty': 'ultima', 'score': 1009809, 'rating': 16.15}, {'musicName': '宵闇の月に抱かれて', 'jacketFile': 'CHU_UI_Jacket_2158.dds', 'playLevel': 14.0, 'musicDifficulty': 'master', 'score': 1008818, 'rating': 16.1318}, {'musicName': 'Athlete Killer "Meteor"', 'jacketFile': 'CHU_UI_Jacket_1065.dds', 'playLevel': 14.0, 'musicDifficulty': 'master', 'score': 1008811, 'rating': 16.1311}, {'musicName': '二次元ドリームフィーバー', 'jacketFile': 'CHU_UI_Jacket_2037.dds', 'playLevel': 14.0, 'musicDifficulty': 'master', 'score': 1008691, 'rating': 16.1191}, {'musicName': '天火明命', 'jacketFile': 'CHU_UI_Jacket_2144.dds', 'playLevel': 14.0, 'musicDifficulty': 'master', 'score': 1008194, 'rating': 16.0694}, {'musicName': 'ENDYMION', 'jacketFile': 'CHU_UI_Jacket_2184.dds', 'playLevel': 14.4, 'musicDifficulty': 'expert', 'score': 1005841, 'rating': 16.0682}, {'musicName': 'Taiko Drum Monster', 'jacketFile': 'CHU_UI_Jacket_0671.dds', 'playLevel': 14.3, 'musicDifficulty': 'master', 'score': 1006288, 'rating': 16.0576}, {'musicName': 'Aleph-0', 'jacketFile': 'CHU_UI_Jacket_0428.dds', 'playLevel': 14.1, 'musicDifficulty': 'expert', 'score': 1007247, 'rating': 16.0494}, {'musicName': '再生不能', 'jacketFile': 'CHU_UI_Jacket_1105.dds', 'playLevel': 14.0, 'musicDifficulty': 'master', 'score': 1007977, 'rating': 16.0477}, {'musicName': 'フューチャー・イヴ', 'jacketFile': 'CHU_UI_Jacket_2344.dds', 'playLevel': 13.9, 'musicDifficulty': 'master', 'score': 1008964, 'rating': 16.046400000000002}, {'musicName': 'こちら、幸福安心委員会です。', 'jacketFile': 'CHU_UI_Jacket_1068.dds', 'playLevel': 13.9, 'musicDifficulty': 'master', 'score': 1008927, 'rating': 16.0427}, {'musicName': 'Rule the World!!', 'jacketFile': 'CHU_UI_Jacket_2109.dds', 'playLevel': 14.0, 'musicDifficulty': 'master', 'score': 1007899, 'rating': 16.0399}, {'musicName': 'FLUFFY FLASH', 'jacketFile': 'CHU_UI_Jacket_2346.dds', 'playLevel': 14.8, 'musicDifficulty': 'master', 'score': 1002058, 'rating': 16.0058}, {'musicName': '電脳少女は歌姫の夢を見るか？', 'jacketFile': 'CHU_UI_Jacket_2019.dds', 'playLevel': 14.2, 'musicDifficulty': 'master', 'score': 1006509, 'rating': 16.0018}, {'musicName': '迷える音色は恋の唄', 'jacketFile': 'CHU_UI_Jacket_2350.dds', 'playLevel': 13.9, 'musicDifficulty': 'master', 'score': 1008486, 'rating': 15.9986}, {'musicName': 'トンデモワンダーズ', 'jacketFile': 'CHU_UI_Jacket_2264.dds', 'playLevel': 13.9, 'musicDifficulty': 'master', 'score': 1008285, 'rating': 15.9785}, {'musicName': 'SON OF SUN', 'jacketFile': 'CHU_UI_Jacket_0887.dds', 'playLevel': 13.8, 'musicDifficulty': 'expert', 'score': 1009937, 'rating': 15.950000000000001}, {'musicName': 'Ascension to Heaven', 'jacketFile': 'CHU_UI_Jacket_0978.dds', 'playLevel': 13.8, 'musicDifficulty': 'expert', 'score': 1009842, 'rating': 15.950000000000001}, {'musicName': 'Fracture Ray', 'jacketFile': 'CHU_UI_Jacket_0749.dds', 'playLevel': 14.7, 'musicDifficulty': 'master', 'score': 1002027, 'rating': 15.9027}]
    
    rating_sum = 0
    for i in range(0, 30):
        try:
            single = b30single(ratings[i], version)
        except IndexError:
            break
        r, g, b, mask = shadow.split()
        pic.paste(shadow, ((int(52 + (i % 5) * 290)), int(287 + int(i / 5) * 127)), mask)
        pic.paste(single, ((int(53+(i%5)*290)), int(289+int(i/5)*127)))
        rating_sum += truncate_two_decimal_places(ratings[i]['rating'])
    b30 = rating_sum / 30
    font_style = ImageFont.truetype("fonts/SourceHanSansCN-Bold.otf", 37)
    draw.text((1331, 205), str(round(b30, 4)), fill=(255,255,255,255), font=font_style, stroke_width=2, stroke_fill="#38809A")

    ratings = process_r10(userid, server, version)
    rating_sum = 0
    for i in range(0, 10):
        try:
            single = b30single(ratings[i], version)
        except IndexError:
            break
        r, g, b, mask = shadow.split()
        pic.paste(shadow, ((int(1582 + (i % 2) * 290)), int(287 + int(i / 2) * 127)), mask)
        pic.paste(single, ((int(1582+(i%2)*290)), int(289+int(i/2)*127)))
        rating_sum += truncate_two_decimal_places(ratings[i]['rating'])
    r10 = rating_sum / 10
    draw.text((1717, 205), str(round(r10, 4)), fill=(255,255,255,255), font=font_style, stroke_width=2, stroke_fill="#38809A")
    
    rank = round((b30 * 3 + r10) / 4, 4)

    font_style = ImageFont.truetype("fonts/SourceHanSansCN-Medium.otf", 16)
    
    
    # 创建一个单独的图层用于绘制rank阴影
    rankimg = Image.new("RGBA", (140, 55), (100, 110, 180, 0))
    draw = ImageDraw.Draw(rankimg)
    font_style = ImageFont.truetype("fonts/SourceHanSansCN-Bold.otf", 34)
    text_width = font_style.getsize(str(rank))
    draw.text((int(70 - text_width[0] / 2), int(20 - text_width[1] / 2)), str(rank), fill=(61, 74, 162, 210),
              font=font_style, stroke_width=2, stroke_fill=(61, 74, 162, 210))
    rankimg = rankimg.filter(ImageFilter.GaussianBlur(1.2))
    draw = ImageDraw.Draw(rankimg)
    draw.text((int(70 - text_width[0] / 2), int(20 - text_width[1] / 2)), str(rank), fill=(255, 255, 255), font=font_style)
    r, g, b, mask = rankimg.split()
    pic.paste(rankimg, (712, 118), mask)

    user_nameplate = get_user_info_pic(user_full_data, user_team, qqnum, userid, server)
    pic.paste(user_nameplate, (57, 55), user_nameplate.split()[3])

    # text = 'Player Rom Version: ' + user_full_data['userData']['lastRomVersion'] + '\n'
    text = '\n'
    if server in server_name:
        text += 'Data is from ' + server_name[server] + '\n'
    text += 'Designed by Watagashi_uni\nGenerated by Unibot'

    font_style = ImageFont.truetype("fonts/SourceHanSansCN-Medium.otf", 16)

    # 创建一个透明图层，用于绘制半透明文字
    shadow_layer = Image.new('RGBA', pic.size, (255, 255, 255, 0))
    shadow_draw = ImageDraw.Draw(shadow_layer)

    # 绘制文字阴影
    shadow_position = (1976, 996) if len(text.split('\n')) == 3 else (1976, 977)
    shadow_draw.text(shadow_position, text, fill=(0, 0, 0, 150), font=font_style, align='right')
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(0.5))
    # 将带有阴影的图层合并到原始图像上
    pic.paste(Image.alpha_composite(pic.convert('RGBA'), shadow_layer), (0, 0))

    # 在原始图像上绘制不透明的文字
    draw = ImageDraw.Draw(pic)
    text_position = (1975, 995) if len(text.split('\n')) == 3 else (1975, 976)
    draw.text(text_position, text, fill=(255, 255, 255), font=font_style, align='right')

    pic = pic.convert("RGB")
    uuid_str = str(uuid.uuid4())
    pic.save(f'piccache/{uuid_str}b30.jpg')

    if server == 'lin':
        banState = 0
        try:
            banState = int(get_user_data(userid, server)['banState'])
        except:
            pass
        if banState == 1:
            raise BanState("本Aimeに紐づくユーザーデータに弊社規約に抵触する疑いのあるデータが存在しています\n今後このようなデータが存在する場合\n本Aimeは使用できなくなりますのでご注意ください", f'piccache/{uuid_str}b30.jpg')
        elif banState == 2:
            raise BanState("本Aimeに紐づくユーザーデータに弊社規約に抵触するユーザーデータが存在しているため\n本Aimeは使用できません", f'piccache/{uuid_str}b30.jpg')

    # pic.show()
    return f'piccache/{uuid_str}b30.jpg'


def b30single(single_data, version):
    color = {
        'master': (187, 51, 238),
        'expert': (238, 67, 102),
        'advanced': (254, 170, 0),
        'ultima': (0, 0, 0),
        'basic': (102, 221, 17)
    }
    musictitle = single_data['musicName']
    
    if version == '2.15':
        pic = Image.new("RGB", (620, 240), (255, 250, 243))
    else:
        pic = Image.new("RGB", (620, 240), (255, 255, 255))
    
    try:
        jacket = Image.open(f'chunithm/jackets/{single_data["jacketFile"]}')
        jacket = jacket.resize((186, 186))
    except:
        jacket = Image.open(f'chunithm/jackets/CHU_UI_Jacket_0081.dds')
        jacket = jacket.resize((186, 186))
    pic.paste(jacket, (32, 28))

    draw = ImageDraw.Draw(pic)
    font = ImageFont.truetype('fonts/YuGothicUI-Semibold.ttf', 36)
    size = font.getsize(musictitle)
    if version == '2.25' and single_data['isdeleted']:
        musictitle = '(配信停止)' + musictitle
    if size[0] > 365:
        musictitle = musictitle[:int(len(musictitle)*(345/size[0]))] + '...'
    draw.text((240, 27), musictitle, '#000000', font)

    font = ImageFont.truetype('fonts/FOT-RodinNTLGPro-DB.ttf', 58)
    draw.text((234, 87), str(single_data['score']), '#000000', font)

    font = ImageFont.truetype('fonts/SourceHanSansCN-Bold.otf', 38)
    draw.ellipse((242, 165, 286, 209), fill=color[single_data['musicDifficulty']])
    draw.rectangle((262, 165, 334, 209), fill=color[single_data['musicDifficulty']])
    draw.ellipse((312, 165, 356, 209), fill=color[single_data['musicDifficulty']])
    draw.text((259, 157), str(single_data['playLevel']), (255, 255, 255), font)
    draw.text((370, 157), '→ ' + str(truncate_two_decimal_places(single_data['rating'])), (0, 0, 0), font)

    if 'isAllJustice' in single_data:
        font = ImageFont.truetype('fonts/FOT-RodinNTLGPro-DB.ttf', 35)
        if single_data['isAllJustice'] == 'true' or single_data['isAllJustice'] is True:
            draw.text((530, 105), "AJ", '#000000', font)
        elif single_data['isFullCombo'] == 'true' or single_data['isFullCombo'] is True:
            draw.text((530, 105), "FC", '#000000', font)
    pic = pic.resize((280, 105))
    return pic


def chuni_r30(userid, server='aqua', version='2.15'):
    # TODO: r30施工中
    if version == '2.15':
        pic = Image.open('pics/chub30sunp.png')
    else:
        pic = Image.open('pics/chub30.png')
    draw = ImageDraw.Draw(pic)

    user_data = get_user_data(userid, server)

    font_style = ImageFont.truetype("fonts/SourceHanSansCN-Bold.otf", 35)
    draw.text((215, 65), user_data['userName'], fill=(0, 0, 0), font=font_style)
    font_style = ImageFont.truetype("fonts/FOT-RodinNTLGPro-DB.ttf", 15)
    try:
        draw.text((218, 118), get_user_team(userid, server)['teamName'], fill=(0, 0, 0), font=font_style)
    except KeyError:
        draw.text((218, 118), 'CHUNITHM', fill=(0, 0, 0), font=font_style)
    font_style = ImageFont.truetype("fonts/FOT-RodinNTLGPro-DB.ttf", 28)
    draw.text((314, 150), str(int(user_data['level']) + int(user_data['reincarnationNum']) * 100), fill=(255, 255, 255), font=font_style)
    
    shadow = Image.new("RGBA", (320, 130), (0, 0, 0, 0))
    shadow.paste(Image.new("RGBA", (280, 105), (0, 0, 0, 50)), (5, 5))
    shadow = shadow.filter(ImageFilter.GaussianBlur(3))

    # ratings = process_b30(userid, server, version)
    
    # rating_sum = 0
    # for i in range(0, 30):
    #     try:
    #         single = b30single(ratings[i], version)
    #     except IndexError:
    #         break
    #     r, g, b, mask = shadow.split()
    #     pic.paste(shadow, ((int(52 + (i % 5) * 290)), int(287 + int(i / 5) * 127)), mask)
    #     pic.paste(single, ((int(53+(i%5)*290)), int(289+int(i/5)*127)))
    #     rating_sum += ratings[i]['rating']
    # b30 = truncate_two_decimal_places(rating_sum / 30)
    # font_style = ImageFont.truetype("fonts/SourceHanSansCN-Bold.otf", 37)
    # draw.text((208, 205), str(b30), fill=(255,255,255,255), font=font_style, stroke_width=2, stroke_fill="#38809A")

    ratings = process_r10(userid, server, version, sort=False)
    rating_sum = 0
    for i in range(0, 30):
        try:
            single = b30single(ratings[i], version)
        except IndexError:
            break
        r, g, b, mask = shadow.split()
        pic.paste(shadow, ((int(52 + (i % 5) * 290)), int(287 + int(i / 5) * 127)), mask)
        pic.paste(single, ((int(53+(i%5)*290)), int(289+int(i/5)*127)))
        rating_sum += ratings[i]['rating']
    r10 = truncate_two_decimal_places(rating_sum / 10)
    draw.text((1726, 205), str(r10), fill=(255,255,255,255), font=font_style, stroke_width=2, stroke_fill="#38809A")
    
    # rank = truncate_two_decimal_places((b30 * 3 + r10) / 4)

    # font_style = ImageFont.truetype("fonts/SourceHanSansCN-Medium.otf", 16)
    
    
    # # 创建一个单独的图层用于绘制rank阴影
    # rankimg = Image.new("RGBA", (120, 55), (100, 110, 180, 0))
    # draw = ImageDraw.Draw(rankimg)
    # font_style = ImageFont.truetype("fonts/SourceHanSansCN-Bold.otf", 35)
    # text_width = font_style.getsize(str(rank))
    # draw.text((int(60 - text_width[0] / 2), int(20 - text_width[1] / 2)), str(rank), fill=(61, 74, 162, 210),
    #           font=font_style, stroke_width=2, stroke_fill=(61, 74, 162, 210))
    # rankimg = rankimg.filter(ImageFilter.GaussianBlur(1.2))
    # draw = ImageDraw.Draw(rankimg)
    # draw.text((int(60 - text_width[0] / 2), int(20 - text_width[1] / 2)), str(rank), fill=(255, 255, 255), font=font_style)
    # r, g, b, mask = rankimg.split()
    # pic.paste(rankimg, (492, 110), mask)

    pic = pic.convert("RGB")
    pic.save(f'piccache/{hashlib.sha256(userid.encode()).hexdigest()}r30.jpg')
    


def get_connection():
    return pymysql.connect(
        host=host, 
        port=port, 
        user='pjsk', 
        password=password,
        database='pjsk', 
        charset='utf8mb4'
    )


database_list = {
        'aqua': 'chunibind',
        'lin': 'linbind',
        'super': 'superbind',
        'na': 'leebind',
        'rin': 'rinbind',
        'mobi': 'mobibind',
        'ring': 'ringbind',
        'shiro': 'shirobind',
    }
# database_list硬编码防止注入。%s会导致表名被加入引号报错

def getchunibind(qqnum, server='aqua'):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(f'SELECT * from {database_list[server]} where qqnum=%s', (qqnum, ))
            data = cursor.fetchone()
            return data[2] if data else None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
    finally:
        conn.close()


def bind_aimeid(qqnum, aimeid, server='aqua'):
    userid = str(aime_to_userid(aimeid, server))
    if userid is None:
        return '卡号不存在'
    try:
        user_data = get_user_full_data(userid, server)
    except ValueError:
        return '你至少先打把中二再绑定吧'
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            sql = f"INSERT INTO {database_list[server]} (qqnum, aimeid) VALUES (%s, %s) ON DUPLICATE KEY UPDATE aimeid=%s"
            val = (str(qqnum), str(userid), str(userid))
            cursor.execute(sql, val)
            conn.commit()

            if not recordname(qqnum, f'chuni_{server}{userid}', user_data['userData']['userName']):
                user_data['userData']['userName'] = ''
            return f"绑定成功！记得撤回卡号哦\n游戏昵称：{user_data['userData']['userName']}\n等级：{user_data['userData']['level']}"
    except Exception as e:
        traceback.print_exc()
        return "绑定失败！"
    finally:
        conn.close()
