FROM buildpack-deps:latest
MAINTAINER Michael Halstead <mhalstead@linuxfoundation.org>

EXPOSE 80
ENV PYTHONUNBUFFERED 1
## Uncomment to set proxy ENVVARS within container
#ENV http_proxy http://your.proxy.server:port
#ENV https_proxy https://your.proxy.server:port

ADD requirements.txt /

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
	python-pip \
	python-mysqldb \
	python-dev \
	python-imaging \
	netcat-openbsd \
	vim \
    && apt-get clean \
	&& rm -rf /var/lib/apt/lists/* \
    && pip install gunicorn setuptools wheel \
    && pip install -r /requirements.txt \
    && groupadd user && useradd --create-home --home-dir /home/user -g user user \
    && mkdir /opt/workdir

# Run gunicorn and celery as unprivileged user
USER user

ADD . /opt/layerindex

ADD settings.py /opt/layerindex/settings.py
ADD docker/updatelayers.sh /opt/updatelayers.sh
ADD docker/migrate.sh /opt/migrate.sh

## Uncomment to add a .gitconfig file within container
#ADD docker/.gitconfig /root/.gitconfig
## Uncomment to add a proxy script within container, if you choose to
## do so, you will also have to edit .gitconfig appropriately
#ADD docker/git-proxy /opt/bin/git-proxy

# Add entrypoint to start celery worker and gnuicorn
ADD docker/entrypoint.sh /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
