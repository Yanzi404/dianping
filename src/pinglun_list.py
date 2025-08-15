import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from mitmproxy import http

from mysql import MySQLDatabase

"""
通过mitmproxy拦截解析请求，获取大众点评评论
"""

# 确保保存目录存在
SAVE_DIR = Path("../log/dianping_responses")
SAVE_DIR.mkdir(parents=True,exist_ok=True)

# 常量定义
TARGET_URL_PATTERN = "m.dianping.com/ugc/review/reviewlist"
SUCCESS_STATUS_CODE = 200

def requests(flow: http.HTTPFlow) -> None:
    pass

def response(flow: http.HTTPFlow) -> None:
    """处理HTTP响应，拦截大众点评评论数据"""
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
            
        # 获取请求参数

        shop_uuid= flow.request.query.get('shopId')
        if not shop_uuid:
            shop_uuid = flow.request.query.get('mtsiReferrer')[-16:]

        print(shop_uuid)
        offset = flow.request.query.get('offset')
        
        if not shop_uuid or not offset:
            print("缺少必要参数: shopUuid 或 offset")
            return
            
        # 保存响应文件
        if not _save_response_file(flow, shop_uuid, offset):
            return
            
        # 解析并保存到数据库
        parse_json(response_json, shop_uuid, offset)
        
    except json.JSONDecodeError:
        print("响应内容不是有效的JSON格式")
    except Exception as e:
        print(f"处理响应时发生错误: {e}")


def _save_response_file(flow: http.HTTPFlow, shop_uuid: str, offset: str) -> bool:
    """保存响应文件到本地"""
    try:
        # 创建以shopUuid命名的子目录
        shop_dir = SAVE_DIR / shop_uuid
        shop_dir.mkdir(parents=True, exist_ok=True)

        # 构建保存文件名（使用时间戳和URL部分作为文件名）
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{timestamp}_{offset}.json"

        # 保存响应内容
        save_path = shop_dir / filename
        with open(save_path, "wb") as f:
            f.write(flow.response.content)
        return True
        
    except Exception as e:
        print(f"保存文件时发生错误: {e}")
        return False


def parse_json(response_data: Dict[str, Any], shop_uuid: str, offset: str) -> None:
    """解析JSON数据并保存到数据库"""
    try:
        db = MySQLDatabase()
        review_list = response_data['reviewInfo']['reviewListInfo']['reviewList']
        
        for review in review_list:
            # 提取评论数据
            review_id = review.get('reviewId')
            user_id = review.get('userId')
            add_time = review.get('addTime')
            star = review.get('star')
            
            # 安全提取评论文本
            text = _extract_review_text(review)
            
            # 提取图片URL
            pics = _extract_review_pics(review)
            
            # reviewId, shopUuid, userId, addTime, text, pics, star, offset
            sql = """
                INSERT INTO reviews(reviewId, shopUuid, userId, addTime, text, pics, star, offset)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            db.execute(sql, (review_id, shop_uuid, user_id, add_time, text, pics, star, offset))
        
        db.commit()
        print(f'当前页：{offset}')
        
    except KeyError as e:
        print(f"JSON数据结构错误，缺少字段: {e}")
    except Exception as e:
        print(f"解析JSON数据时发生错误: {e}")


def _extract_review_text(review: Dict[str, Any]) -> str:
    """安全提取评论文本"""
    try:
        return review['reviewBody']['children'][0]['children'][0]['text']
    except (KeyError, IndexError, TypeError):
        return ""


def _extract_review_pics(review: Dict[str, Any]) -> str:
    """提取评论图片URL"""
    try:
        bigurls = []
        for review_pic in review.get('reviewPics', []):
            if 'bigurl' in review_pic:
                bigurls.append(review_pic['bigurl'])
        return ','.join(bigurls)
    except (KeyError, TypeError):
        return ""