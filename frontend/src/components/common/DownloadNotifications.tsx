import { useEffect } from "react";
import { useStore } from "../../store/useStore";

export default function DownloadNotifications() {
  const { addNotification } = useStore();

  useEffect(() => {
    const handleCompleted = (e: any) => {
      const trackTitle = e.detail?.track?.title || "Track";
      addNotification("success", `Download completed: ${trackTitle}`);
    };

    const handleError = (e: any) => {
      const message = e.detail?.message || "Download failed";
      addNotification("error", message);
    };

    window.addEventListener("download:completed", handleCompleted as any);
    window.addEventListener("download:error", handleError as any);

    return () => {
      window.removeEventListener("download:completed", handleCompleted as any);
      window.removeEventListener("download:error", handleError as any);
    };
  }, [addNotification]);

  return null;
}
