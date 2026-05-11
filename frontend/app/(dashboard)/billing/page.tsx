"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { CheckCircle2, XCircle, Zap } from "lucide-react";
import { useOrg } from "@/contexts/org";
import { BillingStatus } from "@/types/Billing";
import { billingApi } from "@/lib/api";
import { sileo } from "sileo";
import { Skeleton } from "@/components/ui/skeleton";

function BillingSkeleton() {
  return (
    <div className="space-y-8">
      <div>
        <Skeleton className="h-9 w-28" />
        <Skeleton className="h-4 w-64 mt-2" />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-3xl pt-4">
        {[...Array(2)].map((_, i) => (
          <Card key={i} className="flex flex-col">
            <CardHeader>
              <div className="flex items-center justify-between">
                <Skeleton className="h-6 w-16" />
                <Skeleton className="h-8 w-16" />
              </div>
              <Skeleton className="h-4 w-full" />
            </CardHeader>
            <CardContent className="flex-1 space-y-3">
              {[...Array(3)].map((_, j) => (
                <Skeleton key={j} className="h-4 w-full" />
              ))}
            </CardContent>
            <CardFooter>
              <Skeleton className="h-9 w-full" />
            </CardFooter>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ── Plan details ──────────────────────────────────────────────────────────────
const PLANS = {
  free: {
    name: "Free",
    price: "$0",
    description: "For individuals and small teams getting started.",
    features: ["Up to 3 members", "Basic features", "Community support"],
  },
  pro: {
    name: "Pro",
    price: "$29",
    description: "For growing teams that need more power.",
    features: [
      "Unlimited members",
      "All features",
      "Priority support",
      "Advanced analytics",
    ],
  },
};

// ── Status badge ──────────────────────────────────────────────────────────────
function StatusBadge({ status }: { status: string | null }) {
  if (!status) return null;
  const styles: Record<string, string> = {
    active: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
    trialing: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
    past_due:
      "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
    canceled: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
    unpaid: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
  };
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium capitalize ${styles[status] ?? ""}`}
    >
      {status.replace("_", " ")}
    </span>
  );
}

// ── Plan card ─────────────────────────────────────────────────────────────────
function PlanCard({
  planKey,
  isCurrent,
  isOwner,
  onUpgrade,
  onManage,
  loading,
}: {
  planKey: "free" | "pro";
  isCurrent: boolean;
  isOwner: boolean;
  onUpgrade: () => void;
  onManage: () => void;
  loading: boolean;
}) {
  const plan = PLANS[planKey];

  return (
    <Card className={`flex flex-col ${isCurrent ? "border-primary" : ""}`}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CardTitle className="text-xl">{plan.name}</CardTitle>
            {isCurrent && (
              <span className="bg-primary text-primary-foreground text-xs font-medium px-2 py-0.5 rounded-full">
                Current
              </span>
            )}
          </div>
          <span className="text-2xl font-bold">
            {plan.price}
            {planKey !== "free" && (
              <span className="text-sm font-normal text-muted-foreground">
                /mo
              </span>
            )}
          </span>
        </div>
        <CardDescription>{plan.description}</CardDescription>
      </CardHeader>
      <CardContent className="flex-1">
        <ul className="space-y-2">
          {plan.features.map((feature) => (
            <li key={feature} className="flex items-center gap-2 text-sm">
              <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />
              {feature}
            </li>
          ))}
        </ul>
      </CardContent>
      <CardFooter>
        {isOwner && isCurrent && planKey === "pro" ? (
          <Button
            variant="outline"
            className="w-full"
            onClick={onManage}
            disabled={loading}
          >
            {loading ? "Loading…" : "Manage subscription"}
          </Button>
        ) : isOwner && !isCurrent && planKey === "pro" ? (
          <Button className="w-full" onClick={onUpgrade} disabled={loading}>
            <Zap className="mr-2 h-4 w-4" />
            {loading ? "Loading…" : "Upgrade to Pro"}
          </Button>
        ) : isCurrent && planKey === "free" ? (
          <span className="text-sm text-muted-foreground">
            Your current plan
          </span>
        ) : (
          <span />
        )}
      </CardFooter>
    </Card>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function BillingPage() {
  const { activeOrg } = useOrg();
  const searchParams = useSearchParams();
  const [billing, setBilling] = useState<BillingStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  const isOwner = activeOrg?.role === "owner";

  // Show feedback from Stripe redirect
  const checkoutSuccess = searchParams.get("success") === "true";
  const checkoutCanceled = searchParams.get("canceled") === "true";

  useEffect(() => {
    if (!activeOrg) return;
    let cancelled = false;
    billingApi
      .getStatus(activeOrg.id)
      .then((data) => {
        if (!cancelled) setBilling(data);
      })
      .catch(() => {
        if (!cancelled) sileo.error({ title: "Failed to load billing info" });
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [activeOrg?.id]);

  async function handleUpgrade() {
    if (!activeOrg) return;
    setActionLoading(true);
    try {
      const { url } = await billingApi.createCheckout(activeOrg.id);
      window.location.href = url;
    } catch (err) {
      sileo.error({
        title: err instanceof Error ? err.message : "Failed to start checkout",
      });
      setActionLoading(false);
    }
  }

  async function handleManage() {
    if (!activeOrg) return;
    setActionLoading(true);
    try {
      const { url } = await billingApi.createPortal(activeOrg.id);
      window.location.href = url;
    } catch (err) {
      sileo.error({
        title:
          err instanceof Error ? err.message : "Failed to open billing portal",
      });
      setActionLoading(false);
    }
  }

  if (loading) return <BillingSkeleton />;

  const currentPlan = (billing?.plan ?? "free") as "free" | "pro";

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Billing</h1>
        <p className="text-muted-foreground mt-1">
          Manage your plan and subscription for {activeOrg?.name}.
        </p>
      </div>

      {/* Stripe redirect feedback */}
      {checkoutSuccess && (
        <div className="flex items-center gap-2 text-sm text-green-700 bg-green-50 dark:bg-green-950 dark:text-green-300 border border-green-200 dark:border-green-800 rounded-lg px-4 py-3">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          Payment successful — your plan has been upgraded to Pro.
        </div>
      )}
      {checkoutCanceled && (
        <div className="flex items-center gap-2 text-sm text-yellow-700 bg-yellow-50 dark:bg-yellow-950 dark:text-yellow-300 border border-yellow-200 dark:border-yellow-800 rounded-lg px-4 py-3">
          <XCircle className="h-4 w-4 shrink-0" />
          Checkout was canceled. You have not been charged.
        </div>
      )}

      {/* Current status */}
      {billing?.subscription_status && (
        <div className="flex items-center gap-3 text-sm">
          <span className="text-muted-foreground">Subscription status</span>
          <StatusBadge status={billing.subscription_status} />
          {billing.subscription_status === "past_due" && (
            <span className="text-yellow-600 dark:text-yellow-400">
              — payment failed, please update your payment method
            </span>
          )}
        </div>
      )}

      {/* Plan cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-3xl pt-4">
        {(["free", "pro"] as const).map((planKey) => (
          <PlanCard
            key={planKey}
            planKey={planKey}
            isCurrent={currentPlan === planKey}
            isOwner={isOwner}
            onUpgrade={handleUpgrade}
            onManage={handleManage}
            loading={actionLoading}
          />
        ))}
      </div>

      {!isOwner && (
        <p className="text-sm text-muted-foreground">
          Only the org owner can manage billing.
        </p>
      )}
    </div>
  );
}
