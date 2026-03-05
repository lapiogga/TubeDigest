"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import Image from "next/image";
import { signIn, signOut, useSession } from "next-auth/react";
import { Youtube, LogOut, LayoutDashboard, VideoIcon, RefreshCw, AlertCircle, ChevronRight } from "lucide-react";

interface Video {
  video_id: string;
  title: string;
  published_at: string;
  thumbnail_url: string | null;
  ai_summary: string | null;
}

interface Subscription {
  id: number;
  channel_id: string;
  channel_title: string;
  thumbnail_url: string | null;
  category: string;
  videos: Video[];
}

export default function Home() {
  const { data: session, status } = useSession();

  const [isSyncing, setIsSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState("");

  const [categories, setCategories] = useState<string[]>([]);
  const [categoryCounts, setCategoryCounts] = useState<Record<string, number>>({});
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [isLoadingSubs, setIsLoadingSubs] = useState(false);
  const [expandedParents, setExpandedParents] = useState<Set<string>>(new Set());

  // 카테고리 문자열 → 계층 트리: { parent: [fullCategory, ...] }
  const hierarchy = useMemo(() => {
    const tree: Record<string, string[]> = {};
    for (const cat of categories) {
      const sepIdx = cat.indexOf(" > ");
      if (sepIdx !== -1) {
        const parent = cat.substring(0, sepIdx);
        if (!tree[parent]) tree[parent] = [];
        tree[parent].push(cat);
      } else {
        if (!tree[cat]) tree[cat] = [];
      }
    }
    return tree;
  }, [categories]);

  // 카테고리 로드 시 모든 부모 자동 펼치기
  useEffect(() => {
    const parents = new Set<string>();
    for (const cat of categories) {
      const sepIdx = cat.indexOf(" > ");
      if (sepIdx !== -1) parents.add(cat.substring(0, sepIdx));
    }
    setExpandedParents(parents);
  }, [categories]);

  // H-3: useCallback으로 메모이제이션 — C-1 수정: Bearer 헤더 불필요 (프록시 경유)
  const apiFetch = useCallback(async (path: string, options?: RequestInit) => {
    const res = await fetch(path, options);
    if (!res.ok) throw new Error(`API 오류 ${res.status}`);
    return res.json();
  }, []);

  const fetchCategories = useCallback(async () => {
    const data = await apiFetch("/api/youtube/categories");
    setCategories(data.categories ?? []);
    setCategoryCounts(data.category_counts ?? {});
  }, [apiFetch]);

  // 카테고리 목록 조회
  useEffect(() => {
    if (!session) return;
    fetchCategories().catch(console.error);
  }, [session, fetchCategories]);

  // 카테고리 선택 시 구독 목록 조회
  useEffect(() => {
    if (!session) return;
    setIsLoadingSubs(true);
    apiFetch(`/api/youtube/subscriptions?category=${selectedCategory}`)
      .then((data) => setSubscriptions(data.subscriptions ?? []))
      .catch(console.error)
      .finally(() => setIsLoadingSubs(false));
  }, [session, selectedCategory, apiFetch]);

  const handleSync = async () => {
    if (!session) return;
    setIsSyncing(true);
    setSyncMessage("");
    try {
      const data = await apiFetch("/api/youtube/sync-subscriptions", { method: "POST" });
      if (data.status === "success") {
        setSyncMessage(`${data.synced_count}개 채널, ${data.synced_videos ?? 0}개 영상 동기화 완료!`);
        await fetchCategories();
        setSelectedCategory("all");
      } else {
        setSyncMessage("동기화 실패. 다시 시도해 주세요.");
      }
    } catch {
      setSyncMessage("서버 연결 오류.");
    } finally {
      setIsSyncing(false);
    }
  };

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleDateString("ko-KR", { month: "short", day: "numeric" });
    } catch {
      return dateStr;
    }
  };

  if (status === "loading") {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="flex bg-background h-screen items-center justify-center p-4">
        <div className="w-full max-w-md bg-card border border-border rounded-xl shadow-lg p-8 text-center space-y-6">
          <div className="flex justify-center mb-6">
            <div className="bg-primary/10 p-4 rounded-full">
              <Youtube className="w-12 h-12 text-primary" />
            </div>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">TubeDigest</h1>
          <p className="text-muted-foreground text-sm">
            AI 기반 YouTube 구독 분류 및 주간 요약 서비스.
          </p>
          <button
            onClick={() => signIn("google")}
            className="w-full bg-primary hover:bg-primary/90 text-primary-foreground transition-colors font-medium py-3 rounded-lg flex items-center justify-center gap-3 shadow-md"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
              <path d="M1 1h22v22H1z" fill="none" />
            </svg>
            Google로 로그인
          </button>
        </div>
      </div>
    );
  }

  // H-4: sync 실패 시 사용자에게 안내
  if (session.syncFailed) {
    return (
      <div className="flex bg-background h-screen items-center justify-center p-4">
        <div className="w-full max-w-md bg-card border border-border rounded-xl shadow-lg p-8 text-center space-y-4">
          <AlertCircle className="w-12 h-12 text-destructive mx-auto" />
          <h2 className="text-xl font-bold text-foreground">서버 연동 실패</h2>
          <p className="text-muted-foreground text-sm">
            백엔드 서버와 연결에 실패했습니다. 잠시 후 다시 로그인해 주세요.
          </p>
          <button
            onClick={() => signOut()}
            className="w-full bg-secondary text-secondary-foreground py-2 rounded-lg hover:bg-secondary/80 transition-colors"
          >
            로그아웃
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      {/* 헤더 */}
      <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="container mx-auto max-w-7xl px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Youtube className="w-8 h-8 text-primary" />
            <span className="text-xl font-bold tracking-tight">TubeDigest</span>
          </div>
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-3">
              <Image
                src={session?.user?.image || `https://ui-avatars.com/api/?name=${session?.user?.name}`}
                alt="프로필"
                width={32}
                height={32}
                className="rounded-full border border-border"
              />
              <span className="text-sm font-medium hidden sm:block">{session?.user?.name}</span>
            </div>
            <button
              onClick={() => signOut()}
              className="text-muted-foreground hover:text-foreground transition-colors p-2 rounded-md hover:bg-muted"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>

      <main className="flex-1 container mx-auto max-w-7xl px-4 py-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* 사이드바 */}
          <aside className="space-y-6">
            <div className="bg-card border border-border rounded-xl p-5 shadow-sm">
              <h2 className="font-semibold text-lg flex items-center gap-2 mb-4">
                <LayoutDashboard className="w-5 h-5 text-primary" />
                카테고리
              </h2>
              <ul className="max-h-[800px] overflow-y-auto pr-1">
                <li>
                  <button
                    onClick={() => setSelectedCategory("all")}
                    className={`w-full text-left px-3 py-1 rounded-md font-medium text-sm transition-colors ${
                      selectedCategory === "all"
                        ? "bg-primary/10 text-primary"
                        : "text-muted-foreground hover:bg-muted"
                    }`}
                  >
                    전체 채널
                  </button>
                </li>
                {categories.length === 0 ? (
                  <li className="text-xs text-muted-foreground px-3 py-2">
                    동기화 후 카테고리가 표시됩니다.
                  </li>
                ) : (
                  Object.entries(hierarchy).map(([parent, children]) => {
                    const hasChildren = children.length > 0;
                    const isExpanded = expandedParents.has(parent);

                    const parentCount = hasChildren
                      ? children.reduce((sum, c) => sum + (categoryCounts[c] ?? 0), 0)
                      : (categoryCounts[parent] ?? 0);

                    if (parentCount === 0) return null;

                    if (!hasChildren) {
                      // 단독 리프 카테고리
                      return (
                        <li key={parent}>
                          <button
                            onClick={() => setSelectedCategory(parent)}
                            className={`w-full text-left px-3 py-1 rounded-md text-sm font-medium transition-colors flex items-center justify-between gap-1 ${
                              selectedCategory === parent
                                ? "bg-primary/10 text-primary"
                                : "text-muted-foreground hover:bg-muted"
                            }`}
                          >
                            <span>{parent}</span>
                            <span className="text-xs opacity-60">({parentCount})</span>
                          </button>
                        </li>
                      );
                    }

                    // 부모 + 자식 구조
                    return (
                      <li key={parent} className="mt-1">
                        {/* 부모 헤더: 접기/펼치기 + 전체 필터 */}
                        <button
                          onClick={() => {
                            setExpandedParents((prev) => {
                              const next = new Set(prev);
                              if (next.has(parent)) next.delete(parent);
                              else next.add(parent);
                              return next;
                            });
                            setSelectedCategory(parent);
                          }}
                          className={`w-full text-left px-3 py-0.5 rounded-md text-xs font-semibold tracking-wide uppercase transition-colors flex items-center justify-between gap-1 ${
                            selectedCategory === parent
                              ? "text-primary"
                              : "text-muted-foreground/60 hover:text-muted-foreground"
                          }`}
                        >
                          <span className="flex items-center gap-1">
                            {parent}
                            <span className="font-normal opacity-60">({parentCount})</span>
                          </span>
                          <ChevronRight
                            className={`w-3 h-3 flex-shrink-0 transition-transform duration-200 ${
                              isExpanded ? "rotate-90" : ""
                            }`}
                          />
                        </button>

                        {/* 자식 목록 */}
                        {isExpanded && (
                          <ul className="mt-0.5 ml-2 pl-2 border-l border-border">
                            {children.map((child) => {
                              const label = child.split(" > ").slice(1).join(" > ");
                              const count = categoryCounts[child] ?? 0;
                              return (
                                <li key={child}>
                                  <button
                                    onClick={() => setSelectedCategory(child)}
                                    className={`w-full text-left px-2 py-1 rounded-md text-sm transition-colors flex items-center justify-between gap-1 ${
                                      selectedCategory === child
                                        ? "bg-primary/10 text-primary font-medium"
                                        : "text-muted-foreground hover:bg-muted"
                                    }`}
                                  >
                                    <span>{label}</span>
                                    <span className="text-xs opacity-60">({count})</span>
                                  </button>
                                </li>
                              );
                            })}
                          </ul>
                        )}
                      </li>
                    );
                  })
                )}
              </ul>

              <div className="mt-6 space-y-3">
                <button
                  onClick={handleSync}
                  disabled={isSyncing}
                  className="w-full py-2.5 bg-secondary text-secondary-foreground text-sm font-medium rounded-lg hover:bg-secondary/80 transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  <RefreshCw className={`w-4 h-4 ${isSyncing ? "animate-spin" : ""}`} />
                  {isSyncing ? "동기화 중..." : "구독 동기화"}
                </button>
                {syncMessage && (
                  <p className="text-xs text-center text-muted-foreground bg-muted py-2 rounded-md border border-border">
                    {syncMessage}
                  </p>
                )}
              </div>
            </div>
          </aside>

          {/* 메인 콘텐츠 */}
          <div className="md:col-span-3 space-y-6">
            <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
              <h2 className="text-2xl font-bold mb-6 flex items-center gap-2">
                <VideoIcon className="w-6 h-6 text-primary" />
                최근 영상 요약
                {selectedCategory !== "all" && (
                  <span className="text-sm font-normal text-muted-foreground ml-2">
                    — {selectedCategory}
                  </span>
                )}
              </h2>

              {isLoadingSubs ? (
                <div className="flex justify-center py-12">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                </div>
              ) : subscriptions.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-muted-foreground gap-3">
                  <AlertCircle className="w-10 h-10 opacity-40" />
                  <p className="text-sm">
                    {categories.length === 0
                      ? "구독 동기화 버튼을 눌러 채널을 불러오세요."
                      : "이 카테고리에 채널이 없습니다."}
                  </p>
                </div>
              ) : (
                <div className="space-y-6">
                  {subscriptions.map((sub) => (
                    <div key={sub.id} className="border-b border-border pb-6 last:border-0 last:pb-0">
                      {/* 채널 헤더 */}
                      <div className="flex items-center gap-3 mb-3">
                        {sub.thumbnail_url ? (
                          <Image
                            src={sub.thumbnail_url}
                            alt={sub.channel_title}
                            width={36}
                            height={36}
                            className="w-9 h-9 rounded-full border border-border"
                          />
                        ) : (
                          <div className="w-9 h-9 rounded-full bg-muted flex items-center justify-center">
                            <Youtube className="w-4 h-4 text-muted-foreground" />
                          </div>
                        )}
                        <div>
                          <a
                            href={`https://www.youtube.com/channel/${sub.channel_id}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="font-semibold text-sm hover:text-primary hover:underline transition-colors"
                          >
                            {sub.channel_title}
                          </a>
                          <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded-full block w-fit mt-0.5">
                            {sub.category}
                          </span>
                        </div>
                      </div>

                      {/* 영상 목록 */}
                      {sub.videos.length === 0 ? (
                        <p className="text-xs text-muted-foreground pl-12">최근 영상이 없습니다.</p>
                      ) : (
                        <div className="space-y-4 pl-12">
                          {sub.videos.map((video) => (
                            <div key={video.video_id} className="flex gap-3">
                              <div className="relative w-32 h-[72px] bg-muted rounded-md flex-shrink-0 overflow-hidden">
                                {video.thumbnail_url && (
                                  <Image
                                    src={video.thumbnail_url}
                                    alt={video.title}
                                    fill
                                    className="object-cover"
                                  />
                                )}
                              </div>
                              <div className="flex-1 space-y-1">
                                <div className="flex items-start justify-between gap-2">
                                  <p className="font-medium text-sm leading-tight">{video.title}</p>
                                  <span className="text-xs text-muted-foreground whitespace-nowrap">
                                    {formatDate(video.published_at)}
                                  </span>
                                </div>
                                {video.ai_summary ? (
                                  <p className="text-xs text-muted-foreground leading-relaxed">
                                    {video.ai_summary}
                                  </p>
                                ) : (
                                  <p className="text-xs text-muted-foreground italic">
                                    요약 없음 — 요약 생성하려면 동기화 후 재시도
                                  </p>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
