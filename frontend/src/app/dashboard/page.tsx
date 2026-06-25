import sampleDossier from "../../../public/sample_dossier.json";

const MOCK_METRICS = {
  total: 14,
  pending: 3,
  inReview: 8,
  approved: 2,
  rejected: 1,
  duplicatesBlocked: 4,
};

const MOCK_RECENT = [
  { id: sampleDossier.metadata.submission_id, location: sampleDossier.metadata.location_name, score: sampleDossier.scoring.total, status: "verification" },
  { id: "SUB-2026-06-A1B2", location: "Konark Sun Temple Surroundings", score: 74, status: "evaluation" },
  { id: "SUB-2026-06-E5F6", location: "Rani ki Vav Stepwell", score: 91, status: "verification" },
  { id: "SUB-2026-06-C3D4", location: "Nalanda University Ruins", score: 58, status: "registry_check" },
  { id: "SUB-2026-06-G7H8", location: "Thanjavur Palace", score: 65, status: "pending" },
];

function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="bg-white rounded-xl shadow p-5">
      <p className="text-sm text-gray-500">{label}</p>
      <p className={`text-3xl font-bold mt-1 ${color}`}>{value}</p>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <main className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold text-gray-900 mb-1">Admin Dashboard</h1>
        <p className="text-gray-500 text-sm mb-6">Queue overview and processing metrics — using mock data.</p>

        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8">
          <StatCard label="Total Submissions" value={MOCK_METRICS.total} color="text-gray-900" />
          <StatCard label="Pending Review" value={MOCK_METRICS.inReview} color="text-blue-600" />
          <StatCard label="Awaiting Intake" value={MOCK_METRICS.pending} color="text-yellow-600" />
          <StatCard label="Approved" value={MOCK_METRICS.approved} color="text-green-600" />
          <StatCard label="Rejected" value={MOCK_METRICS.rejected} color="text-red-500" />
          <StatCard label="Duplicates Blocked" value={MOCK_METRICS.duplicatesBlocked} color="text-purple-600" />
        </div>

        <div className="bg-white rounded-xl shadow overflow-hidden">
          <div className="px-5 py-4 border-b">
            <h2 className="font-semibold text-gray-900">Recent Submissions</h2>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-5 py-3 text-gray-600 font-medium">Site</th>
                <th className="text-left px-5 py-3 text-gray-600 font-medium">Score</th>
                <th className="text-left px-5 py-3 text-gray-600 font-medium">Stage</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {MOCK_RECENT.map((item) => (
                <tr key={item.id} className="hover:bg-gray-50">
                  <td className="px-5 py-3">
                    <p className="font-medium text-gray-900">{item.location}</p>
                    <p className="text-xs text-gray-400 font-mono">{item.id}</p>
                  </td>
                  <td className="px-5 py-3">
                    <span className={`font-bold ${item.score >= 80 ? "text-green-600" : item.score >= 60 ? "text-yellow-600" : "text-red-500"}`}>
                      {item.score}/100
                    </span>
                  </td>
                  <td className="px-5 py-3">
                    <span className="bg-blue-100 text-blue-700 rounded-full px-2 py-0.5 text-xs">
                      {item.status.replace("_", " ")}
                    </span>
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
