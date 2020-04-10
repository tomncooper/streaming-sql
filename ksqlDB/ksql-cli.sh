#!/usr/bin/env bash

kubectl -n ksqldb run ksqldb-cli-$1 -ti \
    --image=confluentinc/ksqldb-cli:0.8.1 \
    --rm=true --restart=Never \
    -- /usr/bin/ksql http://ksqldb-server:8088