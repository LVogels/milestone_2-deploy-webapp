# Linux Web Services: Milestone 2 - Extensive Deployment Guide

## 1. Introduction

This document serves as a comprehensive guide for the deployment of a three-tier web application stack. The project demonstrates the progression from local development using Docker Compose to a production-like orchestration using Kubernetes (KIND) and GitOps principles with ArgoCD.

The goal is to deploy a web stack consisting of:
1.  **Frontend**: A lightweight web server hosting the user interface.
2.  **Backend (API)**: A Python FastAPI application processing logic and connecting to the database.
3.  **Database**: A MariaDB instance for persistent data storage.

We will explore two major phases:
1.  **Containerization & Local Testing**: Using Docker and Docker Compose to validate the application logic and container builds.
2.  **Orchestration**: Deploying the stack to a multi-node Kubernetes cluster, managing traffic with Ingress, and automating deployment with ArgoCD.

---

## 2. Theoretical Background

### 2.1 Docker & Docker Compose
**Docker** allows us to package applications and their dependencies into "containers". This ensures that the application runs consistently on any environment, solving the "it works on my machine" problem.

**Docker Compose** is a tool for defining and running multi-container Docker applications. It allows us to define the entire stack (frontend, api, db) in a single YAML file.
*   **Why start with Docker Compose?**
    *   **Simplicity**: It is easier to write one `docker-compose.yaml` than multiple Kubernetes manifests.
    *   **Rapid Feedback**: The "build-run-debug" loop is much faster locally.
    *   **Validation**: It proves that the containers work and can talk to each other before introducing the complexity of Kubernetes networking (Services, Ingress, DNS).

### 2.2 Kubernetes (K8s) & KIND
**Kubernetes** is an orchestration platform for automating deployment, scaling, and management of containerized applications. Unlike Docker Compose, which is meant for a single host, Kubernetes manages clusters of computers.

**KIND (Kubernetes IN Docker)** allows us to run a local Kubernetes cluster by using Docker containers as "nodes". This is perfect for learning and testing Kubernetes without expensive cloud infrastructure.

---

## 3. Step 1: Containerization and Docker Compose

In this phase, we define the environment for each component and run them together.

### 3.1 The Backend (API)

The API is built with **FastAPI**, a modern, fast (high-performance) web framework for building APIs with Python.

**File: `api/requirements.txt`**
This file lists the Python libraries required by our application.
```text
fastapi==0.104.1
uvicorn==0.24.0
mysql-connector-python==8.1.0
pydantic==2.4.2
```

**File: `api/app.py`**
This is the main application logic. It defines the API endpoints and handles database connections.
```python
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
import mysql.connector
import os
import socket
import datetime
from pydantic import BaseModel
from typing import Dict, Any

app = FastAPI(title="Milestone2 API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME'),
    'port': os.getenv('DB_PORT')
}

def get_db_connection():
    """Create database connection"""
    return mysql.connector.connect(**DB_CONFIG)

def init_database():
    """Initialize database schema"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL DEFAULT 'John Doe',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert default user if table is empty
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO users (name) VALUES ('John Doe')")
        
        conn.commit()
        cursor.close()
        conn.close()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization failed: {e}")

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_database()

@app.get("/")
async def root():
    return {"message": "Milestone2 API is running"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        conn = get_db_connection()
        conn.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {e}")

@app.get("/user")
async def get_user():
    """Get user name from database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT name FROM users WHERE id = 1")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result:
            return {"name": result['name']}
        else:
            raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

@app.get("/container_id")
async def get_container_id(response: Response):
    """Get container ID (hostname)"""
    response.headers["Connection"] = "close"
    # Prevent browser/proxy caching so each refresh actually hits the backend
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return {"container_id": socket.gethostname(), "timestamp": datetime.datetime.utcnow().isoformat() + "Z"}

@app.put("/user/{name}")
async def update_user(name: str):
    """Update user name"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET name = %s WHERE id = 1", (name,))
        conn.commit()
        cursor.close()
        conn.close()
        
        return {"message": "User updated successfully", "name": name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```
*   **Explanation**: The code initializes a FastAPI app. Crucially, it reads database credentials from **Environment Variables** (`os.getenv`). This is a best practice (The 12-Factor App) because it allows us to change configuration without changing the code.

**File: `api/Dockerfile`**
This file tells Docker how to build the API image.
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .

# Create non-root user
RUN useradd -m -u 1000 apiuser && chown -R apiuser:apiuser /app
USER apiuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```
*   **`FROM python:3.9-slim`**: Uses a lightweight Python base image.
*   **`WORKDIR /app`**: Sets the working directory inside the container.
*   **`RUN ...`**: Installs system dependencies (gcc) needed for some Python packages.
*   **`COPY ...`**: Moves files from our host to the container.
*   **`USER apiuser`**: Runs the process as a non-root user. This is a critical security practice to prevent potential container breakouts.
*   **`HEALTHCHECK`**: Docker will periodically run this command to see if the app is alive.
*   **`CMD`**: The command that runs when the container starts (`uvicorn` is the server).

### 3.2 The Frontend

The frontend is a static HTML page served by **Lighttpd**, a very lightweight web server.

**File: `frontend/index.html`**
The main interface for the user.
```html
<!DOCTYPE html>
<html lang="en">

<head>
  <meta charset="UTF-8" />
  <meta http-equiv="X-UA-Compatible" content="IE=edge" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Milestone 2</title>
</head>

<body>
  <h1><span id="user">Loading...</span> has reached milestone 2!</h1>
  <p>Container ID: <span id="container_id">Loading...</span></p>

  <script>
    // Fetch user from API
    fetch("http://localhost/api/user")
      .then((res) => res.json())
      .then((data) => {
        // Get user name
        const user = data.name;
        // Display user name
        document.getElementById("user").innerText = user;
      })
      .catch((error) => console.error("Error fetching user:", error));

    // Fetch container ID from API
    fetch("http://localhost/api/container_id")
      .then((res) => res.json())
      .then((data) => {
        // Get container ID
        const containerId = data.container_id;
        // Display container ID
        document.getElementById("container_id").innerText = containerId;
      })
      .catch((error) => console.error("Error fetching container ID:", error));
  </script>
</body>

</html>
```

**File: `frontend/lighttpd.conf`**
Configuration for the web server.
```conf
server.document-root = "/var/www/localhost/htdocs"
server.port = 80
server.username = "lighttpd"
server.groupname = "lighttpd"
server.modules = (
    "mod_indexfile",
    "mod_access",
    "mod_alias",
    "mod_redirect",
)

index-file.names = ("index.html")
mimetype.assign = (
    ".html" => "text/html",
    ".js" => "application/javascript",
    ".css" => "text/css",
)

static-file.exclude-extensions = ( ".php", ".pl", ".fcgi" )
```

**File: `frontend/Dockerfile`**
```dockerfile
FROM alpine:3.16

# Install lighttpd and curl for health checks
RUN apk add --no-cache lighttpd curl

# Copy custom lighttpd configuration
COPY lighttpd.conf /etc/lighttpd/lighttpd.conf

# Copy web content

COPY index.html /var/www/localhost/htdocs/

# Create a simple health check
RUN echo '#!/bin/sh' > /healthcheck.sh && \
    echo 'curl -f http://localhost/ || exit 1' >> /healthcheck.sh && \
    chmod +x /healthcheck.sh

# Expose port 80
EXPOSE 80

# Start lighttpd in foreground mode
CMD ["lighttpd", "-D", "-f", "/etc/lighttpd/lighttpd.conf"]

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD /healthcheck.sh
```
*   **`FROM alpine:3.16`**: Alpine is an extremely small Linux distribution (approx 5MB), making our image very efficient.
*   **`apk add`**: Alpine's package manager (like `apt` or `yum`).
*   **`CMD ["lighttpd", "-D", ...]`**: Runs Lighttpd in the foreground (`-D`) so the container keeps running.

### 3.3 The Database

We use a standard **MariaDB** image and initialize it with a SQL script.

**File: `db/init.sql`**
```sql
-- Initialize database
CREATE DATABASE IF NOT EXISTS milestone2;
USE milestone2;

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL DEFAULT 'Test Test',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert initial data
INSERT IGNORE INTO users (id, name) VALUES (1, 'Len Vogels');
```
*   **Explanation**: This script runs automatically when the database container starts for the first time, creating our schema and initial data.

### 3.4 Orchestrating with Docker Compose

**File: `docker-compose.yaml`**
```yaml
version: '3.8'

