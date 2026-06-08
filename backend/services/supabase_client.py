from functools import lru_cache

from supabase import Client, create_client

from config import settings


@lru_cache
def get_supabase() -> Client:
    """Server-side Supabase client using the anon key (auth flows only)."""
    return create_client(settings.supabase_url, settings.supabase_anon_key)


@lru_cache
def get_supabase_admin() -> Client:
    """Server-side Supabase client using the service role key (privileged operations)."""
    return create_client(settings.supabase_url, settings.supabase_service_key)
