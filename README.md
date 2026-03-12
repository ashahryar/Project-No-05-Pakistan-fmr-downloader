# Pakistan AMC FMR Downloader 🇵🇰

Automatically downloads monthly Fund Manager Reports (FMRs) from Pakistan's top AMCs and stores them in AWS S3.

## What it does

- Runs automatically every month (1st–10th) via AWS EventBridge
- Downloads FMR PDFs from 9 Pakistan AMCs
- Saves to S3: `pakistan-fmr-reports/YYYY-MM/amc_name/file.pdf`
- Sends email alert via SNS on success or failure

## AMCs Covered

| AMC | Method | Status |
|-----|--------|--------|
| Al Meezan Investments | Direct URL | ✅ Automated |
| Atlas Asset Management | Direct URL | ✅ Automated |
| NBP Funds | Direct URL | ✅ Automated |
| NAFA / NBP Islamic | Direct URL | ✅ Automated |
| HBL Asset Management | Scraping | ✅ Automated |
| UBL Fund Managers | Scraping | ✅ Automated |
| MCB Funds (Alhamra) | Direct URL | ✅ Automated |
| JS Investments | Scraping | ✅ Automated |
| Faysal Asset Management | Manual | ⚠️ CloudFlare Block |

## AWS Setup

| Service | Detail |
|---------|--------|
| Lambda | Python 3.12, 1024MB, 10min timeout |
| S3 Bucket | `pakistan-fmr-reports` |
| EventBridge | `cron(0 1 1-10 * ? *)` — 6AM PKT, days 1–10 |
| SNS | Email alert on success/failure |
| Layer | requests + beautifulsoup4 |

## How to Deploy

1. Create Lambda function (`fmr-downloader`)
2. Add Lambda layer (requests + bs4)
3. Set environment variables:
   ```
   S3_BUCKET_NAME = pakistan-fmr-reports
   SNS_TOPIC_ARN  = arn:aws:sns:...
   ```
4. Upload `lambda_function.py`
5. Add EventBridge trigger

## Faysal — Manual Step

CloudFlare blocks AWS IPs so Faysal can't be automated.

Every month:
1. Download FMR from [faysalfunds.com](https://www.faysalfunds.com)
2. Upload to `s3://pakistan-fmr-reports/YYYY-MM/faysal_asset/`

## Tech Stack

- Python 3.12
- requests + BeautifulSoup4
- AWS Lambda, S3, EventBridge, SNS, CloudWatch
