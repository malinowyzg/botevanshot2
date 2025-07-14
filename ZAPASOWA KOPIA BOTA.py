import discord
from discord.ext import commands
from discord import app_commands, ui
import json
import os
import uuid
from datetime import datetime, timezone

# ==================== KONFIGURACJA BOTA ====================
# WAŻNE: Nie udostępniaj swojego tokenu publicznie!
# ZMIENIONO: Zalecane jest używanie zmiennych środowiskowych do przechowywania tokenu.
# Dla uproszczenia w przykładzie pozostawiono token, ale w rzeczywistej aplikacji użyj:
# TOKEN = os.getenv('DISCORD_BOT_TOKEN')
# >>> BARDZO WAŻNE: ZASTĄP PONIŻSZY TOKEN SWOIM RZECZYWISTYM TOKENEM BOTA! <<<
TOKEN = 'MTM2MzAxNzY1NzAzMjUwNzUzMg.GlRcPp.5rSB_nudBt5QAcc9hnXzoj-p13qt4p5xpMKE28' # ZASTĄP TO SWOIM RZECZYWISTYM TOKENEM!

# ID kanału, na który bot będzie wysyłał ogłoszenia o pojazdach (np. "baza-pojazdow").
# PAMIĘTAJ: Upewnij się, że te ID są poprawne dla Twojego serwera Discord.
# Aby znaleźć ID kanału/roli/kategorii, włącz tryb deweloperski w Discordzie (Ustawienia użytkownika > Zaawansowane),
# a następnie kliknij prawym przyciskiem myszy na element i wybierz "Kopiuj ID".
BAZA_POJAZDOW_CHANNEL_ID = 1257468612500000908 # PRZYKŁADOWE ID, UPEWNIJ SIĘ, ŻE JEST POPRAWNE

# ID kanału, na który bot będzie wysyłał logi sprzedanych pojazdów.
LOGI_SPRZEDAZY_CHANNEL_ID = 1332862482208788592 # PRZYKŁADOWE ID

# Nazwa pliku JSON do przechowywania danych ogłoszeń i licytacji.
DATA_FILE = 'ogloszenia_data.json'

# ID roli, która ma być oznaczana (@mention) przy nowych ogłoszeniach/licytacjach.
# Ustaw na 0 lub usuń, jeśli nie chcesz oznaczać żadnej roli.
ROLA_DO_OZNACZENIA_ID = 1193965907190481047 # PRZYKŁADOWE ID

# ID kanału dla powiadomień o wypłatach (np. kanał dla zarządu/księgowości).
KANAL_WYPLAT_ID = 1392665912510910576 # PRZYKŁADOWE ID

# Upewnij się, że te ID są poprawne dla Twojego serwera
KANAL_ZGLOSZEN_ID = 1336813393780277338  # PRZYKŁADOWE ID
KATEGORIA_ZGLOSZEN_ID = 1378049281155666101 # PRZYKŁADOWE ID
ROLA_WSPARCIA_ID = 1193883511338311720 # PRZYKŁADOWE ID
ROLA_CZLONEK_ZARZADU_ID = 1193883867141128212 # PRZYKŁADOWE ID Roli "Członek Zarządu"

# ----- INTENTY BOTA -----
# BARDZO WAŻNE: Upewnij się, że te intenty są włączone w Twojej aplikacji Discord (Developer Portal -> Bot -> Privileged Gateway Intents)
intents = discord.Intents.default()
intents.message_content = True # Wymagane do odczytywania treści wiadomości (np. dla komend tekstowych, jeśli takie masz)
intents.members = True       # Wymagane do pobierania informacji o członkach serwera (np. do pingowania użytkowników)
intents.guilds = True        # Wymagane do operacji na serwerach (np. tworzenia kanałów)
bot = commands.Bot(command_prefix='/', intents=intents)

# ==================== FUNKCJE POMOCNICZE DO ZARZĄDZANIA DANYMI ====================

def load_data():
    """
    Wczytuje dane ogłoszeń i licytacji z pliku JSON.
    Jeśli plik nie istnieje lub jest pusty, zwraca początkową strukturę danych.
    """
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                print(f"Ostrzeżenie: Plik {DATA_FILE} jest uszkodzony lub pusty. Inicjuję nową strukturę danych.")
                data = {}
            if "ogloszenia" not in data:
                data["ogloszenia"] = {}
            if "licytacje" not in data:
                data["licytacje"] = {}
            return data
    return {"ogloszenia": {}, "licytacje": {}}

def save_data(data):
    """
    Zapisuje dane ogłoszeń i licytacji do pliku JSON.
    """
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

ogloszenia_db = load_data()

# ==================== MODALE (FORMULARZE) DLA INTERAKCJI UŻYTKOWNIKA ====================

