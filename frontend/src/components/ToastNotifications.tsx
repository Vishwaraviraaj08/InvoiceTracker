// Toast Notification Component for file upload notifications

import { useState, useEffect, useCallback } from 'react';
import { Toast, ToastContainer, ProgressBar } from 'react-bootstrap';

export interface ToastNotification {
    id: string;
    title: string;
    message: string;
    variant: 'success' | 'danger' | 'warning' | 'info';
    timestamp: Date;
}

interface ToastNotificationsProps {
    notifications: ToastNotification[];
    onDismiss: (id: string) => void;
}

export const ToastNotifications = ({ notifications, onDismiss }: ToastNotificationsProps) => {
    return (
        <ToastContainer
            className="p-3"
            style={{
                position: 'fixed',
                top: '20px',
                right: '20px',
                zIndex: 9999
            }}
        >
            {notifications.map((notification) => (
                <FileToast
                    key={notification.id}
                    notification={notification}
                    onDismiss={() => onDismiss(notification.id)}
                />
            ))}
        </ToastContainer>
    );
};

interface FileToastProps {
    notification: ToastNotification;
    onDismiss: () => void;
}

const FileToast = ({ notification, onDismiss }: FileToastProps) => {
    const [progress, setProgress] = useState(100);

    useEffect(() => {
        // Progress bar countdown over 3 seconds
        const interval = setInterval(() => {
            setProgress((prev) => {
                if (prev <= 0) {
                    clearInterval(interval);
                    return 0;
                }
                return prev - 3.33; // Decrease by ~3.33% every 100ms (3 seconds total)
            });
        }, 100);

        // Auto-dismiss after 3 seconds
        const timeout = setTimeout(() => {
            onDismiss();
        }, 3000);

        return () => {
            clearInterval(interval);
            clearTimeout(timeout);
        };
    }, [onDismiss]);

    const getIconAndColor = () => {
        switch (notification.variant) {
            case 'success':
                return { icon: '✅', bgClass: 'bg-success' };
            case 'danger':
                return { icon: '❌', bgClass: 'bg-danger' };
            case 'warning':
                return { icon: '⚠️', bgClass: 'bg-warning' };
            case 'info':
            default:
                return { icon: '📄', bgClass: 'bg-info' };
        }
    };

    const { icon } = getIconAndColor();

    return (
        <Toast
            onClose={onDismiss}
            className="mb-2"
            style={{
                background: 'rgba(30, 30, 50, 0.95)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                backdropFilter: 'blur(10px)'
            }}
        >
            <Toast.Header
                closeButton
                className="text-white"
                style={{ background: 'rgba(40, 40, 60, 0.9)', borderBottom: '1px solid rgba(255,255,255,0.1)' }}
            >
                <span className="me-2">{icon}</span>
                <strong className="me-auto">{notification.title}</strong>
                <small className="text-secondary">just now</small>
            </Toast.Header>
            <Toast.Body className="text-white">
                {notification.message}
                <ProgressBar
                    now={progress}
                    className="mt-2"
                    style={{ height: '3px' }}
                    variant={notification.variant === 'success' ? 'success' : 'info'}
                />
            </Toast.Body>
        </Toast>
    );
};

// Hook for managing toast notifications
export const useToastNotifications = () => {
    const [notifications, setNotifications] = useState<ToastNotification[]>([]);

    const addNotification = useCallback((notification: Omit<ToastNotification, 'id' | 'timestamp'>) => {
        const id = `toast-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        setNotifications((prev) => [
            ...prev,
            { ...notification, id, timestamp: new Date() }
        ]);
    }, []);

    const dismissNotification = useCallback((id: string) => {
        setNotifications((prev) => prev.filter((n) => n.id !== id));
    }, []);

    return {
        notifications,
        addNotification,
        dismissNotification
    };
};

export default ToastNotifications;
