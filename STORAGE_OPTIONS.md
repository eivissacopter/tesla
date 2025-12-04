"""Alternative storage configuration for performance data.

Recommended options for hosting large CSV files:

1. Cloudflare R2 (Best for bandwidth - Zero egress fees)
   - Create R2 bucket
   - Upload CSV files
   - Enable public access or use signed URLs
   - Update PERFORMANCE_BASE_URL in config

2. AWS S3 + CloudFront (Best for global performance)
   - Create S3 bucket
   - Upload files
   - Create CloudFront distribution
   - Caches files globally, reduces bandwidth

3. Google Cloud Storage (Integrates with your GCP)
   - Create GCS bucket
   - Upload files
   - Enable public access
   - Use with Cloud CDN for caching

4. GitHub LFS (Simplest for small scale)
   - Install git-lfs
   - Track *.csv files
   - Push to GitHub
   - Free tier: 1GB storage, 1GB bandwidth/month

Example migration to cloud storage:
"""

# After uploading to cloud storage, just change the config:
# In src/config.py, update:
# PERFORMANCE_BASE_URL = "https://your-bucket.r2.dev/smt/"
# or
# PERFORMANCE_BASE_URL = "https://your-cloudfront-domain.net/smt/"
