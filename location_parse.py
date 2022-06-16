import json

from sources import locations
from database import Mysql
import re
import requests as request
from transliterate import translit
from translate import Translator


def has_cyrillic(text):
    return bool(re.search('[а-яА-Я]', text))


def ru_to_eng(country):
    return Translator(from_lang='russian', to_lang='english').translate(country)


def generator_of_location_data(location):
    data = {
        'id': location['location_id'],
        'name': location['name'],
        'city': location['location_city'],
        'address': location['location_address'],
        'category': location['category']
    }
    return data


def generator_of_post_data(post, geo_id):
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
            'code': code,
            'post_link': post_link,
            'media_link': media_link,
            'user_name': post['user']['username'],
            'media_type': media_type,
            'caption': caption,
            'comment_count': comment_count,
            'like_count': likes_count,
            'geo_id': geo_id
        }
        return data
    except Exception as e:
        print(e)


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
        self.db.create_post_table_if_not_exists()
        for location in locations:
            url = self.__get_url(location)
            if url != self.location_error and url != self.city_error and url != self.country_error:
                response = request.get(url, params={'__a': 1}).json()
                location_data = generator_of_location_data(response['native_location_data']['location_info'])
                if not self.db.exists_location(location_data['id']):
                    self.db.insert_location(location_data)

                geo_id = self.db.get_geo_id_location_id(location_data['id'])
                ranked = response['native_location_data']['ranked']['sections']
                for section in ranked:
                    for media in section['layout_content']['medias']:
                        post_data = generator_of_post_data(media['media'], geo_id)
                        if not self.db.exists_post(post_data['code']):
                            self.db.insert_posts(post_data)
            else:
                print(url)
        print('Locations and posts successfully inserted to table!')
