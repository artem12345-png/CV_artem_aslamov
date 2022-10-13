FROM python:3.10.5-slim-bullseye

ENV TZ=Europe/Moscow
RUN ln -snf "/usr/share/zoneinfo/${TZ}" /etc/localtime \
    && echo "${TZ}" > /etc/timezone \
    && dpkg-reconfigure --frontend noninteractive tzdata

#RUN DEBIAN_FRONTEND=noninteractive apt-get update && apt-get install \
#    -y --no-install-recommends \
#    python3-dev gcc && rm -rf /var/lib/apt/lists/*

WORKDIR /lpost_tk

COPY requirements.txt .
RUN pip install -U pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt
