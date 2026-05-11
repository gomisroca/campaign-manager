export interface BillingStatus {
  plan: string;
  subscription_status: string | null;
  stripe_customer_id: string | null;
  trial_ends_at: string | null;
}
