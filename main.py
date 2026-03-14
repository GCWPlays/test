import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import random
import time
import os

TOKEN = os.getenv("TOKEN")

DATA_FILE = "data.json"

invite_cache = {}
INVITE_REWARD = 100000

PROMO_CODES = {
    "10MEM": 100000,
    "GAMBLE000": 250000,
    "PROGAMBLING": 2500000
}

MINE_CHEAT_ENABLED = True
MINE_CHEAT_USER_ID = 1144253701989609483  # replace with the user ID

ADMIN_IDS = [
    1144253701989609483,
    1460338239599542549
]

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


# ---------------- DATA ------------


def load_data():

    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump({}, f)

    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_data(data):

    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


def get_user(data, user_id):

    user_id = str(user_id)

    if user_id not in data:
        data[user_id] = {}

    user = data[user_id]

    # ensure all fields exist (fixes old data.json users)
    user.setdefault("wallet", 0)
    user.setdefault("last_daily", 0)
    user.setdefault("last_work", 0)
    user.setdefault("last_mine", 0)
    user.setdefault("affiliate", None)
    user.setdefault("affiliate_earnings", 0)
    user.setdefault("coins_donated", 0)

    return user

def add_balance(user_id, amount):

    data = load_data()            # load data.json
    user = get_user(data, user_id) # get that user's data

    user["wallet"] += amount      # add coins to wallet

    save_data(data)               # save updated data.json


# ---------------- COIN FORMATTER ---------------- #

def format_coins(amount):

    amount = float(amount)

    if amount >= 1_000_000_000_000:
        return f"{amount/1_000_000_000_000:.1f}T".rstrip("0").rstrip(".")
    elif amount >= 1_000_000_000:
        return f"{amount/1_000_000_000:.1f}B".rstrip("0").rstrip(".")
    elif amount >= 1_000_000:
        return f"{amount/1_000_000:.1f}M".rstrip("0").rstrip(".")
    elif amount >= 1_000:
        return f"{amount/1_000:.1f}K".rstrip("0").rstrip(".")
    else:
        return str(int(amount))


# ---------------- READY ---------------- #

@bot.event
async def on_ready():

    data = load_data()

    if "invites" not in data:
        data["invites"] = {}

    for guild in bot.guilds:

        try:
            invites = await guild.invites()
        except:
            continue

        for invite in invites:

            code = invite.code
            uses = invite.uses
            inviter = invite.inviter

            if code not in data["invites"]:
                data["invites"][code] = uses
                continue

            old_uses = data["invites"][code]

            if uses > old_uses and inviter:

                difference = uses - old_uses

                inviter_data = get_user(data, inviter.id)
                inviter_data["affiliate_earnings"] += difference * INVITE_REWARD

                data["invites"][code] = uses

    save_data(data)

    await bot.tree.sync()
    print("Bot Ready")


@bot.event
async def on_member_join(member):

    data = load_data()

    if "invites" not in data:
        data["invites"] = {}

    try:
        invites = await member.guild.invites()
    except:
        return

    for invite in invites:

        code = invite.code
        uses = invite.uses
        inviter = invite.inviter

        old_uses = data["invites"].get(code, 0)

        if uses > old_uses and inviter:

            difference = uses - old_uses

            inviter_data = get_user(data, inviter.id)
            new_user = get_user(data, member.id)

            # set affiliate
            new_user["affiliate"] = inviter.id

            # reward inviter
            inviter_data["affiliate_earnings"] += difference * INVITE_REWARD

            data["invites"][code] = uses

    save_data(data)


# -----------------------------
# PARSE AMOUNT
# -----------------------------

import discord
from discord.ext import commands, tasks
import asyncio
import random

rains = {}

# -----------------------------
# PARSE AMOUNT
# -----------------------------

