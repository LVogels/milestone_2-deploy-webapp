# Milestone 2 Kubernetes Implementatie Gids

Dit document beschrijft de stappen voor het opzetten, uitvoeren en afbreken van de Kubernetes-cluster voor Milestone 2 met `kind`.

## Vereisten

Zorg ervoor dat de volgende software is geïnstalleerd voordat u begint:

-   [Docker](https://docs.docker.com/get-docker/)
-   [kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/)
-   [kind](https://kind.sigs.k8s.io/docs/user/quick-start/#installation)
-   [Helm](https://helm.sh/docs/intro/install/)

## Lokale Cluster Opzetten

Volg deze stappen om uw `kind` cluster te starten en de applicatie te implementeren.

### 1. `kind` Cluster Aanmaken

Maak een `kind` cluster aan met de juiste poortkoppelingen voor de Ingress-controller.

```bash
kind create cluster --config kind-config.yaml
```

*Plaats hier een schermafbeelding van de output van het `kind create cluster` commando.*
`[SCHERMAFBEELDING: kind create cluster output]`

### 2. NGINX Ingress Controller Installeren

Installeer de NGINX Ingress-controller die nodig is om verkeer naar uw applicatie te routeren.

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
kubectl wait --namespace ingress-nginx --for=condition=ready pod --selector=app.kubernetes.io/component=controller --timeout=120s
```

*Plaats hier een schermafbeelding van de output van de `kubectl apply` en `kubectl wait` commando's.*
`[SCHERMAFBEELDING: Ingress controller installatie]`

### 3. Docker Images Bouwen en Laden

Bouw de Docker-images voor de API- en Frontend-services en laad ze in uw `kind` cluster.

```bash
docker build -t lv-ms2-api:latest ./api
docker build -t lv-ms2-frontend:latest ./frontend
kind load docker-image lv-ms2-api:latest --name ms2
kind load docker-image lv-ms2-frontend:latest --name ms2
docker pull mysql:5.7
kind load docker-image mysql:5.7 --name ms2
```

*Plaats hier een schermafbeelding van de output van de `docker build` en `kind load` commando's.*
`[SCHERMAFBEELDING: Docker images bouwen en laden]`

## Applicatie Implementatie

Er zijn twee manieren om de applicatie te implementeren: handmatig met `kubectl` of geautomatiseerd met ArgoCD (GitOps).

### Handmatige Implementatie

Implementeer alle Kubernetes-resources (deployments, services, ingress, etc.) met één commando.

```bash
kubectl apply -f k8s/
```

### GitOps met ArgoCD

Voor een geautomatiseerde implementatie kunt u ArgoCD gebruiken.

1.  **ArgoCD Installeren:**
    Installeer ArgoCD met Helm in de `argocd` namespace.
    ```bash
    helm repo add argo https://argoproj.github.io/argo-helm
    helm repo update
    helm install argocd argo/argo-cd --namespace argocd --create-namespace
    ```

2.  **Applicatie Aanmaken:**
    Maak de ArgoCD-applicatie aan door het `argocd-app.yaml` manifest toe te passen.
    ```bash
    kubectl apply -f argocd-app.yaml
    ```
    ArgoCD zal nu de applicatie synchroniseren met de status die is gedefinieerd in de Git-repository.

## Toegang tot de Webinterfaces

### Prometheus Monitoring

Prometheus wordt gebruikt om de resources en prestaties van de cluster te monitoren.

1.  **Toegang tot de Prometheus UI:**
    Gebruik `port-forward` om toegang te krijgen tot de Prometheus-server.
    ```powershell
    $POD_NAME = $(kubectl get pods --namespace monitoring -l "app.kubernetes.io/name=prometheus,app.kubernetes.io/instance=prometheus" -o jsonpath="{.items[0].metadata.name}")
    kubectl --namespace monitoring port-forward $POD_NAME 9090
    ```
    Open vervolgens `http://localhost:9090` in uw browser.

*Plaats hier een schermafbeelding van de Prometheus webinterface.*
`[SCHERMAFBEELDING: Prometheus UI]`

### ArgoCD Webinterface

ArgoCD biedt een webinterface om de status van uw applicaties te bekijken.

1.  **Toegang tot de ArgoCD UI:**
    Gebruik `port-forward` om toegang te krijgen tot de ArgoCD-server.
    ```bash
    kubectl port-forward service/argocd-server -n argocd 8080:443
    ```
    Open `http://localhost:8080` in uw browser.

2.  **Inloggen op ArgoCD:**
    Gebruik de gebruikersnaam `admin`. Het initiële wachtwoord kan worden opgehaald met de volgende commando's:
    ```powershell
    $PASSWORD_B64 = kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}"
    [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($PASSWORD_B64))
    ```

*Plaats hier een schermafbeelding van de ArgoCD webinterface.*
`[SCHERMAFBEELDING: ArgoCD UI]`

## Cluster Afbreken

Om uw `kind` cluster te stoppen en alle resources op te ruimen, gebruikt u het volgende commando:

```bash
kind delete cluster --name ms2
```

*Plaats hier een schermafbeelding van de output van het `kind delete cluster` commando.*
`[SCHERMAFBEELDING: kind delete cluster output]`
