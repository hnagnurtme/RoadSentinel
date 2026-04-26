"""
core/ai/performance_monitor.py
-------------------------------
Performance monitoring and metrics collection for AI pipeline.

Tracks:
- Frame processing latency
- AI inference timing
- Memory usage
- Throughput metrics
- Error rates
"""

import time
import logging
from typing import Dict
from dataclasses import dataclass
from collections import deque
import threading

logger = logging.getLogger(__name__)

@dataclass
class FrameMetrics:
    """Metrics for a single processed frame."""
    timestamp: float
    processing_time_ms: float
    inference_time_ms: float
    detection_count: int
    frame_size_bytes: int
    skipped: bool = False

@dataclass
class PerformanceStats:
    """Aggregated performance statistics."""
    total_frames: int = 0
    processed_frames: int = 0
    skipped_frames: int = 0
    avg_processing_time_ms: float = 0.0
    avg_inference_time_ms: float = 0.0
    avg_fps: float = 0.0
    current_fps: float = 0.0
    memory_usage_mb: float = 0.0
    error_rate: float = 0.0
    uptime_seconds: float = 0.0

class PerformanceMonitor:
    """Real-time performance monitoring for AI pipeline."""
    
    def __init__(self, window_size: int = 1000, history_size: int = 10000):
        self.window_size = window_size
        self.history_size = history_size
        
        # Metrics storage
        self.frame_metrics: deque[FrameMetrics] = deque(maxlen=history_size)
        self.recent_metrics: deque[FrameMetrics] = deque(maxlen=window_size)
        
        # Timing
        self.start_time = time.time()
        self.last_frame_time = 0.0
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Performance counters
        self.error_count = 0
        self.total_processed = 0
        
        logger.info("Performance monitor initialized")

    def record_frame(
        self,
        processing_time_ms: float,
        inference_time_ms: float,
        detection_count: int,
        frame_size_bytes: int,
        skipped: bool = False
    ) -> None:
        """Record metrics for a processed frame."""
        with self.lock:
            timestamp = time.time()
            metrics = FrameMetrics(
                timestamp=timestamp,
                processing_time_ms=processing_time_ms,
                inference_time_ms=inference_time_ms,
                detection_count=detection_count,
                frame_size_bytes=frame_size_bytes,
                skipped=skipped
            )
            
            self.frame_metrics.append(metrics)
            self.recent_metrics.append(metrics)
            
            if not skipped:
                self.total_processed += 1
            
            self.last_frame_time = timestamp

    def record_error(self) -> None:
        """Record an error occurrence."""
        with self.lock:
            self.error_count += 1

    def get_stats(self) -> PerformanceStats:
        """Get current performance statistics."""
        with self.lock:
            now = time.time()
            uptime = now - self.start_time
            
            if not self.recent_metrics:
                return PerformanceStats(uptime_seconds=uptime)
            
            # Calculate averages from recent metrics
            processed_metrics = [m for m in self.recent_metrics if not m.skipped]
            skipped_metrics = [m for m in self.recent_metrics if m.skipped]
            
            total_frames = len(self.recent_metrics)
            processed_frames = len(processed_metrics)
            skipped_frames = len(skipped_metrics)
            
            if processed_frames:
                avg_processing = sum(m.processing_time_ms for m in processed_metrics) / processed_frames
                avg_inference = sum(m.inference_time_ms for m in processed_metrics) / processed_frames
            else:
                avg_processing = avg_inference = 0.0
            
            # Calculate FPS
            if len(self.recent_metrics) >= 2:
                time_span = self.recent_metrics[-1].timestamp - self.recent_metrics[0].timestamp
                current_fps = (len(self.recent_metrics) / time_span) if time_span > 0 else 0.0
            else:
                current_fps = 0.0
            
            # Overall FPS
            overall_fps = self.total_processed / uptime if uptime > 0 else 0.0
            
            # Error rate
            error_rate = (self.error_count / max(1, self.total_processed + self.error_count)) * 100
            
            # Memory usage (simplified)
            try:
                import psutil
                memory_usage = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            except ImportError:
                memory_usage = 0.0
            
            return PerformanceStats(
                total_frames=total_frames,
                processed_frames=processed_frames,
                skipped_frames=skipped_frames,
                avg_processing_time_ms=avg_processing,
                avg_inference_time_ms=avg_inference,
                avg_fps=overall_fps,
                current_fps=current_fps,
                memory_usage_mb=memory_usage,
                error_rate=error_rate,
                uptime_seconds=uptime
            )

    def get_recent_latency(self, seconds: float = 60.0) -> Dict[str, float]:
        """Get latency metrics for recent time window."""
        with self.lock:
            cutoff = time.time() - seconds
            recent = [m for m in self.frame_metrics if m.timestamp >= cutoff and not m.skipped]
            
            if not recent:
                return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "max": 0.0}
            
            processing_times = sorted(m.processing_time_ms for m in recent)
            n = len(processing_times)
            
            return {
                "p50": processing_times[n // 2],
                "p95": processing_times[int(n * 0.95)],
                "p99": processing_times[int(n * 0.99)],
                "max": max(processing_times),
                "count": n
            }

    def reset(self) -> None:
        """Reset all metrics."""
        with self.lock:
            self.frame_metrics.clear()
            self.recent_metrics.clear()
            self.error_count = 0
            self.total_processed = 0
            self.start_time = time.time()
            self.last_frame_time = 0.0
            logger.info("Performance metrics reset")

    def log_stats(self) -> None:
        """Log current performance statistics."""
        stats = self.get_stats()
        
        logger.info(
            f"[PERF] FPS: {stats.current_fps:.1f} ({stats.avg_fps:.1f} avg) | "
            f"Processing: {stats.avg_processing_time_ms:.1f}ms | "
            f"Inference: {stats.avg_inference_time_ms:.1f}ms | "
            f"Memory: {stats.memory_usage_mb:.1f}MB | "
            f"Errors: {stats.error_rate:.1f}% | "
            f"Skipped: {stats.skipped_frames}/{stats.total_frames}"
        )

# Global performance monitor instance
performance_monitor = PerformanceMonitor()