def parse_amount(a):
    a = a.lower()
    if a.endswith("k"): return int(float(a[:-1]) * 1_000)
    if a.endswith("m"): return int(float(a[:-1]) * 1_000_000)
    if a.endswith("b"): return int(float(a[:-1]) * 1_000_000_000)
    return int(a)

# -----------------------------
# BALANCE SYSTEM
# -----------------------------

balances = {}

def add_balance(user_id, amount):
    balances[user_id] = balances.get(user_id, 0) + amount

# -----------------------------
# RAIN BUTTON
# -----------------------------

class JoinButton(discord.ui.Button):
    def __init__(self, rain_id):
        super().__init__(label="🌧 Join Rain", style=discord.ButtonStyle.green)
        self.rain_id = rain_id

    async def callback(self, interaction: discord.Interaction):
        rain = rains.get(self.rain_id)

        if not rain:
            await interaction.response.send_message("Rain already ended.", ephemeral=True)
            return

        if interaction.user.id in rain["users"]:
            await interaction.response.send_message("You already joined.", ephemeral=True)
            return

        rain["users"].add(interaction.user.id)

        await interaction.response.send_message("You joined the rain!", ephemeral=True)

# -----------------------------
# VIEW
# -----------------------------

class RainView(discord.ui.View):
    def __init__(self, rain_id):
        super().__init__(timeout=None)
        self.add_item(JoinButton(rain_id))

# -----------------------------
# RAIN COMMAND
# -----------------------------

@bot.tree.command(name="rain")
async def rain(interaction: discord.Interaction, amount: str, seconds: int):

    total = parse_amount(amount)
    user_id = interaction.user.id

    data = load_data()
    user = get_user(data, user_id)

    # check balance
    if user["wallet"] < total:
        await interaction.response.send_message(
            f"You don't have enough coins.\nBalance: **{user['wallet']}**",
            ephemeral=True
        )
        return

    # remove coins from host wallet
    user["wallet"] -= total
    save_data(data)

    embed = discord.Embed(
        title="🌧 Coin Rain",
        description=(
            f"Host: {interaction.user.mention}\n"
            f"Total Pot: **{format_coins(total)} coins**\n"
            f"⏳ Ends in **{seconds} seconds**\n"
            f"Click the button to join!"
        ),
        color=0x00ffff
    )

    msg = await interaction.channel.send(embed=embed)
    rain_id = msg.id

    rains[rain_id] = {
        "total": total,
        "users": set(),
        "host": user_id
    }

    view = RainView(rain_id)
    await msg.edit(view=view)

    await interaction.response.send_message("Rain started!", ephemeral=True)

    await asyncio.sleep(seconds)

    rain = rains.pop(rain_id, None)

    if not rain or len(rain["users"]) == 0:
        # refund host
        add_balance(user_id, total)
        await interaction.channel.send("🌧 Rain ended. No one joined. Coins refunded.")
        return

    share = rain["total"] // len(rain["users"])

    data = load_data()

    for uid in rain["users"]:
        user = get_user(data, uid)
        user["wallet"] += share

    save_data(data)

    users = ", ".join(f"<@{u}>" for u in rain["users"])

    embed = discord.Embed(
        title="💰 Rain Ended",
        description=(
            f"Users Joined: **{len(rain['users'])}**\n"
            f"Each received: **{format_coins(share)} coins**"
        ),
        color=0x00ff00
    )

    await interaction.channel.send(embed=embed)
    await interaction.channel.send(users)

# -----------------------------
# AUTO RAIN
# -----------------------------

