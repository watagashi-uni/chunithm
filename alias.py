import os
import time
import pymysql
import ujson as json
from modules.mysql_config import *
from modules.pjskinfo import get_match_rate_sqrt, isSingleEmoji, string_similar, writelog
import Levenshtein as lev
import math


def chu_matchname(alias):
    match = {'musicid': 0, "match": 0, 'name': ''}
    with open('chunithm/masterdata/musics.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    for musics in data:
        name = musics['name']
        # 计算精确匹配度
        exact_match = get_match_rate_sqrt(alias.lower(), name.lower())
        # 计算模糊匹配度
        fuzzy_match = string_similar(alias.lower(), name.lower())

        # 选择匹配度较高的一种
        higher_match = max(exact_match, fuzzy_match)

        # 如果找到更高的匹配度，更新结果
        if higher_match > match['match']:
            match['match'] = higher_match
            match['musicid'] = musics['id']
            match['name'] = musics['name']

    return match



def chu_aliastomusicid(alias):
    alias = alias.strip()
    if alias == '':
        return {'musicid': 0, 'match': 0, 'name': '', 'translate': ''}
    if alias.isdigit() and int(alias) < 10000 and int(alias) not in [135, 39, 2085]:
        match = {'musicid': 0, "match": 1, 'name': ''}
        with open('chunithm/masterdata/musics.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        for musics in data:
            if int(alias) == int(musics['id']):
                match['musicid'] = musics['id']
                match['name'] = musics['name']
                return match
    mydb = pymysql.connect(host=host, port=port, user='pjsk', password=password,
                           database='pjsk', charset='utf8mb4')
    mycursor = mydb.cursor()
    mycursor.execute('SELECT * from chualias where alias=%s', (alias,))
    raw = mycursor.fetchone()
    mycursor.close()
    mydb.close()
    if raw is not None:
        with open('chunithm/masterdata/musics.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        name = ''
        for musics in data:
            if int(musics['id']) != raw[2]:
                continue
            name = musics['name']
            break
        
        translate = ''
        return {'musicid': raw[2], 'match': 1, 'name': name, 'translate': translate}
    return chu_matchname(alias)


def chuset(newalias, oldalias, qqnum, username, qun):
    newalias = newalias.strip()
    if isSingleEmoji(newalias):
        return "由于数据库排序规则原因，不支持单个emoji字符作为歌曲昵称"
    resp = chu_aliastomusicid(oldalias)
    if resp['musicid'] == 0:
        return "找不到你要设置的歌曲，请使用正确格式：chuset新昵称to旧昵称"
    musicid = resp['musicid']

    mydb = pymysql.connect(host=host, port=port, user='pjsk', password=password,
                           database='pjsk', charset='utf8mb4')
    mycursor = mydb.cursor()
    sql = f"insert into chualias(ALIAS,MUSICID) values (%s, %s) " \
          f"on duplicate key update musicid=%s"
    val = (newalias, musicid, musicid)
    mycursor.execute(sql, val)
    mydb.commit()
    mycursor.close()
    mydb.close()

    with open('chunithm/masterdata/musics.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    title = ''
    for music in data:
        if int(music['id']) != int(musicid):
            continue
        title = music['name']
    timeArray = time.localtime(time.time())
    Time = time.strftime("%Y-%m-%d %H:%M:%S", timeArray)
    writelog(f'[CHUNITHM][{Time}] {qun} {username}({qqnum}): {newalias}->{title}')
    return f"设置成功！{newalias}->{title}\n已记录bot文档中公开的实时日志，设置不合适的昵称将会被拉黑"


def chudel(alias, qqnum, username, qun):
    alias = alias.strip()
    resp = chu_aliastomusicid(alias)
    if resp['match'] != 1:
        return "找不到你要设置的歌曲，请使用正确格式：chudel昵称"
    mydb = pymysql.connect(host=host, port=port, user='pjsk', password=password,
                           database='pjsk', charset='utf8mb4')
    mycursor = mydb.cursor()
    mycursor.execute("DELETE from chualias where alias=%s", (alias,))
    mydb.commit()
    mycursor.close()
    mydb.close()
    timeArray = time.localtime(time.time())
    Time = time.strftime("%Y-%m-%d %H:%M:%S", timeArray)
    if str(qqnum) == '1103479519':
        writelog(f'[CHUNITHM][{Time}] 管理员删除了{resp["name"]}的昵称：{alias}')
        return "删除成功！"
    writelog(f'[CHUNITHM][{Time}] {qun} {username}({qqnum}): 删除了{resp["name"]}的昵称：{alias}')
    return "删除成功！\n已记录bot文档中公开的实时日志，乱删将被拉黑"


def chualias(alias, musicid=None):
    from imageutils import text2image
    if musicid is None:
        resp = chu_aliastomusicid(alias)
        if resp['musicid'] == 0:
            return "找不到你说的歌曲哦"
        musicid = resp['musicid']
        returnstr = f"{resp['name']}\n匹配度:{round(resp['match'], 4)}\n"
        
    else:
        returnstr = ''
    mydb = pymysql.connect(host=host, port=port, user='pjsk', password=password,
                           database='pjsk', charset='utf8mb4')
    mycursor = mydb.cursor()
    mycursor.execute('SELECT * from chualias where musicid=%s', (musicid,))
    respdata = mycursor.fetchall()
    mycursor.close()
    mydb.close()
    for raw in respdata:
        returnstr = returnstr + raw[1] + "，"
    if len(returnstr[:-1]) > 170:
        infopic = text2image(text=returnstr[:-1] + '\n昵称均为用户添加，与bot和bot主无关\n\n', max_width=800, padding=(30, 30))
        infopic.save(f'piccache/{musicid}alias.png')
        return f"[CQ:image,file=file:///{os.getcwd()}/piccache/{musicid}alias.png,cache=0]"
    else:
        return returnstr[:-1] + '\n昵称均为用户添加，与bot和bot主无关'

