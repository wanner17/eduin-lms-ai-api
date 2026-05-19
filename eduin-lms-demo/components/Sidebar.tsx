"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/ingest", label: "강의자료 업로드", icon: "📁" },
  { href: "/qa", label: "질의응답 (QA)", icon: "💬" },
  { href: "/quiz", label: "문제 생성", icon: "📝" },
  { href: "/summary", label: "요약 자료", icon: "📊" },
];

export default function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="w-56 shrink-0 bg-white border-r border-gray-200 flex flex-col h-full">
      <div className="px-5 py-6 border-b border-gray-200">
        <h1 className="text-base font-bold text-blue-600">EduIn LMS</h1>
        <p className="text-xs text-gray-400 mt-0.5">AI API 데모</p>
      </div>
      <nav className="flex-1 p-3 space-y-1">
        {links.map(({ href, label, icon }) => {
          const active = pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                active
                  ? "bg-blue-50 text-blue-700 font-medium"
                  : "text-gray-600 hover:bg-gray-100"
              }`}
            >
              <span>{icon}</span>
              {label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
