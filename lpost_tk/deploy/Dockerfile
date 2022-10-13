FROM git3.promsoft.ru:5005/epool/lpost_tk:base

COPY app ./app
#COPY static ./static
COPY *.py ./

COPY deploy/logging_deploy.yaml ./logging.yaml

RUN mkdir logs

RUN touch ./.env

#CMD ["python", "start.py"]