@tasks.loop(minutes=10)
async def auto_rain():

    for guild in bot.guilds:

        if guild.text_channels:

            channel = guild.text_channels[0]
            amount = random.randint(500, 2000)

            embed = discord.Embed(
                title="⚡ Auto Rain",
                description=f"Free **{amount} coins** rain!\nClick to join!",
                color=0x00ffff
            )

            msg = await channel.send(embed=embed)

            rain_id = msg.id

            rains[rain_id] = {
                "total": amount,
                "users": set()
            }

            view = RainView(rain_id)
            await msg.edit(view=view)

            await asyncio.sleep(30)

            rain = rains.pop(rain_id, None)

            if not rain or len(rain["users"]) == 0:
                await channel.send("Auto rain ended. No one joined.")
                continue

            share = rain["total"] // len(rain["users"])

            for user in rain["users"]:
                add_balance(user, share)

            embed = discord.Embed(
                title="⚡ Auto Rain Ended",
                description=f"{len(rain['users'])} users joined\nEach got **{share} coins**",
                color=0x00ff00
            )

            await channel.send(embed=embed)


# ---------------- MESSAGE REWARD ---------------- #

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    data = load_data()

    user = get_user(data, message.author.id)

    user["wallet"] += 5

    save_data(data)

    await bot.process_commands(message)

# Shop stock

@bot.tree.command(name="stock", description="View the current shop stock")
async def stock(interaction: discord.Interaction):

    embed = discord.Embed(
        title="🛒 Shop Stock",
        description="Here are the items currently available:",
        color=discord.Color.green()
    )

    # Items and prices
    embed.add_field(name="🚽🍝 Spaghetti Tualetti (SAB)", value="18M Coins", inline=False)
    embed.add_field(name="💰10 Robux", value="10M Coins", inline=False)
    embed.add_field(name="✨ VIP Room", value="50M Coins", inline=False)

    embed.set_footer(text="DM Owner to purchase!")

    await interaction.response.send_message(embed=embed)


# ---------------- BALANCE EMBED ---------------- #

def balance_embed(member, user):

    affiliate = "None"

    if user["affiliate"]:
        affiliate = f"<@{user['affiliate']}>"

    embed = discord.Embed(
        title=f"{member.name}'s Balance",
        color=discord.Color.gold()
    )

    embed.set_thumbnail(url=member.display_avatar.url)

    embed.add_field(
        name="⭐ | Balance",
        value=f"{format_coins(user['wallet'])} coins",
        inline=False
    )

    embed.add_field(
        name="💸 | Affiliate Earnings",
        value=f"{format_coins(user['affiliate_earnings'])} coins\n(100K coins per person u invite)",
        inline=False
    )

    embed.add_field(
        name="🔗 | Affiliated To",
        value=affiliate,
        inline=False
    )

    embed.add_field(
        name="📤 | Coins Donated",
        value=f"{format_coins(user['coins_donated'])} coins",
        inline=False
    )

    return embed


# ---------------- BALANCE ---------------- #

@bot.tree.command(name="balance")
async def balance(interaction: discord.Interaction, member: discord.Member = None):

    data = load_data()

    member = member or interaction.user

    user = get_user(data, member.id)

    embed = balance_embed(member, user)

    await interaction.response.send_message(embed=embed)


# ---------------- DAILY ---------------- #

@bot.tree.command(name="daily")
async def daily(interaction: discord.Interaction):

    data = load_data()

    user = get_user(data, interaction.user.id)

    now = time.time()

    if now - user["last_daily"] < 86400:

        embed = discord.Embed(
            description="You already claimed your daily reward.",
            color=discord.Color.red()
        )

        return await interaction.response.send_message(embed=embed)

    reward = random.randint(300, 600)

    user["wallet"] += reward
    user["last_daily"] = now

    save_data(data)

    embed = discord.Embed(
        description=f"You received {format_coins(reward)} coins.",
        color=discord.Color.green()
    )

    await interaction.response.send_message(embed=embed)


# ---------------- WORK ---------------- #

@bot.tree.command(name="work")
async def work(interaction: discord.Interaction):

    data = load_data()

    user = get_user(data, interaction.user.id)

    now = time.time()

    if now - user["last_work"] < 3600:

        embed = discord.Embed(
            description="You can work again in 1 hour.",
            color=discord.Color.red()
        )

        return await interaction.response.send_message(embed=embed)

    reward = random.randint(100, 300)

    jobs = [
        "programmed a bot",
        "fixed bugs",
        "moderated a server",
        "cleaned chat",
        "designed graphics"
    ]

    job = random.choice(jobs)

    user["wallet"] += reward
    user["last_work"] = now

    save_data(data)

    embed = discord.Embed(
        description=f"You {job} and earned {format_coins(reward)} coins.",
        color=discord.Color.green()
    )

    await interaction.response.send_message(embed=embed)

