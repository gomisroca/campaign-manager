import resend
from backend.config import get_settings

settings = get_settings()
resend.api_key = settings.resend_api_key


def _send(to: str, subject: str, html: str) -> None:
    """
    Send an email via Resend.
    Falls back to printing if email is not configured —
    useful for local development without a Resend account.
    """
    if not settings.email_enabled:
        print(f"\n{'='*60}")
        print(f"EMAIL (stub — set RESEND_API_KEY to send real emails)")
        print(f"To:      {to}")
        print(f"Subject: {subject}")
        print(f"{'='*60}\n")
        return

    resend.Emails.send({
        "from": f"{settings.email_from_name} <{settings.email_from_address}>",
        "to": [to],
        "subject": subject,
        "html": html,
    })


def _invite_html(org_name: str, inviter_email: str, role: str, invite_url: str, expires_days: int = 7) -> str:
    """Simple but clean invite email template."""
    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f9fafb; margin: 0; padding: 40px 20px;">
  <div style="max-width: 480px; margin: 0 auto; background: white; border-radius: 8px; border: 1px solid #e5e7eb; overflow: hidden;">

    <!-- Header -->
    <div style="background: #18181b; padding: 24px 32px;">
      <h1 style="color: white; margin: 0; font-size: 20px; font-weight: 600;">Campaign Manager</h1>
    </div>

    <!-- Body -->
    <div style="padding: 32px;">
      <h2 style="margin: 0 0 8px; font-size: 22px; color: #111827;">You've been invited</h2>
      <p style="margin: 0 0 24px; color: #6b7280; font-size: 15px;">
        <strong style="color: #111827;">{inviter_email}</strong> has invited you to join
        <strong style="color: #111827;">{org_name}</strong> as a <strong style="color: #111827;">{role}</strong>.
      </p>

      <!-- CTA Button -->
      <a href="{invite_url}"
         style="display: inline-block; background: #18181b; color: white; text-decoration: none;
                padding: 12px 24px; border-radius: 6px; font-size: 15px; font-weight: 500;">
        Accept invitation
      </a>

      <p style="margin: 24px 0 0; color: #9ca3af; font-size: 13px;">
        This invitation expires in {expires_days} days. If you weren't expecting this, you can safely ignore this email.
      </p>
    </div>

    <!-- Footer -->
    <div style="padding: 16px 32px; border-top: 1px solid #f3f4f6;">
      <p style="margin: 0; color: #9ca3af; font-size: 12px;">
        Sent by Campaign Manager · If the button doesn't work, copy this link: {invite_url}
      </p>
    </div>

  </div>
</body>
</html>
"""


def send_invite_email(
    to: str,
    org_name: str,
    inviter_email: str,
    role: str,
    invite_url: str,
) -> None:
    _send(
        to=to,
        subject=f"You've been invited to join {org_name} on Campaign Manager",
        html=_invite_html(org_name, inviter_email, role, invite_url),
    )