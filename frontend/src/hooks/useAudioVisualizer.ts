import { useEffect, useRef } from "react";
import type { VisualizerMode } from "../store/slices/playerSlice";
import type { Track } from "../types";

declare global {
  var webkitAudioContext: typeof AudioContext;
}


export function useAudioVisualizer(
  currentTrack: Track | null,
  isPlaying: boolean,
  audioRef: React.RefObject<HTMLAudioElement | null>,
  mode: VisualizerMode = "classic"
) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const sourceRef = useRef<MediaElementAudioSourceNode | null>(null);
  const animationFrameRef = useRef<number | undefined>(undefined);

  const barHeightsRef = useRef<number[]>([]);

  // Reusable arrays to avoid GC pressure
  const dataArrayRef = useRef<Uint8Array | null>(null);
  const timeDataRef = useRef<Uint8Array | null>(null);

  // Initialize Audio Context (once)
  useEffect(() => {
    if (!audioContextRef.current) {
      const AudioContextClass = globalThis.AudioContext || globalThis.webkitAudioContext;
      const ctx = new AudioContextClass();
      const analyser = ctx.createAnalyser();
      analyser.smoothingTimeConstant = 0.8;
      analyser.fftSize = 512;

      audioContextRef.current = ctx;
      analyserRef.current = analyser;
      console.log("Visualizer: AudioContext initialized.");
    }

    const connectAudio = () => {
      const audio = audioRef.current;
      if (!audio) return;

      // Ensure crossOrigin is set
      if (audio.crossOrigin !== "anonymous") {
        audio.crossOrigin = "anonymous";
      }

      if (!sourceRef.current && audioContextRef.current && analyserRef.current) {
        try {
          const source = audioContextRef.current.createMediaElementSource(audio);
          source.connect(analyserRef.current);
          analyserRef.current.connect(audioContextRef.current.destination);
          sourceRef.current = source;
          console.log("Visualizer: Source connected to element.");
        } catch (e) {
          const msg = e instanceof Error ? e.message : "";
          if (!msg.includes("connected")) {
            console.warn("Visualizer: Connection issue:", e);
          }
        }
      }
    };

    connectAudio();

    if (isPlaying && audioContextRef.current?.state === "suspended") {
      audioContextRef.current.resume().catch(console.error);
    }

    const resumeContext = () => {
      if (audioContextRef.current?.state === "suspended") {
        audioContextRef.current.resume();
      }
    };

    document.addEventListener("click", resumeContext);
    document.addEventListener("touchstart", resumeContext);

    return () => {
      document.removeEventListener("click", resumeContext);
      document.removeEventListener("touchstart", resumeContext);
    };
  }, [currentTrack, isPlaying, audioRef]);

  // Effect to handle mode changes and drawing loop
  useEffect(() => {
    if (!canvasRef.current || !analyserRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    analyserRef.current.fftSize = 512;

    const bufferLength = analyserRef.current.frequencyBinCount;
    dataArrayRef.current = new Uint8Array(bufferLength);
    timeDataRef.current = new Uint8Array(bufferLength);

    const getPrimaryColors = () => {
      const root = document.documentElement;
      const primaryHsl = getComputedStyle(root).getPropertyValue("--primary").trim();
      const hslValues = primaryHsl.replaceAll(",", " ").split(/\s+/).filter(Boolean);
      let [h, s, l] = ["250", "100%", "50%"];
      if (hslValues.length >= 3) [h, s, l] = hslValues;
      return {
        base: `hsl(${h}, ${s}, ${l})`,
        alpha: (a: number) => `hsla(${h}, ${s}, ${l}, ${a})`,
      };
    };

    const drawClassic = (data: Uint8Array) => {
      ctx.fillStyle = "rgba(0, 0, 0, 0.2)";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      const colors = getPrimaryColors();
      const numBars = 64;
      const barWidth = (canvas.width / numBars) * 0.8;
      const gap = (canvas.width / numBars) * 0.2;

      for (let i = 0; i < numBars; i++) {
        const index = Math.floor((i / numBars) * (data.length * 0.7));
        const percent = data[index] / 255;
        const height = percent * canvas.height * 0.6;
        if (!barHeightsRef.current[i]) barHeightsRef.current[i] = 0;
        barHeightsRef.current[i] += (height - barHeightsRef.current[i]) * 0.2;
        const x = i * (barWidth + gap) + gap / 2;
        const y = canvas.height - barHeightsRef.current[i];
        const gradient = ctx.createLinearGradient(x, y, x, canvas.height);
        gradient.addColorStop(0, colors.alpha(1));
        gradient.addColorStop(1, colors.alpha(0));
        ctx.fillStyle = gradient;
        ctx.fillRect(x, y, barWidth, barHeightsRef.current[i]);
        ctx.fillStyle = colors.alpha(0.5);
        ctx.fillRect(x, y - 4, barWidth, 2);
      }
    };

    const drawMirrorBars = (data: Uint8Array) => {
      ctx.fillStyle = "rgba(0, 0, 0, 0.2)";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      const colors = getPrimaryColors();
      const numBars = 64;
      const barWidth = (canvas.width / numBars) * 0.8;
      const gap = (canvas.width / numBars) * 0.2;
      const midY = canvas.height / 2;

      for (let i = 0; i < numBars; i++) {
        const index = Math.floor((i / numBars) * (data.length * 0.7));
        const percent = data[index] / 255;
        const halfHeight = percent * midY * 0.85;
        if (!barHeightsRef.current[i]) barHeightsRef.current[i] = 0;
        barHeightsRef.current[i] += (halfHeight - barHeightsRef.current[i]) * 0.2;
        const h = barHeightsRef.current[i];
        const x = i * (barWidth + gap) + gap / 2;

        const gradUp = ctx.createLinearGradient(x, midY - h, x, midY);
        gradUp.addColorStop(0, colors.alpha(1));
        gradUp.addColorStop(1, colors.alpha(0.15));
        ctx.fillStyle = gradUp;
        ctx.fillRect(x, midY - h, barWidth, h);

        const gradDown = ctx.createLinearGradient(x, midY, x, midY + h);
        gradDown.addColorStop(0, colors.alpha(0.15));
        gradDown.addColorStop(1, colors.alpha(1));
        ctx.fillStyle = gradDown;
        ctx.fillRect(x, midY, barWidth, h);

        ctx.fillStyle = colors.alpha(0.6);
        ctx.fillRect(x, midY - h - 3, barWidth, 2);
        ctx.fillRect(x, midY + h + 1, barWidth, 2);
      }
    };

    const drawSpectrumBars = (data: Uint8Array) => {
      ctx.fillStyle = "rgba(0, 0, 0, 0.2)";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      const numBars = 64;
      const barWidth = (canvas.width / numBars) * 0.8;
      const gap = (canvas.width / numBars) * 0.2;

      for (let i = 0; i < numBars; i++) {
        const index = Math.floor((i / numBars) * (data.length * 0.7));
        const percent = data[index] / 255;
        const height = percent * canvas.height * 0.6;
        if (!barHeightsRef.current[i]) barHeightsRef.current[i] = 0;
        barHeightsRef.current[i] += (height - barHeightsRef.current[i]) * 0.2;
        const h = barHeightsRef.current[i];
        const x = i * (barWidth + gap) + gap / 2;
        const hue = (i / numBars) * 280;

        const gradient = ctx.createLinearGradient(x, canvas.height - h, x, canvas.height);
        gradient.addColorStop(0, `hsla(${hue}, 100%, 65%, 1)`);
        gradient.addColorStop(1, `hsla(${hue}, 100%, 40%, 0.2)`);
        ctx.fillStyle = gradient;
        ctx.fillRect(x, canvas.height - h, barWidth, h);

        ctx.fillStyle = `hsla(${hue}, 100%, 80%, 0.7)`;
        ctx.fillRect(x, canvas.height - h - 4, barWidth, 2);
      }
    };

    const drawPulseRings = (data: Uint8Array) => {
      ctx.fillStyle = "rgba(0, 0, 0, 0.15)";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      const colors = getPrimaryColors();
      const cx = canvas.width / 2;
      const cy = canvas.height / 2;

      let bass = 0;
      for (let i = 0; i < 8; i++) bass += data[i];
      bass /= 8 * 255;

      let mid = 0;
      for (let i = 8; i < 48; i++) mid += data[i];
      mid /= 40 * 255;

      let treble = 0;
      for (let i = 48; i < data.length; i++) treble += data[i];
      treble /= (data.length - 48) * 255;

      const rings = [
        { band: bass, baseRadius: 0.18, color: colors.alpha },
        { band: mid, baseRadius: 0.3, color: colors.alpha },
        { band: treble, baseRadius: 0.42, color: colors.alpha },
        { band: (bass + mid) / 2, baseRadius: 0.54, color: colors.alpha },
      ];

      const maxR = Math.min(cx, cy);
      for (const ring of rings) {
        const r = maxR * (ring.baseRadius + ring.band * 0.12);
        const lineWidth = 2 + ring.band * 6;
        const alpha = 0.15 + ring.band * 0.75;

        const glow = ctx.createRadialGradient(cx, cy, r - lineWidth * 2, cx, cy, r + lineWidth * 2);
        glow.addColorStop(0, ring.color(0));
        glow.addColorStop(0.5, ring.color(alpha));
        glow.addColorStop(1, ring.color(0));

        ctx.beginPath();
        ctx.arc(cx, cy, r, 0, Math.PI * 2);
        ctx.lineWidth = lineWidth * 3;
        ctx.strokeStyle = glow;
        ctx.stroke();

        ctx.beginPath();
        ctx.arc(cx, cy, r, 0, Math.PI * 2);
        ctx.lineWidth = lineWidth * 0.5;
        ctx.strokeStyle = ring.color(Math.min(alpha * 1.5, 1));
        ctx.stroke();
      }
    };

    const drawGlow = (data: Uint8Array) => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      let sum = 0;
      for (let i = 0; i < data.length; i++) sum += data[i];
      const intensity = sum / data.length / 255;
      const colors = getPrimaryColors();
      const grad = ctx.createRadialGradient(
        canvas.width / 2,
        canvas.height / 2,
        0,
        canvas.width / 2,
        canvas.height / 2,
        canvas.width
      );
      grad.addColorStop(0, colors.alpha(intensity * 0.8));
      grad.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, canvas.width, canvas.height);
    };

    let debugCounter = 0;

    const render = () => {
      if (!analyserRef.current || !dataArrayRef.current) return;
      const data = dataArrayRef.current;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      analyserRef.current.getByteFrequencyData(data as any);

      // Debug logging every 100 frames
      if (debugCounter++ % 100 === 0) {
        const max = Math.max(...data);
        if (max === 0) console.log("Visualizer: Silence detected (all zeros)");
        else console.log("Visualizer: Signal detected, max amp:", max);
      }

      switch (mode) {
        case "mirror":
          drawMirrorBars(data);
          break;
        case "spectrum":
          drawSpectrumBars(data);
          break;
        case "pulse":
          drawPulseRings(data);
          break;
        case "glow":
          drawGlow(data);
          break;
        default:
          drawClassic(data);
      }

      animationFrameRef.current = requestAnimationFrame(render);
    };

    if (isPlaying && currentTrack) {
      render();
    } else {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }

    return () => {
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
    };
  }, [currentTrack, isPlaying, mode]);

  return canvasRef;
}
