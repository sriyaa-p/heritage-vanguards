"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { API } from "@/lib/api";

interface Stats {
  total: number;
  pending: number;
  registry_check: number;
  evaluation: number;
  in_review: number;
  reviewer_review: number;
  committee_review: number;
  approved: number;
  rejected: number;
  duplicates_blocked: number;
}

interface CommitteeQueueItem {
  submission_id: string;
  location_name: string;
  country: string;
  status: string;
  score: number | null;
  created_at: string;
}

interface AuditLogItem {
  submission_id: string;
  status: string;
  location_name: string;
  country: string;
  score: number | null;
  reviewer_notes?: string;
  committee_comments?: string;
  updated_at: string;
}

export default function CommitteeDashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [pendingItems, setPendingItems] = useState<CommitteeQueueItem[]>([]);
  const [auditItems, setAuditItems] = useState<AuditLogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"pending" | "audit">("pending");

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        // Fetch stats
        const statsRes = await fetch(`${API}/submissions/stats`);
        if (!statsRes.ok) throw new Error(`Stats fetch failed: ${statsRes.status}`);
        const statsData = await statsRes.json();
        setStats(statsData);

        // Fetch pending items (committee_review)
        const pendingRes = await fetch(`${API}/submissions?status=committee_review`);
        if (!pendingRes.ok) throw new Error(`Pending fetch failed: ${pendingRes.status}`);
        const pendingData = await pendingRes.json();
        // Backward-compatible: API may return paginated object {items, total, ...}
        // or flat array (legacy). Handle both.
        const rows = Array.isArray(pendingData) ? pendingData : pendingData?.items ?? [];
        setPendingItems(rows.map((row: any) => ({
          submission_id: row.submission_id,
          location_name: row.location_name ?? "Unknown",
          country: row.country ?? "—",
          status: row.status,
          score: row.score ?? null,
          created_at: row.created_at,
        })));

        // Fetch audit log items
        const auditRes = await fetch(`${API}/submissions/audit-log`);
        if (!auditRes.ok) throw new Error(`Audit log fetch failed: ${auditRes.status}`);
        const auditData = await auditRes.json();
        setAuditItems(auditData);
      } catch (err) {
        console.error("Failed to fetch committee data", err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return (
      <main className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-amber-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-gray-500 text-sm">Loading Committee Dashboard…</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-50 to-gray-100 py-8 px-4 sm:px-6">
      <div className="max-w-6xl mx-auto space-y-6">
        
        {/* Title */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">UNESCO World Heritage Committee</h1>
            <p className="text-gray-500 text-sm mt-1">Final designation panel and historical decision ledger.</p>
          </div>
          <button 
            onClick={() => window.location.reload()} 
            className="text-xs bg-white border rounded-lg px-3 py-1.5 font-medium hover:bg-gray-50 transition shadow-sm text-slate-600"
          >
            Refresh
          </button>
        </div>

        {/* Stats Grid */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white rounded-2xl shadow-sm border border-gray-200/60 p-5">
              <span className="text-2xl">🏛️</span>
              <p className="text-xs text-gray-500 mt-2 font-medium">Designated Sites</p>
              <p className="text-2xl font-black text-slate-900 mt-1">{stats.approved}</p>
            </div>
            <div className="bg-white rounded-2xl shadow-sm border border-gray-200/60 p-5">
              <span className="text-2xl">⚖️</span>
              <p className="text-xs text-gray-500 mt-2 font-medium">Pending Final Decision</p>
              <p className="text-2xl font-black text-amber-600 mt-1">{stats.committee_review}</p>
            </div>
            <div className="bg-white rounded-2xl shadow-sm border border-gray-200/60 p-5">
              <span className="text-2xl">⚡</span>
              <p className="text-xs text-gray-500 mt-2 font-medium">Pipeline Volume</p>
              <p className="text-2xl font-black text-blue-600 mt-1">{stats.total}</p>
            </div>
            <div className="bg-white rounded-2xl shadow-sm border border-gray-200/60 p-5">
              <span className="text-2xl">🛡️</span>
              <p className="text-xs text-gray-500 mt-2 font-medium">Auto-Blocks (Duplicates)</p>
              <p className="text-2xl font-black text-red-600 mt-1">{stats.duplicates_blocked}</p>
            </div>
          </div>
        )}

        {/* Tabs and Table container */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200/60 overflow-hidden">
          {/* Tab headers */}
          <div className="flex border-b border-gray-200 bg-gray-50/50">
            <button
              onClick={() => setActiveTab("pending")}
              className={`px-6 py-4 text-sm font-bold border-b-2 transition-all
                ${activeTab === "pending" ? "border-amber-500 text-amber-700 bg-white" : "border-transparent text-gray-500 hover:text-slate-800"}`}
            >
              Pending Committee Reviews ({pendingItems.length})
            </button>
            <button
              onClick={() => setActiveTab("audit")}
              className={`px-6 py-4 text-sm font-bold border-b-2 transition-all
                ${activeTab === "audit" ? "border-amber-500 text-amber-700 bg-white" : "border-transparent text-gray-500 hover:text-slate-800"}`}
            >
              System Decision Ledger ({auditItems.length})
            </button>
          </div>

          {/* Tab content */}
          <div className="p-6">
            {activeTab === "pending" ? (
              pendingItems.length === 0 ? (
                <div className="text-center py-12">
                  <span className="text-4xl">🎉</span>
                  <h3 className="text-sm font-bold text-slate-900 mt-2">All Caught Up!</h3>
                  <p className="text-gray-400 text-xs mt-1">There are no recommended candidate sites awaiting final UNESCO Committee designation.</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-left">
                    <thead className="bg-slate-50 text-slate-600 text-xs uppercase font-bold border-b">
                      <tr>
                        <th className="px-4 py-3">Site Name</th>
                        <th className="px-4 py-3">Country</th>
                        <th className="px-4 py-3">Heritage Score</th>
                        <th className="px-4 py-3 text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {pendingItems.map((item) => (
                        <tr key={item.submission_id} className="hover:bg-slate-50/50">
                          <td className="px-4 py-4 font-bold text-slate-900">{item.location_name}</td>
                          <td className="px-4 py-4 text-slate-600">{item.country}</td>
                          <td className="px-4 py-4">
                            {item.score !== null ? (
                              <span className={`font-extrabold ${item.score >= 80 ? "text-green-600" : item.score >= 60 ? "text-yellow-600" : "text-red-500"}`}>
                                {item.score}/100
                              </span>
                            ) : <span className="text-gray-300">—</span>}
                          </td>
                          <td className="px-4 py-4 text-right">
                            <Link 
                              href={`/committee/review/${item.submission_id}`} 
                              className="inline-flex items-center justify-center bg-amber-500 hover:bg-amber-600 text-white text-xs font-bold px-3 py-1.5 rounded-lg transition shadow-sm"
                            >
                              Final Review
                            </Link>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )
            ) : (
              auditItems.length === 0 ? (
                <div className="text-center py-12">
                  <span className="text-4xl">📋</span>
                  <h3 className="text-sm font-bold text-slate-900 mt-2">Ledger is Empty</h3>
                  <p className="text-gray-400 text-xs mt-1">No historical decisions have been recorded yet.</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-left">
                    <thead className="bg-slate-50 text-slate-600 text-xs uppercase font-bold border-b">
                      <tr>
                        <th className="px-4 py-3">Site Name</th>
                        <th className="px-4 py-3">Country</th>
                        <th className="px-4 py-3">Outcome</th>
                        <th className="px-4 py-3">Score</th>
                        <th className="px-4 py-3">Reviewer / Committee Notes</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {auditItems.map((item) => {
                        const approved = item.status === "approved";
                        const rejected = item.status === "rejected";
                        return (
                          <tr key={item.submission_id} className="hover:bg-slate-50/50">
                            <td className="px-4 py-4 font-bold text-slate-900">
                              <div>
                                <p>{item.location_name}</p>
                                <span className="text-[10px] text-slate-400 font-mono">{item.submission_id}</span>
                              </div>
                            </td>
                            <td className="px-4 py-4 text-slate-600">{item.country}</td>
                            <td className="px-4 py-4">
                              <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase
                                ${approved ? "bg-green-100 text-green-800" : rejected ? "bg-red-100 text-red-800" : "bg-amber-100 text-amber-800"}`}>
                                {item.status}
                              </span>
                            </td>
                            <td className="px-4 py-4">
                              {item.score !== null ? (
                                <span className="font-bold text-slate-700">{item.score}/100</span>
                              ) : <span className="text-gray-300">—</span>}
                            </td>
                            <td className="px-4 py-4 max-w-xs truncate text-xs text-slate-500">
                              {item.committee_comments ? (
                                <span><strong className="text-slate-700">Committee:</strong> {item.committee_comments}</span>
                              ) : item.reviewer_notes ? (
                                <span><strong className="text-slate-700">Reviewer:</strong> {item.reviewer_notes}</span>
                              ) : <span className="text-gray-300">No notes recorded</span>}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )
            )}
          </div>
        </div>

      </div>
    </main>
  );
}
