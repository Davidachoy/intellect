"""Database schema, seeds, and Supabase client."""

from .client import close_supabase_client, get_supabase_client

__all__ = ["close_supabase_client", "get_supabase_client"]
