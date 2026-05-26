"use client";

import { useState, useEffect, use } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  LiveKitRoom,
  RoomAudioRenderer,
  useTracks,
  VideoTrack,
  useRoomContext,
} from "@livekit/components-react";
import { RoomEvent, Track } from "livekit-client";
import MediaPreCheck from "@/components/MediaPreCheck";
import { Bot } from "lucide-react";

// ── LocalCameraPanel ──────────────────────────────────────────────────────────

function LocalCameraPanel() {
  const tracks = useTracks(
    [{ source: Track.Source.Camera, withPlaceholder: true }],
    { onlySubscribed: false }
  );
  const localTrack = tracks[0];

  // A placeholder track has no `publication`; only render VideoTrack for real tracks
  const hasRealTrack = localTrack && localTrack.publication !== undefined && !localTrack.publication.isMuted;

  return (
    <div className="relative w-full h-full bg-slate-900 flex items-center justify-center overflow-hidden">
      {hasRealTrack ? (
        <VideoTrack trackRef={localTrack} className="w-full h-full object-cover" />
      ) : (
        <div className="flex items-center justify-center w-full h-full text-zinc-500 text-sm">
          Camera off
        </div>
      )}
    </div>
  );
}

// ── EndSessionButton ──────────────────────────────────────────────────────────

function EndSessionButton({ sessionId }: { sessionId: string }) {
  const room = useRoomContext();
  const router = useRouter();

  async function handleEnd() {
    await room.disconnect();
    router.push(`/practice/${sessionId}/assessment`);
  }

  return (
    <button
      onClick={handleEnd}
      className="px-5 py-2.5 rounded-lg bg-red-600 hover:bg-red-500 text-white text-sm font-medium transition-colors"
    >
      End Practice Session
    </button>
  );
}

// ── RoomNotificationHandler ───────────────────────────────────────────────────

interface RoomNotificationHandlerProps {
  sessionId: string;
  setAlertMessage: (msg: string) => void;
}

function RoomNotificationHandler({
  sessionId,
  setAlertMessage,
}: RoomNotificationHandlerProps) {
  const room = useRoomContext();
  const router = useRouter();

  useEffect(() => {
    function handleData(payload: Uint8Array) {
      let parsed: { type?: string; reason?: string };
      try {
        parsed = JSON.parse(new TextDecoder().decode(payload));
      } catch {
        return; // silently discard invalid JSON
      }

      if (parsed.type === "session_ended") {
        const reason = parsed.reason;
        if (reason === "silence_timeout") {
          setAlertMessage("The practice room closed due to prolonged silence.");
        } else if (reason === "disciplinary") {
          setAlertMessage(
            "Session terminated due to camera-off policy enforcement."
          );
        } else {
          setAlertMessage("The practice session has ended.");
        }
        room.disconnect();
      }
    }

    function handleDisconnected() {
      router.push(`/practice/${sessionId}/assessment`);
    }

    room.on(RoomEvent.DataReceived, handleData);
    room.on(RoomEvent.Disconnected, handleDisconnected);

    return () => {
      room.off(RoomEvent.DataReceived, handleData);
      room.off(RoomEvent.Disconnected, handleDisconnected);
    };
  }, [room, router, sessionId, setAlertMessage]);

  return null;
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function InterviewStudioPage({
  params,
}: {
  params: Promise<{ session_id: string }>;
}) {
  const { session_id } = use(params);
  const sessionId = session_id;
  const [livekitToken, setLivekitToken] = useState<string | null>(null);
  const [livekitUrl, setLivekitUrl] = useState<string | null>(null);
  const [alertMessage, setAlertMessage] = useState<string | null>(null);

  function handleReady(token: string, url: string) {
    setLivekitToken(token);
    setLivekitUrl(url);
  }

  if (!livekitToken || !livekitUrl) {
    return <MediaPreCheck sessionId={sessionId} onReady={handleReady} />;
  }

  return (
    <main className="min-h-screen bg-slate-900 flex flex-col">
      {/* Alert banner */}
      {alertMessage && (
        <div className="flex items-center justify-between gap-4 px-6 py-3 bg-amber-500/10 border-b border-amber-500/20">
          <p className="text-sm text-amber-300">{alertMessage}</p>
          <Link
            href="/dashboard"
            className="text-xs text-amber-400 underline underline-offset-2 shrink-0"
          >
            Back to Dashboard
          </Link>
        </div>
      )}

      <LiveKitRoom
        token={livekitToken}
        serverUrl={livekitUrl}
        audio={true}
        video={true}
        onError={(err) =>
          setAlertMessage(`Connection error: ${err.message}`)
        }
        className="flex flex-col flex-1"
      >
        <RoomAudioRenderer />
        <RoomNotificationHandler
          sessionId={sessionId}
          setAlertMessage={setAlertMessage}
        />

        {/* Studio layout */}
        <div className="flex flex-col flex-1 gap-6 p-6 md:p-8">
          {/* Header */}
          <div className="flex items-center justify-between w-full max-w-7xl mx-auto">
            <div>
              <h1 className="text-2xl font-semibold text-zinc-100">
                Practice Interview
              </h1>
              <p className="text-sm text-zinc-400">
                In progress
              </p>
            </div>
            <EndSessionButton sessionId={sessionId} />
          </div>

          {/* Two-screen split */}
          <div className="flex flex-col md:flex-row w-full max-w-7xl mx-auto flex-1 gap-6 min-h-[400px]">
            {/* Agent Screen */}
            <div className="flex-1 bg-slate-800 rounded-2xl border border-zinc-700 flex flex-col items-center justify-center relative overflow-hidden shadow-2xl">
              <div className="absolute top-4 left-4 text-xs font-medium bg-indigo-500/20 text-indigo-300 px-3 py-1.5 rounded-full border border-indigo-500/30">
                AI Interviewer
              </div>
              <div className="w-32 h-32 rounded-full bg-indigo-600/10 flex items-center justify-center ring-4 ring-indigo-500/20 mb-6 relative">
                <div className="absolute inset-0 rounded-full border border-indigo-400/30 animate-ping opacity-75"></div>
                <Bot size={48} className="text-indigo-400" />
              </div>
              <h2 className="text-lg font-medium text-zinc-200">Listening to you...</h2>
              <div className="flex items-center gap-1.5 mt-3">
                <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: '0ms' }}></div>
                <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: '150ms' }}></div>
                <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: '300ms' }}></div>
              </div>
            </div>

            {/* Candidate Screen */}
            <div className="flex-1 rounded-2xl border border-zinc-700 flex flex-col relative overflow-hidden shadow-2xl bg-black">
               <div className="absolute top-4 left-4 z-10 text-xs font-medium bg-black/60 text-zinc-200 px-3 py-1.5 rounded-full border border-zinc-700/50 backdrop-blur-md">
                 You
               </div>
               <LocalCameraPanel />
            </div>
          </div>
        </div>
      </LiveKitRoom>
    </main>
  );
}
