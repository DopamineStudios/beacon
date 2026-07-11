import discord
from discord import app_commands
from discord.ext import commands, tasks
import time
import psutil
import asyncio
import os
import io
from pathlib import Path
fonts_dir = Path(__file__).parent
os.environ["FONTCONFIG_PATH"] = str(fonts_dir.resolve())
import pyvips
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
        self.cached_graph_bytes = None
        self.cache_task.start()

        self.battery_cache = []
        self.battery_interval_mins = 10
        self.battery_duration_mins = 60
        self.battery_max_mins = 240
        self.battery_increment_mins = 20
        self.is_battery_idling = False
        self.battery_task.start()

        self.font_family_title = "Montserrat"


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

                loop = asyncio.get_running_loop()
                graph_buffer = await loop.run_in_executor(None, self.generate_latency_graph)
                if graph_buffer:

                    self.cached_graph_bytes = graph_buffer.getvalue()

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
        """Render the cached latency history into an in-memory PNG graph using pyvips.

        Returns:
            io.BytesIO | None: Generated latency graph result or None if insufficient samples.
        """
        try:
            data = list(self.latency_cache)
            num_samples = len(data)

            if num_samples < 2:
                return None

            scale_factor = 2
            width, height = 600 * scale_factor, 300 * scale_factor
            pad_top, pad_bot, pad_left, pad_right = 175, 80, 100, 40

            font_family_title = self.font_family_title
            font_family_labels = "Sans"

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

            bg = (pyvips.Image.black(width, height, bands=4) + [26, 26, 30, 255]).cast("uchar")
            base_mutable = bg.copy_memory()

            grid_colour = [60, 62, 68, 255]
            num_y_labels = 4
            for i in range(num_y_labels + 1):
                val = target_step * i
                y = (height - pad_bot) - (val / y_limit) * graph_height
                base_mutable = base_mutable.draw_rect(grid_colour, int(pad_left), int(y - scale_factor // 2),
                                                      int(graph_width),
                                                      int(1 * scale_factor), fill=True)

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

            composited_base = base_mutable.copy(interpretation="srgb").composite(fill_layer, "over")

            fg_mutable = pyvips.Image.black(width, height, bands=4).copy_memory()

            def draw_text(mutable_img, text, font_family, size, colour, target_x, target_y, anchor="mt"):
                try:
                    font_string = f"{font_family} {int(size)}"
                    print(font_string)
                    mask = pyvips.Image.text(text, font=font_string, dpi=72)
                except Exception as e:
                    mask = pyvips.Image.text(text, font=f"Sans {int(size)}", dpi=72)
                    print("Error in font:\n", e)

                if anchor == "mt":
                    x = target_x - mask.width // 2
                    y = target_y
                elif anchor == "rm":
                    x = target_x - mask.width
                    y = target_y - mask.height // 2
                else:
                    x = target_x
                    y = target_y

                mask_buffer = mask.write_to_memory()
                safe_mask = pyvips.Image.new_from_memory(mask_buffer, mask.width, mask.height, 1, "uchar")
                return mutable_img.draw_mask(colour, safe_mask, int(x), int(y))

            def draw_thick_line(mutable_img, colour, x1, y1, x2, y2, thickness):
                half = thickness // 2
                for d in range(-half, half + 1):
                    if abs(x2 - x1) > abs(y2 - y1):
                        mutable_img = mutable_img.draw_line(colour, int(x1), int(y1 + d), int(x2), int(y2 + d))
                    else:
                        mutable_img = mutable_img.draw_line(colour, int(x1 + d), int(y1), int(x2 + d), int(y2))
                return mutable_img

            fg_mutable = draw_text(
                fg_mutable,
                "API Latency Graph - Powered by Beacon",
                f"{font_family_title} Bold",
                24 * scale_factor,
                [255, 255, 255, 255],
                width / 2,
                70,
                anchor="mt"
            )

            y_label_colour = [115, 115, 115, 255]
            for i in range(num_y_labels + 1):
                val = target_step * i
                y = (height - pad_bot) - (val / y_limit) * graph_height
                fg_mutable = draw_text(fg_mutable, f"{int(val)}ms", font_family_labels, 10 * scale_factor,
                                       y_label_colour,
                                       pad_left - 15, y, anchor="rm")

            num_x_labels = 5
            tick_colour = [110, 110, 110, 255]
            for i in range(num_x_labels):
                sample_idx = int((i / (num_x_labels - 1)) * (num_samples - 1))
                x = pad_left + (i / (num_x_labels - 1)) * graph_width
                mins_ago = num_samples - 1 - sample_idx

                label = "Now" if mins_ago == 0 else (
                    f"{round(mins_ago / 60, 1)}h" if mins_ago >= 60 else f"{mins_ago}m")

                fg_mutable = fg_mutable.draw_rect(tick_colour, int(x - 1), int(height - pad_bot), 2, 10, fill=True)
                fg_mutable = draw_text(fg_mutable, label, font_family_labels, 12 * scale_factor, tick_colour, x,
                                       height - pad_bot + 25,
                                       anchor="mt")

            accent_rgba = accent_rgb + [255]
            line_thickness = 3 * scale_factor
            for i in range(len(points) - 1):
                fg_mutable = draw_thick_line(fg_mutable, accent_rgba, points[i][0], points[i][1], points[i + 1][0],
                                             points[i + 1][1],
                                             line_thickness)

            final_graph = composited_base.composite(fg_mutable.copy(interpretation="srgb"), "over")

            final_graph = final_graph.resize(0.5, kernel="lanczos3")

            buffer_data = final_graph.write_to_buffer(".png")
            return io.BytesIO(buffer_data)

        except Exception as e:
            import traceback
            self.bot.logger.error(f"Graph generation error: {e}\n{traceback.format_exc()}")
            return None

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
            avg_latency = f"{round(sum(self.latency_cache) / len(self.latency_cache))}ms"
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
        location_line = f"> Bot Host Location: `{location}`\n\n" if location else "\n"
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
                f"> Average API Latency: `{avg_latency}`\n\n"
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
        if not self.cached_graph_bytes:
            return await interaction.response.send_message(
                "Not enough data yet! The bot was restarted very recently. Please wait a few minutes.",
                ephemeral=True
            )
        try:
            buffer = io.BytesIO(self.cached_graph_bytes)
            file = discord.File(buffer, filename="graph.png")
            await interaction.response.send_message(content=None, attachments=file)
        except Exception as e:
            return await interaction.response.send_message(content=f"ERROR: {e}", ephemeral=True)

async def setup(bot):
    """Attach the diagnostics cog to the running bot.

    Args:
        bot: Bot instance that owns this object or callback.

    Returns:
        Any: Result produced by this function.
    """
    await bot.add_cog(Diagnostics(bot))