# lambda_function.py
# ============================================================
# AWS Lambda — Pakistan AMC FMR Downloader v4.0
#
# Fixes in this version:
# 1. lxml → html.parser (built-in, no layer needed)
# 2. SSL verify=False (JS Investments SSL issue)
# 3. Better headers (403 fix for MCB, Meezan)
# 4. UBL + Faysal → scrape instead of direct URL
# ============================================================

import json
import os
import boto3
import requests
from bs4 import BeautifulSoup
from datetime import date, timedelta
import os
import logging
import urllib3

# SSL warnings suppress karo (verify=False ke liye)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── Logging ──
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ── S3 Client ──
s3 = boto3.client("s3")
BUCKET_NAME = os.environ["S3_BUCKET_NAME"]

# ── Requests Session ──
# Better headers — bot detection se bachne ke liye
session = requests.Session()
session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
})


# ============================================================
# PART 1: DATE HELPER
# ============================================================

def get_previous_month_parts():
    """Previous month calculate karta hai. March 2026 → February 2026"""
    today = date.today()
    prev = today.replace(day=1) - timedelta(days=1)
    return {
        "YYYY":        prev.strftime("%Y"),
        "YY":          prev.strftime("%y"),
        "MM":          prev.strftime("%m"),
        "Month":       prev.strftime("%B"),
        "Month_lower": prev.strftime("%B").lower(),  # february, march etc.
        "Mon":         prev.strftime("%b"),
        "MON":         prev.strftime("%b").upper(),
        "mon":         prev.strftime("%b").lower(),
        "year_month":  prev.strftime("%Y-%m"),
    }


def build_url(pattern, parts):
    """URL pattern mein date values fill karta hai."""
    url = pattern
    for key, val in parts.items():
        url = url.replace("{" + key + "}", val)
    return url


# ============================================================
# PART 2: AMC CONFIGURATIONS
# ============================================================

