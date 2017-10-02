SHELL = /bin/bash #requires bash
VENV = $(PWD)/.venv
DEPS = $(wildcard *.py)
GET_PIP = $(VENV)/bin/get-pip.py
PIP = $(VENV)/bin/pip3
DEBS = python3-dev libmysqlclient-dev

.PHONY: local_instance setup clean test help update logged_update db_init db_reinit import images backup

.DEFAULT_GOAL := local_instance

help:
	@echo "Make options for layerindex development"
	@echo
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-10s\033[0m %s\n", $$1, $$2}'

# Use get-pip.py to avoid requiring installation of ensurepip package
$(VENV): .check
	type python3 >/dev/null 2>&1 || { echo >&2 "Python3 required. Aborting."; exit 1; }; \
	test -d $(VENV) || python3 -m venv --without-pip $(VENV); \
	touch $(VENV); \
	wget -O $(GET_PIP) https://bootstrap.pypa.io/get-pip.py; \
	$(VENV)/bin/python3 $(GET_PIP) --ignore-installed; \
	$(PIP) install --upgrade --ignore-installed requests; \
	$(PIP) install --ignore-installed -r requirements.txt; \
	$(PIP) install --ignore-installed gunicorn;

setup: $(VENV) ## Install all python dependencies in virtualenv.

system: ## Convenience target for installing system libraries on Ubuntu/Debian
	sudo apt-get install $(DEBS)

.check: ## Verify system libraries are installed
	@echo "Verifying system library installation"
	@if [ -e /usr/bin/dpkg ]; then \
		for deb in $(DEBS); do \
			dpkg -L $$deb > /dev/null 2>&1; \
			if [ "$$?" != "0" ]; then \
				echo "Package $$deb must be installed. Run 'make system'."; \
				exit 1; \
			fi; \
		done; \
	else \
		echo "WARNING: unable to verify system libraries installed"; \
	fi; \
	touch .check

clean: ## Delete virtualenv and all build directories
	rm -rf $(VENV) .check

test: ## Run tests
	$(VENV)/bin/python3 setup.py test

local_instance: layerindex_db.sqlite3 ## Run local django server with sqlitedb
	$(VENV)/bin/python3 manage.py runserver 0.0.0.0:8000

layerindex_db.sqlite3: $(VENV)
	$(VENV)/bin/python3 manage.py migrate

update: $(VENV) ## Trigger update of layerindex database
	. $(VENV)/bin/activate; ./layerindex/update.py --debug

branch_update: $(VENV) ## Trigger update of a specific branch in layerindex database and redirect to $HOME/log
ifndef BRANCH
	$(error BRANCH required )
endif
	$(eval LOG=$(HOME)/log/layerindex-update.$(shell date +\%Y_\%m_\%d-\%H\%M\%S).log)
	mkdir $(HOME)/log; \
	. $(VENV)/bin/activate; ./layerindex/update.py --branch $(BRANCH) --debug > $(LOG) 2>&1; \
	gzip $(LOG)

branch_full_update: $(VENV) ## Trigger full_reload of a specific branch in layerindex database and redirect to $HOME/log
ifndef BRANCH
	$(error BRANCH required )
endif
	$(eval LOG=$(HOME)/log/layerindex-update.$(shell date +\%Y_\%m_\%d-\%H\%M\%S).log)
	. $(VENV)/bin/activate; ./layerindex/update.py --branch $(BRANCH) --fullreload --debug > $(LOG) 2>&1; gzip $(LOG)

layer_full_update: $(VENV) ## Trigger full_reload of a specific layer and branch in layerindex database and redirect to $HOME/log
ifndef BRANCH
	$(error BRANCH required )
endif
ifndef LAYER
	$(error LAYER required )
endif
	$(eval LOG=$(HOME)/log/layerindex-update.$(shell date +\%Y_\%m_\%d-\%H\%M\%S).log)
	. $(VENV)/bin/activate; ./layerindex/update.py --layer $(LAYER) --branch $(BRANCH) --fullreload --debug > $(LOG) 2>&1;\
	gzip $(LOG)

fullreload: $(VENV) ## Trigger update with full reload of layerindex database
	. $(VENV)/bin/activate; ./layerindex/update.py --fullreload --debug

migrate: $(VENV) ## Apply any database migrations to the mysql database
ifndef SETTINGS
	$(eval SETTINGS=settings)
endif
	$(VENV)/bin/python3 manage.py migrate --settings $(SETTINGS)

db_init: $(VENV) ## Create database and oelayer user with permissions
ifndef SETTINGS
	$(eval SETTINGS=settings)
endif
	mysql -u root -p < db_init.sql; \
	$(VENV)/bin/python3 manage.py syncdb --settings $(SETTINGS);

db_reinit: $(VENV) ## Drop and recreate database. Assume oelayer user already exists.
ifndef SETTINGS
	$(eval SETTINGS=settings)
endif
	mysql -u root -p < db_reinit.sql; \
	$(VENV)/bin/python3 manage.py syncdb --settings $(SETTINGS);

backup: $(VENV) ## Generate a dump of the entire db as a backup strategy
ifndef SETTINGS
	$(eval SETTINGS=settings)
endif
	$(eval BACKUP=$(HOME)/db-backup/wrl-layerindex.$(shell date +\%Y_\%m_\%d-\%H\%M\%S).json)
	mkdir -p $(HOME)/db-backup; \
	$(VENV)/bin/python3 manage.py dumpdata --settings $(SETTINGS) --exclude=contenttypes --exclude=auth.Permission > $(BACKUP); \
	gzip $(HOME)/db-backup/*.json

clone_branch: $(VENV) ## Clone an existing branch with a new name and description
ifndef SETTINGS
	$(eval SETTINGS=settings)
endif
	$(VENV)/bin/python3 manage.py clone_branch --settings $(SETTINGS) \
        --branch "$(BRANCH)" --name "$(NAME)" --description "$(DESCRIPTION)"

import: $(VENV) ## Load layerindex data exported from different layerindex
ifndef IMPORT
	$(error IMPORT required )
endif
ifndef SETTINGS
	$(eval SETTINGS=settings)
endif
	$(VENV)/bin/python3 manage.py loaddata --settings $(SETTINGS) $(IMPORT); \
	$(VENV)/bin/python3 manage.py migrate --settings $(SETTINGS);

restart_gunicorn: ## Production instance uses gunicorn. Send HUP signal to trigger reload
	/sbin/status layerindex-web | cut -d' ' -f 4 | xargs -r kill -HUP
