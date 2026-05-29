"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LayoutDashboard, Mic, Settings, LogOut } from "lucide-react";

const navItems = [
  { label: "Practice Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Device Test Studio", href: "/device-test", icon: Mic },
  { label: "Settings / Profile", href: "/settings", icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  function handleLogout() {
    localStorage.removeItem("auth_token");
    router.push("/login");
  }

  if (
    pathname?.startsWith("/interview") ||
    pathname?.startsWith("/practice") ||
    pathname?.startsWith("/login") ||
    pathname?.startsWith("/register")
  ) {
    return null;
  }

  return (
    <aside className="w-60 min-h-screen bg-slate-800 border-r border-slate-700 flex flex-col py-6 px-4 shrink-0">
      <div className="mb-8 px-2">
        <span className="text-zinc-100 font-semibold text-lg tracking-tight">
          Practice Portal
        </span>
      </div>
      <nav className="flex flex-col gap-1">
        {navItems.map(({ label, href, icon: Icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                active
                  ? "bg-indigo-500/20 text-indigo-400"
                  : "text-zinc-400 hover:bg-slate-700 hover:text-zinc-100"
              }`}
            >
              <Icon size={18} />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="mt-auto pt-4 border-t border-slate-700">
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm w-full text-zinc-400 hover:bg-slate-700 hover:text-zinc-100 transition-colors"
        >
          <LogOut size={18} />
          Logout
        </button>
      </div>
    </aside>
  );
}
