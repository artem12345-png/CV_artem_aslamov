#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import logging.config
from pathlib import Path
from typing import Optional
import sentry_sdk
import yaml
import os
from app.consts import (
    SERVICE_NAME, VERSION, ROOT_DIR, LOGS_DIR)
from typing import TYPE_CHECKING
from app.env_conf import SETTINGS
import MySQLdb
from lxml import etree
import datetime
from app.consts import d_site


if TYPE_CHECKING:
    from MySQLdb.connections import Connection
logger = logging.getLogger(SERVICE_NAME)


def init_logging(use_sentry=True, self_path: Optional[Path] = ROOT_DIR):
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR)

    conf_log_path = self_path / 'logging.yaml'
    conf = yaml.full_load(conf_log_path.open())
    logging.config.dictConfig(conf['logging'])

    if use_sentry and SETTINGS.SENTRY_DSN:
        sentry_sdk.init(dsn=SETTINGS.SENTRY_DSN, release=f"{SERVICE_NAME}@{VERSION}")

    if SETTINGS.DOCKER_HOST:
        sentry_sdk.set_tag('DOCKER_HOST', SETTINGS.DOCKER_HOST)

    sentry_sdk.set_tag('service_name', SERVICE_NAME)
    sentry_sdk.set_tag("maintainer", "aslamov")


def conect() -> 'Connection':
    con = MySQLdb.connect(host=SETTINGS.SQL_HOST, user=SETTINGS.SQL_USER,
                          passwd=SETTINGS.SQL_PASSWORD, db=SETTINGS.SQL_DATABASE,
                          use_unicode=True, charset='utf8', compress=True, autocommit=True)
    return con


