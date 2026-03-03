"use client";

import { useState, useRef, useEffect } from "react";
import { useSession, signIn, signOut } from "next-auth/react";

interface ChatMessage {
  role: "user" | "ai";
  content: string; // Used for user input or raw text
  // AI JSON response fields:
  verdict?: string;
  section_1_summary?: string;
  section_2_law_explanation?: string;
  section_3_real_case_example?: string;
  section_4_caution?: string;
  section_5_counseling_recommendation?: string;
  section_6_suggested_followups?: string[];
  sources?: string[];
  attached_image?: string; // Base64 selected image preview
}

export default function Home() {
  const { data: session, status } = useSession();
  const [activeTab, setActiveTab] = useState<"chat" | "search" | "history">("chat");
  const [popularClaims, setPopularClaims] = useState<string[]>([]);
  const [sessionHistory, setSessionHistory] = useState<any[]>([]);
  const [query, setQuery] = useState("");
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.size > 5 * 1024 * 1024) {
        alert("이미지 크기는 5MB 이하여야 합니다.");
        return;
      }
      const reader = new FileReader();
      reader.onloadend = () => {
        setSelectedImage(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  useEffect(() => {
    setMounted(true);
    fetchPopularClaims();
  }, []);

  const fetchPopularClaims = async () => {
    try {
      const res = await fetch(`http://localhost:8000/claims/popular`);
      if (res.ok) {
        const data = await res.json();
        setPopularClaims(data.popular_claims || []);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const fetchHistory = async () => {
    if (!session?.user) return;
    try {
      const userId = (session.user as any).id;
      const res = await fetch(`http://localhost:8000/sessions?user_id=${userId}`);
      if (res.ok) {
        const data = await res.json();
        setSessionHistory(data.sessions || []);
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    if (activeTab === "history") {
      fetchHistory();
    }
  }, [activeTab, session]);

  const loadSession = async (sid: number) => {
    if (!session?.user) return;
    try {
      const userId = (session.user as any).id;
      const res = await fetch(`http://localhost:8000/sessions/${sid}?user_id=${userId}`);
      if (res.ok) {
        const data = await res.json();
        setSessionId(data.id);
        setChatHistory(data.messages || []);
        setActiveTab("chat");
      }
    } catch (err) {
      console.error(err);
    }
  };

  const toggleBookmark = async (sid: number) => {
    if (!session?.user) return;
    try {
      const userId = (session.user as any).id;
      const res = await fetch(`http://localhost:8000/sessions/${sid}/bookmark?user_id=${userId}`, { method: "POST" });
      if (res.ok) {
        // Refresh history if in history tab
        if (activeTab === "history") fetchHistory();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleShare = (msg: ChatMessage) => {
    const textToShare = `[법률 팩트체크]\n\n요약: ${msg.section_1_summary || '요약 없음'}\n\n판정: ${msg.verdict || '확인불가'}\n${msg.section_2_law_explanation || ''}\n${msg.section_3_real_case_example || ''}\n${msg.section_4_caution || ''}`;
    navigator.clipboard.writeText(textToShare).then(() => {
      alert("결과가 클립보드에 복사되었습니다!");
    });
  };

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

  const submitQuery = async (text: string, imageToUpload: string | null = null) => {
    if (!text || !session?.user) return;

    const userQuery = text;
    const currentImage = imageToUpload;
    setQuery("");
    if (imageToUpload === selectedImage) {
      setSelectedImage(null);
    }
    setChatHistory((prev) => [...prev, { role: "user", content: userQuery, attached_image: currentImage || undefined }]);
    setLoading(true);

    try {
      const userId = (session.user as any).id;
      const response = await fetch(`http://localhost:8000/check?user_id=${userId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query: userQuery,
          session_id: sessionId,
          image_data: currentImage
        }),
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
            section_1_summary: data.result?.section_1_summary || "응답을 생성할 수 없습니다.",
            section_2_law_explanation: data.result?.section_2_law_explanation,
            section_3_real_case_example: data.result?.section_3_real_case_example,
            section_4_caution: data.result?.section_4_caution,
            section_5_counseling_recommendation: data.result?.section_5_counseling_recommendation,
            section_6_suggested_followups: data.result?.section_6_suggested_followups,
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

  const handleCheck = async (e: React.FormEvent) => {
    e.preventDefault();
    submitQuery(query, selectedImage);
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
              <button
                onClick={() => setActiveTab("history")}
                className={`pb-2 px-2 text-sm font-medium transition-colors ${activeTab === "history" ? "text-indigo-400 border-b-2 border-indigo-400" : "text-gray-400 hover:text-gray-200"}`}
              >
                내 이력 및 북마크
              </button>
            </div>

            {activeTab === "chat" ? (
              <>
                <div className="flex-grow overflow-y-auto space-y-6 pr-2 custom-scrollbar pb-6 rounded-xl">
                  {chatHistory.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-gray-500">
                      <p>궁금한 법률 질문을 편하게 입력해주세요.</p>

                      {popularClaims.length > 0 && (
                        <div className="mt-8 overflow-hidden max-w-2xl w-full">
                          <h4 className="text-sm font-bold text-gray-400 mb-4 flex items-center justify-center">
                            <span className="mr-2">🔥</span>실시간 인기 팩트체크
                          </h4>
                          <div className="flex flex-wrap gap-2 justify-center">
                            {popularClaims.map((claim, cIdx) => (
                              <button
                                key={cIdx}
                                onClick={() => setQuery(claim)}
                                className="bg-gray-800 hover:bg-gray-700 border border-gray-700 hover:border-indigo-500 text-gray-300 px-4 py-2 rounded-full text-sm transition-all shadow-sm"
                              >
                                {claim}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    chatHistory.map((msg, idx) => (
                      <div key={idx} className={`flex w-full ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                        <div className={`max-w-[85%] rounded-2xl p-5 ${msg.role === "user"
                          ? "bg-indigo-600 text-white rounded-br-none shadow-md"
                          : "bg-gray-800/80 border border-gray-700/50 text-gray-100 rounded-bl-none shadow-lg"
                          }`}>

                          {msg.role === "user" ? (
                            <div>
                              {msg.attached_image && (
                                <div className="mb-3">
                                  <img src={msg.attached_image} alt="User attachment" className="max-w-xs rounded-xl shadow-sm border border-indigo-400" />
                                </div>
                              )}
                              <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                            </div>
                          ) : (
                            <div className="flex flex-col space-y-4">
                              {/* Rendering parsed AI Response */}
                              {msg.verdict && (
                                <div className="mb-2">
                                  {getVerdictBadge(msg.verdict)}
                                </div>
                              )}

                              {msg.section_1_summary ? (
                                <div className="text-gray-100 font-medium leading-relaxed whitespace-pre-wrap text-[16px] mb-2 p-3 bg-gray-900/60 rounded-xl border border-gray-700/50">
                                  <h4 className="text-sm text-indigo-300 font-bold mb-1 flex items-center">
                                    <span className="mr-2">📝</span>핵심 요약
                                  </h4>
                                  {msg.section_1_summary}
                                </div>
                              ) : (
                                <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                              )}

                              {msg.section_2_law_explanation && (
                                <div className="text-gray-300 leading-relaxed whitespace-pre-wrap text-[15px] pt-2">
                                  <h4 className="text-sm text-blue-300 font-bold mb-1 flex items-center">
                                    <span className="mr-2">⚖️</span>법 조문 기준 설명
                                  </h4>
                                  <div className="pl-6 border-l-2 border-blue-500/30">
                                    {msg.section_2_law_explanation}
                                  </div>
                                </div>
                              )}

                              {msg.section_3_real_case_example && (
                                <div className="bg-gray-900/40 p-3 rounded-lg border border-gray-700/30 mt-3">
                                  <h4 className="text-sm text-indigo-400 font-bold mb-1 flex items-center">
                                    <span className="mr-2">💡</span>현실 적용 예시
                                  </h4>
                                  <p className="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap">{msg.section_3_real_case_example}</p>
                                </div>
                              )}

                              {msg.section_4_caution && (
                                <div className="bg-yellow-900/10 p-3 rounded-lg border border-yellow-700/30 mt-3">
                                  <h4 className="text-sm text-yellow-500 font-bold mb-1 flex items-center">
                                    <span className="mr-2">⚠️</span>주의사항
                                  </h4>
                                  <p className="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap">{msg.section_4_caution}</p>
                                </div>
                              )}

                              {msg.section_5_counseling_recommendation && (
                                <div className="bg-red-900/10 p-3 rounded-lg border border-red-900/30 mt-3">
                                  <h4 className="text-sm text-red-400 font-bold mb-1 flex items-center">
                                    <span className="mr-2">👩‍⚖️</span>전문가 상담 건의
                                  </h4>
                                  <p className="text-sm text-red-200/80 leading-relaxed whitespace-pre-wrap">{msg.section_5_counseling_recommendation}</p>
                                </div>
                              )}

                              {/* Suggested Follow-ups */}
                              {msg.section_6_suggested_followups && msg.section_6_suggested_followups.length > 0 && (
                                <div className="mt-4 pt-3 border-t border-gray-600/50">
                                  <h4 className="text-sm text-indigo-300 font-bold mb-3 flex items-center">
                                    <span className="mr-2">💬</span>추천 후속 질문
                                  </h4>
                                  <div className="flex flex-wrap gap-2">
                                    {msg.section_6_suggested_followups.map((q, qIdx) => (
                                      <button
                                        key={qIdx}
                                        onClick={() => submitQuery(q)}
                                        className="bg-gray-800 hover:bg-indigo-600/80 border border-indigo-500/50 text-indigo-200 hover:text-white px-4 py-2 rounded-full text-sm transition-all shadow-sm text-left"
                                      >
                                        {q}
                                      </button>
                                    ))}
                                  </div>
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

                              {/* Actions */}
                              <div className="mt-3 pt-3 flex items-center gap-3 border-t border-gray-700/30">
                                <button
                                  onClick={() => handleShare(msg)}
                                  className="text-xs flex items-center gap-1 text-gray-400 hover:text-indigo-400 transition"
                                >
                                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"></path></svg>
                                  공유하기
                                </button>
                                {idx === chatHistory.length - 1 && sessionId && (
                                  <button
                                    onClick={() => toggleBookmark(sessionId)}
                                    className="text-xs flex items-center gap-1 text-gray-400 hover:text-yellow-400 transition"
                                  >
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"></path></svg>
                                    세션 북마크
                                  </button>
                                )}
                              </div>
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
                  {selectedImage && (
                    <div className="mb-3 relative inline-block">
                      <img src={selectedImage} alt="Preview" className="h-20 w-20 object-cover rounded-xl border-2 border-indigo-500 shadow-md" />
                      <button
                        onClick={() => setSelectedImage(null)}
                        className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full w-5 h-5 flex items-center justify-center shadow hover:bg-red-600 font-bold"
                      >
                        ✕
                      </button>
                    </div>
                  )}
                  <form onSubmit={handleCheck} className="relative group w-full">
                    <div className="absolute -inset-1 bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl blur opacity-25 transition duration-1000 group-focus-within:opacity-50 group-hover:opacity-50"></div>
                    <div className="relative flex items-center bg-gray-900 rounded-2xl p-1 border border-gray-700/50 shadow-2xl">

                      {/* Image Upload Button */}
                      <label className="cursor-pointer text-gray-400 hover:text-indigo-400 p-3 transition-colors">
                        <input type="file" accept="image/*" className="hidden" onChange={handleImageUpload} />
                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"></path>
                        </svg>
                      </label>

                      <input
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="질문을 입력하세요... (계약서, 명세서 등 이미지 첨부 가능)"
                        className="flex-grow bg-transparent text-white placeholder-gray-500 px-3 py-4 focus:outline-none"
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
            ) : activeTab === "search" ? (
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
            ) : (
              <div className="flex-grow flex flex-col h-full overflow-hidden pb-4">
                <h2 className="text-xl font-bold mb-4 text-indigo-300">이전 팩트체크 기록</h2>
                <div className="flex-grow overflow-y-auto space-y-3 custom-scrollbar pr-2">
                  {sessionHistory.length === 0 ? (
                    <div className="text-center text-gray-500 mt-10 flex flex-col items-center">
                      <svg className="w-16 h-16 text-gray-700 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path></svg>
                      <p>이전 기록이 없습니다.</p>
                      <p className="text-sm mt-1">대화를 시작하여 팩트체크 기록을 남겨보세요.</p>
                    </div>
                  ) : (
                    sessionHistory.map((sess, idx) => (
                      <div key={idx} className="bg-gray-800 border border-gray-700/50 hover:border-indigo-500/50 rounded-xl p-4 transition-all group flex justify-between items-center cursor-pointer shadow-sm" onClick={() => loadSession(sess.id)}>
                        <div className="overflow-hidden pr-4 flex-grow">
                          <h3 className="text-gray-200 font-medium truncate mb-1">
                            {sess.title || "새 질문"}
                          </h3>
                          <p className="text-xs text-gray-500">
                            {new Date(sess.updated_at).toLocaleString()}
                          </p>
                        </div>
                        <div className="flex items-center gap-2 flex-shrink-0">
                          <button
                            onClick={(e) => { e.stopPropagation(); toggleBookmark(sess.id); }}
                            className={`p-2 rounded-full transition-colors ${sess.is_bookmarked ? "text-yellow-400 bg-yellow-400/10" : "text-gray-500 hover:text-yellow-400 hover:bg-gray-700"}`}
                            title="북마크"
                          >
                            <svg className="w-5 h-5" fill={sess.is_bookmarked ? "currentColor" : "none"} stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"></path></svg>
                          </button>
                        </div>
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
