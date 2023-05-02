# Проект - вьюер отзывов на размеченные отзывы и не размеченные отзывы

## Технологии
tqdm=4.64.1
fastapi
fastapi-pagination=0.9.0
clickhouse-driver=0.2.4
clickhouse-sqlalchemy=0.2.2
SQLAlchemy=1.4.38

## Перед запуском
Добавьте .env в директорию markup_reviews/infra
Заполните его согласно файлу sample.env

## Запуск

Перейдите в папку markup_reviews/infra и выполните:

```docker-compose up --build``` для обычной сборки
и ```docker-compose up --build``` -d для скрытой

Проект доступен по адресу 127.0.0.1:8078

# Доступные URL 
127.0.0.1:8078/redoc или 127.0.0.1:8078/docs