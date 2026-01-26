import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import api from "../../services/api";
import { notify } from "../../utils/notify";
import AccountSettings from "./AccountSettings";

// Mocks
vi.mock("../../services/api", () => ({
  default: {
    put: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock("../../utils/notify", () => ({
  notify: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock("../../hooks/useTranslation", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
  default: () => ({ t: (key: string) => key }),
}));

vi.mock("../../store/useStore", () => ({
  useStore: () => ({
    user: { username: "testuser" },
    setUser: vi.fn(),
    logout: vi.fn(),
  }),
}));

// Mock Lucide icons
vi.mock("lucide-react", () => ({
  AlertTriangle: () => <div>Icon-Alert</div>,
  Camera: () => <div>Icon-Camera</div>,
  Lock: () => <div>Icon-Lock</div>,
  Save: () => <div>Icon-Save</div>,
  Trash2: () => <div>Icon-Trash</div>,
  User: () => <div>Icon-User</div>,
  Loader2: () => <div>Icon-Loader</div>,
}));

vi.mock("../ui/ConfirmModal", () => ({
  default: ({ isOpen, onConfirm }: any) =>
    isOpen ? (
      <div data-testid="confirm-modal">
        <button onClick={onConfirm}>Confirm Delete</button>
      </div>
    ) : null,
}));

describe("AccountSettings", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders password change form", () => {
    render(<AccountSettings />);
    expect(screen.getByText("settings.changePassword")).toBeInTheDocument();
  });

  it("validates password mismatch", async () => {
    render(<AccountSettings />);

    // We can select by ID as confirmed in output snapshot (id="newPassword")
    const newPassInput = document.getElementById("newPassword");
    const confirmPassInput = document.getElementById("confirmPassword");
    const saveBtn = screen.getByText("settings.updatePassword");

    if (!newPassInput || !confirmPassInput) throw new Error("Inputs not found");

    fireEvent.change(newPassInput, { target: { value: "password123" } });
    fireEvent.change(confirmPassInput, { target: { value: "password124" } });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(screen.getByText("Passwords do not match")).toBeInTheDocument();
    });
  });

  it("submits successful password change", async () => {
    (api.put as any).mockResolvedValue({ data: {} });

    render(<AccountSettings />);

    const currentPassInput = document.getElementById("currentPassword");
    const newPassInput = document.getElementById("newPassword");
    const confirmPassInput = document.getElementById("confirmPassword");
    const saveBtn = screen.getByText("settings.updatePassword");

    if (!currentPassInput || !newPassInput || !confirmPassInput)
      throw new Error("Inputs not found");

    fireEvent.change(currentPassInput, { target: { value: "oldpassword" } });
    fireEvent.change(newPassInput, { target: { value: "newpassword" } });
    fireEvent.change(confirmPassInput, { target: { value: "newpassword" } });

    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(api.put).toHaveBeenCalledWith("/users/me/password", {
        current_password: "oldpassword",
        new_password: "newpassword",
      });
      expect(notify.success).toHaveBeenCalled();
    });
  });

  it("updates username profile", async () => {
    (api.put as any).mockResolvedValue({ data: { user: { username: "newname" } } });
    render(<AccountSettings />);

    const usernameInput = document.getElementById("username");
    const saveBtn = screen.getByText("settings.saveProfile"); // Assuming translation key

    if (!usernameInput) throw new Error("Input not found");

    fireEvent.change(usernameInput, { target: { value: "newname" } });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(api.put).toHaveBeenCalledWith(
        "/users/me",
        expect.objectContaining({ username: "newname" })
      );
      expect(notify.success).toHaveBeenCalledWith("settings.messages.profileUpdated");
    });
  });

  it("handles account deletion", async () => {
    (api.delete as any).mockResolvedValue({});
    render(<AccountSettings />);

    // Click delete button
    fireEvent.click(screen.getByTestId("delete-account-btn"));

    // Modal should be open
    await waitFor(() => expect(screen.getByTestId("confirm-modal")).toBeInTheDocument());

    // Confirm delete
    fireEvent.click(screen.getByText("Confirm Delete"));

    await waitFor(() => {
      expect(api.delete).toHaveBeenCalledWith(
        "/users/me",
        expect.objectContaining({ params: { delete_library: false } })
      );
      expect(notify.success).toHaveBeenCalledWith("Account deleted successfully");
    });
  });

  it("handles account deletion error", async () => {
    (api.delete as any).mockRejectedValue(new Error("Delete failed"));
    render(<AccountSettings />);

    fireEvent.click(screen.getByTestId("delete-account-btn"));
    await waitFor(() => expect(screen.getByTestId("confirm-modal")).toBeInTheDocument());
    fireEvent.click(screen.getByText("Confirm Delete"));

    await waitFor(() => {
      expect(notify.error).toHaveBeenCalledWith("Failed to delete account");
    });
  });

  it("handles avatar upload", async () => {
    (api.post as any).mockResolvedValue({
      data: { user: { preferences: { avatar_url: "/new-avatar.jpg" } } },
    });
    render(<AccountSettings />);

    // Find hidden file input
    const fileInput = document.querySelector('input[type="file"]');
    if (!fileInput) throw new Error("File input not found");

    const file = new File(["(⌐□_□)"], "chucknorris.png", { type: "image/png" });

    // Trigger upload
    await waitFor(() => {
      fireEvent.change(fileInput, { target: { files: [file] } });
    });

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith(
        "/users/me/avatar",
        expect.any(FormData),
        expect.any(Object)
      );
      expect(notify.success).toHaveBeenCalledWith("settings.messages.avatarUpdated");
    });
  });
});
