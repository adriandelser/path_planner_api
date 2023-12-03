#!/bin/sh

/usr/bin/wait-for-it.sh $POSTGRES_HOST:$POSTGRES_PORT

if [ "$ENV_ROLE" = "production" ]; then

  ./manage.py loaddata pii/fixtures/fixtures.json --format=json
  ./manage.py shell < checks/global_templates/template_gen.py
  ./manage.py loaddata checks/fixtures/global_template_fixtures.json --format=json
  if [ "$DEPLOYMENT" = "portal" ]; then
    yarn install && yarn run build
    ./manage.py cleanup_static
    python3 manage.py collectstatic --no-input
  fi
  echo "========  Printing env ======="
  env
  echo "========= WAITING FOR DB ====================="
fi

command=$(echo $@ | envsubst)
echo "$command"
exec $command
