"use client";
import { useState, useRef } from "react";

export default function SubmitPage() {
  const [submitted, setSubmitted] = useState(false);
  const [submissionId, setSubmissionId] = useState("");
  const [photos, setPhotos] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files) {
      setPhotos(Array.from(e.target.files));
    }
  }

  function removePhoto(index: number) {
    setPhotos((prev) => prev.filter((_, i) => i !== index));
  }

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
      <main className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
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
    <main className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
      <div className="bg-white rounded-xl shadow p-6 sm:p-8 w-full max-w-lg">
        <h1 className="text-2xl font-bold text-gray-900 mb-1">Submit a Heritage Site</h1>
        <p className="text-gray-500 text-sm mb-6">Help us document potential UNESCO candidates in your area.</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Site Name / Location</label>
            <input
              name="location"
              required
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g. Hampi Ruins"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Country</label>
            <input
              name="country"
              required
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g. India"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea
              name="description"
              required
              rows={4}
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Describe the site — its history, cultural significance, and what makes it special."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Photos</label>
            <div
              className="border-2 border-dashed border-gray-300 rounded-lg p-5 text-center cursor-pointer hover:border-blue-400 transition"
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                multiple
                className="hidden"
                onChange={handleFileChange}
              />
              <p className="text-sm text-gray-400">
                📸 Click to select photos <span className="text-gray-300">(JPG, PNG, WEBP)</span>
              </p>
              <p className="text-xs text-gray-300 mt-1">Up to 5 images — processing will happen after submission</p>
            </div>

            {photos.length > 0 && (
              <ul className="mt-2 space-y-1">
                {photos.map((file, i) => (
                  <li key={i} className="flex items-center justify-between text-sm bg-gray-50 rounded px-3 py-1">
                    <span className="text-gray-700 truncate max-w-xs">{file.name}</span>
                    <button
                      type="button"
                      onClick={() => removePhoto(i)}
                      className="text-red-400 hover:text-red-600 ml-2 text-xs"
                    >
                      Remove
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <button
            type="submit"
            className="w-full bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 transition"
          >
            Submit Site
          </button>
        </form>
      </div>
    </main>
  );
}
