FROM python:3.10

COPY ./requirements.txt .
RUN pip install -r requirements.txt

COPY fonts ./fonts
COPY oryxbot ./oryxbot
COPY test ./test
COPY setup.py ./

RUN pip install .
RUN pytest ./test

ENTRYPOINT ["python", "./oryxbot/main.py"]
