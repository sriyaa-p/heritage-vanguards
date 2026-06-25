import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-8">
      <h1 className="text-4xl font-bold text-gray-900 mb-2">
        Heritage Sentinel AI
      </h1>
      <p className="text-gray-500 text-lg mb-10">
        Preserving What Humanity Cannot Rebuild — With Multi-Agent AI
      </p>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full max-w-3xl">
        <Link href="/submit" className="bg-white rounded-xl shadow p-6 hover:shadow-md transition text-center">
          <div className="text-3xl mb-3">📸</div>
          <h2 className="font-semibold text-gray-900 mb-1">Submit a Site</h2>
          <p className="text-sm text-gray-500">Community Reporter — upload photos and description</p>
        </Link>
        <Link href="/review" className="bg-white rounded-xl shadow p-6 hover:shadow-md transition text-center">
          <div className="text-3xl mb-3">🔍</div>
          <h2 className="font-semibold text-gray-900 mb-1">Review Queue</h2>
          <p className="text-sm text-gray-500">Archaeologist — review Confidence Cards</p>
        </Link>
        <Link href="/dashboard" className="bg-white rounded-xl shadow p-6 hover:shadow-md transition text-center">
          <div className="text-3xl mb-3">📊</div>
          <h2 className="font-semibold text-gray-900 mb-1">Dashboard</h2>
          <p className="text-sm text-gray-500">Admin — queue metrics and processing status</p>
        </Link>
      </div>
    </main>
  );
}
