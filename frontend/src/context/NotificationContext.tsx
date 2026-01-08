// Notification Context for global toast notifications

import { createContext, useContext, type ReactNode } from 'react';
import { ToastNotifications, useToastNotifications, type ToastNotification } from '../components/ToastNotifications';

interface NotificationContextType {
    addNotification: (notification: Omit<ToastNotification, 'id' | 'timestamp'>) => void;
    showSuccess: (title: string, message: string) => void;
    showError: (title: string, message: string) => void;
    showInfo: (title: string, message: string) => void;
}

const NotificationContext = createContext<NotificationContextType | null>(null);

export const NotificationProvider = ({ children }: { children: ReactNode }) => {
    const { notifications, addNotification, dismissNotification } = useToastNotifications();

    const showSuccess = (title: string, message: string) => {
        addNotification({ title, message, variant: 'success' });
    };

    const showError = (title: string, message: string) => {
        addNotification({ title, message, variant: 'danger' });
    };

    const showInfo = (title: string, message: string) => {
        addNotification({ title, message, variant: 'info' });
    };

    return (
        <NotificationContext.Provider value={{ addNotification, showSuccess, showError, showInfo }}>
            {children}
            <ToastNotifications notifications={notifications} onDismiss={dismissNotification} />
        </NotificationContext.Provider>
    );
};

export const useNotifications = () => {
    const context = useContext(NotificationContext);
    if (!context) {
        throw new Error('useNotifications must be used within a NotificationProvider');
    }
    return context;
};
