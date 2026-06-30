"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { API } from "@/lib/api";

interface PublicSubmission {
  submission_id: string;
  status: string;
  created_at: string;
  location_name: string;
  country: string;
  description: string;
  photo_urls: string[];
  reviewer_notes?: string;
  committee_comments?: string;
}

const STAGES = [
  { key: "submitted", label: "Submitted", desc: "Dossier received by system" },
  { key: "ai_evaluation", label: "AI Analysis", desc: "Automated verification and duplicate check" },
  { key: "reviewer_review", label: "Archaeologist Review", desc: "Expert assessment of evidence" },
  { key: "committee_review", label: "Committee Review", desc: "Final UNESCO committee evaluation" },
  { key: "final_decision", label: "Final Decision", desc: "Official designation outcome" },
];

export default function TrackPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [submission, setSubmission] = useState<PublicSubmission | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    const fetchPublicData = async () => {
      try {
        const res = await fetch(`${API}/submissions/${id}/public`);
        if (!res.ok) throw new Error("Not found");
        const data = await res.json();
        setSubmission(data);
      } catch {
        setSubmission(null);
      } finally {
        setLoading(false);
      }
    };
    fetchPublicData();
  }, [id]);

  if (loading) {
    return (
      <main className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-amber-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-gray-500 text-sm">Loading tracking details…</p>
        </div>
      </main>
    );
  }

  if (!submission) {
    return (
      <main className="min-h-screen bg-gray-50 flex items-center justify-center p-8">
        <div className="bg-white rounded-xl shadow-md p-8 max-w-md w-full text-center">
          <div className="text-5xl mb-4">🔍</div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">Submission Not Found</h2>
          <p className="text-gray-500 text-sm mb-6">We couldn't find a submission with ID: <span className="font-mono bg-gray-100 px-1.5 py-0.5 rounded">{id}</span></p>
          <button onClick={() => router.push("/submit")} className="w-full bg-slate-900 text-white rounded-lg py-2 text-sm font-medium hover:bg-slate-800 transition">
            Submit a New Site
          </button>
        </div>
      </main>
    );
  }

  // Helper to determine the state of each stage
  const getStageState = (stageKey: string) => {
    const status = submission.status;

    if (stageKey === "submitted") {
      return "completed";
    }

    if (stageKey === "ai_evaluation") {
      if (["pending", "registry_check", "evaluation"].includes(status)) {
        return "active";
      }
      return "completed";
    }

    if (stageKey === "reviewer_review") {
      if (status === "reviewer_review") return "active";
      if (["committee_review", "approved", "rejected"].includes(status)) {
        return "completed";
      }
      return "pending";
    }

    if (stageKey === "committee_review") {
      if (status === "committee_review") return "active";
      if (["approved", "rejected"].includes(status)) {
        return "completed";
      }
      return "pending";
    }

    if (stageKey === "final_decision") {
      if (status === "approved" || status === "rejected") {
        return "completed";
      }
      return "pending";
    }

    return "pending";
  };

  const status = submission.status;
  const isApproved = status === "approved";
  const isRejected = status === "rejected";

  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-50 to-gray-100 py-8 px-4 sm:px-6">
      <div className="max-w-4xl mx-auto space-y-6">
        
        {/* Top Header Card */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200/60 p-6 sm:p-8">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <span className="text-xs font-semibold tracking-wider text-amber-600 uppercase">Site Tracking Portal</span>
              <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight mt-1">{submission.location_name}</h1>
              <p className="text-gray-500 text-sm mt-1">{submission.country} · ID: <span className="font-mono">{submission.submission_id}</span></p>
            </div>
            <div className="shrink-0">
              <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold shadow-sm
                ${isApproved ? "bg-green-100 text-green-800" : isRejected ? "bg-red-100 text-red-800" : "bg-blue-100 text-blue-800 animate-pulse"}`}>
                <span className={`w-2 h-2 rounded-full ${isApproved ? "bg-green-500" : isRejected ? "bg-red-500" : "bg-blue-500"}`} />
                {status === "reviewer_review" ? "Awaiting Reviewer" : status === "committee_review" ? "Recommended to Committee" : status.toUpperCase()}
              </span>
            </div>
          </div>
        </div>

        {/* Main Content Layout */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          
          {/* Left Column: Timeline Tracker */}
          <div className="md:col-span-1 bg-white rounded-2xl shadow-sm border border-gray-200/60 p-6">
            <h2 className="text-base font-bold text-slate-900 mb-6 flex items-center gap-2">
              <span>📅</span> Progress Timeline
            </h2>
            <div className="relative border-l-2 border-gray-200 ml-3 space-y-6 pb-2">
              {STAGES.map((stage) => {
                const state = getStageState(stage.key);
                let dotClass = "bg-gray-200 border-gray-300";
                let textClass = "text-gray-400";
                let checkMark = null;

                if (state === "completed") {
                  dotClass = "bg-green-500 border-green-600 text-white";
                  textClass = "text-slate-800";
                  checkMark = "✓";
                } else if (state === "active") {
                  dotClass = "bg-blue-500 border-blue-600 text-white animate-pulse";
                  textClass = "text-blue-700 font-semibold";
                  checkMark = "●";
                }

                return (
                  <div key={stage.key} className="relative pl-6">
                    {/* Circle Dot */}
                    <span className={`absolute -left-2.5 top-1.5 w-5 h-5 rounded-full border flex items-center justify-center text-[10px] font-bold ${dotClass}`}>
                      {checkMark}
                    </span>
                    <div>
                      <h3 className={`text-xs font-bold ${textClass}`}>{stage.label}</h3>
                      <p className="text-[11px] text-gray-500 mt-0.5 leading-tight">{stage.desc}</p>
                      {stage.key === "final_decision" && isApproved && (
                        <span className="inline-block mt-2 text-[10px] bg-green-100 text-green-800 font-bold px-2 py-0.5 rounded">Designated Site</span>
                      )}
                      {stage.key === "final_decision" && isRejected && (
                        <span className="inline-block mt-2 text-[10px] bg-red-100 text-red-800 font-bold px-2 py-0.5 rounded">Declined</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Right Column: Details & Feedback */}
          <div className="md:col-span-2 space-y-6">
            
            {/* Feedback Panel */}
            {(submission.reviewer_notes || submission.committee_comments) && (
              <div className="bg-gradient-to-br from-amber-500/5 to-orange-500/5 border border-amber-500/20 rounded-2xl p-6 space-y-4">
                <h2 className="text-base font-bold text-amber-900 flex items-center gap-2">
                  <span>💬</span> Official Reviewer Feedback
                </h2>
                
                {submission.reviewer_notes && (
                  <div className="bg-white/75 rounded-xl p-4 border border-amber-500/10">
                    <p className="text-xs font-bold text-slate-800">Archaeologist Evaluation Notes</p>
                    <p className="text-xs text-slate-600 mt-1.5 leading-relaxed italic">"{submission.reviewer_notes}"</p>
                  </div>
                )}

                {submission.committee_comments && (
                  <div className="bg-white/75 rounded-xl p-4 border border-amber-500/10">
                    <p className="text-xs font-bold text-slate-800">UNESCO World Heritage Committee Comments</p>
                    <p className="text-xs text-slate-600 mt-1.5 leading-relaxed italic">"{submission.committee_comments}"</p>
                  </div>
                )}
              </div>
            )}

            {/* Dossier details */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-200/60 p-6 space-y-6">
              <div>
                <h2 className="text-base font-bold text-slate-900 mb-2">Description</h2>
                <p className="text-xs text-slate-600 leading-relaxed whitespace-pre-wrap">{submission.description}</p>
              </div>

              {submission.photo_urls && submission.photo_urls.length > 0 && (
                <div>
                  <h2 className="text-base font-bold text-slate-900 mb-3">Submitted Photos</h2>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                    {submission.photo_urls.map((url, i) => (
                      <div key={i} className="group relative overflow-hidden rounded-xl bg-gray-100 aspect-video border border-gray-200">
                        <img
                          src={url.startsWith("/") ? `${API}${url}` : url}
                          alt={`${submission.location_name} - Photo ${i + 1}`}
                          className="object-cover w-full h-full transition duration-300 group-hover:scale-105"
                        />
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
            
          </div>
        </div>
      </div>
    </main>
  );
}
