// Dashboard Page with Analytics

import { useState, useCallback, useEffect } from 'react';
import { Container, Row, Col, Card, Alert, Spinner } from 'react-bootstrap';
import { useNavigate } from 'react-router-dom';
import { uploadInvoice } from '../services/api';
import { LoadingOverlay } from '../components/Common';
import FolderWatcher from '../components/FolderWatcher';
import {
    SpendingTrendsChart,
    TopVendorsChart,
    StatusBreakdownChart,
    AIInsightsCard,
    SummaryStatsCards
} from '../components/AnalyticsCharts';

const API_BASE = 'http://localhost:8000';

interface AnalyticsData {
    summary: {
        total_invoices: number;
        validated_count: number;
        invalid_count: number;
        pending_count: number;
        total_spend: number;
        average_invoice_value: number;
    } | null;
    trends: Array<{ month: string; total_spend: number; invoice_count: number }>;
    vendors: Array<{ name: string; total_spend: number; invoice_count: number }>;
    statusBreakdown: Array<{ status: string; total_spend: number; invoice_count: number }>;
    insights: string;
}

const Dashboard = () => {
    const navigate = useNavigate();
    const [isUploading, setIsUploading] = useState(false);
    const [uploadResult, setUploadResult] = useState<{ success: boolean; message: string } | null>(null);
    const [dragOver, setDragOver] = useState(false);

    // Analytics state
    const [analytics, setAnalytics] = useState<AnalyticsData>({
        summary: null,
        trends: [],
        vendors: [],
        statusBreakdown: [],
        insights: ''
    });
    const [loadingAnalytics, setLoadingAnalytics] = useState(true);
    const [loadingInsights, setLoadingInsights] = useState(false);

    // Fetch analytics data
    const fetchAnalytics = useCallback(async () => {
        setLoadingAnalytics(true);
        try {
            const [summaryRes, trendsRes, vendorsRes, statusRes] = await Promise.all([
                fetch(`${API_BASE}/api/analytics/summary`),
                fetch(`${API_BASE}/api/analytics/spending-trends?months=6`),
                fetch(`${API_BASE}/api/analytics/top-vendors?limit=5`),
                fetch(`${API_BASE}/api/analytics/spend-by-status`)
            ]);

            const [summary, trends, vendors, status] = await Promise.all([
                summaryRes.json(),
                trendsRes.json(),
                vendorsRes.json(),
                statusRes.json()
            ]);

            setAnalytics(prev => ({
                ...prev,
                summary,
                trends: trends.trends || [],
                vendors: vendors.vendors || [],
                statusBreakdown: status.breakdown || []
            }));
        } catch (error) {
            console.error('Failed to fetch analytics:', error);
        } finally {
            setLoadingAnalytics(false);
        }
    }, []);

    // Fetch AI insights
    const fetchInsights = useCallback(async () => {
        setLoadingInsights(true);
        try {
            const res = await fetch(`${API_BASE}/api/analytics/ai-insights`);
            const data = await res.json();
            setAnalytics(prev => ({ ...prev, insights: data.insights }));
        } catch (error) {
            console.error('Failed to fetch insights:', error);
        } finally {
            setLoadingInsights(false);
        }
    }, []);

    useEffect(() => {
        fetchAnalytics();
        fetchInsights();
    }, [fetchAnalytics, fetchInsights]);

    const handleUpload = useCallback(async (file: File) => {
        setIsUploading(true);
        setUploadResult(null);

        try {
            const result = await uploadInvoice(file);
            setUploadResult({
                success: true,
                message: `${result.filename} uploaded successfully! Document ID: ${result.doc_id}`,
            });

            // Refresh analytics after upload
            fetchAnalytics();

            // Navigate to documents after short delay
            setTimeout(() => navigate('/documents'), 1500);
        } catch (error: unknown) {
            const err = error as { response?: { data?: { detail?: string } } };
            setUploadResult({
                success: false,
                message: err.response?.data?.detail || 'Upload failed. Please try again.',
            });
        } finally {
            setIsUploading(false);
        }
    }, [navigate, fetchAnalytics]);

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setDragOver(false);

        const file = e.dataTransfer.files[0];
        if (file) {
            handleUpload(file);
        }
    }, [handleUpload]);

    const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            handleUpload(file);
        }
    }, [handleUpload]);

    return (
        <Container className="py-4">
            {isUploading && <LoadingOverlay message="Uploading and processing invoice..." />}

            <Row className="mb-4">
                <Col>
                    <h1 className="mb-1">📊 Dashboard</h1>
                    <p className="text-secondary">Analytics and invoice management</p>
                </Col>
            </Row>

            {uploadResult && (
                <Alert variant={uploadResult.success ? 'success' : 'danger'} dismissible onClose={() => setUploadResult(null)}>
                    {uploadResult.message}
                </Alert>
            )}

            {/* Summary Stats */}
            <SummaryStatsCards stats={analytics.summary} />

            <Row className="g-4 mb-4">
                {/* Spending Trends Chart */}
                <Col lg={8}>
                    <Card className="glass-card h-100">
                        <Card.Body>
                            <h6 className="mb-3">📈 Spending Trends (Last 6 Months)</h6>
                            {loadingAnalytics ? (
                                <div className="text-center py-5">
                                    <Spinner animation="border" variant="primary" />
                                </div>
                            ) : (
                                <SpendingTrendsChart data={analytics.trends} />
                            )}
                        </Card.Body>
                    </Card>
                </Col>

                {/* Status Breakdown */}
                <Col lg={4}>
                    <Card className="glass-card h-100">
                        <Card.Body>
                            <h6 className="mb-3">🎯 Invoice Status</h6>
                            {loadingAnalytics ? (
                                <div className="text-center py-5">
                                    <Spinner animation="border" variant="primary" />
                                </div>
                            ) : (
                                <StatusBreakdownChart data={analytics.statusBreakdown} />
                            )}
                        </Card.Body>
                    </Card>
                </Col>
            </Row>

            <Row className="g-4 mb-4">
                {/* Top Vendors */}
                <Col lg={6}>
                    <Card className="glass-card h-100">
                        <Card.Body>
                            <h6 className="mb-3">🏢 Top Vendors by Spend</h6>
                            {loadingAnalytics ? (
                                <div className="text-center py-5">
                                    <Spinner animation="border" variant="primary" />
                                </div>
                            ) : (
                                <TopVendorsChart data={analytics.vendors} />
                            )}
                        </Card.Body>
                    </Card>
                </Col>

                {/* AI Insights */}
                <Col lg={6}>
                    <AIInsightsCard
                        insights={analytics.insights}
                        loading={loadingInsights}
                        onRefresh={fetchInsights}
                    />
                </Col>
            </Row>

            <Row className="g-4">
                {/* Upload Zone */}
                <Col lg={8}>
                    <Card className="glass-card h-100">
                        <Card.Body>
                            <h5 className="mb-4">📤 Upload Invoice</h5>

                            <div
                                className={`upload-zone ${dragOver ? 'dragover' : ''}`}
                                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                                onDragLeave={() => setDragOver(false)}
                                onDrop={handleDrop}
                                onClick={() => document.getElementById('file-input')?.click()}
                            >
                                <div className="upload-zone-icon">📄</div>
                                <h5>Drag & drop your invoice here</h5>
                                <p className="text-secondary mb-3">or click to browse</p>
                                <p className="text-secondary small">Supports PDF, images, and text files (max 10MB)</p>

                                <input
                                    id="file-input"
                                    type="file"
                                    accept=".pdf,.png,.jpg,.jpeg,.txt,.csv"
                                    onChange={handleFileSelect}
                                    style={{ display: 'none' }}
                                />
                            </div>
                        </Card.Body>
                    </Card>
                </Col>

                <Col lg={4}>
                    <Card className="glass-card mb-4">
                        <Card.Body>
                            <h6 className="mb-3">🚀 Quick Actions</h6>
                            <div className="d-grid gap-2">
                                <button className="btn btn-glass text-start" onClick={() => navigate('/documents')}>
                                    📋 View All Documents
                                </button>
                                <button className="btn btn-glass text-start" onClick={() => navigate('/chat')}>
                                    💬 Open Chat Assistant
                                </button>
                            </div>
                        </Card.Body>
                    </Card>

                    <Card className="glass-card mb-4">
                        <Card.Body>
                            <h6 className="mb-3">ℹ️ How it works</h6>
                            <ol className="text-secondary small ps-3 mb-0">
                                <li className="mb-2">Upload your invoice (PDF, image, or text)</li>
                                <li className="mb-2">AI extracts and validates the content</li>
                                <li className="mb-2">Ask questions about any invoice</li>
                                <li>Use the chatbot for invoice management</li>
                            </ol>
                        </Card.Body>
                    </Card>

                    {/* Folder Watcher */}
                    <FolderWatcher />
                </Col>
            </Row>
        </Container>
    );
};

export default Dashboard;
