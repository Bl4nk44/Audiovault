import { motion, AnimatePresence } from "framer-motion";
import { AlertTriangle, X, Trash2 } from "lucide-react";
import { cn } from "../../lib/utils";
import { createPortal } from "react-dom";

interface ConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  variant?: "danger" | "info";
}

export default function ConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmText = "Confirm",
  cancelText = "Cancel",
  variant = "danger",
}: ConfirmModalProps) {
  if (!isOpen) return null;

  return createPortal(
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-100"
          />

          {/* Modal */}
          <div className="fixed inset-0 flex items-center justify-center z-101 pointer-events-none">
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="w-full max-w-md mx-4 pointer-events-auto"
            >
              <div className="bg-card border border-border rounded-2xl shadow-2xl overflow-hidden relative">
                {/* Header Gradient Line */}
                <div
                  className={cn(
                    "h-1 w-full bg-linear-to-r",
                    variant === "danger"
                      ? "from-destructive to-orange-500"
                      : "from-primary to-accent"
                  )}
                />

                <div className="p-6">
                  <div className="flex items-start gap-4">
                    <div
                      className={cn(
                        "p-3 rounded-full shrink-0", // Added shrink-0
                        variant === "danger"
                          ? "bg-destructive/10 text-destructive"
                          : "bg-primary/10 text-primary"
                      )}
                    >
                      <AlertTriangle className="w-6 h-6" />{" "}
                      {/* Changed size prop to className */}
                    </div>
                    <div className="flex-1">
                      <h3 className="text-xl font-bold text-foreground mb-2">
                        {title}
                      </h3>
                      <p className="text-muted-foreground leading-relaxed">
                        {message}
                      </p>
                    </div>
                    <button
                      onClick={onClose}
                      className="text-muted-foreground hover:text-foreground transition-colors"
                    >
                      <X size={20} />
                    </button>
                  </div>

                  <div className="flex justify-end gap-3 mt-8">
                    <button // Changed from Button component
                      onClick={onClose}
                      className="px-4 py-2 rounded-lg bg-secondary text-secondary-foreground hover:bg-secondary/80 transition-colors font-medium text-sm" // Updated classes
                    >
                      {cancelText}
                    </button>
                    <button // Changed from Button component
                      onClick={() => {
                        onConfirm();
                        onClose();
                      }}
                      className={cn(
                        "px-4 py-2 rounded-lg text-white transition-all shadow-lg font-medium text-sm flex items-center gap-2", // Updated classes
                        variant === "danger"
                          ? "bg-destructive! hover:bg-destructive/80! shadow-destructive/20 text-destructive-foreground" // Fixed important modifier syntax
                          : "bg-primary! hover:bg-primary/80! text-primary-foreground shadow-primary/20" // Fixed important modifier syntax and text color
                      )}
                    >
                      {variant === "danger" && <Trash2 size={16} />}{" "}
                      {/* Conditionally added Trash2 */}
                      {confirmText}
                    </button>
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>,
    document.body
  );
}