def sitemap(site: str, subdomain: str):
    query = f"""select count(id) from pr_goods 
       where idcat > 0 
       and price > 0 
       and isactive = 1 
       and sites like '%{str(site)}%';
               """

    with conect() as conn:
        with conn.cursor() as curs:
            root = etree.Element('sitemapindex', xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")

            url = etree.SubElement(root, "sitemap")
            etree.SubElement(url, "loc").text = f'https://{subdomain}.{d_site.get(site)}.ru/sitemap_firms/{site}/{subdomain}'

            url = etree.SubElement(root, "sitemap")
            etree.SubElement(url, "loc").text = f'https://{subdomain}.{d_site.get(site)}.ru/sitemap_cats/{site}/{subdomain}'

            url = etree.SubElement(root, "sitemap")
            etree.SubElement(url, "loc").text = f'https://{subdomain}.{d_site.get(site)}.ru/sitemap_articles/{site}/{subdomain}'

            url = etree.SubElement(root, "sitemap")
            etree.SubElement(url, "loc").text = f'https://{subdomain}.{d_site.get(site)}.ru/sitemap_news/{site}/{subdomain}'

            curs.execute(query)
            items = curs.fetchall()[0][0]
            n = (items // 50000) + 1
            for i in range(n):
                url = etree.SubElement(root, "sitemap")
                etree.SubElement(url, "loc").text = f'https://{subdomain}.{d_site.get(site)}.ru/sitemap_goods/{site}/{subdomain}/{i}'
            obj_xml = etree.tostring(root, pretty_print=True, encoding='utf-8', xml_declaration=True)

    return obj_xml


def goods(site: str, subdomain: str, quantity: int):

    query = f"""
        select id from pr_goods 
        where idcat > 0 
        and price > 0 
        and isactive = 1 
        and sites 
        like '%{str(site)}%' order by title  
        limit 50000 OFFSET {quantity * 50000};
                """

    with conect() as conn:
        with conn.cursor() as curs:
            curs.execute(query)
            root = etree.Element('urlset', xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
            for string in curs:
                url = etree.SubElement(root, "url")
                etree.SubElement(url, "loc").text = f'https://{subdomain}.{d_site.get(site)}.ru/good/{string[0]}'
                etree.SubElement(url, "changefreq").text = 'weekly'
                etree.SubElement(url, "priority").text = '1'
                etree.SubElement(url, "lastmod").text = str(datetime.date.today())


    obj_xml = etree.tostring(root, pretty_print=True, encoding='utf-8', xml_declaration=True)

    return obj_xml


def cats(site: str, subdomain: str):
    query = f"""
        select c.id from pr_catalog c
        right join ep_cat_sites_all a on c.id=a.idcat
        where c.level != 1
        and c.isactive=1 and
        c.num_img != 0 and 
        a.idsite = '{str(site)}' and 
        a.no_yml is null
        order by idleft
                """

    with conect() as conn:
        with conn.cursor() as curs:
            curs.execute(query)
            root = etree.Element('urlset', xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
            url = etree.SubElement(root, "url")
            etree.SubElement(url, "loc").text = f'https://{subdomain}.{d_site.get(site)}.ru/'
            etree.SubElement(url, "changefreq").text = 'daily'
            etree.SubElement(url, "priority").text = '1'
            for string in curs:
                url = etree.SubElement(root, "url")
                etree.SubElement(url, "loc").text = f'https://{subdomain}.{d_site.get(site)}.ru/catalog/{string[0]}'
                etree.SubElement(url, "changefreq").text = 'daily'
                etree.SubElement(url, "priority").text = '1'
                etree.SubElement(url, "lastmod").text = str(datetime.date.today())

    obj_xml = etree.tostring(root, pretty_print=True, encoding='utf-8', xml_declaration=True)

    return obj_xml


def articles(site: str, subdomain: str):

    query = f"""
        select a.iditem,a.num 
        from ep_articles a 
        inner join ep_cat_sites_all c 
        on a.iditem=c.idcat 
        WHERE item='cat' 
        and idsite='{str(site)}'
        and is_view = 1;
                """

    with conect() as conn:
        with conn.cursor() as curs:
            curs.execute(query)
            root = etree.Element('urlset', xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
            for string in curs:
                url = etree.SubElement(root, "url")
                etree.SubElement(url,
                                 "loc").text = f'https://{subdomain}.{d_site.get(site)}.ru/feature/cat/{string[0]}/{string[1]}'
                etree.SubElement(url, "priority").text = '0.8'
                etree.SubElement(url, "lastmod").text = str(datetime.date.today())
                etree.SubElement(url, "changefreq").text = 'daily'

    obj_xml = etree.tostring(root, pretty_print=True, encoding='utf-8', xml_declaration=True)

    return obj_xml


def firms(site: str, subdomain: str):

    query = f"""
        select id from pr_firm 
        where sites 
        like '%{str(site)}%' 
        order by title;
                """

    with conect() as conn:
        with conn.cursor() as curs:
            curs.execute(query)
            root = etree.Element('urlset', xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
            for string in curs:
                url = etree.SubElement(root, "url")
                etree.SubElement(url, "loc").text = f'https://{subdomain}.{d_site.get(site)}.ru/firm/{string[0]}'
                etree.SubElement(url, "changefreq").text = 'daily'
                etree.SubElement(url, "priority").text = '1'
                etree.SubElement(url, "lastmod").text = str(datetime.date.today())

    obj_xml = etree.tostring(root, pretty_print=True, encoding='utf-8', xml_declaration=True)

    return obj_xml


def news(site: str, subdomain: str):

    query = f"""
      select id from ep_news
    where is_show = 1;
                """

    with conect() as conn:
        with conn.cursor() as curs:
            curs.execute(query)
            root = etree.Element('urlset', xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
            url = etree.SubElement(root, "url")
            etree.SubElement(url, "loc").text = f'https://{subdomain}.{d_site.get(site)}.ru/news/'
            etree.SubElement(url, "changefreq").text = 'daily'
            etree.SubElement(url, "priority").text = '1'
            for string in curs:
                url = etree.SubElement(root, "url")
                etree.SubElement(url, "loc").text = f'https://{subdomain}.{d_site.get(site)}.ru/news_one/{string[0]}'
                etree.SubElement(url, "changefreq").text = 'daily'
                etree.SubElement(url, "priority").text = '1'
                etree.SubElement(url, "lastmod").text = str(datetime.date.today())

    obj_xml = etree.tostring(root, pretty_print=True, encoding='utf-8', xml_declaration=True)

    return obj_xml