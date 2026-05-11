"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useOrg } from "@/contexts/org";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { orgsApi } from "@/lib/api";

export default function NewOrgPage() {
  const router = useRouter();
  const { refresh, setActiveOrg } = useOrg();

  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const org = await orgsApi.create(name);
      // Refresh the org list and set the new org as active
      await refresh();
      setActiveOrg({ ...org, role: "owner" });
      router.push("/");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to create organisation",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle className="text-2xl">Create an organisation</CardTitle>
          <CardDescription>
            Organisations are shared spaces where teams collaborate.
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            {error && <p className="text-sm text-destructive">{error}</p>}
            <div className="space-y-2">
              <Label htmlFor="name">Organisation name</Label>
              <Input
                id="name"
                type="text"
                placeholder="Acme Corp"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                autoFocus
              />
            </div>
          </CardContent>
          <CardFooter>
            <Button
              type="submit"
              className="w-full"
              disabled={loading || !name.trim()}
            >
              {loading ? "Creating…" : "Create organisation"}
            </Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
