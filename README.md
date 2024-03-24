# 中二模块说明

该模块不开源 API 和 aimedb 请求部分，用能力的请自己抓包游戏。

## 最初所需文件

- 从 [https://chunithm.sega.jp/storage/json/music.json](https://chunithm.sega.jp/storage/json/music.json) 下载的官方歌曲 json 文件
- 一份 SDHD 游戏文件（包含 A000 和 option）

## 生成歌曲数据
1、新建`masterdata`，`jackets`文件夹

2、修改代理（可删除），填入`A000_dir`和`option_dir`，运行`analyse_official_data.py`，此操作会生成`masterdata`文件夹下的`musics.json`文件和一个`music_difficulties.csv`，里面有本地没有的歌曲的数据，还会下载歌曲封面。

3、打开 csv 文件，填入本地没有的歌曲的定数，ULTIMA 和 WORLD'S END 谱面没有的填 0 即可

4、再运行一次`analyse_official_data.py`，完成数据生成

5、建议安装削除曲补全包后填入路径运行`sdhd_analyser.py`，会生成一份本地处理出来的数据，可补全削除曲。该文件的作用是靠官方数据的文件查不到的歌会在这个文件里面再查一遍，所以可以显示削除曲

## 更新歌曲数据

官方更新 music.json 后下载覆盖，运行一次`analyse_official_data.py`，填入 csv 文件中新曲定数，再运行一次`analyse_official_data.py`即可

## 谱面预览

修改代理（可删除）后，可设置定时任务运行`analyse_sdvxin.py`，会生成`sdvxin_chuni.json`文件，对应曲名和 sdvx.in 网站的 id
