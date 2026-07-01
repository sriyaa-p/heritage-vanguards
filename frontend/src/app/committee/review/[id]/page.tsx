"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { API } from "@/lib/api";

const SCORE_CATEGORIES = [
  { key: "historic_features",     label: "Historic Features",     max: 25 },
  { key: "cultural_significance",  label: "Cultural Significance",  max: 20 },
  { key: "integrity",             label: "Integrity",             max: 15 },
  { key: "authenticity",          label: "Authenticity",          max: 15 },
  { key: "geographic_context",    label: "Geographic Context",    max: 10 },
  { key: "documentation",         label: "Documentation Quality", max: 10 },
  { key: "management_protection", label: "Management & Protection", max: 5 },
  { key: "supporting_evidence",   label: "Supporting Evidence",   max: 15 },
];

function ScoreBar({ score, max }: { score: number; max: number }) {
  const pct = Math.min(Math.round((score / max) * 100), 100);
  const color = pct >= 80 ? "bg-green-500" : pct >= 60 ? "bg-yellow-400" : "bg-red-400";
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 bg-gray-100 rounded-full h-2 overflow-hidden">
        <div className={`${color} h-2 rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono w-12 text-right text-gray-600">{score}/{max}</span>
    </div>
  );
}

export default function CommitteeReviewPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const [dossier, setDossier] = useState<any>(null);
  const [status, setStatus] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [comments, setComments] = useState("");
  const [deciding, setDeciding] = useState(false);
  const [finalDecision, setFinalDecision] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    const fetchData = async () => {
      try {
        const res = await fetch(`${API}/submissions/${id}`);
        if (!res.ok) throw new Error("Not found");
        const data = await res.json();
        setDossier(data.dossier);
        setStatus(data.status);
      } catch {
        setDossier(null);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [id]);

  async function handleFinalize(decision: "approved" | "rejected") {
    setDeciding(true);
    try {
      const res = await fetch(`${API}/submissions/${id}/finalize`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision, comments, committee_id: "committee" }),
      });
      if (!res.ok) throw new Error(`Server error: ${res.status}`);
      setFinalDecision(decision);
    } catch {
      alert("Failed to record committee decision. Please try again.");
    } finally {
      setDeciding(false);
    }
  }

  if (loading) {
    return (
      <main className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-amber-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-gray-500 text-sm">Loading dossier for committee review…</p>
        </div>
      </main>
    );
  }

  if (!dossier) {
    return (
      <main className="min-h-screen bg-gray-50 flex items-center justify-center p-8">
        <div className="text-center">
          <p className="text-2xl mb-2">404</p>
          <p className="text-gray-500 mb-4">Submission not found</p>
          <button onClick={() => router.push("/committee")} className="text-blue-600 hover:underline text-sm">← Back to committee dashboard</button>
        </div>
      </main>
    );
  }

  if (finalDecision) {
    return (
      <main className="min-h-screen bg-gray-50 flex items-center justify-center p-8">
        <div className="bg-white rounded-xl shadow p-8 max-w-md w-full text-center">
          <div className="text-5xl mb-4">{finalDecision === "approved" ? "🏛️" : "❌"}</div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2 capitalize">{finalDecision === "approved" ? "Approved & Designated" : "Rejected"}</h2>
          <p className="text-gray-500">{dossier.metadata?.location_name} has been officially {finalDecision === "approved" ? "designated as a World Heritage Site" : "rejected"}.</p>
          <button onClick={() => router.push("/committee")} className="mt-6 text-blue-600 hover:underline text-sm">← Back to committee dashboard</button>
        </div>
      </main>
    );
  }

  const meta = dossier.metadata ?? {};
  const evidence = dossier.extracted_evidence ?? {};
  const scoring = dossier.scoring ?? {};
  const raw = dossier.raw_evidence ?? {};
  const photos: string[] = raw.photo_urls ?? [];
  const totalScore: number = scoring.total ?? 0;
  const confidence = totalScore >= 80 ? "High" : totalScore >= 60 ? "Moderate" : "Low";
  const confidenceColor = confidence === "High" ? "text-green-600" : confidence === "Moderate" ? "text-yellow-600" : "text-red-500";
  const alreadyDecided = ["approved", "rejected"].includes(status);

  return (
    <main className="min-h-screen bg-gray-50 p-6 sm:p-8">
      <div className="max-w-2xl mx-auto space-y-5">

        {/* Top Header Card */}
        <div className="bg-white rounded-xl shadow p-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <span className="text-xs font-semibold tracking-wider text-amber-600 uppercase">UNESCO Committee Console</span>
              <h1 className="text-2xl font-bold text-gray-900 mt-1">{meta.location_name ?? "Unknown Site"}</h1>
              <p className="text-gray-500 text-sm">{meta.country} · <span className="font-mono">{meta.submission_id}</span></p>
            </div>
            <div className="text-right shrink-0">
              <p className="text-4xl font-bold text-gray-900">{totalScore}<span className="text-lg text-gray-400">/100</span></p>
              <p className={`text-sm font-semibold ${confidenceColor}`}>{confidence} Confidence</p>
            </div>
          </div>
        </div>

        {/* Archaeologist Recommendation notes */}
        {dossier.review && (
          <div className="bg-gradient-to-br from-amber-500/5 to-orange-500/5 border border-amber-500/20 rounded-xl p-5 space-y-2">
            <h3 className="text-sm font-bold text-amber-900 flex items-center gap-1.5">
              <span>👤</span> Archaeologist Recommendation Notes
            </h3>
            <p className="text-xs text-slate-700 leading-relaxed italic bg-white/60 p-3 rounded-lg border border-amber-500/5">
              "{dossier.review.reviewer_notes || "Recommended for designation."}"
            </p>
            <p className="text-[10px] text-gray-400 text-right">Recommended by: {dossier.review.reviewer_id || "reviewer"}</p>
          </div>
        )}

        {/* Photos */}
        {photos.length > 0 && (
          <div className="bg-white rounded-xl shadow p-6">
            <h2 className="font-semibold text-gray-900 mb-3">Submission Photos</h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {photos.map((url, i) => (
                <img
                  key={i}
                  src={url.startsWith("/") ? `${API}${url}` : url}
                  alt={`Site photo ${i + 1}`}
                  className="rounded-lg object-cover w-full h-32 bg-gray-100"
                />
              ))}
            </div>
          </div>
        )}

        {/* Score Breakdown */}
        {scoring.total !== undefined && (
          <div className="bg-white rounded-xl shadow p-6">
            <h2 className="font-semibold text-gray-900 mb-4">Heritage Score Breakdown</h2>
            <div className="space-y-3">
              {SCORE_CATEGORIES.map(({ key, label, max }) => (
                <div key={key}>
                  <div className="flex justify-between text-sm text-gray-600 mb-1">
                    <span>{label}</span>
                  </div>
                  <ScoreBar score={(scoring as Record<string, number>)[key] ?? 0} max={max} />
                </div>
              ))}
            </div>
            {scoring.rationale && (
              <div className="mt-4 p-3 bg-gray-50 rounded-lg text-sm text-gray-600 italic">
                {scoring.rationale}
              </div>
            )}
          </div>
        )}

        {/* Evidence Summary */}
        {evidence.historic_features && (
          <div className="bg-white rounded-xl shadow p-6">
            <h2 className="font-semibold text-gray-900 mb-3">Evidence Summary</h2>
            <div className="space-y-3 text-sm text-gray-700">
              <p><span className="font-medium">Historic Features:</span> {evidence.historic_features}</p>
              <p><span className="font-medium">Cultural Significance:</span> {evidence.cultural_significance}</p>
              <p><span className="font-medium">Integrity:</span> {evidence.integrity}</p>
              <p><span className="font-medium">Authenticity:</span> {evidence.authenticity}</p>
              <p><span className="font-medium">Geographic Context:</span> {evidence.geographic_context}</p>
              <p><span className="font-medium">Documentation Quality:</span> {evidence.documentation_quality}</p>
              <p><span className="font-medium">Management & Protection:</span> {evidence.management_protection}</p>
              <p><span className="font-medium">Supporting Evidence:</span> {evidence.supporting_evidence}</p>
            </div>
          </div>
        )}

        {/* Committee Final Decision */}
        {alreadyDecided ? (
          <div className="bg-white rounded-xl shadow p-6 text-center space-y-3">
            <p className="text-sm text-gray-500">
              This submission has already been <span className={`font-semibold capitalize ${status === "approved" ? "text-green-600" : "text-red-600"}`}>{status === "approved" ? "Approved" : "Rejected"}</span>.
            </p>
            {dossier.committee_review?.committee_comments && (
              <div className="p-3 bg-gray-50 rounded text-left text-xs text-gray-600 italic">
                <p className="font-bold text-slate-700 not-italic mb-1">Committee Comments:</p>
                "{dossier.committee_review.committee_comments}"
              </div>
            )}
            <button onClick={() => router.push("/committee")} className="mt-3 text-blue-600 hover:underline text-sm">← Back to committee dashboard</button>
          </div>
        ) : (
          <div className="bg-white rounded-xl shadow p-6">
            <h2 className="font-semibold text-gray-900 mb-3">Committee Final Designation Decision</h2>
            <textarea
              className="w-full border rounded-lg px-3 py-2 text-sm mb-4 focus:outline-none focus:ring-2 focus:ring-amber-500"
              rows={3}
              placeholder="Enter optional committee comments / designation decree..."
              value={comments}
              onChange={(e) => setComments(e.target.value)}
              disabled={deciding}
            />
            <div className="flex gap-3">
              <button
                onClick={() => handleFinalize("approved")}
                disabled={deciding}
                className="flex-1 bg-green-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-green-700 transition disabled:opacity-50"
              >
                {deciding ? "Saving…" : "Designate Site (Approve)"}
              </button>
              <button
                onClick={() => handleFinalize("rejected")}
                disabled={deciding}
                className="flex-1 bg-red-500 text-white rounded-lg py-2 text-sm font-medium hover:bg-red-600 transition disabled:opacity-50"
              >
                {deciding ? "Saving…" : "Decline (Reject)"}
              </button>
            </div>
          </div>
        )}

      </div>
    </main>
  );
}
