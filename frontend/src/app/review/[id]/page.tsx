"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const SCORE_CATEGORIES = [
  { key: "historic_features",    label: "Historic Features",    max: 30 },
  { key: "cultural_significance", label: "Cultural Significance", max: 25 },
  { key: "geographic_context",   label: "Geographic Context",   max: 15 },
  { key: "documentation",        label: "Documentation",        max: 15 },
  { key: "supporting_evidence",  label: "Supporting Evidence",  max: 15 },
];

const STATUS_LABEL: Record<string, string> = {
  pending: "Queued",
  registry_check: "Registry Check",
  evaluation: "AI Evaluation",
  verification: "Awaiting Review",
  approved: "Approved",
  rejected: "Rejected",
};

function ScoreBar({ score, max }: { score: number; max: number }) {
  const pct = Math.round((score / max) * 100);
  const color = pct >= 80 ? "bg-green-500" : pct >= 60 ? "bg-yellow-400" : "bg-red-400";
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 bg-gray-100 rounded-full h-2">
        <div className={`${color} h-2 rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono w-12 text-right text-gray-600">{score}/{max}</span>
    </div>
  );
}

export default function ConfidenceCardPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const [dossier, setDossier] = useState<any>(null);
  const [status, setStatus] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [notes, setNotes] = useState("");
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

  async function handleDecision(decision: "approved" | "rejected") {
    setDeciding(true);
    try {
      await fetch(`${API}/submissions/${id}/review?decision=${decision}&notes=${encodeURIComponent(notes)}`, {
        method: "PATCH",
      });
      setFinalDecision(decision);
    } catch {
      alert("Failed to submit decision. Please try again.");
    } finally {
      setDeciding(false);
    }
  }

  if (loading) {
    return (
      <main className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-gray-500 text-sm">Loading dossier…</p>
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
          <button onClick={() => router.push("/review")} className="text-blue-600 hover:underline text-sm">← Back to queue</button>
        </div>
      </main>
    );
  }

  if (finalDecision) {
    return (
      <main className="min-h-screen bg-gray-50 flex items-center justify-center p-8">
        <div className="bg-white rounded-xl shadow p-8 max-w-md w-full text-center">
          <div className="text-5xl mb-4">{finalDecision === "approved" ? "✅" : "❌"}</div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2 capitalize">{finalDecision}</h2>
          <p className="text-gray-500">{dossier.metadata?.location_name} has been {finalDecision}.</p>
          <button onClick={() => router.push("/review")} className="mt-6 text-blue-600 hover:underline text-sm">← Back to review queue</button>
        </div>
      </main>
    );
  }

  // Pipeline still running
  if (["pending", "registry_check", "evaluation"].includes(status)) {
    return (
      <main className="min-h-screen bg-gray-50 flex items-center justify-center p-8">
        <div className="bg-white rounded-xl shadow p-8 max-w-md w-full text-center">
          <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <h2 className="text-lg font-bold text-gray-900 mb-2">Pipeline in progress</h2>
          <p className="text-gray-500 text-sm">Stage: <span className="font-medium">{STATUS_LABEL[status] ?? status}</span></p>
          <p className="text-xs text-gray-400 mt-1">This page will be ready when evaluation completes.</p>
          <p className="text-xs font-mono bg-gray-100 rounded p-2 mt-4">{id}</p>
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

        {/* Header */}
        <div className="bg-white rounded-xl shadow p-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{meta.location_name ?? "Unknown Site"}</h1>
              <p className="text-gray-500 text-sm">{meta.country} · <span className="font-mono">{meta.submission_id}</span></p>
              {raw.language_detected && raw.language_detected !== "en" && (
                <span className="mt-1 inline-block text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full">
                  Translated from {raw.language_detected.toUpperCase()}
                </span>
              )}
            </div>
            <div className="text-right shrink-0">
              <p className="text-4xl font-bold text-gray-900">{totalScore}<span className="text-lg text-gray-400">/100</span></p>
              <p className={`text-sm font-semibold ${confidenceColor}`}>{confidence}</p>
            </div>
          </div>
        </div>

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
              <p><span className="font-medium">Geographic Context:</span> {evidence.geographic_context}</p>
              <p><span className="font-medium">Documentation:</span> {evidence.documentation_quality}</p>
              <p><span className="font-medium">Supporting Evidence:</span> {evidence.supporting_evidence}</p>
            </div>
          </div>
        )}

        {/* Registry Check */}
        {dossier.registry_check && (
          <div className="bg-white rounded-xl shadow p-6">
            <h2 className="font-semibold text-gray-900 mb-2">Registry Check</h2>
            <div className="flex items-center gap-2 text-sm">
              <span className={`w-2 h-2 rounded-full ${dossier.registry_check.is_duplicate ? "bg-red-500" : "bg-green-500"}`} />
              <span>{dossier.registry_check.is_duplicate ? `Duplicate of ${dossier.registry_check.matched_site}` : "No duplicate found in UNESCO registry"}</span>
            </div>
          </div>
        )}

        {/* Reviewer Decision */}
        {alreadyDecided ? (
          <div className="bg-white rounded-xl shadow p-6 text-center">
            <p className="text-sm text-gray-500">This submission has already been <span className="font-semibold capitalize">{status}</span>.</p>
            <button onClick={() => router.push("/review")} className="mt-3 text-blue-600 hover:underline text-sm">← Back to review queue</button>
          </div>
        ) : (
          <div className="bg-white rounded-xl shadow p-6">
            <h2 className="font-semibold text-gray-900 mb-3">Reviewer Decision</h2>
            <textarea
              className="w-full border rounded-lg px-3 py-2 text-sm mb-4 focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={3}
              placeholder="Optional notes..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              disabled={deciding}
            />
            <div className="flex gap-3">
              <button
                onClick={() => handleDecision("approved")}
                disabled={deciding}
                className="flex-1 bg-green-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-green-700 transition disabled:opacity-50"
              >
                {deciding ? "Saving…" : "Approve"}
              </button>
              <button
                onClick={() => handleDecision("rejected")}
                disabled={deciding}
                className="flex-1 bg-red-500 text-white rounded-lg py-2 text-sm font-medium hover:bg-red-600 transition disabled:opacity-50"
              >
                {deciding ? "Saving…" : "Reject"}
              </button>
            </div>
          </div>
        )}

      </div>
    </main>
  );
}
