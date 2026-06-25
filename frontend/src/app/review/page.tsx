import Link from "next/link";
import sampleDossier from "../../../public/sample_dossier.json";

const MOCK_QUEUE = [
  { submission_id: sampleDossier.metadata.submission_id, location: sampleDossier.metadata.location_name, country: sampleDossier.metadata.country, score: sampleDossier.scoring.total, status: sampleDossier.metadata.status },
  { submission_id: "SUB-2026-06-A1B2C3D4", location: "Konark Sun Temple Surroundings", country: "India", score: 74, status: "verification" },
  { submission_id: "SUB-2026-06-E5F6G7H8", location: "Rani ki Vav Stepwell", country: "India", score: 91, status: "verification" },
];

export default function ReviewQueuePage() {
  return (
    <main className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-2xl font-bold text-gray-900 mb-1">Review Queue</h1>
        <p className="text-gray-500 text-sm mb-6">Submissions awaiting your decision — click any row to view the Confidence Card.</p>

        <div className="bg-white rounded-xl shadow overflow-hidden">
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
