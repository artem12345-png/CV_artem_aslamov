from pymongo import MongoClient
import json
from app.env_conf import SETTINGS
import re
import httpx
from functools import cache
import os.path
from app.tools import logger
from app.tools import init_logging
import glob

client = MongoClient(SETTINGS.CONNECTION)
db = client.get_database()
query = {'crm.ACTIVE': 'Y', 'crm.IBLOCK_SECTIONS.0.ID': {'$nin': ['1890']}}
PATH_FILE = "site/tovars.json"
PUBLIC_IMAGES_URL = ""
GET_CHILDREN = f"{SETTINGS.URL}disk.folder.getchildren?id="
GET_FILE = f"{SETTINGS.URL}disk.file.get?id="
list_names = list()

# TODO https://jmespath.org/
def get_value(v, default=''):
    if v != v:
        return default

    if v is None:
        return default
    
    return v


def parse_property(obj, qwery, default=''):
    if obj is None:
        return default
    if '.' in qwery:
        key, subqwery = qwery.split('.', 1)
        if key in obj:
            return get_value(parse_property(obj[key], subqwery, default))
        else:
            return default
    if isinstance(obj, dict):
        return get_value(obj.get(qwery, default))
    else:
        return get_value(obj, default)


@cache
def get_cached(parameter, url_template):
    url = f"{url_template}{parameter}"
    r = httpx.get(url)
    return r.json()


def save_file(file_name, file):
    logger.info('saving photo...')
    PATH_SAVE = f"site/images/{file_name}"
    url = file['DOWNLOAD_URL']
    with open(PATH_SAVE, 'wb') as f:
        f.write(httpx.get(url).content)


def check_file(file_name, file):
    list_names.append(file_name)
    logger.info('checking photo...')
    if not os.path.isfile(f"site/images/{file_name}"):
        save_file(file_name, file)


def delete():
    list_names_serv = [x.split('/')[-1] for x in glob.glob('site/images/*.*')]
    delete_list = set(list_names_serv) - set(list_names)
    for item in delete_list:
        os.remove(f'site/images/{item}')


def get_photo(tovar: dict) -> list:
    result = list()
    if link := parse_property(tovar, "crm.PROPERTY_photo_object", ''):
        logger.info('got link from MongoBD')
        folder_pattern = re.compile(r"folderId=\d+")
        folderid = folder_pattern.findall(link)[0]
        if folderid:
            _, folderid = folderid.split("=")

        folder = get_cached(folderid, GET_CHILDREN)['result']
        if folder:
            logger.info('got link on subfolders')
        for subfolder in folder:
            name_subfolder = subfolder['NAME']
            subfolder_id = subfolder['ID']

            files = get_cached(subfolder_id, GET_CHILDREN).get('result')
            if files:
                images = {
                    name_subfolder: []
                }
                for file in files:
                    extension = file['NAME'].split('.')[-1]
                    photo_id = get_cached(file['ID'], GET_FILE)['result']['ID']
                    file_name = f"{photo_id}.{extension}"
                    image_link = f"""{PUBLIC_IMAGES_URL}{file_name}"""
                    image_desc = {
                        'title': f"{file['NAME']}",
                        'link': f"{image_link}"
                    }
                    check_file(file_name, file)
                    images[name_subfolder].append(image_desc)
                result.append(images)
    return result


def get_json(tovars, bd_objects):
    result = []
    logger.info('doing dict for every one tovar in list...')
    for tovar in tovars:
        row = {'object_id': parse_property(tovar, 'crm.PROPERTY_OBJECT_ID', '')}
        row_object = bd_objects.get(row['object_id'], dict())
        row['floor'] = parse_property(tovar, 'crm.PROPERTY_FLOOR', 'Первый этаж')
        row['floors'] = parse_property(tovar, 'crm.PROPERTY_FLOORS', '1')
        row['is_rented'] = parse_property(tovar, 'crm.PROPERTY_IS_RENTED.VALUE', '')
        row['square'] = parse_property(tovar, 'crm.PROPERTY_SQUARE', 0)
        row['arendator_bussiness'] = parse_property(tovar, 'crm.PROPERTY_ARENDATOR_BUSSINESS', '')
        row['price_all'] = parse_property(tovar, 'crm.PROPERTY_PRICE_ALL', 0)
        row['number'] = parse_property(tovar, 'crm.PROPERTY_NUMBER', 0)
        row['price_sq'] = parse_property(tovar, 'crm.PROPERTY_PRICE_SQ', 0)
        row['water'] = parse_property(tovar, 'crm.PROPERTY_WATER.VALUE', '')
        row['plumbing'] = parse_property(tovar, 'crm.PROPERTY_PLUMBING.VALUE', '')
        row['heating'] = parse_property(tovar, 'crm.PROPERTY_HEATING.VALUE', '')
        row['full_power'] = parse_property(tovar, 'crm.PROPERTY_FULL_POWER', '')
        row['tor_type'] = parse_property(tovar, 'crm.PROPERTY_TOR_TYPE.VALUE', '')
        row['entrance_object'] = parse_property(tovar, 'crm.PROPERTY_entrance_object', '')
        row['ads_place_object'] = parse_property(tovar, 'crm.PROPERTY_ads_place_object', '')
        row['google_price_id'] = parse_property(tovar, 'crm.PROPERTY_google_price_id', '')
        row['coordinates'] = parse_property(tovar, 'crm.PROPERTY_PLACE', '')
        row['site_business_conditions_description'] = parse_property(row_object, 'site_business_conditions_description', '')
        row['site_zagolovok_object'] = parse_property(row_object, 'site_zagolovok_object', '')
        row['conception'] = parse_property(row_object, 'conception', '')
        row['site_podzagolovok_object'] = parse_property(row_object, 'site_podzagolovok_object', '')
        row['site_zagolovok2_object'] = parse_property(row_object, 'site_zagolovok2_object', '')
        row['2gis'] = parse_property(row_object, '2gis', '')
        row['town'] = parse_property(tovar, 'crm.PROPERTY_TOWN.VALUE', '')
        row['district'] = parse_property(tovar, 'crm.PROPERTY_DISTRICT.VALUE', '')
        row['designation'] = parse_property(tovar, 'crm.PROPERTY_DESIGNATION.VALUE', '')
        row['site_location_title'] = parse_property(tovar, 'crm.PROPERTY_site_location_title', '')
        row['site_location_description'] = parse_property(tovar, 'crm.PROPERTY_site_location_description', '')
        row['address'] = parse_property(tovar, 'crm.PROPERTY_ADDRESS_FOR_HUMAN', '')
        row['opisanie_premises_site'] = parse_property(tovar, 'crm.PROPERTY_opisanie_premises_site', '')
        row['photo_object'] = get_photo(tovar)
        result.append(row)
    logger.info('return list with dicts')
    return result


def main():
    init_logging(use_sentry=True)
    logger.info('starting programm')
    tovars = list(db.tovars.find(query))
    if tovars:
        logger.info('got tovars from Mongodb')
    else:
        logger.info("couldn't get tovars from bd")

    bd_objects = {str(v['_id']): v for v in db.bd_objects.find({})}
    result = get_json(tovars=tovars, bd_objects=bd_objects)
    if result:
        logger.info('get json')
    else:
        logger.info("couldn't get json from bd")
    delete()
    with open(PATH_FILE, 'w') as f:
        json.dump(result, f, ensure_ascii=False, indent=' ')
        logger.info('saved file')


if __name__ == '__main__':
    main()
