Мини-сервис, запускает скрипт загрузки Нграмм в базу данных, выдает результаты по Review.

# Перед запуском:
создать файл .env в директории проекта:
```.result_dicts/settings/.env```
Указать переменные:
DATABASE_URL_CH
DATABASE_URL_POSTGRES

# Запуск:
Чтобы запустить FastApi из папки с main.py запустить:
python main.py --reload
## Документация Redoc;
http://localhost:8111/redoc

## Запустить скрипт загрузки Ngram:
http://localhost:8111/load_data_in_database/<номер_домена>/<lang_ru_or_en>

# Локальный URL http://localhost:8111

# База данных - ClickHouse
## Параметры таблицы texts:
MergeTree PARTITION BY toYYYYMM(date) ORDER BY (domain_id, id) SAMPLE BY id

## Параметры таблиц, разделенных по доменам:
ENGINE = MergeTree
PARTITION BY domain_id
ORDER BY (org_id, id)
SAMPLE BY id;
SETTINGS data_type_default_nullable = 1;

ИНДЕКС ТАБЛИЦ:
 ngrambf_v1(3, 256, 2, 0) GRANULARITY 2

 Перед запуском добавьте в .env DATABASE_URL_CH с url адресом базы данных по всему проекту.