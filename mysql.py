import pymysql
from pymysql import MySQLError, cursors


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
            self.connection = pymysql.connect(
                host='47.122.123.221',  # 数据库主机地址
                port=3306,
                user='root',  # 数据库用户名
                password='cs8Gz7dKHDyhAPaz',  # 数据库密码
                database='dianping_spiders',  # 数据库名
                charset='utf8mb4',
            )
            self.cursor = self.connection.cursor(cursor=cursors.DictCursor)
        except MySQLError as e:
            print(f"连接失败: {e}")

    def disconnect(self):
        """断开与MySQL数据库的连接"""
        if self.connection and self.connection.open:
            self.cursor.close()
            self.connection.close()
            print("已断开数据库连接")

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
