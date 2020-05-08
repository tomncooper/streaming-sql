#!/usr/bin/env bash

kubectl -n $1 run psql-cli-$2 -ti \
    --image=postgres:latest \
    --rm=true --restart=Never \
    -- psql -h materialize-server -p 6875 materialize
