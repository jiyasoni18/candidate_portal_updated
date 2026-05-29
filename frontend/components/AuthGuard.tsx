"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";

const AUTH_ROUTES = ["/login", "/register"];

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    const token = localStorage.getItem("auth_token");
    const isAuthRoute = AUTH_ROUTES.includes(pathname);

    if (!token && !isAuthRoute) {
      // Unauthenticated user on a protected route → send to login
      router.replace("/login");
    } else if (token && isAuthRoute) {
      // Authenticated user on an auth route → send to dashboard
      router.replace("/dashboard");
    }
  }, [pathname, router]);

  return <>{children}</>;
}
