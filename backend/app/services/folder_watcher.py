"""
Folder Watcher Service
Monitors a folder for new invoices and auto-processes them
"""

import os
import asyncio
import logging
import threading
from pathlib import Path
from typing import Optional, Callable
from datetime import datetime

from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

logger = logging.getLogger(__name__)


class InvoiceFileHandler(FileSystemEventHandler):
    """Handles new file events in watched folder"""
    
    SUPPORTED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg', '.txt', '.csv'}
    
    def __init__(self, callback: Callable[[str], None]):
        self.callback = callback
        self.processed_files = set()
    
    def on_created(self, event: FileCreatedEvent):
        logger.info(f"File event detected: {event.src_path} (is_directory: {event.is_directory})")
        
        if event.is_directory:
            return
        
        filepath = Path(event.src_path)
        
        # Check if supported file type
        if filepath.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            logger.info(f"Skipping unsupported file type: {filepath.suffix}")
            return
        
        # Avoid processing same file multiple times
        if str(filepath) in self.processed_files:
            logger.info(f"File already processed: {filepath.name}")
            return
        
        self.processed_files.add(str(filepath))
        
        logger.info(f"New invoice detected: {filepath.name} - Starting processing...")
        
        # Call the callback in a separate thread to not block watchdog
        threading.Thread(target=self.callback, args=(str(filepath),), daemon=True).start()


