"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, Mic, MicOff, CheckCircle } from "lucide-react";
import { startSession } from "@/lib/api";

interface MediaPreCheckProps {
  sessionId: string;
  onReady: (token: string, url: string) => void;
}

type MicStatus = "idle" | "checking" | "verified" | "error";

// Inline SignalBars sub-component
function SignalBars({ amplitude }: { amplitude: number }) {
  const bars = [0.2, 0.4, 0.6, 0.8, 1.0];
  return (
    <div className="flex items-end gap-1 h-8" aria-hidden="true">
      {bars.map((threshold, i) => {
        const active = amplitude / 255 >= threshold;
        return (
          <div
            key={i}
            className={`w-2 rounded-sm transition-colors ${active ? "bg-emerald-400" : "bg-zinc-700"}`}
            style={{ height: `${(i + 1) * 20}%` }}
          />
        );
      })}
    </div>
  );
}

export default function MediaPreCheck({ sessionId, onReady }: MediaPreCheckProps) {
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string | null>(null);
  const [micStatus, setMicStatus] = useState<MicStatus>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);
  const [amplitude, setAmplitude] = useState(0);

  const streamRef = useRef<MediaStream | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Enumerate devices on mount and auto-start sampling with the first device.
  // We request mic permission first so enumerateDevices returns real labels/IDs.
  useEffect(() => {
    async function initDevices() {
      try {
        // Trigger permission prompt; the stream is immediately stopped after
        const permStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        permStream.getTracks().forEach((t) => t.stop());
      } catch {
        // Permission denied — startSampling will surface the proper error
      }
      const all = await navigator.mediaDevices.enumerateDevices();
      const inputs = all.filter((d) => d.kind === "audioinput");
      setDevices(inputs);
      if (inputs.length > 0) {
        setSelectedDeviceId(inputs[0].deviceId);
        startSampling(inputs[0].deviceId);
      }
    }
    initDevices();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Teardown helper
  function teardown() {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (audioCtxRef.current) {
      audioCtxRef.current.close();
      audioCtxRef.current = null;
    }
  }

  // Cleanup on unmount
  useEffect(() => {
    return () => teardown();
  }, []);

  // Start mic sampling when device is selected
  async function startSampling(deviceId: string) {
    teardown();
    setMicStatus("checking");
    setErrorMessage(null);
    setAmplitude(0);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { deviceId: { exact: deviceId } },
      });
      streamRef.current = stream;

      const ctx = new AudioContext();
      audioCtxRef.current = ctx;

      const source = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);

      const dataArray = new Uint8Array(analyser.frequencyBinCount);

      intervalRef.current = setInterval(() => {
        analyser.getByteFrequencyData(dataArray);
        const avg = dataArray.reduce((sum, v) => sum + v, 0) / dataArray.length;
        setAmplitude(avg);
        if (avg > 10) {
          setMicStatus("verified");
        }
      }, 100);
    } catch (err: unknown) {
      const name = err instanceof Error ? err.name : "";
      if (name === "NotAllowedError") {
        setErrorMessage(
          "Microphone access was denied. Please allow microphone permissions in your browser settings and try again."
        );
      } else if (name === "NotFoundError") {
        setErrorMessage(
          "No microphone found. Please connect a microphone and try again."
        );
      } else {
        setErrorMessage("Unable to access microphone. Please check your device and try again.");
      }
      setMicStatus("error");
    }
  }

  function handleDeviceChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const id = e.target.value;
    setSelectedDeviceId(id);
    startSampling(id);
  }

  async function handleEnterBooth() {
    if (micStatus !== "verified" || isLoading) return;
    setIsLoading(true);
    setStartError(null);
    try {
      const { livekit_token, livekit_url } = await startSession(sessionId);
      onReady(livekit_token, livekit_url);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to start session. Please try again.";
      setStartError(msg);
      setIsLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-900 flex items-center justify-center p-6">
      <div className="w-full max-w-md rounded-xl bg-slate-800 border border-zinc-700 shadow-2xl p-8 space-y-6">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-zinc-100">Microphone Check</h2>
          <p className="mt-1 text-sm text-zinc-400">
            Verify your audio before entering the practice room.
          </p>
        </div>

        {/* Device selector */}
        <div className="space-y-2">
          <label className="block text-sm font-medium text-zinc-300" htmlFor="mic-select">
            Audio Input Device
          </label>
          <select
            id="mic-select"
            value={selectedDeviceId ?? ""}
            onChange={handleDeviceChange}
            className="w-full rounded-lg bg-slate-900 border border-zinc-700 px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            {devices.length === 0 && (
              <option value="">No devices found</option>
            )}
            {devices.map((d) => (
              <option key={d.deviceId} value={d.deviceId}>
                {d.label || `Microphone ${d.deviceId.slice(0, 8)}`}
              </option>
            ))}
          </select>
        </div>

        {/* Signal bars */}
        <div className="flex flex-col items-center gap-3 py-2">
          <SignalBars amplitude={amplitude} />
          <p className="text-xs text-zinc-500">Speak to test your microphone level</p>
        </div>

        {/* Status indicator */}
        {micStatus === "verified" && (
          <div className="flex items-center gap-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 px-4 py-3">
            <CheckCircle size={16} className="text-emerald-400 shrink-0" />
            <span className="text-sm text-emerald-300">Microphone verified</span>
          </div>
        )}

        {micStatus === "checking" && (
          <div className="flex items-center gap-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20 px-4 py-3">
            <Mic size={16} className="text-indigo-400 shrink-0" />
            <span className="text-sm text-indigo-300">Checking microphone… speak to verify</span>
          </div>
        )}

        {micStatus === "error" && errorMessage && (
          <div className="flex items-start gap-2 rounded-lg bg-red-500/10 border border-red-500/20 px-4 py-3">
            <MicOff size={16} className="text-red-400 shrink-0 mt-0.5" />
            <span className="text-sm text-red-300">{errorMessage}</span>
          </div>
        )}

        {/* Start session error */}
        {startError && (
          <p className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
            {startError}
          </p>
        )}

        {/* Enter booth button */}
        <button
          onClick={handleEnterBooth}
          disabled={micStatus !== "verified" || isLoading}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium text-sm transition-colors"
        >
          {isLoading && <Loader2 size={16} className="animate-spin" />}
          {isLoading ? "Connecting…" : "Enter Practice Booth"}
        </button>
      </div>
    </main>
  );
}
