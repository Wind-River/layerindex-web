FROM debian:stretch
MAINTAINER Michael Halstead <mhalstead@linuxfoundation.org>

EXPOSE 80
ENV PYTHONUNBUFFERED=1 \
    LANG=en_US.UTF-8 \
    LC_ALL=en_US.UTF-8 \
    LC_CTYPE=en_US.UTF-8

## Uncomment to set proxy ENVVARS within container
#ENV http_proxy http://your.proxy.server:port
#ENV https_proxy https://your.proxy.server:port

ADD requirements.txt /

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      autoconf \
      g++ \
      gcc \
      make \
      python3-pip \
      python3-dev \
      python3-pil \
      python3-mysqldb \
      python3-setuptools \
      netcat-openbsd \
      libjpeg-dev \
      vim git curl locales libmariadbclient-dev \
    && echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen \
    && locale-gen en_US.UTF-8 \
    && update-locale \
    && mkdir /opt/workdir \
    && pip3 install wheel gunicorn \
    && pip3 install -r /requirements.txt \
    && apt-get purge -y autoconf g++ gcc make python3-dev libjpeg-dev libmariadbclient-dev \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && groupadd -g 500 user \
    && useradd --uid=500 --create-home --home-dir /home/user -g user user

ADD --chown 500:500 . /opt/layerindex

# Copy static resouces to static dir so they can be served by nginx
RUN rm -f /opt/layerindex/layerindex/static/admin \
    && cp -r /usr/local/lib/python3.5/dist-packages/django/contrib/admin/static/admin/ \
        /opt/layerindex/layerindex/static/ \
    && rm -f /opt/layerindex/layerindex/static/rest_framework \
    && cp -r /usr/local/lib/python3.5/dist-packages/rest_framework/static/rest_framework/ \
        /opt/layerindex/layerindex/static/ \
    && mkdir /opt/layers && chown -R user:user /opt/layers

ADD docker/updatelayers.sh /opt/updatelayers.sh
ADD docker/migrate.sh /opt/migrate.sh

# Add entrypoint to start celery worker and gnuicorn
ADD docker/entrypoint.sh /entrypoint.sh

# Run gunicorn and celery as unprivileged user
USER user

ENTRYPOINT ["/entrypoint.sh"]
