import { useRef, useEffect } from "react";
import type { Track } from "../types";

declare global {
  var webkitAudioContext: typeof AudioContext;
}

/**
 * Modern audio equalizer visualizer with smooth animated bars.
 * Bars react to different frequency bands (bass, mids, highs).
 * Uses CSS primary color from the current theme.
 */
export function useAudioVisualizer(
  currentTrack: Track | null,
  isPlaying: boolean
) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const sourceRef = useRef<MediaElementAudioSourceNode | null>(null);
  const animationFrameRef = useRef<number | undefined>(undefined);
  const barHeightsRef = useRef<number[]>([]);

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
      analyserRef.current.fftSize = 128; // 64 frequency bins
      analyserRef.current.smoothingTimeConstant = 0.75;
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

    // Get primary color from CSS variable and build proper HSLA colors
    const getPrimaryColors = () => {
      const root = document.documentElement;
      const primaryHsl = getComputedStyle(root).getPropertyValue("--primary").trim();
      
      // CSS variable format might be "190 90% 50%" or "190, 90%, 50%"
      // We need to convert to proper hsla() format
      const hslValues = primaryHsl.replaceAll(",", " ").split(/\s+/).filter(Boolean);
      
      if (hslValues.length >= 3) {
        const [h, s, l] = hslValues;
        return {
          solid: `hsl(${h}, ${s}, ${l})`,
          bright: `hsla(${h}, ${s}, ${l}, 1)`,
          medium: `hsla(${h}, ${s}, ${l}, 0.7)`,
          dim: `hsla(${h}, ${s}, ${l}, 0.3)`,
          glow: `hsla(${h}, ${s}, ${l}, 0.5)`,
        };
      }
      
      // Fallback to orange if parsing fails
      return {
        solid: "hsl(25, 95%, 53%)",
        bright: "hsla(25, 95%, 53%, 1)",
        medium: "hsla(25, 95%, 53%, 0.7)",
        dim: "hsla(25, 95%, 53%, 0.3)",
        glow: "hsla(25, 95%, 53%, 0.5)",
      };
    };

    const NUM_BARS = 48;
    const BAR_GAP = 4;
    
    // Initialize bar heights if not set
    if (barHeightsRef.current.length !== NUM_BARS) {
      barHeightsRef.current = new Array(NUM_BARS).fill(0);
    }

    const draw = () => {
      if (!ctx || !analyserRef.current) return;

      const bufferLength = analyserRef.current.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);
      analyserRef.current.getByteFrequencyData(dataArray);

      // Clear with transparency for subtle trails
      ctx.fillStyle = "rgba(0, 0, 0, 0.15)";
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      const colors = getPrimaryColors();
      const barWidth = (canvas.width - (NUM_BARS - 1) * BAR_GAP) / NUM_BARS;
      const maxBarHeight = canvas.height * 0.7;

      // Distribute frequency data across bars (more bass, less highs)
      for (let i = 0; i < NUM_BARS; i++) {
        // Map bar index to frequency bin with logarithmic scaling
        const freqIndex = Math.floor(Math.pow(i / NUM_BARS, 1.5) * bufferLength);
        const value = dataArray[Math.min(freqIndex, bufferLength - 1)] / 255;
        
        // Target height with some amplification for visual impact
        const targetHeight = value * maxBarHeight * (1 + (1 - i / NUM_BARS) * 0.5);
        
        // Smooth interpolation for falling effect
        const currentHeight = barHeightsRef.current[i];
        const newHeight = targetHeight > currentHeight 
          ? targetHeight // Rise quickly
          : currentHeight * 0.92; // Fall smoothly
        
        barHeightsRef.current[i] = newHeight;

        const x = i * (barWidth + BAR_GAP);
        const barHeight = Math.max(newHeight, 3); // Minimum height
        const y = (canvas.height - barHeight) / 2; // Center vertically

        // Create gradient for each bar
        const gradient = ctx.createLinearGradient(x, y, x, y + barHeight);
        const intensity = barHeight / maxBarHeight;
        
        if (intensity > 0.7) {
          // High intensity - brightest
          gradient.addColorStop(0, colors.bright);
          gradient.addColorStop(0.5, colors.solid);
          gradient.addColorStop(1, colors.medium);
        } else if (intensity > 0.3) {
          // Medium intensity
          gradient.addColorStop(0, colors.solid);
          gradient.addColorStop(0.5, colors.medium);
          gradient.addColorStop(1, colors.dim);
        } else {
          // Low intensity
          gradient.addColorStop(0, colors.medium);
          gradient.addColorStop(1, colors.dim);
        }

        // Draw glow effect for high bars
        if (intensity > 0.5) {
          ctx.save();
          ctx.shadowColor = colors.glow;
          ctx.shadowBlur = 15 * intensity;
          ctx.fillStyle = gradient;
          ctx.beginPath();
          ctx.roundRect(x, y, barWidth, barHeight, barWidth / 3);
          ctx.fill();
          ctx.restore();
        }

        // Draw bar with rounded corners
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.roundRect(x, y, barWidth, barHeight, barWidth / 3);
        ctx.fill();

        // Add highlight on top of bar
        if (barHeight > 10) {
          ctx.fillStyle = `rgba(255, 255, 255, ${0.1 + intensity * 0.2})`;
          ctx.beginPath();
          ctx.roundRect(x + 1, y + 1, barWidth - 2, barHeight * 0.3, barWidth / 4);
          ctx.fill();
        }
      }

      // Add mirror reflection at bottom (subtle)
      ctx.save();
      ctx.globalAlpha = 0.15;
      ctx.scale(1, -0.3);
      ctx.translate(0, -canvas.height * 4);
      
      for (let i = 0; i < NUM_BARS; i++) {
        const barHeight = barHeightsRef.current[i];
        if (barHeight < 5) continue;
        
        const x = i * (barWidth + BAR_GAP);
        const y = (canvas.height - barHeight) / 2;
        
        ctx.fillStyle = colors.dim;
        ctx.beginPath();
        ctx.roundRect(x, y, barWidth, barHeight, barWidth / 3);
        ctx.fill();
      }
      ctx.restore();

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
      // Animate bars down when paused
      const fadeOut = () => {
        let stillAnimating = false;
        for (let i = 0; i < barHeightsRef.current.length; i++) {
          if (barHeightsRef.current[i] > 0.5) {
            barHeightsRef.current[i] *= 0.9;
            stillAnimating = true;
          } else {
            barHeightsRef.current[i] = 0;
          }
        }
        
        ctx.fillStyle = "rgba(0, 0, 0, 0.2)";
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        if (stillAnimating) {
          animationFrameRef.current = requestAnimationFrame(fadeOut);
        }
      };
      fadeOut();
    }

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [currentTrack, isPlaying]);

  return canvasRef;
}
