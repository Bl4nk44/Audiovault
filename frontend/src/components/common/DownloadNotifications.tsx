import { useEffect } from "react";

import type { DownloadCompletedDetail, DownloadErrorDetail } from "../../types/events";
import { notify as toast } from "../../utils/notify";

export default function DownloadNotifications() {
  useEffect(() => {
    const handleCompleted = (e: CustomEvent<DownloadCompletedDetail>) => {
      toast.success(`Download completed: ${e.detail.track.title}`);
    };

    const handleError = (e: CustomEvent<DownloadErrorDetail>) => {
      toast.error(`Download failed: ${e.detail.message}`);
    };

    globalThis.addEventListener("download:completed", handleCompleted as EventListener);
    globalThis.addEventListener("download:error", handleError as EventListener);

    return () => {
      globalThis.removeEventListener("download:completed", handleCompleted as EventListener);
      globalThis.removeEventListener("download:error", handleError as EventListener);
    };
  }, []); // The original dependency array was [addNotification]. The instruction's Code Edit shows '[]addNotification])', which is syntactically incorrect. Assuming the intent was to remove 'addNotification' from the dependencies if 'toast' is used directly, resulting in '[]'.

  return null;
}
