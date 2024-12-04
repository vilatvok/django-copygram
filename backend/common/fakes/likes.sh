#!/bin/bash

compose_file=~/Documents/projects/copygram/compose.dev.yaml
count=$1

docker compose -f $compose_file run --rm backend python manage.py generate_likes --count $count
docker compose -f $compose_file stop db redis

