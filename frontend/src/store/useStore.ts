import { create } from "zustand";
import { createAuthSlice, type AuthSlice } from "./slices/authSlice";
import { createPlayerSlice, type PlayerSlice } from "./slices/playerSlice";
import { createQueueSlice, type QueueSlice } from "./slices/queueSlice";
import { createWatchlistSlice, type WatchlistSlice } from "./slices/watchlistSlice";
import { createNotificationSlice, type NotificationSlice } from "./slices/notificationSlice";

type AppState = AuthSlice & PlayerSlice & QueueSlice & WatchlistSlice & NotificationSlice;

export const useStore = create<AppState>((...a) => ({
  ...createAuthSlice(...a),
  ...createPlayerSlice(...a),
  ...createQueueSlice(...a),
  ...createWatchlistSlice(...a),
  ...createNotificationSlice(...a),
}));
