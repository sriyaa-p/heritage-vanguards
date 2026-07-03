"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { API } from "@/lib/api";

const MIN_DESC_LENGTH = 20;
const MAX_PHOTOS = 5;
const MAX_PHOTO_SIZE_MB = 10;

const PIPELINE_STAGES = [
  { status: "pending",        label: "Received",          desc: "Submission saved" },
  { status: "registry_check", label: "Registry Check",    desc: "Checking UNESCO database for duplicates" },
  { status: "evaluation",     label: "AI Evaluation",     desc: "Gemini extracting evidence and scoring" },
  { status: "reviewer_review", label: "Ready for Review",  desc: "Dossier sent to archaeologist review queue" },
];

const TERMINAL = ["approved", "rejected", "reviewer_review"];

function PipelineTracker({ submissionId, onReset }: { submissionId: string; onReset: () => void }) {
  const [status, setStatus] = useState("pending");
  const [rejectionReason, setRejectionReason] = useState<string | null>(null);
  const router = useRouter();
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    intervalRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${API}/submissions/${submissionId}`);
        if (!res.ok) return;
        const data = await res.json();
        const s = data.status;
        setStatus(s);

        if (s === "rejected") {
          const reason = data.dossier?.review?.reviewer_notes ?? null;
            setRejectionReason(reason);
          clearInterval(intervalRef.current!);
        } else if (s === "reviewer_review") {
          clearInterval(intervalRef.current!);
          setTimeout(() => router.push(`/dashboard/track/${submissionId}`), 1500);
        }
      } catch { /* keep polling */ }
    }, 2000);

    return () => clearInterval(intervalRef.current!);
  }, [submissionId, router]);

  const currentIdx = PIPELINE_STAGES.findIndex((s) => s.status === status);

  if (rejectionReason != null) {
    const isDuplicate = rejectionReason.toLowerCase().includes("already exists in the unesco");
    return (
      <div className="bg-white rounded-xl shadow p-8 max-w-md w-full text-center">
        <div className="text-5xl mb-4">{isDuplicate ? "📋" : "📊"}</div>
        <h2 className="text-xl font-bold text-gray-900 mb-2">
          {isDuplicate ? "Site Already Listed" : "Insufficient Evidence"}
        </h2>
        <p className="text-gray-600 text-sm mb-4 text-left leading-relaxed">{rejectionReason}</p>
        <p className="text-xs font-mono bg-gray-100 rounded p-2 mb-4">{submissionId}</p>
        {!isDuplicate && (
          <button onClick={onReset} className="w-full bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 transition mb-2">
            Improve and resubmit →
          </button>
        )}
        <button onClick={onReset} className="text-gray-400 hover:text-gray-600 text-sm">
          Submit a different site
        </button>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow p-8 max-w-md w-full">
      <h2 className="text-lg font-bold text-gray-900 mb-1">Processing your submission</h2>
      <p className="text-xs font-mono text-gray-400 mb-6">{submissionId}</p>

      <div className="space-y-4">
        {PIPELINE_STAGES.map((stage, i) => {
          const done = i < currentIdx || (i === currentIdx && TERMINAL.includes(status));
          const active = i === currentIdx && !TERMINAL.includes(status);
          return (
            <div key={stage.status} className="flex items-start gap-3">
              <div className={`mt-0.5 w-6 h-6 rounded-full flex items-center justify-center shrink-0 text-xs font-bold
                ${done ? "bg-green-500 text-white" : active ? "bg-blue-500 text-white animate-pulse" : "bg-gray-100 text-gray-400"}`}>
                {done ? "✓" : i + 1}
              </div>
              <div>
                <p className={`text-sm font-medium ${done ? "text-green-700" : active ? "text-blue-700" : "text-gray-400"}`}>
                  {stage.label}
                </p>
                {active && <p className="text-xs text-gray-500 mt-0.5">{stage.desc}</p>}
              </div>
            </div>
          );
        })}
      </div>

      {status === "reviewer_review" && (
        <p className="mt-6 text-center text-sm text-green-600 font-medium animate-pulse">
          Redirecting to tracking portal…
        </p>
      )}
    </div>
  );
}

export default function SubmitPage() {
  const [submissionId, setSubmissionId] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [photos, setPhotos] = useState<File[]>([]);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    if (!e.target.files) return;
    const files = Array.from(e.target.files);
    const newErrors: Record<string, string> = {};

    // Validate photo count
    const combined = [...photos, ...files];
    if (combined.length > MAX_PHOTOS) {
      newErrors.photos = `Maximum ${MAX_PHOTOS} photos allowed. You selected ${combined.length}.`;
      setErrors(newErrors);
      return;
    }

    // Validate file sizes
    const oversized = files.filter((f) => f.size > MAX_PHOTO_SIZE_MB * 1024 * 1024);
    if (oversized.length > 0) {
      newErrors.photos = `${oversized[0].name} exceeds ${MAX_PHOTO_SIZE_MB}MB limit.`;
      setErrors(newErrors);
      return;
    }

    setPhotos(combined);
    setErrors((prev) => { const next = { ...prev }; delete next.photos; return next; });
  }

  function removePhoto(index: number) {
    setPhotos((prev) => prev.filter((_, i) => i !== index));
    setErrors((prev) => { const next = { ...prev }; delete next.photos; return next; });
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const description = (form.elements.namedItem("description") as HTMLTextAreaElement).value;
    const locationName = (form.elements.namedItem("location") as HTMLInputElement).value.trim();
    const country = (form.elements.namedItem("country") as HTMLInputElement).value.trim();

    const newErrors: Record<string, string> = {};

    if (locationName.length < 2) {
      newErrors.location = "Site name must be at least 2 characters.";
    }
    if (country.length < 2) {
      newErrors.country = "Country must be at least 2 characters.";
    }
    if (description.trim().length < MIN_DESC_LENGTH) {
      newErrors.description = `Description must be at least ${MIN_DESC_LENGTH} characters.`;
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    setErrors({});
    setIsSubmitting(true);

    const data = {
      location_name: locationName,
      country: country,
      description: description,
      submitted_by: "community_user",
    };

    try {
      const formData = new FormData();
      formData.append("location_name", data.location_name);
      formData.append("country", data.country);
      formData.append("description", data.description);
      formData.append("submitted_by", data.submitted_by);
      photos.forEach((file) => formData.append("files", file));

      const res = await fetch(`${API}/submissions/with-photos`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const body = await res.text().catch(() => "");
        setErrors({ submit: `Submission failed (${res.status}): ${body || res.statusText}` });
        setIsSubmitting(false);
        return;
      }

      const result = await res.json();
      setSubmissionId(result.submission_id);
      setSubmitted(true);
    } catch (err) {
      setErrors({ submit: "Network error. Please check your connection and try again." });
      setIsSubmitting(false);
    }
  }

  function handleReset() {
    setSubmissionId("");
    setSubmitted(false);
    setPhotos([]);
    setErrors({});
    setIsSubmitting(false);
  }

  if (submitted) {
    return (
      <main className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <PipelineTracker submissionId={submissionId} onReset={handleReset} />
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
      <div className="bg-white rounded-xl shadow p-6 sm:p-8 w-full max-w-lg">
        <h1 className="text-2xl font-bold text-gray-900 mb-1">Submit a Heritage Site</h1>
        <p className="text-gray-500 text-sm mb-6">Help us document potential UNESCO candidates in your area.</p>

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          {/* Location */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Site Name / Location</label>
            <input name="location" required className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="e.g. Hampi Ruins" />
            {errors.location && <p className="text-red-500 text-xs mt-1">{errors.location}</p>}
          </div>

          {/* Country */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Country</label>
            <input name="country" required className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="e.g. India" />
            {errors.country && <p className="text-red-500 text-xs mt-1">{errors.country}</p>}
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea name="description" required rows={4} className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="Describe the site — its history, cultural significance, and what makes it special." />
            {errors.description && <p className="text-red-500 text-xs mt-1">{errors.description}</p>}
          </div>

          {/* Photos */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Photos <span className="text-gray-400 font-normal">(max {MAX_PHOTOS}, {MAX_PHOTO_SIZE_MB}MB each)</span>
            </label>
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-5 text-center cursor-pointer hover:border-blue-400 transition" onClick={() => fileInputRef.current?.click()}>
              <input ref={fileInputRef} type="file" accept="image/*" multiple className="hidden" onChange={handleFileChange} />
              <p className="text-sm text-gray-400">📸 Click to select photos <span className="text-gray-300">(JPG, PNG, WEBP)</span></p>
            </div>
            {errors.photos && <p className="text-red-500 text-xs mt-1">{errors.photos}</p>}
            {photos.length > 0 && (
              <ul className="mt-2 space-y-1">
                {photos.map((file, i) => (
                  <li key={i} className="flex items-center justify-between text-sm bg-gray-50 rounded px-3 py-1">
                    <span className="text-gray-700 truncate max-w-xs">{file.name} <span className="text-gray-400">({(file.size / 1024 / 1024).toFixed(1)} MB)</span></span>
                    <button type="button" onClick={() => removePhoto(i)} className="text-red-400 hover:text-red-600 ml-2 text-xs">Remove</button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Submit error */}
          {errors.submit && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
              {errors.submit}
            </div>
          )}

          {/* Submit button */}
          <button
            type="submit"
            disabled={isSubmitting}
            className={`w-full rounded-lg py-2 text-sm font-medium transition ${
              isSubmitting
                ? "bg-blue-400 text-white cursor-not-allowed"
                : "bg-blue-600 text-white hover:bg-blue-700"
            }`}
          >
            {isSubmitting ? (
              <span className="flex items-center justify-center gap-2">
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Submitting…
              </span>
            ) : (
              "Submit Site"
            )}
          </button>
        </form>
      </div>
    </main>
  );
}
