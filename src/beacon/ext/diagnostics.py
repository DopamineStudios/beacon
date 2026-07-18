import os
import sys
import ctypes
import io
import psutil
import time
import asyncio
from pathlib import Path
import discord
from discord.ext import commands, tasks
from discord import app_commands

fonts_dir = Path(__file__).parent.resolve()


def _register_internal_library_fonts():
    try:
        if sys.platform.startswith("linux"):
            lib_name = "libfontconfig.so.1"
        elif sys.platform == "darwin":
            lib_name = "libfontconfig.1.dylib"
        else:
            lib_name = "libfontconfig-1.dll"

        fontconfig = ctypes.CDLL(lib_name)

        for font_file in fonts_dir.glob("*.ttf"):
            fontconfig.FcConfigAppFontAddFile(None, str(font_file).encode('utf-8'))

    except Exception:
        pass

_register_internal_library_fonts()


import pyvips

from collections import deque
from .path import framework_version
from ..core import beacon_commands


class Diagnostics(commands.Cog):
    """Diagnostics cog that reports latency, uptime, and host health metrics."""

    def __init__(self, bot):
        """Initialize sampling state and start periodic latency collection.

        Args:
            bot: Bot instance that owns this object or callback.
        """
        self.bot = bot
        self.api_latency_cache = deque(maxlen=1440)
        self.api_temp_samples = []
        self.process = psutil.Process(os.getpid())
        self.process.cpu_percent(interval=None)
        self.current_cpu = 0.0

        self.cached_api_graph_bytes = None
        self.cached_heartbeat_graph_bytes = None

        self.heartbeat_latency_cache = deque(maxlen=1440)
        self.heartbeat_temp_samples = []
        self.cache_task.start()

        self.battery_cache = []
        self.battery_interval_mins = 10
        self.battery_duration_mins = 60
        self.battery_max_mins = 240
        self.battery_increment_mins = 20
        self.is_battery_idling = False
        self.battery_task.start()

        self.font_family_title = "Montserrat"

    async def cog_unload(self):
        """Stop background sampling when the cog is unloaded.

        Returns:
            Any: Result produced by this function.
        """
        self.cache_task.cancel()
        self.battery_task.cancel()

    @tasks.loop(seconds=5.0)
    async def cache_task(self):
        """Collect API and Heartbeat latency samples and keep rolling latency averages."""
        if not self.bot.is_ready():
            return

        try:
            self.current_cpu = self.process.cpu_percent(interval=None)

            total_latency = None
            try:
                start = time.perf_counter()
                await asyncio.wait_for(
                    self.bot.http.request(discord.http.Route("GET", "/gateway")),
                    timeout=3.0
                )
                end = time.perf_counter()
                total_latency = round((end - start) * 1000)
            except (asyncio.TimeoutError, Exception):
                total_latency = 999

            import math
            if isinstance(total_latency, (int, float)) and not math.isnan(total_latency):
                if math.isinf(total_latency) or total_latency >= 999:
                    self.api_temp_samples.append(999)
                else:
                    self.api_temp_samples.append(total_latency)

            if self.bot.latency is None or math.isinf(self.bot.latency) or math.isnan(self.bot.latency):
                hb_latency = 999
            else:
                hb_latency = round(self.bot.latency * 1000)

            self.heartbeat_temp_samples.append(min(hb_latency, 999))

            if len(self.api_temp_samples) >= 12:
                avg_latency = sum(self.api_temp_samples) / len(self.api_temp_samples)
                self.api_latency_cache.append(avg_latency)
                self.api_temp_samples.clear()
                self.cached_api_graph_bytes = None

            if len(self.heartbeat_temp_samples) >= 12:
                avg_hb = sum(self.heartbeat_temp_samples) / len(self.heartbeat_temp_samples)
                self.heartbeat_latency_cache.append(avg_hb)
                self.heartbeat_temp_samples.clear()
                self.cached_heartbeat_graph_bytes = None

        except Exception as e:
            self.bot.logger.critical(f"[{self.bot.instance_id}] Beacon: {e}")

    @cache_task.before_loop
    async def before_cache_task(self):
        """Wait for readiness before starting periodic diagnostics sampling.

        Returns:
            Any: Result produced by this function.
        """
        await self.bot.wait_until_ready()
        await asyncio.sleep(10)

    @tasks.loop(minutes=10.0)
    async def battery_task(self):
        """Periodically sample host battery metrics to detect bypass charging or idling status.

        Returns:
            Any: Result produced by this function.
        """
        if not self.bot.is_ready():
            return

        try:
            battery = psutil.sensors_battery()
            if not battery:
                return

            percent = battery.percent
            charging = battery.power_plugged
            status_str = "(Charging)" if charging else "(Discharging)"
            current_state = f"{percent}% {status_str}"

            if self.battery_cache and current_state != self.battery_cache[-1]:
                self.is_battery_idling = False
                self.battery_cache.clear()
                if self.battery_duration_mins < self.battery_max_mins:
                    self.battery_duration_mins = min(
                        self.battery_max_mins,
                        self.battery_duration_mins + self.battery_increment_mins
                    )

            self.battery_cache.append(current_state)

            required_samples = self.battery_duration_mins // self.battery_interval_mins
            while len(self.battery_cache) > required_samples:
                self.battery_cache.pop(0)

            if len(self.battery_cache) >= required_samples and len(set(self.battery_cache)) == 1:
                self.is_battery_idling = True

        except Exception as e:
            self.bot.logger.error(f"[{self.bot.instance_id}] Beacon: {e}")

    @battery_task.before_loop
    async def before_battery_task(self):
        """Wait for readiness before starting periodic battery diagnostics sampling.

        Returns:
            Any: Result produced by this function.
        """
        await self.bot.wait_until_ready()

    async def get_location(self):
        """Resolve host geolocation information from the current public IP.

        Returns:
            Any: Location.
        """
        def fetch():
            """Perform blocking IP geolocation lookup off the event loop.

            Returns:
                Any: Result produced by this function.
            """
            if not self.bot.secure_mode:
                import geocoder
                g = geocoder.ip('me')
                if g.ok:
                    return f"{g.country} ({g.city})" if g.city else g.country
                return "Unknown Region"
            return None

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, fetch)

    def generate_latency_graph(self, graph_type: str):
        """Render the cached latency history into an in-memory PNG graph using pyvips."""
        try:
            if graph_type.strip().lower() == "heartbeat":
                data = list(self.heartbeat_latency_cache)
            else:
                data = list(self.api_latency_cache)
            num_samples = len(data)

            if num_samples < 2:
                return None

            scale_factor = 2
            width, height = 600 * scale_factor, 300 * scale_factor
            pad_top, pad_bot, pad_left, pad_right = 175, 80, 100, 40

            max_val = max(data) if data else 100
            steps = [10, 25, 50, 100, 250, 500, 1000]
            target_step = next((s for s in steps if s > max_val / 4), max_val / 4)
            y_limit = target_step * 4

            graph_height = height - pad_top - pad_bot
            graph_width = width - pad_left - pad_right

            points = []
            for i, val in enumerate(data):
                x = pad_left + (i / (num_samples - 1)) * graph_width
                y = (height - pad_bot) - (val / y_limit) * graph_height
                points.append((x, y))

            bg_color = [26, 26, 30, 255]
            base = (pyvips.Image.black(width, height, bands=4) + bg_color).copy(interpretation="srgb")

            grid_colour = [60, 62, 68, 255]
            for i in range(5):
                val = target_step * i
                y = (height - pad_bot) - (val / y_limit) * graph_height
                base = base.draw_rect(grid_colour, int(pad_left), int(y - scale_factor // 2),
                                      int(graph_width), int(1 * scale_factor), fill=True)

            fill_points = [(pad_left, height - pad_bot)] + points + [(width - pad_right, height - pad_bot)]
            svg_points_str = " ".join(f"{int(x)},{int(y)}" for x, y in fill_points)
            svg_mask_str = f'<svg width="{width}" height="{height}"><polygon points="{svg_points_str}" fill="white" /></svg>'

            svg_img = pyvips.Image.svgload_buffer(svg_mask_str.encode('utf-8'))
            poly_alpha = svg_img[3] if svg_img.bands == 4 else svg_img[0]
            poly_mask = (poly_alpha * (40 / 255)).cast("uchar")

            accent_rgb = list(self.bot.accent_colour[:3])
            secondary_rgb = [max(0, min(255, int(channel * 0.925))) for channel in accent_rgb]
            poly_colour_block = (pyvips.Image.black(width, height, bands=3) + secondary_rgb).cast("uchar")
            fill_layer = poly_colour_block.bandjoin(poly_mask).copy(interpretation="srgb")

            base = base.composite(fill_layer, "over")

            fg = pyvips.Image.black(width, height, bands=4).copy(interpretation="srgb")

            def draw_text_fast(img, text, font_family, size, colour, target_x, target_y, anchor="mt"):
                try:
                    mask = pyvips.Image.text(text, font=f"{font_family} {int(size)}", dpi=72)
                except:
                    mask = pyvips.Image.text(text, font=f"Sans {int(size)}", dpi=72)

                if anchor == "mt":
                    x, y = target_x - mask.width // 2, target_y
                elif anchor == "rm":
                    x, y = target_x - mask.width, target_y - mask.height // 2
                else:
                    x, y = target_x, target_y

                text_colour = (pyvips.Image.black(mask.width, mask.height, bands=4) + colour).copy(interpretation="srgb")
                return img.composite2(text_colour.bandjoin(mask), 'over', x=int(x), y=int(y))

            fg = draw_text_fast(fg, f"{graph_type} Latency Graph - Powered by Beacon",
                                self.font_family_title + " Bold", 24 * scale_factor,
                                [255, 255, 255, 255], width / 2, 70, "mt")

            y_label_colour = [140, 140, 140, 255]
            for i in range(5):
                val = target_step * i
                y = (height - pad_bot) - (val / y_limit) * graph_height
                fg = draw_text_fast(fg, f"{int(val)}ms", "Sans", 10 * scale_factor,
                                    y_label_colour, pad_left - 15, y, "rm")

            tick_colour = [130, 130, 130, 255]
            num_x_labels = 5
            for i in range(num_x_labels):
                sample_idx = int((i / (num_x_labels - 1)) * (num_samples - 1))
                x = pad_left + (i / (num_x_labels - 1)) * graph_width
                mins_ago = num_samples - 1 - sample_idx
                label = "Now" if mins_ago == 0 else (
                    f"{round(mins_ago / 60, 1)}h" if mins_ago >= 60 else f"{mins_ago}m")

                fg = fg.draw_rect(tick_colour, int(x - 1), int(height - pad_bot), 2, 10, fill=True)
                fg = draw_text_fast(fg, label, "Sans", 12 * scale_factor, tick_colour, x, height - pad_bot + 25, "mt")

            accent_rgba = accent_rgb + [255]
            offsets = [-1, 0, 1]
            for off in offsets:
                for i in range(len(points) - 1):
                    fg = fg.draw_line(accent_rgba, int(points[i][0] + off), int(points[i][1] + off),
                                      int(points[i + 1][0] + off), int(points[i + 1][1] + off))

            final_graph = base.composite(fg, "over")
            final_graph = final_graph.resize(0.5, kernel="lanczos3")

            return io.BytesIO(final_graph.write_to_buffer(".png"))

        except Exception as e:
            import traceback
            self.bot.logger.error(f"[{self.bot.instance_id}] Beacon: Graph error: {e}\n{traceback.format_exc()}")
            return None

    @beacon_commands.command(name="ping", description="Get detailed latency and bot information")
    async def ping(self, interaction: discord.Interaction):
        """Send an embed with detailed latency, uptime, and system stats.

        Args:
            interaction: Interaction context received from Discord.

        Returns:
            Any: Result produced by this function.
        """

        def format_uptime(seconds):
            """Convert elapsed seconds into a compact human-readable duration.

            Args:
                seconds: Duration in seconds.

            Returns:
                Any: Formatted uptime value.
            """
            weeks = seconds // (7 * 24 * 60 * 60)
            seconds %= (7 * 24 * 60 * 60)
            days = seconds // (24 * 60 * 60)
            seconds %= (24 * 60 * 60)
            hours = seconds // (60 * 60)
            seconds %= (60 * 60)
            minutes = seconds // 60
            seconds %= 60

            parts = []
            if weeks > 0:
                parts.append(f"{int(weeks)}w")
            if days > 0:
                parts.append(f"{int(days)}d")
            if hours > 0:
                parts.append(f"{int(hours)}h")
            if minutes > 0:
                parts.append(f"{int(minutes)}m")
            if seconds > 0 or not parts:
                parts.append(f"{int(seconds)}s")

            return " ".join(parts)

        initial_message = (
            "Pinging...\n"
            "Digging around for your IP address...\n"
            "Getting your location...\n"
            "Calculating distance to your home...\n"
            "Sending you some icecream...\n"
            "Done! Icecream sent."
        )

        if self.api_latency_cache:
            avg_api_latency = f"{round(sum(self.api_latency_cache) / len(self.api_latency_cache))}ms"
        else:
            avg_api_latency = "Calculating..."
        if self.heartbeat_latency_cache:
            avg_heartbeat_latency = f"{round(sum(self.heartbeat_latency_cache) / len(self.heartbeat_latency_cache))}ms"
        else:
            avg_heartbeat_latency = "Calculating..."
        start_time = time.time()
        await interaction.response.send_message(initial_message)
        end_time = time.time()
        shard_id_line = None
        if hasattr(self.bot, 'shards'):
            shard_id = interaction.guild.shard_id if interaction.guild else (interaction.user.id >> 22) % self.bot.shard_count or 0
            shard_id_line = f"> Running on Shard `{shard_id}` of `{self.bot.shard_count}` Shards\n\n"

            shard = self.bot.get_shard(shard_id)

            shard_runner = getattr(shard, '_parent', None)
            shard_ws = getattr(shard_runner, 'ws', None) if shard_runner else None

            if shard_ws and hasattr(shard_ws, 'gateway'):
                gateway_raw = str(shard_ws.gateway)
            elif hasattr(self.bot, 'gateway_url') and self.bot.gateway_url:
                gateway_raw = self.bot.gateway_url
            else:
                gateway_raw = "Global/Unknown"

        else:
            gateway_raw = str(self.bot.ws.gateway) if self.bot.ws else "Global/Unknown"
        final_shard_id_line = shard_id_line or "\n"
        gateway_node = gateway_raw.split('gateway-')[-1].split('.')[
            0] if 'gateway-' in gateway_raw else "Global/Unknown"
        round_latency = round((end_time - start_time) * 1000)
        discord_latency = round(self.bot.latency * 1000)
        location = None
        if not self.bot.secure_mode:
            location = await self.get_location()
        location_line = f"> Bot Host Location: `{location}`\n" if location else ""
        try:
            start = time.perf_counter()
            await self.bot.http.request(discord.http.Route("GET", "/gateway"))
            end = time.perf_counter()
            connection_latency = round((end - start) * 1000)
        except Exception:
            connection_latency = "Error"

        if hasattr(self.bot, 'start_time'):
            uptime_seconds = int(time.time() - self.bot.start_time)
        else:
            uptime_seconds = 0
        uptime_formatted = format_uptime(uptime_seconds)

        proc_seconds = int(time.time() - getattr(self.bot, 'process_start_time', time.time()))
        proc_uptime = format_uptime(proc_seconds)

        try:
            process = psutil.Process(os.getpid())
            memory_bytes = process.memory_info().rss
            memory_mb = memory_bytes / (1024 * 1024)

            if memory_mb >= 1024:
                memory_gb = int(memory_mb // 1024)
                memory_remaining_mb = round(memory_mb % 1024, 2)
                memory_usage = f"{memory_gb}GB {memory_remaining_mb}MB"
            else:
                memory_usage = f"{round(memory_mb, 2)}MB"
        except Exception:
            memory_usage = "Unable to calculate"

        try:
            battery = psutil.sensors_battery()
            if battery:
                percent = battery.percent
                charging = battery.power_plugged
                status_str = "(Charging)" if charging else "(Discharging)"
                current_state = f"{percent}% {status_str}"

                if self.battery_cache and current_state != self.battery_cache[-1]:
                    self.is_battery_idling = False
                    self.battery_cache.clear()
                    if self.battery_duration_mins < self.battery_max_mins:
                        self.battery_duration_mins = min(
                            self.battery_max_mins,
                            self.battery_duration_mins + self.battery_increment_mins
                        )

                if self.is_battery_idling:
                    battery_status = f"> Host Device Battery Status: `{percent}% (Idling/Bypass Charging)`"
                else:
                    battery_status = f"> Host Device Battery Status: `{percent}% {status_str}`"
            else:
                battery_status = ""
        except Exception:
            battery_status = "> Host Device Battery Status: `Unable to determine`"

        cpu_usage = self.current_cpu
        if cpu_usage == 0:
            formatted_cpu_usage = "0"
        else:
            formatted_cpu_usage = f"{cpu_usage:.1f}"
        bot_version_line = f"> Bot Version: `{self.bot.version}`\n" if self.bot.version else ""
        embed = discord.Embed(
            title="Pong!",
            description=(
                f"{bot_version_line}"
                f"> Powered by Beacon Framework `v{framework_version}` by Dopamine Studios\n"
                f"> Beacon Instance ID: `{self.bot.instance_id}`\n\n"
                f"> Connected to Discord Gateway: `{gateway_node}`\n"
                f"{location_line}"
                f"{final_shard_id_line}"
                f"> API Latency: `{connection_latency}ms`\n"
                f"> Round-trip Latency: `{round_latency}ms`\n"
                f"> Heartbeat/WebSocket Latency: `{discord_latency}ms`\n\n"
                f"> Average API Latency: `{avg_api_latency}`\n"
                f"> Average Heartbeat/WebSocket Latency: `{avg_heartbeat_latency}`\n\n"
                f"> Connection Uptime: `{uptime_formatted}`\n"
                f"> Process Uptime: `{proc_uptime}`\n\n"
                f"> CPU Usage: `{formatted_cpu_usage}%`\n"
                f"> Memory Usage: `{memory_usage}`\n"
                f"{battery_status}"
            ),
            color=discord.Colour.from_rgb(*self.bot.accent_colour)
        )
        message = await interaction.original_response()
        await message.edit(content=None, embed=embed)

    latency = beacon_commands.Group(name="latency", description="Shows latency information about the bot")

    @latency.command(name="graph", description="Shows a graph of the average latency in the last 24 hours")
    @app_commands.choices(graph_type=[
        app_commands.Choice(name="API Latency Graph", value="api"),
        app_commands.Choice(name="Heartbeat Latency Graph", value="heartbeat")
    ])
    @app_commands.describe(
        graph_type="The type of latency graph you want to see, either for API latency or for Heartbeat latency. Defaults to API latency graph.")
    async def graph(self, interaction: discord.Interaction, graph_type: app_commands.Choice[str] | None = None):
        """Return a generated latency trend graph when enough samples exist.

        Args:
            interaction: Interaction context received from Discord.
            graph_type: The type of latency graph you want to see, either for API latency or for Heartbeat latency. Defaults to API latency graph.

        Returns:
            Any: Result produced by this function.
        """
        graph_type_value = graph_type.value if graph_type is not None else "api"
        loop = asyncio.get_running_loop()

        if graph_type_value == "api":
            if len(self.api_latency_cache) < 2:
                return await interaction.response.send_message(
                    "Beacon: Not enough data yet! The bot was restarted very recently. Please wait a few minutes.",
                    ephemeral=True
                )

            try:
                await interaction.response.defer()
                if not self.cached_api_graph_bytes:
                    graph_buffer = await loop.run_in_executor(None, self.generate_latency_graph, "API")
                    if graph_buffer:
                        self.cached_api_graph_bytes = graph_buffer.getvalue()

                buffer = io.BytesIO(self.cached_api_graph_bytes)
                file = discord.File(buffer, filename="beacon_api_graph.png")
                await interaction.edit_original_response(content=None, attachments=[file])
            except Exception as e:
                return await interaction.edit_original_response(content=f"Beacon: ERROR: {e}")

        elif graph_type_value == "heartbeat":
            if len(self.heartbeat_latency_cache) < 2:
                return await interaction.response.send_message(
                    "Beacon: Not enough data yet! The bot was restarted very recently. Please wait a few minutes.",
                    ephemeral=True
                )

            try:
                await interaction.response.defer()
                if not self.cached_heartbeat_graph_bytes:
                    hb_graph_buffer = await loop.run_in_executor(None, self.generate_latency_graph, "Heartbeat")
                    if hb_graph_buffer:
                        self.cached_heartbeat_graph_bytes = hb_graph_buffer.getvalue()

                buffer = io.BytesIO(self.cached_heartbeat_graph_bytes)
                file = discord.File(buffer, filename="beacon_heartbeat_graph.png")
                await interaction.edit_original_response(content=None, attachments=[file])
            except Exception as e:
                return await interaction.edit_original_response(content=f"Beacon: ERROR: {e}")
        else:
            return await interaction.response.send_message(content="That's not a valid Graph Type!")


async def setup(bot):
    """Attach the diagnostics cog to the running bot.

    Args:
        bot: Bot instance that owns this object or callback.

    Returns:
        Any: Result produced by this function.
    """
    await bot.add_cog(Diagnostics(bot))