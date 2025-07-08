import requests
from urllib.parse import quote
from bs4 import BeautifulSoup
from mysql import MySQLDatabase


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
        'Cookie': 'navCtgScroll=0; navCtgScroll=0; _lx_utm=utm_source%3Dbing%26utm_medium%3Dorganic; _lxsdk_cuid=197e3bae7fbc8-08252380aa41288-18525636-157188-197e3bae7fbc8; _lxsdk=197e3bae7fbc8-08252380aa41288-18525636-157188-197e3bae7fbc8; fspop=test; _hc.v=6d8930e3-6e7f-c9b7-27e3-1fe06d96b357.1751872367; s_ViewType=10; utm_source_rg=; WEBDFPID=yxv6vw9v4x4u5xu9zvu331z8880031zx802v6yy33705795817u8256x-1751958798888-1751872398327ICQAEUQ75613c134b6a252faa6802015be905512983; qruuid=d83cc62e-d30d-4f3e-83e4-1b7e64606723; dper=02028b2036aa2de46be28dd3714a1ffb9f19499a526ccf6174dfcf998e6174369f35fb4ba40af8a85a7817c7f0328d9c6d8b8069866f19a00e7400000000cc2a0000d8c30aa1171c8b0e3189861193614c79b38b2bb4c93f5a07260fda17c12ae8a202e94015ad9164b813f3c988dbe8a057; ll=7fd06e815b796be3df069dec7836c3df; Hm_lvt_602b80cf8079ae6591966cc70a3940e7=1751872434; HMACCOUNT=51F39F65C40784E4; __CACHE@is_login=true; logan_custom_report=; cy=3; cye=hangzhou; __CACHE@referer=https://www.dianping.com/search/keyword/3/0_%E5%85%AC%E5%9B%AD; logan_session_token=qjicniql0cqqis392v4p; Hm_lpvt_602b80cf8079ae6591966cc70a3940e7=1751956916; _lxsdk_s=197e8c461fd-1e7-3ea-e1b%7C%7C43; s_ViewType=10'
    }
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
        name, image_url, spot_url, rating, review_count, category, location =bs(html)
        db.execute(f"insert into scenic_spots(name,image_url,spot_url,rating,review_count,category,location) values('{name}','{image_url}','{spot_url}','{rating}','{review_count}','{category}','{location}')")

    db.commit()



