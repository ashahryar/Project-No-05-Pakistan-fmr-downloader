# 🇵🇰 Pakistan AMC FMR Downloader

> Automatically downloads monthly **Fund Manager Reports (FMRs)** from Pakistan's top Asset Management Companies and stores them in AWS S3.

![AWS Lambda](https://img.shields.io/badge/AWS-Lambda-orange?logo=amazon-aws)
![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![S3](https://img.shields.io/badge/AWS-S3-green?logo=amazon-s3)
![EventBridge](https://img.shields.io/badge/AWS-EventBridge-purple?logo=amazon-aws)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)

---

## 📋 Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Supported AMCs](#supported-amcs)
- [Project Structure](#project-structure)
- [Setup Guide](#setup-guide)
- [How It Works](#how-it-works)
- [Maintenance](#maintenance)

---

## 📌 Overview

Har mahine manually 9 alag websites pe jana aur FMR download karna — time-consuming tha.

**Is project ne ye problem solve ki:**

| Pehle | Baad |
|-------|------|
| 9 websites manually visit | ✅ Automatic |
| ~2 hours/month | ✅ 2 min/month |
| Koi reminder nahi | ✅ Email alert aata hai |
| Files scattered | ✅ S3 mein organized |

---

## 🏗️ Architecture

```
EventBridge (Cron)
    │
    │  Har mahine 1-10 tarikh, 6 AM PKT
    ▼
AWS Lambda (Python 3.12)
    │
    ├── Direct URL Download ──► 6 AMCs
    └── Web Scraping ─────────► 2 AMCs
    │
    ├──► S3 Bucket (pakistan-fmr-reports)
    │    └── 2026-02/
    │        ├── al_meezan/
    │        ├── atlas_asset/
    │        └── ... (8 folders)
    │
    └──► SNS → Email Alert
         "✅ FMR Downloaded [2026-02]"
```

---

## 🏦 Supported AMCs

| # | AMC | Method | Status |
|---|-----|--------|--------|
| 1 | Al Meezan Investments | Direct URL | ✅ Automated |
| 2 | Atlas Asset Management | Direct URL | ✅ Automated |
| 3 | NBP Funds | Direct URL | ✅ Automated |
| 4 | NAFA / NBP Islamic | Direct URL | ✅ Automated |
| 5 | HBL Asset Management | Scraping | ✅ Automated |
| 6 | UBL Fund Managers | Scraping | ✅ Automated |
| 7 | MCB Funds (Alhamra) | Direct URL | ✅ Automated |
| 8 | JS Investments | Scraping | ✅ Automated |
| 9 | Faysal Asset Management | Manual | ⚠️ CloudFlare Block |

---

## 📁 Project Structure

```
pakistan-fmr-downloader/
│
├── src/
│   ├── lambda_function.py    # Main Lambda code
│   └── requirements.txt      # Python dependencies
│
├── docs/
│   └── setup-guide.md        # Detailed setup instructions
│
├── .github/
│   └── workflows/
│       └── deploy.yml        # Auto deploy to Lambda on push
│
├── .gitignore
└── README.md
```

---

## ⚙️ Setup Guide

### Prerequisites
- AWS Account
- Python 3.12
- AWS CLI configured

### Step 1 — AWS Resources Banao

**S3 Bucket:**
```bash
aws s3 mb s3://pakistan-fmr-reports --region us-east-1
```

**Lambda Function:**
```
Runtime: Python 3.12
Memory:  1024 MB
Timeout: 10 minutes
```

**Environment Variables:**
```
S3_BUCKET_NAME = pakistan-fmr-reports
SNS_TOPIC_ARN  = arn:aws:sns:us-east-1:XXXXXXXXXXXX:fmr-alerts
```

### Step 2 — Lambda Layer Banao

```bash
mkdir python
pip install requests beautifulsoup4 -t python/
zip -r bs4_layer.zip python/
```

AWS Console → Lambda → Layers → Create layer → Upload ZIP

### Step 3 — EventBridge Schedule

```
cron(0 1 1-10 * ? *)
= Har mahine 1-10 tarikh, 6 AM PKT (1 AM UTC)
```

### Step 4 — GitHub Secrets Add Karo

```
GitHub Repo → Settings → Secrets → Actions

AWS_ACCESS_KEY_ID     = (tumhara AWS key)
AWS_SECRET_ACCESS_KEY = (tumhara AWS secret)
```

### Step 5 — Deploy

```bash
git clone https://github.com/tumhara-username/pakistan-fmr-downloader
cd pakistan-fmr-downloader
git add .
git commit -m "Initial setup"
git push origin main
# GitHub Actions automatically Lambda pe deploy kar dega!
```

---

## 🔄 How It Works

### Direct URL Method
```python
# Kuch AMCs ka URL predictable hota hai
url = f"https://nbpfunds.com/.../FMR-{month}-{year}.pdf"
response = requests.get(url)
# PDF download → S3 upload
```

### Scraping Method
```python
# Kuch AMCs ka URL dynamic hota hai
page = requests.get("https://hblasset.com/downloads/")
soup = BeautifulSoup(page.text, "html.parser")
links = soup.find_all("a", href=True)
# PDF link dhundo → download → S3 upload
```

### Duplicate Check
```python
# Agar file pehle se S3 pe hai → skip karo
s3.head_object(Bucket=bucket, Key=s3_key)
# Already exists → Skipped!
```

---

## 🔧 Maintenance

### Faysal Asset Management (Manual)
CloudFlare block ki wajah se automated nahi ho saka.

**Har mahine karo:**
1. [faysalfunds.com](https://www.faysalfunds.com) → FMR download karo
2. S3 → `pakistan-fmr-reports/YYYY-MM/faysal_asset/` → Upload

### Agar Koi AMC Fail Ho
Email aayega:
```
🚨 FMR Alert — 1 AMC(s) Failed [2026-03]
❌ Failed: hbl_asset
Log Group: /aws/lambda/fmr-downloader
```

**Fix karo:**
1. CloudWatch → Log group → Error dekho
2. AMC ki website check karo — URL change hua?
3. `src/lambda_function.py` mein URL update karo
4. `git push` → Auto deploy ho jayega!

### URL Update Karna
```python
# lambda_function.py mein AMC config dhundo
"nbp_funds": {
    "urls": [
        "https://nbpfunds.com/.../FMR-{Month}-{YYYY}.pdf",  # Update here
    ],
}
```

---

## 📊 S3 Structure

```
pakistan-fmr-reports/
├── 2026-01/
│   ├── al_meezan/AlMeezan-FMR-January-2026.pdf
│   ├── atlas_asset/Atlas-FMR-jan-26.pdf
│   └── ...
├── 2026-02/
│   ├── al_meezan/AlMeezan-FMR-February-2026.pdf
│   └── ...
└── 2026-03/  ← Next month automatic!
```

---

## 🛠️ Tech Stack

| Tool | Use |
|------|-----|
| Python 3.12 | Lambda runtime |
| requests | HTTP requests / PDF download |
| BeautifulSoup4 | HTML scraping |
| boto3 | AWS SDK |
| AWS Lambda | Serverless execution |
| AWS S3 | PDF storage |
| AWS EventBridge | Monthly scheduler |
| AWS SNS | Email notifications |
| AWS CloudWatch | Logs & monitoring |
| GitHub Actions | Auto deployment |

---

## 👤 Author

Built with ❤️ — Pakistan AMC FMR Automation Project
