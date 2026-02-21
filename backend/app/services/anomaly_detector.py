import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

import numpy as np
from rapidfuzz import fuzz

from app.db.mongodb import get_database

logger = logging.getLogger(__name__)

DUPLICATE_THRESHOLD = 85
PRICE_ANOMALY_MULTIPLIER = 2.0


class AnomalyDetector:
    """Detects anomalies in invoices: duplicates and price outliers."""

    async def check_duplicates(self, document_id: str) -> List[Dict[str, Any]]:
        """Check for duplicate invoices using fuzzy matching."""
        db = get_database()

        target_doc = await db.documents.find_one({"id": document_id})
        if not target_doc:
            return []

        target_metadata = target_doc.get("metadata", {})
        target_vendor = target_metadata.get("vendor", "")
        target_invoice_num = target_metadata.get("invoice_number", "")
        target_total = target_metadata.get("total", 0)

        other_docs = await db.documents.find(
            {"id": {"$ne": document_id}}
        ).to_list(length=100)

        duplicates = []
        for doc in other_docs:
            doc_metadata = doc.get("metadata", {})
            doc_vendor = doc_metadata.get("vendor", "")
            doc_invoice_num = doc_metadata.get("invoice_number", "")
            doc_total = doc_metadata.get("total", 0)

            vendor_score = fuzz.ratio(target_vendor.lower(), doc_vendor.lower()) if target_vendor and doc_vendor else 0
            invoice_num_score = fuzz.ratio(target_invoice_num.lower(), doc_invoice_num.lower()) if target_invoice_num and doc_invoice_num else 0
            total_match = 100 if target_total and doc_total and abs(float(target_total) - float(doc_total)) < 0.01 else 0

            overall_score = (vendor_score * 0.3 + invoice_num_score * 0.4 + total_match * 0.3)

            if overall_score >= DUPLICATE_THRESHOLD:
                duplicates.append({
                    "document_id": doc.get("id", str(doc.get("_id", ""))),
                    "filename": doc.get("filename", ""),
                    "similarity_score": round(overall_score, 2),
                    "matching_fields": {
                        "vendor": {"score": vendor_score, "value": doc_vendor},
                        "invoice_number": {"score": invoice_num_score, "value": doc_invoice_num},
                        "total": {"match": total_match > 0, "value": doc_total}
                    }
                })

        duplicates.sort(key=lambda x: x["similarity_score"], reverse=True)
        return duplicates

    async def check_price_anomalies(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Check for price anomalies by comparing to vendor average."""
        db = get_database()

        target_doc = await db.documents.find_one({"id": document_id})
        if not target_doc:
            return None

        target_metadata = target_doc.get("metadata", {})
        target_vendor = target_metadata.get("vendor", "")
        target_total = target_metadata.get("total", 0)

        if not target_vendor or not target_total:
            return None

        try:
            target_total = float(target_total)
        except (ValueError, TypeError):
            return None

        vendor_docs = await db.documents.find({
            "id": {"$ne": document_id},
            "metadata.vendor": {"$regex": target_vendor, "$options": "i"}
        }).to_list(length=100)

        if len(vendor_docs) < 2:
            return None

        totals = []
        for doc in vendor_docs:
            total = doc.get("metadata", {}).get("total", 0)
            try:
                totals.append(float(total))
            except (ValueError, TypeError):
                continue

        if not totals:
            return None

        avg_total = np.mean(totals)
        std_total = np.std(totals) if len(totals) > 1 else 0

        is_anomaly = target_total > avg_total * PRICE_ANOMALY_MULTIPLIER
        if std_total > 0:
            z_score = (target_total - avg_total) / std_total
            is_anomaly = is_anomaly or abs(z_score) > 2

        if is_anomaly:
            return {
                "is_anomaly": True,
                "current_total": target_total,
                "vendor_average": round(avg_total, 2),
                "vendor_std": round(std_total, 2),
                "deviation_percentage": round(((target_total - avg_total) / avg_total) * 100, 1) if avg_total > 0 else 0,
                "sample_size": len(totals),
                "message": f"Total ${target_total} is significantly higher than the vendor average of ${avg_total:.2f}"
            }
        return None

    async def run_all_checks(self, document_id: str) -> Dict[str, Any]:
        """Run all anomaly checks on a document."""
        duplicates = await self.check_duplicates(document_id)
        price_anomaly = await self.check_price_anomalies(document_id)

        return {
            "document_id": document_id,
            "has_anomalies": bool(duplicates or price_anomaly),
            "duplicates": duplicates,
            "price_anomaly": price_anomaly,
            "checked_at": datetime.utcnow().isoformat()
        }


_anomaly_detector: AnomalyDetector | None = None


def get_anomaly_detector() -> AnomalyDetector:
    """Get or create anomaly detector instance."""
    global _anomaly_detector
    if _anomaly_detector is None:
        _anomaly_detector = AnomalyDetector()
    return _anomaly_detector
