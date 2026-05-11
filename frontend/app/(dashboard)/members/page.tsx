"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { UserPlus, Trash2, Users, Mail } from "lucide-react";
import { invitesApi, orgsApi } from "@/lib/api";
import { MemberResponse } from "@/types/Orgs";
import { InviteResponse } from "@/types/Invites";
import { useOrg } from "@/contexts/org";
import { sileo } from "sileo";
import { Skeleton } from "@/components/ui/skeleton";
import { Avatar } from "@/components/avatar";

// ── Empty states ─────────────────────────────────────────────────────────────────
function EmptyMembers({ orgName }: { orgName: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="rounded-full bg-muted p-4 mb-4">
        <Users className="h-8 w-8 text-muted-foreground" />
      </div>
      <h3 className="font-semibold text-lg mb-1">No members yet</h3>
      <p className="text-muted-foreground text-sm max-w-xs">
        Invite your team to collaborate in {orgName}.
      </p>
    </div>
  );
}

function EmptyInvites() {
  return (
    <div className="flex flex-col items-center justify-center py-10 text-center">
      <div className="rounded-full bg-muted p-3 mb-3">
        <Mail className="h-6 w-6 text-muted-foreground" />
      </div>
      <p className="text-muted-foreground text-sm">No pending invites.</p>
    </div>
  );
}