class KwotaSprzedazyModal(ui.Modal, title='Potwierdź Sprzedaż Pojazdu'):
    def __init__(self, ogloszenie_id: str):
        super().__init__()
        self.ogloszenie_id = ogloszenie_id

        self.kwota = ui.TextInput(
            label="Za jaką kwotę został sprzedany pojazd?",
            placeholder="Wprowadź kwotę, np. 90000 Dolarów",
            required=True,
            max_length=50
        )
        self.add_item(self.kwota)

    async def on_submit(self, interaction: discord.Interaction):
        global ogloszenia_db

        kwota_sprzedazy = self.kwota.value

        if self.ogloszenie_id not in ogloszenia_db["ogloszenia"]:
            await interaction.response.send_message(
                "Błąd: Nie znaleziono ogłoszenia o podanym ID.",
                ephemeral=True
            )
            return

        ogloszenie = ogloszenia_db["ogloszenia"][self.ogloszenie_id]

        ogloszenie['status'] = 'SPRZEDANY'
        ogloszenie['kwota_sprzedazy'] = kwota_sprzedazy
        ogloszenie['data_sprzedazy'] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        save_data(ogloszenia_db)

        try:
            if 'baza_message_id' in ogloszenie and ogloszenie['baza_message_id']:
                baza_kanal = bot.get_channel(BAZA_POJAZDOW_CHANNEL_ID)
                if baza_kanal:
                    try:
                        baza_wiadomosc = await baza_kanal.fetch_message(ogloszenie['baza_message_id'])
                        await baza_wiadomosc.delete()
                        print(f"Usunięto ogłoszenie o ID {self.ogloszenie_id} z kanału bazy pojazdów.")
                    except discord.NotFound:
                        print(f"Wiadomość z ogłoszeniem o ID {ogloszenie['baza_message_id']} w bazie pojazdów nie znaleziona (być może już usunięta).")
                    except discord.Forbidden:
                        print(f"Błąd uprawnień: Nie mam uprawnień do usunięcia wiadomości w kanale bazy pojazdów.")
                else:
                    print(f"Błąd: Nie znaleziono kanału bazy pojazdów o ID: {BAZA_POJAZDOW_CHANNEL_ID} do usunięcia wiadomości.")

            if 'powiadomienie_message_id' in ogloszenie and ogloszenie['powiadomienie_message_id']:
                powiadomienie_kanal_id = ogloszenie.get('powiadomienie_channel_id')
                if powiadomienie_kanal_id:
                    powiadomienie_kanal = bot.get_channel(powiadomienie_kanal_id)
                    if powiadomienie_kanal:
                        try:
                            powiadomienie_wiadomosc = await powiadomienie_kanal.fetch_message(ogloszenie['powiadomienie_message_id'])
                            await powiadomienie_wiadomosc.delete()
                            print(f"Usunięto powiadomienie o ogłoszeniu o ID {self.ogloszenie_id} z kanału {powiadomienie_kanal.name}.")
                        except discord.NotFound:
                            print(f"Wiadomość z powiadomieniem o ID {ogloszenie['powiadomienie_message_id']} nie znaleziona (być może już usunięta).")
                        except discord.Forbidden:
                            print(f"Błąd uprawnień: Nie mam uprawnień do usunięcia wiadomości w kanale powiadomień.")
                    else:
                        print(f"Błąd: Nie znaleziono kanału powiadomień o ID: {powiadomienie_kanal_id} do usunięcia wiadomości.")
                else:
                    print(f"Brak zapisanego ID kanału powiadomień dla ogłoszenia {self.ogloszenie_id}.")

            await interaction.response.send_message("Ogłoszenie zostało oznaczone jako sprzedane i usunięte z obu kanałów.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("Błąd: Nie mam uprawnień do usunięcia jednej z wiadomości ogłoszenia. Skontaktuj się z administratorem bota.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Wystąpił nieoczekiwany błąd podczas usuwania wiadomości: {e}", ephemeral=True)

        logi_kanal = bot.get_channel(LOGI_SPRZEDAZY_CHANNEL_ID)
        if logi_kanal:
            log_embed = discord.Embed(
                title=f"Zarejestrowano Sprzedaż Pojazdu: {ogloszenie['Nazwa Pojazdu']}",
                color=discord.Color.orange()
            )
            log_embed.add_field(name="Kwota Sprzedaży", value=kwota_sprzedazy, inline=True)
            log_embed.add_field(name="Sprzedający", value=ogloszenie['Sprzedający'], inline=True)
            log_embed.add_field(name="ID Ogłoszenia", value=self.ogloszenie_id, inline=False)
            log_embed.add_field(name="Zarejestrowano przez", value="System (Modal)", inline=True)
            log_embed.add_field(name="Data Sprzedaży", value=ogloszenie['data_sprzedazy'], inline=True)
            if 'Obniżka' in ogloszenie and ogloszenie['Obniżka'] != "Brak":
                log_embed.add_field(name="Możliwa Obniżka", value=ogloszenie['Obniżka'], inline=False)

            log_view = WyplaconoView(self.ogloszenie_id, kwota_sprzedazy, ogloszenie['Sprzedający'])
            try:
                await logi_kanal.send(embed=log_embed, view=log_view)
                print(f"Informacja o sprzedaży '{ogloszenie['Nazwa Pojazdu']}' wysłana na kanał logów z przyciskiem WYPŁACONO.")
            except discord.Forbidden:
                print(f"Błąd: Nie mam uprawnień do wysłania wiadomości na kanał logów o ID: {LOGI_SPRZEDAZY_CHANNEL_ID}.")
            except Exception as e:
                print(f"Wystąpił błąd podczas wysyłania na kanał logów: {e}")
        else:
            print(f"Błąd: Nie znaleziono kanału logów sprzedaży o ID: {LOGI_SPRZEDAZY_CHANNEL_ID}. Nie można wysłać wpisu.")


# ==================== WIDOKI (VIEW) DLA PRZYCISKÓW INTERAKTYWNYCH ====================

class OgloszenieView(ui.View):
    def __init__(self, ogloszenie_id: str):
        super().__init__(timeout=None)
        self.ogloszenie_id = ogloszenie_id

    @ui.button(label="POJAZD SPRZEDANY", style=discord.ButtonStyle.success, custom_id="sold_vehicle_button")
    async def confirm_sold(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(KwotaSprzedazyModal(self.ogloszenie_id))

class WyplaconoView(ui.View):
    def __init__(self, ogloszenie_id: str, kwota_sprzedazy: str, sprzedajacy: str):
        super().__init__(timeout=None)
        self.ogloszenie_id = ogloszenie_id
        self.kwota_sprzedazy = kwota_sprzedazy
        self.sprzedajacy = sprzedajacy

    @ui.button(label="WYPŁACONO", style=discord.ButtonStyle.primary, custom_id="paid_out_button")
    async def paid_out_button(self, interaction: discord.Interaction, button: ui.Button):
        kanal_wyplat = bot.get_channel(KANAL_WYPLAT_ID)
        if kanal_wyplat:
            powiadomienie_embed = discord.Embed(
                title="✅ Wypłata Zarejestrowana",
                description=f"Zarejestrowano wypłatę.",
                color=discord.Color.green()
            )
            powiadomienie_embed.add_field(name="ID Ogłoszenia", value=self.ogloszenie_id, inline=True)
            powiadomienie_embed.add_field(name="Sprzedający", value=self.sprzedajacy, inline=True)
            powiadomienie_embed.add_field(name="Kwota Wypłaty", value=self.kwota_sprzedazy, inline=False)
            powiadomienie_embed.add_field(name="Data Wypłaty", value=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"), inline=True)
            powiadomienie_embed.set_footer(text=f"Potwierdzono przez: System")

            try:
                await kanal_wyplat.send(embed=powiadomienie_embed)
                await interaction.response.send_message("Potwierdzono wypłatę. Powiadomienie wysłane na kanał wypłat.", ephemeral=True)

                button.disabled = True
                await interaction.message.edit(view=self)
                print(f"Wypłata dla ogłoszenia '{self.ogloszenie_id}' potwierdzona. Powiadomienie wysłane.")
            except discord.Forbidden:
                await interaction.response.send_message(
                    f"Błąd: Nie mam uprawnień do wysłania wiadomości na kanał wypłat o ID: {KANAL_WYPLAT_ID}.",
                    ephemeral=True
                )
            except Exception as e:
                await interaction.response.send_message(
                    f"Wystąpił błąd podczas wysyłania powiadomienia o wypłacie: {e}",
                    ephemeral=True
                )
        else:
            await interaction.response.send_message(
                f"Błąd: Nie znaleziono kanału wypłat o ID: {KANAL_WYPLAT_ID}. Nie można wysłać powiadomienia.",
                ephemeral=True
            )

# ==================== EVENTY BOTA DISCORD ====================

@bot.event
async def on_ready():
    """
    Funkcja wywoływana, gdy bot jest gotowy i zalogowany do Discorda.
    Synchronizuje komendy slash i sprawdza dostępność skonfigurowanych kanałów/ról.
    """
    print(f'Zalogowano jako {bot.user}!')
    try:
        # Synchronizacja komend slash z Discordem
        synced = await bot.tree.sync()
        print(f"Zsynchronizowano {len(synced)} komend slash.")

        # Dodaj trwały widok po restarcie bota (ważne dla przycisków w panelu zgłoszeń)
        # Upewnij się, że PanelZgloszenView jest zdefiniowany przed wywołaniem bot.add_view
        bot.add_view(PanelZgloszenView())


        # Sprawdzenie dostępności kanałów i ról
        baza_kanal = bot.get_channel(BAZA_POJAZDOW_CHANNEL_ID)
        if baza_kanal:
            print(f"Kanał bazy pojazdów znaleziony: #{baza_kanal.name} (ID: {BAZA_POJAZDOW_CHANNEL_ID})")
        else:
            print(f"UWAGA: Kanał bazy pojazdów o ID {BAZA_POJAZDOW_CHANNEL_ID} NIE ZNALEZIONY. Upewnij się, że ID jest poprawne i bot ma dostęp do tego kanału.")

        logi_kanal = bot.get_channel(LOGI_SPRZEDAZY_CHANNEL_ID)
        if logi_kanal:
            print(f"Kanał logów sprzedaży znaleziony: #{logi_kanal.name} (ID: {LOGI_SPRZEDAZY_CHANNEL_ID})")
        else:
            print(f"UWAGA: Kanał logów sprzedaży o ID {LOGI_SPRZEDAZY_CHANNEL_ID} NIE ZNALEZIONY. Upewnij się, że ID jest poprawne i bot ma dostęp do tego kanału.")

        kanal_wyplat = bot.get_channel(KANAL_WYPLAT_ID)
        if kanal_wyplat:
            print(f"Kanał wypłat znaleziony: #{kanal_wyplat.name} (ID: {KANAL_WYPLAT_ID})")
        else:
            print(f"UWAGA: Kanał wypłat o ID {KANAL_WYPLAT_ID} NIE ZNALEZIONY. Upewnij się, że ID jest poprawne i bot ma dostęp do tego kanału.")

        if ROLA_DO_OZNACZENIA_ID:
            # Poprawka: Sprawdź, czy bot jest na jakimś serwerze, zanim spróbujesz pobrać rolę
            if bot.guilds:
                # Pobierz rolę z pierwszego dostępnego serwera, na którym jest bot
                # W bardziej złożonych botach możesz chcieć sprawdzić konkretne serwery
                rola = bot.guilds[0].get_role(ROLA_DO_OZNACZENIA_ID)
                if rola:
                    print(f"Rola do oznaczenia znaleziona: @{rola.name} (ID: {ROLA_DO_OZNACZENIA_ID})")
                else:
                    print(f"UWAGA: Rola do oznaczenia o ID {ROLA_DO_OZNACZENIA_ID} NIE ZNALEZIONA na dostępnych serwerach. Upewnij się, że ID jest poprawne.")
            else:
                print(f"UWAGA: Bot nie jest na żadnym serwerze, nie można sprawdzić roli do oznaczenia.")


        # Sprawdzenie kanałów i ról dla systemu zgłoszeń
        kanal_zgloszen = bot.get_channel(KANAL_ZGLOSZEN_ID)
        if kanal_zgloszen:
            print(f"Kanał zgłoszeń znaleziony: #{kanal_zgloszen.name} (ID: {KANAL_ZGLOSZEN_ID})")
        else:
            print(f"UWAGA: Kanał zgłoszeń o ID {KANAL_ZGLOSZEN_ID} NIE ZNALEZIONY.")

        kategoria_zgloszen = bot.get_channel(KATEGORIA_ZGLOSZEN_ID)
        if kategoria_zgloszen and isinstance(kategoria_zgloszen, discord.CategoryChannel):
            print(f"Kategoria zgłoszeń znaleziona: #{kategoria_zgloszen.name} (ID: {KATEGORIA_ZGLOSZEN_ID})")
        else:
            print(f"UWAGA: Kategoria zgłoszeń o ID {KATEGORIA_ZGLOSZEN_ID} NIE ZNALEZIONA lub nie jest kategorią.")

        if ROLA_WSPARCIA_ID:
            if bot.guilds: # Upewnij się, że bot jest na jakimś serwerze
                # Pobierz rolę z pierwszego dostępnego serwera, na którym jest bot
                # W bardziej złożonych botach możesz chcieć sprawdzić konkretne serwery
                rola_wsparcia = bot.guilds[0].get_role(ROLA_WSPARCIA_ID)
                if rola_wsparcia:
                    print(f"Rola wsparcia znaleziona: @{rola_wsparcia.name} (ID: {ROLA_WSPARCIA_ID})")
                else:
                    print(f"UWAGA: Rola wsparcia o ID {ROLA_WSPARCIA_ID} NIE ZNALEZIONA na dostępnych serwerach.")
            else:
                print("UWAGA: Bot nie jest na żadnym serwerze, nie można sprawdzić roli wsparcia.")

    except Exception as e:
        print(f"Błąd podczas synchronizacji komend slash lub sprawdzania kanałów: {e}")

# ==================== KOMENDY SLASH DLA UŻYTKOWNIKÓW ====================

@bot.tree.command(name="dodaj", description="Dodaj ogłoszenie sprzedaży pojazdu do komisu.")
@app_commands.describe(
    nazwa_pojazdu="Pełna nazwa pojazdu (np. Dinka Jester)",
    sprzedajacy_imie="Imię sprzedającego",
    cena_salonowa="Cena pojazdu w salonie (np. 120000 )",
    cena_komis="Cena pojazdu w naszym komisie (np. 95000 )",
    dodatki="Lista dodatków/wyposażenia (np. Silnik, Felgi itp.)",
    mozliwa_obnizka="O ile tysięcy można zejść z ceny (np. 5 tys.)", # Zmieniona kolejność
    zdjecia_link="Link do zdjęcia pojazdu (np. Imgur, Discord CDN)."  # Zmieniona kolejność
)
async def dodaj_ogloszenie(
    interaction: discord.Interaction,
    nazwa_pojazdu: str,
    sprzedajacy_imie: str,
    cena_salonowa: str,
    cena_komis: str,
    dodatki: str,
    mozliwa_obnizka: str = "Brak",
    zdjecia_link: str = "Brak"
):
    global ogloszenia_db

    if zdjecia_link != "Brak" and not (zdjecia_link.startswith("http://") or zdjecia_link.startswith("https://")):
        await interaction.response.send_message(
            "Podany link do zdjęcia jest nieprawidłowy. Upewnij się, że zaczyna się od `http://` lub `https://`.",
            ephemeral=True
        )
        return

    ogloszenie_id = str(uuid.uuid4())

    ogloszenie_data = {
        "ID": ogloszenie_id,
        "Nazwa Pojazdu": nazwa_pojazdu,
        "Sprzedający": sprzedajacy_imie,
        "Cena Salonowa": cena_salonowa,
        "Cena w Naszym Komisie": cena_komis,
        "Dodatki Pojazdu": dodatki,
        "Obniżka": mozliwa_obnizka,
        "Zdjęcia Pojazdu": zdjecia_link,
        "Dodano przez": interaction.user.display_name,
        "Dodano przez ID": interaction.user.id,
        "Data dodania": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "status": "AKTYWNE",
        "baza_message_id": None,
        "powiadomienie_message_id": None,
        "powiadomienie_channel_id": None
    }
    ogloszenia_db["ogloszenia"][ogloszenie_id] = ogloszenie_data

    embed_response = discord.Embed(
        title=f"{nazwa_pojazdu} - {cena_komis}",
        description="Pojazd został dodany do oferty komisu!",
        color=discord.Color.blue()
    )
    embed_response.add_field(name="🙋‍♂️ Sprzedający", value=sprzedajacy_imie, inline=False)
    embed_response.add_field(name="🏢 Cena Salonowa", value=cena_salonowa, inline=True)
    embed_response.add_field(name="💵 Cena w Komisie", value=cena_komis, inline=True)
    embed_response.add_field(name="⚙️ Dodatki Pojazdu", value=dodatki, inline=False)

    if zdjecia_link != "Brak":
        embed_response.set_image(url=zdjecia_link)

    embed_response.set_footer(text=f"ID Ogłoszenia: {ogloszenie_id} • {ogloszenie_data['Data dodania']}")

    role_mention_string = f"<@&{ROLA_DO_OZNACZENIA_ID}>" if ROLA_DO_OZNACZENIA_ID else ""
    try:
        await interaction.response.send_message(
            content=f"{role_mention_string} Otrzymałeś Powiadomienie o Nowym Ogłoszeniu.",
            embed=embed_response,
            ephemeral=False
        )
        response_message = await interaction.original_response()
        ogloszenia_db["ogloszenia"][ogloszenie_id]['powiadomienie_message_id'] = response_message.id
        ogloszenia_db["ogloszenia"][ogloszenie_id]['powiadomienie_channel_id'] = interaction.channel.id
        save_data(ogloszenia_db)
        print(f"Powiadomienie o ogłoszeniu '{nazwa_pojazdu}' wysłane na kanał interakcji (ID wiadomości: {response_message.id}).")
    except discord.Forbidden:
        print(f"Błąd uprawnień: Bot nie ma uprawnień do wysyłania wiadomości na kanale {interaction.channel.name}.")
    except Exception as e:
        print(f"Wystąpił błąd podczas wysyłania powiadomienia na kanał interakcji: {e}")

    baza_kanal = bot.get_channel(BAZA_POJAZDOW_CHANNEL_ID)
    if baza_kanal:
        embed_baza = discord.Embed(
            title=f"{nazwa_pojazdu} - {cena_komis}",
            description="Pojazd został dodany do oferty komisu!",
            color=discord.Color.blue()
        )
        embed_baza.add_field(name="🙋‍♂️ Sprzedający", value=sprzedajacy_imie, inline=False)
        embed_baza.add_field(name="🏢 Cena Salonowa", value=cena_salonowa, inline=True)
        embed_baza.add_field(name="💵 Cena w Komisie", value=cena_komis, inline=True)
        if mozliwa_obnizka != "Brak":
            embed_baza.add_field(name="⬇️ Możliwa Obniżka", value=mozliwa_obnizka, inline=False)
        embed_baza.add_field(name="⚙️ Dodatki Pojazdu", value=dodatki, inline=False)

        if zdjecia_link != "Brak":
            embed_baza.set_image(url=zdjecia_link)

        embed_baza.set_footer(text=f"ID Ogłoszenia: {ogloszenie_id} • {ogloszenie_data['Data dodania']}")

        try:
            view = OgloszenieView(ogloszenie_id)
            baza_wiadomosc = await baza_kanal.send(embed=embed_baza, view=view)
            ogloszenia_db["ogloszenia"][ogloszenie_id]['baza_message_id'] = baza_wiadomosc.id
            save_data(ogloszenia_db)
            print(f"Ogłoszenie dla '{nazwa_pojazdu}' wysłane na kanał bazowy (ID wiadomości: {baza_wiadomosc.id}).")
        except discord.Forbidden:
            print(f"Błąd uprawnień: Bot nie ma uprawnień do wysyłania wiadomości na kanale #{baza_kanal.name} (ID: {BAZA_POJAZDOW_CHANNEL_ID}).")
        except Exception as e:
            print(f"Nieznany błąd podczas wysyłania ogłoszenia na kanał bazowy: {e}")
    else:
        print(f"Nie znaleziono kanału bazy pojazdów o ID: {BAZA_POJAZDOW_CHANNEL_ID}. Nie można wysłać ogłoszenia do bazy.")

@bot.tree.command(name="licytacja", description="Tworzenie Nowej Licytacji .")
@app_commands.describe(
    nazwa_pojazdu="Pełna nazwa pojazdu (np. Dinka Jester)",
    cena_startowa="Cena początkowa licytacji (np. 50000 )",
    przebicia="Kwota o jaka przebijamy np. 1 Dolar lub 1.000.)",
    data_zakonczenia="Kiedy kończy się licytacja (np. 10.07 lub 10.07.2025)",
    godzina="O której godzinie kończy się licytacja (np. 20:00, 23:59)",
    dodatki="Lista dodatków/wyposażenia (np. Silnik, Felgi itp.)",
    zdjecia_link="Link do zdjęcia - MOŻNA WRZUCAĆ FOTKI NA KANAŁ ZDJĘCIA POJAZDÓW!"
)
async def licytacja(
    interaction: discord.Interaction,
    nazwa_pojazdu: str,
    cena_startowa: str,
    przebicia: str,
    data_zakonczenia: str,
    godzina: str,
    dodatki: str,
    zdjecia_link: str = "Brak"
):
    global ogloszenia_db

    if zdjecia_link != "Brak" and not (zdjecia_link.startswith("http://") or zdjecia_link.startswith("https://")):
        await interaction.response.send_message(
            "Podany link do zdjęcia jest nieprawidłowy. Upewnij się, że zaczyna się od `http://` lub `https://`.",
            ephemeral=True
        )
        return

    licytacja_id = str(uuid.uuid4())

    licytacja_data = {
        "ID": licytacja_id,
        "Nazwa Pojazdu": nazwa_pojazdu,
        "Cena Startowa Licytacji": cena_startowa,
        "Data Zakończenia Licytacji": data_zakonczenia,
        "Godzina Zakończenia Licytacji": godzina,
        "Dodatki Pojazdu": dodatki,
        "Zdjęcia Pojazdu": zdjecia_link,
        "Dodano przez": interaction.user.display_name,
        "Dodano przez ID": interaction.user.id,
        "Data dodania": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "licytacja_message_id": None,
        "licytacja_channel_id": None
    }
    ogloszenia_db["licytacje"][licytacja_id] = licytacja_data

    embed = discord.Embed(
        title=f"🔥 LICYTACJA - {nazwa_pojazdu} 🔥",
        description="",
        color=discord.Color.gold()
    )
    embed.add_field(name="💰 Cena Startowa", value=cena_startowa, inline=False)
    embed.add_field(name="🧮 Przebijamy o", value=przebicia, inline=True)
    embed.add_field(name="⏳ Koniec", value=data_zakonczenia, inline=False)
    embed.add_field(name="⏲ Godzinia", value=godzina, inline=True)
    embed.add_field(name="⚙️ Dodatki Pojazdu", value=dodatki, inline=False)

    if zdjecia_link != "Brak":
        embed.set_image(url=zdjecia_link)

    embed.set_footer(text=f"Zwycięzca Licytacji ma 24h na odbiór pojazdu. Czas Liczymy od Oficjalnego Ogłoszenia Zwycięzcy przez Pracownika!")

    role_mention_string = f"<@&{ROLA_DO_OZNACZENIA_ID}>" if ROLA_DO_OZNACZENIA_ID else ""

    try:
        await interaction.response.send_message(
            content=f"{role_mention_string} 📲Otrzymałeś Nowe Powiadomienie O Licytacji📲",
            embed=embed,
            ephemeral=False
        )
        response_message = await interaction.original_response()
        ogloszenia_db["licytacje"][licytacja_id]['licytacja_message_id'] = response_message.id
        ogloszenia_db["licytacje"][licytacja_id]['licytacja_channel_id'] = interaction.channel.id
        save_data(ogloszenia_db)
        print(f"Ogłoszenie o licytacji dla '{nazwa_pojazdu}' wysłane na kanał interakcji (ID wiadomości: {response_message.id}).")

    except discord.Forbidden:
        await interaction.followup.send(
            f"Błąd uprawnień: Nie mam uprawnień do wysyłania wiadomości na tym kanale.",
            ephemeral=True
        )
        print(f"Błąd uprawnień: Bot nie ma uprawnień do wysyłania wiadomości na kanale {interaction.channel.name} (ID: {interaction.channel.id}).")
    except Exception as e:
        await interaction.followup.send(
            f"Wystąpił nieznany błąd podczas wysyłania ogłoszenia o licytacji: {e}",
            ephemeral=True
        )
        print(f"Nieznany błąd podczas wysyłania ogłoszenia o licytacji: {e}")

# ==================== KOMENDA: /informacja ====================

@bot.tree.command(name="informacja", description="Wysyła wiadomość podaną przez użytkownika.")
@app_commands.describe(
    tresc_wiadomosci="Treść wiadomości, którą bot ma wysłać."
)
async def informacja(
    interaction: discord.Interaction,
    tresc_wiadomosci: str
):
    """
    Wysyła wiadomość tekstową podaną przez użytkownika na kanał,
    na którym komenda została wywołana.
    """
    try:
        await interaction.response.send_message(tresc_wiadomosci)
        print(f"Komenda /informacja użyta. Wysyłam: '{tresc_wiadomosci}'")
    except discord.Forbidden:
        await interaction.response.send_message(
            "Błąd: Nie mam uprawnień do wysłania wiadomości na tym kanale.",
            ephemeral=True
        )
        print(f"Błąd uprawnień: Bot nie ma uprawnień do wysyłania wiadomości na kanale {interaction.channel.name} (ID: {interaction.channel.id}).")
    except Exception as e:
        await interaction.response.send_message(
            f"Wystąpił nieoczekiwany błąd: {e}",
            ephemeral=True
        )
        print(f"Wystąpił błąd podczas obsługi komendy /informacja: {e}")
        
# ==================== KOMENDA: /pracownik ====================
@bot.tree.command(name="pracownik", description="Wysyła wiadomość powitalną na kanale z oznaczeniem użytkownika i wysyła do niego PW.")
@app_commands.describe(
    uzytkownik="Użytkownik, którego chcesz oznaczyć i wysłać PW."
   )
   
async def pracownik(
    interaction: discord.Interaction,
    uzytkownik: discord.Member 
):
    """
    Wysyła wiadomość tekstową "Witaj w naszym zespole" na kanale, na którym komenda została wywołana,
    oznaczając wybranego użytkownika, oraz wysyła prywatną wiadomość do tego użytkownika.
    """
    # Ustalona wiadomość do wysłania
    predefined_message = "Witaj w gronie Pracowników **EVANS CARS**. Wszystkie Potrzebne materiały do wykonywania swojej pracy znajdziesz na kanale <#1199742339632091247>.\n Nasz Kanał DISCORD ma formę alpikacji mobilnej na Telefon dlatego proszę abys zmienił swój nick na naszym serwerze na forme\n ** IC | OOC**.\n Podczas Pracy korzystamy z krutkofalówek dostępnych na serwerze.\n Kanał IC na jakim działamy to **2831**."

    try:
        # Wysyłanie wiadomości na kanale z oznaczeniem użytkownika
        await interaction.response.send_message(f"{uzytkownik.mention} {predefined_message}")
        print(f"Komenda /pracownik użyta przez {interaction.user.display_name}. Wysyłam wiadomość na kanale do {uzytkownik.display_name}.")

        # Wysyłanie prywatnej wiadomości do użytkownika
        try:
            await uzytkownik.send(f"Otrzymałeś prywatną wiadomość od **{interaction.guild.name}**:\n\n**Wiadomość z kanału:** {predefined_message}\n\n*Ta wiadomość została wygenerowana automatycznie. Nie odpowiadaj na nią.*")
            print(f"Wysłano prywatną wiadomość do {uzytkownik.display_name}.")
        except discord.Forbidden:
            print(f"Błąd uprawnień: Nie można wysłać PW do {uzytkownik.display_name}. Użytkownik mógł zablokować wiadomości prywatne.")
            # Użycie followup.send, ponieważ response.send_message zostało już użyte
            await interaction.followup.send(
                f"Nie udało się wysłać prywatnej wiadomości do {uzytkownik.mention}. Użytkownik mógł zablokować wiadomości prywatne.",
                ephemeral=True
            )
        except Exception as e:
            print(f"Wystąpił nieoczekiwany błąd podczas wysyłania PW do {uzytkownik.display_name}: {e}")
            # Użycie followup.send
            await interaction.followup.send(
                f"Wystąpił błąd podczas wysyłania prywatnej wiadomości do {uzytkownik.mention}. Błąd: {e}",
                ephemeral=True
            )

    except discord.Forbidden:
        await interaction.response.send_message(
            "Błąd: Nie mam uprawnień do wysłania wiadomości na tym kanale.",
            ephemeral=True
        )
        print(f"Błąd uprawnień: Bot nie ma uprawnień do wysyłania wiadomości na kanale {interaction.channel.name} (ID: {interaction.channel.id}).")
    except Exception as e:
        await interaction.response.send_message(
            f"Wystąpił nieoczekiwany błąd podczas obsługi komendy /pracownik: {e}",
            ephemeral=True
        )
        print(f"Wystąpił błąd podczas obsługi komendy /pracownik: {e}")


## Komenda: /koniec
@bot.tree.command(name="koniec", description="Ogłoś zwycięzcę licytacji i kwotę.")
@app_commands.describe(
    zwyciezca="Użytkownik, który wygrał licytację.",
    kwota="Kwota, za którą licytacja została wygrana (np. 150000 PLN)."
)
async def koniec_licytacji(
    interaction: discord.Interaction,
    zwyciezca: discord.Member,
    kwota: str
):
    """
    Ogłasza koniec licytacji, podając zwycięzcę licytacji, kwotę
    oraz informację o czasie na odbiór pojazdu, a także wysyła PW do zwycięzcy.
    """
    try:
        public_embed = discord.Embed(
            title="🎉 KONIEC LICYTACJI 🎉",
            description="Licytacja została zakończona!",
            color=discord.Color.green()
        )
        public_embed.add_field(name="🏆 Zwycięzca Licytacji 🏆", value=zwyciezca.mention, inline=False)
        public_embed.add_field(name="💰 Kwota", value=kwota, inline=False)
        public_embed.set_footer(text="ZWYCIĘZCA MA 24h NA ODBIÓR POJAZDU.")

        await interaction.response.send_message(embed=public_embed)
        print(f"Komenda /koniec użyta przez {interaction.user.display_name}. Zwycięzca: {zwyciezca.display_name}, Kwota: {kwota}")

        try:
            dm_embed = discord.Embed(
                title="🏆Gratulacje! Wygrałeś Licytację! 🏆",
                description=f"Wygrałeś licytację pojazdu za kwotę: **{kwota}**💵.",
                color=discord.Color.gold()
            )
            dm_embed.add_field(name="Ważne informacje:", value="Masz **24 godziny** na odbiór pojazdu od momentu oficjalnego ogłoszenia zwycięzcy przez pracownika. Pojazd może wydać **każdy** pracownik naszego komisu będący w Lokalu. ***Wiadomość Wygenerowana Automatycznie, Nie odpisuj na nią.***", inline=False)
            dm_embed.set_footer(text="Dziękujemy Ekipa EVANS CARS DEALERSHIP!")

            await zwyciezca.send(embed=dm_embed)
            print(f"Wysłano prywatną wiadomość do zwycięzcy licytacji ({zwyciezca.display_name}).")
        except discord.Forbidden:
            print(f"Błąd uprawnień: Nie można wysłać PW do {zwyciezca.display_name}. Użytkownik mógł zablokować wiadomości prywatne.")
            # Użycie followup.send
            await interaction.followup.send(
                f"Nie udało się wysłać prywatnej wiadomości do {zwyciezca.mention}. Użytkownik mógł zablokować wiadomości prywatne. Pamiętaj, aby poinformować zwycięzcę ręcznie!",
                ephemeral=True
            )
        except Exception as e:
            print(f"Wystąpił nieoczekiwany błąd podczas wysyłania PW do zwycięzcy: {e}")
            # Użycie followup.send
            await interaction.followup.send(
                f"Wystąpił błąd podczas wysyłania prywatnej wiadomości do zwycięzcy. Pamiętaj, aby poinformować go ręcznie! Błąd: {e}",
                ephemeral=True
            )

    except discord.Forbidden:
        await interaction.response.send_message(
            "Błąd: Nie mam uprawnień do wysłania wiadomości na tym kanale.",
            ephemeral=True
        )
        print(f"Błąd uprawnień: Bot nie ma uprawnień do wysyłania wiadomości na kanale {interaction.channel.name} (ID: {interaction.channel.id}).")
    except Exception as e:
        await interaction.response.send_message(
            f"Wystąpił nieoczekiwany błąd podczas ogłaszania końca licytacji: {e}",
            ephemeral=True
        )
        print(f"Wystąpił błąd podczas obsługi komendy /koniec: {e}")

@bot.tree.command(name="czas", description="Wysyła powiadomienie o pozostałym czasie do końca licytacji.")
@app_commands.describe(
    godziny="Liczba godzin pozostałych do końca licytacji.",
    minuty="Liczba minut pozostałych do końca licytacji.",
    rola_do_oznaczenia="Opcjonalnie: Rola, która ma zostać oznaczona w powiadomieniu."
)
async def czas(
    interaction: discord.Interaction,
    godziny: int,
    minuty: int,
    rola_do_oznaczenia: discord.Role = None
):
    if godziny < 0 or minuty < 0:
        await interaction.response.send_message(
            "Godziny i minuty muszą być liczbami nieujemnymi.",
            ephemeral=True
        )
        return

    czas_str = ""
    if godziny == 1:
        czas_str += f"**{godziny}** Godzina"
    elif godziny > 1:
        czas_str += f"**{godziny}** Godzin"

    if godziny > 0 and minuty > 0:
        czas_str += " i "

    if minuty == 1:
        czas_str += f"**{minuty}** Minuta"
    elif minuty > 1:
        czas_str += f"**{minuty}** Minut"

    if not czas_str and (godziny == 0 and minuty == 0):
        czas_str = "mniej niż minutę"
    elif not czas_str:
        if godziny > 0:
            czas_str = f"**{godziny}** Godzin"
        elif minuty > 0:
            czas_str = f"**{minuty}** Minut"


    embed = discord.Embed(
        title="🔔 Powiadomienie 🔔",
        color=discord.Color.red()
    )

    if rola_do_oznaczenia:
        embed.description = f"**POWIADOMIENIE**\n{rola_do_oznaczenia.mention} Do Końca Licytacji Pozostało: {czas_str}."
    else:
        embed.description = f"**POWIADOMIENIE**\nDo Końca Licytacji Pozostało: {czas_str}."

    try:
        await interaction.response.send_message(embed=embed)
        print(f"Komenda /czas użyta przez {interaction.user.display_name}. Wysyłam powiadomienie o czasie: {godziny}h {minuty}m.")
    except discord.Forbidden:
        await interaction.response.send_message(
            "Błąd: Nie mam uprawnień do wysłania wiadomości na tym kanale lub do oznaczenia roli. Sprawdź uprawnienia bota.",
            ephemeral=True
        )
        print(f"Błąd uprawnień: Bot nie ma uprawnień do wysyłania wiadomości na kanale {interaction.channel.name} (ID: {interaction.channel.id}).")
    except Exception as e:
        await interaction.response.send_message(
            f"Wystąpił nieoczekiwany błąd: {e}",
            ephemeral=True
        )
        print(f"Wystąpił błąd podczas obsługi komendy /czas: {e}")
        
#-_____________________________________________________________________URLOP_______________________________________________________________________________________________
        
@bot.tree.command(name="urlop", description="Zgłoś urlop i powiadom Członków Zarządu.")
@app_commands.describe(
    rozpoczecie="Data rozpoczęcia urlopu (np. DD.MM.RRRR)",
    zakonczenie="Data zakończenia urlopu (np. DD.MM.RRRR)"
)
async def urlop(
    interaction: discord.Interaction,
    rozpoczecie: str,
    zakonczenie: str
):
    """
    Wysyła na kanale informację o urlopie użytkownika i wysyła PW do roli 'Członek Zarządu'.
    """
    user_display_name = interaction.user.display_name

    embed_channel = discord.Embed(
        title="🔔 Zgłoszenie Urlopu 🔔",
        description=f"Użytkownik {interaction.user.mention} zgłasza urlop.",
        color=discord.Color.dark_orange()
    )
    embed_channel.add_field(name="📅 Rozpoczęcie Urlopu", value=rozpoczecie, inline=True)
    embed_channel.add_field(name="🗓️ Zakończenie Urlopu", value=zakonczenie, inline=True)
    embed_channel.set_footer(text=f"Zgłoszono przez: {user_display_name} | ID: {interaction.user.id}")

    # Wysyłanie wiadomości na kanale, gdzie użyto komendy
    try:
        await interaction.response.send_message(embed=embed_channel)
        print(f"Komenda /urlop użyta przez {user_display_name}. Wysyłam informację o urlopie na kanale.")
    except discord.Forbidden:
        await interaction.response.send_message(
            "Błąd: Nie mam uprawnień do wysłania wiadomości na tym kanale.",
            ephemeral=True
        )
        print(f"Błąd uprawnień: Bot nie ma uprawnień do wysyłania wiadomości na kanale {interaction.channel.name}.")
        return # Zakończ funkcję, jeśli nie można wysłać na kanał

    # Wysłanie PW do członków roli "Członek Zarządu"
    if ROLA_CZLONEK_ZARZADU_ID:
        rola_zarzadu = interaction.guild.get_role(ROLA_CZLONEK_ZARZADU_ID)
        if rola_zarzadu:
            embed_dm = discord.Embed(
                title="🚨 POWIADOMIENIE O URLOPIE (Zarząd) 🚨",
                description=f"Nowe zgłoszenie urlopu od pracownika: **{user_display_name}**.",
                color=discord.Color.red()
            )
            embed_dm.add_field(name="Użytkownik", value=f"{interaction.user.mention} (ID: {interaction.user.id})", inline=False)
            embed_dm.add_field(name="Rozpoczęcie Urlopu", value=rozpoczecie, inline=True)
            embed_dm.add_field(name="Zakończenie Urlopu", value=zakonczenie, inline=True)
            embed_dm.set_footer(text=f"Zgłoszenie z serwera: {interaction.guild.name}")

            members_with_role = [member for member in rola_zarzadu.members if not member.bot] # Wyślij tylko do prawdziwych użytkowników

            if not members_with_role:
                print(f"Brak członków z rolą '{rola_zarzadu.name}' do wysłania PW o urlopie.")
                await interaction.followup.send(
                    f"Wiadomość o urlopie została wysłana na kanał, ale nie znaleziono żadnych członków z rolą '{rola_zarzadu.name}' do wysłania PW.",
                    ephemeral=True
                )
                return

            for member in members_with_role:
                try:
                    await member.send(embed=embed_dm)
                    print(f"Wysłano PW o urlopie do {member.display_name} (Członek Zarządu).")
                except discord.Forbidden:
                    print(f"Błąd uprawnień: Nie mogę wysłać PW do {member.display_name}. Prawdopodobnie zablokował wiadomości prywatne.")
                except Exception as e:
                    print(f"Wystąpił błąd podczas wysyłania PW o urlopie do {member.display_name}: {e}")
            
            # Potwierdzenie wysłania PW, jeśli udało się wysłać do kogokolwiek
            if any(m for m in members_with_role if not m.bot): # Sprawdź, czy choć jedna PW została podjęta
                # Używamy followup.send, ponieważ initial response już wysłana
                await interaction.followup.send(
                    f"Wiadomość o urlopie została wysłana na kanał oraz do Członków Zarządu.",
                    ephemeral=True
                )
            else:
                 await interaction.followup.send(
                    f"Wiadomość o urlopie została wysłana na kanał, ale żaden Członek Zarządu nie otrzymał PW (np. zablokowane wiadomości prywatne).",
                    ephemeral=True
                )

        else:
            print(f"Błąd: Rola 'Członek Zarządu' o ID {ROLA_CZLONEK_ZARZADU_ID} nie została znaleziona na serwerze. Nie można wysłać PW.")
            # Używamy followup.send, ponieważ initial response już wysłana
            await interaction.followup.send(
                f"Wiadomość o urlopie została wysłana na kanał, ale nie udało się powiadomić Członków Zarządu (rola nie znaleziona).",
                ephemeral=True
            )
    else:
        print("Brak skonfigurowanego ID dla roli 'Członek Zarządu'. Nie wysyłam PW.")
        await interaction.followup.send(
            "Wiadomość o urlopie została wysłana na kanał, ale rola 'Członek Zarządu' nie jest skonfigurowana, więc PW nie zostały wysłane.",
            ephemeral=True
        )


#_____________________________________SYSTEM ZGŁOSZEN___________________________________________________________________________________________________________
# --- KLASA MODALU (FORMULARZA) OGÓLNEGO ZGŁOSZENIA ---
class ZgloszenieModal(ui.Modal, title="Formularz Zgłoszenia"):
    # Zmieniono: Dodana metoda __init__ aby umożliwić dziedziczenie i przekazywanie title
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.temat = ui.TextInput(
            label="Temat Zgłoszenia",
            placeholder="Np. Problem z logowaniem, Pytanie o zasady, Zgłoszenie gracza",
            max_length=100,
            required=True,
            style=discord.TextStyle.short
        )
        self.opis = ui.TextInput(
            label="Opis Problemu/Pytania",
            placeholder="Opisz swój problem/pytanie szczegółowo...",
            max_length=1000,
            required=True,
            style=discord.TextStyle.long
        )
        self.add_item(self.temat)
        self.add_item(self.opis)

    async def on_submit(self, interaction: discord.Interaction):
        await self._handle_submission(interaction, "Ogólne Zgłoszenie")

    async def _handle_submission(self, interaction: discord.Interaction, zgłoszenie_type: str, fields: dict = None):
        kanal_zgloszen = bot.get_channel(KANAL_ZGLOSZEN_ID)
        kategoria_zgloszen = bot.get_channel(KATEGORIA_ZGLOSZEN_ID)
        # Poprawka: Sprawdź, czy guild jest dostępny, zanim spróbujesz pobrać rolę
        rola_wsparcia = interaction.guild.get_role(ROLA_WSPARCIA_ID) if interaction.guild else None

        if not kanal_zgloszen or not kategoria_zgloszen or not rola_wsparcia:
            await interaction.response.send_message(
                "Błąd konfiguracji bota. Skontaktuj się z administracją. Upewnij się, że wszystkie ID kanałów/kategorii/ról są poprawne i bot ma do nich dostęp.",
                ephemeral=True
            )
            return

        channel_name = f"{zgłoszenie_type.lower().replace(' ', '-')}-{interaction.user.name.lower().replace(' ', '-')}-{discord.utils.snowflake_time(interaction.id).strftime('%H%M%S')}"
        if len(channel_name) > 100:
            channel_name = channel_name[:95] + str(interaction.id)[-5:]

        try:
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                rola_wsparcia: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }

            new_channel = await interaction.guild.create_text_channel(
                name=channel_name,
                category=kategoria_zgloszen,
                overwrites=overwrites,
                reason=f"Nowe {zgłoszenie_type} od {interaction.user.display_name}"
            )

            await interaction.response.send_message(
                f"Twoje {zgłoszenie_type} zostało utworzone! Możesz je znaleźć tutaj: {new_channel.mention}",
                ephemeral=True
            )

            embed = discord.Embed(
                title=f"Nowe {zgłoszenie_type} od {interaction.user.display_name}",
                color=discord.Color.blue()
            )

            if fields:
                for name, value in fields.items():
                    embed.add_field(name=name, value=value, inline=False)
            else:
                # To jest dla ogólnego zgłoszenia (ZgloszenieModal)
                embed.add_field(name="Temat", value=self.temat.value, inline=False)
                embed.add_field(name="Opis", value=self.opis.value, inline=False)

            embed.add_field(name="Status", value="Otwarte", inline=True)
            embed.set_footer(text=f"ID Kanału: {new_channel.id}")

            await new_channel.send(
                content=f"{interaction.user.mention} {rola_wsparcia.mention}",
                embed=embed
            )
            print(f"Utworzono {zgłoszenie_type} dla {interaction.user.display_name} w kanale {new_channel.name}")

        except discord.Forbidden:
            await interaction.response.send_message(
                "Błąd: Bot nie ma uprawnień do tworzenia kanałów lub zarządzania uprawnieniami. Skontaktuj się z administracją.",
                ephemeral=True
            )
            print(f"Błąd uprawnień: Bot nie ma uprawnień do tworzenia kanałów lub zarządzania uprawnieniami na serwerze {interaction.guild.name}.")
        except Exception as e:
            await interaction.response.send_message(
                f"Wystąpił nieoczekiwany błąd podczas tworzenia {zgłoszenie_type}: {e}",
                ephemeral=True
            )
            print(f"Błąd podczas tworzenia {zgłoszenie_type}: {e}")

# --- KLASY MODALI DLA NOWYCH PRZYCISKÓW ---

class SprzedazWozuModal(ZgloszenieModal, title="Formularz Sprzedaży Pojazdu"):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.clear_items()

        self.nickic = ui.TextInput(
            label="Nick IC Twojej Postaci",
            placeholder="Wpisz Nick Postaci do której należy Pojazd.",
            max_length=100,
            required=True,
            style=discord.TextStyle.short
        )
        self.nazwa_pojazdu = ui.TextInput(
            label="Nazwa/Model Pojazdu",
            placeholder="Model Pojazdu",
            max_length=100,
            required=True,
            style=discord.TextStyle.short
        )
        self.cena = ui.TextInput(
            label="Oczekiwana Cena",
            placeholder="Np. 15000$, do negocjacji",
            max_length=50,
            required=True,
            style=discord.TextStyle.short
        )
        self.kontakt_info = ui.TextInput(
            label="Kontakt",
            placeholder="Numer Telefonu IC.",
            max_length=500,
            required=False,
            style=discord.TextStyle.long
        )
        self.add_item(self.nickic)
        self.add_item(self.nazwa_pojazdu)
        self.add_item(self.cena)
        self.add_item(self.kontakt_info)

    async def on_submit(self, interaction: discord.Interaction):
        fields = {
            "Rodzaj Zgłoszenia": "Sprzedaż Pojazdu",
            "Dane Klienta": self.nickic.value,
            "Nazwa/Model Pojazdu": self.nazwa_pojazdu.value,
            "Oczekiwana Cena": self.cena.value,
            "Kontakt": self.kontakt_info.value if self.kontakt_info.value else "Brak informacji"
        }
        await self._handle_submission(interaction, "Sprzedaż Pojazdu", fields)

class WyslijPodanieModal(ZgloszenieModal, title="Wyślij Podania"):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.clear_items()

        self.nickic = ui.TextInput(
            label="Nick IC",
            placeholder="Wpisujemy Nick IC naszej postaci.",
            max_length=100,
            required=True,
            style=discord.TextStyle.short
        )
        self.doswiadczenie = ui.TextInput(
            label="Twoje doświadczenie", # Zmieniono label na bardziej precyzyjny
            placeholder="Opisz swoje doświadczenie, umiejętności.",
            max_length=1000,
            required=True,
            style=discord.TextStyle.long
        )
        self.linkforum = ui.TextInput(
            label="LINK DO KONTA GLOBALNEGO",
            placeholder="Musimy Zweryfikować Liste Twoich Kar.",
            max_length=1000,
            required=True,
            style=discord.TextStyle.long
        )
        self.add_item(self.nickic)
        self.add_item(self.doswiadczenie)
        self.add_item(self.linkforum)

    async def on_submit(self, interaction: discord.Interaction):
        fields = {
            "Nick IC" : self.nickic.value,
            "Doświadczenie": self.doswiadczenie.value,
            "||OOC LINK DO FORUM||": self.linkforum.value,
        }
        await self._handle_submission(interaction, "Podanie O Prace", fields)

class UmowWizyteModal(ZgloszenieModal, title="Formularz Umówienia Wizyty"):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.clear_items()

        self.typ_wizyty = ui.TextInput(
            label="Typ Wizyty",
            placeholder="Np. Konsultacja, Serwis, Spotkanie",
            max_length=100,
            required=True,
            style=discord.TextStyle.short
        )
        self.preferowany_termin = ui.TextInput(
            label="Preferowany Termin/Data (opcjonalnie)",
            placeholder="Np. Dziś wieczorem, jutro rano, konkretna data.",
            max_length=100,
            required=False,
            style=discord.TextStyle.short
        )
        self.dodatkowe_info = ui.TextInput(
            label="Dodatkowe Informacje",
            placeholder="Wszelkie dodatkowe uwagi dotyczące wizyty.",
            max_length=500,
            required=False,
            style=discord.TextStyle.long
        )
        self.add_item(self.typ_wizyty)
        self.add_item(self.preferowany_termin)
        self.add_item(self.dodatkowe_info)

    async def on_submit(self, interaction: discord.Interaction):
        fields = {
            "Rodzaj Zgłoszenia": "Umówienie Wizyty",
            "Typ Wizyty": self.typ_wizyty.value,
            "Preferowany Termin": self.preferowany_termin.value if self.preferowany_termin.value else "Brak informacji",
            "Dodatkowe Informacje": self.dodatkowe_info.value if self.dodatkowe_info.value else "Brak informacji"
        }
        await self._handle_submission(interaction, "Umówienie Wizyty", fields)

# --- KLASA WIDOKU (PRZYCISKI) PANELU ZGŁOSZEŃ ---
class PanelZgloszenView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="🚘 SPRZEDAJ POJAZD", style=discord.ButtonStyle.blurple, custom_id="create_ticket_vehicle_sale")
    async def create_ticket_vehicle_sale(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(SprzedazWozuModal())

    @ui.button(label="📝 WYSLIJ PODANIE", style=discord.ButtonStyle.blurple, custom_id="create_ticket_application")
    async def create_ticket_application(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(WyslijPodanieModal())

    @ui.button(label="🕺 UMÓW WIZYTE", style=discord.ButtonStyle.blurple, custom_id="create_ticket_appointment")
    async def create_ticket_appointment(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(UmowWizyteModal())

    @ui.button(label="✏️ INNA SPRAWA", style=discord.ButtonStyle.green, custom_id="create_ticket_general")
    async def create_ticket_general(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(ZgloszenieModal())

# --- Komenda slash do wysłania panelu zgłoszeń ---
@bot.tree.command(name="panel_zgloszen", description="Wysyła panel zgłoszeń z różnymi opcjami.")
@app_commands.default_permissions(manage_channels=True)
async def panel_zgloszen(interaction: discord.Interaction):
    embed = discord.Embed(
        title="System Zgłoszeń 🚘 EVANS CARS 🚘",
        description="Wybierz opcję, która najlepiej pasuje do Twojego zapytania:",
        color=discord.Color.blue()
    )
    embed.add_field(name="🚘SPRZEDAJ POJAZD", value="Jeśli chcesz sprzedać pojazd.", inline=True)
    embed.add_field(name="📝WYSLIJ PODANIE", value="Aby złożyć podanie o przyjęcie do zespołu.", inline=True)
    embed.add_field(name="🕺UMÓW WIZYTE", value="Aby zaplanować spotkanie lub konsultację.", inline=True)
    embed.add_field(name="️✏️INNA SPRAWAE", value="Dla ogólnych pytań i problemów.", inline=True)
    embed.set_footer(text="Zgłoszenia będą tworzone w dedykowanych kanałach dostępnych jedynie przez Pracowników Komisu.")

    await interaction.response.send_message(embed=embed, view=PanelZgloszenView())
    print(f"Wysłano panel zgłoszeń przez {interaction.user.display_name}.")

# ==================== URUCHOMIENIE BOTA ====================
if __name__ == '__main__':
    bot.run(TOKEN)