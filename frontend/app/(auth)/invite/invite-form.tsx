"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useAuth } from "@/contexts/auth";
import { useOrg } from "@/contexts/org";
import { InvitePublicResponse } from "@/types/Invites";
import { invitesApi } from "@/lib/api";

type PageState =
  | "loading"
  | "invalid"
  | "ready"
  | "accepting"
  | "done"
  | "error";

export default function InviteForm() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const router = useRouter();
  const { user } = useAuth();
  const { refresh } = useOrg();

  const [invite, setInvite] = useState<InvitePublicResponse | null>(null);
  const [state, setState] = useState<PageState>(() =>
    token ? "loading" : "invalid",
  );
  const [errorMsg, setErrorMsg] = useState("");

  // Load invite details on mount
  useEffect(() => {
    if (!token) {
      return;
    }
    let cancelled = false;
    invitesApi
      .getByToken(token)
      .then((data) => {
        if (cancelled) return;
        setInvite(data);
        setState(data.is_valid ? "ready" : "invalid");
      })
      .catch(() => {
        if (!cancelled) setState("invalid");
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  async function handleAccept() {
    setState("accepting");
    try {
      await invitesApi.accept(token);
      await refresh(); // reload org list so the new org appears in the switcher
      setState("done");
    } catch (err) {
      setErrorMsg(
        err instanceof Error ? err.message : "Failed to accept invite",
      );
      setState("error");
    }
  }

  // ── Loading ──────────────────────────────────────────────────────────────
  if (state === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <p className="text-muted-foreground text-sm">Loading invite…</p>
      </div>
    );
  }

  // ── Invalid / expired ────────────────────────────────────────────────────
  if (state === "invalid" || !invite) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background px-4">
        <Card className="w-full max-w-sm text-center">
          <CardHeader>
            <CardTitle>Invite not found</CardTitle>
            <CardDescription>
              This invite link is invalid, expired, or has already been
              accepted.
            </CardDescription>
          </CardHeader>
          <CardFooter className="justify-center">
            <Button asChild variant="outline">
              <Link href="/">Go to dashboard</Link>
            </Button>
          </CardFooter>
        </Card>
      </div>
    );
  }

  // ── Done ─────────────────────────────────────────────────────────────────
  if (state === "done") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background px-4">
        <Card className="w-full max-w-sm text-center">
          <CardHeader>
            <CardTitle>You&apos;re in! 🎉</CardTitle>
            <CardDescription>
              You&apos;ve joined <strong>{invite.org_name}</strong> as a{" "}
              {invite.role}.
            </CardDescription>
          </CardHeader>
          <CardFooter className="justify-center">
            <Button onClick={() => router.push("/")}>Go to dashboard</Button>
          </CardFooter>
        </Card>
      </div>
    );
  }

  // ── Error ────────────────────────────────────────────────────────────────
  if (state === "error") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background px-4">
        <Card className="w-full max-w-sm text-center">
          <CardHeader>
            <CardTitle>Something went wrong</CardTitle>
            <CardDescription>{errorMsg}</CardDescription>
          </CardHeader>
          <CardFooter className="justify-center gap-3">
            <Button variant="outline" onClick={() => setState("ready")}>
              Try again
            </Button>
            <Button asChild variant="ghost">
              <Link href="/">Go to dashboard</Link>
            </Button>
          </CardFooter>
        </Card>
      </div>
    );
  }

  // ── Ready to accept ───────────────────────────────────────────────────────
  // If the user isn't logged in, send them to login first with a redirect back
  const loginUrl = `/login?redirect=${encodeURIComponent(`/invite?token=${token}`)}`;
  const registerUrl = `/register?redirect=${encodeURIComponent(`/invite?token=${token}`)}`;

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>You&apos;ve been invited</CardTitle>
          <CardDescription>
            Join <strong>{invite.org_name}</strong> as a{" "}
            <strong>{invite.role}</strong>.
          </CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          This invite was sent to <strong>{invite.email}</strong>.{" "}
          {!user && "Sign in with that email address to accept it."}
          {user && user.email !== invite.email && (
            <span className="text-destructive block mt-2">
              You&apos;re signed in as <strong>{user.email}</strong> but this
              invite is for <strong>{invite.email}</strong>. Please sign in with
              the correct account.
            </span>
          )}
        </CardContent>
        <CardFooter className="flex flex-col gap-3">
          {!user ? (
            <>
              <Button asChild className="w-full">
                <Link href={loginUrl}>Sign in to accept</Link>
              </Button>
              <Button asChild variant="outline" className="w-full">
                <Link href={registerUrl}>Create account</Link>
              </Button>
            </>
          ) : user.email === invite.email ? (
            <Button
              className="w-full"
              onClick={handleAccept}
              disabled={state === "accepting"}
            >
              {state === "accepting" ? "Joining…" : `Join ${invite.org_name}`}
            </Button>
          ) : (
            <Button asChild variant="outline" className="w-full">
              <Link href={loginUrl}>Sign in with the correct account</Link>
            </Button>
          )}
        </CardFooter>
      </Card>
    </div>
  );
}
