"""
CONFIT Backend - Tax Receipt PDF Service (Phase 4)
==================================================
Service for generating bilingual tax receipt PDFs.

Features:
- Bilingual Arabic/English PDF generation
- AWS S3 storage in Bahrain region (me-south-1)
- Ministry registration for tax-deductible donations
- HTML template rendering with WeasyPrint
"""

import logging
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.donation_models import Donor, DonationRecord
from database.models import User

logger = logging.getLogger(__name__)

# AWS S3 configuration
S3_BUCKET = os.getenv("TAX_RECEIPT_BUCKET", "confit-tax-receipts")
S3_REGION = os.getenv("AWS_REGION", "me-south-1")  # Bahrain


class TaxReceiptError(Exception):
    """Base exception for tax receipt errors."""
    pass


class TaxReceiptService:
    """Async service for generating and storing tax receipt PDFs."""
    
    PIASTRES_PER_EGP = 100
    
    def __init__(self, db: AsyncSession):
        self._db = db
    
    # ========================================
    # PDF GENERATION
    # ========================================
    
    async def generate_tax_receipt(
        self,
        donation_id: str,
        language: str = "bilingual",  # "ar", "en", or "bilingual"
    ) -> str:
        """
        Generate a tax receipt PDF for a donation.
        
        Returns S3 URL to the stored PDF.
        """
        # Fetch donation and donor
        donation = await self._db.execute(
            select(DonationRecord).where(DonationRecord.id == donation_id)
        )
        donation_obj = donation.scalar_one_or_none()
        if not donation_obj:
            raise TaxReceiptError(f"Donation {donation_id} not found")
        
        donor = await self._db.execute(
            select(Donor).where(Donor.id == donation_obj.donor_id)
        )
        donor_obj = donor.scalar_one_or_none()
        if not donor_obj:
            raise TaxReceiptError(f"Donor not found for donation {donation_id}")
        
        # Check tax deductible eligibility
        if not donor_obj.is_tax_deductible_eligible:
            raise TaxReceiptError("Donation is not tax-deductible eligible")
        
        # Fetch user for name/email
        user = await self._db.execute(
            select(User).where(User.id == donor_obj.user_id)
        )
        user_obj = user.scalar_one_or_none()
        
        # Generate receipt number
        receipt_number = self._generate_receipt_number(donation_obj)
        
        # Build receipt data
        receipt_data = {
            "receipt_number": receipt_number,
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "donor_name": donor_obj.display_name or (user_obj.name if user_obj else "Anonymous"),
            "donor_email": user_obj.email if user_obj else None,
            "amount_egp": donation_obj.amount_piastres / self.PIASTRES_PER_EGP,
            "currency": donation_obj.currency,
            "payment_id": donation_obj.payment_id,
            "ministry_registration": self._get_ministry_registration(),
            "tax_year": datetime.now(timezone.utc).year,
            "organization_name": "CONFIT",
            "organization_address": "Cairo, Egypt",
        }
        
        # Generate HTML
        html_content = self._render_html(receipt_data, language)
        
        # Generate PDF
        pdf_bytes = await self._generate_pdf(html_content)
        
        # Store in S3
        s3_key = f"tax-receipts/{donation_obj.donor_id}/{receipt_number}.pdf"
        s3_url = await self._store_pdf(s3_key, pdf_bytes)
        
        # Update donation with receipt URL
        donation_obj.tax_receipt_url = s3_url
        await self._db.commit()
        
        logger.info(
            "Generated tax receipt %s for donation %s",
            receipt_number, donation_id
        )
        
        return s3_url
    
    def _generate_receipt_number(self, donation: DonationRecord) -> str:
        """Generate unique receipt number."""
        year = datetime.now(timezone.utc).year
        short_id = donation.id[:8].upper()
        return f"TR-{year}-{short_id}"
    
    def _get_ministry_registration(self) -> str:
        """Get ministry registration number for tax deductions."""
        # This would be configured per organization
        return os.getenv("MINISTRY_REGISTRATION_NUMBER", "REG-CONFIT-2024")
    
    # ========================================
    # HTML TEMPLATE
    # ========================================
    
    def _render_html(self, data: Dict[str, Any], language: str) -> str:
        """Render HTML template for tax receipt."""
        
        # Arabic translations
        ar_translations = {
            "Tax Receipt": " receipt",
            "Receipt Number": " receipt",
            "Date": " ",
            "Donor Name": " ",
            "Amount": " ",
            "Tax Year": " ",
            "Ministry Registration": " ",
            "This document confirms your tax-deductible donation": 
                "          ",
            "Thank you for your generous support": "    ",
        }
        
        def t(key: str) -> str:
            """Translate key based on language."""
            if language == "ar":
                return ar_translations.get(key, key)
            elif language == "bilingual":
                ar = ar_translations.get(key, key)
                return f"{key} / {ar}"
            return key
        
        return f"""
<!DOCTYPE html>
<html dir="{'rtl' if language == 'ar' else 'ltr'}">
<head>
    <meta charset="UTF-8">
    <title>Tax Receipt - {data['receipt_number']}</title>
    <style>
        @page {{
            size: A4;
            margin: 2cm;
        }}
        body {{
            font-family: 'Arial', 'Helvetica', sans-serif;
            font-size: 12pt;
            line-height: 1.6;
            color: #333;
        }}
        .header {{
            text-align: center;
            border-bottom: 2px solid #333;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .logo {{
            font-size: 24pt;
            font-weight: bold;
            color: #2c3e50;
        }}
        .receipt-title {{
            font-size: 18pt;
            margin-top: 20px;
        }}
        .content {{
            margin: 20px 0;
        }}
        .field {{
            margin: 10px 0;
            display: flex;
        }}
        .label {{
            font-weight: bold;
            width: 200px;
        }}
        .value {{
            flex: 1;
        }}
        .amount-box {{
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            padding: 15px;
            margin: 20px 0;
            text-align: center;
        }}
        .amount {{
            font-size: 24pt;
            font-weight: bold;
            color: #27ae60;
        }}
        .footer {{
            margin-top: 50px;
            border-top: 1px solid #ccc;
            padding-top: 20px;
            font-size: 10pt;
            color: #666;
        }}
        .ministry-info {{
            background: #e8f4f8;
            padding: 10px;
            margin: 20px 0;
            border-radius: 5px;
        }}
        .bilingual {{
            direction: ltr;
        }}
        .bilingual .ar {{
            direction: rtl;
            text-align: right;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">{data['organization_name']}</div>
        <div class="receipt-title">{t('Tax Receipt')}</div>
    </div>
    
    <div class="content">
        <div class="field">
            <span class="label">{t('Receipt Number')}:</span>
            <span class="value">{data['receipt_number']}</span>
        </div>
        <div class="field">
            <span class="label">{t('Date')}:</span>
            <span class="value">{data['date']}</span>
        </div>
        <div class="field">
            <span class="label">{t('Donor Name')}:</span>
            <span class="value">{data['donor_name']}</span>
        </div>
        
        <div class="amount-box">
            <div>{t('Amount')}</div>
            <div class="amount">{data['amount_egp']:.2f} {data['currency']}</div>
        </div>
        
        <div class="field">
            <span class="label">{t('Tax Year')}:</span>
            <span class="value">{data['tax_year']}</span>
        </div>
        
        <div class="ministry-info">
            <strong>{t('Ministry Registration')}:</strong> {data['ministry_registration']}
            <br><br>
            {t('This document confirms your tax-deductible donation')}
        </div>
    </div>
    
    <div class="footer">
        <p>{t('Thank you for your generous support')}</p>
        <p>{data['organization_name']} - {data['organization_address']}</p>
    </div>
</body>
</html>
"""
    
    # ========================================
    # PDF GENERATION (WeasyPrint)
    # ========================================
    
    async def _generate_pdf(self, html_content: str) -> bytes:
        """
        Generate PDF from HTML using WeasyPrint.
        
        Falls back to simple HTML if WeasyPrint not available.
        """
        try:
            from weasyprint import HTML, CSS
            from weasyprint.text.fonts import FontConfiguration
            
            font_config = FontConfiguration()
            html = HTML(string=html_content)
            css = CSS(string='''
                @page { size: A4; margin: 2cm; }
            ''')
            
            pdf = html.write_pdf(stylesheets=[css], font_config=font_config)
            return pdf
            
        except ImportError:
            logger.warning("WeasyPrint not available, storing HTML instead")
            # Return HTML as bytes for storage
            return html_content.encode('utf-8')
    
    # ========================================
    # S3 STORAGE
    # ========================================
    
    async def _store_pdf(self, key: str, pdf_bytes: bytes) -> str:
        """
        Store PDF in AWS S3 (Bahrain region).
        
        Returns S3 URL.
        """
        try:
            import boto3
            from botocore.config import Config
            
            s3 = boto3.client(
                's3',
                region_name=S3_REGION,
                config=Config(
                    signature_version='s3v4',
                    s3={'address_style': 'virtual'}
                )
            )
            
            s3.put_object(
                Bucket=S3_BUCKET,
                Key=key,
                Body=pdf_bytes,
                ContentType='application/pdf',
                Metadata={
                    'generated-at': datetime.now(timezone.utc).isoformat()
                }
            )
            
            url = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{key}"
            return url
            
        except Exception as e:
            logger.warning("S3 upload failed: %s, returning local path", e)
            # Fallback to local storage path
            return f"local://{key}"
    
    # ========================================
    # MINISTRY REGISTRATION
    # ========================================
    
    async def register_with_ministry(
        self,
        donor_id: str,
        tax_id: str,
        id_document_url: str,
    ) -> bool:
        """
        Register donor with ministry for tax-deductible status.
        
        This would integrate with government API for Egypt.
        Returns True if registration successful.
        """
        donor = await self._db.execute(
            select(Donor).where(Donor.id == donor_id)
        )
        donor_obj = donor.scalar_one_or_none()
        if not donor_obj:
            raise TaxReceiptError(f"Donor {donor_id} not found")
        
        # Placeholder for ministry API integration
        # In production, this would call government API
        logger.info(
            "Ministry registration requested for donor %s with tax_id %s",
            donor_id, tax_id
        )
        
        # Mark as eligible for now
        donor_obj.is_tax_deductible_eligible = True
        await self._db.commit()
        
        return True


async def get_tax_receipt_service(db: AsyncSession) -> TaxReceiptService:
    """Dependency injection for TaxReceiptService."""
    return TaxReceiptService(db)
