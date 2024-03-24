import requests
from bs4 import BeautifulSoup
import json


def update_sdvx_chuni():
    urls = [
        "https://sdvx.in/chunithm/sort/pops.htm",
        "https://sdvx.in/chunithm/sort/niconico.htm",
        "https://sdvx.in/chunithm/sort/toho.htm",
        "https://sdvx.in/chunithm/sort/variety.htm",
        "https://sdvx.in/chunithm/sort/irodorimidori.htm",
        "https://sdvx.in/chunithm/sort/gekimai.htm",
        "https://sdvx.in/chunithm/sort/original.htm",
        "https://sdvx.in/chunithm/del.htm"
    ]

    songs = {}

    proxies = {
        "http": "http://localhost:7890",
        "https": "http://localhost:7890",
    }

    for url in urls:
        response = requests.get(url, proxies=proxies)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        scripts = soup.find_all('script')

        for script in scripts:
            if script.string:
                content = script.string.strip()
                if content.startswith("SORT"):
                    try:
                        song_id = str(content.split('()')[0].replace('SORT', '').strip())
                        title = script.find_next_sibling(string=True)
                        songs[title] = song_id
                    except:
                        pass


        print(f"已解析 {url} 的曲名和ID。")


    with open('chunithm/sdvxin_chuni.json', 'w', encoding='utf-8') as file:
        json.dump(songs, file, ensure_ascii=False, indent=4)

if __name__ == '__main__':
    update_sdvx_chuni()