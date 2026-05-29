"use client";

import { render, screen, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { RoomEvent } from "livekit-client";

// ── Module-level mocks ────────────────────────────────────────────────────────

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    className,
  }: {
    href: string;
    children: React.ReactNode;
    className?: string;
  }) => (
    <a href={href} className={className}>
      {children}
    </a>
  ),
}));

// Shared mock room instance used across tests
const mockRoom = {
  on: vi.fn(),
  off: vi.fn(),
  disconnect: vi.fn(),
};

vi.mock("@livekit/components-react", () => ({
  LiveKitRoom: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="livekit-room">{children}</div>
  ),
  RoomAudioRenderer: () => <div data-testid="room-audio-renderer" />,
  useTracks: () => [],
  VideoTrack: () => <div data-testid="video-track" />,
  useRoomContext: () => mockRoom,
}));

vi.mock("../components/MediaPreCheck", () => ({
  default: ({
    onReady,
  }: {
    sessionId: string;
    onReady: (token: string, url: string) => void;
  }) => (
    <div data-testid="media-pre-check">
      <button onClick={() => onReady("test-token", "ws://lk")}>
        Enter Practice Booth
      </button>
    </div>
  ),
}));

// Import after mocks are registered
import InterviewStudioPage from "../app/interview/[session_id]/page";

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("InterviewStudioPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders MediaPreCheck before token is set", async () => {
    await act(async () => {
      render(<InterviewStudioPage params={{ session_id: "sess-1" }} />);
    });

    expect(screen.getByTestId("media-pre-check")).toBeInTheDocument();
    expect(screen.queryByTestId("livekit-room")).not.toBeInTheDocument();
  });

  it("renders LiveKitRoom after token is set via onReady", async () => {
    await act(async () => {
      render(<InterviewStudioPage params={{ session_id: "sess-1" }} />);
    });

    await act(async () => {
      screen.getByText("Enter Practice Booth").click();
    });

    expect(screen.queryByTestId("media-pre-check")).not.toBeInTheDocument();
    expect(screen.getByTestId("livekit-room")).toBeInTheDocument();
  });
});

// ── RoomNotificationHandler tests ─────────────────────────────────────────────

describe("RoomNotificationHandler — DataReceived handler", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  /**
   * Helper: render the page with a token already set so RoomNotificationHandler
   * mounts, then extract the DataReceived handler registered on the mock room.
   */
  async function renderWithRoom() {
    await act(async () => {
      render(<InterviewStudioPage params={{ session_id: "sess-42" }} />);
    });

    // Transition past MediaPreCheck
    await act(async () => {
      screen.getByText("Enter Practice Booth").click();
    });

    // Find the DataReceived handler registered via room.on(...)
    const dataReceivedCall = mockRoom.on.mock.calls.find(
      ([event]) => event === RoomEvent.DataReceived
    );
    expect(dataReceivedCall).toBeDefined();
    return dataReceivedCall![1] as (payload: Uint8Array) => void;
  }

  function encode(obj: object): Uint8Array {
    return new TextEncoder().encode(JSON.stringify(obj));
  }

  it("sets silence_timeout alert message for matching watchdog signal", async () => {
    await renderWithRoom();

    // Trigger the handler directly via the mock room's registered callback
    const handler = mockRoom.on.mock.calls.find(
      ([event]) => event === RoomEvent.DataReceived
    )![1] as (payload: Uint8Array) => void;

    await act(async () => {
      handler(encode({ type: "session_ended", reason: "silence_timeout" }));
    });

    expect(
      screen.getByText(
        "The practice room closed due to prolonged silence."
      )
    ).toBeInTheDocument();
  });

  it("sets disciplinary alert message for matching watchdog signal", async () => {
    await renderWithRoom();

    const handler = mockRoom.on.mock.calls.find(
      ([event]) => event === RoomEvent.DataReceived
    )![1] as (payload: Uint8Array) => void;

    await act(async () => {
      handler(encode({ type: "session_ended", reason: "disciplinary" }));
    });

    expect(
      screen.getByText(
        "Session terminated due to camera-off policy enforcement."
      )
    ).toBeInTheDocument();
  });

  it("silently discards invalid JSON without throwing", async () => {
    await renderWithRoom();

    const handler = mockRoom.on.mock.calls.find(
      ([event]) => event === RoomEvent.DataReceived
    )![1] as (payload: Uint8Array) => void;

    // Should not throw
    await act(async () => {
      handler(new TextEncoder().encode("not-valid-json{{{"));
    });

    // No alert banner should appear
    expect(screen.queryByText(/practice room closed/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/camera-off/i)).not.toBeInTheDocument();
  });

  it("calls room.disconnect() after a session_ended signal", async () => {
    await renderWithRoom();

    const handler = mockRoom.on.mock.calls.find(
      ([event]) => event === RoomEvent.DataReceived
    )![1] as (payload: Uint8Array) => void;

    await act(async () => {
      handler(encode({ type: "session_ended", reason: "silence_timeout" }));
    });

    expect(mockRoom.disconnect).toHaveBeenCalled();
  });
});
