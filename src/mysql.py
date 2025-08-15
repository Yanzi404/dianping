import pymysql
from pymysql import MySQLError, cursors
from config import DatabaseConfig


class MySQLDatabase:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MySQLDatabase, cls).__new__(cls)
            cls._instance.connection = None
            cls._instance.cursor = None
            cls._instance.__connect()
        return cls._instance

    def __connect(self):
        """连接到MySQL数据库"""
        try:
            # 从配置文件获取数据库连接信息
            db_config = DatabaseConfig.get_mysql_config()
            
            self.connection = pymysql.connect(**db_config)
            self.cursor = self.connection.cursor(cursor=cursors.DictCursor)
        except MySQLError as e:
            print(f"连接失败: {e}")

    def disconnect(self):
        """断开与MySQL数据库的连接"""
        if self.connection and self.connection.open:
            self.cursor.close()
            self.connection.close()
            print("已断开数据库连接")
    
    def close(self):
        """关闭数据库连接（与disconnect方法相同）"""
        self.disconnect()

    def commit(self):
        """提交事务"""
        if self.connection and self.connection.open:
            self.connection.commit()
            print("已提交事务")

    def execute(self, query,args):
        """执行SQL"""
        try:
            self.cursor.execute(query, args)
        except MySQLError as e:
            print(f"执行失败: {e}")
