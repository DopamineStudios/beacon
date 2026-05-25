import logging
import discord
import hashlib
import json
import os
from discord import app_commands

logger = logging.getLogger("discord")


class CommandRegistry:
    """Tracks local app-command state and synchronizes it only when changed.

    """
    def __init__(self, bot):
        """Store bot context and initialize sync-state storage details.

        Args:
            bot: Bot instance that owns this object or callback.
        """
        self.bot = bot
        self.state_path = os.path.join("core", "sync_state.json")

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

    def _generate_tree_hash(self, guild: discord.Guild = None):
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

    def _get_stored_hash(self, scope_id: str):
        """Load the last persisted command-tree hash for a scope.

        Args:
            scope_id: Storage key for the sync-hash scope.

        Returns:
            Any: Result produced by this function.
        """
        if not os.path.exists(self.state_path):
            return None
        try:
            with open(self.state_path, "r") as f:
                data = json.load(f)
                return data.get(scope_id)
        except Exception:
            return None

    def _save_hash(self, scope_id: str, new_hash: str):
        """Persist the latest command-tree hash for a scope.

        Args:
            scope_id: Storage key for the sync-hash scope.
            new_hash: Freshly calculated command-tree hash.

        Returns:
            Any: Result produced by this function.
        """
        os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
        data = {}
        if os.path.exists(self.state_path):
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
            except Exception:
                pass

        data[scope_id] = new_hash
        with open(self.state_path, "w") as f:
            json.dump(data, f, indent=4)

    async def smart_sync(self, guild: discord.Guild = None):
        """Sync commands only when the local tree hash differs from stored state.

        Args:
            guild: Guild to scope the operation to; uses global scope when omitted.

        Returns:
            str: Human-readable sync status message.
        """
        scope_id = f"guild_{guild.id}" if guild else "global"
        scope_name = f"Guild({guild.id})" if guild else "Global"

        current_hash = self._generate_tree_hash(guild)
        stored_hash = self._get_stored_hash(scope_id)

        if current_hash != stored_hash:
            logger.info(f"Beacon: Detected  changes. Syncing {scope_name} commands...")
            try:
                await self.bot.tree.sync(guild=guild)
                self._save_hash(scope_id, current_hash)
                return f"Beacon: Detected changes, and completed command sync for {scope_name} successfully."
            except Exception as e:
                logger.error(f"Beacon: Sync failed: {e}")
                return f"Beacon: Error syncing {scope_name}."

        logger.info(f"Beacon: Compared stored local hash to current local hash. {scope_name} commands are up to date. Skipping sync API call.")
        return f"Beacon: Compared stored local hash to current local hash. {scope_name} commands are up to date. Skipping sync API call."

    async def force_sync(self, guild: discord.Guild = None):
        """Force a command sync call regardless of hash comparison.

        Args:
            guild: Guild to scope the operation to; uses global scope when omitted.

        Returns:
            str: Human-readable sync status message.
        """
        scope = f"Guild: {guild.name} ({guild.id})" if guild else "Global"
        try:
            await self.bot.tree.sync(guild=guild)
            return f"Beacon: Synced slash commands to: {scope}."
        except discord.HTTPException as e:
            return f"Beacon: Rate limit or API error: {e}"