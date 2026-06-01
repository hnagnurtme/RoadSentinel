import { useEffect, useRef, useState, useCallback } from "react";
import React from "react";
import {
  Wifi, WifiOff, Camera, CameraOff, RefreshCw,
  ZapOff, Zap, Activity, Users, AlertTriangle
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useLanguage } from "@/i18n/LanguageContext";

const WS_BASE = (import.meta.env.VITE_WS_ALERTS_URL as string | undefined)
  ? (import.meta.env.VITE_WS_ALERTS_URL as string).replace(/\/alerts$/, "")
  : "ws://localhost:8000/api/v1/ws";
const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000/api/v1";
const UI_FRAME_INTERVAL_MS = 66;
const UI_STATS_INTERVAL_MS = 400;

// ─── Types ────────────────────────────────────────────────────────────────────

interface Driver {
  _id: string;
  name: string | null;
  email: string;
  avatar_image_url: string | null;
  name__given: string | null;
  name__family: string | null;
  role?: string;
}

interface Detection {
  label: string;
  conf: number;
  bbox: [number, number, number, number]; // x1, y1, x2, y2
}

interface FrameMessage {
  type: "frame";
  frame_idx: number;
  timestamp: number;
  jpeg: string;
  detections: Detection[];
  driver_event?: string;
  driver_confidence?: number;
  event_timing?: {
    active: boolean;
    event: string;
    started_at: number | null;
    duration_ms: number;
    confidence: number;
  };
  device: string;
}

interface PongMessage {
  type: "pong";
  camera: boolean;
  clients: number;
  device: string;
}

interface AlertCreatedMessage {
  type: "alert_created";
  data: {
    _id: string | null;
    message: string;
    alert_type: string;
    device_id: string;
    driver_id: string | null;
    vehicle_id: string | null;
    evidence_url: string | null;
    _created_at: string | null;
  };
}

interface LiveViolationAlert {
  id: string;
  alertId: string | null;
  event: string;
  confidence: number;
  timestamp: number;
  frameIdx: number;
  message: string;
  evidenceUrl: string | null;
}

type WsMessage = FrameMessage | PongMessage | AlertCreatedMessage | { type: string; [k: string]: unknown };

// ─── Hook: useCameraStream ────────────────────────────────────────────────────