AMC_CONFIGS = {

    # ── Direct URL AMCs ──

    "al_meezan": {
        "name": "Al Meezan Investment Management",
        "method": "direct",
        "urls": [
            "https://www.almeezangroup.com/assets/uploads/{YYYY}/{MM}/FMR-{Month}-{YYYY}.pdf",
            "https://www.almeezangroup.com/wp-content/uploads/{YYYY}/{MM}/FMR-{Month}-{YYYY}.pdf",
        ],
        "s3_folder": "al_meezan",
        "filename": "AlMeezan-FMR-{Month}-{YYYY}.pdf",
        "ssl_verify": True,
    },

    "atlas_asset": {
        "name": "Atlas Asset Management",
        "method": "direct",
        "urls": [
            "https://www.atlasfunds.com.pk/downloads/fmr/fmr_{mon}-{YY}-conventional.pdf",
            "https://www.atlasfunds.com.pk/downloads/fmr/fmr_{mon}-{YY}.pdf",
        ],
        "s3_folder": "atlas_asset",
        "filename": "Atlas-FMR-{mon}-{YY}.pdf",
        "ssl_verify": True,
    },

    "nbp_funds": {
        "name": "NBP Funds",
        "method": "direct",
        "urls": [
            "https://www.nbpfunds.com/wp-content/uploads/{YYYY}/{MM}/Complete-FMR-Conventional-{Month}-{YYYY}.pdf",
            "https://www.nbpfunds.com/wp-content/uploads/{YYYY}/{MM}/Complete-FMR-Conventional.pdf",
        ],
        "s3_folder": "nbp_funds",
        "filename": "NBP-FMR-{Month}-{YYYY}.pdf",
        "ssl_verify": True,
    },

    "nafa_nbp": {
        "name": "NAFA / NBP Funds Islamic",
        "method": "direct",
        "urls": [
            "https://www.nbpfunds.com/wp-content/uploads/{YYYY}/{MM}/Complete-FMR-Islamic-{Month}-{YYYY}.pdf",
            "https://www.nbpfunds.com/wp-content/uploads/{YYYY}/{MM}/Complete-FMR-Islamic.pdf",
        ],
        "s3_folder": "nafa_nbp",
        "filename": "NAFA-Islamic-FMR-{Month}-{YYYY}.pdf",
        "ssl_verify": True,
    },

    # ── Scrape AMCs ──
    # (Inki sites pe direct URL kaam nahi karti)

    "hbl_asset": {
        "name": "HBL Asset Management",
        "method": "scrape",
        "listing_url": "https://hblasset.com/downloadcategories/fund-manager-report/",
        "keywords": ["fmr", "fund-manager", "fund_manager", "report"],
        "base_url": "https://hblasset.com",
        "s3_folder": "hbl_asset",
        "filename": "HBL-FMR-{Month}-{YYYY}.pdf",
        "ssl_verify": True,
    },

    "faysal_asset": {
        "name": "Faysal Asset Management",
        # URL confirmed: /uploads/post/download/FMR-{Month}-{YYYY}.pdf
        # Problem: CloudFlare blocks AWS IP on www.faysalfunds.com
        # Solution: Try cerpsuite subdomain (investor portal — different server!)
        "method": "direct",
        "urls": [
            # Investor portal — different server, may not have CloudFlare
            "https://faysalfunds.cerpsuite.com/uploads/post/download/FMR-{Month}-{YYYY}.pdf",
            # Try without www
            "https://faysalfunds.com/uploads/post/download/FMR-{Month}-{YYYY}.pdf",
            # Original with www
            "https://www.faysalfunds.com/uploads/post/download/FMR-{Month}-{YYYY}.pdf",
        ],
        "s3_folder": "faysal_asset",
        "filename": "Faysal-FMR-{Month}-{YYYY}.pdf",
        "ssl_verify": True,
        "extra_headers": {
            "Referer": "https://faysalfunds.cerpsuite.com/",
        },
    },

    "ubl_funds": {
        "name": "UBL Fund Managers",
        "method": "scrape",
        "listing_url": "https://www.ublfunds.com.pk/download/performance-reports/",
        "keywords": ["fmr", "fund", "manager"],
        "base_url": "https://www.ublfunds.com.pk",
        "s3_folder": "ubl_funds",
        "filename": "UBL-FMR-{Month}-{YYYY}.pdf",
        "ssl_verify": False,
        "extra_headers": {
            "Referer": "https://www.ublfunds.com.pk/",
        },
    },

    "mcb_funds": {
        "name": "MCB Funds (Alhamra)",
        # CONFIRMED STATIC URLs from Google search:
        # mcbfunds.com/download/latest_fmrs_for_website/shariah_funds/Alhamra-Islamic-Stock-Fund.pdf
        # These are "latest" URLs — always point to current month PDF!
        # No date in URL — just download latest and upload to dated S3 folder
        "method": "direct",
        "urls": [
            "https://www.mcbfunds.com/download/latest_fmrs_for_website/shariah_funds/Alhamra-Islamic-Stock-Fund.pdf",
            "https://www.mcbfunds.com/download/latest_fmrs_for_website/shariah_funds/Alhamra-Islamic-Income-Fund.pdf",
        ],
        "s3_folder": "mcb_funds",
        "filename": "MCB-FMR-{Month}-{YYYY}.pdf",
        "ssl_verify": True,
        "extra_headers": {
            "Referer": "https://www.mcbfunds.com/",
        },
    },

    "js_investments": {
        "name": "JS Investments",
        "method": "scrape",
        "listing_url": "https://jsil.com/all-downloads/fund-manager-reports/",
        "keywords": ["fmr", "jsil", "fund"],
        "base_url": "https://jsil.com",
        "s3_folder": "js_investments",
        "filename": "JS-FMR-{Month}-{YYYY}.pdf",
        "ssl_verify": False,  # SSL cert issue fix
    },

}


# ============================================================
# PART 3: DOWNLOAD FUNCTIONS
# ============================================================

