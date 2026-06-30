"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { API } from "@/lib/api";

// Polished color palette for a professional look
const STATUS_STYLES: Record<string, string> = {
  verification: "bg-blue-50 text-blue-700 border-blue-200",
  approved: "bg-emerald-50 text-emerald-700 border-emerald-200",
  rejected: "bg-rose-50 text-rose-700 border-rose-200",
  evaluation: "bg-amber-50 text-amber-700 border-amber-200",
  registry_check: "bg-violet-50 text-violet-700 border-violet-200",
  pending: "bg-slate-50 text-slate-600 border-slate-200",
};

const STATUS_LABEL: Record<string, string> = {
  verification: "Awaiting Review",
  approved: "Approved",
  rejected: "Rejected",
  evaluation: "Evaluating",
  registry_check: "Registry Check",
  pending: "Queued",
};

interface QueueItem {
  submission_id: string;
  location_name: string;
  country: string;
  status: string;
  score: number | null;
  created_at: string;
}

function ReviewQueueContent() {
  const searchParams = useSearchParams();
  const [items, setItems] = useState<QueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState(searchParams.get("status") ?? "verification");

  useEffect(() => {
    const fetchQueue = async () => {
      setLoading(true);
      const url = filter === "all" ? `${API}/submissions` : `${API}/submissions?status=${filter}`;
      try {
        const res = await fetch(url);
        const data = await res.json();
        setItems(data.map((row: any) => ({
          submission_id: row.submission_id,
          location_name: row.location_name ?? "Unknown Site",
          country: row.country ?? "—",
          status: row.status,
          score: row.score ?? null,
          created_at: row.created_at,
        })));
      } catch { setItems([]); } finally { setLoading(false); }
    };
    fetchQueue();
  }, [filter]);

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-end border-b pb-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Review Queue</h1>
          <p className="text-slate-500 mt-1">Manage and verify pending cultural heritage nominations.</p>
        </div>
        <button onClick={() => window.location.reload()} className="text-sm text-slate-400 hover:text-blue-600 transition">Refresh Data</button>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2">
        {["verification", "all", "approved", "rejected"].map((f) => (
          <button key={f} onClick={() => setFilter(f)} 
            className={`px-4 py-2 rounded-lg text-sm font-medium transition ${filter === f ? "bg-blue-600 text-white shadow-md" : "bg-white border text-slate-600 hover:border-blue-300"}`}>
            {STATUS_LABEL[f] || "All Submissions"}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="bg-white rounded-2xl border shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-slate-400">Loading pipeline data...</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50">
              <tr className="text-left text-slate-500">
                <th className="px-6 py-4 font-medium">Site Location</th>
                <th className="px-6 py-4 font-medium">Country</th>
                <th className="px-6 py-4 font-medium">Heritage Score</th>
                <th className="px-6 py-4 font-medium">Pipeline Status</th>
                <th className="px-6 py-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {items.map((item) => (
                <tr key={item.submission_id} className="hover:bg-slate-50/50 transition">
                  <td className="px-6 py-4 font-semibold text-slate-900">{item.location_name}</td>
                  <td className="px-6 py-4 text-slate-600">{item.country}</td>
                  <td className="px-6 py-4">
                    {item.score !== null ? (
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                          <div className={`h-full ${item.score >= 80 ? "bg-emerald-500" : "bg-amber-400"}`} style={{ width: `${item.score}%` }} />
                        </div>
                        <span className="font-mono font-bold text-slate-700">{item.score}</span>
                      </div>
                    ) : <span className="text-slate-300 italic">Pending</span>}
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2.5 py-1 rounded-full text-xs font-semibold border ${STATUS_STYLES[item.status] || ""}`}>
                      {STATUS_LABEL[item.status] || item.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <Link href={`/review/${item.submission_id}`} className="text-blue-600 hover:text-blue-800 font-bold">Review →</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

export const dynamic = "force-dynamic";

export default function ReviewQueuePage() {
  return (
    <Suspense
      fallback={
        <main className="min-h-screen bg-gray-50 p-4 sm:p-8">
          <div className="max-w-3xl mx-auto text-center py-20">
            <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            <p className="text-gray-400 text-sm">Loading review queue…</p>
          </div>
        </main>
      }
    >
      <ReviewQueueContent />
    </Suspense>
  );
}
