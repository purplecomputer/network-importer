ARG PYTHON_VER="3.7"

FROM python:${PYTHON_VER}

RUN pip install --upgrade pip \
  && pip install poetry

WORKDIR /local

RUN poetry config virtualenvs.create false \
  && poetry install --no-interaction --no-ansi --no-root

COPY . /local
RUN poetry install --no-interaction --no-ansi

WORKDIR /claner
COPY nautobotcleaner/. /cleaner

