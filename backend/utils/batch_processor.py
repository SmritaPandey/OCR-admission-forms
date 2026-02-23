"""
Batch Processor
Handle batch processing of forms with queue management
"""
from typing import List, Dict, Any, Optional, Callable
from enum import Enum
from datetime import datetime
import asyncio
from dataclasses import dataclass, asdict
import json
import logging

from backend.config import settings

logger = logging.getLogger(__name__)

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class BatchJob:
    """Represents a batch processing job"""
    job_id: str
    status: JobStatus
    total_items: int
    processed_items: int
    successful_items: int
    failed_items: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    errors: List[Dict[str, Any]] = None
    results: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.results is None:
            self.results = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['status'] = self.status.value
        result['created_at'] = self.created_at.isoformat()
        if self.started_at:
            result['started_at'] = self.started_at.isoformat()
        if self.completed_at:
            result['completed_at'] = self.completed_at.isoformat()
        result['progress_percentage'] = self.progress_percentage
        return result
    
    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage"""
        if self.total_items == 0:
            return 0.0
        return (self.processed_items / self.total_items) * 100

class BatchProcessor:
    """Process items in batch with progress tracking"""
    
    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self.jobs: Dict[str, BatchJob] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._background_tasks: set = set()  # Track background tasks
    
    async def process_batch(
        self,
        items: List[Any],
        process_func: Callable,
        job_id: Optional[str] = None
    ) -> str:
        """
        Process a batch of items
        
        Args:
            items: List of items to process
            process_func: Async function to process each item
            job_id: Optional job ID (generated if not provided)
        
        Returns:
            Job ID
        """
        import uuid
        if not job_id:
            job_id = str(uuid.uuid4())
        
        job = BatchJob(
            job_id=job_id,
            status=JobStatus.PENDING,
            total_items=len(items),
            processed_items=0,
            successful_items=0,
            failed_items=0,
            created_at=datetime.utcnow()
        )
        self.jobs[job_id] = job
        
        # Start processing in background
        # In FastAPI, we're already in an async context with a running event loop
        # Use get_running_loop() to get the current loop and create the task
        try:
            loop = asyncio.get_running_loop()
            # Create task in the running loop - this ensures it executes
            task = loop.create_task(self._process_items(job, items, process_func))
            logger.info(f"Created background task for batch job {job_id} with {len(items)} items")
        except RuntimeError as e:
            # Fallback if no running loop (shouldn't happen in FastAPI)
            logger.error(f"No running event loop found: {e}")
            task = asyncio.create_task(self._process_items(job, items, process_func))
        
        # Store the task to prevent garbage collection
        self._background_tasks.add(task)
        task.add_done_callback(lambda t: self._background_tasks.discard(t))
        
        return job_id
    
    async def _process_items(
        self,
        job: BatchJob,
        items: List[Any],
        process_func: Callable
    ):
        """Process items for a job - can be called directly or as background task"""
        logger.info(f"Starting batch processing for job {job.job_id} with {len(items)} items")
        if job.status == JobStatus.PENDING:
            job.status = JobStatus.PROCESSING
        if not job.started_at:
            job.started_at = datetime.utcnow()
        
        try:
            # Process items with concurrency limit
            tasks = []
            for item in items:
                task = asyncio.create_task(
                    self._process_item_with_semaphore(job, item, process_func)
                )
                tasks.append(task)
            
            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Log any exceptions that occurred
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Task {i} failed with exception: {result}")
            
            # Mark job as completed
            if job.status != JobStatus.CANCELLED:
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.utcnow()
                logger.info(f"Batch job {job.job_id} completed: {job.successful_items} successful, {job.failed_items} failed")
        except Exception as e:
            logger.error(f"Batch processing failed for job {job.job_id}: {e}", exc_info=True)
            job.status = JobStatus.FAILED
            job.completed_at = datetime.utcnow()
    
    async def _process_item_with_semaphore(
        self,
        job: BatchJob,
        item: Any,
        process_func: Callable
    ):
        """Process a single item with semaphore for concurrency control"""
        async with self._semaphore:
            try:
                result = await process_func(item)
                # Update counters atomically
                job.processed_items += 1
                # Result should already have status, filename, etc.
                if result and isinstance(result, dict):
                    if result.get("status") == "success":
                        job.successful_items += 1
                    else:
                        job.failed_items += 1
                    job.results.append(result)
                else:
                    # Fallback if result format is unexpected
                    job.successful_items += 1
                    job.results.append({
                        "filename": str(item.get("original_filename", item)) if isinstance(item, dict) else str(item),
                        "status": "success",
                        "result": result
                    })
                
                # Log progress periodically
                if job.processed_items % 5 == 0 or job.processed_items == job.total_items:
                    logger.info(f"Job {job.job_id}: {job.processed_items}/{job.total_items} processed ({job.progress_percentage:.1f}%)")
                    
            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                logger.error(f"Batch processing error: {error_trace}")
                
                job.processed_items += 1
                job.failed_items += 1
                filename = str(item.get("original_filename", item)) if isinstance(item, dict) else str(item)
                error_info = {
                    "filename": filename,
                    "status": "error",
                    "error": str(e)
                }
                job.errors.append(error_info)
                job.results.append(error_info)
    
    def get_job_status(self, job_id: str) -> Optional[BatchJob]:
        """Get job status"""
        return self.jobs.get(job_id)
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job"""
        job = self.jobs.get(job_id)
        if job and job.status in [JobStatus.PENDING, JobStatus.PROCESSING]:
            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.utcnow()
            return True
        return False
    
    def get_all_jobs(self) -> List[Dict[str, Any]]:
        """Get all jobs"""
        return [job.to_dict() for job in self.jobs.values()]
    
    def cleanup_old_jobs(self, days: int = 7):
        """Remove old completed jobs"""
        cutoff = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff = cutoff.replace(day=cutoff.day - days)
        
        jobs_to_remove = [
            job_id for job_id, job in self.jobs.items()
            if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]
            and job.completed_at and job.completed_at < cutoff
        ]
        
        for job_id in jobs_to_remove:
            del self.jobs[job_id]

# Global instance (uses BATCH_MAX_CONCURRENT from config)
batch_processor = BatchProcessor(max_concurrent=settings.BATCH_MAX_CONCURRENT)

