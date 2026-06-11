#!/bin/sh
# Deploy to Cloud Run from source
# Usage: ./deploy.sh

set -e

echo "Pushing to GitHub..."
git push origin main

echo ""
echo "Deploying to Cloud Run..."
# Resources must match cloudbuild.yaml — the image needs ~8Gi (torch + spacy).
gcloud run deploy picture-book-gen \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 8Gi \
  --cpu 4 \
  --timeout 600 \
  --no-cpu-throttling \
  --min-instances 1 \
  --max-instances 1

echo ""
echo "Done! Live at: https://picture-book-gen-264948620024.us-central1.run.app/"
