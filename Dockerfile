ARG PYTHON_VER="3.7"

FROM python:${PYTHON_VER}

RUN pip install --upgrade pip \
  && pip install poetry

WORKDIR /local
COPY pyproject.toml poetry.lock /local/
COPY nautobotcleaner/config.py /local/
COPY nautobotcleaner/importdeviceroutes.py /local/
COPY nautobotcleaner/importdevicevlans.py /local/
COPY nautobotcleaner/import_cid.py /local/
COPY nautobotcleaner/main.py /local/
COPY nautobotcleaner/list_of_devices.txt /local/

RUN poetry config virtualenvs.create false \
  && poetry install --no-interaction --no-ansi --no-root \
  && pip install python-dotenv gevent \
  && mkdir MAINRUN

COPY . /local
RUN poetry install --no-interaction --no-ansi

ENTRYPOINT ["python"]
