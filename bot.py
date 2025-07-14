import discord
from discord.ext import commands
from PIL import Image
import pytesseract
import io

# Ustaw ścieżkę Tesseract w kontenerze Linux (Fly.io będzie używać /usr/bin/tesseract)
pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='.', intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Zalogowano jako {bot.user}")

@bot.command(name='odczytaj')
async def odczytaj(ctx):
    if not ctx.message.attachments:
        await ctx.send("❗ Wyślij obraz jako załącznik do komendy `.odczytaj`.")
        return

    attachment = ctx.message.attachments[0]
    image_bytes = await attachment.read()
    image = Image.open(io.BytesIO(image_bytes))

    text = pytesseract.image_to_string(image, lang='pol')

    embed = discord.Embed(
        title="📄 Wynik OCR",
        description=text if text.strip() else "*Nie znaleziono tekstu.*",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

bot.run('YOUR_DISCORD_BOT_TOKEN')
