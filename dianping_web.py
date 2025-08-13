import requests
from urllib.parse import quote
from bs4 import BeautifulSoup
from mysql import MySQLDatabase

"""
采用请求接口+解析html的方式，得到大众点评景点信息
"""


def search_api(query, page):
    url = f"https://www.dianping.com/search/keyword/3/0_{query}/o11p{page}"
    payload = {}
    headers = {
        'Host': 'www.dianping.com',
        'sec-ch-ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-User': '?1',
        'Sec-Fetch-Dest': 'document',
        'Referer': f"https://www.dianping.com/search/keyword/3/0_{quote(query)}/o11",
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Cookie': 'navCtgScroll=143.125; navCtgScroll=143.75; _lxsdk_cuid=197e3bae7fbc8-08252380aa41288-18525636-157188-197e3bae7fbc8; _lxsdk=197e3bae7fbc8-08252380aa41288-18525636-157188-197e3bae7fbc8; _hc.v=6d8930e3-6e7f-c9b7-27e3-1fe06d96b357.1751872367; s_ViewType=10; cy=3; cye=hangzhou; cityid=344; default_ab=shopreviewlist%3AA%3A1; WEBDFPID=yxv6vw9v4x4u5xu9zvu331z8880031zx802v6yy33705795817u8256x-1755083195317-1751872398327ICQAEUQ75613c134b6a252faa6802015be905512983; fspop=test; utm_source_rg=; logan_session_token=yilwnfphmgnighv7ydzz; qruuid=eb006209-8c86-40cf-b953-f6184f2875f2; dplet=43d4151e356b68c597b49baa18410114; dper=0202b1225a343b95b4b261a3808e53d9d3265c6522b853c27df8613f8e66e7639cd50dd27d413aa66cbd789d5d6ea9d24deec0febf09320a64e4000000001f2c0000ec22ee001836fc6bcdf418f60bd6e3ecb31a21f65d9376feb673834f5a044c487f3e82a92c5d8b883273e239a638d560; ll=7fd06e815b796be3df069dec7836c3df; ua=dpuser_3684539262; ctu=367c98c08ecf92cd3692006a61e154f14d4c247fc0dc71724bfed7e3ed03d67c; Hm_lvt_602b80cf8079ae6591966cc70a3940e7=1753177912,1754996962; HMACCOUNT=51F39F65C40784E4; _lxsdk_s=1989df5e5b2-ef4-e3d-b3%7C%7C184; Hm_lpvt_602b80cf8079ae6591966cc70a3940e7=1754997084'    }
    response = requests.request("GET", url, headers=headers, data=payload)
    if response.status_code == 200:
        with open(f'html/{query}{page}.html', 'w', encoding='utf-8') as file:
            file.write(response.text)
        return response.text
    else:
        raise Exception(f"请求失败，状态码：{response.status_code},当前查询：{query},当前页面：{page}")


def bs(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    # 获取列表容器
    shop_list = soup.find('div', {'id': 'shop-all-list'})
    # 获取所有项
    shop_items = shop_list.find_all('li')
    # 遍历每个项并提取信息
    for shop in shop_items:
        # 景区名称
        name = shop.find('h4').text.strip()
        # 图片链接
        img_tag = shop.find('img')
        image_url = img_tag['src'] if img_tag else None
        # 景区链接
        spot_url = shop.find('a', {'data-click-name': 'shop_title_click'})['href']

        # 评分
        star_icon = shop.find('div', class_='star_icon')
        classes = star_icon.find('span').get('class', [])
        star_class = [c for c in classes if 'star_' in c][0]
        rating = star_class.split('_')[1]

        # 评价数量
        review_count = shop.find('b').text if shop.find('b') else '0'
        # 分类标签
        category = shop.find('span', {'class': 'tag'}).text
        # 地区
        location = shop.find_all('span', {'class': 'tag'})[1].text if len(
            shop.find_all('span', {'class': 'tag'})) > 1 else None
        # 打印提取的信息
        print(f"景区名称: {name}")
        print(f"图片链接: {image_url}")
        print(f"景区链接: {spot_url}")
        print(f"评分: {rating}/50")
        print(f"评价数量: {review_count}条")
        print(f"分类: {category}")
        print(f"地点: {location}")
        print("-" * 50)
        return name, image_url, spot_url, rating, review_count, category, location


if __name__ == '__main__':
    db = MySQLDatabase()
    for i in range(1, 14):
        html = search_api(query='公园', page=i)
        name, image_url, spot_url, rating, review_count, category, location = bs(html)
        db.execute(
            f"insert into scenic_spots(name,image_url,spot_url,rating,review_count,category,location) values('{name}','{image_url}','{spot_url}','{rating}','{review_count}','{category}','{location}')")
    db.commit()