// ── Skeleton ─────────────────────────────────────────────────────────────────
function MembersSkeleton() {
  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <Skeleton className="h-9 w-36" />
          <Skeleton className="h-4 w-48 mt-2" />
        </div>
        <Skeleton className="h-9 w-36" />
      </div>
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-24" />
        </CardHeader>
        <CardContent className="p-0">
          <div className="divide-y">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="flex items-center gap-4 px-6 py-4">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-4 w-48" />
                <Skeleton className="h-6 w-20" />
                <Skeleton className="h-4 w-24" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ── Role badge ────────────────────────────────────────────────────────────────
function RoleBadge({ role }: { role: string }) {
  const variants: Record<string, string> = {
    owner: "bg-primary text-primary-foreground",
    admin: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
    member: "bg-secondary text-secondary-foreground",
  };
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${variants[role] ?? variants.member}`}
    >
      {role}
    </span>
  );
}

// ── Invite dialog ─────────────────────────────────────────────────────────────
function InviteDialog({
  orgId,
  onInvited,
}: {
  orgId: string;
  onInvited: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("member");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await invitesApi.create(orgId, email, role);
      setOpen(false);
      setEmail("");
      setRole("member");
      onInvited();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send invite");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">
          <UserPlus className="mr-2 h-4 w-4" />
          Invite member
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Invite a member</DialogTitle>
          <DialogDescription>
            They&apos;ll receive an email with a link to join your organisation.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="space-y-4 py-4">
            {error && <p className="text-sm text-destructive">{error}</p>}
            <div className="space-y-2">
              <Label htmlFor="invite-email">Email address</Label>
              <Input
                id="invite-email"
                type="email"
                placeholder="colleague@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="invite-role">Role</Label>
              <Select value={role} onValueChange={setRole}>
                <SelectTrigger id="invite-role">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="member">Member</SelectItem>
                  <SelectItem value="admin">Admin</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setOpen(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? "Sending…" : "Send invite"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function MembersPage() {
  const { activeOrg } = useOrg();
  const [members, setMembers] = useState<MemberResponse[]>([]);
  const [invites, setInvites] = useState<InviteResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const isAdmin = activeOrg?.role === "admin" || activeOrg?.role === "owner";

  async function load() {
    if (!activeOrg) return;
    setLoading(true);
    try {
      const [m, i] = await Promise.all([
        orgsApi.listMembers(activeOrg.id),
        isAdmin ? invitesApi.list(activeOrg.id) : Promise.resolve([]),
      ]);
      setMembers(m);
      setInvites(i);
    } catch {
      setError("Failed to load members");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      if (!cancelled) await load();
    };
    run();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeOrg?.id]);

  async function handleRemove(userId: string) {
    if (!activeOrg || !confirm("Remove this member?")) return;
    try {
      await orgsApi.removeMember(activeOrg.id, userId);
      setMembers((prev) => prev.filter((m) => m.user_id !== userId));
    } catch (err) {
      sileo.error({
        title: "Failed to remove member",
        description: err instanceof Error ? err.message : undefined,
      });
    }
  }

  async function handleRoleChange(userId: string, newRole: string) {
    if (!activeOrg) return;
    await orgsApi.updateMemberRole(activeOrg.id, userId, newRole).catch(() => {
      sileo.error({ title: "Failed to load members" });
      setLoading(false);
    });
    setMembers((prev) =>
      prev.map((m) => (m.user_id === userId ? { ...m, role: newRole } : m)),
    );
  }

  async function handleRevokeInvite(inviteId: string) {
    if (!activeOrg || !confirm("Revoke this invite?")) return;
    await invitesApi.revoke(activeOrg.id, inviteId).catch(() => {
      sileo.error({ title: "Failed to load members" });
      setLoading(false);
    });
    setInvites((prev) => prev.filter((i) => i.id !== inviteId));
  }

  if (loading) return <MembersSkeleton />;
  if (error) return <div className="text-destructive text-sm">{error}</div>;

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Members</h1>
          <p className="text-muted-foreground mt-1">
            {members.length} member{members.length !== 1 ? "s" : ""} in{" "}
            {activeOrg?.name}
          </p>
        </div>
        {isAdmin && activeOrg && (
          <InviteDialog orgId={activeOrg.id} onInvited={load} />
        )}
      </div>

      {/* Members table */}
      <Card>
        <CardHeader>
          <CardTitle>Members</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Joined</TableHead>
                {isAdmin && <TableHead className="w-20" />}
              </TableRow>
            </TableHeader>
            <TableBody>
              {members.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={isAdmin ? 5 : 4}>
                    <EmptyMembers
                      orgName={activeOrg?.name ?? "this organisation"}
                    />
                  </TableCell>
                </TableRow>
              ) : (
                members.map((member) => (
                  <TableRow key={member.user_id}>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2">
                        <Avatar
                          name={member.full_name}
                          avatarUrl={member.avatar_url}
                          size="sm"
                        />
                        <span className="font-medium">
                          {member.full_name ?? "—"}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {member.email}
                    </TableCell>
                    <TableCell>
                      {isAdmin && member.role !== "owner" ? (
                        <Select
                          value={member.role}
                          onValueChange={(v) =>
                            handleRoleChange(member.user_id, v)
                          }
                        >
                          <SelectTrigger className="w-28 h-7 text-xs">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="member">Member</SelectItem>
                            <SelectItem value="admin">Admin</SelectItem>
                          </SelectContent>
                        </Select>
                      ) : (
                        <RoleBadge role={member.role} />
                      )}
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {new Date(member.joined_at).toLocaleDateString()}
                    </TableCell>
                    {isAdmin && (
                      <TableCell>
                        {member.role !== "owner" && (
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 text-muted-foreground hover:text-destructive"
                            onClick={() => handleRemove(member.user_id)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        )}
                      </TableCell>
                    )}
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Pending invites — admins/owners only */}
      {isAdmin && (
        <Card>
          <CardHeader>
            <CardTitle>Pending invites</CardTitle>
            <CardDescription>
              These invites have been sent but not yet accepted.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            {invites.length === 0 ? (
              <EmptyInvites />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Email</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Invited by</TableHead>
                    <TableHead>Expires</TableHead>
                    <TableHead className="w-20" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {invites.map((invite) => (
                    <TableRow key={invite.id}>
                      <TableCell className="font-medium">
                        {invite.email}
                      </TableCell>
                      <TableCell>
                        <RoleBadge role={invite.role} />
                      </TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {invite.invited_by_email}
                      </TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {new Date(invite.expires_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 text-muted-foreground hover:text-destructive"
                          onClick={() => handleRevokeInvite(invite.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
