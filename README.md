# Streaming SQL

This repo has example Kubernetes deployment files and example applications for various streaming SQL options.

## Kafka

All the examples in this repo assume you have an Apache Kafka cluster running and accessible on you Kubernetes cluster. [Strimzi](https://strimzi.io/) is a great way to get Kafka up and running on Kubernetes.

Install the latest version of the Strimzi Kafka Cluster Operator on your cluster with the following command (see [the docs](https://strimzi.io/docs/latest/#downloads-str) for other deployment options):

```bash
curl -L http://strimzi.io/install/latest \
    | sed 's/namespace: .*/namespace: <namespace>/' \
    | kubectl apply -f - -n <namespace>
```

The spin up a 3 node Kafka cluster with the following command (see the [project repository](https://github.com/strimzi/strimzi-kafka-operator/tree/master/examples/kafka) for other example Kafka deployments):

```bash
kubectl apply -f \
    https://strimzi.io/examples/latest/kafka/kafka-persistent.yaml \
    -n <namespace>
```

## ksqlDB

[ksqlDB](https://ksqldb.io/) is a streaming SQL implementation based on [Apache Kafka](https://kafka.apache.org/) and the [Kafka Stream](https://kafka.apache.org/documentation/streams/) library.

It is not a fully open source solution as it is licensed under the Confluent Community License Agreement v1.0.

To test out ksqlDB, you need to change the `KSQL_BOOTSTRAP_SERVERS` environment variable in the `ksqlDB-deployment.yaml` to match the boostrap address of you Kafka cluster. If you are using Strimzi with the example above then this should be set as below (if you changed the `metadata.name` field of the `kafka` custom resource then change `my-cluster` to match the new name):

```yaml
- name: KSQL_BOOTSTRAP_SERVERS
  value: PLAINTEXT://my-cluster-kafka-bootstrap:9092
```

Then you can deploy your ksqlDB instance:

```bash
$ kubectl apply -f ksqlDB/ksqlDB-deployment.yaml
```

Once deployed you can interact with the server using the `ksql-cli` command line client running in another pod using the `ksql-cli.sh` script:

```bash
$ ./ksqlDB/ksql-cli.sh 1
```

Where the number after the script is used to label different invocations of the CLI if you want to run more than one instance for data entry and analysis.

Now you can play with ksqlDB and follow the [project quickstart guide](https://ksqldb.io/quickstart.html).

## materialize

[Materialize](https://materialize.io/) uses a streaming engine based on timely dataflow to provide a PostgreSQL compatible SQL interface. 

This is not a fully open source solution as it is licensed under the Business Source License v1.1. Which limits you to running the code on a singe instance unless you purchase a licence.

You can deploy the materialize server using the following command:

```bash
$ kubectl apply -f materialize/materialize-deployment.yaml
```

Once deployed you can interact with the server using the `psql` command line client running in another pod using the `psql-cli.sh` script:

```bash
$ ./materialize/psql-cli.sh 1
```

Where the number after the script is used to label different invocations of the CLI if you want to run more than one instance for data entry and analysis.

Now you can play with materialize and follow the [project quickstart guide](https://materialize.io/docs/get-started/).
