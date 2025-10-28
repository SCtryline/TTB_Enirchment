#!/usr/bin/env python3
"""
Background Processing for Long-Running Enrichment Tasks
Provides immediate response with job tracking
"""

import uuid
import json
import time
import threading
from typing import Dict, Optional, Any
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BackgroundProcessor:
    """
    Manages background enrichment jobs
    - Creates job IDs for tracking
    - Returns immediately to avoid timeouts
    - Processes enrichment in background
    - Provides status checking endpoint
    """
    
    def __init__(self):
        self.jobs = {}
        self.job_file = 'data/cache/background_jobs.json'
        self.load_jobs()
    
    def load_jobs(self):
        """Load existing jobs from file"""
        try:
            with open(self.job_file, 'r') as f:
                self.jobs = json.load(f)
        except:
            self.jobs = {}
    
    def save_jobs(self):
        """Save jobs to file"""
        try:
            with open(self.job_file, 'w') as f:
                json.dump(self.jobs, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving jobs: {e}")
    
    def create_job(self, brand_name: str, job_type: str = 'enrichment') -> str:
        """Create a new background job"""
        job_id = str(uuid.uuid4())[:8]
        
        self.jobs[job_id] = {
            'id': job_id,
            'brand_name': brand_name,
            'type': job_type,
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'result': None,
            'error': None,
            'progress': 0
        }
        
        self.save_jobs()
        logger.info(f"Created job {job_id} for {brand_name}")
        
        return job_id
    
    def update_job(self, job_id: str, status: str = None, 
                   result: Any = None, error: str = None, 
                   progress: int = None):
        """Update job status"""
        if job_id in self.jobs:
            job = self.jobs[job_id]
            
            if status:
                job['status'] = status
            if result is not None:
                job['result'] = result
            if error:
                job['error'] = error
            if progress is not None:
                job['progress'] = progress
            
            job['updated_at'] = datetime.now().isoformat()
            self.save_jobs()
            
            logger.info(f"Updated job {job_id}: status={status}, progress={progress}")
    
    def get_job(self, job_id: str) -> Optional[Dict]:
        """Get job status"""
        return self.jobs.get(job_id)
    
    def process_in_background(self, job_id: str, enrichment_func, *args, **kwargs):
        """
        Process enrichment in background thread
        
        Args:
            job_id: Job ID to update
            enrichment_func: Function to call for enrichment
            *args, **kwargs: Arguments to pass to enrichment function
        """
        def run_enrichment():
            try:
                logger.info(f"Starting background processing for job {job_id}")
                self.update_job(job_id, status='processing', progress=10)
                
                # Simulate progress updates
                self.update_job(job_id, progress=30)
                
                # Run the actual enrichment
                result = enrichment_func(*args, **kwargs)
                
                self.update_job(job_id, progress=90)
                
                # Store result
                self.update_job(
                    job_id, 
                    status='completed',
                    result=result,
                    progress=100
                )
                
                logger.info(f"Completed job {job_id} successfully")
                
            except Exception as e:
                logger.error(f"Job {job_id} failed: {e}")
                self.update_job(
                    job_id,
                    status='failed',
                    error=str(e),
                    progress=100
                )
        
        # Start background thread
        thread = threading.Thread(target=run_enrichment)
        thread.daemon = True
        thread.start()
        
        logger.info(f"Started background thread for job {job_id}")
    
    def cleanup_old_jobs(self, hours: int = 24):
        """Remove jobs older than specified hours"""
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(hours=hours)
        
        jobs_to_remove = []
        for job_id, job in self.jobs.items():
            try:
                created = datetime.fromisoformat(job['created_at'])
                if created < cutoff:
                    jobs_to_remove.append(job_id)
            except:
                pass
        
        for job_id in jobs_to_remove:
            del self.jobs[job_id]
        
        if jobs_to_remove:
            self.save_jobs()
            logger.info(f"Cleaned up {len(jobs_to_remove)} old jobs")


# Global instance
background_processor = BackgroundProcessor()