FROM python:3.10-buster

# create the appropriate directories
ENV APP_HOME=/home/app/web/
RUN mkdir -p $APP_HOME
RUN mkdir -p $APP_HOME/staticfiles && mkdir -p $APP_HOME/media && mkdir -p $APP_HOME/logging


RUN apt-get -y update && apt-get -y install \
    curl \
    libpq-dev \
    gcc \
    gettext \
    git \
    procps
RUN curl -fsSL https://deb.nodesource.com/setup_14.x | bash -
RUN apt-get update && apt-get install -y netcat nodejs zip unzip && npm install -g yarn
RUN addgroup --system app && adduser --system app --ingroup app
COPY wait-for-it.sh /usr/bin/wait-for-it.sh

ENV POETRY_VERSION=1.5.0
RUN pip install -U "poetry==$POETRY_VERSION"
RUN pip install -U pip celery setuptools wheel


WORKDIR $APP_HOME

COPY pyproject.toml poetry.lock $APP_HOME
RUN poetry config virtualenvs.create false && poetry install


COPY . $APP_HOME
#RUN #chown -R -L app:app $APP_HOME

# change to the app user - security reason
#USER app
# run entrypoint.sh
ENTRYPOINT ["/home/app/web/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--access-logfile", "-", "--workers", "4", "--bind", ":8000"]

#future.
#ARG USER_ID
#ARG GROUP_ID
#
#RUN if [ "$ENV_ROLE" = "production" ]; then \
#        chown -R -L app:app $APP_HOME && usermod -aG sudo app && echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers; \
#    else \
#        if [ -n "$USER_ID" ] && [ -n "$GROUP_ID" ]; then \
#            usermod -u $USER_ID app; \
#            groupmod -g $GROUP_ID app; \
#        fi; \
#    fi
