import os
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

class DatabaseConfig:
    """数据库配置类"""
    
    @staticmethod
    def get_mysql_config():
        """获取MySQL数据库配置"""
        return {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'user': os.getenv('DB_USER', 'root'),
            'password': os.getenv('DB_PASSWORD', ''),
            'database': os.getenv('DB_NAME', 'dianping_spiders'),
            'charset': os.getenv('DB_CHARSET', 'utf8mb4')
        }