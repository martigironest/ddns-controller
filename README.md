# Dynamic DNS (DDNS) Cloud Controller

An automated Dynamic DNS (DDNS) management service deployed on AWS EC2, provisioned with Terraform, containerized via Docker, and continuously deployed through GitHub Actions.

The system incorporates a dual-domain isolation architecture to decouple the administrative interface from the target test host, along with direct DNS resolution to bypass intermediate recursive resolver caching.

Designed, developed, and maintained end-to-end by **Martí Girón Estévez** ([@martigironest](https://github.com/martigironest)).

---

## Architecture Overview

The system prevents administrative lockout by separating the management endpoint from the dynamic target domain being updated.

```text
+-------------------------------------------------------------------------+
|                               Client / User                             |
+-------------------------------------------------------------------------+
      |                                              ^
      | 1. HTTP Request                              | 5. Render Verification
      v                                              |
+------------------------------+                     |
| Admin Domain                 |                     |
| (e.g. panel.duckdns.org)     |                     |
| -> Fixed AWS EC2 Public IP   |                     |
+------------------------------+                     |
      |                                              |
      v                                              |
+-------------------------------------------------------------------------+
| AWS EC2 Instance (Ubuntu 24.04 LTS / t3.micro)                          |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  | Docker Engine                                                     |  |
|  |   +-------------------------------------------------------------+ |  |
|  |   | FastAPI Application (Uvicorn / Python 3.11)                 | |  |
|  |   |                                                             | |  |
|  |   |  - Web UI (Jinja2 / Tailwind CSS)                           | |  |
|  |   |  - POST /v1/sync handler                                    | |  |
|  |   |  - Direct DNS Resolver (dnspython)                          | |  |
|  |   +-------------------------------------------------------------+ |  |
|  +-------------------------------------------------------------------+  |
+-------------------------------------------------------------------------+
          |                                       ^
          | 2. HTTPS Update                       | 4. Direct DNS Query
          v                                       |    (1.1.1.1 / 8.8.8.8)
+--------------------+                            |
| DuckDNS REST API   |                            |
+--------------------+                            |
          |                                       |
          | 3. Set A Record                       |
          v                                       |
+----------------------------------------------------+
| Target Domain (e.g. target-ddns.duckdns.org)       |
+----------------------------------------------------+
```

### Dual-Domain Segregation Strategy

1. **Administrative Domain (Fixed):**
   - Resolves directly to the public IPv4 address of the AWS EC2 instance.
   - Hosts the management web interface and API endpoints.
   - Remains completely unchanged during testing to guarantee permanent availability.

2. **Target Domain (Dynamic Test Target):**
   - Serves as the dynamic host manipulated by API operations.
   - Accepts updates (simulated or real) to validate that upstream DNS records propagate as expected.

---

## Live Endpoints

- **Dashboard / Web UI:** `http://<your-admin-domain>.duckdns.org`
- **Target DDNS Record:** `<your-target-domain>.duckdns.org`

### API Specifications

| Method | Endpoint | Description | Parameters |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | Serves the management dashboard and current DNS state. | None |
| `POST` | `/v1/sync` | Submits a new IPv4 address to update the target DDNS record. | `new_ip` (Form field, valid IPv4 format) |

---

## Technology Stack

| Layer | Component | Technical Role |
| :--- | :--- | :--- |
| **Application Runtime** | Python 3.11, FastAPI, Uvicorn | Asynchronous web framework providing HTTP routing and templating. |
| **DNS Resolution** | dnspython 2.6.1 | Bypasses local caching resolvers to perform authoritative status queries. |
| **HTTP Client** | httpx 0.27.0 | Non-blocking async client for DuckDNS API requests. |
| **Containerization** | Docker, Docker Compose | Immutable, reproducible runtime packaging based on `python:3.11-slim`. |
| **Infrastructure as Code** | Terraform (AWS Provider ~> 5.0) | Declarative provisioning of EC2 compute, Security Groups, and AMI resolution. |
| **Cloud Provider** | AWS (Region: `eu-west-1`) | Virtual private cloud compute via EC2 (`t3.micro`, Free Tier compatible). |
| **CI/CD Pipeline** | GitHub Actions | Automated build, test, and zero-downtime SSH deployment to the EC2 host. |

---

## Key Engineering Decisions

### 1. Direct DNS Resolver Cache Bypass
Standard DNS lookups rely on local system daemons and recursive ISP resolvers that honor long TTLs or implement aggressive negative caching. To obtain deterministic verification, the backend queries Cloudflare (`1.1.1.1`) and Google (`8.8.8.8`) DNS resolvers directly via `dnspython` with explicit 2.0-second timeouts.

### 2. Secret Decoupling and Security
No production secrets or API tokens exist within repository commits or static files:
- Infrastructure access relies on isolated SSH key pairs.
- Sensitive credentials (`DUCKDNS_TOKEN`, `TARGET_DOMAIN`) are injected at runtime through GitHub Actions encrypted secrets into the target container environment.

### 3. Resource-Aware Container Lifecycle
To ensure reliability on burstable, memory-constrained cloud instances (`t3.micro`):
- Containers run with `--restart always` to recover from system reboots.
- CI/CD execution includes `docker image prune -f` after image compilation to prevent storage exhaustion.

### 4. Fully Automated Cloud Bootstrap
The EC2 provisioning script utilizes AWS `user_data` (cloud-init) to configure the official Docker repository, install dependencies, set user group permissions, and enable system services without manual SSH intervention.

---

## Repository Structure

```text
.
├── .github/
│   └── workflows/
│       └── deploy.yml          # GitHub Actions CI/CD deployment pipeline
├── app/
│   ├── index.html              # Frontend dashboard (Tailwind CSS, Jinja2)
│   ├── main.py                 # FastAPI application and DNS resolution logic
│   └── requirements.txt        # Python dependency manifest
├── terraform/
│   ├── main.tf                 # EC2, Security Group, and AMI resource definitions
│   ├── outputs.tf              # Public IP and SSH connection string outputs
│   └── variables.tf            # Configurable AWS region, instance, and key variables
├── .env.example                # Template for required environment variables
├── Dockerfile                  # Multi-stage Python container build
└── README.md                   # System documentation
```

---

## Local Development and Testing

### Prerequisites
- Docker Engine 24.0+
- Git

### Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/martigironest/ddns-controller.git
   cd ddns-controller
   ```

2. Create the environment file:
   ```bash
   cp .env.example .env
   ```

3. Update `.env` with your DuckDNS credentials:
   ```env
   DUCKDNS_TOKEN=your-duckdns-token-here
   TARGET_DOMAIN=your-target-subdomain
   ```

4. Build and run the container:
   ```bash
   docker build -t ddns-controller .
   docker run -d -p 80:80 --env-file .env --name ddns-app ddns-controller
   ```

5. Access the local dashboard at `http://localhost`.

---

## Infrastructure Deployment (Terraform)

### Prerequisites
- Terraform >= 1.5.0
- Configured AWS CLI credentials (`aws configure`)

### Steps

1. Navigate to the Terraform directory:
   ```bash
   cd terraform
   ```

2. Initialize providers and modules:
   ```bash
   terraform init
   ```

3. Validate the execution plan:
   ```bash
   terraform plan
   ```

4. Apply the configuration:
   ```bash
   terraform apply -auto-approve
   ```

5. Note the outputs:
   - `public_ip`: IPv4 address assigned to the EC2 instance.
   - `ssh_connection_command`: SSH command to connect to the server.

---

## CI/CD Pipeline Configuration

The GitHub Actions workflow (`.github/workflows/deploy.yml`) triggers on every push to the `main` branch.

### Required GitHub Secrets

Configure the following secrets in your repository settings under **Settings > Secrets and variables > Actions**:

| Secret Name | Description | Example |
| :--- | :--- | :--- |
| `EC2_HOST` | Public IPv4 address of the EC2 instance | `54.216.xxx.xxx` |
| `EC2_USER` | Default system user for the Ubuntu AMI | `ubuntu` |
| `EC2_SSH_KEY` | Private SSH key matching the AWS Key Pair | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `DUCKDNS_TOKEN` | Private authentication token from DuckDNS | `a1b2c3d4-e5f6-7890-abcd-ef1234567890` |
| `TARGET_DOMAIN` | Subdomain managed by the controller | `target-ddns` |

---

## Author & Project Ownership

This project was architected, engineered, and deployed end-to-end as an independent portfolio showcase by:

- **Author:** Martí Girón Estévez
- **GitHub Profile:** [@martigironest](https://github.com/martigironest)
- **Repository:** [martigironest/ddns-controller](https://github.com/martigironest/ddns-controller)

All architectural decisions, Infrastructure as Code configurations, application logic, and automated CI/CD deployment routines were independently authored and implemented by the developer.

---

## References and Upstream Sources

The following official documentation, registries, and marketplaces were leveraged during design and implementation:

- **Infrastructure as Code (IaC):**
  - [Terraform AWS Provider - Terraform Registry](https://registry.terraform.io/providers/hashicorp/aws/latest): Reference for EC2 instance provisioning, data source filtering, and security group ingress/egress rules.
  - [Canonical Ubuntu Cloud Images](https://cloud-images.ubuntu.com/locator/ec2/): AMI locator filters for Ubuntu Noble 24.04 LTS.
- **Continuous Integration & Continuous Deployment (CI/CD):**
  - [GitHub Actions Marketplace](https://github.com/marketplace?type=actions): Ecosystem for workflow automation components.
  - [appleboy/ssh-action (GitHub Marketplace)](https://github.com/marketplace/actions/ssh-remote-commands): Remote SSH action for zero-touch EC2 container deployment.
  - [actions/checkout (GitHub Marketplace)](https://github.com/marketplace/actions/checkout): Standard repository checkout action for GitHub Actions.
- **DNS & Network Specifications:**
  - [DuckDNS Specifications](https://www.duckdns.org/spec.jsp): Public API specification for programmatic dynamic DNS record updates.
  - [RFC 5737 - IPv4 Address Blocks Reserved for Documentation](https://datatracker.ietf.org/doc/html/rfc5737): Standards reference for test-net IP ranges used in demo presets.
- **Application Frameworks & Libraries:**
  - [FastAPI Framework Documentation](https://fastapi.tiangolo.com/): Async route handlers and Jinja2 template integration.
  - [dnspython Documentation](https://www.dnspython.org/): DNS resolver configuration for authoritative upstream queries.
  - [Tailwind CSS CDN](https://tailwindcss.com/docs/installation/play-cdn): Utility-first styling for the client interface.