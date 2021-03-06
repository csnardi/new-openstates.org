FROM python:3.7-slim
LABEL maintainer="James Turk <james@openstates.org>"

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONIOENCODING 'utf-8'
ENV LANG 'C.UTF-8'

RUN BUILD_DEPS=" \
      python3-dev \
      git \
      libpq-dev \
      libgeos-dev \
      libgdal-dev \
      wget \
      postgresql-client \
    " \
    && apt-get update && apt-get install -y --no-install-recommends $BUILD_DEPS

ADD . /code/
WORKDIR /code/

RUN wget https://deb.nodesource.com/setup_10.x -O nodesource.sh \
    && bash nodesource.sh \
    && apt install -y nodejs \
    && npm ci \
    && npm run build

RUN set -ex \
    && pip install poetry \
    && poetry install

EXPOSE 8000
STOPSIGNAL SIGINT
ENTRYPOINT ["poetry", "run", "./manage.py"]
CMD ["runserver", "0.0.0.0:8000"]
