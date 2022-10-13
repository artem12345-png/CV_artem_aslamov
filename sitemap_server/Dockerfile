FROM python:3.9

# Setting Moscow time-zone
ENV TZ=Europe/Moscow
# hadolint ignore=DL3008
RUN ln -snf "/usr/share/zoneinfo/${TZ}" /etc/localtime && \
    echo "${TZ}" > /etc/timezone && \
    apt-get install --no-install-recommends -y tzdata default-libmysqlclient-dev && \
    dpkg-reconfigure --frontend noninteractive tzdata

WORKDIR /opt/sitemap_server

# Устанавливаем пакеты Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Создаем папку с логами
RUN mkdir logs
COPY logging.yaml .

# Копируем файлы в текущую папку
COPY app app
COPY server.py .




CMD ["python", "server.py"]