def download_pdf(url, ssl_verify=True):
    """
    URL se PDF download karta hai.
    Returns: bytes ya None
    """
    try:
        resp = session.get(
            url,
            timeout=30,
            allow_redirects=True,
            verify=ssl_verify,
        )
        if resp.status_code == 200:
            if resp.content[:4] == b"%PDF":
                logger.info(f"✅ {len(resp.content)//1024}KB: {url}")
                return resp.content
            else:
                logger.warning(f"Not a PDF: {url}")
        else:
            logger.warning(f"HTTP {resp.status_code}: {url}")
    except requests.exceptions.SSLError:
        # SSL error pe retry with verify=False
        if ssl_verify:
            logger.warning(f"SSL error, retrying without verify: {url}")
            return download_pdf(url, ssl_verify=False)
    except Exception as e:
        logger.warning(f"Download error: {e}")
    return None


def scrape_pdf_link(config):
    """
    BeautifulSoup se page scrape karta hai.
    FIX: lxml → html.parser (built-in, no install needed)
    Returns: PDF URL ya None
    """
    listing_url = config["listing_url"]
    keywords    = config["keywords"]
    base_url    = config["base_url"]
    ssl_verify  = config.get("ssl_verify", True)
    extra_hdrs  = config.get("extra_headers", {})

    try:
        # Extra headers apply karo (403 fix ke liye)
        resp = session.get(
            listing_url,
            timeout=30,
            verify=ssl_verify,
            headers={**session.headers, **extra_hdrs},
        )

        if resp.status_code != 200:
            logger.warning(f"Page {resp.status_code}: {listing_url}")
            return None

        # ✅ FIX: "lxml" → "html.parser" (Python built-in!)
        soup = BeautifulSoup(resp.text, "html.parser")

        pdf_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            href_lower = href.lower()

            if not href_lower.endswith(".pdf"):
                continue
            if not any(kw in href_lower for kw in keywords):
                continue

            # Relative → Absolute URL
            if href.startswith("http"):
                pdf_links.append(href)
            elif href.startswith("//"):
                pdf_links.append("https:" + href)
            elif href.startswith("/"):
                pdf_links.append(base_url + href)
            else:
                pdf_links.append(base_url + "/" + href)

        if pdf_links:
            logger.info(f"Found {len(pdf_links)} links → {pdf_links[0]}")
            return pdf_links[0]
        else:
            logger.warning(f"No PDF links on: {listing_url}")
            return None

    except Exception as e:
        logger.error(f"Scrape error {listing_url}: {e}")
        return None


# ============================================================
# PART 4: S3 OPERATIONS
# ============================================================

def check_s3_exists(s3_key):
    """Duplicate check — S3 pe file hai ya nahi."""
    try:
        s3.head_object(Bucket=BUCKET_NAME, Key=s3_key)
        return True
    except Exception:
        return False


def upload_to_s3(pdf_bytes, s3_key):
    """PDF S3 pe upload karta hai."""
    try:
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=s3_key,
            Body=pdf_bytes,
            ContentType="application/pdf",
        )
        logger.info(f"✅ S3 uploaded: {s3_key}")
        return True
    except Exception as e:
        logger.error(f"S3 failed: {e}")
        return False


# ============================================================
# PART 5: PROCESS ONE AMC
# ============================================================

def process_amc(amc_key, config, date_parts):
    """
    Ek AMC ka poura flow:
    1. Duplicate check
    2. Download (direct/scrape)
    3. S3 upload
    """
    filename = build_url(config["filename"], date_parts)
    s3_key   = f"{date_parts['year_month']}/{config['s3_folder']}/{filename}"
    ssl      = config.get("ssl_verify", True)

    # Duplicate check
    if check_s3_exists(s3_key):
        logger.info(f"⏭️ Skipped: {s3_key}")
        return "skipped"

    pdf_bytes = None

    if config["method"] == "direct":
        for url_pattern in config["urls"]:
            url = build_url(url_pattern, date_parts)
            pdf_bytes = download_pdf(url, ssl_verify=ssl)
            if pdf_bytes:
                break

    elif config["method"] == "scrape":
        pdf_url = scrape_pdf_link(config)
        if pdf_url:
            pdf_bytes = download_pdf(pdf_url, ssl_verify=ssl)

    if pdf_bytes:
        return "uploaded" if upload_to_s3(pdf_bytes, s3_key) else "failed"

    logger.error(f"❌ No PDF found: {config['name']}")
    return "failed"


