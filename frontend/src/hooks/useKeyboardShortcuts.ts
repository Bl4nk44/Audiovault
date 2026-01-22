import { useCallback } from "react";
import { useHotkeys } from "react-hotkeys-hook";
import { useStore } from "../store/useStore";

/**
 * Global keyboard shortcuts for the audio player.
 *
 * Shortcuts:
 * - Space: Play/Pause
 * - ArrowRight: Next track
 * - ArrowLeft: Previous track
 * - ArrowUp / +: Volume up (10%)
 * - ArrowDown / -: Volume down (10%)
 * - M: Mute/Unmute
 */
export function useKeyboardShortcuts() {
  const { togglePlay, nextTrack, prevTrack, volume, setVolume, currentTrack } = useStore();

  const adjustVolume = useCallback(
    (delta: number) => {
      const newVolume = Math.max(0, Math.min(1, volume + delta));
      setVolume(newVolume);
    },
    [volume, setVolume]
  );

  // Play/Pause - Space (prevent scrolling)
  useHotkeys(
    "space",
    (e) => {
      e.preventDefault();
      if (currentTrack) {
        togglePlay();
      }
    },
    { enableOnFormTags: false }
  );

  // Next track - Arrow Right
  useHotkeys(
    "right",
    (e) => {
      e.preventDefault();
      nextTrack();
    },
    { enableOnFormTags: false }
  );

  // Previous track - Arrow Left
  useHotkeys(
    "left",
    (e) => {
      e.preventDefault();
      prevTrack();
    },
    { enableOnFormTags: false }
  );

  // Volume up - Arrow Up or +
  useHotkeys(
    "up, shift+=, =",
    (e) => {
      e.preventDefault();
      adjustVolume(0.1);
    },
    { enableOnFormTags: false }
  );

  // Volume down - Arrow Down or -
  useHotkeys(
    "down, -",
    (e) => {
      e.preventDefault();
      adjustVolume(-0.1);
    },
    { enableOnFormTags: false }
  );

  // Mute toggle - M
  useHotkeys(
    "m",
    (e) => {
      e.preventDefault();
      setVolume(volume > 0 ? 0 : 1);
    },
    { enableOnFormTags: false }
  );
}
