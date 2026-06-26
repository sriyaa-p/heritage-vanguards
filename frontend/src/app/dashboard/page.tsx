"use client";
import { useEffect, useState } from "react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const STATUS_COLOR: Record<string, string> = {
  verification: "bg-blue-100 text-blue-700",
  approved: "bg-green-100 text-green-700",
  rejected: "bg-red-100 text-red-700",
  evaluation: "bg-yellow-100 text-yellow-700",
  registry_check: "bg-purple-100 text-purple-700",
  pending: "bg-gray-100 text-gray-600",
};

interface Stats {
  total: number;
  pending: number;
  registry_check: number;
  evaluation: number;
  in_review: number;
  approved: number;
  rejected: number;
  duplicates_blocked: number;
}

interface RecentItem {
  submission_id: string;
  location_name: string;
  country: string;
  status: string;
  score: number | null;
  created_at: string;
}

function StatCard({ label, value, color, loading }: { label: string; value: number; color: string; loading: boolean }) {
  return (
    <div className="bg-white rounded-xl shadow p-4 sm:p-5">
      <p className="text-xs sm:text-sm text-gray-500">{label}</p>
      {loading ? (
        <div className="h-8 w-12 bg-gray-100 animate-pulse rounded mt-1" />
      ) : (
        <p className={`text-2xl sm:text-3xl font-bold mt-1 ${color}`}>{value}</p>
      )}
    </div>
  );
}

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [recent, setRecent] = useState<RecentItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const [statsRes, listRes] = await Promise.all([
          fetch(`${API}/submissions/stats`),
          fetch(`${API}/submissions`),
        ]);
        const statsData = await statsRes.json();
        const listData = await listRes.json();

        setStats(statsData);

        // Enrich first 10 with scores
        const enriched = await Promise.all(
          listData.slice(0, 10).map(async (row: any) => {
            let score: number | null = null;
            try {
              const detail = await fetch(`${API}/submissions/${row.submission_id}`);
              const d = await detail.json();
              score = d.dossier?.scoring?.total ?? null;
            } catch { /* skip */ }
            return {
              submission_id: row.submission_id,
              location_name: row.location_name ?? "Unknown",
              country: row.country ?? "—",
              status: row.status,
              score,
              created_at: row.created_at,
            };
          })
        );
        setRecent(enriched);
      } catch {
        setStats(null);
      } finally {
        setLoading(false);
      }
    };
    fetchAll();
  }, []);

  return (
    <main className="min-h-screen bg-gray-50 p-4 sm:p-8">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Admin Dashboard</h1>
            <p className="text-gray-500 text-sm">Live queue overview and processing metrics.</p>
          </div>
          <button onClick={() => window.location.reload()} className="text-xs text-gray-400 hover:text-gray-600 mt-1">Refresh</button>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 sm:gap-4 mb-8">
          <StatCard label="Total Submissions" value={stats?.total ?? 0}             color="text-gray-900"    loading={loading} />
          <StatCard label="Awaiting Review"   value={stats?.in_review ?? 0}         color="text-blue-600"   loading={loading} />
          <StatCard label="In Pipeline"       value={(stats?.pending ?? 0) + (stats?.registry_check ?? 0) + (stats?.evaluation ?? 0)} color="text-yellow-600" loading={loading} />
          <StatCard label="Approved"          value={stats?.approved ?? 0}           color="text-green-600"  loading={loading} />
          <StatCard label="Rejected"          value={stats?.rejected ?? 0}           color="text-red-500"    loading={loading} />
          <StatCard label="Duplicates Blocked" value={stats?.duplicates_blocked ?? 0} color="text-purple-600" loading={loading} />
        </div>

        <div className="bg-white rounded-xl shadow overflow-hidden">
          <div className="px-4 sm:px-5 py-4 border-b flex items-center justify-between">
            <h2 className="font-semibold text-gray-900">Recent Submissions</h2>
            <Link href="/review" className="text-xs text-blue-600 hover:underline">View all →</Link>
          </div>

          {loading ? (
            <div className="p-8 text-center">
              <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
              <p className="text-gray-400 text-sm">Loading…</p>
            </div>
          ) : recent.length === 0 ? (
            <div className="p-8 text-center text-gray-400 text-sm">
              No submissions yet. <Link href="/submit" className="text-blue-600 hover:underline">Submit the first one →</Link>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm min-w-[480px]">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="text-left px-4 sm:px-5 py-3 text-gray-600 font-medium">Site</th>
                    <th className="text-left px-4 sm:px-5 py-3 text-gray-600 font-medium">Country</th>
                    <th className="text-left px-4 sm:px-5 py-3 text-gray-600 font-medium">Score</th>
                    <th className="text-left px-4 sm:px-5 py-3 text-gray-600 font-medium">Stage</th>
                    <th className="px-4 py-3" />
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {recent.map((item) => (
                    <tr key={item.submission_id} className="hover:bg-gray-50">
                      <td className="px-4 sm:px-5 py-3">
                        <p className="font-medium text-gray-900">{item.location_name}</p>
                        <p className="text-xs text-gray-400 font-mono">{item.submission_id}</p>
                      </td>
                      <td className="px-4 sm:px-5 py-3 text-gray-500">{item.country}</td>
                      <td className="px-4 sm:px-5 py-3">
                        {item.score !== null ? (
                          <span className={`font-bold ${item.score >= 80 ? "text-green-600" : item.score >= 60 ? "text-yellow-600" : "text-red-500"}`}>
                            {item.score}/100
                          </span>
                        ) : <span className="text-gray-300">—</span>}
                      </td>
                      <td className="px-4 sm:px-5 py-3">
                        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLOR[item.status] ?? "bg-gray-100 text-gray-600"}`}>
                          {item.status.replace(/_/g, " ")}
                        </span>
                      </td>
                      <td className="px-4 sm:px-5 py-3 text-right">
                        <Link href={`/review/${item.submission_id}`} className="text-blue-600 hover:underline text-xs">
                          View →
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
