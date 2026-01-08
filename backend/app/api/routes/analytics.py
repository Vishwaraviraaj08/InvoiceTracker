"""
Analytics API Routes
Provides endpoints for dashboard analytics and insights
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import logging

from app.db.mongodb import get_database
from app.core.llm.groq_client import get_groq_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary")
async def get_summary():
    """Get overall analytics summary"""
    db = get_database()
    
    # Get all documents
    documents = await db.documents.find().to_list(length=1000)
    
    total_invoices = len(documents)
    validated_count = sum(1 for d in documents if d.get("validation_status") == "valid")
    invalid_count = sum(1 for d in documents if d.get("validation_status") == "invalid")
    pending_count = sum(1 for d in documents if d.get("validation_status") == "pending")
    
    # Calculate total spend from metadata
    total_spend = 0.0
    for doc in documents:
        metadata = doc.get("metadata", {})
        if metadata and metadata.get("total"):
            try:
                total_spend += float(metadata["total"])
            except (ValueError, TypeError):
                pass
    
    # Average invoice value
    avg_value = total_spend / total_invoices if total_invoices > 0 else 0
    
    return {
        "total_invoices": total_invoices,
        "validated_count": validated_count,
        "invalid_count": invalid_count,
        "pending_count": pending_count,
        "total_spend": round(total_spend, 2),
        "average_invoice_value": round(avg_value, 2),
        "currency": "USD"
    }


@router.get("/spending-trends")
async def get_spending_trends(months: int = 6):
    """Get monthly spending trends"""
    db = get_database()
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months * 30)
    
    # Get documents within range
    documents = await db.documents.find({
        "upload_timestamp": {"$gte": start_date}
    }).to_list(length=1000)
    
    # Group by month
    monthly_data = defaultdict(lambda: {"total": 0, "count": 0})
    
    for doc in documents:
        upload_date = doc.get("upload_timestamp")
        if upload_date:
            month_key = upload_date.strftime("%Y-%m")
            metadata = doc.get("metadata", {})
            if metadata and metadata.get("total"):
                try:
                    monthly_data[month_key]["total"] += float(metadata["total"])
                    monthly_data[month_key]["count"] += 1
                except (ValueError, TypeError):
                    monthly_data[month_key]["count"] += 1
    
    # Convert to sorted list
    trends = []
    for month_key in sorted(monthly_data.keys()):
        data = monthly_data[month_key]
        # Parse month for display
        year, month = month_key.split("-")
        month_name = datetime(int(year), int(month), 1).strftime("%b %Y")
        trends.append({
            "month": month_name,
            "month_key": month_key,
            "total_spend": round(data["total"], 2),
            "invoice_count": data["count"]
        })
    
    return {"trends": trends, "months_included": months}


@router.get("/top-vendors")
async def get_top_vendors(limit: int = 5):
    """Get top vendors by total spend"""
    db = get_database()
    
    documents = await db.documents.find().to_list(length=1000)
    
    vendor_totals = defaultdict(lambda: {"total": 0, "count": 0})
    
    for doc in documents:
        metadata = doc.get("metadata", {})
        vendor = metadata.get("vendor", "Unknown")
        if vendor:
            try:
                total = float(metadata.get("total", 0))
                vendor_totals[vendor]["total"] += total
                vendor_totals[vendor]["count"] += 1
            except (ValueError, TypeError):
                vendor_totals[vendor]["count"] += 1
    
    # Sort by total spend and get top N
    sorted_vendors = sorted(
        vendor_totals.items(),
        key=lambda x: x[1]["total"],
        reverse=True
    )[:limit]
    
    return {
        "vendors": [
            {
                "name": vendor,
                "total_spend": round(data["total"], 2),
                "invoice_count": data["count"]
            }
            for vendor, data in sorted_vendors
        ]
    }


@router.get("/spend-by-status")
async def get_spend_by_status():
    """Get spending breakdown by validation status"""
    db = get_database()
    
    documents = await db.documents.find().to_list(length=1000)
    
    status_data = defaultdict(lambda: {"total": 0, "count": 0})
    
    for doc in documents:
        status = doc.get("validation_status", "pending")
        metadata = doc.get("metadata", {})
        try:
            total = float(metadata.get("total", 0))
            status_data[status]["total"] += total
            status_data[status]["count"] += 1
        except (ValueError, TypeError):
            status_data[status]["count"] += 1
    
    return {
        "breakdown": [
            {
                "status": status,
                "total_spend": round(data["total"], 2),
                "invoice_count": data["count"]
            }
            for status, data in status_data.items()
        ]
    }


@router.get("/ai-insights")
async def get_ai_insights():
    """Generate AI-powered insights about spending patterns"""
    db = get_database()
    
    # Get summary data
    documents = await db.documents.find().to_list(length=1000)
    
    if not documents:
        return {
            "insights": "No invoices uploaded yet. Start by uploading some invoices to get AI-powered insights!",
            "generated_at": datetime.now().isoformat()
        }
    
    # Prepare data summary for LLM
    total_invoices = len(documents)
    vendor_counts = defaultdict(int)
    monthly_totals = defaultdict(float)
    total_spend = 0
    
    for doc in documents:
        metadata = doc.get("metadata", {})
        vendor = metadata.get("vendor", "Unknown")
        vendor_counts[vendor] += 1
        
        try:
            amount = float(metadata.get("total", 0))
            total_spend += amount
            
            upload_date = doc.get("upload_timestamp")
            if upload_date:
                month_key = upload_date.strftime("%B %Y")
                monthly_totals[month_key] += amount
        except (ValueError, TypeError):
            pass
    
    top_vendors = sorted(vendor_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    
    # Create context for LLM
    context = f"""Invoice Analytics Summary:
- Total Invoices: {total_invoices}
- Total Spend: ${total_spend:,.2f}
- Average Invoice: ${total_spend/total_invoices:,.2f}
- Top Vendors: {', '.join([f'{v[0]} ({v[1]} invoices)' for v in top_vendors])}
- Monthly Breakdown: {dict(monthly_totals)}
"""
    
    try:
        groq_client = get_groq_client()
        result = await groq_client.invoke(
            messages=[{"role": "user", "content": "Analyze this invoice data and provide 3-4 brief, actionable insights about spending patterns, trends, or recommendations. Be specific with numbers."}],
            system_prompt=f"You are a financial analyst. Based on this data, provide concise insights:\n\n{context}"
        )
        
        return {
            "insights": result["content"],
            "data_summary": {
                "total_invoices": total_invoices,
                "total_spend": round(total_spend, 2),
                "top_vendors": [v[0] for v in top_vendors]
            },
            "generated_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"AI insights generation failed: {e}")
        return {
            "insights": f"Based on your data: You have {total_invoices} invoices totaling ${total_spend:,.2f}. Your top vendor is {top_vendors[0][0] if top_vendors else 'Unknown'}.",
            "generated_at": datetime.now().isoformat()
        }
