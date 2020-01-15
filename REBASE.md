# Procedure for rebasing internal WR layerindex

## Preparation

Requires a separate computer for setting up and running the rebased
code. A machine with docker and docker-compose is recommended for
running the full stack. To simulate the full reverse proxy setup on
lpd-web.wrs.com, a machine with apache2, mariadb and a local user
named oelayer is required.

## Test instance setup

On test instance, install mariadb and its root credentials. As user
oelayer:

    > git clone -b rebase-<old> git://lxgit.wrs.com/tools/layerindex-web
    > cd layerindex-web
    > make db_init
    or
    > make db_reinit

This will setup the virtualenv and initial database tables.

## Export and import using json

On lpd-web:

    > make db-backup

This will make a compressed json file in:

    /home/oelayer/db-backup/wrl-layerindex.<date>-<time>.json.gz

Transfer the json file to the test instance and run:

    > make import IMPORT=wrl-layerindex.<date>-<time>.json.gz

Unfortunately this takes a _really_ long time.

## Export and import using mysql tools

On lpd-web:

    > mysqldump -u root -p layerindex  > ~/backup.sql

Transfer the sql file to the test instance and run:

    > mysql -u root -p

    mysql> use layerindex
    mysql> source backup.sql

Sometimes it might be necessary to use the json format in order to
drop specific tables.

## Rebase

Start with the upstream-master branch which should contain the latest
patches. Create a new rebase branch using this starting point. The
current convention is to name the rebase branch rebase-<date>.

    > git checkout upstream-master
    > git pull
    > git checkout -b rebase-<date>

The rebase consists of four pieces of functionality:

- The specific configs for running the layerindex on lpd-web
- The WR Templates model and view
- The WR Templates database migration
- The additional docker and docker-compose tools for layerindex
  development
  
From the previous rebase branch, cherry-pick these commits to the new
rebase branch. Sometimes extra commits will need to be squashed into
these patches.

Once the first patch has been merged use `make clean && make setup` to
recreate the virtualenv to ensure all the dependencies are installed.

For the database migration, create a merge migration using:

    > .venv/bin/python3 manage.py makemigrations --settings settings --merge

Inspect the migrations carefully, but the WR Template changes
shouldn't conflict.

If there is a conflict, the wrtemplate migration will need to be moved
to the end and a full drop and reload using the json import will be
required.

## Testing the rebase

First step is to test that the migration works:

    > make migrate

If this succeeds then the database should be ready to be used. Run a
local instance of the layerindex-web:

    > .venv/bin/python3 manage.py runserver 0.0.0.0:8000

This should allow you to interact with and verify that the upgrade
worked.

## Reverse proxy setup with subpath

Configure apache with the following configuration:

    <Proxy *>
        Require all granted
    </Proxy>
    ProxyPreserveHost On

    Alias /layerindex/static/ /home/oelayer/layerindex-web/layerindex/static/
    <Directory /home/oelayer/layerindex-web/layerindex/static/>
        Require all granted
    </Directory>

    ProxyPass /layerindex/static/ !
    ProxyPass /layerindex/ "http://127.0.0.1:8000/layerindex/"
    ProxyPassReverse /layerindex/ "http://127.0.0.1:8000/layerindex/"
    RequestHeader set SCRIPT_NAME "/layerindex"

and run gunicorn:

    > .venv/bin/gunicorn --workers=2 --name=layerindex --bind=localhost:8000 \
        --log-level=debug --reload wsgi

## Docker-compose setup

Another option is to use docker-compose to run the full stack in
docker containers instead of touching the base system. Once the docker
patches have been merged, run:

    > cd docker
    > docker build -t yocto/layerindex-app .
    > docker-compose up --abort-on-container-exit; docker-compose rm --force -v

This will build the local layerindex-web image. It also requires port
443 to be open.

Switch to a different terminal and log into the docker_layerindex_1
container:

    > docker exec -it -u 0 docker_layerindex_1

Now all the previous operations that use the database, etc. can be
done inside the docker containers.
