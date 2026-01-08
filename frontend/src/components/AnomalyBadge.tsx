// Anomaly Badge Component

import { Badge, OverlayTrigger, Tooltip } from 'react-bootstrap';

interface Anomaly {
    type: 'duplicate' | 'price_anomaly';
    severity: 'warning' | 'high';
    message: string;
    similarity_score?: number;
    similar_document_name?: string;
    current_amount?: number;
    average_amount?: number;
    multiplier?: number;
}

interface AnomalyBadgeProps {
    anomalies: Anomaly[];
}

const AnomalyBadge = ({ anomalies }: AnomalyBadgeProps) => {
    if (!anomalies || anomalies.length === 0) {
        return null;
    }

    const getIcon = (type: string) => {
        switch (type) {
            case 'duplicate':
                return '📋';
            case 'price_anomaly':
                return '💰';
            default:
                return '⚠️';
        }
    };

    const getBadgeVariant = (severity: string) => {
        switch (severity) {
            case 'high':
                return 'danger';
            case 'warning':
                return 'warning';
            default:
                return 'secondary';
        }
    };

    return (
        <div className="d-flex gap-1 flex-wrap">
            {anomalies.map((anomaly, index) => (
                <OverlayTrigger
                    key={index}
                    placement="top"
                    overlay={
                        <Tooltip id={`anomaly-tooltip-${index}`}>
                            <div className="text-start">
                                <strong>{anomaly.type === 'duplicate' ? 'Potential Duplicate' : 'Price Anomaly'}</strong>
                                <br />
                                {anomaly.message}
                                {anomaly.similarity_score && (
                                    <><br />Similarity: {anomaly.similarity_score}%</>
                                )}
                                {anomaly.multiplier && (
                                    <><br />{anomaly.multiplier}x above average</>
                                )}
                            </div>
                        </Tooltip>
                    }
                >
                    <Badge
                        bg={getBadgeVariant(anomaly.severity)}
                        className="cursor-pointer"
                        style={{ cursor: 'pointer' }}
                    >
                        {getIcon(anomaly.type)} {anomaly.type === 'duplicate' ? 'Duplicate?' : 'High Price'}
                    </Badge>
                </OverlayTrigger>
            ))}
        </div>
    );
};

export default AnomalyBadge;
