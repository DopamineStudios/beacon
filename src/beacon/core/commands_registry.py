import logging
import discord
import hashlib
import json
import os
import asyncio
from discord import app_commands

GREY = ""
CYAN = ""
RESET = ""

class CommandRegistry:
    """Tracks local app-command state and synchronises it only when changed with rate-limiting protection.

    """

    def __init__(self, bot):
        """Store bot context and initialise sync-state storage details.

        Args:
            bot: Bot instance that owns this object or callback.
        """
        self.bot = bot
        package_dir = os.path.dirname(os.path.abspath(__file__))
        self.state_path = os.path.join(package_dir, "sync_state.json")

        if not hasattr(bot, "_global_cmd_sync_lock"):
            bot._global_cmd_sync_lock = asyncio.Lock()
        self.sync_lock = bot._global_cmd_sync_lock

    def _get_local_signature(self, command):
        """Build a deterministic signature dict for a local command node.

        Args:
            command: Application command object to inspect.

        Returns:
            Any: Result produced by this function.
        """
        if isinstance(command, discord.app_commands.ContextMenu):
            cmd_type = command.type.value
        elif isinstance(command, discord.app_commands.Group):
            cmd_type = 1
        else:
            cmd_type = 1

        signature = {
            "name": str(command.name),
            "type": cmd_type,
            "description": getattr(command, 'description', "") if cmd_type == 1 else "",
            "options": []
        }

        raw_options = []
        if hasattr(command, 'commands'):
            raw_options = command.commands
        elif hasattr(command, '_params'):
            raw_options = command._params.values()

        for opt in raw_options:
            if isinstance(opt, (discord.app_commands.Command, discord.app_commands.Group)):
                signature["options"].append(self._get_local_signature(opt))
            else:
                opt_data = {
                    "name": str(opt.name),
                    "description": str(opt.description or ""),
                    "type": int(opt.type.value),
                    "required": getattr(opt, 'required', True)
                }
                if hasattr(opt, 'choices') and opt.choices:
                    opt_data["choices"] = sorted([str(c.value) for c in opt.choices])

                signature["options"].append(opt_data)

        signature["options"] = sorted(signature["options"], key=lambda x: x["name"])
        return signature

    def _generate_tree_hash(self, guild: discord.Guild | None = None):
        """Hash the current local command tree for a guild or global scope.

        Args:
            guild: Guild to scope the operation to; uses global scope when omitted.

        Returns:
            Any: Result produced by this function.
        """
        local_commands = self.bot.tree.get_commands(guild=guild)
        local_map = {c.name: self._get_local_signature(c) for c in local_commands}

        sorted_map = {k: local_map[k] for k in sorted(local_map.keys())}
        dump = json.dumps(sorted_map, sort_keys=True)
        return hashlib.sha256(dump.encode('utf-8')).hexdigest()

    def _get_stored_state(self, scope_id: str):
        """Load the last persisted command-tree state for a scope.

        Args:
            scope_id: Storage key for the sync-hash scope.

        Returns:
            dict: Dict containing 'hash' and 'bot_id', or None.
        """
        if not os.path.exists(self.state_path):
            return None
        try:
            with open(self.state_path, "r") as f:
                data = json.load(f)
                return data.get(scope_id)
        except Exception:
            return None

    def _save_state(self, scope_id: str, new_hash: str):
        """Persist the latest command-tree hash and bot ID for a scope.

        Args:
            scope_id: Storage key for the sync-hash scope.
            new_hash: Freshly calculated command-tree hash.
        """
        os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
        data = {}
        if os.path.exists(self.state_path):
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
            except Exception:
                pass

        bot_id = self.bot.user.id if self.bot.user else None

        data[scope_id] = {
            "hash": new_hash,
            "bot_id": bot_id
        }

        with open(self.state_path, "w") as f:
            json.dump(data, f, indent=4)

    async def smart_sync(self, guild: discord.Guild | None = None):
        """Sync commands only when the local tree hash or bot ID differs from stored state."""
        if self.sync_lock.locked():
            return f"[`{self.bot.instance_id}`] Beacon: A command synchronisation is already in progress. Please wait for it to complete."

        scope_id = f"guild_{guild.id}" if guild else "global"
        scope_name = f"Guild({guild.id})" if guild else "Global"

        current_hash = self._generate_tree_hash(guild)
        stored_state = self._get_stored_state(scope_id)

        current_bot_id = self.bot.user.id if self.bot.user else None

        if (
                stored_state
                and stored_state.get("hash") == current_hash
                and stored_state.get("bot_id") == current_bot_id
        ):
            self.bot.logger.info(
                f"{GREY}[{self.bot.instance_id}]{CYAN} Beacon{RESET}: Compared stored state to current state. {scope_name} commands are up to date for this bot. Skipping sync API call."
            )
            return f"[`{self.bot.instance_id}`] Beacon: Compared stored state to current state. {scope_name} commands are up to date. Skipping sync API call."

        async with self.sync_lock:
            self.bot.logger.info(
                f"{GREY}[{self.bot.instance_id}]{CYAN} Beacon{RESET}: Detected changes or bot swap. Syncing {scope_name} commands...")
            backoff = 2.0
            max_backoff = 300.0

            while True:
                try:
                    await self.bot.tree.sync(guild=guild)
                    self._save_state(scope_id, current_hash)
                    return f"[`{self.bot.instance_id}`] Beacon: Detected changes, and completed command sync for {scope_name} successfully."

                except discord.HTTPException as e:
                    if e.status == 429 or 500 <= e.status < 600:
                        self.bot.logger.warning(
                            f"{GREY}[{self.bot.instance_id}]{CYAN} Beacon{RESET}: Sync hit HTTP {e.status}. Retrying in {backoff} seconds...")
                        await asyncio.sleep(backoff)

                        if backoff >= max_backoff:
                            self.bot.logger.error(
                                f"{GREY}[{self.bot.instance_id}]{CYAN} Beacon{RESET}: Sync aborted. Maximum backoff time of 5 minutes reached for {scope_name}."
                            )
                            return f"[`{self.bot.instance_id}`] Beacon: Error syncing {scope_name}. The Discord API did not accept requests after maximum backoff configurations."

                        backoff = min(backoff * 2, max_backoff)
                    else:
                        self.bot.logger.error(f"{GREY}[{self.bot.instance_id}]{CYAN} Beacon{RESET}: Sync failed with unretriable error: {e}")
                        return f"[`{self.bot.instance_id}`] Beacon: Error syncing {scope_name}: HTTP status {e.status} encountered."

                except Exception as e:
                    self.bot.logger.error(f"{GREY}[{self.bot.instance_id}]{CYAN} Beacon{RESET}: Unexpected error during sync execution: {e}")
                    return f"[`{self.bot.instance_id}`] Beacon: Error syncing {scope_name}: {e}"

    async def force_sync(self, guild: discord.Guild | None = None):
        """Force a command sync call regardless of configuration states, respecting the global lock."""
        if self.sync_lock.locked():
            return f"[`{self.bot.instance_id}`] Beacon: A command synchronisation is already in progress. Please wait for it to complete."

        scope = f"Guild: {guild.name} ({guild.id})" if guild else "Global"

        async with self.sync_lock:
            try:
                await self.bot.tree.sync(guild=guild)
                scope_id = f"guild_{guild.id}" if guild else "global"
                self._save_state(scope_id, self._generate_tree_hash(guild))
                return f"[`{self.bot.instance_id}`] Beacon: Synced slash commands to: {scope}."
            except discord.HTTPException as e:
                return f"[`{self.bot.instance_id}`] Beacon: Rate limit or API error: {e}"