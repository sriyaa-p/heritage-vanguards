export default function Home() {
  return (
    <main className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-8">
      <h1 className="text-4xl font-bold text-gray-900 mb-4">
        Heritage Sentinel AI
      </h1>
      <p className="text-gray-600 text-lg mb-8">
        Preserving What Humanity Cannot Rebuild — With Multi-Agent AI
      </p>
      <div className="bg-white rounded-xl shadow p-6 max-w-md w-full text-center">
        <p className="text-green-600 font-semibold">System is running</p>
        <p className="text-gray-500 text-sm mt-2">
          Submit a heritage site candidate to begin the review workflow.
        </p>
      </div>
    </main>
  );
}