# Blackjack

class BlackjackView(discord.ui.View):

    def __init__(self, player, bet):
        super().__init__(timeout=120)

        self.player = player
        self.bet = bet

        self.deck = [2,3,4,5,6,7,8,9,10,10,10,10,11] * 4
        random.shuffle(self.deck)

        self.player_hand = [self.deck.pop(), self.deck.pop()]
        self.dealer_hand = [self.deck.pop(), self.deck.pop()]

    def value(self, hand):
        value = sum(hand)
        aces = hand.count(11)

        while value > 21 and aces:
            value -= 10
            aces -= 1

        return value

    def hand_text(self, hand):
        return " ".join(str(x) for x in hand)

    def make_embed(self, reveal=False):

        dealer = self.hand_text(self.dealer_hand) if reveal else f"{self.dealer_hand[0]} ?"

        return discord.Embed(
            title="Blackjack",
            description=
            f"Bet: {format_coins(self.bet)} coins\n\n"
            f"Your Hand: {self.hand_text(self.player_hand)} ({self.value(self.player_hand)})\n"
            f"Dealer Hand: {dealer}",
            color=discord.Color.green()
        )

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.green)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user.id != self.player:
            return await interaction.response.send_message(
                "You are not playing this game.", ephemeral=True
            )

        self.player_hand.append(self.deck.pop())

        if self.value(self.player_hand) > 21:

            embed = discord.Embed(
                title="Bust!",
                description=f"You lost {format_coins(self.bet)} coins.",
                color=discord.Color.red()
            )

            for child in self.children:
                child.disabled = True

            return await interaction.response.edit_message(embed=embed, view=self)

        await interaction.response.edit_message(
            embed=self.make_embed(),
            view=self
        )

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.blurple)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user.id != self.player:
            return await interaction.response.send_message(
                "You are not playing this game.", ephemeral=True
            )

        while self.value(self.dealer_hand) < 17:
            self.dealer_hand.append(self.deck.pop())

        player_val = self.value(self.player_hand)
        dealer_val = self.value(self.dealer_hand)

        data = load_data()
        user = get_user(data, interaction.user.id)

        if dealer_val > 21 or player_val > dealer_val:

            winnings = self.bet * 2
            user["wallet"] += winnings
            result = f"You won {format_coins(winnings)} coins!"

        elif player_val == dealer_val:

            user["wallet"] += self.bet
            result = "Push! Bet returned."

        else:

            result = f"You lost {format_coins(self.bet)} coins."

        save_data(data)

        embed = discord.Embed(
            title="Blackjack Result",
            description=
            f"Your Hand: {self.hand_text(self.player_hand)} ({player_val})\n"
            f"Dealer Hand: {self.hand_text(self.dealer_hand)} ({dealer_val})\n\n"
            f"{result}",
            color=discord.Color.blue()
        )

        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(embed=embed, view=self)

@bot.tree.command(name="blackjack")
async def blackjack(interaction: discord.Interaction, bet: int):

    data = load_data()
    user = get_user(data, interaction.user.id)

    if bet <= 0:
        return await interaction.response.send_message("Invalid bet.", ephemeral=True)

    if user["wallet"] < bet:
        return await interaction.response.send_message(
            "You don't have enough coins.", ephemeral=True
        )

    user["wallet"] -= bet
    save_data(data)

    view = BlackjackView(interaction.user.id, bet)

    await interaction.response.send_message(
        embed=view.make_embed(),
        view=view
    )


# ---------------- MINE ---------------- #

