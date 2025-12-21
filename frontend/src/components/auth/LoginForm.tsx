import { useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { login, getMe } from "../../services/auth";
import { useStore } from "../../store/useStore";
import { notify as toast } from "../../utils/notify";
import { motion } from "framer-motion";
import Button from "../ui/Button";
import { Mail, Lock, AlertCircle } from "lucide-react";
import type { LoginCredentials } from "../../types";

export default function LoginForm() {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm();
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const { addSession, setTokens } = useStore();

  const onSubmit = async (data: LoginCredentials) => {
    setIsLoading(true);
    try {
      const response = await login(data);
      const { access_token, refresh_token } = response;

      // Fetch user details immediately after login to get full profile
      // We temporarily set token to allow the request
      setTokens(access_token, refresh_token);
      const user = await getMe();

      // Now add full session
      addSession(user, access_token, refresh_token);

      toast.success("Logged in successfully");
      navigate("/");
    } catch (error) {
      console.error("Login error:", error);
      const err = error as {
        response?: { data?: { detail?: string } };
        message?: string;
      };
      const errorMessage =
        err.response?.data?.detail ||
        err.message ||
        "Login failed. Please check your connection.";
      toast.error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const inputVariants = {
    focus: {
      scale: 1.02,
      borderColor: "rgba(34, 197, 94, 0.5)",
      boxShadow: "0 0 15px rgba(34, 197, 94, 0.2)",
    },
    blur: {
      scale: 1,
      borderColor: "rgba(255, 255, 255, 0.1)",
      boxShadow: "none",
    },
  };

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      className="space-y-6 w-full max-w-md relative z-10"
    >
      <div className="space-y-2">
        <label className="text-sm font-medium ml-1 text-gray-300">
          Username or Email
        </label>
        <div className="relative group">
          <Mail
            className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-primary transition-colors"
            size={18}
          />
          <motion.input
            variants={inputVariants}
            whileFocus="focus"
            initial="blur"
            {...register("email", {
              required: "Username or Email is required",
            })}
            className="w-full pl-10 pr-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder:text-gray-500 focus:outline-none transition-all"
            type="text"
            placeholder="Username or email"
          />
        </div>
        {errors.email && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-2 text-red-400 text-xs ml-1"
          >
            <AlertCircle size={12} />
            <span>{errors.email.message as string}</span>
          </motion.div>
        )}
      </div>

      <div className="space-y-2">
        <label className="text-sm font-medium ml-1 text-gray-300">
          Password
        </label>
        <div className="relative group">
          <Lock
            className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-primary transition-colors"
            size={18}
          />
          <motion.input
            variants={inputVariants}
            whileFocus="focus"
            initial="blur"
            {...register("password", { required: "Password is required" })}
            className="w-full pl-10 pr-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder:text-gray-500 focus:outline-none transition-all"
            type="password"
            placeholder="••••••••"
          />
        </div>
        {errors.password && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-2 text-red-400 text-xs ml-1"
          >
            <AlertCircle size={12} />
            <span>{errors.password.message as string}</span>
          </motion.div>
        )}
      </div>

      <Button
        type="submit"
        isLoading={isLoading}
        className="w-full py-6 text-lg shadow-lg shadow-primary/20"
        variant="primary"
      >
        Sign In
      </Button>
    </form>
  );
}
