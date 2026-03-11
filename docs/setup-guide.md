# Setup Guide — Pakistan FMR Downloader

## AWS Resources Checklist

### ✅ S3 Bucket
- Name: `pakistan-fmr-reports`
- Region: `us-east-1`
- Access: Private

### ✅ IAM Role — FMR_Roles
Permissions:
- `AmazonSNSFullAccess`
- `FMR-Lambda-S3-Policy` (custom):
  - s3:PutObject
  - s3:GetObject
  - s3:ListBucket
  - logs:CreateLogGroup
  - logs:CreateLogStream
  - logs:PutLogEvents

### ✅ Lambda Function — fmr-downloader
- Runtime: Python 3.12
- Architecture: x86_64
- Memory: 1024 MB
- Timeout: 10 minutes
- Layer: bs4-requests-layer

### ✅ Lambda Layer — bs4-requests-layer
```bash
mkdir python
pip install requests beautifulsoup4 -t python/
zip -r bs4_layer.zip python/
```

### ✅ EventBridge Rule — fmr-monthly-schedule
```
cron(0 1 1-10 * ? *)
```
Matlab: UTC 1 AM = PKT 6 AM, Days 1-10 of every month

### ✅ SNS Topic — fmr-alerts
- Type: Standard
- Subscription: Email

## GitHub Actions Setup

### AWS IAM User banana (for GitHub)
```
IAM → Users → Create user
Name: github-fmr-deploy
Permissions: AWSLambdaFullAccess

Access keys banao → copy karo
```

### GitHub Secrets Add Karo
```
Repo → Settings → Secrets and variables → Actions → New secret

AWS_ACCESS_KEY_ID     = AKIA...
AWS_SECRET_ACCESS_KEY = ...
```

### Auto Deploy Test Karo
```bash
# Koi bhi change karo src/ mein
git add src/lambda_function.py
git commit -m "Update AMC URLs"
git push origin main

# GitHub → Actions tab → Deploy running dikhega!
```

## Monthly Maintenance Checklist

Har mahine email check karo:
- [ ] ✅ Email aaya? Sab AMCs successful?
- [ ] ❌ Koi AMC fail hua? → CloudWatch logs dekho → URL fix karo
- [ ] ⚠️ Faysal manually download karo → S3 upload karo

## Troubleshooting

### 403 Error
```
Matlab: Website ne block kar diya
Fix: Headers update karo ya URL check karo
```

### 404 Error  
```
Matlab: URL galat hai — naming convention change hui
Fix: AMC website manually check karo → sahi URL dhundo → code update karo
```

### Lambda Timeout
```
Matlab: 10 min se zyada lag raha hai
Fix: Memory 1024MB se 2048MB karo
```
