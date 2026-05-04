import { useEffect, useRef } from "react";
import type { VisualizerMode } from "../store/slices/playerSlice";
import type { Track } from "../types";

declare global {
  var webkitAudioContext: typeof AudioContext;
}

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  color: string;
  life: number;
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

  // State refs for specific modes
  const barHeightsRef = useRef<number[]>([]);
  const particlesRef = useRef<Particle[]>([]);
  const rotationRef = useRef(0);

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

    // Adjust FFT size based on mode
    if (mode === "wave") {
      analyserRef.current.fftSize = 2048;
    } else {
      analyserRef.current.fftSize = 512;
    }

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

    const drawWave = (data: Uint8Array) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      analyserRef.current!.getByteTimeDomainData(data as any);
      ctx.fillStyle = "rgba(0, 0, 0, 0.2)";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      const colors = getPrimaryColors();
      ctx.lineWidth = 3;
      ctx.strokeStyle = colors.alpha(0.8);
      ctx.beginPath();
      const sliceWidth = canvas.width / data.length;
      let x = 0;
      for (let i = 0; i < data.length; i++) {
        const v = data[i] / 128;
        const y = (v * canvas.height) / 2;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
        x += sliceWidth;
      }
      ctx.stroke();
    };

    const drawCircle = (data: Uint8Array) => {
      ctx.fillStyle = "rgba(0, 0, 0, 0.2)";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      const colors = getPrimaryColors();
      const centerX = canvas.width / 2;
      const centerY = canvas.height / 2;
      const radius = Math.min(centerX, centerY) * 0.4;
      const numBars = 60;
      rotationRef.current += 0.005;
      ctx.save();
      ctx.translate(centerX, centerY);
      ctx.rotate(rotationRef.current);
      const step = (Math.PI * 2) / numBars;
      for (let i = 0; i < numBars; i++) {
        const index = Math.floor((i / numBars) * (data.length * 0.6));
        const barHeight = (data[index] / 255) * (Math.min(centerX, centerY) * 0.5);
        if (!barHeightsRef.current[i]) barHeightsRef.current[i] = 0;
        barHeightsRef.current[i] += (barHeight - barHeightsRef.current[i]) * 0.2;
        ctx.rotate(step);
        ctx.fillStyle = colors.alpha(0.8);
        ctx.fillRect(0, radius, 4, barHeightsRef.current[i]);
      }
      ctx.restore();
    };

    const drawParticles = (data: Uint8Array) => {
      ctx.fillStyle = "rgba(0, 0, 0, 0.2)";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      const colors = getPrimaryColors();
      let bass = 0;
      for (let i = 0; i < 10; i++) bass += data[i];
      bass /= 10 * 255;
      if (bass > 0.6 && particlesRef.current.length < 100) {
        for (let k = 0; k < 5; k++) {
          /* eslint-disable sonarjs/pseudo-random */
          const ang = Math.random() * Math.PI * 2; // NOSONAR - animation RNG, not security-sensitive
          particlesRef.current.push({
            x: canvas.width / 2,
            y: canvas.height / 2,
            vx: Math.cos(ang) * (Math.random() * 5 + 2), // NOSONAR
            vy: Math.sin(ang) * (Math.random() * 5 + 2), // NOSONAR
            size: Math.random() * 4 + 2, // NOSONAR
            color: colors.alpha(Math.random()), // NOSONAR
            /* eslint-enable sonarjs/pseudo-random */
            life: 1,
          });
        }
      }
      for (const p of particlesRef.current) {
        p.x += p.vx;
        p.y += p.vy;
        p.life -= 0.02;
        p.size *= 0.95;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = p.color;
        ctx.fill();
      }
      particlesRef.current = particlesRef.current.filter((p) => p.life > 0);
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
        case "wave":
          drawWave(timeDataRef.current!);
          break;
        case "circle":
          drawCircle(data);
          break;
        case "particles":
          drawParticles(data);
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
