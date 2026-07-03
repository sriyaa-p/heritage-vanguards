"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

export default function Header() {
  const pathname = usePathname();
  const [role, setRole] = useState<string>("reporter");

  useEffect(() => {
    const saved = localStorage.getItem("user-role") || "reporter";
    setRole(saved);
  }, []);

  const handleRoleChange = (newRole: string) => {
    setRole(newRole);
    localStorage.setItem("user-role", newRole);
  };

  return (
    <header className="bg-slate-900 text-white border-b border-slate-800 sticky top-0 z-50 backdrop-blur-md bg-opacity-95 shadow-lg">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
        <Link href="/dashboard" className="flex items-center gap-2 group">
          <span className="text-xl">🛡️</span>
          <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-amber-400 to-orange-500 bg-clip-text text-transparent group-hover:from-amber-300 group-hover:to-orange-400 transition-all duration-300">
            Heritage Sentinel AI
          </span>
        </Link>

        {/* Navigation links based on role */}
        <nav className="hidden md:flex items-center gap-6 text-sm font-medium">
          <Link
            href="/dashboard"
            className={`transition-colors hover:text-amber-400 ${
              pathname === "/dashboard" ? "text-amber-400" : "text-slate-300"
            }`}
          >
            Dashboard
          </Link>

          {role === "reporter" && (
            <Link
              href="/submit"
              className={`transition-colors hover:text-amber-400 ${
                pathname === "/submit" ? "text-amber-400" : "text-slate-300"
              }`}
            >
              Submit Site
            </Link>
          )}

          {role === "reviewer" && (
            <Link
              href="/review"
              className={`transition-colors hover:text-amber-400 ${
                pathname.startsWith("/review") ? "text-amber-400" : "text-slate-300"
              }`}
            >
              Archaeologist Review Queue
            </Link>
          )}

          {role === "committee" && (
            <Link
              href="/committee"
              className={`transition-colors hover:text-amber-400 ${
                pathname.startsWith("/committee") ? "text-amber-400" : "text-slate-300"
              }`}
            >
              Committee Panel
            </Link>
          )}
        </nav>

        {/* Role Selector */}
        <div className="flex items-center gap-2 sm:gap-3">
          <span className="text-xs text-slate-400 hidden sm:inline font-mono">Role:</span>
          <div className="relative inline-block text-left">
            <select
              value={role}
              onChange={(e) => handleRoleChange(e.target.value)}
              className="bg-slate-800 border border-slate-700 text-slate-200 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-amber-500 font-medium transition cursor-pointer hover:bg-slate-700"
            >
              <option value="reporter">Reporter</option>
              <option value="reviewer">Archaeologist (Reviewer)</option>
              <option value="committee">UNESCO Committee</option>
            </select>
          </div>
        </div>
      </div>

      {/* Mobile nav indicator */}
      <div className="md:hidden bg-slate-800 px-4 py-2 flex items-center justify-around text-xs border-t border-slate-700/50">
        <Link
          href="/dashboard"
          className={`hover:text-amber-400 ${pathname === "/dashboard" ? "text-amber-400" : "text-slate-400"}`}
        >
          Dashboard
        </Link>
        {role === "reporter" && (
          <Link
            href="/submit"
            className={`hover:text-amber-400 ${pathname === "/submit" ? "text-amber-400" : "text-slate-400"}`}
          >
            Submit Site
          </Link>
        )}
        {role === "reviewer" && (
          <Link
            href="/review"
            className={`hover:text-amber-400 ${pathname.startsWith("/review") ? "text-amber-400" : "text-slate-400"}`}
          >
            Review Queue
          </Link>
        )}
        {role === "committee" && (
          <Link
            href="/committee"
            className={`hover:text-amber-400 ${pathname.startsWith("/committee") ? "text-amber-400" : "text-slate-400"}`}
          >
            Committee
          </Link>
        )}
      </div>
    </header>
  );
}