class MinesButton(discord.ui.Button):
    def __init__(self, x, y, game):
        super().__init__(style=discord.ButtonStyle.secondary, label="⬛")
        self.x = x
        self.y = y
        self.game = game

    async def callback(self, interaction: discord.Interaction):

        if interaction.user.id != self.game.player:
            return await interaction.response.send_message(
                "You are not playing this game.", ephemeral=True
            )

        if (self.x, self.y) in self.game.bombs:

            # show bomb on clicked tile
            self.label = "💣"
            self.style = discord.ButtonStyle.danger

            # disable all buttons
            for child in self.view.children:
                child.disabled = True

            embed = discord.Embed(
                title="Boom!",
                description=f"Bet: {self.game.bet} coins\n"
                            f"Multiplier: {self.game.multiplier:.2f}x\n"
                            f"Loss: {self.game.bet} coins\n"
                            f"Gems Found: {self.game.gems_found}",
                color=discord.Color.red()
            )

            await interaction.response.edit_message(embed=embed, view=self.view)

        self.style = discord.ButtonStyle.green
        self.label = "💎"
        self.disabled = True

        self.game.gems_found += 1
        self.game.multiplier += 0.15

        payout = int(self.game.bet * self.game.multiplier)

        embed = discord.Embed(
            title="MINES",
            description=f"Bet: {self.game.bet} coins\n"
                        f"Multiplier: {self.game.multiplier:.2f}x\n"
                        f"Current Payout: {format_coins(payout)} coins\n"
                        f"Gems Found: {self.game.gems_found}",
            color=discord.Color.blue()
        )

        await interaction.response.edit_message(embed=embed, view=self.view)


class CashoutButton(discord.ui.Button):
    def __init__(self, game):
        super().__init__(style=discord.ButtonStyle.primary, label="Cashout")
        self.game = game

    async def callback(self, interaction: discord.Interaction):

        if interaction.user.id != self.game.player:
            return

        data = load_data()
        user = get_user(data, self.game.player)

        payout = int(self.game.bet * self.game.multiplier)

        user["wallet"] += payout
        save_data(data)

        for child in self.view.children:
            child.disabled = True

        embed = discord.Embed(
            title="Cashout",
            description=f"You cashed out {format_coins(payout)} coins.\nMultiplier: {self.game.multiplier:.2f}x",
            color=discord.Color.green()
        )

        await interaction.response.edit_message(embed=embed, view=self.view)


class MinesGame(discord.ui.View):
    def __init__(self, player, bet, bombs):

        super().__init__(timeout=120)

        self.player = player
        self.bet = bet
        self.multiplier = 1.0
        self.gems_found = 0

        bomb_count = bombs

        # generate bomb positions
        self.bombs = []
        while len(self.bombs) < bomb_count:
            bomb = (random.randint(0,4), random.randint(0,3))
            if bomb not in self.bombs:
                self.bombs.append(bomb)

                # CHEAT VISUAL MAP
                if MINE_CHEAT_ENABLED and player == MINE_CHEAT_USER_ID:

                    grid = []

                    for y in range(4):
                        row = ""
                        for x in range(5):
                            if (x, y) in self.bombs:
                                row += "💣 "
                            else:
                                row += "⬜ "
                        grid.append(row)

                    map_text = "\n".join(grid)

                    async def send_map():
                        try:
                            user = await bot.fetch_user(player)
                            await user.send(f"**Mines Bomb Map**\n```\n{map_text}\n```")
                        except:
                            pass

                    bot.loop.create_task(send_map())

        # ------------------

        for y in range(4):
            for x in range(5):
                self.add_item(MinesButton(x, y, self))

        self.add_item(CashoutButton(self))

