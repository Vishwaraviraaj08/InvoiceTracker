// Analytics Charts Components

import { Card, Spinner } from 'react-bootstrap';
import ReactMarkdown from 'react-markdown';
import {
    AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
    XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';

const COLORS = ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe', '#00f2fe'];

interface SpendingTrend {
    month: string;
    total_spend: number;
    invoice_count: number;
}

interface Vendor {
    name: string;
    total_spend: number;
    invoice_count: number;
}

interface StatusBreakdown {
    status: string;
    total_spend: number;
    invoice_count: number;
}

// Spending Trends Chart
export const SpendingTrendsChart = ({ data }: { data: SpendingTrend[] }) => {
    if (!data || data.length === 0) {
        return (
            <div className="text-center text-secondary py-4">
                <p>No spending data available yet</p>
            </div>
        );
    }

    return (
        <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <defs>
                    <linearGradient id="colorSpend" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#667eea" stopOpacity={0.8} />
                        <stop offset="95%" stopColor="#667eea" stopOpacity={0.1} />
                    </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                <XAxis dataKey="month" stroke="rgba(255,255,255,0.7)" tick={{ fill: 'rgba(255,255,255,0.7)' }} />
                <YAxis stroke="rgba(255,255,255,0.7)" tick={{ fill: 'rgba(255,255,255,0.7)' }} />
                <Tooltip
                    contentStyle={{
                        background: 'rgba(0,0,0,0.8)',
                        border: '1px solid rgba(255,255,255,0.2)',
                        borderRadius: '8px',
                        color: 'white'
                    }}
                    formatter={(value: number) => [`$${value.toLocaleString()}`, 'Spend']}
                />
                <Area
                    type="monotone"
                    dataKey="total_spend"
                    stroke="#667eea"
                    fillOpacity={1}
                    fill="url(#colorSpend)"
                    name="Total Spend"
                />
            </AreaChart>
        </ResponsiveContainer>
    );
};

// Top Vendors Chart
export const TopVendorsChart = ({ data }: { data: Vendor[] }) => {
    if (!data || data.length === 0) {
        return (
            <div className="text-center text-secondary py-4">
                <p>No vendor data available yet</p>
            </div>
        );
    }

    return (
        <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data} layout="vertical" margin={{ top: 10, right: 30, left: 80, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                <XAxis type="number" stroke="rgba(255,255,255,0.7)" tick={{ fill: 'rgba(255,255,255,0.7)' }} />
                <YAxis
                    dataKey="name"
                    type="category"
                    stroke="rgba(255,255,255,0.7)"
                    tick={{ fill: 'rgba(255,255,255,0.7)' }}
                    width={70}
                />
                <Tooltip
                    contentStyle={{
                        background: 'rgba(0,0,0,0.8)',
                        border: '1px solid rgba(255,255,255,0.2)',
                        borderRadius: '8px',
                        color: 'white'
                    }}
                    formatter={(value: number) => [`$${value.toLocaleString()}`, 'Total Spend']}
                />
                <Bar dataKey="total_spend" fill="#764ba2" radius={[0, 4, 4, 0]}>
                    {data.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                </Bar>
            </BarChart>
        </ResponsiveContainer>
    );
};

// Status Breakdown Pie Chart
export const StatusBreakdownChart = ({ data }: { data: StatusBreakdown[] }) => {
    if (!data || data.length === 0) {
        return (
            <div className="text-center text-secondary py-4">
                <p>No status data available</p>
            </div>
        );
    }

    const statusColors: Record<string, string> = {
        valid: '#10b981',
        invalid: '#ef4444',
        pending: '#f59e0b'
    };

    return (
        <ResponsiveContainer width="100%" height={250}>
            <PieChart>
                <Pie
                    data={data}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={90}
                    paddingAngle={5}
                    dataKey="invoice_count"
                    nameKey="status"
                    label={({ status, percent }) => `${status} ${(percent * 100).toFixed(0)}%`}
                >
                    {data.map((entry, index) => (
                        <Cell
                            key={`cell-${index}`}
                            fill={statusColors[entry.status] || COLORS[index % COLORS.length]}
                        />
                    ))}
                </Pie>
                <Tooltip
                    contentStyle={{
                        background: 'rgba(0,0,0,0.8)',
                        border: '1px solid rgba(255,255,255,0.2)',
                        borderRadius: '8px',
                        color: 'white'
                    }}
                />
                <Legend
                    formatter={(value) => <span style={{ color: 'rgba(255,255,255,0.8)' }}>{value}</span>}
                />
            </PieChart>
        </ResponsiveContainer>
    );
};

// AI Insights Card
interface AIInsightsProps {
    insights: string;
    loading: boolean;
    onRefresh: () => void;
}

export const AIInsightsCard = ({ insights, loading, onRefresh }: AIInsightsProps) => {
    return (
        <Card className="glass-card h-100">
            <Card.Body>
                <div className="d-flex justify-content-between align-items-center mb-3">
                    <h6 className="mb-0">🤖 AI Insights</h6>
                    <button
                        className="btn btn-sm btn-glass"
                        onClick={onRefresh}
                        disabled={loading}
                    >
                        {loading ? <Spinner size="sm" /> : '🔄'}
                    </button>
                </div>
                {loading ? (
                    <div className="text-center py-4">
                        <Spinner animation="border" variant="primary" />
                        <p className="mt-2 text-secondary">Analyzing patterns...</p>
                    </div>
                ) : (
                    <div className="ai-insights-content markdown-content" style={{ color: 'rgba(255,255,255,0.9)' }}>
                        {insights ? (
                            <ReactMarkdown
                                components={{
                                    h1: ({ children }) => <h5 className="mb-2 mt-3">{children}</h5>,
                                    h2: ({ children }) => <h6 className="mb-2 mt-2">{children}</h6>,
                                    h3: ({ children }) => <h6 className="mb-2 mt-2">{children}</h6>,
                                    p: ({ children }) => <p className="mb-2 small">{children}</p>,
                                    ul: ({ children }) => <ul className="mb-2 ps-3 small">{children}</ul>,
                                    ol: ({ children }) => <ol className="mb-2 ps-3 small">{children}</ol>,
                                    li: ({ children }) => <li className="mb-1">{children}</li>,
                                    strong: ({ children }) => <strong className="fw-bold text-info">{children}</strong>,
                                    hr: () => <hr className="my-2 border-secondary" />,
                                }}
                            >
                                {insights}
                            </ReactMarkdown>
                        ) : (
                            'No insights available yet. Upload some invoices to get started!'
                        )}
                    </div>
                )}
            </Card.Body>
        </Card>
    );
};

// Summary Stats Cards
interface SummaryStats {
    total_invoices: number;
    validated_count: number;
    invalid_count: number;
    pending_count: number;
    total_spend: number;
    average_invoice_value: number;
}

export const SummaryStatsCards = ({ stats }: { stats: SummaryStats | null }) => {
    if (!stats) {
        return (
            <div className="row g-3 mb-4">
                {[1, 2, 3, 4].map((i) => (
                    <div key={i} className="col-md-3">
                        <Card className="glass-card text-center">
                            <Card.Body>
                                <Spinner animation="border" size="sm" />
                            </Card.Body>
                        </Card>
                    </div>
                ))}
            </div>
        );
    }

    const cards = [
        { label: 'Total Invoices', value: stats.total_invoices, icon: '📄', color: '#667eea' },
        { label: 'Total Spend', value: `$${stats.total_spend.toLocaleString()}`, icon: '💰', color: '#10b981' },
        { label: 'Validated', value: stats.validated_count, icon: '✅', color: '#10b981' },
        { label: 'Avg. Invoice', value: `$${stats.average_invoice_value.toLocaleString()}`, icon: '📊', color: '#f59e0b' }
    ];

    return (
        <div className="row g-3 mb-4">
            {cards.map((card, index) => (
                <div key={index} className="col-md-3 col-sm-6">
                    <Card className="glass-card h-100" style={{ borderLeft: `4px solid ${card.color}` }}>
                        <Card.Body className="d-flex align-items-center">
                            <span className="me-3" style={{ fontSize: '2rem' }}>{card.icon}</span>
                            <div>
                                <div className="text-secondary small">{card.label}</div>
                                <div className="h4 mb-0" style={{ color: 'white' }}>{card.value}</div>
                            </div>
                        </Card.Body>
                    </Card>
                </div>
            ))}
        </div>
    );
};
