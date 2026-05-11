"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { tokens } from "@/lib/api";

export default function AuthCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const accessToken = searchParams.get("access_token");
    const refreshToken = searchParams.get("refresh_token");
    const error = searchParams.get("error");

    if (error) {
      router.replace(`/login?error=${encodeURIComponent(error)}`);
      return;
    }

    if (!accessToken || !refreshToken) {
      router.replace("/login?error=Missing+tokens");
      return;
    }

    tokens.set(accessToken, refreshToken);
    router.replace("/");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <p className="text-muted-foreground text-sm">Signing you in…</p>
    </div>
  );
}