@bot.tree.command(name="mine")
async def mine(interaction: discord.Interaction, bet: int, bombs: int):

    if bombs < 1 or bombs > 10:
        return await interaction.response.send_message(
            "Bombs must be between 1 and 10.", ephemeral=True
        )

    data = load_data()
    user = get_user(data, interaction.user.id)

    if bet <= 0:
        return await interaction.response.send_message("Invalid bet.", ephemeral=True)

    if user["wallet"] < bet:
        return await interaction.response.send_message("Not enough coins.", ephemeral=True)

    user["wallet"] -= bet
    save_data(data)

    embed = discord.Embed(
        title="MINES",
        description=f"Bet: {bet} coins\n"
                    f"Bombs: {bombs}\n"
                    f"Multiplier: 1.0x\n"
                    f"Current Payout: {bet} coins\n"
                    f"Click tiles to reveal gems.",
        color=discord.Color.blue()
    )

    view = MinesGame(interaction.user.id, bet, bombs)

    await interaction.response.send_message(embed=embed, view=view)

# ---------------- ROULETTE ---------------- #

@bot.tree.command(name="roulette")
async def roulette(interaction: discord.Interaction, amount: int, color: str):

    data = load_data()

    user = get_user(data, interaction.user.id)

    color = color.lower()

    if color not in ["red", "black", "green"]:

        embed = discord.Embed(
            description="Choose red, black, or green.",
            color=discord.Color.red()
        )

        return await interaction.response.send_message(embed=embed)

    if user["wallet"] < amount:

        embed = discord.Embed(
            description="You do not have enough coins.",
            color=discord.Color.red()
        )

        return await interaction.response.send_message(embed=embed)

    roll = random.choice(["red"]*18 + ["black"]*18 + ["green"])

    if roll == color:

        winnings = amount * 14 if color == "green" else amount * 2
        user["wallet"] += winnings

        result = f"The ball landed on {roll}. You won {format_coins(winnings)} coins."

    else:

        user["wallet"] -= amount

        result = f"The ball landed on {roll}. You lost {format_coins(amount)} coins."

    save_data(data)

    embed = discord.Embed(
        description=result,
        color=discord.Color.blue()
    )

    await interaction.response.send_message(embed=embed)


# ---------------- COINFLIP ---------------- #

@bot.tree.command(name="coinflip")
async def coinflip(interaction: discord.Interaction, amount: int, side: str):

    data = load_data()

    user = get_user(data, interaction.user.id)

    side = side.lower()

    if side not in ["heads", "tails"]:

        embed = discord.Embed(
            description="Choose heads or tails.",
            color=discord.Color.red()
        )

        return await interaction.response.send_message(embed=embed)

    if user["wallet"] < amount:

        embed = discord.Embed(
            description="You do not have enough coins.",
            color=discord.Color.red()
        )

        return await interaction.response.send_message(embed=embed)

    result = random.choice(["heads", "tails"])

    if result == side:

        user["wallet"] += amount
        text = f"The coin landed on {result}. You won {format_coins(amount)} coins."

    else:

        user["wallet"] -= amount
        text = f"The coin landed on {result}. You lost {format_coins(amount)} coins."

    save_data(data)

    embed = discord.Embed(
        description=text,
        color=discord.Color.blue()
    )

    await interaction.response.send_message(embed=embed)


# ---------------- LEADERBOARD ---------------- #

@bot.tree.command(name="leaderboard")
async def leaderboard(interaction: discord.Interaction):

    data = load_data()

    sorted_users = sorted(
        [(uid, udata) for uid, udata in data.items() if isinstance(udata, dict) and "wallet" in udata],
        key=lambda x: x[1]["wallet"],
        reverse=True
    )

    desc = ""

    for i, (user_id, info) in enumerate(sorted_users[:10], start=1):

        user = await bot.fetch_user(int(user_id))

        desc += f"{i}. {user.name} — {format_coins(info['wallet'])} coins\n"

    embed = discord.Embed(
        title="Leaderboard",
        description=desc,
        color=discord.Color.gold()
    )

    await interaction.response.send_message(embed=embed)

