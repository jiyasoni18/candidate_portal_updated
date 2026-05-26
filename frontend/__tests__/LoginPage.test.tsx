import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import LoginPage from "../app/login/page.tsx";

// Mock next/navigation
const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

// Mock api module
vi.mock("../lib/api", () => ({
  loginUser: vi.fn(),
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

describe("LoginPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it("renders email, password inputs and submit button", () => {
    render(<LoginPage />);
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
  });

  it("shows error for empty email on submit", async () => {
    render(<LoginPage />);
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));
    await waitFor(() => {
      expect(screen.getByText("Email is required.")).toBeInTheDocument();
    });
    const { loginUser } = await import("../lib/api");
    expect(loginUser).not.toHaveBeenCalled();
  });

  it("shows error for empty password on submit", async () => {
    render(<LoginPage />);
    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "user@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));
    await waitFor(() => {
      expect(screen.getByText("Password is required.")).toBeInTheDocument();
    });
    const { loginUser } = await import("../lib/api");
    expect(loginUser).not.toHaveBeenCalled();
  });

  it("shows error for invalid email format", async () => {
    render(<LoginPage />);
    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "not-an-email" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "password123" },
    });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));
    await waitFor(() => {
      expect(
        screen.getByText("Please enter a valid email address.")
      ).toBeInTheDocument();
    });
    const { loginUser } = await import("../lib/api");
    expect(loginUser).not.toHaveBeenCalled();
  });

  it("shows loading state while submitting", async () => {
    const { loginUser } = await import("../lib/api");
    (loginUser as ReturnType<typeof vi.fn>).mockReturnValue(new Promise(() => {}));

    render(<LoginPage />);
    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "user@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "password123" },
    });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /signing in/i })).toBeDisabled();
    });
  });

  it("stores token and redirects to /dashboard on success", async () => {
    const { loginUser } = await import("../lib/api");
    (loginUser as ReturnType<typeof vi.fn>).mockResolvedValue({
      access_token: "test-jwt",
      token_type: "bearer",
    });

    render(<LoginPage />);
    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "user@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "password123" },
    });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(localStorage.getItem("auth_token")).toBe("test-jwt");
      expect(mockPush).toHaveBeenCalledWith("/dashboard");
    });
  });

  it("displays API error message on 401", async () => {
    const { loginUser, ApiError } = await import("../lib/api");
    (loginUser as ReturnType<typeof vi.fn>).mockRejectedValue(
      new (ApiError as any)(401, "Invalid email or password.")
    );

    render(<LoginPage />);
    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "user@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "wrongpassword" },
    });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText("Invalid email or password.")).toBeInTheDocument();
    });
  });

  it("includes a link to /register", () => {
    render(<LoginPage />);
    const link = screen.getByRole("link", { name: /create one/i });
    expect(link).toHaveAttribute("href", "/register");
  });
});
