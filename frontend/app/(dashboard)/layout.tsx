"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  ChevronsUpDown,
  Plus,
  Settings,
  Users,
  LayoutDashboard,
  LogOut,
  CreditCard,
} from "lucide-react";
import { useOrg } from "@/contexts/org";
import { useAuth } from "@/contexts/auth";
import { Skeleton } from "@/components/ui/skeleton";
import { ThemeToggle } from "@/components/theme-toggle";
import { Avatar } from "@/components/avatar";

function SidebarSkeleton() {
  return (
    <div className="flex h-screen bg-background">
      <aside className="w-56 border-r flex flex-col py-4 px-2 shrink-0">
        <div className="mb-4 px-1">
          <Skeleton className="h-9 w-full" />
        </div>
        <div className="flex-1 space-y-1">
          {[...Array(3)].map((_, i) => (
            <Skeleton key={i} className="h-9 w-full" />
          ))}
        </div>
        <div className="border-t pt-3 mt-3 px-1 space-y-2">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-9 w-full" />
        </div>
      </aside>
      <main className="flex-1 p-8">
        <Skeleton className="h-8 w-48 mb-2" />
        <Skeleton className="h-4 w-64" />
      </main>
    </div>
  );
}

function OrgSwitcher() {
  const { orgs, activeOrg, setActiveOrg } = useOrg();
  const router = useRouter();

  if (!activeOrg) return null;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          className="w-full justify-between px-2 font-medium"
        >
          <span className="truncate">{activeOrg.name}</span>
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-56" align="start">
        <DropdownMenuLabel className="text-xs text-muted-foreground">
          Organisations
        </DropdownMenuLabel>
        {orgs.map((org) => (
          <DropdownMenuItem
            key={org.id}
            onClick={() => setActiveOrg(org)}
            className="cursor-pointer"
          >
            <span className="truncate">{org.name}</span>
            {org.id === activeOrg.id && (
              <span className="ml-auto text-xs text-muted-foreground">
                Active
              </span>
            )}
          </DropdownMenuItem>
        ))}
        <DropdownMenuSeparator />
        <DropdownMenuItem
          className="cursor-pointer"
          onClick={() => router.push("/orgs/new")}
        >
          <Plus className="mr-2 h-4 w-4" />
          New organisation
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

const navItems = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/members", label: "Members", icon: Users },
  { href: "/billing", label: "Billing", icon: CreditCard },
  { href: "/settings", label: "Settings", icon: Settings },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, loading: authLoading, logout } = useAuth();
  const { activeOrg, loading: orgLoading } = useOrg();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!authLoading && !user) {
      router.replace("/login");
    }
  }, [user, authLoading, router]);

  // Redirect to org creation if user has no orgs
  useEffect(() => {
    if (authLoading || orgLoading) return;
    if (!user) return;
    if (!activeOrg && pathname !== "/orgs/new") {
      router.replace("/orgs/new");
    }
  }, [authLoading, orgLoading, user, activeOrg, router, pathname]);

  if (authLoading || orgLoading || !user) return <SidebarSkeleton />;

  function handleLogout() {
    logout();
    router.push("/login");
  }

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <aside className="w-56 border-r flex flex-col py-4 px-2 shrink-0">
        {/* Org switcher */}
        <div className="mb-4 px-1">
          <OrgSwitcher />
        </div>

        {/* Nav */}
        <nav className="flex-1 space-y-1">
          {navItems.map(({ href, label, icon: Icon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors ${
                  active
                    ? "bg-accent text-accent-foreground font-medium"
                    : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
                }`}
              >
                <Icon className="h-4 w-4 shrink-0" />
                {label}
              </Link>
            );
          })}
        </nav>

        {/* User + logout */}
        <div className="border-t pt-3 mt-3 px-1">
          <div className="flex items-center gap-2 px-2 mb-2">
            <Avatar
              name={user.full_name}
              avatarUrl={user.avatar_url ?? null}
              size="sm"
            />
            <span className="text-xs text-muted-foreground truncate">
              {user.email}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <Button
              variant="ghost"
              size="sm"
              className="flex-1 justify-start text-muted-foreground"
              onClick={handleLogout}
            >
              <LogOut className="mr-2 h-4 w-4" />
              Sign out
            </Button>
            <ThemeToggle />
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto p-8">{children}</main>
    </div>
  );
}
