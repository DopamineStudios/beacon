from discord import app_commands
from functools import wraps
from .preconditions import global_cooldown as g_cooldown, permissions_preset as preset, cooldown as local_cooldown
import sys

def command(
        name: str | None = None,
        description: str | None = None,
        global_cooldown: bool | None = True,
        permissions_preset: str | None = None,
        cooldown: tuple[int, float] | None = None,
        **kwargs
):
    """Build a slash-command decorator that applies framework defaults and checks."""

    if permissions_preset and permissions_preset.lower() != "bot_owner":
        kwargs['guild_only'] = True

    def decorator(func):
        cmd = app_commands.command(
            name=name or func.__name__,
            description=description or (func.__doc__ or "No description provided"),
            **kwargs
        )(func)

        if permissions_preset:
            cmd = preset(permissions_preset)(cmd)

        if cooldown:
            rate, per = cooldown
            cmd = local_cooldown(rate, per)(cmd)
        elif global_cooldown:
            cmd = g_cooldown()(cmd)

        return cmd

    return decorator


class Group(app_commands.Group):
    def __init__(
            self,
            name: str | None = None,
            description: str | None = None,
            global_cooldown: bool | None = True,
            permissions_preset: str | None = None,
            cooldown: tuple[int, float] | None = None,
            **kwargs
    ):
        super().__init__(
            name=name or self.__class__.__name__.lower(),
            description=description or (self.__doc__ or "No description provided"),
            **kwargs
        )
        self._beacon_settings = {
            'permissions_preset': permissions_preset,
            'cooldown': cooldown,
            'global_cooldown': global_cooldown
        }

    def add_command(self, command: app_commands.Command | app_commands.Group, /, *, override: bool = False) -> None:
        """Apply Beacon features to every command added to this group."""
        preset_val = self._beacon_settings['permissions_preset']
        cooldown_val = self._beacon_settings['cooldown']
        global_cd = self._beacon_settings['global_cooldown']

        if preset_val and preset_val.lower() != "bot_owner":
            command.guild_only = True

        if preset_val:
            preset(preset_val)(command)

        if cooldown_val:
            rate, per = cooldown_val
            local_cooldown(rate, per)(command)
        elif global_cd:
            g_cooldown()(command)

        return super().add_command(command, override=override)

_current_module = sys.modules[__name__]
for attr in dir(app_commands):
    if not hasattr(_current_module, attr):
        setattr(_current_module, attr, getattr(app_commands, attr))