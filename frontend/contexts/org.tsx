"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { useAuth } from "@/contexts/auth";
import { OrgWithRoleResponse } from "@/types/Orgs";
import { orgsApi } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────
interface OrgState {
  orgs: OrgWithRoleResponse[];
  activeOrg: OrgWithRoleResponse | null;
  loading: boolean;
  setActiveOrg: (org: OrgWithRoleResponse) => void;
  refresh: () => Promise<void>;
}

const ORG_STORAGE_KEY = "active_org_id";

// ── Context ───────────────────────────────────────────────────────────────────
const OrgContext = createContext<OrgState | null>(null);

export function OrgProvider({ children }: { children: React.ReactNode }) {
  const { user, loading: authLoading } = useAuth();
  const [orgs, setOrgs] = useState<OrgWithRoleResponse[]>([]);
  const [activeOrg, setActiveOrgState] = useState<OrgWithRoleResponse | null>(
    null,
  );

  const [loading, setLoading] = useState(true);

  const fetchOrgs = useCallback(async () => {
    if (!user) {
      setOrgs([]);
      setActiveOrgState(null);
      setLoading(false);
      return;
    }
    try {
      const data = await orgsApi.list();
      setOrgs(data);
      const storedId = localStorage.getItem(ORG_STORAGE_KEY);
      const restored = data.find((o) => o.id === storedId) ?? data[0] ?? null;
      setActiveOrgState(restored);
    } catch {
      setOrgs([]);
      setActiveOrgState(null);
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    if (authLoading) return;
    let cancelled = false;
    const run = async () => {
      if (!cancelled) await fetchOrgs();
    };
    run();
    return () => {
      cancelled = true;
    };
  }, [fetchOrgs, authLoading]);

  const setActiveOrg = useCallback((org: OrgWithRoleResponse) => {
    setActiveOrgState(org);
    localStorage.setItem(ORG_STORAGE_KEY, org.id);
  }, []);

  return (
    <OrgContext.Provider
      value={{
        orgs,
        activeOrg,
        loading,
        setActiveOrg,
        refresh: fetchOrgs,
      }}
    >
      {children}
    </OrgContext.Provider>
  );
}

// ── Hook ──────────────────────────────────────────────────────────────────────
export function useOrg(): OrgState {
  const ctx = useContext(OrgContext);
  if (!ctx) throw new Error("useOrg must be used inside <OrgProvider>");
  return ctx;
}
