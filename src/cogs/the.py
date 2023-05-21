import io
import traceback

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from PIL import ImageSequence

from cogs.utils import embed_templates

from typing import Any
import PIL
import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageSequence
import aiohttp
import io
from moviepy.editor import *

class The(commands.Cog):
    """
    This cog lets you make a "the" barnacle boy laser eyes meme
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.background_url = "https://i.kym-cdn.com/photos/images/newsfeed/001/777/063/d42.png"
        self.x = 30
        self.y = 340

    async def fetch_image(self, url: str) -> io.BytesIO:
        """
        Fetch the image from the URL

        Parameters
        ----------
        url (str): url

        Returns
        ----------
        (io.BytesIO): data buffer
        """
        if not url:
            return None

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return None
                data = io.BytesIO(await resp.read())
                return data

    def outline_text(
        self,
        draw: ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont,
        x: int,
        y: int,
        thickness: int,
    ) -> None:
        """
        Outlines given text
        """

        for dx in range(-thickness, thickness + 1):
            for dy in range(-thickness, thickness + 1):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), text, font=font, fill="black")
        draw.text((x, y), text, font=font, fill="white")

    @app_commands.command()
    async def the(
        self, interaction: discord.Interaction, top_text: str = "", image_url: str = "", bottom_text: str = ""
    ):
        """
        Generer en barnacle boy laser eyes THE mem basert på gitt bilde/tekst

        Parameters
        ----------
        interaction (discord.Interaction): Slash command context object
        caption (str): top text
        image_url (str): image url
        bottom_text (str): bottom text

        Returns
        ----------
        (discord.File): an image or a video
        """
        await interaction.response.defer()
        gif = False
        video = False
        try:
            bg_data = await self.fetch_image(self.background_url)
            background = Image.open(bg_data)

            image_data = await self.fetch_image(image_url)

            if image_data:
                try:
                    image = Image.open(image_data)

                    if image.format.lower() == "gif":
                        gif = True
                        frames = []
                        for frame in ImageSequence.Iterator(image):
                            frame = frame.convert("RGBA").resize((200, 200), Image.ANTIALIAS)
                            new_frame = background.copy().convert("RGBA")
                            new_frame.alpha_composite(frame, (self.x, self.y))
                            frames.append(new_frame)

                        draw = ImageDraw.Draw(frames[0], "RGBA")
                    else:
                        image = image.convert("RGBA").resize((200, 200), Image.ANTIALIAS)
                        background = background.convert("RGBA")
                        background.alpha_composite(image, (self.x, self.y))

                        draw = ImageDraw.Draw(background, "RGBA")

                except PIL.UnidentifiedImageError:
                    video = True
                    video_clip = VideoFileClip(io.BytesIO(image_data.getvalue()))
                    audio_clip = video_clip.audio
                    image = video_clip.resize((200, 200))

                    # Convert the background to a video clip with the same duration as the input video
                    bg_video_clip = ImageClip(background).set_duration(video_clip.duration).resize((1280, 720))

                    # Overlay the input video on the background video
                    result = CompositeVideoClip([bg_video_clip, image.set_position((self.x, self.y))])

                    # Set the audio of the resulting video
                    result = result.set_audio(audio_clip)

            font = ImageFont.truetype("./src/assets/fonts/impact.ttf", 120)

            if top_text:
                text_x, text_y = (210, -10)
                self.outline_text(draw, top_text.upper(), font, text_x, text_y, thickness=5)

            if bottom_text:
                text_x, text_y = (150, 550)
                self.outline_text(draw, bottom_text.upper(), font, text_x, text_y, thickness=5)

            if gif:
                with io.BytesIO() as output:
                    frames[0].save(
                        output,
                        format="GIF",
                        save_all=True,
                        append_images=frames[1:],
                        duration=image.info["duration"],
                        loop=0,
                        transparency=image.info.get("transparency", 0),
                        disposal=2,  # Use 'restore to background color' disposal method
                    )
                    output.seek(0)
                    await interaction.followup.send(file=discord.File(output, "result.gif"))
            elif video:
                with io.BytesIO() as output:
                    result.write_videofile(
                        output.name,
                        codec="libx264",
                        audio_codec="aac",
                        temp_audiofile="temp_audio.m4a",
                        remove_temp=True,
                        threads=4,
                    )
                    output.seek(0)
                    await interaction.followup.send(file=discord.File(output, "result.mp4"))
            else:
                with io.BytesIO() as output:
                    background.save(output, format="PNG")
                    output.seek(0)
                    await interaction.followup.send(file=discord.File(output, "result.png"))

        except Exception as e:
            self.bot.logger.warning(f"An error occurred while processing the images: {e}")
            traceback.print_exc()
            await interaction.followup.send(
                embed=embed_templates.error_fatal(
                    interaction, "Klarte ikke å generere mem! Har du gitt en ordentlig bildelenke?"
                )
            )


async def setup(bot):
    """
    Add the cog to the bot on extension load

    Parameters
    ----------
    bot (commands.Bot): Bot instance
    """

    await bot.add_cog(The(bot))