services:
  frontend:
    build: ./frontend
    container_name: lv-ms2-frontend
    ports:
      - "8080:80"
    depends_on:
      - api
    networks:
      - ms2-network
    restart: unless-stopped

  api:
    build: ./api
    container_name: lv-ms2-api
    ports:
      - "8000:8000"
    environment:
      - DB_HOST=db
      - DB_USER=root
      - DB_PASSWORD=milestone2
      - DB_NAME=milestone2
      - DB_PORT=3306
    depends_on:
      db:
        condition: service_healthy
    networks:
      - ms2-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  db:
    image: mariadb:11
    container_name: lv-ms2-db
    environment:
      MYSQL_ROOT_PASSWORD: milestone2
      MYSQL_DATABASE: milestone2
    volumes:
      - db_data:/var/lib/mysql
      - ./db/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    networks:
      - ms2-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "mariadb-admin", "ping", "-h", "127.0.0.1", "-uroot", "-pmilestone2"]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 30s


networks:
  ms2-network:
    driver: bridge

volumes:
  db_data:
```
*   **`services`**: Defines the containers we want to run.
*   **`build: ./frontend`**: Tells Compose to build the image from the `./frontend` directory instead of pulling it.
*   **`ports`**: Maps host ports to container ports (`"8080:80"` means accessing localhost:8080 goes to container port 80).
*   **`depends_on`**: Ensures start order. The API waits for the DB to be "healthy" before starting.
*   **`networks`**: All services join `ms2-network` so they can talk to each other by name (e.g., API connects to `db`).
*   **`volumes`**: `db_data` persists the database files so data isn't lost when the container stops.

### 3.5 Running the Stack

To start the application, run:

```bash
docker-compose up --build
```
*   **`up`**: Create and start containers.
*   **`--build`**: Force a rebuild of images (useful if you changed code).

> **[INSERT SCREENSHOT HERE]**
> *Description: A screenshot of your terminal showing the output of `docker-compose up`. It should show logs from `lv-ms2-frontend`, `lv-ms2-api`, and `lv-ms2-db` indicating they have started successfully (e.g., "Uvicorn running on...", "mysqld: ready for connections").*

You can now visit `http://localhost:8080` to see the application running.

---

## 4. Step 2: Kubernetes Deployment (KIND)

Now that we know the app works, we move to Kubernetes. This adds self-healing (restarting crashed pods), scaling (running multiple copies), and advanced networking.

### 4.1 Cluster Configuration

We need a cluster that supports an **Ingress Controller** (a reverse proxy that routes traffic).

**File: `kind-config.yaml`**
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
  - containerPort: 8080
    protocol: TCP
    hostPort: 8080
- role: worker
- role: worker
```
*   **`nodes`**: We define 1 control-plane (master) and 2 workers.
*   **`extraPortMappings`**: This is crucial. It maps port 80 on your *host machine* to port 80 on the *control-plane container*. This allows the Ingress controller inside the cluster to receive traffic from your browser.
*   **`node-labels`**: Tags the node so the Ingress controller knows where to run.

**Command: Create Cluster**
```bash
kind create cluster --config kind-config.yaml
```
*   **`--config`**: Tells KIND to use our custom configuration file.

> **[INSERT SCREENSHOT HERE]**
> *Description: A screenshot of your terminal showing the output of `kind create cluster`. It should show "Creating cluster 'ms2'..." and "Cluster creation complete".*

### 4.2 Setting up Ingress

We install NGINX Ingress Controller.

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
```
*   **`kubectl apply`**: The universal command to create/update resources in Kubernetes.

**Wait for it to be ready:**
```bash
kubectl wait --namespace ingress-nginx --for=condition=ready pod --selector=app.kubernetes.io/component=controller --timeout=120s
```

**Patch the Controller:**
We need to ensure the Ingress controller runs on the specific node we prepared in `kind-config.yaml`.
```bash
kubectl patch deployment -n ingress-nginx ingress-nginx-controller -p '{"spec":{"template":{"spec":{"nodeSelector":{"ingress-ready":"true"}}}}}'
```

### 4.3 Loading Images

Since KIND runs inside Docker, it cannot see the images on your host machine by default. We must load them.

```bash
docker build -t lv-ms2-api:latest ./api
docker build -t lv-ms2-frontend:latest ./frontend
kind load docker-image lv-ms2-api:latest --name ms2
kind load docker-image lv-ms2-frontend:latest --name ms2
docker pull mysql:5.7
kind load docker-image mysql:5.7 --name ms2
```
*   **`kind load docker-image`**: Transfers the image from your local Docker daemon into the KIND cluster nodes.

### 4.4 Kubernetes Manifests

We define our application state using YAML files.

**1. Storage (PVC & ConfigMap)**
**File: `k8s/storage.yaml`**
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: db-data-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: db-init-script
data:
  init.sql: |
    CREATE DATABASE IF NOT EXISTS milestone2;
    USE milestone2;

    -- Create users table
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL DEFAULT 'Test Test',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Insert initial data
    INSERT IGNORE INTO users (id, name) VALUES (1, 'Len Vogels');