function useCameraStream(deviceId: string) {
  const [isConnected, setIsConnected] = useState(false);
  const [cameraOnline, setCameraOnline] = useState(false);
  const [viewers, setViewers] = useState(0);
  const [fps, setFps] = useState(0);
  const [totalFrames, setTotalFrames] = useState(0);
  const [lastJpeg, setLastJpeg] = useState<string | null>(null);
  const [detections, setDetections] = useState<Detection[]>([]);
  const [eventTiming, setEventTiming] = useState<FrameMessage["event_timing"] | null>(null);
  const [liveAlerts, setLiveAlerts] = useState<LiveViolationAlert[]>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const frameTimestamps = useRef<number[]>([]);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pingTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const alertTimers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());
  const latestFrameRef = useRef<{
    frameIdx: number;
    jpeg: string;
    detections: Detection[];
    eventTiming: FrameMessage["event_timing"] | null;
  } | null>(null);
  const lastRenderedFrameRef = useRef(0);
  const totalFramesRef = useRef(0);
  const lastStatsUpdateRef = useRef(0);
  
  // Debouncing for detection events
  const lastAlertProcessTime = useRef(0);
  const alertProcessingTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(`${WS_BASE}/frontend`);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      ws.send(JSON.stringify({ type: "ping" }));
      pingTimer.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "ping" }));
        }
      }, 15000);
    };

    ws.onmessage = (evt) => {
      console.log(`[DEBUG] WebSocket message type: ${typeof evt.data}, size: ${evt.data?.length || 'N/A'}`);
      
      // Handle binary JPEG frames directly
      if (evt.data instanceof Blob) {
        const reader = new FileReader();
        reader.onload = () => {
          const base64 = (reader.result as string).split(',')[1];
          const newFrameIdx = (latestFrameRef.current?.frameIdx ?? 0) + 1;
          
          // Merge with current state to preserve detections/timing from JSON messages
          latestFrameRef.current = {
            frameIdx: newFrameIdx,
            jpeg: base64,
            detections: latestFrameRef.current?.detections ?? [],
            eventTiming: latestFrameRef.current?.eventTiming ?? null,
          };
          totalFramesRef.current += 1;

          // FPS calculation
          const now = Date.now();
          frameTimestamps.current.push(now);
          const cutoff = now - 2000;
          frameTimestamps.current = frameTimestamps.current.filter((t: number) => t >= cutoff);

          if (now - lastStatsUpdateRef.current >= UI_STATS_INTERVAL_MS) {
            lastStatsUpdateRef.current = now;
            setFps(Math.round((frameTimestamps.current.length / 2) * 10) / 10);
            setTotalFrames(totalFramesRef.current);
          }
        };
        reader.readAsDataURL(evt.data);
        return;
      }

      // Handle JSON messages
      let data: WsMessage;
      try {
        data = JSON.parse(evt.data as string);
      } catch {
        return;
      }

      if (data.type === "frame") {
        const frame = data as FrameMessage;
        // Merge with current state to preserve jpeg from binary messages
        latestFrameRef.current = {
          frameIdx: frame.frame_idx,
          jpeg: frame.jpeg || latestFrameRef.current?.jpeg || "",
          detections: frame.detections ?? latestFrameRef.current?.detections ?? [],
          eventTiming: frame.event_timing ?? latestFrameRef.current?.eventTiming ?? null,
        };
        totalFramesRef.current += 1;

        // FPS calculation
        const now = Date.now();
        frameTimestamps.current.push(now);
        const cutoff = now - 2000;
        frameTimestamps.current = frameTimestamps.current.filter((t: number) => t >= cutoff);

        if (now - lastStatsUpdateRef.current >= UI_STATS_INTERVAL_MS) {
          lastStatsUpdateRef.current = now;
          setFps(Math.round((frameTimestamps.current.length / 2) * 10) / 10);
          setTotalFrames(totalFramesRef.current);
        }
      } else if (data.type === "pong") {
        const pong = data as PongMessage;
        setCameraOnline(pong.camera);
        setViewers(pong.clients);
      } else if (data.type === "alert_created") {
        // Debounce rapid alert processing to prevent UI overload
        const now = Date.now();
        const timeSinceLastAlert = now - lastAlertProcessTime.current;
        
        // Clear any pending timeout
        if (alertProcessingTimeout.current) {
          clearTimeout(alertProcessingTimeout.current);
        }
        
        // Process with debouncing - immediate for first alert, delayed for rapid ones
        const processAlert = () => {
          lastAlertProcessTime.current = Date.now();
          
          requestAnimationFrame(() => {
            const incoming = data as AlertCreatedMessage;
            const createdAtMs = incoming.data._created_at
              ? new Date(incoming.data._created_at).getTime()
              : Date.now();
            const confidenceMatch = incoming.data.message.match(/confidence=([0-9.]+)/i);
            const parsedConfidence = confidenceMatch ? Number.parseFloat(confidenceMatch[1]) : 0;
            const id = `${incoming.data._id ?? createdAtMs}-${Math.random().toString(16).slice(2, 8)}`;
            
            console.log(`[DEBUG] Processing alert: ${incoming.data.alert_type} (debounced)`);
            
            const alertItem: LiveViolationAlert = {
              id,
              alertId: incoming.data._id,
              event: incoming.data.alert_type,
              confidence: Number.isFinite(parsedConfidence) ? parsedConfidence : 0,
              timestamp: Number.isFinite(createdAtMs) ? createdAtMs : Date.now(),
              frameIdx: 0,
              message: incoming.data.message,
              evidenceUrl: incoming.data.evidence_url,
            };
            
            // Batch state update to prevent multiple re-renders
            setLiveAlerts((prev: LiveViolationAlert[]) => {
              const newAlerts = [alertItem, ...prev].slice(0, 4);
              return newAlerts;
            });

            const timer = setTimeout(() => {
              setLiveAlerts((prev: LiveViolationAlert[]) => prev.filter((item) => item.id !== id));
              alertTimers.current.delete(id);
            }, 12000);
            alertTimers.current.set(id, timer);
          });
        };
        
        // If rapid alerts (> 2 per second), debounce with 100ms delay
        if (timeSinceLastAlert < 500) {
          alertProcessingTimeout.current = setTimeout(processAlert, 100);
        } else {
          processAlert(); // Process immediately for spaced alerts
        }
      } else if (data.type === "camera_offline") {
        setCameraOnline(false);
        setEventTiming(null);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      setCameraOnline(false);
      if (pingTimer.current) clearInterval(pingTimer.current);
      reconnectTimer.current = setTimeout(connect, 4000);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [deviceId]);

  useEffect(() => {
    connect();
    return () => {
      if (pingTimer.current) clearInterval(pingTimer.current);
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      if (alertProcessingTimeout.current) clearTimeout(alertProcessingTimeout.current);
      for (const timer of alertTimers.current.values()) {
        clearTimeout(timer);
      }
      alertTimers.current.clear();
      wsRef.current?.close();
    };
  }, [connect]);

  useEffect(() => {
    let animationFrameId: number;
    let lastRenderTime = 0;
    const TARGET_INTERVAL = 1000 / 15; // 15 FPS target for UI

    const render = (timestamp: number) => {
      const latest = latestFrameRef.current;
      if (!latest) {
        animationFrameId = requestAnimationFrame(render);
        return;
      }

      // Debug logging
      if (latest.frameIdx % 10 === 0) {
        console.log(`[DEBUG] Frame ${latest.frameIdx}, lastRendered: ${lastRenderedFrameRef.current}`);
      }

      if (latest.frameIdx === lastRenderedFrameRef.current) {
        animationFrameId = requestAnimationFrame(render);
        return;
      }

      // Throttle rendering to target FPS
      if (timestamp - lastRenderTime >= TARGET_INTERVAL) {
        lastRenderedFrameRef.current = latest.frameIdx;
        setLastJpeg(latest.jpeg);
        setDetections(latest.detections);
        setEventTiming(latest.eventTiming);
        lastRenderTime = timestamp;
        
        console.log(`[DEBUG] Rendered frame ${latest.frameIdx}`);
      }

      animationFrameId = requestAnimationFrame(render);
    };

    animationFrameId = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  const sendCommand = useCallback((cmd: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(cmd));
    }
  }, []);

  const reconnect = useCallback(() => {
    if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    wsRef.current?.close();
    totalFramesRef.current = 0;
    lastStatsUpdateRef.current = 0;
    latestFrameRef.current = null;
    lastRenderedFrameRef.current = 0;
    setTotalFrames(0);
    frameTimestamps.current = [];
    setFps(0);
    setLastJpeg(null);
    setDetections([]);
    setEventTiming(null);
    setLiveAlerts([]);
    setTimeout(connect, 300);
  }, [connect]);

  return {
    isConnected,
    cameraOnline,
    viewers,
    fps,
    totalFrames,
    lastJpeg,
    detections,
    eventTiming,
    liveAlerts,
    reconnect,
  };
}

