"""
Export Tool for LangGraph Agent
Allows natural language export of invoices to CSV/Excel
"""

import os
import csv
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

from openpyxl import Workbook

from app.db.mongodb import get_database

logger = logging.getLogger(__name__)

# Export directory
EXPORTS_DIR = Path("./exports")
EXPORTS_DIR.mkdir(exist_ok=True)


async def query_invoices(
    vendor: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[Dict]:
    """Query invoices based on filters"""
    db = get_database()
    
    query = {}
    
    if vendor:
        query["metadata.vendor"] = {"$regex": vendor, "$options": "i"}
    
    if status:
        query["validation_status"] = status
    
    if start_date or end_date:
        date_query = {}
        if start_date:
            date_query["$gte"] = start_date
        if end_date:
            date_query["$lte"] = end_date
        if date_query:
            query["upload_timestamp"] = date_query
    
    documents = await db.documents.find(query).to_list(length=1000)
    return documents


def format_invoice_for_export(doc: Dict) -> Dict:
    """Format a document for export"""
    metadata = doc.get("metadata", {})
    return {
        "Document ID": doc.get("id", str(doc.get("_id", ""))),
        "Filename": doc.get("filename", ""),
        "Vendor": metadata.get("vendor", ""),
        "Invoice Number": metadata.get("invoice_number", ""),
        "Date": metadata.get("date", ""),
        "Total": metadata.get("total", ""),
        "Currency": metadata.get("currency", "USD"),
        "Status": doc.get("validation_status", "pending"),
        "Upload Date": doc.get("upload_timestamp", "").isoformat() if hasattr(doc.get("upload_timestamp", ""), "isoformat") else str(doc.get("upload_timestamp", "")),
        "Force Validated": "Yes" if doc.get("forced_valid") else "No"
    }


async def export_to_csv(documents: List[Dict], filename: str) -> str:
    """Export documents to CSV file"""
    filepath = EXPORTS_DIR / filename
    
    if not documents:
        # Create empty file with headers
        headers = ["Document ID", "Filename", "Vendor", "Invoice Number", "Date", "Total", "Currency", "Status", "Upload Date", "Force Validated"]
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
    else:
        formatted = [format_invoice_for_export(doc) for doc in documents]
        headers = list(formatted[0].keys())
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(formatted)
    
    logger.info(f"Exported {len(documents)} invoices to {filepath}")
    return str(filepath)


async def export_to_excel(documents: List[Dict], filename: str) -> str:
    """Export documents to Excel file"""
    filepath = EXPORTS_DIR / filename
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Invoices"
    
    headers = ["Document ID", "Filename", "Vendor", "Invoice Number", "Date", "Total", "Currency", "Status", "Upload Date", "Force Validated"]
    ws.append(headers)
    
    # Style header row
    for cell in ws[1]:
        cell.font = cell.font.copy(bold=True)
    
    if documents:
        formatted = [format_invoice_for_export(doc) for doc in documents]
        for doc in formatted:
            ws.append([doc.get(h, "") for h in headers])
    
    # Auto-adjust column widths
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = adjusted_width
    
    wb.save(filepath)
    logger.info(f"Exported {len(documents)} invoices to {filepath}")
    return str(filepath)


async def export_invoices(
    format: str = "csv",
    vendor: Optional[str] = None,
    status: Optional[str] = None,
    date_range: Optional[str] = None
) -> Dict[str, Any]:
    """
    Export invoices to CSV or Excel format.
    
    Args:
        format: Output format - "csv" or "excel"
        vendor: Optional vendor name filter
        status: Optional status filter (valid, invalid, pending)
        date_range: Optional date range description (e.g., "January 2024", "last 30 days")
    
    Returns:
        Dict with success status and download URL
    """
    try:
        # Parse date range (simplified)
        start_date = None
        end_date = None
        
        # Query invoices
        documents = await query_invoices(
            vendor=vendor,
            status=status,
            start_date=start_date,
            end_date=end_date
        )
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filters_str = ""
        if vendor:
            filters_str += f"_{vendor}"
        if status:
            filters_str += f"_{status}"
        
        if format.lower() == "excel":
            filename = f"invoices{filters_str}_{timestamp}.xlsx"
            filepath = await export_to_excel(documents, filename)
        else:
            filename = f"invoices{filters_str}_{timestamp}.csv"
            filepath = await export_to_csv(documents, filename)
        
        return {
            "success": True,
            "filename": filename,
            "download_url": f"/api/exports/{filename}",
            "invoice_count": len(documents),
            "format": format.lower(),
            "filters_applied": {
                "vendor": vendor,
                "status": status,
                "date_range": date_range
            }
        }
    except Exception as e:
        logger.error(f"Export failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }
