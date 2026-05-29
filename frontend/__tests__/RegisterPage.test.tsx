import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import RegisterPage from "../app/register/page";

// Mock next/navigation
const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

// Mock api module
vi.mock("../lib/api", () => ({
  registerUser: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number;
    detail: string;
    constructor(status: number, detail: string) {
      super(detail);
      this.name = "ApiError";
      this.status = status;
      this.detail = detail;
    }
  },
}));

function fillForm({
  fullName = "Jane Smith",
  email = "jane@example.com",
  password = "password123",
  confirmPassword = "password123",
}: {
  fullName?: string;
  email?: string;
  password?: string;
  confirmPassword?: string;
} = {}) {
  if (fullName !== undefined) {
    fireEvent.change(screen.getByLabelText("Full name"), { target: { value: fullName } });
  }
  if (email !== undefined) {
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: email } });
  }
  if (password !== undefined) {
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: password } });
  }
  if (confirmPassword !== undefined) {
    fireEvent.change(screen.getByLabelText("Confirm password"), { target: { value: confirmPassword } });
  }
}

describe("RegisterPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it("renders all inputs and submit button", () => {
    render(<RegisterPage />);
    expect(screen.getByLabelText("Full name")).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    expect(screen.getByLabelText("Confirm password")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /create account/i })).toBeInTheDocument();
  });

  it("shows error for empty full name on submit", async () => {
    render(<RegisterPage />);
    fillForm({ fullName: "" });
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));
    await waitFor(() => {
      expect(screen.getByText("Full name is required.")).toBeInTheDocument();
    });
    const { registerUser } = await import("../lib/api");
    expect(registerUser).not.toHaveBeenCalled();
  });

  it("shows error for empty email on submit", async () => {
    render(<RegisterPage />);
    fillForm({ email: "" });
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));
    await waitFor(() => {
      expect(screen.getByText("Email is required.")).toBeInTheDocument();
    });
    const { registerUser } = await import("../lib/api");
    expect(registerUser).not.toHaveBeenCalled();
  });

  it("shows error for invalid email format", async () => {
    render(<RegisterPage />);
    fillForm({ email: "not-an-email" });
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));
    await waitFor(() => {
      expect(screen.getByText("Please enter a valid email address.")).toBeInTheDocument();
    });
    const { registerUser } = await import("../lib/api");
    expect(registerUser).not.toHaveBeenCalled();
  });

  it("shows error for password shorter than 8 characters", async () => {
    render(<RegisterPage />);
    fillForm({ password: "short", confirmPassword: "short" });
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));
    await waitFor(() => {
      expect(screen.getByText("Password must be at least 8 characters.")).toBeInTheDocument();
    });
    const { registerUser } = await import("../lib/api");
    expect(registerUser).not.toHaveBeenCalled();
  });

  it("shows error when passwords do not match", async () => {
    render(<RegisterPage />);
    fillForm({ password: "password123", confirmPassword: "different1" });
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));
    await waitFor(() => {
      expect(screen.getByText("Passwords do not match.")).toBeInTheDocument();
    });
    const { registerUser } = await import("../lib/api");
    expect(registerUser).not.toHaveBeenCalled();
  });

  it("shows loading state while submitting", async () => {
    const { registerUser } = await import("../lib/api");
    (registerUser as ReturnType<typeof vi.fn>).mockReturnValue(new Promise(() => {}));

    render(<RegisterPage />);
    fillForm();
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /creating account/i })).toBeDisabled();
    });
  });

  it("stores token and redirects to /dashboard on success", async () => {
    const { registerUser } = await import("../lib/api");
    (registerUser as ReturnType<typeof vi.fn>).mockResolvedValue({
      access_token: "test-jwt",
      token_type: "bearer",
    });

    render(<RegisterPage />);
    fillForm();
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(localStorage.getItem("auth_token")).toBe("test-jwt");
      expect(mockPush).toHaveBeenCalledWith("/dashboard");
    });
  });

  it("displays API error on duplicate email (409)", async () => {
    const { registerUser, ApiError } = await import("../lib/api");
    (registerUser as ReturnType<typeof vi.fn>).mockRejectedValue(
      new (ApiError as any)(409, "Email already registered.")
    );

    render(<RegisterPage />);
    fillForm();
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByText("Email already registered.")).toBeInTheDocument();
    });
  });

  it("includes a link to /login", () => {
    render(<RegisterPage />);
    const link = screen.getByRole("link", { name: /sign in/i });
    expect(link).toHaveAttribute("href", "/login");
  });
});