// ─── Hook: useDrivers ────────────────────────────────────────────────────────

function useDrivers() {
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`${API_BASE}/users`)
      .then((r) => r.json())
      .then((json) => {
        const data = json?.data ?? json ?? [];
        const allUsers = Array.isArray(data) ? data : [];
        const filteredDrivers = allUsers.filter((u: any) => u.role === "driver");
        setDrivers(filteredDrivers);
      })
      .catch(() => setDrivers([]))
      .finally(() => setLoading(false));
  }, []);

  return { drivers, loading };
}

// ─── LiveCanvas ───────────────────────────────────────────────────────────────

interface LiveCanvasProps {
  jpeg: string | null;
  detections: Detection[];
  cameraOnline: boolean;
  isConnected: boolean;
}

function LiveCanvas({ jpeg, detections, cameraOnline, isConnected }: LiveCanvasProps) {
  const frameCanvasRef = useRef<HTMLCanvasElement>(null);
  const overlayCanvasRef = useRef<HTMLCanvasElement>(null);
  const imgRef = useRef(new Image());
  const pendingRef = useRef<string | null>(null);
  const decodingRef = useRef(false);
  const detectionsRef = useRef<Detection[]>([]);
  const offscreenCanvasRef = useRef<OffscreenCanvas | null>(null);

  // Keep latest detections in a ref so the draw callback always has them
  useEffect(() => { detectionsRef.current = detections; }, [detections]);

  const drawAnnotations = useCallback(() => {
    const overlayCanvas = overlayCanvasRef.current;
    const frameCanvas = frameCanvasRef.current;
    if (!overlayCanvas || !frameCanvas) {
      return;
    }

    if (overlayCanvas.width !== frameCanvas.width || overlayCanvas.height !== frameCanvas.height) {
      overlayCanvas.width = frameCanvas.width;
      overlayCanvas.height = frameCanvas.height;
    }

    const ctx = overlayCanvas.getContext("2d");
    if (!ctx) {
      return;
    }

    ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);

    for (const det of detectionsRef.current) {
      const [x1, y1, x2, y2] = det.bbox;
      const label = `${det.label} ${(det.conf * 100).toFixed(0)}%`;

      ctx.strokeStyle = "#00ff88";
      ctx.lineWidth = 2;
      ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

      ctx.font = "bold 11px Inter, sans-serif";
      const textWidth = ctx.measureText(label).width;
      ctx.fillStyle = "rgba(0,255,136,0.85)";
      ctx.fillRect(x1, y1 - 16, textWidth + 6, 16);
      ctx.fillStyle = "#000";
      ctx.fillText(label, x1 + 3, y1 - 3);
    }
  }, []);

  useEffect(() => {
    drawAnnotations();
  }, [detections, drawAnnotations]);

  useEffect(() => {
    if (!jpeg) return;

    const img = imgRef.current;
    const frameCanvas = frameCanvasRef.current;
    if (!frameCanvas) return;

    // Initialize offscreen canvas for better performance
    if (!offscreenCanvasRef.current && typeof OffscreenCanvas !== 'undefined') {
      offscreenCanvasRef.current = new OffscreenCanvas(320, 240);
    }

    pendingRef.current = jpeg;

    const process = () => {
      if (decodingRef.current || !pendingRef.current) return;
      decodingRef.current = true;
      const src = `data:image/jpeg;base64,${pendingRef.current}`;
      pendingRef.current = null;

      console.log(`[DEBUG] Processing new frame, size: ${src.length}`);

      img.onload = () => {
        console.log(`[DEBUG] Image loaded, size: ${img.width}x${img.height}`);
        
        // Use offscreen canvas if available for better performance
        const targetCanvas = offscreenCanvasRef.current || frameCanvas;
        
        if (targetCanvas.width !== img.width || targetCanvas.height !== img.height) {
          targetCanvas.width = img.width;
          targetCanvas.height = img.height;
          if (frameCanvas.width !== img.width || frameCanvas.height !== img.height) {
            frameCanvas.width = img.width;
            frameCanvas.height = img.height;
          }
        }

        const ctx = targetCanvas.getContext("2d");
        if (ctx) {
          ctx.clearRect(0, 0, targetCanvas.width, targetCanvas.height);
          ctx.drawImage(img, 0, 0);
        }

        // If using offscreen canvas, copy to main canvas
        if (offscreenCanvasRef.current && frameCanvas) {
          const mainCtx = frameCanvas.getContext("2d");
          if (mainCtx) {
            mainCtx.clearRect(0, 0, frameCanvas.width, frameCanvas.height);
            mainCtx.drawImage(offscreenCanvasRef.current, 0, 0);
          }
        }

        drawAnnotations();
        decodingRef.current = false;
        
        console.log(`[DEBUG] Frame rendered to canvas`);
        
        // Process next frame if pending
        if (pendingRef.current) {
          requestAnimationFrame(process);
        }
      };
      
      img.onerror = () => {
        console.error(`[DEBUG] Image load failed`);
        decodingRef.current = false;
      };
      
      // Disable caching by adding timestamp
      img.src = src + `#${Date.now()}`;
    };

    requestAnimationFrame(process);
  }, [jpeg, drawAnnotations]);

  return (
    <div className="relative w-full bg-black rounded-xl overflow-hidden" style={{ aspectRatio: "4/3" }}>
      <canvas
        ref={frameCanvasRef}
        width={320}
        height={240}
        className="w-full h-full object-contain"
      />
      <canvas
        ref={overlayCanvasRef}
        width={320}
        height={240}
        className="absolute inset-0 w-full h-full object-contain pointer-events-none"
      />
      {/* Overlay when offline */}
      {(!isConnected || !cameraOnline) && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/80 gap-3">
          <CameraOff className="w-12 h-12 text-outline/50" />
          <p className="text-sm font-semibold text-outline/70">
            {!isConnected ? "Connecting to server…" : "Camera offline"}
          </p>
          {isConnected && !cameraOnline && (
            <p className="text-xs text-outline/50">Waiting for ESP32-CAM to connect</p>
          )}
        </div>
      )}
      {/* Live badge */}
      {cameraOnline && (
        <div className="absolute top-3 left-3 flex items-center gap-1.5 bg-black/60 backdrop-blur-sm px-2.5 py-1 rounded-full">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500" />
          </span>
          <span className="text-[10px] font-bold text-white uppercase tracking-widest">Live</span>
        </div>
      )}
    </div>
  );
}

