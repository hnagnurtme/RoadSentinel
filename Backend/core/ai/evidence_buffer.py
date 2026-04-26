"""
core/ai/evidence_buffer.py
----------------------------
Rolling evidence buffer with pre-event capture for driver monitoring.

This replaces the current evidence pipeline with a more robust
pre-event capture system that includes event onset context.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from collections import deque
import time
import uuid


@dataclass
class EvidenceFramePacket:
    """Single frame packet for evidence collection."""
    timestamp: float
    frame_idx: int
    jpeg_bytes: bytes
    detections: List[Dict[str, Any]]  # Raw YOLO detections
    event: Optional[str] = None     # Dominant event at this frame
    confidence: float = 0.0


@dataclass
class EvidenceConfig:
    """Configuration for evidence buffer."""
    enabled: bool = True
    fps: int = 5
    pre_event_seconds: int = 3    # capture onset
    post_event_seconds: int = 7   # capture peak + resolution
    codec: str = "mp4v"
    codec_candidates: List[str] = field(default_factory=lambda: ["avc1", "H264", "mp4v"])
    keep_local_after_upload: bool = False
    # Only save evidence for WARNING and CRITICAL
    min_severity_for_evidence: str = "WARNING"


class RollingEvidenceBuffer:
    """
    Pre-event buffer: keeps the last N seconds of frames so the clip
    includes context BEFORE the event was confirmed.

    Pre-buffer: 3 seconds before event confirmed (captures onset)
    Post-buffer: filled after trigger fires (captures peak)
    Total clip: pre + post = configurable (default 10s)
    """

    def __init__(self, config: EvidenceConfig) -> None:
        self._cfg = config
        total_frames = config.fps * (config.pre_event_seconds + config.post_event_seconds)
        self._pre_frames = config.fps * config.pre_event_seconds
        self._buffer: deque[EvidenceFramePacket] = deque(maxlen=total_frames)
        self._triggered = False
        self._post_count = 0
        self._post_target = config.fps * config.post_event_seconds
        self._frame_idx = 0

    def push(self, 
             jpeg_bytes: bytes, 
             detections: List[Dict[str, Any]], 
             event: Optional[str] = None,
             confidence: float = 0.0) -> bool:
        """
        Add a new frame to the buffer.
        
        Returns True when the post-trigger buffer is full (clip is ready).
        """
        if not self._cfg.enabled:
            return False
            
        packet = EvidenceFramePacket(
            timestamp=time.time(),
            frame_idx=self._frame_idx,
            jpeg_bytes=jpeg_bytes,
            detections=detections,
            event=event,
            confidence=confidence
        )
        
        self._buffer.append(packet)
        self._frame_idx += 1
        
        if self._triggered:
            self._post_count += 1
            return self._post_count >= self._post_target
        return False

    def trigger(self) -> None:
        """Call when AlertDecisionEngine fires. Starts post-event capture."""
        if not self._cfg.enabled:
            return
        self._triggered = True
        self._post_count = 0

    def get_clip_frames(self) -> List[EvidenceFramePacket]:
        """Get all frames for the current evidence clip."""
        return list(self._buffer)

    def is_ready(self) -> bool:
        """Check if the post-trigger buffer is full and clip is ready."""
        return self._triggered and self._post_count >= self._post_target

    def reset(self) -> None:
        """Reset buffer state (call after clip is saved)."""
        self._buffer.clear()
        self._triggered = False
        self._post_count = 0
        self._frame_idx = 0


class EvidenceClipProcessor:
    """
    Processes evidence clips from buffer frames.
    Handles encoding, uploading, and cleanup.
    """

    def __init__(self, config: EvidenceConfig) -> None:
        self._cfg = config
        self._upload_enabled = False  # Will be set based on Cloudinary config

    def process_clip(self, 
                   frames: List[EvidenceFramePacket],
                   alert_id: uuid.UUID,
                   event_type: str) -> Optional[str]:
        """
        Process frames into an evidence clip and upload.
        
        Returns the evidence URL if successful, None otherwise.
        """
        if not frames or not self._cfg.enabled:
            return None
            
        try:
            # TODO: Implement video encoding using OpenCV
            # This would involve:
            # 1. Creating a video writer with configured codec
            # 2. Decoding JPEG frames and writing to video
            # 3. Saving to temporary file
            # 4. Uploading to Cloudinary if enabled
            # 5. Cleaning up temporary file if not configured to keep
            
            # For now, return a placeholder URL
            evidence_url = f"evidence/{alert_id}_{event_type}.mp4"
            
            # TODO: Implement actual Cloudinary upload
            # if self._upload_enabled:
            #     evidence_url = self._upload_to_cloudinary(temp_file, alert_id, event_type)
            
            return evidence_url
            
        except Exception as e:
            # Log error but don't fail the alert
            print(f"Failed to process evidence clip: {e}")
            return None

    def enable_upload(self, cloudinary_config: Dict[str, Any]) -> None:
        """Enable Cloudinary upload with provided configuration."""
        self._upload_enabled = bool(cloudinary_config.get("enabled", False))
        # TODO: Initialize Cloudinary client here
