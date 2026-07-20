# 🚀 Complete Step-by-Step AWS Deployment Guide

This guide provides step-by-step instructions to deploy **ContractSimplifier** (React Frontend + FastAPI Backend) to **Amazon Web Services (AWS)** using Docker.

---

## 📋 Overview & Architecture

The application uses a **multi-stage Dockerfile**:
1. **Stage 1 (Node.js)**: Builds the React frontend into static HTML/JS/CSS assets.
2. **Stage 2 (Python 3.12)**: Serves both the FastAPI backend (`/api/analyze`) and the static React frontend from a single container on **port 8000**.

Because the entire app runs inside one container, you can deploy it easily using **AWS App Runner** (recommended) or **AWS EC2**.

---

## 🏆 Method 1: AWS App Runner via GitHub (Recommended — 5 Minutes)

AWS App Runner automatically builds your Docker image, manages SSL/HTTPS certificates, auto-scales, and provides a public domain.

### Step 1: Push Your Code to GitHub
Ensure your code is pushed to your GitHub repository:
```bash
git add .
git commit -m "Prepare for AWS deployment"
git push origin main
```

### Step 2: Open AWS App Runner
1. Log into the [AWS Management Console](https://console.aws.amazon.com/).
2. Search for **App Runner** in the top search bar and click **Create service**.

### Step 3: Connect Source Repository
1. Under **Source**, select **Source code repository**.
2. Under **Connect to GitHub**, click **Add new** and authorize AWS to access your GitHub account.
3. Select your repository (`contractsimplifier-ibm-aicte-alpha1`) and branch (`main`).
4. Under **Deployment trigger**, select **Automatic** (deploys automatically whenever you push code).
5. Click **Next**.

### Step 4: Configure Build Settings
1. Under **Build settings**, select **Use a Dockerfile**.
2. **Dockerfile path**: `Dockerfile` (leave as default).
3. **Port**: `8000` (FastAPI container port).
4. Click **Next**.

### Step 5: Configure Service & Environment Variables
1. **Service name**: `contractsimplifier`
2. **Virtual CPU & Memory**: `1 vCPU, 2 GB` (default is sufficient).
3. **Environment variables**: Add your API key(s):
   - Key: `GROQ_API_KEY` | Value: `your_real_groq_api_key`
   - Key: `GEMINI_API_KEY` | Value: `your_real_gemini_api_key` *(Optional fallback)*
4. Click **Next**, review your configuration, and click **Create & deploy**.

### Step 6: Access Your Live Application
AWS will take 3–5 minutes to build and deploy. Once finished, App Runner will provide a live HTTPS URL:
`https://<random-id>.us-east-1.awsapprunner.com`

---

## 📦 Method 2: AWS App Runner via ECR (Container Registry)

If you prefer building the Docker image locally or in CI/CD before pushing to AWS:

### Step 1: Create an ECR Repository
1. Open the **Amazon ECR** console.
2. Click **Create repository**.
3. Name: `contractsimplifier` -> Click **Create repository**.

### Step 2: Build & Push Image from Terminal
Run the commands provided in your ECR repository's **"View push commands"** button:

```bash
# 1. Authenticate Docker to AWS ECR (replace aws_account_id & region)
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <aws_account_id>.dkr.ecr.us-east-1.amazonaws.com

# 2. Build the Docker image locally
docker build -t contractsimplifier .

# 3. Tag the image for ECR
docker tag contractsimplifier:latest <aws_account_id>.dkr.ecr.us-east-1.amazonaws.com/contractsimplifier:latest

# 4. Push image to ECR
docker push <aws_account_id>.dkr.ecr.us-east-1.amazonaws.com/contractsimplifier:latest
```

### Step 3: Deploy to App Runner
1. Go to **AWS App Runner** -> **Create service**.
2. Select **Container registry** -> **Amazon ECR**.
3. Choose your image URI (`contractsimplifier:latest`).
4. Set Port to `8000`, add your `GROQ_API_KEY` under Environment Variables, and click **Deploy**.

---

## 🖥️ Method 3: AWS EC2 (Virtual Machine)

If you prefer running on a standard Virtual Private Server (EC2):

### Step 1: Launch an EC2 Instance
1. Open **EC2 Console** -> Click **Launch Instance**.
2. Name: `ContractSimplifier-Server`
3. AMI: **Ubuntu Server 24.04 LTS** (Free tier eligible).
4. Instance type: `t2.micro` or `t3.micro`.
5. Key pair: Select or create an SSH key pair (e.g. `my-key.pem`).
6. **Network Settings**: Check:
   - ✅ Allow SSH traffic from Anywhere
   - ✅ Allow HTTP traffic from the internet
   - ✅ Allow HTTPS traffic from the internet
7. Click **Launch Instance**.

### Step 2: Connect via SSH & Install Docker
```bash
ssh -i "my-key.pem" ubuntu@<YOUR_EC2_PUBLIC_IP>

# Update packages and install Docker
sudo apt update && sudo apt install -y docker.io git
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ubuntu
```
*(Log out and log back in for group changes to take effect)*

### Step 3: Clone Repo & Build Container
```bash
git clone https://github.com/Hassan092-prog/contractsimplifier-ibm-aicte-alpha1.git
cd contractsimplifier-ibm-aicte-alpha1

# Build the Docker image
docker build -t contractsimplifier .
```

### Step 4: Run Container on Port 80 (HTTP)
```bash
docker run -d \
  --name contractsimplifier \
  -p 80:8000 \
  -e GROQ_API_KEY="your_real_groq_api_key" \
  -e GEMINI_API_KEY="your_real_gemini_api_key" \
  --restart always \
  contractsimplifier
```

Your app is now live at: `http://<YOUR_EC2_PUBLIC_IP>`!

---

## 🔍 Verification & Health Check

After deploying using any method, verify your deployment:
- Open `https://<YOUR-APP-URL>/health` in your browser.
- Expected response: `{"status":"ok","version":"0.1.0"}`
- Test uploading a contract PDF or pasting text in the web UI.

---

## 🛡️ Security Checklist for Production
- [ ] Never commit real API keys into Git; pass them via AWS App Runner / EC2 Environment Variables.
- [ ] Maintain free Groq API keys at [console.groq.com](https://console.groq.com).
- [ ] Keep `GEMINI_API_KEY` set as an automatic fallback if Groq rate limits are reached.