```
*   **`PersistentVolumeClaim` (PVC)**: Requests 1GB of storage. K8s will provision this so our DB data persists.
*   **`ConfigMap`**: Stores the `init.sql` script. This allows us to inject the script into the DB container without rebuilding the image.

**2. Database Deployment**
**File: `k8s/db-deployment.yaml`**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lv-ms2-db
spec:
  replicas: 1
  selector:
    matchLabels:
      app: lv-ms2-db
  template:
    metadata:
      labels:
        app: lv-ms2-db
    spec:
      containers:
      - name: mariadb
        image: mariadb:11
        ports:
        - containerPort: 3306
        env:
        - name: MYSQL_ROOT_PASSWORD
          value: "milestone2"
        - name: MYSQL_DATABASE
          value: "milestone2"
        - name: MYSQL_TCP_PORT
          value: "3306"
        volumeMounts:
        - name: db-data
          mountPath: /var/lib/mysql
        - name: init-script
          mountPath: /docker-entrypoint-initdb.d
        livenessProbe:
          exec:
            command: 
            - /bin/sh
            - -c
            - "mariadb-admin ping -uroot -pmilestone2"
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
        readinessProbe:
          exec:
            command:
            - /bin/sh
            - -c
            - "mariadb-admin ping -uroot -pmilestone2"
          initialDelaySeconds: 15
          periodSeconds: 5
          timeoutSeconds: 5
      volumes:
      - name: db-data
        persistentVolumeClaim:
          claimName: db-data-pvc
      - name: init-script
        configMap:
          name: db-init-script
---
apiVersion: v1
kind: Service
metadata:
  name: lv-ms2-db-service
spec:
  selector:
    app: lv-ms2-db
  ports:
  - name: mysql
    port: 3306
    targetPort: 3306
```
*   **`Deployment`**: Manages the Pods. `replicas: 1` ensures 1 DB instance is running.
*   **`Service`**: Exposes the DB to other pods.
    *   `name: lv-ms2-db-service`: This becomes the DNS name. The API will connect to this host.

**3. API Deployment**
**File: `k8s/api-deployment.yaml`**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lv-ms2-api
spec:
  replicas: 2
  selector:
    matchLabels:
      app: lv-ms2-api
  template:
    metadata:
      labels:
        app: lv-ms2-api
    spec:
      containers:
      - name: api
        image: lenv1891/lv-ms2-api:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 8000
        env:
        - name: DB_HOST
          value: "lv-ms2-db-service"
        - name: DB_USER
          value: "root"
        - name: DB_PASSWORD
          value: "milestone2"
        - name: DB_NAME
          value: "milestone2"
        - name: DB_PORT
          value: "3306"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 40
          periodSeconds: 30
          timeoutSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: lv-ms2-api-service
spec:
  selector:
    app: lv-ms2-api
  ports:
  - port: 8000
    targetPort: 8000
```
*   **`replicas: 2`**: We run **2 copies** of the API for high availability. If one crashes, the other handles traffic.
*   **`env`**: We pass the DB connection details. Note `DB_HOST` is `lv-ms2-db-service` (the K8s Service name).
*   **`livenessProbe`**: K8s checks `/health`. If it fails, K8s kills and restarts the pod.
*   **`readinessProbe`**: K8s checks `/health`. If it fails, K8s stops sending traffic to this pod until it recovers.

**4. Frontend Deployment**
**File: `k8s/frontend-deployment.yaml`**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lv-ms2-frontend
spec:
  replicas: 1
  selector:
    matchLabels:
      app: lv-ms2-frontend
  template:
    metadata:
      labels:
        app: lv-ms2-frontend
    spec:
      containers:
      - name: frontend
        image: lenv1891/lv-ms2-frontend:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 80
        livenessProbe:
          exec:
            command: ["/bin/sh", "-c", "curl -f http://localhost/ || exit 1"]
          initialDelaySeconds: 5
          periodSeconds: 30
          timeoutSeconds: 3
        readinessProbe:
          exec:
            command: ["/bin/sh", "-c", "curl -f http://localhost/ || exit 1"]
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
---
apiVersion: v1
kind: Service
metadata:
  name: lv-ms2-frontend-service
spec:
  type: NodePort
  selector:
    app: lv-ms2-frontend
  ports:
  - port: 80
    targetPort: 80
    nodePort: 30080
```
*   Similar to API, but exposes port 80.
*   **`Service` type `NodePort`**: Exposes the service on a specific port on the node (30080), though we will primarily use Ingress.

