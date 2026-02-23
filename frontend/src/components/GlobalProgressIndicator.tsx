import { useState, useMemo } from 'react';
import { useBatchUpload } from '../contexts/BatchUploadContext';
import { useNavigate } from 'react-router-dom';
import './GlobalProgressIndicator.css';

function GlobalProgressIndicator() {
    const { currentJob, cancelJob, clearJob } = useBatchUpload();
    const [isExpanded, setIsExpanded] = useState(false);
    const navigate = useNavigate();

    const currentStatus = currentJob?.status;
    const isProcessing = currentStatus === 'processing';
    const isCompleted = currentStatus === 'completed';
    const isFailed = currentStatus === 'failed';
    const isCancelled = currentStatus === 'cancelled';

    const statusColor = useMemo(() => {
        if (isCompleted) return '#10b981';
        if (isFailed) return '#ef4444';
        if (isCancelled) return '#6b7280';
        return '#3b82f6';
    }, [isCompleted, isFailed, isCancelled]);

    if (!currentJob) return null;

    const progress = currentJob.progress_percentage || 0;
    const radius = 18;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (progress / 100) * circumference;

    return (
        <div
            className={`global-progress-v2 ${isExpanded ? 'expanded' : 'collapsed'} ${currentJob.status}`}
            onMouseEnter={() => setIsExpanded(true)}
            onMouseLeave={() => setIsExpanded(false)}
        >
            <div className="progress-main-content">
                <div className="progress-circle-container">
                    <svg className="progress-ring" width="44" height="44">
                        <circle
                            className="progress-ring-bg"
                            stroke="rgba(255, 255, 255, 0.1)"
                            strokeWidth="3"
                            fill="transparent"
                            r={radius}
                            cx="22"
                            cy="22"
                        />
                        <circle
                            className="progress-ring-fill"
                            stroke={statusColor}
                            strokeWidth="3"
                            strokeDasharray={`${circumference} ${circumference}`}
                            style={{ strokeDashoffset: offset }}
                            strokeLinecap="round"
                            fill="transparent"
                            r={radius}
                            cx="22"
                            cy="22"
                        />
                    </svg>
                    <div className="progress-percentage-text" style={{ color: statusColor }}>
                        {progress >= 100 ? (
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                            </svg>
                        ) : Math.round(progress)}
                    </div>
                </div>

                <div className="progress-text-content">
                    <div className="progress-job-title">
                        {isProcessing ? 'Processing Forms...' : isCompleted ? 'Upload Complete' : 'Batch Upload'}
                    </div>
                    <div className="progress-job-subtitle">
                        {currentJob.processed_items} of {currentJob.total_items} items processed
                    </div>
                </div>

                {isExpanded && (
                    <div className="progress-expanded-actions">
                        <button className="action-btn view-btn" onClick={() => navigate('/batch-upload')} title="View Results">
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                            </svg>
                        </button>
                        {isProcessing ? (
                            <button className="action-btn cancel-btn" onClick={cancelJob} title="Cancel Processing">
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        ) : (
                            <button className="action-btn dismiss-btn" onClick={clearJob} title="Dismiss">
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        )}
                    </div>
                )}
            </div>

            {isExpanded && (isProcessing || isCompleted) && (
                <div className="progress-detailed-stats">
                    <div className="stat-item success">
                        <span className="dot"></span>
                        <span className="label">Success:</span>
                        <span className="value">{currentJob.successful_items}</span>
                    </div>
                    <div className="stat-item error">
                        <span className="dot"></span>
                        <span className="label">Failed:</span>
                        <span className="value">{currentJob.failed_items}</span>
                    </div>
                </div>
            )}
        </div>
    );
}

export default GlobalProgressIndicator;
