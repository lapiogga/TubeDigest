import { DefaultSession } from "next-auth"

declare module "next-auth" {
    interface Session {
        accessToken?: string;
        refreshToken?: string;
        // C-1 수정: backendToken 제거 — 서버 사이드 getToken()으로만 접근
        syncFailed?: boolean;  // H-4: 백엔드 sync 실패 여부
        user: DefaultSession["user"]
    }
}

declare module "next-auth/jwt" {
    interface JWT {
        accessToken?: string;
        refreshToken?: string;
        backendToken?: string;  // JWT에만 보관 (서버 전용)
        syncFailed?: boolean;
    }
}