**5. Ingress**
**File: `k8s/frontend-ingress.yaml`**
This is the entry point for external traffic.
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ms2-frontend-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /$2
spec:
  rules:
  - host: lvms2.com
    http:
      paths:
      # API routes must come first (more specific path)
      - path: /api(/|$)(.*)
        pathType: ImplementationSpecific
        backend:
          service:
            name: lv-ms2-api-service
            port:
              number: 8000
      # Frontend routes come last (catch-all)
      - path: /
        pathType: Prefix
        backend:
          service:
            name: lv-ms2-frontend-service
            port:
              number: 80
```
*   **`host: lvms2.com`**: The domain name we will use.
*   **Routing Rules**:
    *   Traffic to `lvms2.com/api/...` goes to the **API Service**.
    *   Traffic to `lvms2.com/` goes to the **Frontend Service**.
*   **Rewrite Target**: Removes `/api` from the path before sending it to the backend (so the backend sees `/user` instead of `/api/user`).

### 4.5 Manual Deployment

To deploy everything manually:

```bash
kubectl apply -f k8s/storage.yaml
kubectl apply -f k8s/db-deployment.yaml
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/frontend-ingress.yaml
```

> **[INSERT SCREENSHOT HERE]**
> *Description: A screenshot of your terminal showing the output of `kubectl get pods`. It should show all pods (api, db, frontend) with status "Running".*

---

## 5. Step 3: GitOps Deployment with ArgoCD

**GitOps** is a practice where the Git repository is the "source of truth". Instead of running `kubectl apply` manually, we ask an agent (ArgoCD) to sync the cluster state with the Git repo.

### 5.1 Installing ArgoCD

```bash
helm repo add argo https://argoproj.github.io/argo-helm
helm install argocd argo/argo-cd --namespace argocd --create-namespace
```
*   **Helm**: A package manager for Kubernetes. It simplifies installing complex apps like ArgoCD.

### 5.2 The ArgoCD Application

**File: `argocd-app.yaml`**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: milestone2-app
  namespace: argocd # ArgoCD applications are typically managed in the argocd namespace
spec:
  project: default
  source:
    repoURL: https://github.com/LVogels/milestone_2-deploy-webapp.git
    targetRevision: HEAD # Or a specific branch like 'main' or 'master'
    path: k8s # The path within the repository where your Kubernetes manifests are located
  destination:
    server: https://kubernetes.default.svc # This refers to the in-cluster Kubernetes API server
    namespace: ms2
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
    - CreateNamespace=true # Automatically create the target namespace if it doesn't exist
```
*   **`source`**: Points to *this* GitHub repository and the `k8s` folder.
*   **`destination`**: Tells ArgoCD to deploy into the `ms2` namespace.
*   **`syncPolicy`**:
    *   `automated`: ArgoCD automatically applies changes found in Git.
    *   `selfHeal`: If you manually delete a pod, ArgoCD will recreate it to match Git.
    *   `prune`: If you remove a file from Git, ArgoCD deletes the resource from the cluster.

### 5.3 Deploying via ArgoCD

```bash
kubectl apply -f argocd-app.yaml
```

Now, ArgoCD monitors the repository. If you push a change to the `k8s` folder, ArgoCD will automatically update the cluster.

> **[INSERT SCREENSHOT HERE]**
> *Description: A screenshot of the ArgoCD UI (accessed via port-forwarding) showing the "milestone2-app" as "Healthy" and "Synced".*

---

## 6. Verification & Conclusion

### 6.1 Accessing the Application

1.  **DNS Spoofing**: Since we don't own `lvms2.com`, we map it to localhost.
    *   Edit `C:\Windows\System32\drivers\etc\hosts` (Windows) or `/etc/hosts` (Linux/Mac).
    *   Add: `127.0.0.1 lvms2.com`
2.  Open browser to `http://lvms2.com`.

> **[INSERT SCREENSHOT HERE]**
> *Description: A screenshot of your web browser showing the running application at `http://lvms2.com`. It should display "Len Vogels has reached milestone 2!" and a container ID.*

### 6.2 Conclusion

We have successfully:
1.  Containerized a 3-tier application.
2.  Verified it locally with Docker Compose.
3.  Provisioned a local Kubernetes cluster with KIND.
4.  Deployed the app using standard Manifests.
5.  Implemented GitOps using ArgoCD for automated delivery.

This setup mimics a professional production environment, providing scalability, reliability, and automated deployment workflows.
