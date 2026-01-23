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
});