# ============================================================
# PART 6: LAMBDA HANDLER
# ============================================================

def lambda_handler(event, context):
    """
    AWS Lambda entry point.
    Trigger: EventBridge cron(0 1 1-10 * ? *)
    """
    logger.info("=" * 60)
    logger.info("FMR Lambda v4.0 — Starting")
    logger.info("=" * 60)

    date_parts = get_previous_month_parts()
    logger.info(f"Target: {date_parts['Month']} {date_parts['YYYY']}")

    results = {"uploaded": [], "skipped": [], "failed": []}

    for amc_key, config in AMC_CONFIGS.items():
        logger.info(f"\n>>> {config['name']} [{config['method'].upper()}]")
        try:
            result = process_amc(amc_key, config, date_parts)
            results[result].append(amc_key)
        except Exception as e:
            logger.error(f"Unexpected: {amc_key} → {e}")
            results["failed"].append(amc_key)

    logger.info("\n" + "=" * 60)
    logger.info("📊 SUMMARY")
    logger.info(f"✅ Uploaded ({len(results['uploaded'])}): {results['uploaded']}")
    logger.info(f"⏭️ Skipped  ({len(results['skipped'])}): {results['skipped']}")
    logger.info(f"❌ Failed   ({len(results['failed'])}): {results['failed']}")
    logger.info("=" * 60)

    # SNS Alert — failure pe email bhejo
    sns_arn = os.environ.get("SNS_TOPIC_ARN")
    if sns_arn:
        try:
            sns = boto3.client("sns")
            month = date_parts["year_month"]

            if results["failed"]:
                # Failure alert
                subject = f"🚨 FMR Alert — {len(results['failed'])} AMC(s) Failed [{month}]"
                message = (
                    f"FMR Downloader Report — {month}\n"
                    f"{'='*40}\n\n"
                    f"✅ Uploaded ({len(results['uploaded'])}): {', '.join(results['uploaded']) or 'None'}\n"
                    f"⏭️ Skipped  ({len(results['skipped'])}): {', '.join(results['skipped']) or 'None'}\n"
                    f"❌ Failed   ({len(results['failed'])}): {', '.join(results['failed'])}\n\n"
                    f"Action needed: Check CloudWatch logs for details.\n"
                    f"Log Group: /aws/lambda/fmr-downloader"
                )
            elif results["uploaded"]:
                # Success — new uploads
                subject = f"✅ FMR Downloaded — {len(results['uploaded'])} new file(s) [{month}]"
                message = (
                    f"FMR Downloader Report — {month}\n"
                    f"{'='*40}\n\n"
                    f"✅ Uploaded ({len(results['uploaded'])}): {', '.join(results['uploaded'])}\n"
                    f"⏭️ Skipped  ({len(results['skipped'])}): {', '.join(results['skipped']) or 'None'}\n"
                    f"❌ Failed   ({len(results['failed'])}): None\n\n"
                    f"All files saved to S3: pakistan-fmr-reports/{month}/"
                )
            else:
                # All skipped — already downloaded
                subject = f"⏭️ FMR Check — All files already in S3 [{month}]"
                message = (
                    f"FMR Downloader Report — {month}\n"
                    f"{'='*40}\n\n"
                    f"All {len(results['skipped'])} AMC files already exist in S3.\n"
                    f"No action needed."
                )

            sns.publish(TopicArn=sns_arn, Subject=subject, Message=message)
            logger.info(f"📧 SNS alert sent: {subject}")
        except Exception as e:
            logger.error(f"SNS send failed: {e}")

    return {
        "statusCode": 200,
        "body": json.dumps({
            "target_month": date_parts["year_month"],
            "uploaded": results["uploaded"],
            "skipped":  results["skipped"],
            "failed":   results["failed"],
        }, indent=2)
    }
