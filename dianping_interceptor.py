import json
from mitmproxy import http
from pathlib import Path
from datetime import datetime

from mysql import MySQLDatabase

"""
通过mitmproxy拦截解析请求，获取大众点评评论
"""
# 确保保存目录存在
SAVE_DIR = Path("./dianping_responses")
SAVE_DIR.mkdir(exist_ok=True)


def response(flow: http.HTTPFlow):
    # 检查是否是目标URL
    if "m.dianping.com/ugc/review/reviewlist" in flow.request.url:
        try:
            if flow.response.status_code != 200:
                raise Exception("响应状态不为200")
            response_json = flow.response.json()
            if response_json['code'] != 200:
                raise Exception(f"响应参数不为200，响应内容：{response_json}")
            try:
                # 创建以shopUuid命名的子目录
                shop_uuid = flow.request.query.get('shopUuid')
                shop_dir = SAVE_DIR / shop_uuid
                shop_dir.mkdir(parents=True, exist_ok=True)

                # 构建保存文件名（使用时间戳和URL部分作为文件名）
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                offset = flow.request.query.get('offset')
                filename = f"{timestamp}_{offset}.json"

                # 保存响应内容
                save_path = shop_dir / filename
                with open(save_path, "wb") as f:
                    f.write(flow.response.content)
            except Exception as e:
                raise Exception(f"保存文件时发生错误: {e}")
            parse_json(response_json, shop_uuid, offset)
        except Exception as e:
            print(f"{e}")


def parse_json(json: dict, shop_uuid, offset):
    db = MySQLDatabase()
    review_list = json['reviewInfo']['reviewListInfo']['reviewList']
    for review in review_list:
        reviewId = review['reviewId']
        userId = review['userId']
        addTime = review['addTime']
        text = review['reviewBody']['children'][0]['children'][0]['text']
        star = review['star']
        bigurls = []
        for reviewPic in review['reviewPics']:
            bigurls.append(reviewPic['bigurl'])
        pics = ','.join(bigurls)
        db.execute(
            f"insert into reviews(reviewId,shopUuid,userId,addTime,text,pics,star,offset) values({reviewId},{shop_uuid},{userId},'{addTime}','{text}','{pics}',{star},{offset})")
    db.commit()
    print(f'当前页：{offset}')


def test_parse_json():
    with open("./dianping_responses/20250730173251_17602428_0.json", "r") as f:
        parse_json(json.load(f), 123, 10)
