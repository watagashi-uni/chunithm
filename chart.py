import json
import os
import difflib
import re
import traceback
from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError
import requests
from io import BytesIO

from chunithm.alias import chu_aliastomusicid


def load_songs(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        return json.load(file)


def find_song_id(song_title):
    filename = 'chunithm/sdvxin_chuni.json'
    songs = load_songs(filename)

    # 尝试直接匹配
    if song_title in songs:
        return songs[song_title], song_title

    # 尝试模糊匹配
    close_matches = difflib.get_close_matches(song_title, songs.keys(), n=1, cutoff=0.8)
    if close_matches:
        return songs[close_matches[0]], close_matches[0]

    # 正则表达式，用于删除特定的后缀
    pattern = re.compile(r' -.*?-|～.*?～')
    
    # 移除特定的后缀并再次尝试模糊匹配
    cleaned_title = pattern.sub('', song_title).strip()
    close_matches = difflib.get_close_matches(cleaned_title, songs.keys(), n=1, cutoff=0.9)
    if close_matches:
        return songs[close_matches[0]], close_matches[0]

    # 尝试匹配标题中的一部分
    parts = re.split(r' -|- |～| ～', song_title)
    for part in parts:
        if part in songs:
            return songs[part], part

    return None # 没有找到匹配项


def official_id_to_sdvx_id(official_id):
    # 从music.json文件加载歌曲
    json_filename = "chunithm/music.json"
    with open(json_filename, 'r', encoding='utf-8') as file:
        json_songs = json.load(file)

    song_title = None
    # 从music.json中使用ID找到对应的曲目标题
    for song in json_songs:
        if str(song["id"]) == str(official_id):
            song_title = song["title"]
            break

    if song_title is None:
        raise ChuChartError("找不到你说的歌曲")

    # 使用之前定义的查找方法找到对应的sdvxin_chuni.json中的ID
    return find_song_id(song_title)


# setup proxy
PROXY = {'http': 'http://localhost:7890', 'https': 'http://localhost:7890'}


def paste_image(background, image, force=False):
    if image.mode == 'RGBA':
        # 如果图像是 RGBA 模式，则使用透明通道作为掩码
        background.paste(image, (0, 0), image.split()[3])
    elif force:
        # 如果图像不是 RGBA 模式，则直接粘贴
        background.paste(image, (0, 0))
    return background


class ChuChartError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


def download_and_merge_images(musicid, sdvxid, difficulty):
    # 构建URL
    prefix = sdvxid[:2]
    
    base_url = f"https://sdvx.in/chunithm/{prefix}/bg/{sdvxid}bg.png"
    if difficulty == 'master':
        obj_url = f"https://sdvx.in/chunithm/{prefix}/obj/data{sdvxid}mst.png"
    elif difficulty == 'ultima':
        obj_url = f"https://sdvx.in/chunithm/ult/obj/data{sdvxid}ult.png"
    else:
        obj_url = f"https://sdvx.in/chunithm/{prefix}/obj/data{sdvxid}{difficulty[:3]}.png"
    bar_url = f"https://sdvx.in/chunithm/{prefix}/bg/{sdvxid}bar.png"

    # 下载图像
    try:
        obj_image = Image.open(BytesIO(requests.get(obj_url, proxies=PROXY).content))
    except UnidentifiedImageError:
        if difficulty == 'ultima':
            raise ChuChartError('没有ULTIMA谱面数据')
        else:
            raise ChuChartError('谱面图片下载失败')
    base_image = Image.open(BytesIO(requests.get(base_url, proxies=PROXY).content))
    bar_image = Image.open(BytesIO(requests.get(bar_url, proxies=PROXY).content))

    # 确定所有图像中的最大宽度和高度
    max_width = max(base_image.width, obj_image.width, bar_image.width)
    max_height = max(base_image.height, obj_image.height, bar_image.height)

    # 创建一个新的黑色背景图像
    black_image = Image.new("RGBA", (max_width, max_height), (0, 0, 0, 255))

    # 在黑色背景上平铺每个图像
    black_image = paste_image(black_image, base_image)
    black_image = paste_image(black_image, obj_image, True)
    merged_image = paste_image(black_image, bar_image)

    # 保存图像
    directory = os.path.join("charts", "chunithm", str(musicid))
    os.makedirs(directory, exist_ok=True)
    output_path = os.path.join(directory, f"{difficulty}.jpg")
    # 保存图像为JPEG格式，并选择一个质量设置
    merged_image = merged_image.convert('RGB') # 将图像转换为RGB，因为JPEG不支持透明度
    merged_image.save(output_path, 'JPEG', quality=60) # 你可以调整质量参数来达到所需的文件大小
    
    print(f"图像已保存到 {output_path}")
    return output_path


def get_chunithm_chart(alias, difficulty):
    resp = chu_aliastomusicid(alias)
    musicid = str(resp['musicid'])
    print(musicid, difficulty)
    if int(musicid) > 8000:
        raise ChuChartError("暂不支持World's end 谱面生成")
    local_path = os.path.join("charts", "chunithm", str(musicid), f"{difficulty}.jpg")
    
    info = official_id_to_sdvx_id(musicid)
    if info is not None:
        sdvxid, title = info
    else:
        raise ChuChartError('无法生成谱面图片，可能谱面保管所还没更新或bot更新不及时')
    if os.path.exists(local_path):
        return (title, ) + (local_path,) + (resp['match'], )
    if sdvxid is not None:
        download_and_merge_images(musicid, sdvxid, difficulty)
        return (title, ) + (local_path,) + (resp['match'], )
    else:
        raise ChuChartError('无法生成谱面图片，可能谱面保管所还没更新或bot更新不及时')


if __name__ == '__main__':
    pass

