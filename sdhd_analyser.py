import os
import shutil
import xml.etree.ElementTree as ET
import json


def parse_music_data(xml_file):
    print(xml_file)
    tree = ET.parse(xml_file)
    root = tree.getroot()

    music_info = {
        "releaseTagName": root.find("./releaseTagName/str").text,
        "name": root.find("./name/str").text,
        "id": root.find("./cueFileName/id").text,
        "genreNames": [genre.find("./str").text for genre in root.findall("./genreNames/list/StringID")],
        "jaketFile": root.find("./jaketFile/path").text,
        "difficulties": {}
    }
    
    for fumen in root.findall("./fumens/MusicFumenData"):
        if fumen.find("./enable").text.lower() == 'false':
            level = 0
        else:
            level = float(fumen.find("./level").text)
            level += float(fumen.find("./levelDecimal").text) / 100
        music_info["difficulties"][fumen.find("./type/data").text.lower()] = level
    
    return music_info

def process_music_data(input_dir, output_dir, json_file):
    music_data = []
    jacket_dir = os.path.join(output_dir, "jackets")

    if not os.path.exists(jacket_dir):
        os.makedirs(jacket_dir)
    
    for root, dirs, files in os.walk(input_dir):
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            if os.path.isdir(dir_path):
                for file in os.listdir(dir_path):
                    if file.endswith(".xml"):
                        xml_file = os.path.join(dir_path, file)
                        new_music_info = parse_music_data(xml_file)
                        for old_music_info in music_data:
                            if old_music_info['id'] == new_music_info['id']:
                                old_music_info['difficulties'].update(new_music_info['difficulties'])
                                break
                        else:
                            music_data.append(new_music_info)
                
                        dds_file = os.path.join(dir_path, new_music_info["jaketFile"])
                        dest_file = os.path.join(jacket_dir, new_music_info["jaketFile"])
                        if os.path.exists(dds_file) and not os.path.exists(dest_file):
                            shutil.copy(dds_file, jacket_dir)
    
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(music_data, f, indent=4, ensure_ascii=False)


def update_music_data(option_dir, output_dir, json_file):
    jacket_dir = os.path.join(output_dir, "jackets")
    if not os.path.exists(jacket_dir):
        os.makedirs(jacket_dir)

    with open(json_file, 'r', encoding='utf-8') as f:
        music_data = json.load(f)

    for root, dirs, _ in os.walk(option_dir):
        for dir in dirs:
            music_dir = os.path.join(root, dir, 'music')
            if os.path.exists(music_dir):
                for item in os.listdir(music_dir):
                    item_path = os.path.join(music_dir, item)
                    if os.path.isdir(item_path):
                        for file in os.listdir(item_path):
                            if file.endswith(".xml"):
                                xml_file = os.path.join(item_path, file)
                                new_music_info = parse_music_data(xml_file)
                                for old_music_info in music_data:
                                    if old_music_info['id'] == new_music_info['id']:
                                        for key, value in new_music_info['difficulties'].items():
                                            if value != 0:
                                                old_music_info['difficulties'][key] = value
                                        break
                                else:
                                    music_data.append(new_music_info)
                
                                dds_file = os.path.join(item_path, new_music_info["jaketFile"])
                                dest_file = os.path.join(jacket_dir, new_music_info["jaketFile"])
                                if os.path.exists(dds_file) and not os.path.exists(dest_file):
                                    shutil.copy(dds_file, jacket_dir)
    
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(music_data, f, indent=4, ensure_ascii=False)

A000_dir = 'F:/SDHD2.12/App/data/A000/music/'
option_dir = 'F:/SDHD2.12/App/bin/option'
output_dir = 'chunithm'
json_file = os.path.join(output_dir, "masterdata/musics_local.json")

process_music_data(A000_dir, output_dir, json_file)
update_music_data(option_dir, output_dir, json_file)