"""
Anomaly Detection Service
Detects duplicate invoices and unusual prices
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from rapidfuzz import fuzz

from app.db.mongodb import get_database

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Detects anomalies in invoices such as duplicates and unusual prices"""
    
    # Thresholds
    DUPLICATE_SIMILARITY_THRESHOLD = 85  # % similarity to consider duplicate
    PRICE_ANOMALY_MULTIPLIER = 3.0  # Flag if price is 3x above avg for vendor
    MIN_SAMPLES_FOR_AVERAGE = 2  # Need at least 2 invoices to calculate average
    
    async def detect_anomalies(self, document_id: str) -> Dict[str, Any]:
        """
        Run all anomaly detection on a document.
        
        Returns:
            Dict with detected anomalies
        """
        db = get_database()
        
        # Get the target document
        doc = await db.documents.find_one({"id": document_id})
        if not doc:
            return {"anomalies": [], "error": "Document not found"}
        
        anomalies = []
        
        # Check for duplicates
        duplicate_result = await self.detect_duplicates(doc)
        if duplicate_result:
            anomalies.append(duplicate_result)
        
        # Check for price anomalies
        price_result = await self.detect_price_anomaly(doc)
        if price_result:
            anomalies.append(price_result)
        
        return {
            "document_id": document_id,
            "anomalies": anomalies,
            "anomaly_count": len(anomalies),
            "checked_at": datetime.now().isoformat()
        }
    
    async def detect_duplicates(self, doc: Dict) -> Optional[Dict]:
        """Check if this document is similar to existing ones"""
        db = get_database()
        
        doc_id = doc.get("id", str(doc.get("_id", "")))
        metadata = doc.get("metadata", {})
        
        # Get all other documents
        other_docs = await db.documents.find({"id": {"$ne": doc_id}}).to_list(length=500)
        
        if not other_docs:
            return None
        
        best_match = None
        best_score = 0
        
        for other in other_docs:
            other_meta = other.get("metadata", {})
            
            # Calculate similarity score based on multiple factors
            score = 0
            factors = 0
            
            # Invoice number similarity
            if metadata.get("invoice_number") and other_meta.get("invoice_number"):
                inv_sim = fuzz.ratio(
                    str(metadata["invoice_number"]).lower(),
                    str(other_meta["invoice_number"]).lower()
                )
                score += inv_sim
                factors += 1
            
            # Vendor similarity
            if metadata.get("vendor") and other_meta.get("vendor"):
                vendor_sim = fuzz.ratio(
                    str(metadata["vendor"]).lower(),
                    str(other_meta["vendor"]).lower()
                )
                score += vendor_sim
                factors += 1
            
            # Total amount match (exact match = high weight)
            if metadata.get("total") and other_meta.get("total"):
                try:
                    if float(metadata["total"]) == float(other_meta["total"]):
                        score += 100
                        factors += 1
                except (ValueError, TypeError):
                    pass
            
            # Date match
            if metadata.get("date") and other_meta.get("date"):
                if str(metadata["date"]) == str(other_meta["date"]):
                    score += 100
                    factors += 1
            
            # Calculate average similarity
            if factors > 0:
                avg_score = score / factors
                if avg_score > best_score:
                    best_score = avg_score
                    best_match = other
        
        # If similarity exceeds threshold, flag as potential duplicate
        if best_score >= self.DUPLICATE_SIMILARITY_THRESHOLD and best_match:
            return {
                "type": "duplicate",
                "severity": "warning" if best_score < 95 else "high",
                "message": f"Potential duplicate of invoice {best_match.get('filename', 'Unknown')}",
                "similarity_score": round(best_score, 1),
                "similar_document_id": best_match.get("id", str(best_match.get("_id", ""))),
                "similar_document_name": best_match.get("filename", "Unknown")
            }
        
        return None
    
    async def detect_price_anomaly(self, doc: Dict) -> Optional[Dict]:
        """Check if price is unusually high for this vendor"""
        db = get_database()
        
        metadata = doc.get("metadata", {})
        vendor = metadata.get("vendor")
        total = metadata.get("total")
        
        if not vendor or not total:
            return None
        
        try:
            current_total = float(total)
        except (ValueError, TypeError):
            return None
        
        # Get historical invoices from same vendor
        doc_id = doc.get("id", str(doc.get("_id", "")))
        vendor_docs = await db.documents.find({
            "id": {"$ne": doc_id},
            "metadata.vendor": {"$regex": vendor, "$options": "i"}
        }).to_list(length=100)
        
        if len(vendor_docs) < self.MIN_SAMPLES_FOR_AVERAGE:
            return None
        
        # Calculate average and detect anomaly
        totals = []
        for vdoc in vendor_docs:
            vmeta = vdoc.get("metadata", {})
            if vmeta.get("total"):
                try:
                    totals.append(float(vmeta["total"]))
                except (ValueError, TypeError):
                    pass
        
        if not totals:
            return None
        
        avg_total = sum(totals) / len(totals)
        
        # Flag if current total is significantly higher than average
        if current_total > avg_total * self.PRICE_ANOMALY_MULTIPLIER:
            return {
                "type": "price_anomaly",
                "severity": "warning",
                "message": f"Amount ${current_total:,.2f} is {current_total/avg_total:.1f}x higher than average (${avg_total:,.2f}) for {vendor}",
                "current_amount": current_total,
                "average_amount": round(avg_total, 2),
                "vendor": vendor,
                "multiplier": round(current_total / avg_total, 1)
            }
        
        return None


# Global instance
_anomaly_detector: AnomalyDetector | None = None


def get_anomaly_detector() -> AnomalyDetector:
    """Get or create anomaly detector instance"""
    global _anomaly_detector
    if _anomaly_detector is None:
        _anomaly_detector = AnomalyDetector()
    return _anomaly_detector
