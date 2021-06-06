#!/bin/bash

helm uninstall owdev -n openwhisk
kind delete cluster

kind create cluster --config kind-cluster.yaml
# label all as invoker, then overwrite first as core
kubectl label node --all openwhisk-role=invoker
kubectl label node kind-worker openwhisk-role=core --overwrite

cd openwhisk
./gradlew distDocker
docker tag whisk/controller whisk/controller:latest
kind load docker-image whisk/controller

cd ..
helm install owdev ./openwhisk-deploy-kube/helm/openwhisk -n openwhisk --create-namespace -f mycluster.yaml

echo "Sleeping for 5 minutes before pod is up"
sleep 5m

# additional info to controller PoC: load known composition information
# echo "loading known composition information into controller"
# kubectl cp compositions/tree_reduce-composition.json owdev-controller-0:/tree_reduce-composition.json -n openwhisk

echo "Testing the cluster"
./test.sh

# https://github.com/apache/openwhisk/blob/master/docs/conductors.md#conductor-annotation
cd compositions
wsk action create triple triple.js -i
wsk action create increment triple_inc.js -i
wsk action create tripleAndIncrement tripleAndIncrement.js -i -a conductor true
wsk action invoke tripleAndIncrement -ir -p value 3
cd ..

cd compositions
./build_and_run.sh cause_test_split
cd ..
