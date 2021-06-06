# Thesis custom OpenWhisk setup

To run OpenWhisk in a development environment (as docker-compose quick-start method re-downloads the source code each time), we need a Kubernetes cluster. The documentation (https://github.com/apache/openwhisk-deploy-kube) suggests the ‘simplest way to get a small Kubernetes cluster suitable for development and testing’ is to use one of the Docker-in-Docker approaches, like kind for linux. 


## Kind 

Kind suggests it is helpful to have kubectl installed for more functionality (https://kubernetes.io/docs/tasks/tools/install-kubectl/ ). 

### Kubectl 

```sh
sudo curl -LO "https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl"

sudo chmod +x ./kubectl 

sudo mv ./kubectl /usr/local/bin/kubectl 
```

We will require docker (https://www.digitalocean.com/community/tutorials/how-to-install-and-use-docker-on-ubuntu-20-04 ) 
!! MAKE SURE YOUR USER IS IN THE DOCKER GROUP WITH `id –nG` !! 

### Install: 

```sh
sudo curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.9.0/kind-linux-amd64  

sudo chmod +x ./kind  

sudo mv ./kind /usr/local/bin/kind 
```

### Next steps
- Follow steps in here: https://github.com/apache/openwhisk-deploy-kube/blob/master/docs/k8s-kind.md#creating-the-kubernetes-cluster  
- In folder /home/jonas/repo/thesis-serverless 
- Create kind-cluster.yaml as specified:
```yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
- role: worker
  extraPortMappings:
    - hostPort: 31001
      containerPort: 31001
- role: worker
```
```sh
kind create cluster --config kind-cluster.yaml
# label all as invoker, then overwrite first as core
kubectl label node --all openwhisk-role=invoker
kubectl label node kind-worker openwhisk-role=core --overwrite
```
- create mycluster.yaml as specified:
```yaml
whisk:
  ingress:
    type: NodePort
    # get this internal IP from: kubectl describe node kind-worker | grep InternalIP: | awk '{print $2}'
    apiHostName: 172.19.0.3
    apiHostPort: 31001

invoker:
  containerFactory:
    impl: "kubernetes"

controller:
  imageName: "whisk/controller"
  imageTag: "latest"

nginx:
  httpsNodePort: 31001
```
## Helm

Helm is a tool to simplify the deployment and management of applications on Kubernetes clusters. The OpenWhisk Helm chart requires Helm 3.x. The following command installs the latest snap version (3.4.1 at the time of writing this).

```sh
sudo snap install helm --classic
```

## Deployment

- Clone repository at: [apache/openwhisk-deploy-kube](https://github.com/apache/openwhisk-deploy-kube)
- `helm install owdev ./openwhisk-deploy-kube/helm/openwhisk -n openwhisk --create-namespace -f mycluster.yaml`
- `wsk property set --apihost 172.19.0.3:31001`  [Should be changed according to IP and PORT specified in mycluster.yaml]
- `wsk property set --auth 23bc46b1-71f6-4ed5-8c54-816aa4f8c502:123zO3xZCLrMN6v2BKK1dXYFpXlPkccOFqm12CdAsMgRU4VrNZ9lyGVCGuMDGIwP`
- test with `helm test owdev -n openwhisk`
- pod status and progress can be viewed using `kubectl get pods -n openwhisk --watch`

The properties that you set are actually stored in the `~/.wskprops` file that is shared among all openwhisk utilities.
When making changes to a module, to redeploy it without redeploying the entire OpenWhisk system you can do the following:
- change openwhisk source code
```sh
    ./gradlew distDocker
    docker tag whisk/controller whisk/controller:vXX
    kind load docker-image whisk/controller
```
- change mycluster.yaml
```yaml
controller:
  imageName: "whisk/controller"
  imageTag: "vXX"
```
- `helm upgrade owdev ./openwhisk-deploy-kube/helm/openwhisk -n openwhisk -f mycluster.yaml`

## Redeploy from scratch

When you restart your server, the cluster can behave unexpectedly. The best solution is to run the deployment script with some additional prep commands.

```sh
helm uninstall owdev -n openwhisk
kind delete cluster

kind create cluster --config kind-cluster.yaml
kubectl label node kind-worker openwhisk-role=core
kubectl label node kind-worker2 openwhisk-role=invoker

cd openwhisk
./gradlew distDocker
docker tag whisk/controller whisk/controller:latest
kind load docker-image whisk/controller

cd ..
helm install owdev ./openwhisk-deploy-kube/helm/openwhisk -n openwhisk --create-namespace -f mycluster.yaml
```

## Usage

### Test

Create and invoke a simple function: use `test.sh`

### Workflow terminology

In Openwhisk terminology a workflow of functions that execute one after the other is called a *composition*. Compositions can be defined and deployed using the official utility programs using [Python](https://github.com/apache/openwhisk-composer-python) or [JavaScript](https://github.com/apache/openwhisk-composer).

Here, we will use the JS utility, as it contains the most functionality of the two options. Installation is done through npm.

```sh
  npm install -g openwhisk-composer
```

### JS Composer for Openwhisk

After installing the JS composer for Openwhisk, two seperate utilities are available: *compose* and *deploy*.
All functionality of the composer can be found [here](https://github.com/apache/openwhisk-composer/blob/master/docs/COMBINATORS.md).

example usage (we use the -i flag to use our local openwhisk cluster): 
```sh
  compose composition.js > composition.json
  deploy composition composition.json -iw
  wsk action invoke composition -i --blocking --result -P parameters.json
```

The parameters.json file is used (as explained below) to provide additional parameters that are required for completing the invocation, such as redis URI and SSL certificates:
```json
{
  "param_name_1": "param_value_1",
    "$composer": {
        "redis": {
            "uri": "redis://owdev-redis.openwhisk.svc:6379",
        },
        "openwhisk": {
            "ignore_certs": true
        }
    },
}
```

Parallel executions require a properly configured REDIS instance, which is annoying to add to the current cluster setup. Luckily, I found out that the internally used redis instance from openwhisk in kubernetes is registered as a service. Therefore we can add its service address `redis://owdev-redis.openwhisk.svc:6379` as a target for the intermediate storage in parallelized tasks.

An example usage of the composer utility is as follows. The example shows a branch and sequence structure. Notice how the state is passed throughout the left branch and the values placed by the first node can be read/modified by the second before finishing. Results of parallel invocation are collected in an array behind the key `value` of the resulting object.

```js
const composer = require('openwhisk-composer')

const l1 = composer.action('l1', { action: () => { return {"left_state": 1} } });
const l2 = composer.action('l2', { action:  (state) => { state["left_state"] += 7;state["l2"] = 5; return state } });
const left_branch = composer.sequence(l1, l2);

const right_branch = composer.action('right_branch', { action: function () { return {"right_state": 1} } });

module.exports = composer.if(
    composer.action('decision', { action: ({password}) => { return { value: password === 'abc123' } } }),
    composer.parallel(left_branch, right_branch),
    composer.action('failure', { action: function () { return { message: 'failure' } } }))

/*
for parameter 'password' = 'abc123'
{
    "value": [
        {
            "l2": 5,
            "left_state": 8
        },
        {
            "right_state": 1
        }
    ]
}
*/
```

Inside the controller, one way to have access to global composition information is by reading the JSON description file directly into controller state. This requires the file to be copied from the host to the right kubernetes pod, which can be done using `kubectl cp`. The line below read a file's contents to a string, but there surely is a far cleaner way to read a JSON file into a Map datastructure in Scala. I will get to that in the future.
```scala
val fileContents = scala.io.Source.fromFile("tree_reduce-composition.json").mkString; //returns the file data as String
```

## Debugging

- get info (logs) of pod: `kubectl describe pods -n openwhisk <POD_NAME>`
- inspect logs of a pod: `kubectl logs -n openwhisk <POD_NAME> --follow`, e.g. `kubectl logs -n openwhisk owdev-controller-0 --follow`

## Monitoring and Metrics

After having specified the settings

```yaml
metrics:
  prometheusEnabled: true
  userMetricsEnabled: true
```

in mycluster.yaml, grafana dashboards are enabled at: `https://172.19.0.3:31001/monitoring/dashboards` (port and ip come from mycluster.yaml whisk.ingress section).


## Project structure

2 git submodules, openwhisk and openwhisk-deploy-kube:
- **openwhisk**: A submodule linking to a forked version of the official openwhisk repository. Customization can be found in the `thesis-master` branch of the fork.
- **openwhisk-deploy-kube**: no changes have to be made to this repository, it is used as read-only.

### Clone project

```sh
    git clone git@github.ugent.be:jovdrven/thesis-openwhisk.git --recursive
    cd openwhisk
    git checkout thesis-master
    cd ..
```
