import { render, screen, fireEvent, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import MediaPreCheck from "../components/MediaPreCheck";
import * as api from "../lib/api";

// Mock the api module
vi.mock("../lib/api", () => ({
  startSession: vi.fn(),
}));

const startSessionMock = vi.mocked(api.startSession);

// Stub navigator.mediaDevices globally (jsdom doesn't provide it)
const mockEnumerateDevices = vi.fn();
const mockGetUserMedia = vi.fn();

Object.defineProperty(globalThis.navigator, "mediaDevices", {
  value: { enumerateDevices: mockEnumerateDevices, getUserMedia: mockGetUserMedia },
  writable: true,
  configurable: true,
});

function makeMockStream() {
  const track = { stop: vi.fn() };
  return {
    getTracks: () => [track],
  } as unknown as MediaStream;
}

function makeAudioContextClass(avgAmplitude: number) {
  const dataArray = new Uint8Array(128).fill(avgAmplitude);
  const analyser = {
    fftSize: 256,
    frequencyBinCount: 128,
    getByteFrequencyData: vi.fn((arr: Uint8Array) => arr.set(dataArray)),
    connect: vi.fn(),
  };
  const source = { connect: vi.fn() };
  // Must be a class/constructor for vi.stubGlobal
  return class MockAudioContext {
    createMediaStreamSource() { return source; }
    createAnalyser() { return analyser; }
    close() {}
  };
}

describe("MediaPreCheck", () => {
  const onReady = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockEnumerateDevices.mockResolvedValue([
      { deviceId: "mic-1", kind: "audioinput", label: "Default Mic", groupId: "" } as MediaDeviceInfo,
    ]);
  });

  it("populates the device dropdown from enumerateDevices", async () => {
    mockGetUserMedia.mockResolvedValue(makeMockStream());
    vi.stubGlobal("AudioContext", makeAudioContextClass(0));

    await act(async () => {
      render(<MediaPreCheck sessionId="sess-1" onReady={onReady} />);
    });

    expect(screen.getByText("Default Mic")).toBeInTheDocument();
  });

  it("disables the button and shows error text on NotAllowedError", async () => {
    const err = new Error("denied");
    err.name = "NotAllowedError";
    mockGetUserMedia.mockRejectedValue(err);

    await act(async () => {
      render(<MediaPreCheck sessionId="sess-1" onReady={onReady} />);
    });

    await act(async () => {
      fireEvent.change(screen.getByRole("combobox"), { target: { value: "mic-1" } });
    });

    expect(screen.getByText(/microphone access was denied/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /enter practice booth/i })).toBeDisabled();
  });

  it("disables the button and shows error text on NotFoundError", async () => {
    const err = new Error("not found");
    err.name = "NotFoundError";
    mockGetUserMedia.mockRejectedValue(err);

    await act(async () => {
      render(<MediaPreCheck sessionId="sess-1" onReady={onReady} />);
    });

    await act(async () => {
      fireEvent.change(screen.getByRole("combobox"), { target: { value: "mic-1" } });
    });

    expect(screen.getByText(/no microphone found/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /enter practice booth/i })).toBeDisabled();
  });

  it("enables the button and calls startSession when mic is verified", async () => {
    vi.useFakeTimers();

    mockGetUserMedia.mockResolvedValue(makeMockStream());
    // Amplitude 50 > threshold 10 → verified on first interval tick
    vi.stubGlobal("AudioContext", makeAudioContextClass(50));

    startSessionMock.mockResolvedValue({
      livekit_token: "tok",
      livekit_url: "ws://lk",
      room_name: "room-1",
      status: "interviewing",
    });

    await act(async () => {
      render(<MediaPreCheck sessionId="sess-1" onReady={onReady} />);
    });

    // Trigger device selection to start sampling
    await act(async () => {
      fireEvent.change(screen.getByRole("combobox"), { target: { value: "mic-1" } });
    });

    // Advance fake timers so the 100ms interval fires
    await act(async () => {
      vi.advanceTimersByTime(200);
    });

    vi.useRealTimers();

    expect(screen.getByText(/microphone verified/i)).toBeInTheDocument();

    const button = screen.getByRole("button", { name: /enter practice booth/i });
    expect(button).not.toBeDisabled();

    await act(async () => {
      fireEvent.click(button);
    });

    expect(startSessionMock).toHaveBeenCalledWith("sess-1");
    expect(onReady).toHaveBeenCalledWith("tok", "ws://lk");
  });
});