interface EventTimingPanelProps {
  eventTiming: FrameMessage["event_timing"] | null;
}

function EventTimingPanel({ eventTiming }: EventTimingPanelProps) {
  if (!eventTiming?.active) {
    return (
      <div className="rounded-lg bg-surface-container px-3 py-1.5">
        <span className="text-[10px] font-bold uppercase tracking-wider text-outline">
          Event Timer: Idle
        </span>
      </div>
    );
  }
  const seconds = Math.max(0, Math.floor((eventTiming.duration_ms ?? 0) / 1000));
  const mm = String(Math.floor(seconds / 60)).padStart(2, "0");
  const ss = String(seconds % 60).padStart(2, "0");
  const eventName = eventTiming.event.replaceAll("_", " ");

  return (
    <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-1.5 flex items-center gap-2">
      <span className="text-[10px] font-bold uppercase tracking-wider text-red-700">Event Timer</span>
      <span className="text-xs font-semibold text-red-900">{eventName}</span>
      <span className="text-xs font-black tabular-nums text-red-700">{mm}:{ss}</span>
    </div>
  );
}

// ─── Live Monitor View (Sub-component) ──────────────────────────────────────────

interface LiveMonitorViewProps {
  deviceId: string;
  selectedDriver: Driver;
  onBack: () => void;
}