class FolderWatcher:
    """
    Watches a folder for new invoice files and processes them.
    """
    
    def __init__(self):
        self.observer: Optional[Observer] = None
        self.watch_path: Optional[str] = None
        self.is_running = False
        self.processed_files: list = []
        self.processing_files = set()  # Track files currently being processed
        self.auto_validate = True
    
    def _process_file(self, filepath: str):
        """Process a newly detected file"""
        try:
            # Use asyncio.run() to handle the async operation in this thread
            # This creates a new event loop for this thread and cleans it up properly
            asyncio.run(self._async_process_file(filepath))
        except Exception as e:
            logger.error(f"Error processing file {filepath}: {e}")
    
    async def _async_process_file(self, filepath: str):
        """Async file processing"""
        from app.services.document_service import get_document_service
        
        path = Path(filepath)
        
        # Check if already being processed
        if path.name in self.processing_files:
            return
            
        self.processing_files.add(path.name)
        
        try:
            # Wait a bit for file to be fully written
            await asyncio.sleep(1)
            
            if not path.exists():
                logger.warning(f"File no longer exists: {filepath}")
                return
            
            try:
                # Read file content
                with open(filepath, 'rb') as f:
                    content = f.read()
                
                if not content:
                    logger.warning(f"Empty file: {filepath}")
                    return
                
                # Check if exists in DB
                from app.db.repositories.document_repo import DocumentRepository
                existing = await DocumentRepository.find_by_filename(path.name)
                if existing:
                    logger.info(f"Skipping duplicate file: {path.name}")
                    # Add to processed list to avoid re-checking
                    self.processed_files.append({
                        "filename": path.name,
                        "filepath": filepath,
                        "doc_id": existing.id,
                        "processed_at": datetime.now().isoformat()
                    })
                    return

                # Upload via document service
                service = get_document_service()
                result = await service.upload_document(path.name, content)
                
                logger.info(f"Auto-processed invoice: {path.name} -> {result.doc_id}")
                
                # Track processed file
                self.processed_files.append({
                    "filename": path.name,
                    "filepath": filepath,
                    "doc_id": result.doc_id,
                    "processed_at": datetime.now().isoformat()
                })
                
                # Keep only last 50 processed files
                if len(self.processed_files) > 50:
                    self.processed_files = self.processed_files[-50:]
                
            except Exception as e:
                logger.error(f"Failed to process {filepath}: {e}")
        finally:
            if path.name in self.processing_files:
                self.processing_files.remove(path.name)
    
    def start(self, folder_path: str, auto_validate: bool = True) -> bool:
        """Start watching a folder"""
        if self.is_running:
            self.stop()
        
        # Reset watch_path to ensure clean state
        self.watch_path = None
        
        path = Path(folder_path)
        
        # Ensure it's a directory path, not a file
        if path.is_file():
            logger.error(f"Watch path is a file, not a directory: {folder_path}")
            return False
        
        if not path.exists():
            try:
                path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created watch folder: {folder_path}")
            except Exception as e:
                logger.error(f"Failed to create watch folder: {e}")
                return False
        
        if not path.is_dir():
            logger.error(f"Watch path is not a directory: {folder_path}")
            return False
        
        # Store as absolute path string
        self.watch_path = str(path.absolute())
        self.auto_validate = auto_validate
        
        # Create handler and observer
        handler = InvoiceFileHandler(self._process_file)
        # Use PollingObserver for better Windows compatibility
        self.observer = PollingObserver()
        self.observer.schedule(handler, self.watch_path, recursive=False)
        
        try:
            self.observer.start()
            self.is_running = True
            logger.info(f"Started watching folder: {self.watch_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to start folder watcher: {e}")
            self.watch_path = None
            return False
    
    def stop(self) -> bool:
        """Stop watching"""
        if not self.is_running or not self.observer:
            return False
        
        try:
            self.observer.stop()
            self.observer.join(timeout=5)
            self.is_running = False
            # Keep watch_path so UI can show last watched folder
            logger.info("Stopped folder watcher")
            return True
        except Exception as e:
            logger.error(f"Error stopping watcher: {e}")
            return False
    
    def get_status(self) -> dict:
        """Get current watcher status"""
        return {
            "is_running": self.is_running,
            "watch_path": self.watch_path,
            "auto_validate": self.auto_validate,
            "processed_count": len(self.processed_files),
            "recent_files": self.processed_files[-10:] if self.processed_files else []
        }
    
    async def scan_folder_async(self) -> list:
        """Scan folder for existing unprocessed files and process them (async version)"""
        if not self.watch_path:
            return []
        
        from app.services.document_service import get_document_service
        
        path = Path(self.watch_path)
        if not path.exists():
            return []
        
        processed_paths = {f.get("filepath") for f in self.processed_files}
        supported_extensions = {'.pdf', '.png', '.jpg', '.jpeg', '.txt', '.csv'}
        new_files = []
        
        for file_path in path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                
                # Check if already processed (local check)
                if str(file_path) in processed_paths or str(file_path.absolute()) in processed_paths:
                    continue

                # Check if currently being processed (Lock)
                if file_path.name in self.processing_files:
                    continue
                
                self.processing_files.add(file_path.name)
                
                try:
                    # Read content
                    with open(file_path, 'rb') as f:
                        content = f.read()
                    
                    if content:
                        # Check if exists in DB
                        from app.db.repositories.document_repo import DocumentRepository
                        existing = await DocumentRepository.find_by_filename(file_path.name)
                        
                        if existing:
                            continue

                        # Upload via document service
                        service = get_document_service()
                        result = await service.upload_document(file_path.name, content)
                        
                        new_files.append({"filename": file_path.name, "doc_id": result.doc_id})
                        
                        self.processed_files.append({
                            "filename": file_path.name,
                            "filepath": str(file_path),
                            "doc_id": result.doc_id,
                            "processed_at": datetime.now().isoformat()
                        })
                except Exception as e:
                    logger.error(f"Failed to scan/process {file_path}: {e}")
                finally:
                    if file_path.name in self.processing_files:
                        self.processing_files.remove(file_path.name)
        
        return new_files


# Global instance
_folder_watcher: FolderWatcher | None = None


def get_folder_watcher() -> FolderWatcher:
    """Get or create folder watcher instance"""
    global _folder_watcher
    if _folder_watcher is None:
        _folder_watcher = FolderWatcher()
    return _folder_watcher


