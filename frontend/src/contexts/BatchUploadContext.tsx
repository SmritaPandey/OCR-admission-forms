import { createContext, useContext, useState, useCallback, useEffect, useRef, ReactNode } from 'react';
import { apiService } from '../services/api';

export interface BatchJob {
    job_id: string;
    status: string;
    total_items: number;
    processed_items: number;
    successful_items: number;
    failed_items: number;
    progress_percentage: number;
    created_at: string;
    started_at?: string;
    completed_at?: string;
}

interface BatchUploadContextType {
    currentJob: BatchJob | null;
    isPolling: boolean;
    startJob: (job: BatchJob) => void;
    cancelJob: () => Promise<void>;
    clearJob: () => void;
}

const BatchUploadContext = createContext<BatchUploadContextType | undefined>(undefined);

export function BatchUploadProvider({ children }: { children: ReactNode }) {
    const [currentJob, setCurrentJob] = useState<BatchJob | null>(null);
    const [isPolling, setIsPolling] = useState(false);
    const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

    const stopPolling = useCallback(() => {
        if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current);
            pollingIntervalRef.current = null;
        }
        setIsPolling(false);
    }, []);

    const startPolling = useCallback((jobId: string) => {
        stopPolling();
        setIsPolling(true);

        let consecutiveFailures = 0;
        const MAX_CONSECUTIVE_FAILURES = 5; // Stop after 5 consecutive failures

        const poll = async () => {
            try {
                const status = await apiService.getBatchJobStatus(jobId);
                // Reset failure counter on success
                consecutiveFailures = 0;
                
                // Ensure progress_percentage is calculated if missing
                if (status.progress_percentage === undefined && status.total_items > 0) {
                    status.progress_percentage = (status.processed_items / status.total_items) * 100;
                }
                setCurrentJob(status);

                if (status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled') {
                    stopPolling();
                    // Clear from local storage when done
                    if (status.status !== 'processing') {
                        localStorage.removeItem('activeBatchJobId');
                    }
                }
            } catch (error: any) {
                consecutiveFailures++;
                
                // Check if it's a 404 (job not found)
                if (error?.response?.status === 404 || String(error).includes('404')) {
                    stopPolling();
                    localStorage.removeItem('activeBatchJobId');
                    if (process.env.NODE_ENV === 'development') {
                        console.warn('Batch job not found (404), stopping polling');
                    }
                    return;
                }
                
                // Check if it's a network error (backend not available)
                const isNetworkError = error?.code === 'ERR_NETWORK' || 
                                      error?.message?.includes('Network error') ||
                                      !error?.response; // No response means network issue
                
                if (isNetworkError) {
                    // Stop polling after too many consecutive network failures
                    if (consecutiveFailures >= MAX_CONSECUTIVE_FAILURES) {
                        stopPolling();
                        localStorage.removeItem('activeBatchJobId');
                        if (process.env.NODE_ENV === 'development') {
                            console.warn(`Stopped polling after ${MAX_CONSECUTIVE_FAILURES} consecutive network failures. Backend may be unavailable.`);
                        }
                        return;
                    }
                    
                    // Only log network errors in development, and only occasionally
                    if (process.env.NODE_ENV === 'development' && consecutiveFailures === 1) {
                        console.warn('Network error polling batch job status. Backend may be unavailable. Will retry...');
                    }
                } else {
                    // For other errors, log in development
                    if (process.env.NODE_ENV === 'development') {
                        console.error('Failed to get job status:', error);
                    }
                }
            }
        };

        // Poll immediately, then every 1.5 seconds for faster updates
        poll();
        pollingIntervalRef.current = setInterval(poll, 1500);
    }, [stopPolling]);

    // Check for active job on mount
    const hasResumedRef = useRef(false);
    useEffect(() => {
        const savedJobId = localStorage.getItem('activeBatchJobId');
        if (savedJobId && !hasResumedRef.current) {
            hasResumedRef.current = true; // Prevent duplicate logs in StrictMode
            // Only log in development
            if (process.env.NODE_ENV === 'development') {
                console.log('Resuming active batch job:', savedJobId);
            }
            startPolling(savedJobId);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []); // Only run on mount

    const startJob = useCallback((job: BatchJob) => {
        setCurrentJob(job);
        if (job.status === 'processing' || job.status === 'pending') {
            localStorage.setItem('activeBatchJobId', job.job_id);
            startPolling(job.job_id);
        }
    }, [startPolling]);

    const cancelJob = useCallback(async () => {
        if (currentJob && (currentJob.status === 'processing' || currentJob.status === 'pending')) {
            try {
                await apiService.cancelBatchJob(currentJob.job_id);
                // Status update will happen on next poll or we can force it
                // But let's keep polling until the server says "cancelled"
            } catch (error) {
                console.error('Failed to cancel job:', error);
            }
        }
    }, [currentJob]);

    const clearJob = useCallback(() => {
        stopPolling();
        setCurrentJob(null);
        localStorage.removeItem('activeBatchJobId');
    }, [stopPolling]);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            stopPolling();
        };
    }, [stopPolling]);

    return (
        <BatchUploadContext.Provider value={{ currentJob, isPolling, startJob, cancelJob, clearJob }}>
            {children}
        </BatchUploadContext.Provider>
    );
}

export function useBatchUpload() {
    const context = useContext(BatchUploadContext);
    if (context === undefined) {
        throw new Error('useBatchUpload must be used within a BatchUploadProvider');
    }
    return context;
}
