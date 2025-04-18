"""
CLI utility for managing the application cache.

This module provides commands to view, clear, and manage the cache
to help reduce API calls and improve performance.
"""

import asyncio
import sys
from rich.console import Console
from rich.table import Table

from app.utils.cache_manager import cache_manager

console = Console()

async def show_cache_stats():
    """Display statistics about the current cache."""
    stats = await cache_manager.get_stats()
    
    console.print("[bold cyan]Cache Statistics[/bold cyan]")
    console.print(f"Total namespaces: {stats['total_namespaces']}")
    console.print(f"Total entries: {stats['total_entries']}")
    
    # Display TTL settings
    ttl_table = Table(title="Default TTL Settings (seconds)")
    ttl_table.add_column("Namespace", style="cyan")
    ttl_table.add_column("TTL (seconds)", justify="right")
    
    for namespace, ttl in stats['default_ttls'].items():
        ttl_table.add_row(namespace, str(ttl))
    
    console.print(ttl_table)
    
    # Display namespace details
    if stats['namespaces']:
        ns_table = Table(title="Cache Namespaces")
        ns_table.add_column("Namespace", style="cyan")
        ns_table.add_column("Total Entries", justify="right")
        ns_table.add_column("Active", justify="right", style="green")
        ns_table.add_column("Expired", justify="right", style="yellow")
        
        for namespace, details in stats['namespaces'].items():
            ns_table.add_row(
                namespace,
                str(details['total_entries']),
                str(details['active_entries']),
                str(details['expired_entries'])
            )
        
        console.print(ns_table)
    else:
        console.print("[yellow]No cache entries found.[/yellow]")

async def clear_cache(namespace=None):
    """Clear the cache, optionally for a specific namespace only."""
    if namespace:
        count = await cache_manager.clear_namespace(namespace)
        console.print(f"[green]Cleared {count} entries from namespace '{namespace}'[/green]")
    else:
        count = await cache_manager.clear_all()
        console.print(f"[green]Cleared all caches ({count} total entries)[/green]")

async def set_ttl(namespace, ttl_seconds):
    """Set the TTL for a specific namespace."""
    try:
        ttl = int(ttl_seconds)
        if ttl <= 0:
            console.print("[red]TTL must be a positive integer[/red]")
            return
        
        cache_manager.set_default_ttl(namespace, ttl)
        console.print(f"[green]Set TTL for namespace '{namespace}' to {ttl} seconds[/green]")
    except ValueError:
        console.print("[red]TTL must be a valid integer[/red]")

async def main():
    """Main entry point for the cache CLI."""
    if len(sys.argv) < 2:
        console.print("[bold cyan]Cache Management CLI[/bold cyan]")
        console.print("Available commands:")
        console.print("  stats       - Show cache statistics")
        console.print("  clear       - Clear all caches")
        console.print("  clear <ns>  - Clear a specific namespace")
        console.print("  set-ttl <ns> <seconds> - Set TTL for a namespace")
        return
    
    command = sys.argv[1].lower()
    
    if command == "stats":
        await show_cache_stats()
    elif command == "clear":
        if len(sys.argv) > 2:
            namespace = sys.argv[2]
            await clear_cache(namespace)
        else:
            await clear_cache()
    elif command == "set-ttl":
        if len(sys.argv) < 4:
            console.print("[red]Usage: set-ttl <namespace> <seconds>[/red]")
            return
        namespace = sys.argv[2]
        ttl_seconds = sys.argv[3]
        await set_ttl(namespace, ttl_seconds)
    else:
        console.print(f"[red]Unknown command: {command}[/red]")
        console.print("Use with no arguments to see available commands.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\nExiting.", style="bold blue")
        sys.exit(0)
