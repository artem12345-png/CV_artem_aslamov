FROM akhmetov/python-telegram

# Устанавливаем пакеты Python
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY test.py .
CMD [ "python", "test.py" ]
