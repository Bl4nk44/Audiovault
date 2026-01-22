import { useCallback, useState } from "react";

interface ConfirmDialogOptions {
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  variant?: "danger" | "info";
}

interface ConfirmDialogState extends ConfirmDialogOptions {
  isOpen: boolean;
  onConfirm: () => void;
}

const defaultState: ConfirmDialogState = {
  isOpen: false,
  title: "",
  message: "",
  confirmText: "Confirm",
  cancelText: "Cancel",
  variant: "danger",
  onConfirm: () => {},
};

/**
 * Hook for managing confirmation dialogs.
 *
 * @example
 * const { dialogProps, confirm, closeDialog } = useConfirmDialog();
 *
 * // Trigger confirmation
 * const handleDelete = async () => {
 *   const confirmed = await confirm({
 *     title: "Delete Playlist",
 *     message: "Are you sure you want to delete this playlist?",
 *     confirmText: "Delete",
 *     variant: "danger"
 *   });
 *   if (confirmed) {
 *     // perform delete
 *   }
 * };
 *
 * // Render the dialog
 * <ConfirmModal {...dialogProps} />
 */
export function useConfirmDialog() {
  const [state, setState] = useState<ConfirmDialogState>(defaultState);
  const [resolveRef, setResolveRef] = useState<((value: boolean) => void) | null>(null);

  const confirm = useCallback((options: ConfirmDialogOptions): Promise<boolean> => {
    return new Promise((resolve) => {
      setResolveRef(() => resolve);
      setState({
        ...defaultState,
        ...options,
        isOpen: true,
        onConfirm: () => {
          resolve(true);
          setState(defaultState);
          setResolveRef(null);
        },
      });
    });
  }, []);

  const closeDialog = useCallback(() => {
    if (resolveRef) {
      resolveRef(false);
    }
    setState(defaultState);
    setResolveRef(null);
  }, [resolveRef]);

  const dialogProps = {
    isOpen: state.isOpen,
    onClose: closeDialog,
    onConfirm: state.onConfirm,
    title: state.title,
    message: state.message,
    confirmText: state.confirmText,
    cancelText: state.cancelText,
    variant: state.variant,
  };

  return {
    dialogProps,
    confirm,
    closeDialog,
    isOpen: state.isOpen,
  };
}
