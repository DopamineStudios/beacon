import discord
from discord import app_commands
from discord.ext import commands, tasks
import time
import psutil
import asyncio
import os
import io
from PIL import Image, ImageDraw, ImageFont
from collections import deque
from .path import framework_version, BOLDFONT_PATH
from ..core import beacon_commands


class Diagnostics(commands.Cog):
    """Diagnostics cog that reports latency, uptime, and host health metrics.

    """
    def __init__(self, bot):
        """Initialize sampling state and start periodic latency collection.

        Args:
            bot: Bot instance that owns this object or callback.
        """
        self.bot = bot
        self.latency_cache = deque(maxlen=1440)
        self.temp_samples = []
        self.process = psutil.Process(os.getpid())
        self.process.cpu_percent(interval=None)
        self.current_cpu = 0.0
        self.cache_task.start()

        self.battery_cache = []
        self.battery_interval_mins = 10
        self.battery_duration_mins = 60
        self.battery_max_mins = 240
        self.battery_increment_mins = 20
        self.is_battery_idling = False
        self.battery_task.start()


    def cog_unload(self):
        """Stop background sampling when the cog is unloaded.

        Returns:
            Any: Result produced by this function.
        """
        self.cache_task.cancel()
        self.battery_task.cancel()

    @tasks.loop(seconds=5.0)
    async def cache_task(self):
        """Collect API latency samples and keep rolling latency averages.

        Returns:
            Any: Result produced by this function.
        """
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
            except asyncio.TimeoutError:
                total_latency = None
            except Exception as e:
                self.bot.logger.error(f"Beacon: {e}")
                total_latency = None

            if isinstance(total_latency, (int, float)):
                self.temp_samples.append(total_latency)

            if len(self.temp_samples) >= 12:
                avg_latency = sum(self.temp_samples) / len(self.temp_samples)
                self.latency_cache.append(avg_latency)
                self.temp_samples.clear()

        except Exception as e:
            self.bot.logger.critical(f"Beacon: {e}")

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
            self.bot.logger.error(f"Beacon: {e}")

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

    def generate_latency_graph(self):
        """Render the cached latency history into an in-memory PNG graph.

        Returns:
            Any: Generated latency graph result.
        """

        def get_secondary_colour(main_rgb, darken_factor=0.925, alpha=40):
            """
            Calculates a semi-transparent filler colour from a main line colour.

            Args:
                main_rgb (tuple): The (R, G, B) tuple of the main line.
                darken_factor (float): How much to dim the colour (default 92.5%).
                alpha (int): The transparency level (0-255).

            Returns:
                tuple: An (R, G, B, A) tuple for the filler.
            """
            secondary_rgb = tuple(max(0, min(255, int(channel * darken_factor))) for channel in main_rgb)

            return secondary_rgb + (alpha,)

        scale_factor = 2
        width, height = 600 * scale_factor, 300 * scale_factor
        pad_top, pad_bot, pad_left, pad_right = 175, 80, 100, 40

        img = Image.new("RGBA", (width, height), color=(30, 31, 34, 255))
        draw = ImageDraw.Draw(img)

        try:
            title_font = ImageFont.truetype(BOLDFONT_PATH, 22 * scale_factor)
        except Exception as e:
            self.bot.logger.error(f"Beacon: Custom font not found at {BOLDFONT_PATH}. Using default.\n{e}")
            title_font = ImageFont.load_default()

        draw.text(
            (50, 60),
            "Average API Latency - Powered by Beacon",
            fill=(255, 255, 255, 255),
            font=title_font
        )

        data = list(self.latency_cache)
        num_samples = len(data)

        if num_samples < 2:
            return None

        max_val = max(data) if data else 100
        steps = [10, 25, 50, 100, 250, 500, 1000]
        target_step = next((s for s in steps if s > max_val / 4), max_val / 4)
        y_limit = target_step * 4

        grid_color = (60, 62, 68, 255)
        num_y_labels = 4
        graph_height = height - pad_top - pad_bot
        for i in range(num_y_labels + 1):
            val = target_step * i
            y = (height - pad_bot) - (val / y_limit) * graph_height
            draw.line([(pad_left, y), (width - pad_right, y)], fill=grid_color, width=1 * scale_factor)
            draw.text((pad_left - 15, y), f"{int(val)}ms", fill=(180, 180, 180), anchor="rm",
                      font_size=12 * scale_factor)

        graph_width = width - pad_left - pad_right

        num_x_labels = 5
        for i in range(num_x_labels):
            sample_idx = int((i / (num_x_labels - 1)) * (num_samples - 1))

            x = pad_left + (i / (num_x_labels - 1)) * graph_width

            mins_ago = num_samples - 1 - sample_idx

            if mins_ago == 0:
                label = "Now"
            elif mins_ago >= 60:
                label = f"{round(mins_ago / 60, 1)}h"
            else:
                label = f"{mins_ago}m"

            draw.line([(x, height - pad_bot), (x, height - pad_bot + 10)], fill=(150, 150, 150), width=2)
            draw.text((x, height - pad_bot + 25), label, fill=(150, 150, 150), anchor="mt", font_size=12 * scale_factor)

        points = []
        for i, val in enumerate(data):
            x = pad_left + (i / (num_samples - 1)) * graph_width
            y = (height - pad_bot) - (val / y_limit) * graph_height
            points.append((x, y))

        fill_points = [(pad_left, height - pad_bot)] + points + [(width - pad_right, height - pad_bot)]
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        secondary_colour = get_secondary_colour(self.bot.accent_colour)
        overlay_draw.polygon(fill_points, fill=secondary_colour)
        img = Image.alpha_composite(img, overlay)

        draw = ImageDraw.Draw(img)
        draw.line(points, fill=self.bot.accent_colour, width=3 * scale_factor, joint="round")

        img = img.resize((600, 300), resample=Image.LANCZOS)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer

    @app_commands.command(name="ping", description="Get detailed latency and bot information")

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

        if self.latency_cache:
            avg_latency = f"{round(sum(self.latency_cache) / len(self.latency_cache), 2)}ms"
            sample_count = len(self.latency_cache)
        else:
            avg_latency = "Calculating..."
            sample_count = 0
        start_time = time.time()
        await interaction.response.send_message(initial_message)
        end_time = time.time()
        gateway_raw = str(self.bot.ws.gateway)
        gateway_node = gateway_raw.split('gateway-')[-1].split('.')[
            0] if 'gateway-' in gateway_raw else "Global/Unknown"
        round_latency = round((end_time - start_time) * 1000)
        discord_latency = round(self.bot.latency * 1000)
        location = None
        if not self.bot.secure_mode:
            location = await self.get_location()
        location_line = f"> Bot Host Location: `{location}`\n\n" if location else ""
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
                f"> Powered by Beacon `v{framework_version}`\n\n"
                f"> Connected to Discord Gateway: `{gateway_node}`\n"
                f"{location_line}"
                f"> API Latency: `{connection_latency}ms`\n"
                f"> Round-trip Latency: `{round_latency}ms`\n"
                f"> Heartbeat/WebSocket Latency: `{discord_latency}ms`\n\n"
                f"> Average API Latency: `{avg_latency}` (over `{sample_count}` samples where each sample is average of 12 samples)\n\n"
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
    async def graph(self, interaction: discord.Interaction):
        """Return a generated latency trend graph when enough samples exist.

        Args:
            interaction: Interaction context received from Discord.

        Returns:
            Any: Result produced by this function.
        """
        await interaction.response.defer()
        try:
            graph_buffer = self.generate_latency_graph()
        except Exception as e:
            return await interaction.edit_original_response(content=f"ERROR: {e}")
        if graph_buffer:
            file = discord.File(graph_buffer, filename="graph.png")
            await interaction.edit_original_response(content=None, attachments=[file])
        else:
            await interaction.edit_original_response(content="Not enough data yet! The bot or cog was restarted very recently. Please wait a few minutes.")

async def setup(bot):
    """Attach the diagnostics cog to the running bot.

    Args:
        bot: Bot instance that owns this object or callback.

    Returns:
        Any: Result produced by this function.
    """
    await bot.add_cog(Diagnostics(bot))