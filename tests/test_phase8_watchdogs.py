"""
Unit tests for Phase 8 silence watchdog — Requirements 2.1, 3.1, 3.2, 3.4.

Strategy: patch asyncio.sleep with a coroutine that yields once via
asyncio.sleep(0) called on the *real* sleep before patching, avoiding
recursion. We control loop.time() via side_effect to simulate time passing.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent import run_silence_watchdog


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_agent():
    agent = MagicMock()
    agent.say = AsyncMock()
    agent.interrupt = AsyncMock()
    return agent


def _make_ctx():
    ctx = MagicMock()
    ctx.room = MagicMock()
    ctx.room.disconnect = AsyncMock()
    return ctx


# A coroutine that yields control once without recursing into the patched sleep.
# We capture the real asyncio.sleep before any patching happens.
_real_sleep = asyncio.sleep


async def _noop_sleep(*_args, **_kwargs):
    """Yield control once using the real asyncio.sleep(0)."""
    await _real_sleep(0)


# ---------------------------------------------------------------------------
# Test: warning fires at 60 s threshold (Requirement 2.1)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_warning_fires_at_60s():
    """Silence watchdog must call agent.say() with a warning when elapsed >= 60 s."""
    loop = asyncio.get_event_loop()
    # Set last_speech far enough in the past that elapsed > 60 s immediately
    now = loop.time()
    session_state = {
        "last_candidate_speech_time": now - 65.0,
        "camera_mute_count": 0,
        "is_camera_active": True,
        "silence_paused": False,
        "end_reason": "",
    }
    agent = _make_agent()
    ctx = _make_ctx()

    say_calls = []

    async def fake_say(text):
        say_calls.append(text)
        # After warning, simulate candidate speaking so watchdog resets and loops
        session_state["last_candidate_speech_time"] = loop.time()

    agent.say = fake_say

    with patch("asyncio.sleep", side_effect=_noop_sleep):
        task = asyncio.create_task(
            run_silence_watchdog(agent, ctx, session_state, "Alice")
        )
        # Let the watchdog run through warning + grace reset, then cancel
        for _ in range(15):
            await _real_sleep(0)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    assert len(say_calls) >= 1, "Warning should have been delivered"


# ---------------------------------------------------------------------------
# Test: disconnect called after grace window expiry (Requirement 3.1)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_disconnect_after_grace_window_expiry():
    """ctx.room.disconnect() must be called when grace window expires without speech."""
    # Sequence drives the watchdog through:
    #   monitoring poll → elapsed 65 s → warning
    #   grace_start captured
    #   grace poll 1 → grace_elapsed 5 s (not expired)
    #   grace poll 2 → grace_elapsed 35 s (expired → terminate)
    time_seq = iter([
        1065.0,  # monitoring: elapsed check
        1065.0,  # grace_start
        1065.0,  # speech_time_at_warning snapshot
        1070.0,  # grace poll 1: grace_elapsed = 5 s
        1100.0,  # grace poll 2: grace_elapsed = 35 s → expired
    ])

    def fake_time():
        try:
            return next(time_seq)
        except StopIteration:
            return 1200.0

    session_state = {
        "last_candidate_speech_time": 1000.0,
        "camera_mute_count": 0,
        "is_camera_active": True,
        "silence_paused": False,
        "end_reason": "",
    }
    agent = _make_agent()
    ctx = _make_ctx()

    loop = asyncio.get_event_loop()
    with patch.object(loop, "time", side_effect=fake_time):
        with patch("asyncio.sleep", side_effect=_noop_sleep):
            await run_silence_watchdog(agent, ctx, session_state, "Bob")

    ctx.room.disconnect.assert_awaited_once()
    assert session_state["end_reason"] == "silence_timeout"


# ---------------------------------------------------------------------------
# Test: timer resets when candidate speaks during grace window (Requirement 3.2)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_timer_resets_on_speech_during_grace_window():
    """When candidate speaks during grace window, watchdog resets and does NOT disconnect."""
    call_index = 0
    time_sequence = [
        1065.0,  # monitoring poll — elapsed 65 s → warning
        1065.0,  # grace_start
        1065.0,  # speech_time_at_warning snapshot
        1070.0,  # grace poll 1 — grace_elapsed = 5 s, candidate spoke → reset
        1070.0,  # monitoring poll after reset — elapsed ~4 s → no action
        1070.0,
        1070.0,
        1070.0,
    ]

    def fake_time():
        nonlocal call_index
        val = time_sequence[min(call_index, len(time_sequence) - 1)]
        call_index += 1
        return val

    session_state = {
        "last_candidate_speech_time": 1000.0,
        "camera_mute_count": 0,
        "is_camera_active": True,
        "silence_paused": False,
        "end_reason": "",
    }
    agent = _make_agent()
    ctx = _make_ctx()

    say_calls = []

    async def fake_say(text):
        say_calls.append(text)
        if len(say_calls) == 1:
            # Simulate candidate speaking during grace window
            session_state["last_candidate_speech_time"] = 1066.0

    agent.say = fake_say

    loop = asyncio.get_event_loop()
    with patch.object(loop, "time", side_effect=fake_time):
        with patch("asyncio.sleep", side_effect=_noop_sleep):
            task = asyncio.create_task(
                run_silence_watchdog(agent, ctx, session_state, "Carol")
            )
            for _ in range(20):
                await _real_sleep(0)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    # Warning was delivered
    assert len(say_calls) >= 1
    # Disconnect was NOT called
    ctx.room.disconnect.assert_not_awaited()
    assert session_state["end_reason"] != "silence_timeout"


# ---------------------------------------------------------------------------
# Test: silence_paused flag prevents elapsed advancement (Requirement 3.4)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_silence_paused_prevents_warning():
    """When silence_paused is True, the watchdog must not fire the warning."""
    session_state = {
        "last_candidate_speech_time": 0.0,   # very old — would normally trigger
        "camera_mute_count": 0,
        "is_camera_active": False,
        "silence_paused": True,              # paused by camera monitor
        "end_reason": "",
    }
    agent = _make_agent()
    ctx = _make_ctx()

    loop = asyncio.get_event_loop()
    # loop.time() returns a large value so elapsed would be huge if not paused
    with patch.object(loop, "time", return_value=9999.0):
        with patch("asyncio.sleep", side_effect=_noop_sleep):
            task = asyncio.create_task(
                run_silence_watchdog(agent, ctx, session_state, "Dave")
            )
            for _ in range(10):
                await _real_sleep(0)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    agent.say.assert_not_awaited()
    ctx.room.disconnect.assert_not_awaited()


# ===========================================================================
# Camera monitor tests — Requirements 4.1, 5.4, 5.5
# ===========================================================================

from agent import run_camera_monitor


def _make_session_state():
    return {
        "last_candidate_speech_time": 0.0,
        "camera_mute_count": 0,
        "is_camera_active": True,
        "silence_paused": False,
        "end_reason": "",
    }


def _make_track_event(kind="video"):
    """Return a mock event whose .track.kind matches the given kind."""
    track = MagicMock()
    track.kind = kind
    event = MagicMock()
    event.track = track
    return event


# ---------------------------------------------------------------------------
# Helper: capture event listeners registered on ctx.room
# ---------------------------------------------------------------------------

def _make_ctx_with_listeners():
    """Return (ctx, listeners_dict) where listeners_dict maps event_name → handler."""
    listeners = {}
    ctx = MagicMock()
    ctx.room = MagicMock()
    ctx.room.disconnect = AsyncMock()

    def _on(event_name, handler):
        listeners[event_name] = handler

    ctx.room.on = _on
    return ctx, listeners


# ---------------------------------------------------------------------------
# Test: track_muted fires agent.interrupt() and sets silence_paused (Req 4.1, 4.2)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_camera_mute_calls_interrupt_and_pauses_silence():
    """On track_muted, agent.interrupt() must be called and silence_paused set True."""
    session_state = _make_session_state()
    agent = _make_agent()
    ctx, listeners = _make_ctx_with_listeners()

    task = asyncio.create_task(
        run_camera_monitor(agent, ctx, session_state, "Eve")
    )
    # Let the monitor register its listeners
    await _real_sleep(0)

    # Fire the mute event
    listeners["track_muted"](_make_track_event("video"))
    await _real_sleep(0)

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    agent.interrupt.assert_awaited_once()
    assert session_state["silence_paused"] is True
    assert session_state["camera_mute_count"] == 1


# ---------------------------------------------------------------------------
# Test: 5th cumulative mute sets end_reason = "disciplinary" (Req 5.5)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fifth_mute_terminates_with_disciplinary():
    """Camera mute count reaching 5 must set end_reason = 'disciplinary'."""
    session_state = _make_session_state()
    session_state["camera_mute_count"] = 4   # already at 4; next mute is the 5th
    agent = _make_agent()
    ctx, listeners = _make_ctx_with_listeners()

    task = asyncio.create_task(
        run_camera_monitor(agent, ctx, session_state, "Frank")
    )
    await _real_sleep(0)

    listeners["track_muted"](_make_track_event("video"))
    # Allow ensure_future coroutines to run
    for _ in range(5):
        await _real_sleep(0)

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert session_state["end_reason"] == "disciplinary"
    ctx.room.disconnect.assert_awaited()


# ---------------------------------------------------------------------------
# Test: escalation warnings fire at correct cumulative intervals (Req 5.1-5.3)
# and end_reason = "disciplinary" set when Warning 3 expires (Req 5.4)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_escalation_sequence_terminates_after_warning3():
    """Full escalation (15s+20s+5s) must end with end_reason = 'disciplinary'."""
    session_state = _make_session_state()
    agent = _make_agent()
    ctx, listeners = _make_ctx_with_listeners()

    say_calls = []

    async def fake_say(text):
        say_calls.append(text)

    agent.say = fake_say

    sleep_calls = []

    async def fake_sleep(seconds):
        sleep_calls.append(seconds)
        await _real_sleep(0)

    task = asyncio.create_task(
        run_camera_monitor(agent, ctx, session_state, "Grace")
    )
    await _real_sleep(0)

    with patch("asyncio.sleep", side_effect=fake_sleep):
        listeners["track_muted"](_make_track_event("video"))
        # Drive the escalation coroutine through all its sleeps
        for _ in range(30):
            await _real_sleep(0)

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Three warnings must have been delivered
    assert len(say_calls) == 3, f"Expected 3 warnings, got {len(say_calls)}: {say_calls}"
    # Sleep intervals: 15, 20, 5, 1 (post-warning-3 check)
    assert 15 in sleep_calls
    assert 20 in sleep_calls
    assert 5 in sleep_calls
    assert session_state["end_reason"] == "disciplinary"
    ctx.room.disconnect.assert_awaited()


# ---------------------------------------------------------------------------
# Test: unmute cancels escalation and resumes silence watchdog (Req 4.4)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unmute_cancels_escalation_and_resumes_silence():
    """track_unmuted must cancel the escalation and set silence_paused = False."""
    session_state = _make_session_state()
    agent = _make_agent()
    ctx, listeners = _make_ctx_with_listeners()

    say_calls = []

    async def fake_say(text):
        say_calls.append(text)

    agent.say = fake_say

    async def slow_sleep(seconds):
        # Simulate a long sleep so unmute can fire before Warning 1
        if seconds == 15:
            await _real_sleep(0.05)
        else:
            await _real_sleep(0)

    task = asyncio.create_task(
        run_camera_monitor(agent, ctx, session_state, "Hank")
    )
    await _real_sleep(0)

    with patch("asyncio.sleep", side_effect=slow_sleep):
        listeners["track_muted"](_make_track_event("video"))
        await _real_sleep(0)
        # Unmute before the 15 s Warning 1 fires
        listeners["track_unmuted"](_make_track_event("video"))
        for _ in range(10):
            await _real_sleep(0)

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert session_state["silence_paused"] is False
    assert session_state["is_camera_active"] is True
    # No warnings should have been delivered (escalation was cancelled)
    assert len(say_calls) == 0
    ctx.room.disconnect.assert_not_awaited()


# ---------------------------------------------------------------------------
# Test: non-video track events are ignored (filter guard)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_non_video_track_ignored():
    """Mute events for audio tracks must not affect session_state."""
    session_state = _make_session_state()
    agent = _make_agent()
    ctx, listeners = _make_ctx_with_listeners()

    task = asyncio.create_task(
        run_camera_monitor(agent, ctx, session_state, "Iris")
    )
    await _real_sleep(0)

    listeners["track_muted"](_make_track_event("audio"))
    await _real_sleep(0)

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert session_state["camera_mute_count"] == 0
    assert session_state["silence_paused"] is False
    agent.interrupt.assert_not_awaited()


# ===========================================================================
# Dropout monitor tests — Requirements 6.1, 6.3, 6.4
# ===========================================================================

from agent import run_dropout_monitor


def _make_ctx_with_dropout_listeners():
    """Return (ctx, listeners_dict) capturing all room event registrations."""
    listeners = {}
    ctx = MagicMock()
    ctx.room = MagicMock()
    ctx.room.disconnect = AsyncMock()

    def _on(event_name, handler):
        listeners[event_name] = handler

    ctx.room.on = _on
    return ctx, listeners


# ---------------------------------------------------------------------------
# Test: disconnect event pauses timers (Requirement 6.1)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dropout_disconnect_pauses_timers():
    """participant_disconnected must set silence_paused = True."""
    session_state = {
        "last_candidate_speech_time": 0.0,
        "camera_mute_count": 0,
        "is_camera_active": True,
        "silence_paused": False,
        "end_reason": "",
    }
    ctx, listeners = _make_ctx_with_dropout_listeners()
    agent = _make_agent()

    task = asyncio.create_task(run_dropout_monitor(agent, ctx, session_state))
    await _real_sleep(0)

    # Fire disconnect event
    listeners["participant_disconnected"](MagicMock())
    await _real_sleep(0)

    assert session_state["silence_paused"] is True

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


# ---------------------------------------------------------------------------
# Test: reconnect within window resumes timers (Requirement 6.3)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dropout_reconnect_within_window_resumes_timers():
    """Reconnecting within 60 s must set silence_paused = False."""
    session_state = {
        "last_candidate_speech_time": 0.0,
        "camera_mute_count": 0,
        "is_camera_active": True,
        "silence_paused": False,
        "end_reason": "",
    }
    ctx, listeners = _make_ctx_with_dropout_listeners()
    agent = _make_agent()

    task = asyncio.create_task(run_dropout_monitor(agent, ctx, session_state))
    await _real_sleep(0)

    # Disconnect then quickly reconnect
    listeners["participant_disconnected"](MagicMock())
    await _real_sleep(0)
    assert session_state["silence_paused"] is True

    listeners["participant_connected"](MagicMock())
    # Allow the _reconnect_window coroutine to detect the event and resume
    for _ in range(10):
        await _real_sleep(0)

    assert session_state["silence_paused"] is False
    assert session_state["end_reason"] == ""
    ctx.room.disconnect.assert_not_awaited()

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


# ---------------------------------------------------------------------------
# Test: 60 s timeout without reconnect terminates with candidate_leave (Req 6.4)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dropout_timeout_terminates_with_candidate_leave():
    """60-second reconnection window expiry must set end_reason = 'candidate_leave'."""
    session_state = {
        "last_candidate_speech_time": 0.0,
        "camera_mute_count": 0,
        "is_camera_active": True,
        "silence_paused": False,
        "end_reason": "",
    }
    ctx, listeners = _make_ctx_with_dropout_listeners()
    agent = _make_agent()

    # Patch asyncio.wait_for to raise TimeoutError immediately
    async def fake_wait_for(coro, timeout):
        coro.close()  # clean up the coroutine without running it
        raise asyncio.TimeoutError()

    task = asyncio.create_task(run_dropout_monitor(agent, ctx, session_state))
    await _real_sleep(0)

    with patch("asyncio.wait_for", side_effect=fake_wait_for):
        listeners["participant_disconnected"](MagicMock())
        # Allow the _reconnect_window coroutine to run through the timeout path
        for _ in range(10):
            await _real_sleep(0)

    assert session_state["end_reason"] == "candidate_leave"
    ctx.room.disconnect.assert_awaited()

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


# ===========================================================================
# Integration test: concurrent termination race — Requirement 1.2
# ===========================================================================


@pytest.mark.asyncio
async def test_first_writer_wins_concurrent_termination():
    """Only the first end_reason written is preserved when two watchdogs race to terminate."""
    session_state = {
        "last_candidate_speech_time": 0.0,
        "camera_mute_count": 0,
        "is_camera_active": True,
        "silence_paused": False,
        "end_reason": "",
    }

    ctx = MagicMock()
    ctx.room = MagicMock()
    ctx.room.disconnect = AsyncMock()

    async def _watchdog_a():
        """Simulates silence watchdog terminating first."""
        await _real_sleep(0)
        if session_state["end_reason"] == "":
            session_state["end_reason"] = "silence_timeout"
        try:
            await ctx.room.disconnect()
        except Exception:
            pass

    async def _watchdog_b():
        """Simulates camera monitor terminating slightly after."""
        await _real_sleep(0)
        await _real_sleep(0)  # one extra yield — arrives second
        if session_state["end_reason"] == "":
            session_state["end_reason"] = "disciplinary"
        try:
            await ctx.room.disconnect()
        except Exception:
            pass

    task_a = asyncio.create_task(_watchdog_a())
    task_b = asyncio.create_task(_watchdog_b())
    await asyncio.gather(task_a, task_b, return_exceptions=True)

    # First writer (silence_timeout) must win; disciplinary must not overwrite it
    assert session_state["end_reason"] == "silence_timeout"
