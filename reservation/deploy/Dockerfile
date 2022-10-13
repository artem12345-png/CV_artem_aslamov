FROM python:3.10

# Устанавливаем московское время
ENV TZ=Europe/Moscow
# hadolint ignore=DL3008
RUN ln -snf "/usr/share/zoneinfo/${TZ}" /etc/localtime && \
    echo "${TZ}" > /etc/timezone && \
    apt-get install --no-install-recommends -y default-libmysqlclient-dev tzdata && \
    dpkg-reconfigure --frontend noninteractive tzdata


# INSTALL TOOLS
# hadolint ignore=DL3008,DL3009
RUN apt-get update \
    && apt-get -y install unzip libaio-dev --no-install-recommends \
    && mkdir -p /opt/reservation/api \
    && apt-get clean  \
    && rm -rf /var/lib/apt/lists/*

COPY deploy/oracle-instantclient/ /opt/reservation
COPY deploy/install-instantclient.sh /opt/reservation

WORKDIR /opt/reservation

ENV ORACLE_HOME=/opt/oracle/instantclient
ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$ORACLE_HOME

ENV OCI_HOME=/opt/oracle/instantclient
ENV OCI_LIB_DIR=/opt/oracle/instantclient
ENV OCI_INCLUDE_DIR=/opt/oracle/instantclient/sdk/include

RUN chmod +x ./install-instantclient.sh
RUN ./install-instantclient.sh

COPY requirements.txt /opt/reservation
# INSTALL INSTANTCLIENT AND DEPENDENCIES
RUN pip install -r requirements.txt

# Создаем папку с логами
RUN mkdir logs
COPY deploy/logging.yaml /opt/reservation/logging.yaml
COPY . .
