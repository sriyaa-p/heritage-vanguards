"use client";
import { useState } from "react";
import sampleDossier from "../../../../public/sample_dossier.json";

const SCORE_CATEGORIES = [
  { key: "historic_features", label: "Historic Features", max: 30 },
  { key: "cultural_significance", label: "Cultural Significance", max: 25 },
  { key: "geographic_context", label: "Geographic Context", max: 15 },
  { key: "documentation", label: "Documentation", max: 15 },
  { key: "supporting_evidence", label: "Supporting Evidence", max: 15 },
];

function ScoreBar({ score, max }: { score: number; max: number }) {
  const pct = Math.round((score / max) * 100);
  const color = pct >= 80 ? "bg-green-500" : pct >= 60 ? "bg-yellow-400" : "bg-red-400";
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 bg-gray-100 rounded-full h-2">
        <div className={`${color} h-2 rounded-full`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono w-12 text-right text-gray-600">{score}/{max}</span>
    </div>
  );
}

export default function ConfidenceCardPage() {
  const d = sampleDossier;
  const [decision, setDecision] = useState<"approved" | "rejected" | null>(null);
  const [notes, setNotes] = useState("");
  const totalScore = d.scoring.total;
  const confidence = totalScore >= 80 ? "High" : totalScore >= 60 ? "Moderate" : "Low";
  const confidenceColor = confidence === "High" ? "text-green-600" : confidence === "Moderate" ? "text-yellow-600" : "text-red-500";

  if (decision) {
    return (
      <main className="min-h-screen bg-gray-50 flex items-center justify-center p-8">
        <div className="bg-white rounded-xl shadow p-8 max-w-md w-full text-center">
          <div className="text-5xl mb-4">{decision === "approved" ? "✅" : "❌"}</div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2 capitalize">{decision}</h2>
          <p className="text-gray-500">{d.metadata.location_name} has been {decision}.</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-2xl mx-auto space-y-5">

        <div className="bg-white rounded-xl shadow p-6">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{d.metadata.location_name}</h1>
              <p className="text-gray-500 text-sm">{d.metadata.country} · {d.metadata.submission_id}</p>
            </div>
            <div className="text-right">
              <p className="text-4xl font-bold text-gray-900">{totalScore}<span className="text-lg text-gray-400">/100</span></p>
              <p className={`text-sm font-semibold ${confidenceColor}`}>{confidence} Confidence</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow p-6">
          <h2 className="font-semibold text-gray-900 mb-4">Heritage Score Breakdown</h2>
          <div className="space-y-3">
            {SCORE_CATEGORIES.map(({ key, label, max }) => (
              <div key={key}>
                <div className="flex justify-between text-sm text-gray-600 mb-1">
                  <span>{label}</span>
                </div>
                <ScoreBar score={(d.scoring as Record<string, number>)[key]} max={max} />
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-xl shadow p-6">
          <h2 className="font-semibold text-gray-900 mb-3">Evidence Summary</h2>
          <div className="space-y-3 text-sm text-gray-700">
            <p><span className="font-medium">Historic Features:</span> {d.extracted_evidence.historic_features}</p>
            <p><span className="font-medium">Cultural Significance:</span> {d.extracted_evidence.cultural_significance}</p>
            <p><span className="font-medium">Geographic Context:</span> {d.extracted_evidence.geographic_context}</p>
            <p><span className="font-medium">Documentation:</span> {d.extracted_evidence.documentation_quality}</p>
            <p><span className="font-medium">Supporting Evidence:</span> {d.extracted_evidence.supporting_evidence}</p>
          </div>
          <div className="mt-4 p-3 bg-gray-50 rounded-lg text-sm text-gray-600 italic">
            {d.scoring.rationale}
          </div>
        </div>

        <div className="bg-white rounded-xl shadow p-6">
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
              onClick={() => setDecision("approved")}
              className="flex-1 bg-green-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-green-700 transition"
            >
              Approve
            </button>
            <button
              onClick={() => setDecision("rejected")}
              className="flex-1 bg-red-500 text-white rounded-lg py-2 text-sm font-medium hover:bg-red-600 transition"
            >
              Reject
            </button>
          </div>
        </div>

      </div>
    </main>
  );
}
