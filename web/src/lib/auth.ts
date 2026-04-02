import { type NextAuthOptions } from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";

const API_URL = process.env.API_URL || "http://localhost:8010";

/**
 * Refresh the backend JWT token before it expires.
 * Returns new token data or null if refresh fails.
 */
async function refreshAccessToken(token: Record<string, unknown>) {
  try {
    const res = await fetch(`${API_URL}/api/v1/auth/refresh`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token.accessToken}`,
      },
    });

    if (!res.ok) {
      // Token is already expired or invalid — force re-login
      return { ...token, error: "RefreshFailed" };
    }

    const data = await res.json();
    return {
      ...token,
      accessToken: data.access_token,
      // Refresh again 5 minutes before expiry (token lasts 60 min)
      accessTokenExpires: Date.now() + 55 * 60 * 1000,
    };
  } catch {
    return { ...token, error: "RefreshFailed" };
  }
}

export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      name: "MedBed Insight",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) return null;

        try {
          const res = await fetch(`${API_URL}/api/v1/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              email: credentials.email,
              password: credentials.password,
            }),
          });

          if (!res.ok) return null;

          const data = await res.json();
          return {
            id: data.user_id,
            email: data.email,
            accessToken: data.access_token,
            // Token expires in 60 min; refresh 5 min early
            accessTokenExpires: Date.now() + 55 * 60 * 1000,
          };
        } catch {
          return null;
        }
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      // Initial sign-in — store token + expiry
      if (user) {
        const u = user as unknown as Record<string, unknown>;
        token.accessToken = u.accessToken;
        token.accessTokenExpires = u.accessTokenExpires;
        token.userId = user.id;
        return token;
      }

      // Token still valid — return as-is
      if (
        typeof token.accessTokenExpires === "number" &&
        Date.now() < token.accessTokenExpires
      ) {
        return token;
      }

      // Token expired or about to expire — refresh it
      return await refreshAccessToken(token as Record<string, unknown>);
    },
    async session({ session, token }) {
      const s = session as unknown as Record<string, unknown>;
      s.accessToken = token.accessToken;
      s.error = token.error; // Pass refresh errors to client
      if (session.user) {
        const u = session.user as unknown as Record<string, unknown>;
        u.id = token.userId;
      }
      return session;
    },
  },
  pages: {
    signIn: "/login",
  },
  session: {
    strategy: "jwt",
    maxAge: 60 * 60, // 1 hour
  },
};
