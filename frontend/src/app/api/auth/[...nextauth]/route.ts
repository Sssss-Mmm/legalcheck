import NextAuth, { NextAuthOptions } from "next-auth";
import GoogleProvider from "next-auth/providers/google";

export const authOptions: NextAuthOptions = {
    providers: [
        GoogleProvider({
            clientId: process.env.GOOGLE_CLIENT_ID || "MOCK_CLIENT_ID",
            clientSecret: process.env.GOOGLE_CLIENT_SECRET || "MOCK_CLIENT_SECRET",
        }),
        // Add more providers like Kakao if needed
    ],
    callbacks: {
        async signIn({ user, account, profile }) {
            try {
                // Upsert User in FastAPI Backend
                await fetch("http://localhost:8000/auth/login", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({
                        email: user.email,
                        name: user.name,
                        provider: account?.provider,
                        provider_id: account?.providerAccountId,
                        image_url: user.image,
                    }),
                });
                return true;
            } catch (e) {
                console.error("FastAPI Login Sync Error:", e);
                return true; // Still allow login, but DB sync failed
            }
        },
        async session({ session, token }) {
            // Pass the user ID or other info to the session if needed
            // Here we just fetch the backend user_id via email if desired, 
            // but to keep it simple, we will lookup by email in FastAPI or modify FastAPI to accept email as user identity.
            // Wait, our check endpoint requires user_id. We should fetch user_id.
            try {
                const res = await fetch("http://localhost:8000/auth/login", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ email: session.user?.email })
                });
                const data = await res.json();
                if (session.user) {
                    (session.user as any).id = data.id;
                }
            } catch (e) {
                console.error(e);
            }
            return session;
        },
    },
    secret: process.env.NEXTAUTH_SECRET || "secret_for_local_development",
};

const handler = NextAuth(authOptions);
export { handler as GET, handler as POST };
