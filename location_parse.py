import datetime

from sources import locations
from database import Mysql
import re
import requests as request
from translate import Translator


def has_cyrillic(text):
    return bool(re.search('[а-яА-Я]', text))


def ru_to_eng(country):
    return Translator(from_lang='russian', to_lang='english').translate(country)


def generator_of_location_data(location):
    try:
        data = {
            'id': location['location_id'],
            'name': location['name'],
            'city': location['location_city'],
            'address': location['location_address'],
            'category': location['category']
        }
        return data
    except Exception as e:
        f = open('log.txt', 'w')
        error_info = str(e) + '| ' + str(datetime.date.today()) + '\n'
        f.write(error_info)
        f.close()
        pass


def generator_owner_data(owner):
    try:
        data = {
            'id': owner['pk'],
            'user_name': owner['username'],
            'full_name': owner['full_name'],
            'profile_picture': owner['profile_pic_url'],
            'profile_link': 'https://www.instagram.com/' + owner['username'] + '/'
        }
        return data
    except Exception as e:
        f = open('log.txt', 'w')
        error_info = str(e) + '| ' + str(datetime.date.today()) + '\n'
        f.write(error_info)
        f.close()
        pass


def generator_of_post_data(post, geo_id, res_id):
    try:
        m_type = post['media_type']
        code = post['code']
        post_link = 'https://www.instagram.com/p/' + code + '/'
        media_link = ''
        media_type = ''
        caption = ''
        comment_count = 0
        likes_count = 0
        if post['caption'] is not None:
            caption = post['caption']['text']
        if 'comment_count' in post.keys():
            comment_count = post['comment_count']
        if 'like_count' in post.keys():
            likes_count = post['like_count']

        if m_type == 8:
            media_type = 'album'
            album = post['carousel_media']
            for album_media in album:
                media = album_media
                if media['media_type'] == 1:
                    media_link += media['image_versions2']['candidates'][0]['url'] + ' | '
                elif media['media_type'] == 2:
                    media_link += media['video_versions'][0]['url']
        elif m_type == 1:
            media_type = 'image'
            media_link = post['image_versions2']['candidates'][0]['url']
        elif m_type == 2:
            media_type = 'video'
            media_link = post['video_versions'][0]['url']

        data = {
            'id': post['pk'],
            'code': code,
            'post_link': post_link,
            'media_link': media_link,
            'media_type': media_type,
            'caption': caption,
            'comment_count': comment_count,
            'like_count': likes_count,
            'res_id': res_id,
            'geo_id': geo_id
        }
        return data
    except Exception as e:
        f = open('log.txt', 'w')
        error_info = str(e) + '| ' + str(datetime.date.today()) + '/n'
        f.write(error_info)
        f.close()
        pass


class Parser:
    def __init__(self):
        self.locations = locations
        self.db = Mysql()
        self.country_status = "country"
        self.city_status = "city"
        self.location_status = "location"
        self.city_error = 'city_error'
        self.country_error = 'country_error'
        self.location_error = 'location_error'
        self.base_url = "https://www.instagram.com/explore/locations/"

    def __get_id(self, status, url, name):
        page = 1
        response = request.get(url, params={'page': page, '__a': 1}).json()
        geo_id = ''
        while response != {}:

            if status == self.country_status:
                response_list = response['country_list']
            elif status == self.city_status:
                response_list = response['city_list']
            else:
                response_list = response['location_list']

            if name in str(response_list):
                for geo in response_list:
                    if str(geo['name']).lower() == str(name).lower():
                        geo_id = geo['id']
                        break
            page += 1
            response = request.get(url, params={'page': page, '__a': 1}).json()

        return geo_id

    def __get_url(self, location):
        country = location['country']
        city = location['city']
        place = location['location']

        if has_cyrillic(country):
            country = ru_to_eng(country)
        if has_cyrillic(city):
            city = ru_to_eng(city)

        country_id = self.__get_id(self.country_status, self.base_url, country)
        if country_id != '':
            city_url = self.base_url + country_id + '/'
            city_id = self.__get_id(self.city_status, city_url, city)
            if city_id != '':
                location_url = self.base_url + city_id + '/'
                location_id = self.__get_id(self.location_status, location_url, place)
                if location_id != '':
                    return self.base_url + location_id + '/'
                else:
                    return self.location_error
            else:
                return self.city_error
        else:
            return self.country_error

    def parse(self):
        self.db.create_location_table_if_not_exits()
        self.db.create_owner_table_if_not_exists()
        self.db.create_post_table_if_not_exists()

        for location in locations:
            try:
                url = self.__get_url(location)
                if url != self.location_error and url != self.city_error and url != self.country_error:
                    response = request.get(url, params={'__a': 1}).json()
                    location_data = generator_of_location_data(response['native_location_data']['location_info'])
                    if not self.db.exists_location(location_data['id']):
                        self.db.insert_location(location_data)

                    geo_id = self.db.get_geo_id_by_location_id(location_data['id'])
                    ranked = response['native_location_data']['ranked']['sections']
                    for section in ranked:
                        try:
                            for media in section['layout_content']['medias']:
                                owner = media['media']['user']
                                if not self.db.exists_owner(owner['pk']):
                                    self.db.insert_owner(generator_owner_data(owner))

                                owner_id = self.db.get_owner_id_by_owner_pk(owner['pk'])
                                post_data = generator_of_post_data(media['media'], geo_id, owner_id)
                                if not self.db.exists_post(post_data['code']):
                                    self.db.insert_posts(post_data)
                        except Exception as e:
                            f = open('log.txt', 'w')
                            error_info = str(e) + '| ' + str(datetime.date.today()) + ' | ' + location + '\n'
                            f.write(error_info)
                            f.close()
                            pass
                else:
                    print(url)
            except Exception as e:
                f = open('log.txt', 'w')
                error_info = str(e) + '| ' + str(datetime.date.today()) + ' | ' + location + '\n'
                f.write(error_info)
                f.close()
                pass
        print('Locations and posts successfully inserted to table!')
