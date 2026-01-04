# Deploying the Web Application with ArgoCD

This guide provides step-by-step instructions on how to run the web application in this project using ArgoCD for a GitOps workflow.

## Prerequisites

Before you start, make sure you have the following tools installed:

-   [Docker](https://docs.docker.com/get-docker/)
-   [kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/)
-   [kind](https://kind.sigs.k8s.io/docs/user/quick-start/#installation)
-   [Helm](https://helm.sh/docs/intro/install/)

## Step 1: Create a Local Kubernetes Cluster

First, you need a Kubernetes cluster running locally. We will use `kind` to create a cluster based on the `kind-config.yaml` file in this project.

1.  **Create the `kind` cluster:**
    This command will create a new cluster named `ms2` configured with an Ingress controller.

    ```bash
    kind create cluster --config kind-config.yaml
    ```

2.  **Install NGINX Ingress Controller:**
    The Ingress controller allows you to access your services from outside the cluster.

    ```bash
    kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
    kubectl wait --namespace ingress-nginx --for=condition=ready pod --selector=app.kubernetes.io/component=controller --timeout=120s
    ```

3.  **Patch the Ingress Controller:**
    This patch ensures the Ingress controller runs on the `control-plane` node, where `kind` forwards `localhost` traffic. Note: PowerShell has issues with this command's syntax; using a different shell like Git Bash or WSL is recommended.

    ```bash
    kubectl patch deployment -n ingress-nginx ingress-nginx-controller -p '{"spec":{"template":{"spec":{"nodeSelector":{"ingress-ready":"true"}}}}}'
    ```



## Step 2: Install ArgoCD

Next, install ArgoCD on your cluster using Helm.

1.  **Add the ArgoCD Helm repository:**

    ```bash
    helm repo add argo https://argoproj.github.io/argo-helm
    ```

2.  **Install the ArgoCD Helm chart:**
    This command will install ArgoCD in the `argocd` namespace, creating it if it doesn't exist.

    ```bash
    helm install argocd argo/argo-cd --namespace argocd --create-namespace
    ```

3.  **Wait for ArgoCD to be ready:**
    Ensure all ArgoCD components are running before proceeding.

    ```bash
    kubectl wait --for=condition=ready pod --all -n argocd --timeout=300s
    ```

## Step 3: Access the ArgoCD UI

To manage your deployments, you can use the ArgoCD web UI.

1.  **Port-forward the ArgoCD server:**
    This command exposes the ArgoCD server on `localhost:8080`.

    ```bash
    kubectl port-forward service/argocd-server -n argocd 8080:443
    ```

2.  **Get the initial admin password:**
    The initial password for the `admin` user is stored in a Kubernetes secret.

    ```powershell
    # For PowerShell:
    $PASSWORD_B64 = kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}"
    [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($PASSWORD_B64))

    # For Bash/Zsh:
    kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d; echo
    ```

    You can now log in to the ArgoCD UI at `http://localhost:8080` with the username `admin` and the password you just retrieved.

## Step 4: Deploy the Application with ArgoCD

The `argocd-app.yaml` file in this repository defines the application and points to the Git repository containing the Kubernetes manifests.

1.  **Apply the ArgoCD application manifest:**
    This command tells ArgoCD to start managing and deploying our application.

    ```bash
    kubectl apply -f argocd-app.yaml
    ```

    ArgoCD will now fetch the Kubernetes manifests from the `k8s` directory of the `https://github.com/LVogels/milestone_2-deploy-webapp.git` repository and deploy them to your `kind` cluster.

## Step 5: Verify the Deployment

You can verify that the application has been deployed successfully through the ArgoCD UI or the command line.

1.  **Check the ArgoCD UI:**
    Navigate to `http://localhost:8080` and you should see the `milestone2-app` application. The status should eventually become `Healthy` and `Synced`.

2.  **Check with `kubectl`:**
    You can also use `kubectl` to check the status of your pods and services.

    ```bash
    kubectl get all
    kubectl get pods -o wide
    ```

    Your application should now be running and accessible at `http://localhost`.
