#!/usr/bin/env bash

kubectl -n $1 run ksqldb-cli-$2 -ti \
    --image=confluentinc/ksqldb-cli:0.8.1 \
    --rm=true --restart=Never \
    -- /usr/bin/ksql http://ksqldb-server:8088
