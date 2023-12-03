# ENV defaults to local (so that requirements/local.txt are installed), but can be overridden
#  (e.g. ENV=production make setup).
ENV ?= local
# PYTHON specifies the python binary to use when creating virtualenv
PYTHON ?= python3.9

# Editor can be defined globally but defaults to nano
EDITOR ?= nano

# By default we open the editor after copying settings, but can be overridden
#  (e.g. EDIT_SETTINGS=no make settings).
EDIT_SETTINGS ?= yes

# Get root dir and project dir
PROJECT_ROOT ?= $(PWD)
SITE_ROOT 	 ?= $(PROJECT_ROOT)

BLACK	?= \033[0;30m
RED		?= \033[0;31m
GREEN	?= \033[0;32m
LIGHT_GREEN ?= \033[1;32m
YELLOW	?= \033[0;33m
BLUE	?= \033[0;34m
LIGHT_BLUE ?= \033[1;36m
PURPLE	?= \033[0;35m
CYAN	?= \033[0;36m
GRAY	?= \033[0;37m
COFF	?= \033[0m

INFO 	?= $(LIGHT_BLUE)
SUCCESS ?= $(LIGHT_GREEN)
WARNING ?= $(YELLOW)
ERROR 	?= $(RED)
DEBUG 	?= $(CYAN)
FORMAT 	?= $(GRAY)
BOLD ?= \033[1m


DOCKER_COMPOSE			= docker-compose
DOCKER_COMPOSE_RUN		= $(DOCKER_COMPOSE) run --rm
DOCKER_COMPOSE_DJANGO	= $(DOCKER_COMPOSE_RUN) django

.PHONY: all help validate-system-packages dir_setup setup run logs set-rabbitmq-permissions docker
.PHONY: bash compilemessages createsuperuser docker-django docker-manage makemessages makemigrations migrate shell
.PHONY: clean pre pre-commit test psql
.PHONY: migrate docker-logs makemessages compilemessages psql


all: help


help:
	@echo "+------<<<<                                 Configuration                                >>>>------+"
	@echo ""
	@echo "ENV: $(ENV)"
	@echo "PYTHON: $(PYTHON)"
	@echo "PROJECT_ROOT: $(PROJECT_ROOT)"
	@echo "SITE_ROOT: $(SITE_ROOT)"
	@echo ""
	@echo "+------<<<<                                     Tasks                                    >>>>------+"
	@echo ""
	@echo "$(CYAN)make setup$(COFF)    - Sets up the project in your local machine"
	@echo "                This includes copying PyCharm files, creating local settings file, and setting up Docker."
	@echo ""
	@echo "$(CYAN)make pycharm$(COFF)  - Copies default PyCharm settings (unless they already exist)"
	@echo ""
	@echo "$(CYAN)make test$(COFF)     - Runs automatic tests on your python code"
	@echo ""
	@echo "$(CYAN)make coverage$(COFF) - Runs code test coverage calculation"
	@echo ""
	@echo "$(CYAN)make quality$(COFF)  - Runs automatic code quality tests on your code"
	@echo ""

# =========== [ SYSTEM SETUP AND VALIDATION ] ================
validate-system-packages:
	@echo "$(INFO)Validating system packages...$(COFF)"
	@#which poetry > /dev/null			|| (echo "$(ERROR)Poetry not found. Please install it.$(COFF)" && exit 1)
	@#which rabbitmqctl > /dev/null		|| (echo "$(ERROR)RabbitMQ command line tool not found. Please install it.$(COFF)" && exit 1)
	@which docker > /dev/null			|| (echo "$(ERROR)Docker not found. Please install it.$(COFF)" && exit 1)
	@which docker-compose > /dev/null 	|| (echo "$(ERROR)Docker Compose not found. Please install it.$(COFF)" && exit 1)
	@echo "All required system packages are installed."

.env: .env-dev-example
	@if [ ! -f .env ]; then \
		echo "$(CYAN)Creating .env file$(COFF)"; \
		install -b --suffix=.bak -m 644 .env-dev-example .env; \
	else \
		echo "$(CYAN).env file already exists$(COFF)"; \
	fi
merge-env:
	if [ -z "$(file2)" ]; then \
		cp $(file1) .env; \
	else \
		cat $(file1) $(file2)  > .env; \
	fi
print_make_state:
	echo "Current ENV_FILES: $(ENV_FILES)"
dir_setup: .env
# Set environment commands

set-integration:
	$(MAKE) merge-env file1=.env.development file2=.env.integration

set-development:
	$(MAKE) merge-env file1=.env.development

setup: validate-system-packages dir_setup
	@echo "$(INFO)Rebuilding docker$(COFF)"
	$(DOCKER_COMPOSE) down -v
	$(DOCKER_COMPOSE) build
	@echo "$(INFO)Running django migrations$(COFF)"
	@make migrate
	@echo "$(FORMAT)\n\n=============[$(BOLD)$(SUCCESS) SETUP SUCCEEDED $(FORMAT)]========================="
	@echo "$(INFO) Run 'make run cmd=< -d >' to start Django development server.$(COFF)"
setup-shell:
	make setup && make rund && make shell
docker-refresh:
	$(DOCKER_COMPOSE) restart
run: docker
docker:
	$(DOCKER_COMPOSE) up $(cmd)
rund:
	$(MAKE) run cmd="-d $(cmd)"
logs:
	$(DOCKER_COMPOSE) logs -f

set-rabbitmq-permissions:
	@echo "$(INFO)Waiting for RabbitMQ to start...$(COFF)"
	@while ! docker exec server_template_rabbitmq rabbitmqctl status >/dev/null 2>&1; do \
		sleep 1; \
	done
	@echo "$(INFO)RabbitMQ started$(COFF)"
	docker exec server_template_rabbitmq rabbitmqctl list_vhosts
	docker exec server_template_rabbitmq rabbitmqctl set_permissions -p platform guest ".*" ".*" ".*"

# =========== [ DJANGO RELATED COMMANDS ] ================
bash:
	$(DOCKER_COMPOSE_DJANGO) bash

compilemessages:
	$(DOCKER_COMPOSE_DJANGO) ./manage.py compilemessages

createsuperuser:
	$(DOCKER_COMPOSE_DJANGO) ./manage.py createsuperuser $(cmd)

docker-django:
	$(DOCKER_COMPOSE_DJANGO) $(cmd)


docker-manage:
	$(DOCKER_COMPOSE_DJANGO) ./manage.py $(cmd)

makemessages:
	$(DOCKER_COMPOSE_DJANGO) ./manage.py makemessages -a
	$(DOCKER_COMPOSE_DJANGO) ./manage.py makemessages -a -d djangojs

makemigrations:
	$(DOCKER_COMPOSE_DJANGO) ./manage.py makemigrations $(cmd)

migrate:
	$(DOCKER_COMPOSE_DJANGO) ./manage.py migrate $(cmd)

shell:
	$(DOCKER_COMPOSE_DJANGO) ./manage.py shell

# =========== [ TESTING & QUALITY ] ======================
clean:
	@echo "$(INFO)Cleaning pyc files$(COFF)"
	@cd $(SITE_ROOT) && find . -name "*.pyc" -exec rm -rf {} \;

coverage:
	@echo "$(INFO)Running automatic code coverage check$(COFF)"
	$(DOCKER_COMPOSE_DJANGO) coverage run -m py.test
	$(DOCKER_COMPOSE_DJANGO) coverage html
	$(DOCKER_COMPOSE_DJANGO) coverage report

pre: pre-commit
pre-commit:
	@echo "$(INFO)Running pre-commit routine$(COFF)"
	make schema
	poetry run pre-commit run --all-files

pre-commit-docker:
	@echo "$(INFO)Running pre-commit routine$(COFF)"
	make schema
	$(DOCKER_COMPOSE_DJANGO) poetry run pre-commit run --all-files

test: clean
	docker-compose down
	@echo "$(INFO)Running automatic tests$(COFF)"
	make run cmd=-d
	$(DOCKER_COMPOSE_DJANGO) py.test --durations=50 --disable-warnings $(args) $(path); RESULT=$$? ;
	$(DOCKER_COMPOSE_DJANGO) rm -rf django_extras/migrations

profile: clean
	docker-compose down
	@echo "$(INFO)Running automatic tests$(COFF)"
	make run cmd=-d
	$(DOCKER_COMPOSE_DJANGO) py.test --durations=30 --disable-warnings $(args) $(path) --profile; RESULT=$$? ;
	$(DOCKER_COMPOSE_DJANGO) rm -rf django_extras/migrations

show-profile:
	poetry run snakeviz prof/combined.prof

# =========== [ UNSURE ] =================================

psql:
	pwd
	. ./.env && docker-compose exec postgres psql --user "$$POSTGRES_USER" --dbname "$$POSTGRES_DB"


data:
	make docker-refresh
	make migrate
	make set-rabbitmq-permissions
	${DOCKER_COMPOSE_RUN} django ./manage.py loaddata $(path)
	make docker


prune:
	docker-compose down -v


schema:
	$(DOCKER_COMPOSE) run -e AUTHZ_ACTIVE=false -e AUTH_ACTIVE=false -e SHOW_SWAGGER_DOCS=false --rm django ./manage.py spectacular --file schema.yml
