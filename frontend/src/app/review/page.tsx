"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { API } from "@/lib/api";

const STATUS_COLOR: Record<string, string> = {
  verification: "bg-blue-100 text-blue-700",
  approved: "bg-green-100 text-green-700",
  rejected: "bg-red-100 text-red-700",
  evaluation: "bg-yellow-100 text-yellow-700",
  registry_check: "bg-purple-100 text-purple-700",
  pending: "bg-gray-100 text-gray-600",
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

export default function ReviewQueuePage() {
  const [items, setItems] = useState<QueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("verification");

  useEffect(() => {
    const fetchQueue = async () => {
      setLoading(true);
      try {
        const url = filter === "all"
          ? `${API}/submissions`
          : `${API}/submissions?status=${filter}`;
        const res = await fetch(url);
        const data = await res.json();
        const mapped: QueueItem[] = data.map((row: any) => ({
          submission_id: row.submission_id,
          location_name: row.location_name ?? "Unknown",
          country: row.country ?? "—",
          status: row.status,
          score: row.score ?? null,
          created_at: row.created_at,
        }));
        setItems(mapped);
      } catch {
        setItems([]);
      } finally {
        setLoading(false);
      }
    };
    fetchQueue();
  }, [filter]);

  const FILTERS = [
    { value: "verification", label: "Awaiting Review" },
    { value: "all",          label: "All Submissions" },
    { value: "approved",     label: "Approved" },
    { value: "rejected",     label: "Rejected" },
  ];

  return (
    <main className="min-h-screen bg-gray-50 p-4 sm:p-8">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Review Queue</h1>
            <p className="text-gray-500 text-sm">Click any row to view the Confidence Card and make a decision.</p>
          </div>
          <button onClick={() => window.location.reload()} className="text-xs text-gray-400 hover:text-gray-600 mt-1">Refresh</button>
        </div>

        {/* Filter tabs */}
        <div className="flex gap-2 mb-5 overflow-x-auto pb-1">
          {FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setFilter(f.value)}
              className={`shrink-0 text-xs px-3 py-1.5 rounded-full font-medium transition
                ${filter === f.value ? "bg-blue-600 text-white" : "bg-white text-gray-600 border hover:border-blue-400"}`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="text-center py-20">
            <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            <p className="text-gray-400 text-sm">Loading submissions…</p>
          </div>
        ) : items.length === 0 ? (
          <div className="text-center py-20 bg-white rounded-xl shadow">
            <p className="text-gray-400 text-sm">No submissions found for this filter.</p>
            {filter === "verification" && (
              <p className="text-gray-300 text-xs mt-1">Submissions appear here once the pipeline finishes evaluating.</p>
            )}
          </div>
        ) : (
          <>
            {/* Mobile: stacked cards */}
            <div className="flex flex-col gap-3 sm:hidden">
              {items.map((item) => (
                <div key={item.submission_id} className="bg-white rounded-xl shadow p-4">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1 min-w-0 mr-2">
                      <p className="font-medium text-gray-900 truncate">{item.location_name}</p>
                      <p className="text-xs text-gray-400">{item.country}</p>
                    </div>
                    <span className={`text-lg font-bold shrink-0 ${item.score !== null ? (item.score >= 80 ? "text-green-600" : item.score >= 60 ? "text-yellow-600" : "text-red-500") : "text-gray-400"}`}>
                      {item.score !== null ? `${item.score}/100` : "—"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLOR[item.status] ?? "bg-gray-100 text-gray-600"}`}>
                      {STATUS_LABEL[item.status] ?? item.status}
                    </span>
                    <Link href={`/review/${item.submission_id}`} className="text-blue-600 hover:underline text-sm font-medium">
                      View Card →
                    </Link>
                  </div>
                </div>
              ))}
            </div>

            {/* Desktop: table */}
            <div className="hidden sm:block bg-white rounded-xl shadow overflow-x-auto">
              <table className="w-full text-sm min-w-[480px]">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="text-left px-4 py-3 text-gray-600 font-medium">Site</th>
                    <th className="text-left px-4 py-3 text-gray-600 font-medium">Country</th>
                    <th className="text-left px-4 py-3 text-gray-600 font-medium">Score</th>
                    <th className="text-left px-4 py-3 text-gray-600 font-medium">Status</th>
                    <th className="px-4 py-3" />
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {items.map((item) => (
                    <tr key={item.submission_id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-medium text-gray-900">{item.location_name}</td>
                      <td className="px-4 py-3 text-gray-500">{item.country}</td>
                      <td className="px-4 py-3">
                        {item.score !== null ? (
                          <span className={`font-bold ${item.score >= 80 ? "text-green-600" : item.score >= 60 ? "text-yellow-600" : "text-red-500"}`}>
                            {item.score}/100
                          </span>
                        ) : <span className="text-gray-300">—</span>}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLOR[item.status] ?? "bg-gray-100 text-gray-600"}`}>
                          {STATUS_LABEL[item.status] ?? item.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Link href={`/review/${item.submission_id}`} className="text-blue-600 hover:underline text-xs">
                          View Card →
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </main>
  );
}
