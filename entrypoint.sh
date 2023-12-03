#!/bin/sh

/usr/bin/wait-for-it.sh $POSTGRES_HOST:$POSTGRES_PORT

if [ "$ENV_ROLE" = "production" ]; then

  if [ "$DEPLOYMENT" = "front-end" ]; then
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
