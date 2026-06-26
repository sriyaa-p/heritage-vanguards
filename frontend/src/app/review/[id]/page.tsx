"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const SCORE_CATEGORIES = [
  { key: "historic_features",   label: "Historic Features",   max: 30 },
  { key: "cultural_significance", label: "Cultural Significance", max: 25 },
  { key: "geographic_context",  label: "Geographic Context",  max: 15 },
  { key: "documentation",       label: "Documentation",       max: 15 },
  { key: "supporting_evidence", label: "Supporting Evidence", max: 15 },
];

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
  const [loading, setLoading] = useState(true);
  const [decision, setDecision] = useState<"approved" | "rejected" | null>(null);
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`${API}/submissions/${id}`);
        if (!res.ok) throw new Error("Not found");
        const data = await res.json();
        setDossier(data.dossier);
      } catch {
        setDossier(null);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  async function handleDecision(d: "approved" | "rejected") {
    setSubmitting(true);
    try {
      await fetch(`${API}/submissions/${id}/review?decision=${d}&notes=${encodeURIComponent(notes)}&reviewer_id=archaeologist`, {
        method: "PATCH",
      });
      setDecision(d);
    } catch {
      setDecision(d); // optimistic for demo
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <main className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-400 text-sm animate-pulse">Loading Confidence Card...</p>
      </main>
    );
  }

  if (!dossier) {
    return (
      <main className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-500 mb-4">Submission not found.</p>
          <button onClick={() => router.push("/review")} className="text-blue-600 hover:underline text-sm">← Back to queue</button>
        </div>
      </main>
    );
  }

  if (decision) {
    return (
      <main className="min-h-screen bg-gray-50 flex items-center justify-center p-8">
        <div className="bg-white rounded-xl shadow p-8 max-w-md w-full text-center">
          <div className="text-5xl mb-4">{decision === "approved" ? "✅" : "❌"}</div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2 capitalize">{decision}</h2>
          <p className="text-gray-500 mb-6">{dossier.metadata?.location_name} has been {decision}.</p>
          <button onClick={() => router.push("/review")} className="text-blue-600 hover:underline text-sm">← Back to queue</button>
        </div>
      </main>
    );
  }

  const meta = dossier.metadata || {};
  const scoring = dossier.scoring || {};
  const evidence = dossier.extracted_evidence || {};
  const photos: string[] = dossier.raw_evidence?.photo_urls || [];
  const totalScore = scoring.total ?? 0;
  const confidence = totalScore >= 80 ? "High Confidence" : totalScore >= 60 ? "Moderate Confidence" : "Low Confidence";
  const confidenceColor = totalScore >= 80 ? "text-green-600" : totalScore >= 60 ? "text-yellow-600" : "text-red-500";
  const lang = dossier.raw_evidence?.language_detected;
  const translated = dossier.raw_evidence?.translated_description;

  return (
    <main className="min-h-screen bg-gray-50 p-4 sm:p-8">
      <div className="max-w-2xl mx-auto space-y-4">

        <button onClick={() => router.push("/review")} className="text-blue-600 hover:underline text-sm">← Back to queue</button>

        {/* Header */}
        <div className="bg-white rounded-xl shadow p-5 sm:p-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h1 className="text-xl sm:text-2xl font-bold text-gray-900">{meta.location_name}</h1>
              <p className="text-gray-500 text-sm">{meta.country} · {meta.submission_id}</p>
              {lang && lang !== "en" && lang !== "unknown" && (
                <span className="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full mt-1 inline-block">
                  Translated from {lang.toUpperCase()}
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
          <div className="bg-white rounded-xl shadow p-5">
            <h2 className="font-semibold text-gray-900 mb-3">Submitted Photos</h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {photos.map((url, i) => (
                <img
                  key={i}
                  src={url.startsWith("/") ? `${API}${url}` : url}
                  alt={`Photo ${i + 1}`}
                  className="w-full h-32 object-cover rounded-lg bg-gray-100"
                  onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                />
              ))}
            </div>
          </div>
        )}

        {/* Score breakdown */}
        <div className="bg-white rounded-xl shadow p-5 sm:p-6">
          <h2 className="font-semibold text-gray-900 mb-4">Heritage Score Breakdown</h2>
          <div className="space-y-3">
            {SCORE_CATEGORIES.map(({ key, label, max }) => (
              <div key={key}>
                <p className="text-sm text-gray-600 mb-1">{label}</p>
                <ScoreBar score={(scoring as Record<string, number>)[key] ?? 0} max={max} />
              </div>
            ))}
          </div>
        </div>

        {/* Evidence summary */}
        {Object.values(evidence).some(Boolean) && (
          <div className="bg-white rounded-xl shadow p-5 sm:p-6">
            <h2 className="font-semibold text-gray-900 mb-3">Evidence Summary</h2>
            {lang && lang !== "en" && lang !== "unknown" && translated && (
              <div className="mb-3 p-3 bg-blue-50 rounded-lg text-sm text-blue-700">
                <span className="font-medium">Translated description:</span> {translated}
              </div>
            )}
            <div className="space-y-3 text-sm text-gray-700">
              {evidence.historic_features && <p><span className="font-medium">Historic Features:</span> {evidence.historic_features}</p>}
              {evidence.cultural_significance && <p><span className="font-medium">Cultural Significance:</span> {evidence.cultural_significance}</p>}
              {evidence.geographic_context && <p><span className="font-medium">Geographic Context:</span> {evidence.geographic_context}</p>}
              {evidence.documentation_quality && <p><span className="font-medium">Documentation:</span> {evidence.documentation_quality}</p>}
              {evidence.supporting_evidence && <p><span className="font-medium">Supporting Evidence:</span> {evidence.supporting_evidence}</p>}
            </div>
            {scoring.rationale && (
              <div className="mt-4 p-3 bg-gray-50 rounded-lg text-sm text-gray-600 italic">
                {scoring.rationale}
              </div>
            )}
          </div>
        )}

        {/* Reviewer decision */}
        <div className="bg-white rounded-xl shadow p-5 sm:p-6">
          <h2 className="font-semibold text-gray-900 mb-3">Reviewer Decision</h2>
          <textarea
            className="w-full border rounded-lg px-3 py-2 text-sm mb-4 focus:outline-none focus:ring-2 focus:ring-blue-500"
            rows={3}
            placeholder="Optional notes..."
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
          <div className="flex gap-3">
            <button
              onClick={() => handleDecision("approved")}
              disabled={submitting}
              className="flex-1 bg-green-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-green-700 transition disabled:opacity-50"
            >
              Approve
            </button>
            <button
              onClick={() => handleDecision("rejected")}
              disabled={submitting}
              className="flex-1 bg-red-500 text-white rounded-lg py-2 text-sm font-medium hover:bg-red-600 transition disabled:opacity-50"
            >
              Reject
            </button>
          </div>
        </div>

      </div>
    </main>
  );
}
