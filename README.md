# Milestone 2 Kubernetes Setup

This document outlines the steps to set up, run, and tear down the Kubernetes cluster for Milestone 2 using `kind`.

## Prerequisites

Before you begin, ensure you have the following installed:

-   [Docker](https://docs.docker.com/get-docker/)
-   [kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/)
-   [kind](https://kind.sigs.k8s.io/docs/user/quick-start/#installation)

## Starting the Cluster

Follow these steps to start your `kind` cluster and deploy the application:

1.  **Create/Update kind configuration:**
    Ensure you have the `kind-config.yaml` file in your project root with the following content. This configures `kind` to map host ports to the Ingress controller and adds a worker node.

    ```yaml
    kind: Cluster
    apiVersion: kind.x-k8s.io/v1alpha4
    name: ms2
    nodes:
    - role: control-plane
      kubeadmConfigPatches:
      - |
        kind: InitConfiguration
        nodeRegistration:
          kubeletExtraArgs:
            node-labels: "ingress-ready=true"
      extraPortMappings:
      - containerPort: 80
        hostPort: 80
        protocol: TCP
      - containerPort: 443
        hostPort: 443
        protocol: TCP
    - role: worker
    ```

2.  **Delete existing cluster (if any) and create a new one:**
    First, ensure any old cluster is removed, then create a new one using the configuration.

    ```bash
    kind delete cluster --name ms2
    kind create cluster --config kind-config.yaml
    ```

3.  **Install NGINX Ingress Controller:**
    Install the NGINX Ingress controller for `kind`.

    ```bash
    kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
    ```

4.  **Wait for the Ingress Controller to be ready:**
    
    ```bash
    kubectl wait --namespace ingress-nginx --for=condition=ready pod --selector=app.kubernetes.io/component=controller --timeout=120s
    ```

5.  **Patch the Ingress Controller Deployment:**
    Patch the Ingress controller deployment to run on the control plane node.

    ```bash
    kubectl patch deployment -n ingress-nginx ingress-nginx-controller -p '{"spec":{"template":{"spec":{"nodeSelector":{"ingress-ready":"true"}}}}}'
    ```

6.  **Wait for the new Ingress Controller pod to be ready:**

    ```bash
    kubectl wait --namespace ingress-nginx --for=condition=ready pod --selector=app.kubernetes.io/component=controller --timeout=120s
    ```

7.  **Untaint the control-plane node:**
    By default, the control-plane node has a taint that prevents pods from being scheduled on it. For a local development cluster, you can remove this taint to allow pods to be scheduled on all nodes.

    ```bash
    kubectl taint nodes ms2-control-plane node-role.kubernetes.io/control-plane-
    ```

8.  **Build Docker Images:**
    Build the Docker images for your API and Frontend services.

    ```bash
    docker build -t lv-ms2-api:latest ./api
    docker build -t lv-ms2-frontend:latest ./frontend
    ```

9.  **Load Docker Images into kind cluster:**
    Load the built images and the `mysql:5.7` image (used by the database deployment) into your `kind` cluster.

    ```bash
    kind load docker-image lv-ms2-api:latest --name ms2
    kind load docker-image lv-ms2-frontend:latest --name ms2
    docker pull mysql:5.7 # Pull mysql image locally first if not already present
    kind load docker-image mysql:5.7 --name ms2
    ```

10. **Apply Kubernetes Manifests:**
    Deploy all your Kubernetes resources (deployments, services, ingress, etc.).

    ```bash
    kubectl apply -f k8s/
    ```

11. **Scale the API Deployment:**
    Scale the API deployment to 2 replicas to distribute the load across the nodes.

    ```bash
    kubectl scale deployment lv-ms2-api --replicas=2
    ```

12. **Verify Cluster Status:**
    Check the status of your Kubernetes pods and services, and see which nodes the pods are running on.

    ```bash
    kubectl get all
    kubectl get pods -o wide
    ```

Your application should now be accessible at `http://localhost`.

## Monitoring

Prometheus is used to monitor the cluster resources and performance. It was installed using Helm.

To access the Prometheus UI, open a new terminal and run the following commands:

```powershell
$POD_NAME = $(kubectl get pods --namespace monitoring -l "app.kubernetes.io/name=prometheus,app.kubernetes.io/instance=prometheus" -o jsonpath="{.items[0].metadata.name}")
kubectl --namespace monitoring port-forward $POD_NAME 9090
```

You can then access the Prometheus UI by navigating to `http://localhost:9090` in your web browser.

## GitOps with ArgoCD

ArgoCD has been installed to enable a GitOps workflow.

### Accessing the ArgoCD UI

1.  **Port-forward the ArgoCD server:**
    Open a new terminal and run the following command:
    ```bash
    kubectl port-forward service/argocd-server -n argocd 8080:443
    ```
    Then, open your web browser and navigate to `http://localhost:8080`.

2.  **Log in to ArgoCD:**
    Use the username `admin`. To get the initial password, run the following commands:
    ```powershell
    $PASSWORD_B64 = kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}"
    [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($PASSWORD_B64))
    ```

## Stopping the Cluster

To stop and clean up your `kind` cluster, simply delete it:

```bash
kind delete cluster --name ms2
```

This will remove all nodes and deployed resources from your local machine.

