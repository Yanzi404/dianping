import json
from typing import Dict, Any

from mitmproxy import http

from mysql import MySQLDatabase

# 常量定义
TARGET_URL_PATTERN = "m.dianping.com/wxmapi/wxsearch/search"
SUCCESS_STATUS_CODE = 200


def requests(flow: http.HTTPFlow) -> None:
    pass


def response(flow: http.HTTPFlow) -> None:
    # 检查是否是目标URL
    if TARGET_URL_PATTERN not in flow.request.url:
        return

    try:
        # 验证响应状态
        if flow.response.status_code != SUCCESS_STATUS_CODE:
            print(f"响应状态码错误: {flow.response.status_code}")
            return

        response_json = flow.response.json()
        if response_json.get('code') != SUCCESS_STATUS_CODE:
            print(f"响应参数错误，code: {response_json.get('code')}")
            return

        # 解析并保存到数据库
        parse_json(response_json)
    except json.JSONDecodeError:
        print("响应内容不是有效的JSON格式")
    except Exception as e:
        print(f"处理响应时发生错误: {e}")


def parse_json(response_data: Dict[str, Any]) -> None:
    """解析JSON数据并保存到数据库"""
    try:
        db = MySQLDatabase()

        # 获取景点列表
        attractions_list = response_data.get('data', {}).get('list', [])

        if not attractions_list:
            print("没有找到景点数据")
            return

        # 准备插入语句
        sql = """
            INSERT INTO attractions (
                shopUuid, categoryName, name, defaultPic, priceText, 
                recommendReason, regionName, reviewCount, starScore,
                categoryId, cityId, shopPower, shopType, myLat, myLng
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                categoryName = VALUES(categoryName),
                name = VALUES(name),
                defaultPic = VALUES(defaultPic),
                priceText = VALUES(priceText),
                recommendReason = VALUES(recommendReason),
                regionName = VALUES(regionName),
                reviewCount = VALUES(reviewCount),
                starScore = VALUES(starScore),
                categoryId = VALUES(categoryId),
                cityId = VALUES(cityId),
                shopPower = VALUES(shopPower),
                shopType = VALUES(shopType),
                myLat = VALUES(myLat),
                myLng = VALUES(myLng),
                updated_at = CURRENT_TIMESTAMP
        """

        # 解析每个景点数据
        for item in attractions_list:
            if item.get('type') != 1:  # 只处理type为1的景点数据
                continue

            shop_info = item.get('shopInfo', {})
            if not shop_info:
                continue

            # 提取所需字段
            shop_uuid = shop_info.get('shopUuid', '')
            category_name = shop_info.get('categoryName', '')
            name = shop_info.get('name', '')
            default_pic = shop_info.get('defaultPic', '')
            price_text = shop_info.get('priceText', '')

            # 提取推荐理由
            recommend_reason_obj = shop_info.get('recommendReason', {})
            recommend_reason = recommend_reason_obj.get('text', '') if recommend_reason_obj else ''

            region_name = shop_info.get('regionName', '')
            review_count = shop_info.get('reviewCount', '')

            # 处理星级评分
            star_score_str = shop_info.get('starScore', '0')
            try:
                star_score = float(star_score_str) if star_score_str else 0.0
            except (ValueError, TypeError):
                star_score = 0.0

            # 其他字段
            category_id = shop_info.get('categoryId', 0)
            city_id = shop_info.get('cityId', 0)
            shop_power = shop_info.get('shopPower', 0)
            shop_type = shop_info.get('shopType', 0)

            # 处理经纬度
            try:
                my_lat = float(shop_info.get('myLat', '0')) if shop_info.get('myLat') else 0.0
                my_lng = float(shop_info.get('myLng', '0')) if shop_info.get('myLng') else 0.0
            except (ValueError, TypeError):
                my_lat = 0.0
                my_lng = 0.0

            # 验证必要字段
            if not shop_uuid or not name:
                print(f"跳过无效数据: shopUuid={shop_uuid}, name={name}")
                continue

            # 准备数据
            values = (
                shop_uuid, category_name, name, default_pic, price_text,
                recommend_reason, region_name, review_count, star_score,
                category_id, city_id, shop_power, shop_type, my_lat, my_lng
            )

            # 执行插入
            try:
                db.execute(sql, values)
                print(f"成功处理景点: {name} (UUID: {shop_uuid})")
            except Exception as e:
                print(f"插入景点数据失败 {name}: {e}")
                continue

        # 提交事务
        db.commit()

    except KeyError as e:
        print(f"JSON数据结构错误，缺少字段: {e}")
    except Exception as e:
        print(f"解析JSON数据时发生错误: {e}")
