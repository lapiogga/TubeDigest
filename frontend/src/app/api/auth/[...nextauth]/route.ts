import NextAuth from "next-auth";
import GoogleProvider from "next-auth/providers/google";

// H-1: 환경변수 미설정 시 서버 기동 차단
const clientId = process.env.GOOGLE_CLIENT_ID;
const clientSecret = process.env.GOOGLE_CLIENT_SECRET;
if (!clientId || !clientSecret) {
    throw new Error("GOOGLE_CLIENT_ID 또는 GOOGLE_CLIENT_SECRET 환경변수가 설정되지 않았습니다.");
}

const handler = NextAuth({
    providers: [
        GoogleProvider({
            clientId,
            clientSecret,
            authorization: {
                params: {
                    scope: "openid email profile https://www.googleapis.com/auth/youtube",
                    prompt: "consent",
                    access_type: "offline",
                    response_type: "code",
                },
            },
        }),
    ],
    callbacks: {
        async jwt({ token, account, user }) {
            if (account && user) {
                token.accessToken = account.access_token;
                token.refreshToken = account.refresh_token;

                try {
                    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
                    const syncSecret = process.env.NEXTAUTH_SYNC_SECRET;
                    const res = await fetch(`${apiUrl}/api/auth/sync`, {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                            ...(syncSecret ? { "X-Sync-Secret": syncSecret } : {}),
                        },
                        body: JSON.stringify({
                            google_id: token.sub || account.providerAccountId,
                            email: user.email || "",
                            name: user.name || "",
                            access_token: account.access_token,
                            refresh_token: account.refresh_token || null,
                        }),
                    });
                    if (res.ok) {
                        const data = await res.json();
                        if (data.status === "success") {
                            // backendToken은 JWT에만 저장 — 클라이언트 session에 미노출 (C-1 수정)
                            token.backendToken = data.token;
                        }
                    } else {
                        // H-4: sync 실패 플래그 저장 → session에서 UX 처리 가능
                        token.syncFailed = true;
                    }
                } catch (e) {
                    console.error("Failed to sync user to backend", e);
                    token.syncFailed = true;
                }
            }
            return token;
        },
        async session({ session, token }) {
            session.accessToken = token.accessToken as string;
            // C-1 수정: backendToken을 session에서 제거 — 서버 사이드 getToken()으로만 접근
            // H-4: sync 실패 여부를 클라이언트에 전달
            session.syncFailed = token.syncFailed as boolean | undefined;
            return session;
        },
    },
    secret: process.env.NEXTAUTH_SECRET,
});

export { handler as GET, handler as POST };
