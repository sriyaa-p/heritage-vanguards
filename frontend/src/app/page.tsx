"use client";
import { useRouter } from "next/navigation";

const ROLES = [
  {
    role: "reporter",
    href: "/submit",
    icon: "📸",
    title: "Community Reporter",
    description: "Submit a heritage site candidate with photos and description.",
    color: "hover:border-blue-400 hover:shadow-blue-100",
    badge: "bg-blue-100 text-blue-700",
  },
  {
    role: "reviewer",
    href: "/review",
    icon: "🔍",
    title: "Archaeologist Reviewer",
    description: "Review AI-generated Confidence Cards and approve or reject submissions.",
    color: "hover:border-green-400 hover:shadow-green-100",
    badge: "bg-green-100 text-green-700",
  },
  {
    role: "admin",
    href: "/dashboard",
    icon: "📊",
    title: "Admin",
    description: "Monitor queue metrics, pipeline stages, and system health.",
    color: "hover:border-purple-400 hover:shadow-purple-100",
    badge: "bg-purple-100 text-purple-700",
  },
];

export default function RoleSelectPage() {
  const router = useRouter();

  function enter(href: string, role: string) {
    sessionStorage.setItem("role", role);
    router.push(href);
  }

  return (
    <main className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-6">
      <h1 className="text-4xl font-bold text-gray-900 mb-2 text-center">
        Heritage Sentinel AI
      </h1>
      <p className="text-gray-500 text-lg mb-10 text-center">
        Preserving What Humanity Cannot Rebuild — With Multi-Agent AI
      </p>

      <p className="text-sm text-gray-400 uppercase tracking-widest mb-6 font-medium">
        Select your role to continue
      </p>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5 w-full max-w-3xl">
        {ROLES.map(({ role, href, icon, title, description, color, badge }) => (
          <button
            key={role}
            onClick={() => enter(href, role)}
            className={`bg-white rounded-xl shadow border-2 border-transparent p-6 text-left transition-all duration-150 ${color} hover:shadow-md cursor-pointer`}
          >
            <div className="text-3xl mb-3">{icon}</div>
            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${badge} mb-2 inline-block`}>
              {title}
            </span>
            <p className="text-sm text-gray-500 mt-2">{description}</p>
          </button>
        ))}
      </div>
    </main>
  );
}
