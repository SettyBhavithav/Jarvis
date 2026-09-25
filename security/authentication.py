"""
JARVIS V2 - Authentication & Access Control
Enforces strict user verification, session tracking, Supabase Auth integration,
and default-to-DENY remote access protection.
"""
import uuid
from typing import Optional, List, Tuple
from pydantic import BaseModel, Field
from core.config import config
from core.exceptions import SecurityPolicyError
from storage.supabase import storage_adapter

class UserSession(BaseModel):
    user_id: str
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: Optional[str] = None
    role: str = "authenticated"
    channel: str = "voice"
    access_token: Optional[str] = None

class AuthenticationManager:
    def __init__(self):
        self.allowed_discord_ids: List[int] = config.DISCORD_ALLOWED_USER_IDS

    def verify_discord_user(self, user_id: int) -> bool:
        """
        Verifies if a Discord user is explicitly authorized.
        CRITICAL RULE: If the allowlist is empty, default to DENY for safety!
        """
        if not self.allowed_discord_ids or len(self.allowed_discord_ids) == 0:
            print(f"🛑 [Security Alert: Discord allowlist is empty. Denying access to user {user_id} by default.]")
            return False
        return user_id in self.allowed_discord_ids

    def create_test_auth_user(self) -> Tuple[str, str]:
        """
        Provisions a real Supabase Auth test user and returns its ACTUAL credentials.

        Returns:
            (actual_user_id, access_token) where:
              - actual_user_id is the UUID Supabase assigned in auth.users
              - access_token is a real JWT whose sub == actual_user_id

        This is the ONLY correct way to test RLS policies, because it ensures:
            JWT auth.uid() == database user_id

        Raises:
            RuntimeError: If a real JWT cannot be obtained. NEVER falls back to
                the service role key as an identity token — that would bypass RLS
                and make the test meaningless.

        Cleanup:
            Call delete_test_auth_user(actual_user_id) when done.
        """
        import httpx
        import certifi

        if not storage_adapter.supabase_service_role_key:
            raise RuntimeError(
                "SUPABASE_SERVICE_ROLE_KEY is required to provision integration test users. "
                "Set it in .env and re-run: pytest -m integration"
            )
        if not storage_adapter.supabase_url:
            raise RuntimeError("SUPABASE_URL is not configured.")

        # Use a unique email per test run to avoid collisions
        run_tag = uuid.uuid4().hex[:12]
        synthetic_email = f"integ-{run_tag}@jarvis-integration.test"
        synthetic_password = f"Jarvis-Test-{uuid.uuid4().hex}"

        admin_headers = {
            "apikey": storage_adapter.supabase_service_role_key,
            "Authorization": f"Bearer {storage_adapter.supabase_service_role_key}",
            "Content-Type": "application/json"
        }

        with httpx.Client(verify=certifi.where(), timeout=15.0) as client:
            # Step 1: Create the user in auth.users via Admin API
            # This fires the on_auth_user_created trigger →
            # auto-seeds public.users + public.user_profiles via our DB trigger.
            create_res = client.post(
                f"{storage_adapter.supabase_url}/auth/v1/admin/users",
                json={
                    "email": synthetic_email,
                    "password": synthetic_password,
                    "email_confirm": True,
                    "user_metadata": {"full_name": f"IntegTest-{run_tag}"}
                },
                headers=admin_headers
            )

            if create_res.status_code not in [200, 201]:
                raise RuntimeError(
                    f"Failed to create integration test user "
                    f"({create_res.status_code}): {create_res.text[:300]}"
                )

            created_user = create_res.json()
            # This is the UUID Supabase assigned — the ONE true identity for this user.
            actual_user_id = created_user["id"]

            # Step 2: Sign in with email+password to get a REAL JWT.
            # The returned access_token has sub == actual_user_id, which PostgREST
            # exposes as auth.uid() — the value your RLS policies check against.
            signin_res = client.post(
                f"{storage_adapter.supabase_url}/auth/v1/token?grant_type=password",
                json={"email": synthetic_email, "password": synthetic_password},
                headers={
                    "apikey": storage_adapter.supabase_anon_key or storage_adapter.supabase_key,
                    "Content-Type": "application/json"
                }
            )

            if signin_res.status_code not in [200, 201]:
                # Clean up the orphaned auth user before failing
                self.delete_test_auth_user(actual_user_id)
                raise RuntimeError(
                    f"Created auth user but failed to sign in to obtain JWT "
                    f"({signin_res.status_code}): {signin_res.text[:300]}"
                )

            token_data = signin_res.json()
            access_token = token_data.get("access_token")

            if not access_token:
                self.delete_test_auth_user(actual_user_id)
                raise RuntimeError(
                    "Sign-in succeeded but response contained no access_token. "
                    f"Response keys: {list(token_data.keys())}"
                )

            return actual_user_id, access_token

    def delete_test_auth_user(self, user_id: str) -> None:
        """
        Deletes a test user and all their data from both public.users (CASCADE removes
        all child rows) and auth.users (Admin API).

        Cleanup order:
          1. DELETE from public.users WHERE id = user_id  (service role, CASCADE)
             → removes tasks, memories, scheduled_tasks, audit_logs etc. via FK CASCADE
          2. DELETE from auth.users via Admin API
             → removes the Supabase Auth identity

        Silently ignores errors — cleanup failures must not mask test failures.
        """
        import httpx
        import certifi

        if not storage_adapter.supabase_service_role_key or not storage_adapter.supabase_url:
            return

        admin_headers = {
            "apikey": storage_adapter.supabase_service_role_key,
            "Authorization": f"Bearer {storage_adapter.supabase_service_role_key}",
            "Content-Type": "application/json"
        }
        try:
            with httpx.Client(verify=certifi.where(), timeout=10.0) as client:
                # Step 1: Delete public.users row (CASCADE removes all child data)
                client.delete(
                    f"{storage_adapter.supabase_url}/rest/v1/users?id=eq.{user_id}",
                    headers=admin_headers
                )
                # Step 2: Delete auth.users entry
                client.delete(
                    f"{storage_adapter.supabase_url}/auth/v1/admin/users/{user_id}",
                    headers=admin_headers
                )
        except Exception as e:
            print(f"[Auth cleanup warning — delete_test_auth_user({user_id})]: {e}")


    def authenticate_bearer_token(self, token: str) -> Optional[UserSession]:
        """Validates bearer tokens against Supabase Auth or local token registry."""
        if not token:
            return None
        # Clean Bearer prefix
        clean_token = token.replace("Bearer ", "").strip()
        auth_data = storage_adapter.auth_verify_token(clean_token)
        if auth_data:
            return UserSession(
                user_id=auth_data.get("id", str(uuid.uuid4())),
                email=auth_data.get("email"),
                role=auth_data.get("role", "authenticated"),
                channel="api",
                access_token=clean_token
            )
        return None

    def authenticate_request(
        self,
        channel: str,
        user_identifier: str,
        token: Optional[str] = None
    ) -> UserSession:
        """Establishes an authenticated UserSession with role & channel verification."""
        if channel == "discord":
            try:
                uid = int(user_identifier)
                if not self.verify_discord_user(uid):
                    raise SecurityPolicyError(f"Unauthorized Discord user ID {uid}. Access denied.")
                # Map authorized Discord user to deterministic UUID
                user_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"discord_{uid}"))
                return UserSession(user_id=user_uuid, role="owner", channel="discord")
            except ValueError:
                raise SecurityPolicyError("Invalid Discord user identifier.")

        if channel == "api":
            if not token:
                raise SecurityPolicyError("Missing required Authorization Bearer token.")
            session = self.authenticate_bearer_token(token)
            if not session:
                raise SecurityPolicyError("Invalid or expired authentication token.")
            return session

        # Local Voice / Console channel: authenticated local owner session
        owner_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, "local_owner_setty"))
        return UserSession(user_id=owner_uuid, email="owner@jarvis.local", role="owner", channel="voice")

# Global Auth Singleton
auth_manager = AuthenticationManager()
