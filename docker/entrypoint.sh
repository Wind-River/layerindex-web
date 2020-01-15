#!/bin/bash

cd /opt/layerindex || exit 1

if [ "$RUN_CELERY" == 'true' ]; then
    if [ -n "$RABBIT_BROKER" ]; then
        sed -i "s/RABBIT_BROKER = .*/RABBIT_BROKER = '$RABBIT_BROKER'/" settings.py
    fi

    if [ -n "$RABBIT_BACKEND" ]; then
        sed -i "s/RABBIT_BACKEND = .*/RABBIT_BACKEND = '$RABBIT_BACKEND'/" settings.py
    fi

    # Start Celery
    /usr/local/bin/celery -A layerindex.tasks worker --loglevel="${CELERY_LOG_LEVEL:-info}" \
                          --workdir=/opt/layerindex
else
    echo "Waiting for database to come online"
    for i in $(seq 1 1 "${STARTUP_DELAY:-10}"); do echo -n "$i." && sleep 1; done; echo

    if [ "$LAYERINDEX_INIT" == "yes" ]; then
        python3 manage.py migrate
    fi

    if [ -n "$LAYERINDEX_ADMIN" ] && [ -n "$LAYERINDEX_ADMIN_EMAIL" ] && [ -n "$LAYERINDEX_ADMIN_PASS" ]; then
        echo "from django.contrib.auth.models import User; User.objects.create_superuser('$LAYERINDEX_ADMIN', '$LAYERINDEX_ADMIN_EMAIL', '$LAYERINDEX_ADMIN_PASS')" | python3 manage.py shell
    fi

    # populate the static files volume to be served by reverse proxy container
    STAMP=/opt/layerindex/layerindex/static/.collected
    if [ ! -f "$STAMP" ]; then
        export STATIC_ROOT=/opt/layerindex/layerindex/static
        python3 /opt/layerindex/manage.py collectstatic --no-input
        touch "$STAMP"
    fi

    # Start Gunicorn
    /usr/local/bin/gunicorn wsgi:application --workers="${GUNICORN_NUM_WORKERS:-4}" \
                            --bind="${GUNICORN_BIND:-:5000}" \
                            --log-level="${GUNICORN_LOG_LEVEL:-debug}" \
                            --pid=/tmp/gunicorn.pid \
                            --chdir=/opt/layerindex
fi
