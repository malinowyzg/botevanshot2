import discord
from discord import app_commands # Potrzebne do komend slash i modali
from discord.ui import Modal, TextInput

# --- Konfiguracja Bota ---
TOKEN = "MTM4MjEzNjM2MDQwNzY2NjgwMA.GOmb3A.4fb71jT08CErbRJxQzVeFa9E1qMIUZaeqkBKug"  # Wklej tutaj token swojego bota
GUILD_ID = 1045001836224073820 # Wklej ID swojego serwera (gildii)

# --- Inicjalizacja Bota ---
intents = discord.Intents.default()
# Tworzymy klienta bota, który będzie obsługiwał drzewo komend
class MyBot(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        # Drzewo komend przechowuje wszystkie komendy slash
        self.tree = app_commands.CommandTree(self)

    # Funkcja do synchronizacji komend przy starcie
    async def setup_hook(self):
        guild_obj = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild_obj)
        await self.tree.sync(guild=guild_obj)

bot = MyBot(intents=intents)

# --- Definicja Modalu (Formularza) ---
class PalletStatusModal(Modal, title="Weryfikacja Stanu Paletowego"):
    # Pole tekstowe dla PEPCO
    pepco_count = TextInput(
        label="PEPCO",
        placeholder="Ilość Palet PEPCO",
        style=discord.TextStyle.short,
        required=True,
        max_length=5
    )

    # Pole tekstowe dla TEDI
    tedi_count = TextInput(
        label="TEDi",
        placeholder="Ilość Palet TEDI.",
        style=discord.TextStyle.short,
        required=True,
        max_length=5
    )

    # Pole tekstowe dla ZWROTNYCH
    returns_count = TextInput(
        label="ZWROTNE",
        placeholder="Ilość Palet ZWROTNYCH.",
        style=discord.TextStyle.short,
        required=True,
        max_length=5
    )

    # Ta funkcja jest wywoływana, gdy użytkownik kliknie "Wyślij"
    async def on_submit(self, interaction: discord.Interaction):
        # Pobieramy dane z formularza
        pepco = self.pepco_count.value
        tedi = self.tedi_count.value
        zwrotne = self.returns_count.value
        
        # Tworzymy embeda z odpowiedzią, podobnego do tego z poprzedniego zadania
        embed = discord.Embed(
            title="📦 Zaktualizowano Stan Paletowy 📦",
            description=f"Nowe wartości zostały zapisane przez **{interaction.user.mention}**.",
            color=discord.Color.green()
        )
        embed.add_field(name="PEPCO", value=f"`{pepco}` sztuk", inline=False)
        embed.add_field(name="TEDi", value=f"`{tedi}` sztuk", inline=False)
        embed.add_field(name="ZWROTNE", value=f"`{zwrotne}` sztuk", inline=False)
        embed.set_footer(text="Pamiętaj, zliczamy fizycznie ilość palet na oddziale i te wartości wprowadzamy do formularza.")

        # Odpowiadamy na interakcję, wysyłając embed
        # ephemeral=False oznacza, że wiadomość będzie widoczna dla wszystkich na kanale
        await interaction.response.send_message(embed=embed, ephemeral=False)

# --- Definicja Komendy Slash ---
@bot.tree.command(name="palety", description="Otwiera formularz do aktualizacji stanu paletowego.")
async def palety(interaction: discord.Interaction):
    """Wyświetla modal do aktualizacji stanu palet."""
    # Tworzymy i wysyłamy modal do użytkownika, który wpisał komendę
    await interaction.response.send_modal(PalletStatusModal())
    
    
    
# ---------DODANIE FORMULARZA ZADANIE---------------------------------
# --- Definicja Modalu (Formularza) ---
class ZadanieStatusModal(Modal, title="WYKONANIE ZADANIA DZIENNEGO"):
    # Pole tekstowe dla PEPCO
    pepco_count = TextInput(
        label="Zadanie",
        placeholder="Jakie Zadanie Wykonałeś?",
        style=discord.TextStyle.long,
        required=True,
        max_length=100
    )
    
# Ta funkcja jest wywoływana, gdy użytkownik kliknie "Wyślij"
    async def on_submit(self, interaction: discord.Interaction):
        # Pobieramy dane z formularza
        pepco = self.pepco_count.value
    
        # Tworzymy embeda z odpowiedzią, podobnego do tego z poprzedniego zadania
        embed = discord.Embed(
            title="📋WYKONANIE ZADANIA📋",
            description=f"Zadnie Wykonane przez **{interaction.user.mention}**.",
            color=discord.Color.red()
        )
        embed.add_field(name="Zadanie", value=f"`{pepco}` zostało wykonane!", inline=False)
        embed.set_footer(text="Poprawnie Zapisano Rekord w Kopi Zapasowej Maszyny.")

        # Odpowiadamy na interakcję, wysyłając embed
        # ephemeral=False oznacza, że wiadomość będzie widoczna dla wszystkich na kanale
        await interaction.response.send_message(embed=embed, ephemeral=False)

# --- Definicja Komendy Slash ---
@bot.tree.command(name="zadanie", description="Zadanie Dzienne.")
async def zadanie(interaction: discord.Interaction):
    """Wyświetla modal do aktualizacji stanu palet."""
    # Tworzymy i wysyłamy modal do użytkownika, który wpisał komendę
    await interaction.response.send_modal(ZadanieStatusModal())
    
# --- Event gotowości bota ---
@bot.event
async def on_ready():
    print(f'Zalogowano jako {bot.user.name}')
    print(f'Bot jest gotowy do przyjmowania komend.')
    print('Przeprowadzono Spójność Plików Bota z Maszyną Hostingu.')

# --- Uruchomienie Bota ---
bot.run(TOKEN)