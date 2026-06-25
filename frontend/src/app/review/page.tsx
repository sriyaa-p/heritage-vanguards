import Link from "next/link";
import sampleDossier from "../../../public/sample_dossier.json";

const MOCK_QUEUE = [
  { submission_id: sampleDossier.metadata.submission_id, location: sampleDossier.metadata.location_name, country: sampleDossier.metadata.country, score: sampleDossier.scoring.total, status: sampleDossier.metadata.status },
  { submission_id: "SUB-2026-06-A1B2C3D4", location: "Konark Sun Temple Surroundings", country: "India", score: 74, status: "verification" },
  { submission_id: "SUB-2026-06-E5F6G7H8", location: "Rani ki Vav Stepwell", country: "India", score: 91, status: "verification" },
];

export default function ReviewQueuePage() {
  return (
    <main className="min-h-screen bg-gray-50 p-4 sm:p-8">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-2xl font-bold text-gray-900 mb-1">Review Queue</h1>
        <p className="text-gray-500 text-sm mb-6">Submissions awaiting your decision — click any row to view the Confidence Card.</p>

        {/* Mobile: stacked cards */}
        <div className="flex flex-col gap-3 sm:hidden">
          {MOCK_QUEUE.map((item) => (
            <div key={item.submission_id} className="bg-white rounded-xl shadow p-4">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <p className="font-medium text-gray-900">{item.location}</p>
                  <p className="text-xs text-gray-400">{item.country}</p>
                </div>
                <span className={`text-lg font-bold ${item.score >= 80 ? "text-green-600" : item.score >= 60 ? "text-yellow-600" : "text-red-500"}`}>
                  {item.score}/100
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="bg-blue-100 text-blue-700 rounded-full px-2 py-0.5 text-xs">{item.status}</span>
                <Link href={`/review/${item.submission_id}`} className="text-blue-600 hover:underline text-sm font-medium">
                  View Card →
                </Link>
              </div>
            </div>
          ))}
        </div>

        {/* Desktop: table */}
        <div className="hidden sm:block bg-white rounded-xl shadow overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-3 text-gray-600 font-medium">Site</th>
                <th className="text-left px-4 py-3 text-gray-600 font-medium">Country</th>
                <th className="text-left px-4 py-3 text-gray-600 font-medium">Heritage Score</th>
                <th className="text-left px-4 py-3 text-gray-600 font-medium">Status</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {MOCK_QUEUE.map((item) => (
                <tr key={item.submission_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{item.location}</td>
                  <td className="px-4 py-3 text-gray-500">{item.country}</td>
                  <td className="px-4 py-3">
                    <span className={`font-bold ${item.score >= 80 ? "text-green-600" : item.score >= 60 ? "text-yellow-600" : "text-red-500"}`}>
                      {item.score}/100
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="bg-blue-100 text-blue-700 rounded-full px-2 py-0.5 text-xs">{item.status}</span>
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
      </div>
    </main>
  );
}