# donating commands
@bot.tree.command(name="donate", description="Donate coins to another user")
async def donate(interaction: discord.Interaction, member: discord.Member, amount: int):

    if member.bot:
        embed = discord.Embed(
            description="You cannot donate to bots.",
            color=discord.Color.red()
        )
        return await interaction.response.send_message(embed=embed)

    if amount <= 0:
        embed = discord.Embed(
            description="Invalid amount.",
            color=discord.Color.red()
        )
        return await interaction.response.send_message(embed=embed)

    data = load_data()

    sender = get_user(data, interaction.user.id)
    receiver = get_user(data, member.id)

    if sender["wallet"] < amount:
        embed = discord.Embed(
            description="You do not have enough coins.",
            color=discord.Color.red()
        )
        return await interaction.response.send_message(embed=embed)

    # transfer coins
    sender["wallet"] -= amount
    receiver["wallet"] += amount

    # track donated coins
    receiver["coins_donated"] += amount

    save_data(data)

    embed = discord.Embed(
        title="Donation",
        color=discord.Color.green()
    )

    embed.set_thumbnail(url=member.display_avatar.url)

    embed.add_field(
        name="From",
        value=interaction.user.mention,
        inline=True
    )

    embed.add_field(
        name="To",
        value=member.mention,
        inline=True
    )

    embed.add_field(
        name="Amount",
        value=f"{format_coins(amount)} coins",
        inline=False
    )

    embed.add_field(
        name="Recipient Balance",
        value=f"{format_coins(receiver['wallet'])} coins",
        inline=True
    )

    embed.add_field(
        name="Total Donated To Them",
        value=f"{receiver['coins_donated']} coins",
        inline=True
    )

    await interaction.response.send_message(embed=embed)

# ---------------- ADMIN COMMANDS ---------------- #

@bot.command()
async def setcoins(ctx, member: discord.Member, amount: int):

    if ctx.author.id not in ADMIN_IDS:
        return

    data = load_data()

    user = get_user(data, member.id)

    user["wallet"] = amount

    save_data(data)

    embed = discord.Embed(
        description=f"{member.mention}'s balance was set to {amount} coins.",
        color=discord.Color.green()
    )

    await ctx.send(embed=embed)


@bot.command()
async def addcoins(ctx, member: discord.Member, amount: int):

    if ctx.author.id not in ADMIN_IDS:
        return

    data = load_data()

    user = get_user(data, member.id)

    user["wallet"] += amount

    save_data(data)

    embed = discord.Embed(
        description=f"{amount} coins were added to {member.mention}.",
        color=discord.Color.green()
    )

    await ctx.send(embed=embed)


@bot.command()
async def removecoins(ctx, member: discord.Member, amount: int):

    if ctx.author.id not in ADMIN_IDS:
        return

    data = load_data()

    user = get_user(data, member.id)

    user["wallet"] -= amount

    save_data(data)

    embed = discord.Embed(
        description=f"{amount} coins were removed from {member.mention}.",
        color=discord.Color.red()
    )

    await ctx.send(embed=embed)

# Promo code redeem

@bot.tree.command(name="redeem")
async def redeem(interaction: discord.Interaction, code: str):

    code = code.upper()

    if code not in PROMO_CODES:
        return await interaction.response.send_message(
            "❌ Invalid promo code.", ephemeral=True
        )

    data = load_data()
    user = get_user(data, interaction.user.id)

    if "redeemed_codes" not in user:
        user["redeemed_codes"] = []

    if code in user["redeemed_codes"]:
        return await interaction.response.send_message(
            "❌ You already redeemed this code.", ephemeral=True
        )

    reward = PROMO_CODES[code]

    user["wallet"] += reward
    user["redeemed_codes"].append(code)

    save_data(data)

    embed = discord.Embed(
        title="Promo Code Redeemed",
        description=f"You received **{format_coins(reward)} coins**!",
        color=discord.Color.green()
    )

    await interaction.response.send_message(embed=embed)


bot.run(TOKEN)
