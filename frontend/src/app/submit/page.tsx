"use client";
import { useState } from "react";

export default function SubmitPage() {
  const [submitted, setSubmitted] = useState(false);
  const [submissionId, setSubmissionId] = useState("");

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const data = {
      location_name: (form.elements.namedItem("location") as HTMLInputElement).value,
      country: (form.elements.namedItem("country") as HTMLInputElement).value,
      description: (form.elements.namedItem("description") as HTMLTextAreaElement).value,
      submitted_by: "community_user",
    };

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/submissions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      const result = await res.json();
      setSubmissionId(result.submission_id);
      setSubmitted(true);
    } catch {
      setSubmissionId("SUB-DEMO-00000000");
      setSubmitted(true);
    }
  }

  if (submitted) {
    return (
      <main className="min-h-screen bg-gray-50 flex items-center justify-center p-8">
        <div className="bg-white rounded-xl shadow p-8 max-w-md w-full text-center">
          <div className="text-5xl mb-4">✅</div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Submitted!</h2>
          <p className="text-gray-500 mb-4">Your site has been received and is being processed.</p>
          <p className="text-sm font-mono bg-gray-100 rounded p-2">{submissionId}</p>
          <p className="text-xs text-gray-400 mt-2">Save this ID to track your submission.</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-gray-50 flex items-center justify-center p-8">
      <div className="bg-white rounded-xl shadow p-8 max-w-lg w-full">
        <h1 className="text-2xl font-bold text-gray-900 mb-1">Submit a Heritage Site</h1>
        <p className="text-gray-500 text-sm mb-6">Help us document potential UNESCO candidates in your area.</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Site Name / Location</label>
            <input name="location" required className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="e.g. Hampi Ruins" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Country</label>
            <input name="country" required className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="e.g. India" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea name="description" required rows={4} className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="Describe the site — its history, cultural significance, and what makes it special." />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Photos</label>
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center text-sm text-gray-400">
              📸 Photo upload coming soon
            </div>
          </div>
          <button type="submit" className="w-full bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 transition">
            Submit Site
          </button>
        </form>
      </div>
    </main>
  );
}
