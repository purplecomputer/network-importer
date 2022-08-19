ARG PYTHON_VER="3.7"

FROM python:${PYTHON_VER}

RUN pip install --upgrade pip \
  && pip install poetry

WORKDIR /local
COPY pyproject.toml poetry.lock /local/
COPY NautobotCleaner/config.py /local/
COPY NautobotCleaner/importdeviceroutes.py /local/
COPY NautobotCleaner/importdevicevlans.py /local/
COPY NautobotCleaner/main.py /local/
COPY NautobotCleaner/list_of_devices.txt /local/

RUN poetry config virtualenvs.create false \
  && poetry install --no-interaction --no-ansi --no-root \
  && pip install python-dotenv

COPY . /local
RUN poetry install --no-interaction --no-ansi

