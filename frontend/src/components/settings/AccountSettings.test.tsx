import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import api from "../../services/api";
import { useStore } from "../../store/useStore";
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

vi.mock("../../store/useStore", () => ({
  useStore: vi.fn(),
}));

vi.mock("../../utils/notify", () => ({
  notify: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock("../../hooks/useTranslation", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, className, onClick, style }: any) => (
      <div className={className} onClick={onClick} style={style}>
        {children}
      </div>
    ),
    h1: ({ children, className }: any) => <h1 className={className}>{children}</h1>,
    h3: ({ children, className }: any) => <h3 className={className}>{children}</h3>,
    button: ({ children, className, onClick, disabled, type, ...props }: any) => (
      <button className={className} onClick={onClick} disabled={disabled} type={type} {...props}>
        {children}
      </button>
    ),
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

describe("AccountSettings", () => {
  const mockSetUser = vi.fn();
  const mockLogout = vi.fn();
  const mockUser = {
    username: "testuser",
    email: "test@example.com",
    preferences: { avatar_url: "http://avatar.url" },
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (useStore as any).mockReturnValue({
      user: mockUser,
      setUser: mockSetUser,
      logout: mockLogout,
    });
  });

  it("should render profile info", () => {
    render(<AccountSettings />);
    expect(screen.getByDisplayValue("testuser")).toBeInTheDocument();
    expect(screen.getByText("test@example.com")).toBeInTheDocument();
  });

  it("should update profile on submit", async () => {
    const user = userEvent.setup();
    (api.put as any).mockResolvedValue({ data: { user: { ...mockUser, username: "newname" } } });

    render(<AccountSettings />);

    const usernameInput = screen.getByDisplayValue("testuser");
    await user.clear(usernameInput);
    await user.type(usernameInput, "newname");

    const saveButton = screen.getByText("settings.saveProfile");
    await user.click(saveButton);

    await waitFor(() => {
      expect(api.put).toHaveBeenCalledWith(
        "/users/me",
        expect.objectContaining({ username: "newname" })
      );
    });

    expect(mockSetUser).toHaveBeenCalled();
    expect(notify.success).toHaveBeenCalled();
  });

  it("should update password", async () => {
    const user = userEvent.setup();
    (api.put as any).mockResolvedValue({ data: {} });

    render(<AccountSettings />);

    await user.type(screen.getByLabelText("settings.currentPassword"), "oldpass");
    await user.type(screen.getByLabelText("settings.newPassword"), "newpass");
    await user.type(screen.getByLabelText("Confirm New Password"), "newpass");

    const updateButton = screen.getByText("settings.updatePassword");
    await user.click(updateButton);

    await waitFor(() => {
      expect(api.put).toHaveBeenCalledWith("/users/me/password", {
        current_password: "oldpass",
        new_password: "newpass",
      });
    });

    expect(notify.success).toHaveBeenCalled();
  });

  it("should show error if passwords do not match", async () => {
    const user = userEvent.setup();
    render(<AccountSettings />);

    await user.type(screen.getByLabelText("settings.newPassword"), "newpass");
    await user.type(screen.getByLabelText("Confirm New Password"), "mismatch");

    const updateButton = screen.getByText("settings.updatePassword");
    await user.click(updateButton);

    expect(await screen.findByText("Passwords do not match")).toBeInTheDocument();
    expect(api.put).not.toHaveBeenCalled();
  });

  it("should handle avatar selection/upload", async () => {
    const file = new File(["hello"], "hello.png", { type: "image/png" });
    (api.post as vi.Mock).mockResolvedValue({
      data: { user: { ...mockUser, preferences: { avatar_url: "/new/avatar.png" } } },
    });

    const { container } = render(<AccountSettings />);

    // Find hidden input specifically by type
    const input = container.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith(
        "/users/me/avatar",
        expect.any(FormData),
        expect.any(Object)
      );
      expect(mockSetUser).toHaveBeenCalled();
      expect(notify.success).toHaveBeenCalledWith("settings.messages.avatarUpdated");
    });
  });

  it("should handle account deletion flow with library deletion", async () => {
    const user = userEvent.setup();
    (api.delete as any).mockResolvedValue({});

    render(<AccountSettings />);

    const deleteButtons = screen.getAllByRole("button", { name: /Delete Account/i });
    await user.click(deleteButtons[0]);

    // Choose to delete library
    const checkbox = screen.getByLabelText(/Delete my downloaded library/i);
    await user.click(checkbox);

    // Click confirm in modal
    const allButtons = screen.getAllByRole("button", { name: /Delete Account/i });
    const confirmButton = allButtons[allButtons.length - 1];

    await user.click(confirmButton);

    await waitFor(() => {
      expect(api.delete).toHaveBeenCalledWith(
        "/users/me",
        expect.objectContaining({
          params: { delete_library: true },
        })
      );
    });

    expect(mockLogout).toHaveBeenCalled();
  });

  it("should handle profile update error", async () => {
    const user = userEvent.setup();
    (api.put as any).mockRejectedValue({ response: { data: { detail: "Invalid username" } } });

    render(<AccountSettings />);
    const saveButton = screen.getByText("settings.saveProfile");
    await user.click(saveButton);

    await waitFor(() => {
      expect(notify.error).toHaveBeenCalledWith("Invalid username");
    });
  });

  it("should handle password update error", async () => {
    const user = userEvent.setup();
    (api.put as any).mockRejectedValue({
      response: { data: { detail: "Wrong current password" } },
    });

    render(<AccountSettings />);
    await user.type(screen.getByLabelText("settings.currentPassword"), "wrong");
    await user.type(screen.getByLabelText("settings.newPassword"), "newpass123");
    await user.type(screen.getByLabelText("Confirm New Password"), "newpass123");

    await user.click(screen.getByText("settings.updatePassword"));

    await waitFor(() => {
      expect(notify.error).toHaveBeenCalledWith("Wrong current password");
    });
  });
});
