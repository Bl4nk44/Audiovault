import { AxiosError } from "axios";
import { motion } from "framer-motion";
import { AlertTriangle, Camera, Lock, Save, Trash2, User } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "../../hooks/useTranslation";
import api from "../../services/api";
import { useStore } from "../../store/useStore";
import { notify as toast } from "../../utils/notify";
import Button from "../ui/Button";
import ConfirmModal from "../ui/ConfirmModal";

interface ProfileFormData {
  username: string;
  avatar_url?: string;
}

interface PasswordFormData {
  currentPassword?: string;
  newPassword?: string;
  confirmPassword?: string;
}

export default function AccountSettings() {
  const { t } = useTranslation();
  const { user, setUser, logout } = useStore();
  const [isLoading, setIsLoading] = useState(false);

  // Account Deletion State
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [deleteLibrary, setDeleteLibrary] = useState(false);

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm({
    defaultValues: {
      username: user?.username || "",
      avatar_url: "",
    },
  });

  // Populate form with user data, effectively hiding internal paths
  // Use useEffect for side effects instead of useState callback
  useEffect(() => {
    if (user?.username) setValue("username", user.username);
    if (user?.preferences?.avatar_url) {
      // Only show the URL if it is an external link (starts with http)
      // If it's internal (starts with /), keep the input empty to avoid showing raw path
      const url = user.preferences.avatar_url;
      if (typeof url === "string" && url.startsWith("http")) {
        setValue("avatar_url", url);
      } else {
        setValue("avatar_url", "");
      }
    }
  }, [user, setValue]);

  const {
    register: registerPassword,
    handleSubmit: handleSubmitPassword,
    reset: resetPassword,
    watch,
    formState: { errors: passwordErrors },
  } = useForm();

  const newPasswordValue = watch("newPassword");

  const onUpdateProfile = async (data: ProfileFormData) => {
    setIsLoading(true);
    try {
      // Filter out empty avatar_url to prevent overwriting existing avatar with empty string
      // unless we want to allow clearing? For now assuming empty input means "keep current"
      const payload: Partial<ProfileFormData> = { ...data };
      if (!payload.avatar_url) {
        delete payload.avatar_url;
      }

      const response = await api.put("/users/me", payload);
      setUser({ ...user!, ...response.data.user });
      toast.success(t("settings.messages.profileUpdated"));
    } catch (error) {
      const err = error as AxiosError<{ detail: string }>;
      toast.error(err.response?.data?.detail || t("settings.messages.updateError"));
    } finally {
      setIsLoading(false);
    }
  };

  const onUpdatePassword = async (data: PasswordFormData) => {
    setIsLoading(true);
    try {
      await api.put("/users/me/password", {
        current_password: data.currentPassword,
        new_password: data.newPassword,
      });
      toast.success(t("settings.messages.passwordUpdated"));
      resetPassword();
    } catch (error) {
      const err = error as AxiosError<{ detail: string }>;
      toast.error(err.response?.data?.detail || t("settings.messages.updateError"));
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteAccount = async () => {
    setIsLoading(true);
    try {
      await api.delete("/users/me", {
        params: { delete_library: deleteLibrary },
      });
      toast.success("Account deleted successfully");
      logout();
    } catch (error) {
      const err = error as AxiosError<{ detail: string }>;
      toast.error(err.response?.data?.detail || "Failed to delete account");
      setIsLoading(false);
    }
  };

  // Setup file input ref
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleAvatarClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    setIsLoading(true);
    try {
      const response = await api.post("/users/me/avatar", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });
      // Update local state with new avatar URL
      setUser({ ...user!, ...response.data.user });

      // Also update the form value for avatar_url
      // Clear the input field because we have an internal path now
      setValue("avatar_url", "");
      toast.success(t("settings.messages.avatarUpdated"));
    } catch (error) {
      const err = error as AxiosError<{ detail: string }>;
      toast.error(err.response?.data?.detail || t("settings.messages.uploadError"));
    } finally {
      setIsLoading(false);
    }
  };

  const getAvatarSrc = (url?: string) => {
    if (!url) return undefined;
    if (url.startsWith("http")) return url;
    // If it's a relative path from our backend (e.g. /stream/...)
    return `${
      import.meta.env.VITE_API_URL?.replace("/api/v1", "") || "http://localhost:8000"
    }${url}`;
  };

  return (
    <div className="space-y-8">
      {/* Profile Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="p-8 rounded-3xl border border-white/10 bg-white/5 backdrop-blur-xl shadow-xl"
      >
        <h3 className="text-xl font-bold text-white border-b border-white/10 pb-4 mb-6 flex items-center gap-3">
          <User className="text-primary" size={24} />
          {t("settings.profileInfo")}
        </h3>

        <form onSubmit={handleSubmit(onUpdateProfile)} className="space-y-6">
          <div className="flex items-center gap-6 mb-8">
            <div className="relative group">
              <div className="w-24 h-24 rounded-full bg-linear-to-br from-primary to-green-600 flex items-center justify-center shadow-lg overflow-hidden">
                {user?.preferences?.avatar_url &&
                typeof user.preferences.avatar_url === "string" ? (
                  <img
                    src={getAvatarSrc(user.preferences.avatar_url)}
                    alt="Avatar"
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <User size={40} className="text-black" />
                )}
              </div>
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                className="hidden"
                accept="image/*"
              />
              <button
                type="button"
                onClick={handleAvatarClick}
                className="absolute inset-0 bg-black/50 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
              >
                <Camera className="text-white" size={24} />
              </button>
            </div>
            <div>
              <h4 className="text-lg font-bold text-white">{user?.username}</h4>
              <p className="text-gray-400 text-sm">{user?.email}</p>
            </div>
          </div>

          <div className="grid gap-6 md:grid-cols-2">
            <div className="space-y-2">
              <label htmlFor="username" className="text-sm font-medium text-gray-300 ml-1">
                {t("settings.username")}
              </label>
              <input
                id="username"
                {...register("username", { required: "Username is required" })}
                className="w-full px-4 py-3 rounded-xl bg-black/20 border border-white/10 text-white focus:outline-none focus:border-primary/50"
              />
              {errors.username && (
                <span className="text-red-400 text-xs ml-1">
                  {errors.username.message as string}
                </span>
              )}
            </div>
          </div>

          <div className="flex justify-end">
            <Button type="submit" isLoading={isLoading} variant="primary" className="px-6">
              <Save size={18} className="mr-2" /> {t("settings.saveProfile")}
            </Button>
          </div>
        </form>
      </motion.div>

      {/* Password Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="p-8 rounded-3xl border border-white/10 bg-white/5 backdrop-blur-xl shadow-xl"
      >
        <h3 className="text-xl font-bold text-white border-b border-white/10 pb-4 mb-6 flex items-center gap-3">
          <Lock className="text-orange-500" size={24} />
          {t("settings.changePassword")}
        </h3>

        <form onSubmit={handleSubmitPassword(onUpdatePassword)} className="space-y-6 max-w-md">
          <div className="space-y-2">
            <label htmlFor="currentPassword" className="text-sm font-medium text-gray-300 ml-1">
              {t("settings.currentPassword")}
            </label>
            <input
              id="currentPassword"
              type="password"
              {...registerPassword("currentPassword", {
                required: "Current password is required",
              })}
              className="w-full px-4 py-3 rounded-xl bg-black/20 border border-white/10 text-white focus:outline-none focus:border-primary/50"
            />
            {passwordErrors.currentPassword && (
              <span className="text-red-400 text-xs ml-1">
                {passwordErrors.currentPassword.message as string}
              </span>
            )}
          </div>

          <div className="space-y-2">
            <label htmlFor="newPassword" className="text-sm font-medium text-gray-300 ml-1">
              {t("settings.newPassword")}
            </label>
            <input
              id="newPassword"
              type="password"
              {...registerPassword("newPassword", {
                required: "New password is required",
                minLength: { value: 6, message: "Minimum 6 characters" },
              })}
              className="w-full px-4 py-3 rounded-xl bg-black/20 border border-white/10 text-white focus:outline-none focus:border-primary/50"
            />
            {passwordErrors.newPassword && (
              <span className="text-red-400 text-xs ml-1">
                {passwordErrors.newPassword.message as string}
              </span>
            )}
          </div>

          <div className="space-y-2">
            <label htmlFor="confirmPassword" className="text-sm font-medium text-gray-300 ml-1">
              Confirm New Password
            </label>
            <input
              id="confirmPassword"
              type="password"
              {...registerPassword("confirmPassword", {
                required: "Please confirm your password",
                validate: (val) => {
                  if (!val) return "Please confirm your password";
                  if (val !== newPasswordValue) return "Passwords do not match";
                  return true;
                },
              })}
              className="w-full px-4 py-3 rounded-xl bg-black/20 border border-white/10 text-white focus:outline-none focus:border-primary/50"
            />
            {passwordErrors.confirmPassword && (
              <span className="text-red-400 text-xs ml-1">
                {passwordErrors.confirmPassword.message as string}
              </span>
            )}
          </div>

          <div className="flex justify-end">
            <Button
              type="submit"
              isLoading={isLoading}
              variant="outline"
              className="px-6 hover:bg-orange-500/10 hover:text-orange-500 hover:border-orange-500/50"
            >
              {t("settings.updatePassword")}
            </Button>
          </div>
        </form>
      </motion.div>

      {/* Danger Zone */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="p-8 rounded-3xl border border-red-500/20 bg-red-500/5 backdrop-blur-xl shadow-xl"
      >
        <h3 className="text-xl font-bold text-red-500 border-b border-red-500/20 pb-4 mb-6 flex items-center gap-3">
          <AlertTriangle className="text-red-500" size={24} />
          Danger Zone
        </h3>

        <div className="flex items-center justify-between">
          <div>
            <h4 className="text-lg font-bold text-white mb-1">Delete Account</h4>
            <p className="text-gray-400 text-sm">
              Permanently delete your account and all associated data.
            </p>
          </div>
          <Button
            variant="danger"
            onClick={() => setIsDeleteModalOpen(true)}
            className="shrink-0"
            data-testid="delete-account-btn"
          >
            <Trash2 size={18} className="mr-2" /> Delete Account
          </Button>
        </div>
      </motion.div>

      <ConfirmModal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        onConfirm={handleDeleteAccount}
        title="Delete Account"
        message="Are you sure you want to delete your account? This action cannot be undone."
        confirmText="Delete Account"
        variant="danger"
      >
        <div className="mt-4 flex items-start gap-3 p-3 rounded-lg bg-black/20 border border-red-500/20">
          <input
            type="checkbox"
            id="deleteLibrary"
            checked={deleteLibrary}
            onChange={(e) => setDeleteLibrary(e.target.checked)}
            className="mt-1 w-4 h-4 rounded border-border bg-muted text-red-500 focus:ring-red-500 focus:ring-offset-gray-900"
          />
          <label
            htmlFor="deleteLibrary"
            className="text-sm text-gray-300 cursor-pointer select-none"
          >
            <span className="block font-medium text-white mb-1">Delete my downloaded library</span>
            <span className="block text-gray-400">
              Also delete all music files associated with this account from the server storage.
            </span>
          </label>
        </div>
      </ConfirmModal>
    </div>
  );
}
