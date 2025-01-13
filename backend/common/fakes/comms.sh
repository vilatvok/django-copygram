#!/bin/bash

compose_file=~/Documents/projects/copygram/compose.dev.yaml
count=$1

docker exec backend python manage.py generate_comments --count $count
