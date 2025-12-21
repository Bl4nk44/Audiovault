import type { Track } from "./index";

export interface DownloadProgressDetail {
  download_id: string;
  progress: number;
}

export interface DownloadCompletedDetail {
  track: Track;
}

export interface DownloadErrorDetail {
  message: string;
}

declare global {
  interface WindowEventMap {
    "download:progress": CustomEvent<DownloadProgressDetail>;
    "download:completed": CustomEvent<DownloadCompletedDetail>;
    "download:error": CustomEvent<DownloadErrorDetail>;
  }
}
