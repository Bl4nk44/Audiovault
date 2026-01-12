import { useRef, useEffect } from "react";
import type { Track } from "../types";

declare global {
  var webkitAudioContext: typeof AudioContext;
}

export function useAudioVisualizer(
  currentTrack: Track | null,
  isPlaying: boolean
) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const sourceRef = useRef<MediaElementAudioSourceNode | null>(null);
  const animationFrameRef = useRef<number | undefined>(undefined);

  useEffect(() => {
    if (!canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Initialize Audio Context
    if (!audioContextRef.current) {
      const AudioContextClass =
        globalThis.AudioContext || globalThis.webkitAudioContext;
      audioContextRef.current = new AudioContextClass();
      analyserRef.current = audioContextRef.current.createAnalyser();
      analyserRef.current.fftSize = 256;
    }

    // Connect to audio element
    const audio = document.querySelector("audio");
    if (audio && !sourceRef.current && audioContextRef.current && analyserRef.current) {
      try {
        sourceRef.current =
          audioContextRef.current.createMediaElementSource(audio);
        sourceRef.current.connect(analyserRef.current);
        analyserRef.current.connect(audioContextRef.current.destination);
      } catch (e) {
        console.error("Audio source already connected", e);
      }
    }

    const draw = () => {
      if (!ctx || !analyserRef.current) return;

      const bufferLength = analyserRef.current.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);

      analyserRef.current.getByteFrequencyData(dataArray);

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const barWidth = (canvas.width / bufferLength) * 2.5;
      let barHeight;
      let x = 0;

      for (let i = 0; i < bufferLength; i++) {
        barHeight = (dataArray[i] / 255) * canvas.height;

        const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
        // Use primary color (orange-500 equivalent)
        gradient.addColorStop(0, "rgba(249, 115, 22, 1)");
        gradient.addColorStop(1, "rgba(249, 115, 22, 0.2)");

        ctx.fillStyle = gradient;
        // Rounded top bars
        ctx.beginPath();
        ctx.roundRect(x, canvas.height - barHeight, barWidth, barHeight, [
          4, 4, 0, 0,
        ]);
        ctx.fill();

        x += barWidth + 1;
      }

      animationFrameRef.current = requestAnimationFrame(draw);
    };

    if (isPlaying && currentTrack) {
      if (audioContextRef.current?.state === "suspended") {
        audioContextRef.current.resume();
      }
      draw();
    } else {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [currentTrack, isPlaying]);

  return canvasRef;
}
