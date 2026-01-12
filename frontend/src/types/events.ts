import type { Track } from "./index";

export interface DownloadProgressDetail {
  download_id: string;
  progress: number;
  status?: string;
  track?: {
    title: string;
    artist: string;
    image_url?: string;
  };
}

export interface DownloadCompletedDetail {
  download_id?: string;
  filename?: string;
  track: Track;
}

export interface DownloadErrorDetail {
  download_id?: string;
  error?: string;
  message: string;
}

export interface DownloadProcessingDetail {
  download_id: string;
  status: string;
}

export interface DownloadPausedDetail {
  download_id: string;
}

export interface DownloadCancelledDetail {
  download_id: string;
}

declare global {
  interface WindowEventMap {
    "download:progress": CustomEvent<DownloadProgressDetail>;
    "download:completed": CustomEvent<DownloadCompletedDetail>;
    "download:error": CustomEvent<DownloadErrorDetail>;
    "download:processing": CustomEvent<DownloadProcessingDetail>;
    "download:paused": CustomEvent<DownloadPausedDetail>;
    "download:cancelled": CustomEvent<DownloadCancelledDetail>;
  }
}
