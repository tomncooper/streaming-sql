#!/usr/bin/env bash

kubectl -n materialize run psql-cli-$1 -ti \
    --image=postgres:latest \
    --rm=true --restart=Never \
    -- psql -h materialize-server -p 6875 materialize
