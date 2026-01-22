import { motion } from "framer-motion";

interface GaugeProps {
  value: number; // 0 to 100
  label: string;
  subLabel?: string;
  color: string; // Tailwind text color class
  icon?: React.ReactNode;
}

export default function Gauge({ value, label, subLabel, color, icon }: Readonly<GaugeProps>) {
  // Clamp value between 0 and 100
  const clampedValue = Math.min(Math.max(value, 0), 100);

  // SVG properties for a semi-circle gauge
  const radius = 80;
  const strokeWidth = 12;
  const center = radius + strokeWidth;

  // Arc calculation
  const arcPath = `M ${strokeWidth},${center} A ${radius},${radius} 0 0,1 ${center * 2 - strokeWidth},${center}`;
  const arcLength = Math.PI * radius;

  const strokeDashoffset = arcLength - (clampedValue / 100) * arcLength;

  return (
    <div className={`flex flex-col items-center justify-center relative ${color}`}>
      <div className="relative">
        <svg
          width={center * 2}
          height={center + 10}
          viewBox={`0 0 ${center * 2} ${center + 10}`}
          className="overflow-visible"
        >
          {/* Background Track */}
          <path
            d={arcPath}
            fill="none"
            stroke="currentColor"
            strokeWidth={strokeWidth}
            strokeOpacity={0.15}
            strokeLinecap="round"
          />

          {/* Progress Arc */}
          <motion.path
            d={arcPath}
            fill="none"
            stroke="currentColor"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={arcLength}
            initial={{ strokeDashoffset: arcLength }}
            animate={{ strokeDashoffset }}
            transition={{ type: "spring", stiffness: 60, damping: 20 }}
            className="drop-shadow-[0_0_8px_currentColor]"
          />
        </svg>

        {/* Value Text centered at bottom of arc */}
        <div className="absolute inset-0 flex flex-col items-center justify-end pb-0 pointer-events-none">
          {icon && <div className="mb-2 opacity-80 scale-125">{icon}</div>}
          <span className="text-3xl font-bold text-white drop-shadow-md pb-1">
            {Math.round(clampedValue)}
            <span className="text-lg opacity-70">%</span>
          </span>
        </div>
      </div>

      <div className="text-center -mt-2">
        <p className="text-gray-300 font-bold text-lg">{label}</p>
        {subLabel && <p className="text-gray-500 text-xs font-mono mt-1">{subLabel}</p>}
      </div>
    </div>
  );
}
