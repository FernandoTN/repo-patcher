"""Graceful shutdown handling for long-running operations."""
import signal
import asyncio
import threading
import time
from typing import List, Optional, Callable, Any
from contextlib import asynccontextmanager
import logging

from .structured_logging import get_logger


class GracefulShutdown:
    """Handles graceful shutdown of the application."""
    
    def __init__(self, timeout: float = 30.0):
        """
        Initialize graceful shutdown handler.
        
        Args:
            timeout: Maximum time to wait for shutdown in seconds
        """
        self.timeout = timeout
        self.logger = get_logger(__name__)
        self.shutdown_event = asyncio.Event()
        self.cleanup_tasks: List[Callable] = []
        self.active_operations: List[asyncio.Task] = []
        self._shutdown_in_progress = False
        self._lock = asyncio.Lock()
    
    def register_cleanup(self, cleanup_func: Callable) -> None:
        """Register a cleanup function to be called on shutdown."""
        self.cleanup_tasks.append(cleanup_func)
    
    def register_signal_handlers(self) -> None:
        """Register signal handlers for graceful shutdown."""
        if threading.current_thread() == threading.main_thread():
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            
            # On Windows, also handle CTRL_BREAK_EVENT
            if hasattr(signal, 'SIGBREAK'):
                signal.signal(signal.SIGBREAK, self._signal_handler)
    
    def _signal_handler(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals."""
        signal_names = {
            signal.SIGINT: "SIGINT",
            signal.SIGTERM: "SIGTERM"
        }
        if hasattr(signal, 'SIGBREAK'):
            signal_names[signal.SIGBREAK] = "SIGBREAK"
        
        signal_name = signal_names.get(signum, f"Signal {signum}")
        self.logger.info(f"Received {signal_name}, initiating graceful shutdown")
        
        # Set shutdown event
        asyncio.create_task(self._initiate_shutdown())
    
    async def _initiate_shutdown(self) -> None:
        """Initiate the shutdown process."""
        async with self._lock:
            if self._shutdown_in_progress:
                return
            
            self._shutdown_in_progress = True
            self.shutdown_event.set()
    
    async def wait_for_shutdown(self) -> None:
        """Wait for shutdown signal."""
        await self.shutdown_event.wait()
    
    async def shutdown(self) -> None:
        """Perform graceful shutdown."""
        self.logger.info("Starting graceful shutdown")
        start_time = time.time()
        
        try:
            # Cancel active operations
            if self.active_operations:
                self.logger.info(f"Cancelling {len(self.active_operations)} active operations")
                
                for task in self.active_operations:
                    if not task.done():
                        task.cancel()
                
                # Wait for operations to complete or timeout
                if self.active_operations:
                    try:
                        await asyncio.wait_for(
                            asyncio.gather(*self.active_operations, return_exceptions=True),
                            timeout=self.timeout * 0.8  # Use 80% of timeout for operations
                        )
                    except asyncio.TimeoutError:
                        self.logger.warning("Some operations did not complete within timeout")
            
            # Run cleanup tasks
            if self.cleanup_tasks:
                self.logger.info(f"Running {len(self.cleanup_tasks)} cleanup tasks")
                
                cleanup_timeout = self.timeout * 0.2  # Use 20% of timeout for cleanup
                for cleanup_func in self.cleanup_tasks:
                    try:
                        if asyncio.iscoroutinefunction(cleanup_func):
                            await asyncio.wait_for(cleanup_func(), timeout=cleanup_timeout / len(self.cleanup_tasks))
                        else:
                            cleanup_func()
                    except Exception as e:
                        self.logger.error(f"Cleanup function failed: {e}")
            
            duration = time.time() - start_time
            self.logger.info(f"Graceful shutdown completed in {duration:.2f} seconds")
            
        except Exception as e:
            self.logger.error(f"Error during graceful shutdown: {e}")
            raise
    
    @asynccontextmanager
    async def operation(self, name: str = "operation"):
        """Context manager for tracking long-running operations."""
        task = asyncio.current_task()
        if task:
            async with self._lock:
                self.active_operations.append(task)
            
            self.logger.debug(f"Started operation: {name}")
            
            try:
                yield
            except asyncio.CancelledError:
                self.logger.info(f"Operation cancelled: {name}")
                raise
            except Exception as e:
                self.logger.error(f"Operation failed: {name}", error=str(e))
                raise
            finally:
                async with self._lock:
                    if task in self.active_operations:
                        self.active_operations.remove(task)
                
                self.logger.debug(f"Completed operation: {name}")
    
    def is_shutdown_requested(self) -> bool:
        """Check if shutdown has been requested."""
        return self.shutdown_event.is_set()


class ResourceManager:
    """Manages resources with automatic cleanup."""
    
    def __init__(self, shutdown_handler: GracefulShutdown):
        """Initialize resource manager."""
        self.shutdown_handler = shutdown_handler
        self.resources: List[Any] = []
        self.logger = get_logger(__name__)
        
        # Register cleanup
        shutdown_handler.register_cleanup(self.cleanup_all)
    
    def register_resource(self, resource: Any, cleanup_method: str = "close") -> Any:
        """
        Register a resource for automatic cleanup.
        
        Args:
            resource: Resource to manage
            cleanup_method: Method name to call for cleanup
            
        Returns:
            The resource (for chaining)
        """
        setattr(resource, "_cleanup_method", cleanup_method)
        self.resources.append(resource)
        return resource
    
    async def cleanup_all(self) -> None:
        """Clean up all registered resources."""
        if not self.resources:
            return
        
        self.logger.info(f"Cleaning up {len(self.resources)} resources")
        
        for resource in reversed(self.resources):  # Cleanup in reverse order
            try:
                cleanup_method = getattr(resource, "_cleanup_method", "close")
                
                if hasattr(resource, cleanup_method):
                    method = getattr(resource, cleanup_method)
                    
                    if asyncio.iscoroutinefunction(method):
                        await method()
                    else:
                        method()
                
            except Exception as e:
                self.logger.error(f"Failed to cleanup resource {type(resource).__name__}: {e}")
        
        self.resources.clear()


class TimeoutManager:
    """Manages timeouts for operations."""
    
    def __init__(self, shutdown_handler: GracefulShutdown):
        """Initialize timeout manager."""
        self.shutdown_handler = shutdown_handler
        self.logger = get_logger(__name__)
    
    @asynccontextmanager
    async def timeout(self, seconds: float, operation_name: str = "operation"):
        """Context manager with timeout that respects shutdown."""
        try:
            # Check if shutdown is already requested
            if self.shutdown_handler.is_shutdown_requested():
                raise asyncio.CancelledError("Shutdown requested")
            
            # Create timeout task
            timeout_task = asyncio.create_task(asyncio.sleep(seconds))
            shutdown_task = asyncio.create_task(self.shutdown_handler.wait_for_shutdown())
            
            # Wait for either timeout or shutdown
            done, pending = await asyncio.wait(
                [timeout_task, shutdown_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel pending tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            # Check what completed first
            if shutdown_task in done:
                self.logger.info(f"Operation '{operation_name}' interrupted by shutdown")
                raise asyncio.CancelledError("Shutdown requested")
            
            if timeout_task in done:
                self.logger.warning(f"Operation '{operation_name}' timed out after {seconds}s")
                raise asyncio.TimeoutError(f"Operation timed out after {seconds} seconds")
            
            # Normal execution
            yield
            
        except asyncio.CancelledError:
            self.logger.info(f"Operation '{operation_name}' was cancelled")
            raise
        except Exception as e:
            self.logger.error(f"Operation '{operation_name}' failed", error=str(e))
            raise


# Global shutdown handler
shutdown_handler = GracefulShutdown()
resource_manager = ResourceManager(shutdown_handler)
timeout_manager = TimeoutManager(shutdown_handler)


def setup_shutdown_handling() -> GracefulShutdown:
    """Set up global shutdown handling."""
    shutdown_handler.register_signal_handlers()
    return shutdown_handler


@asynccontextmanager
async def managed_operation(name: str = "operation"):
    """Context manager for managed operations."""
    async with shutdown_handler.operation(name):
        yield


@asynccontextmanager 
async def operation_timeout(seconds: float, name: str = "operation"):
    """Context manager for operations with timeout."""
    async with timeout_manager.timeout(seconds, name):
        yield