function LiveMonitorView({ deviceId, selectedDriver, onBack }: LiveMonitorViewProps) {
  const {
    isConnected,
    cameraOnline,
    viewers,
    fps,
    totalFrames,
    lastJpeg,
    detections,
    eventTiming,
    liveAlerts,
    reconnect,
  } = useCameraStream(deviceId);

  const audioContextRef = useRef<AudioContext | null>(null);
  const lastAlertIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (liveAlerts.length === 0) return;
    const newest = liveAlerts[0];
    if (!newest || lastAlertIdRef.current === newest.id) return;
    lastAlertIdRef.current = newest.id;

    setTimeout(() => {
      try {
        const AudioContextCtor = window.AudioContext || (window as any).webkitAudioContext;
        if (!AudioContextCtor) return;
        if (!audioContextRef.current) audioContextRef.current = new AudioContextCtor();
        const ctx = audioContextRef.current;
        if (ctx.state === "suspended") void ctx.resume();

        const t0 = ctx.currentTime;
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = "triangle";
        osc.frequency.setValueAtTime(980, t0);
        osc.frequency.exponentialRampToValueAtTime(740, t0 + 0.18);
        gain.gain.setValueAtTime(0.0001, t0);
        gain.gain.exponentialRampToValueAtTime(0.09, t0 + 0.03);
        gain.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.22);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(t0);
        osc.stop(t0 + 0.24);
      } catch (e) { /* ignore */ }
    }, 0);
  }, [liveAlerts]);

  useEffect(() => {
    return () => {
      if (audioContextRef.current) void audioContextRef.current.close();
    };
  }, []);

  const formatEvent = useCallback((event: string) => {
    return event.split("_").map(c => c.charAt(0).toUpperCase() + c.slice(1)).join(" ");
  }, []);

  return (
    <div className="flex flex-col gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Floating Alerts Container */}
      <div className="fixed right-6 top-24 z-40 w-[320px] pointer-events-none space-y-2">
        {liveAlerts.map((alert) => (
          <div key={alert.id} className="pointer-events-auto rounded-xl border border-red-500/25 bg-red-50/95 shadow-xl backdrop-blur px-3 py-2.5 animate-in slide-in-from-right-8 fade-in duration-300">
            <div className="flex items-start gap-2.5">
              <div className="mt-0.5 rounded-lg bg-red-100 p-1.5">
                <AlertTriangle className="w-4 h-4 text-red-700" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-[11px] font-black uppercase tracking-wider text-red-700">New Violation</p>
                <p className="text-sm font-bold text-red-900 truncate">{formatEvent(alert.event)}</p>
                <p className="text-[11px] text-red-800/80 mt-0.5 truncate">{alert.message}</p>
                <div className="mt-2 flex justify-end">
                  <button
                    onClick={() => alert.alertId && window.open(`${window.location.origin}/alerts/${alert.alertId}`, "_blank")}
                    className="text-[10px] font-bold uppercase tracking-wide px-2.5 py-1 rounded bg-red-700 text-white hover:bg-red-800 transition-colors"
                  >
                    View
                  </button>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* View Header */}
      <div className="flex justify-between items-end">
        <div className="flex flex-col gap-1">
          <button 
            onClick={onBack}
            className="text-xs font-bold text-outline hover:text-primary flex items-center gap-1 mb-2 transition-colors"
          >
            ← Back to Drivers
          </button>
          <h2 className="text-3xl font-extrabold tracking-tight text-primary flex items-center gap-3">
            <Activity className="w-8 h-8 text-red-500" />
            Monitoring: {selectedDriver.name || selectedDriver.email}
          </h2>
        </div>
        <div className="flex gap-2">
          <button
            onClick={reconnect}
            className="flex items-center gap-2 px-4 py-2 rounded-lg ring-1 ring-outline-variant/20 bg-surface-container-lowest hover:bg-surface-container-low text-secondary text-xs font-bold transition-all"
          >
            <RefreshCw className="w-4 h-4" />
            Reconnect
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Stream Stats */}
        <div className="lg:col-span-3 flex flex-col gap-4">
          <div className="bg-surface-container-lowest rounded-xl ring-1 ring-outline-variant/15 shadow-sm p-4 flex flex-col gap-3">
            <h3 className="text-xs font-bold text-primary uppercase tracking-wider flex items-center gap-2">
              <Activity className="w-4 h-4" /> Stream Status
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-surface-container-low/50 rounded-lg p-3 text-center">
                <p className="text-2xl font-black tabular-nums text-primary">{fps}</p>
                <p className="text-[9px] font-bold text-outline uppercase tracking-wider mt-0.5">FPS</p>
              </div>
              <div className="bg-surface-container-low/50 rounded-lg p-3 text-center">
                <p className="text-2xl font-black tabular-nums text-primary">{viewers}</p>
                <p className="text-[9px] font-bold text-outline uppercase tracking-wider mt-0.5">Viewers</p>
              </div>
              <div className="col-span-2 bg-surface-container-low/50 rounded-lg p-3 text-center">
                <p className="text-xl font-black tabular-nums text-primary">{totalFrames.toLocaleString()}</p>
                <p className="text-[9px] font-bold text-outline uppercase tracking-wider mt-0.5">Total Frames</p>
              </div>
            </div>
            <div className="space-y-2 mt-2 pt-2 border-t border-surface-container-high">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-outline uppercase">Network</span>
                <span className={cn("text-[10px] font-black uppercase", isConnected ? "text-emerald-600" : "text-red-500")}>
                  {isConnected ? "Connected" : "Offline"}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-outline uppercase">Camera</span>
                <span className={cn("text-[10px] font-black uppercase", cameraOnline ? "text-emerald-600" : "text-red-500")}>
                  {cameraOnline ? "Online" : "Waiting"}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Video Feed */}
        <div className="lg:col-span-9">
          <div className="bg-surface-container-lowest rounded-xl ring-1 ring-outline-variant/15 shadow-sm overflow-hidden">
            <div className="px-5 py-3.5 border-b border-surface-container-high bg-surface-container-low/30 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-xs font-bold text-primary uppercase tracking-wider">Live Feed</span>
                <EventTimingPanel eventTiming={eventTiming} />
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-bold text-outline bg-surface-container px-2 py-0.5 rounded font-mono">
                  {deviceId}
                </span>
              </div>
            </div>
            <div className="p-4">
              <LiveCanvas
                jpeg={lastJpeg}
                detections={detections}
                cameraOnline={cameraOnline}
                isConnected={isConnected}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Main Monitor Screen ──────────────────────────────────────────────────────

interface MonitorProps {
  deviceId: string;
}

export function Monitor({ deviceId }: MonitorProps) {
  const { language } = useLanguage();
  const { drivers, loading: driversLoading } = useDrivers();
  const [selectedDriver, setSelectedDriver] = useState<Driver | null>(null);
  const [viewMode, setViewMode] = useState<'list' | 'live'>('list');

  const handleStartMonitoring = (driver: Driver) => {
    setSelectedDriver(driver);
    setViewMode('live');
  };

  if (viewMode === 'live' && selectedDriver) {
    return (
      <div className="p-8 max-w-[1600px] min-h-screen">
        <LiveMonitorView 
          deviceId={deviceId} 
          selectedDriver={selectedDriver} 
          onBack={() => setViewMode('list')} 
        />
      </div>
    );
  }

  return (
    <div className="p-8 flex flex-col gap-8 max-w-[1600px] min-h-screen">
      {/* Header */}
      <div>
        <h2 className="text-4xl font-black tracking-tight text-primary flex items-center gap-4">
          <Users className="w-10 h-10 text-primary" />
          LiveMonitor
        </h2>
        <p className="text-secondary text-sm mt-2 max-w-2xl">
          {language === "en"
            ? "Select a driver from the list below to begin real-time monitoring. The camera stream will only be activated once a specific driver is selected."
            : "Chọn một tài xế từ danh sách bên dưới để bắt đầu giám sát thời gian thực. Luồng camera sẽ chỉ được kích hoạt sau khi một tài xế cụ thể được chọn."}
        </p>
      </div>

      {/* Driver Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {driversLoading ? (
          Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="bg-surface-container-lowest rounded-2xl p-6 ring-1 ring-outline-variant/15 animate-pulse flex flex-col gap-4">
              <div className="w-16 h-16 rounded-full bg-surface-container-high" />
              <div className="space-y-2">
                <div className="h-4 bg-surface-container-high rounded w-3/4" />
                <div className="h-3 bg-surface-container-high rounded w-1/2" />
              </div>
              <div className="mt-4 h-10 bg-surface-container-high rounded-xl" />
            </div>
          ))
        ) : drivers.length === 0 ? (
          <div className="col-span-full py-20 text-center flex flex-col items-center gap-3 bg-surface-container-low rounded-3xl border-2 border-dashed border-outline-variant/30">
            <Users className="w-12 h-12 text-outline/30" />
            <p className="text-secondary font-medium">No drivers found in the system.</p>
          </div>
        ) : (
          drivers.map((driver) => {
            const displayName = driver.name || [driver.name__given, driver.name__family].filter(Boolean).join(" ") || driver.email;
            return (
              <div 
                key={driver._id}
                className="group bg-surface-container-lowest rounded-2xl p-6 ring-1 ring-outline-variant/15 hover:ring-primary/30 hover:shadow-xl hover:shadow-primary/5 transition-all flex flex-col gap-4"
              >
                <div className="flex items-center gap-4">
                  {driver.avatar_image_url ? (
                    <img
                      src={driver.avatar_image_url}
                      alt={displayName}
                      className="w-16 h-16 rounded-2xl object-cover ring-4 ring-surface-container-low group-hover:ring-primary/10 transition-all"
                      referrerPolicy="no-referrer"
                    />
                  ) : (
                    <div className="w-16 h-16 rounded-2xl bg-primary/5 flex items-center justify-center text-2xl font-black text-primary">
                      {displayName.charAt(0).toUpperCase()}
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <h3 className="font-bold text-on-surface truncate group-hover:text-primary transition-colors">
                      {displayName}
                    </h3>
                    <p className="text-xs text-outline truncate">{driver.email}</p>
                  </div>
                </div>
                
                <div className="mt-2 pt-4 border-t border-surface-container-high">
                  <button
                    onClick={() => handleStartMonitoring(driver)}
                    className="w-full flex items-center justify-center gap-2 bg-surface-container-high hover:bg-primary hover:text-white text-on-surface-variant font-bold text-sm py-3 rounded-xl transition-all"
                  >
                    <Camera className="w-4 h-4" />
                    View Monitor
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
