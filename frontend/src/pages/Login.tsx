import LoginForm from "../components/auth/LoginForm";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import Logo from "../components/common/Logo";
import { useRegistrationStatus } from "../hooks/useRegistrationStatus";

export default function Login() {
  const { data: registration } = useRegistrationStatus();
  const registrationEnabled = registration?.enabled ?? false;

  return (
    <div className="min-h-screen w-full flex items-center justify-center p-4 bg-background">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="w-full max-w-md bg-black/40 backdrop-blur-xl border border-white/10 rounded-(--radius) p-8 shadow-2xl relative overflow-hidden"
      >
        <div className="text-center mb-8 flex flex-col items-center">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <Logo size="lg" />
          </motion.div>
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
            className="text-muted-foreground mt-2"
          >
            Sign in to continue to Audiovault
          </motion.p>
        </div>

        <LoginForm />

        {registrationEnabled && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
            className="mt-8 text-center text-sm text-muted-foreground"
          >
            Don't have an account?{" "}
            <Link
              to="/register"
              className="text-primary hover:text-green-400 font-medium hover:underline transition-all"
            >
              Create account
            </Link>
          </motion.p>
        )}
      </motion.div>
    </div>
  );
}
