from config import db
from pymysql import connect


class Mysql:
    def __init__(self):
        self.conn = connect(
            host=db['host'],
            port=db['port'],
            user=db['user'],
            password=db['pass'],
            database=db['db_name']
        )
        self.cur = self.conn.cursor()

    def create_location_table_if_not_exits(self):
        self.cur.execute('Create table if not exists location('
                         'id int PRIMARY KEY AUTO_INCREMENT NOT NULL,'
                         'location_id int,'
                         'location_name varchar(255),'
                         'city varchar(255),'
                         'address Text,'
                         'category varchar(255)'
                         ')')
        self.conn.commit()

    def create_post_table_if_not_exists(self):
        self.cur.execute('Create table if not exists posts('
                         'id int PRIMARY KEY AUTO_INCREMENT NOT NULL,'
                         'code varchar(255),'
                         'post_link Text,'
                         'media_link Text,'
                         'user_name varchar(255),'
                         'media_type varchar(255),'
                         'caption Text,'
                         'comment_count int,'
                         'like_count int,'
                         'geo_id int,'
                         'FOREIGN KEY (geo_id) REFERENCES location(id)'
                         ')')
        self.conn.commit()

    def insert_location(self, location):
        self.cur.execute('Insert into location(location_id, location_name, city, address, category) '
                         'values (%s,%s,%s,%s,%s)',
                         (location['id'], location['name'], location['city'], location['address'],
                          location['category']))
        self.conn.commit()

    def insert_posts(self, post):
        self.cur.execute('Insert into posts(code, post_link, media_link, user_name, media_type,'
                         ' caption, comment_count, like_count, geo_id) '
                         'values (%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                         (post['code'], post['post_link'], post['media_link'], post['user_name'],
                          post['media_type'], post['caption'], post['comment_count'],
                          post['like_count'], post['geo_id']))
        self.conn.commit()

    def exists_location(self, location_id):
        self.cur.execute(f"Select count(*) from location where location_id='{location_id}'")
        return self.cur.fetchone()[0] > 0

    def exists_post(self, code):
        self.cur.execute(f"Select count(*) from posts where code = '{code}'")
        return self.cur.fetchone()[0] > 0

    def get_geo_id_location_id(self, location_id):
        self.cur.execute(f"Select id from location where location_id='{location_id}'")
        return self.cur.fetchone()[0]
