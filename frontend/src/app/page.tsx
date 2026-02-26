"use client";

import { useState, useRef, useEffect } from "react";
import { useSession, signIn, signOut } from "next-auth/react";

interface ChatMessage {
  role: "user" | "ai";
  content: string; // Used for user input or raw text
  // AI JSON response fields:
  verdict?: string;
  explanation?: string;
  example_case?: string;
  caution_note?: string;
  sources?: string[];
}

export default function Home() {
  const { data: session, status } = useSession();
  const [activeTab, setActiveTab] = useState<"chat" | "search">("chat");
  const [query, setQuery] = useState("");
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [mounted, setMounted] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Search state
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery) return;
    setIsSearching(true);
    try {
      const res = await fetch(`http://localhost:8000/search/articles?query=${encodeURIComponent(searchQuery)}`);
      const data = await res.json();
      setSearchResults(data.results || []);
    } catch (err) {
      console.error(err);
    } finally {
      setIsSearching(false);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatHistory]);

  const handleCheck = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query || !session?.user) return;

    const userQuery = query;
    setQuery("");
    setChatHistory((prev) => [...prev, { role: "user", content: userQuery }]);
    setLoading(true);

    try {
      const userId = (session.user as any).id;
      const response = await fetch(`http://localhost:8000/check?user_id=${userId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query: userQuery, session_id: sessionId }),
      });

      const data = await response.json();
      if (response.ok) {
        setSessionId(data.session_id);

        // Handling structured JSON response from backend
        // data.result contains the parsed JSON object
        setChatHistory((prev) => [
          ...prev,
          {
            role: "ai",
            content: "",
            verdict: data.result?.verdict || "ERROR",
            explanation: data.result?.explanation || "응답을 생성할 수 없습니다.",
            example_case: data.result?.example_case,
            caution_note: data.result?.caution_note,
            sources: data.sources
          },
        ]);
      } else {
        setChatHistory((prev) => [
          ...prev,
          { role: "ai", content: `Error: ${data.detail}` },
        ]);
      }
    } catch (error) {
      console.error("Error fetching data:", error);
      setChatHistory((prev) => [
        ...prev,
        { role: "ai", content: "서버에 연결할 수 없습니다. 백엔드 서버가 켜져 있는지 확인해주세요." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  if (!mounted || status === "loading") {
    return <div className="min-h-screen bg-gray-900 flex items-center justify-center text-white">Loading...</div>;
  }

  // Helper for rendering verdict badges
  const getVerdictBadge = (verdict?: string) => {
    switch (verdict) {
      case "TRUE":
        return <span className="bg-green-500/20 text-green-400 border border-green-500/50 px-3 py-1 rounded-full text-xs font-bold tracking-wide">사실성 높음 (TRUE)</span>;
      case "PARTIAL":
        return <span className="bg-yellow-500/20 text-yellow-400 border border-yellow-500/50 px-3 py-1 rounded-full text-xs font-bold tracking-wide">일부 사실 (PARTIAL)</span>;
      case "FALSE":
        return <span className="bg-red-500/20 text-red-400 border border-red-500/50 px-3 py-1 rounded-full text-xs font-bold tracking-wide">사실 아님 (FALSE)</span>;
      default:
        return <span className="bg-gray-500/20 text-gray-400 border border-gray-500/50 px-3 py-1 rounded-full text-xs font-bold tracking-wide">확인 불가 (ERROR)</span>;
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-black text-white selection:bg-indigo-500 selection:text-white flex flex-col">
      {/* Header */}
      <header className="p-6 flex justify-between items-center border-b border-gray-800 backdrop-blur-md">
        <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-500">
          Legal Fact Checker
        </h1>
        {session ? (
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              {session.user?.image && (
                <img src={session.user.image} alt="Profile" className="w-8 h-8 rounded-full" />
              )}
              <span className="text-sm text-gray-300">{session.user?.name}</span>
            </div>
            <button onClick={() => signOut()} className="text-sm text-gray-400 hover:text-white transition">
              로그아웃
            </button>
          </div>
        ) : null}
      </header>

      {/* Main Content */}
      <div className="flex-grow container mx-auto px-4 py-8 flex flex-col max-w-4xl max-h-[calc(100vh-80px)]">
        {!session ? (
          <div className="flex-grow flex flex-col items-center justify-center space-y-6 text-center h-full">
            <h2 className="text-4xl md:text-5xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-indigo-500 to-purple-500">
              법률 팩트체커에 오신 것을 환영합니다
            </h2>
            <p className="text-lg text-gray-400 max-w-xl">
              복잡한 법률, AI가 명쾌하게 팩트체크 해드립니다. 로그인 후 이전 대화 맥락을 기억하는 꼬리 질문 기능을 활용해 보세요.
            </p>
            <button
              onClick={() => signIn("google")}
              className="bg-white text-gray-900 font-semibold py-3 px-8 rounded-xl transition-all duration-300 transform hover:scale-105 shadow-lg flex items-center gap-3"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
              </svg>
              Google로 시작하기
            </button>
          </div>
        ) : (
          <div className="flex flex-col h-full overflow-hidden">
            {/* Tabs */}
            <div className="flex space-x-4 mb-4 border-b border-gray-700/50 pb-2 flex-shrink-0">
              <button
                onClick={() => setActiveTab("chat")}
                className={`pb-2 px-2 text-sm font-medium transition-colors ${activeTab === "chat" ? "text-indigo-400 border-b-2 border-indigo-400" : "text-gray-400 hover:text-gray-200"}`}
              >
                팩트체크 대화
              </button>
              <button
                onClick={() => setActiveTab("search")}
                className={`pb-2 px-2 text-sm font-medium transition-colors ${activeTab === "search" ? "text-indigo-400 border-b-2 border-indigo-400" : "text-gray-400 hover:text-gray-200"}`}
              >
                조문 검색
              </button>
            </div>

            {activeTab === "chat" ? (
              <>
                <div className="flex-grow overflow-y-auto space-y-6 pr-2 custom-scrollbar pb-6 rounded-xl">
                  {chatHistory.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-gray-500">
                      <p>궁금한 법률 질문을 편하게 입력해주세요.</p>
                      <p className="text-sm mt-2">예: 수습 기간에 해고하면 월급은 어떻게 되나요?</p>
                    </div>
                  ) : (
                    chatHistory.map((msg, idx) => (
                      <div key={idx} className={`flex w-full ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                        <div className={`max-w-[85%] rounded-2xl p-5 ${msg.role === "user"
                          ? "bg-indigo-600 text-white rounded-br-none shadow-md"
                          : "bg-gray-800/80 border border-gray-700/50 text-gray-100 rounded-bl-none shadow-lg"
                          }`}>

                          {msg.role === "user" ? (
                            <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                          ) : (
                            <div className="flex flex-col space-y-4">
                              {/* Rendering parsed AI Response */}
                              {msg.verdict && (
                                <div className="mb-2">
                                  {getVerdictBadge(msg.verdict)}
                                </div>
                              )}

                              {msg.explanation ? (
                                <div className="text-gray-200 leading-relaxed whitespace-pre-wrap text-[15px]">
                                  {msg.explanation}
                                </div>
                              ) : (
                                <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                              )}

                              {msg.example_case && (
                                <div className="bg-gray-900/50 p-3 rounded-lg border border-gray-700/30">
                                  <h4 className="text-sm text-indigo-400 font-bold mb-1 flex items-center">
                                    <span className="mr-2">💡</span>현실 적용 사례
                                  </h4>
                                  <p className="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap">{msg.example_case}</p>
                                </div>
                              )}

                              {msg.caution_note && (
                                <div className="bg-red-900/10 p-3 rounded-lg border border-red-900/30">
                                  <h4 className="text-sm text-red-400 font-bold mb-1 flex items-center">
                                    <span className="mr-2">⚠️</span>주의사항
                                  </h4>
                                  <p className="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap">{msg.caution_note}</p>
                                </div>
                              )}

                              {/* Sources */}
                              {msg.sources && msg.sources.length > 0 && (
                                <div className="mt-2 pt-3 border-t border-gray-600/50">
                                  <h4 className="text-xs text-gray-400 uppercase tracking-wider mb-2 font-semibold">참고 문서</h4>
                                  <ul className="space-y-1">
                                    {msg.sources.map((src, sIdx) => (
                                      <li key={sIdx} className="text-xs text-indigo-300 flex items-center">
                                        <span className="w-1.5 h-1.5 bg-indigo-500 rounded-full mr-2"></span>
                                        {src}
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                  {loading && (
                    <div className="flex justify-start">
                      <div className="bg-gray-800/80 border border-gray-700/50 p-4 rounded-2xl rounded-bl-none flex space-x-2">
                        <div className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce delay-75"></div>
                        <div className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce delay-150"></div>
                      </div>
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </div>

                <div className="flex-shrink-0 w-full mt-4 bg-gray-900 pb-10">
                  <form onSubmit={handleCheck} className="relative group w-full">
                    <div className="absolute -inset-1 bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl blur opacity-25 transition duration-1000 group-focus-within:opacity-50 group-hover:opacity-50"></div>
                    <div className="relative flex items-center bg-gray-900 rounded-2xl p-1 border border-gray-700/50 shadow-2xl">
                      <input
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="질문을 입력하세요..."
                        className="flex-grow bg-transparent text-white placeholder-gray-500 px-6 py-4 focus:outline-none"
                        disabled={loading}
                      />
                      <button
                        type="submit"
                        disabled={loading || !query}
                        className="bg-indigo-600 hover:bg-indigo-500 text-white p-3 rounded-xl transition-all duration-300 mr-1 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14 5l7 7m0 0l-7 7m7-7H3"></path></svg>
                      </button>
                    </div>
                  </form>
                </div>
              </>
            ) : (
              <div className="flex-grow flex flex-col h-full overflow-hidden pb-4">
                <form onSubmit={handleSearch} className="mb-4 flex gap-2 flex-shrink-0">
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="검색할 규정이나 법령 키워드를 입력하세요..."
                    className="flex-grow bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-indigo-500"
                  />
                  <button
                    type="submit"
                    disabled={isSearching || !searchQuery}
                    className="bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-3 rounded-xl transition-all disabled:opacity-50"
                  >
                    {isSearching ? "검색 중..." : "검색"}
                  </button>
                </form>

                <div className="flex-grow overflow-y-auto space-y-4 pr-2 custom-scrollbar pb-6 rounded-xl">
                  {searchResults.length === 0 && !isSearching ? (
                    <div className="text-center text-gray-500 mt-10">검색 결과가 여기에 표시됩니다.</div>
                  ) : (
                    searchResults.map((result, idx) => (
                      <div key={idx} className="bg-gray-800 border border-gray-700 rounded-xl p-5 shadow-sm">
                        <h3 className="text-lg font-bold text-indigo-300 mb-2">
                          {result.law_name} {result.article_number}
                        </h3>
                        <p className="text-gray-300 whitespace-pre-wrap leading-relaxed text-[15px]">
                          {result.content}
                        </p>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </main>
  );
}
