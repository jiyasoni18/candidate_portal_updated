"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { registerUser, ApiError } from "@/lib/api";

function validateEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

export default function RegisterPage() {
  const router = useRouter();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [fullNameError, setFullNameError] = useState("");
  const [emailError, setEmailError] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [confirmPasswordError, setConfirmPasswordError] = useState("");
  const [apiError, setApiError] = useState("");
  const [loading, setLoading] = useState(false);

  function validate(): boolean {
    let valid = true;
    setFullNameError("");
    setEmailError("");
    setPasswordError("");
    setConfirmPasswordError("");
    setApiError("");

    if (!fullName.trim()) {
      setFullNameError("Full name is required.");
      valid = false;
    }

    if (!email.trim()) {
      setEmailError("Email is required.");
      valid = false;
    } else if (!validateEmail(email)) {
      setEmailError("Please enter a valid email address.");
      valid = false;
    }

    if (!password) {
      setPasswordError("Password is required.");
      valid = false;
    } else if (password.length < 8) {
      setPasswordError("Password must be at least 8 characters.");
      valid = false;
    }

    if (!confirmPassword) {
      setConfirmPasswordError("Please confirm your password.");
      valid = false;
    } else if (password && confirmPassword !== password) {
      setConfirmPasswordError("Passwords do not match.");
      valid = false;
    }

    return valid;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    setLoading(true);
    try {
      const data = await registerUser(fullName, email, password);
      localStorage.setItem("auth_token", data.access_token);
      router.push("/dashboard");
    } catch (err) {
      if (err instanceof ApiError) {
        setApiError(err.detail);
      } else {
        setApiError("Something went wrong. Try again.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center px-4">
      <div className="w-full max-w-sm bg-slate-800 border border-slate-700 rounded-xl p-8">
        <h1 className="text-xl font-semibold text-zinc-100 mb-6">Create account</h1>

        <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
          {/* Full Name */}
          <div className="flex flex-col gap-1">
            <label htmlFor="fullName" className="text-sm text-zinc-400">
              Full name
            </label>
            <input
              id="fullName"
              type="text"
              autoComplete="name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="Jane Smith"
            />
            {fullNameError && (
              <p className="text-xs text-red-400" role="alert">
                {fullNameError}
              </p>
            )}
          </div>

          {/* Email */}
          <div className="flex flex-col gap-1">
            <label htmlFor="email" className="text-sm text-zinc-400">
              Email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="you@example.com"
            />
            {emailError && (
              <p className="text-xs text-red-400" role="alert">
                {emailError}
              </p>
            )}
          </div>

          {/* Password */}
          <div className="flex flex-col gap-1">
            <label htmlFor="password" className="text-sm text-zinc-400">
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="••••••••"
            />
            {passwordError && (
              <p className="text-xs text-red-400" role="alert">
                {passwordError}
              </p>
            )}
          </div>

          {/* Confirm Password */}
          <div className="flex flex-col gap-1">
            <label htmlFor="confirmPassword" className="text-sm text-zinc-400">
              Confirm password
            </label>
            <input
              id="confirmPassword"
              type="password"
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="••••••••"
            />
            {confirmPasswordError && (
              <p className="text-xs text-red-400" role="alert">
                {confirmPasswordError}
              </p>
            )}
          </div>

          {/* API error */}
          {apiError && (
            <p className="text-xs text-red-400" role="alert">
              {apiError}
            </p>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={loading}
            className="mt-2 flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 disabled:cursor-not-allowed text-white text-sm font-medium transition-colors"
          >
            {loading ? (
              <>
                <span
                  className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"
                  aria-hidden="true"
                />
                Creating account…
              </>
            ) : (
              "Create account"
            )}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-zinc-500">
          Already have an account?{" "}
          <Link href="/login" className="text-indigo-400 hover:text-indigo-300">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
