"use client";

import { useState } from "react";

export default function Home() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const handleCheck = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query) return;

    setLoading(true);
    setResult(null);

    try {
      const response = await fetch("http://localhost:8000/check", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query }),
      });

      const data = await response.json();
      setResult(data);
    } catch (error) {
      console.error("Error fetching data:", error);
      setResult({ result: "Error", reasoning: "Failed to connect to the server." });
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-black text-white selection:bg-indigo-500 selection:text-white">
      <div className="container mx-auto px-4 py-16 flex flex-col items-center justify-center min-h-screen">

        {/* Header Section */}
        <div className="text-center mb-12 space-y-4">
          <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-indigo-500 to-purple-500 animate-gradient-x">
            Legal Fact Checker
          </h1>
          <p className="text-lg md:text-xl text-gray-400 max-w-2xl mx-auto">
            복잡한 법률, AI가 명쾌하게 팩트체크 해드립니다. <br />
            <span className="text-sm text-gray-500">(근로기준법, 주택임대차보호법 기반)</span>
          </p>
        </div>

        {/* Input Section */}
        <div className="w-full max-w-3xl">
          <form onSubmit={handleCheck} className="relative group">
            <div className="absolute -inset-1 bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl blur opacity-25 group-hover:opacity-75 transition duration-1000 group-hover:duration-200"></div>
            <div className="relative flex items-center bg-gray-900 rounded-2xl p-2 border border-gray-700/50 shadow-2xl">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="예: 수습 기간에 해고하면 월급은 어떻게 되나요?"
                className="flex-grow bg-transparent text-white placeholder-gray-500 px-6 py-4 text-lg focus:outline-none"
                disabled={loading}
              />
              <button
                type="submit"
                disabled={loading}
                className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-3 px-8 rounded-xl transition-all duration-300 transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg"
              >
                {loading ? (
                  <span className="flex items-center">
                    <svg className="animate-spin -ml-1 mr-2 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    분석 중
                  </span>
                ) : (
                  "검사하기"
                )}
              </button>
            </div>
          </form>
        </div>

        {/* Result Section */}
        {result && (
          <div className="w-full max-w-3xl mt-12 animate-fade-in-up">
            <div className="bg-gray-800/50 backdrop-blur-xl border border-gray-700 rounded-3xl p-8 shadow-2xl relative overflow-hidden">
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 to-purple-500"></div>

              <div className="space-y-6">
                <div>
                  <h3 className="text-gray-400 text-sm font-semibold uppercase tracking-wider mb-2">판정 결과</h3>
                  <div className="prose prose-invert max-w-none">
                    <p className="text-xl leading-relaxed whitespace-pre-wrap">{result.result}</p>
                  </div>
                </div>

                {result.sources && result.sources.length > 0 && (
                  <div className="pt-6 border-t border-gray-700/50">
                    <h3 className="text-gray-400 text-sm font-semibold uppercase tracking-wider mb-3">참고 법령</h3>
                    <ul className="grid gap-2">
                      {result.sources.map((source: string, idx: number) => (
                        <li key={idx} className="bg-gray-900/50 rounded-lg px-4 py-2 text-sm text-gray-300 border border-gray-700/30 flex items-center">
                          <span className="w-2 h-2 bg-indigo-500 rounded-full mr-3"></span>
                          {source}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Footer */}
        <footer className="mt-20 text-gray-600 text-sm">
          <p>© 2026 Legal Fact Checker. Powered by AI. Not Legal Advice.</p>
        </footer>
      </div>
    </main>
  );
}
