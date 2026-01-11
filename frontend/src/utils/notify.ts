import toast from "react-hot-toast";
import { useStore } from "../store/useStore";

type NotificationType = "success" | "error" | "info" | "warning";

const addNotification = (type: NotificationType, message: string) => {
  useStore.getState().addNotification(type, message);
};

export const notify = {
  success: (message: string) => {
    addNotification("success", message);
    toast.success(message);
  },
  error: (message: string) => {
    addNotification("error", message);
    toast.error(message);
  },
  info: (message: string) => {
    addNotification("info", message);
    // React-hot-toast doesn't have 'info' by default usually, but we can use simple toast or custom icon
    toast(message, { icon: "ℹ️" });
  },
  warning: (message: string) => {
    addNotification("warning", message);
    toast(message, { icon: "⚠️" });
  },
  // Keep raw toast access if needed
  custom: toast,
};
