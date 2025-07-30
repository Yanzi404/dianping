# https://www.mafengwo.cn/jd/10156/gonglve.html

import requests
from bs4 import BeautifulSoup

from mysql import MySQLDatabase

"""
采用请求接口+解析html的方式，得到马蜂窝景点信息
"""


def api(page):
    url = "https://www.mafengwo.cn/ajax/router.php"
    payload = f"sAct=KMdd_StructWebAjax%7CGetPoisByTag&iMddid=10156&iTagId=0&iPage={page}&_ts=1753168294443&_sn=1019e57167"
    headers = {
        'Host': 'www.mafengwo.cn',
        'Cookie': 'mfw_uuid=686fc46c-dd23-d5f0-5a7d-896b5fe965d7; uva=s%3A92%3A%22a%3A3%3A%7Bs%3A2%3A%22lt%22%3Bi%3A1752155245%3Bs%3A10%3A%22last_refer%22%3Bs%3A24%3A%22https%3A%2F%2Fwww.mafengwo.cn%2F%22%3Bs%3A5%3A%22rhost%22%3BN%3B%7D%22%3B; __mfwurd=a%3A3%3A%7Bs%3A6%3A%22f_time%22%3Bi%3A1752155245%3Bs%3A9%3A%22f_rdomain%22%3Bs%3A15%3A%22www.mafengwo.cn%22%3Bs%3A6%3A%22f_host%22%3Bs%3A3%3A%22www%22%3B%7D; __mfwuuid=686fc46c-dd23-d5f0-5a7d-896b5fe965d7; PHPSESSID=0blpkmfr3j4q6rrusf0lt0te12; oad_n=a%3A3%3A%7Bs%3A3%3A%22oid%22%3Bi%3A1029%3Bs%3A2%3A%22dm%22%3Bs%3A15%3A%22www.mafengwo.cn%22%3Bs%3A2%3A%22ft%22%3Bs%3A19%3A%222025-07-22+14%3A54%3A47%22%3B%7D; __mfwc=direct; __mfwa=1752155245180.37945.2.1752155245180.1753167288147; __mfwlv=1753167288; __mfwvn=2; Hm_lvt_8288b2ed37e5bc9b4c9f7008798d2de0=1752155245,1753167288; HMACCOUNT=51F39F65C40784E4; bottom_ad_status=0; mfw_passport_redirect=https%3A%2F%2Fwww.mafengwo.cn%2Fpoi%2Fadd.php%3FiId%3D10156; __mfwb=6acc0c14258f.17.direct; __mfwlt=1753167970; Hm_lpvt_8288b2ed37e5bc9b4c9f7008798d2de0=1753167971; w_tsfp=ltvuV0MF2utBvS0Q7KnokkOsHzwkcDo4h0wpEaR0f5thQLErU5mA0od8tsn+NHHb5sxnvd7DsZoyJTLYCJI3dwMSFs2Ve4wZ2ViQxoQk3tsQBUQ0EsnaCAFMdbJz6jNCL3hCNxS00jA8eIUd379yilkMsyN1zap3TO14fstJ019E6KDQmI5uDW3HlFWQRzaLbjcMcuqPr6g18L5a5W6PtlzzeF1wCulCgRaR1itLCysrtBe5J7pYM0/+d5uvSqA=',
        'sec-ch-ua-platform': '"macOS"',
        'x-requested-with': 'XMLHttpRequest',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'sec-ch-ua-mobile': '?0',
        'origin': 'https://www.mafengwo.cn',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'referer': 'https://www.mafengwo.cn/jd/10156/gonglve.html',
        'accept-language': 'zh-CN,zh;q=0.9',
        'priority': 'u=1, i'
    }
    try:
        response = requests.request("POST", url, headers=headers, data=payload)
        return response.json()
    except Exception as e:
        print(f"请求失败：{e}，当前页面：{page}")


def parse(data, db):
    # 提取HTML文本
    html_list = data["data"]["list"]

    # 解析列表HTML
    soup_list = BeautifulSoup(html_list, 'html.parser')
    list_items = soup_list.find_all('li')

    print("\nParsed List Items:")
    for item in list_items:
        a_tag = item.find('a')
        if a_tag:
            title = a_tag.get('title', '')
            href = a_tag.get('href', '')
            img_tag = a_tag.find('img')
            img_src = img_tag.get('src', '') if img_tag else ''
            print(f"Title: {title}, Href: {href}, Image: {img_src}")
            db.execute(
                f"INSERT INTO `mafengwo_list` (`title`, `href`, `image`) VALUES ('{title}', '{href}', '{img_src}')")
    db.commit()


if __name__ == '__main__':
    db = MySQLDatabase()
    json_data = api(page=2)
    parse(json_data, db)
    # for page in range(2,3):
    #     json_data = api(page)
    #     parse(json_data,db)
