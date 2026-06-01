# Cloud Deployment Guide (RunPod)

This guide covers how to deploy the GPU Worker (Celery + Models) on a RunPod instance.

## 1. Provision a RunPod Instance

- **GPU:** NVIDIA A100 (80GB VRAM) or at minimum a 48GB GPU (e.g. RTX 6000 Ada).
- **Template:** RunPod PyTorch Template (Ubuntu 22.04 + PyTorch 2.1+).
- **Storage:** 
  - Container Disk: 20GB
  - Volume (Persistent): **200GB** (Crucial for storing Wan, CogVideo, and Llama weights).
- **Ports:** Expose SSH. You do not need to expose HTTP ports because the Celery worker reaches out to your Cloud Redis to fetch jobs.

## 2. Setup the Worker Environment

SSH into the instance and run the following commands to install Docker and clone the repo:

```bash
apt-get update && apt-get install -y docker.io docker-compose git
git clone <your-github-repo-url> videoai
cd videoai
```

## 3. Configure the Environment Variables

Create a `.env` file in the `backend/` directory on the worker:

```env
# Cloud Database (e.g. Supabase or Render)
DATABASE_URL_SYNC=postgresql+psycopg2://user:password@your-cloud-db:5432/videoai

# Cloud Redis (e.g. Upstash or Render)
REDIS_URL=redis://your-cloud-redis:6379/0
CELERY_BROKER_URL=redis://your-cloud-redis:6379/0
CELERY_RESULT_BACKEND=redis://your-cloud-redis:6379/1

# Cloudflare R2 / AWS S3 for saving generated videos
R2_ACCOUNT_ID=your_account_id
R2_ACCESS_KEY=your_access_key
R2_SECRET_KEY=your_secret_key
R2_BUCKET_NAME=videoai
R2_PUBLIC_URL=https://your-public-r2-domain.com

# Model Auth
HF_TOKEN=your_huggingface_token
```

## 4. Run the Worker

Use Docker Compose to build and start *only* the worker service.

```bash
docker-compose up -d --build worker
```

To monitor the logs and ensure models are downloading correctly:
```bash
docker-compose logs -f worker
```

## 5. Deploy Frontend & API

- **Frontend:** Push to Vercel. Set `NEXT_PUBLIC_API_URL` to your cloud backend URL.
- **Backend API:** Push to Render or Fly.io. Ensure the `DATABASE_URL` and `REDIS_URL` match what is used by the worker.

You're good to go! The API will queue jobs, and the RunPod worker will seamlessly process them and upload the results to R2.
