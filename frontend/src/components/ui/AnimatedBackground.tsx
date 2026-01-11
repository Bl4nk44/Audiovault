export const AnimatedBackground = () => {
  return (
    <div className="fixed inset-0 w-full h-full -z-50 overflow-hidden pointer-events-none bg-background transition-colors duration-700">
      {/* Subtle Vignette for depth (edges only) */}
      <div className="absolute inset-0 bg-radial-gradient from-transparent via-transparent to-black/20 opacity-100" />
    </div>
  );
};
