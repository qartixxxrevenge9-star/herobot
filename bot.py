from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "I am alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

import discord
from discord.ext import commands
import json
import datetime
import random
import os

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.getenv('BOT_TOKEN')

LOG_CHANNEL_ID = 1485626459384057917 # ID канала для логов
PREFIX = '!'

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

DATA_FILE = 'data.json'

# --- СИСТЕМА ДАННЫХ ---
def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump({"users": {}, "shop": {}}, f)
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"users": {}, "shop": {}}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_user(data, user_id):
    uid = str(user_id)
    if uid not in data["users"]:
        data["users"][uid] = {"money": 0, "warns": 0, "inventory": []}
    return data["users"][uid]

async def send_log(guild, title, description, color=discord.Color.blue()):
    channel = guild.get_channel(LOG_CHANNEL_ID)
    if channel:
        embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.datetime.now())
        await channel.send(embed=embed)

# --- СОБЫТИЯ ---
@bot.event
async def on_ready():
    print(f'✅ Бот {bot.user} запущен!')
    print(f'✅ База данных загружена.')

@bot.event
async def on_member_join(member):
    welcome_channel = member.guild.system_channel
    if welcome_channel:
        await welcome_channel.send(f"👋 Привет, {member.mention}! Добро пожаловать!")
    await send_log(member.guild, "📥 Вход", f"Пользователь {member} зашел на сервер.")

@bot.event
async def on_member_remove(member):
    await send_log(member.guild, "📤 Выход", f"Пользователь {member} покинул сервер.")

# --- ОБРАБОТКА ОШИБОК (Чтобы бот не молчал) ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(f"❌ У вас недостаточно прав: `{error.missing_permissions}`")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Пользователь не найден. Упомяните его через @")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Пропущен аргумент! Пример: `{ctx.prefix}{ctx.command.name} [параметр]`")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Подождите {error.retry_after:.1f} сек.")
    else:
        print(f"Ошибка: {error}")

# --- МОДЕРАЦИЯ ---

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="Нарушение"):
    await member.kick(reason=reason)
    await ctx.send(f"👢 {member.mention} кикнут.")
    await send_log(ctx.guild, "👢 Кик", f"Модератор: {ctx.author}\nЦель: {member}\nПричина: {reason}", discord.Color.orange())

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="Нарушение"):
    await member.ban(reason=reason)
    await ctx.send(f"🔨 {member.mention} забанен навсегда.")
    await send_log(ctx.guild, "🔨 Бан", f"Модератор: {ctx.author}\nЦель: {member}\nПричина: {reason}", discord.Color.red())

@bot.command()
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, minutes: int, *, reason="Нарушение"):
    duration = datetime.timedelta(minutes=minutes)
    await member.timeout(duration, reason=reason)
    await ctx.send(f"🔇 {member.mention} отправлен в тайм-аут на {minutes} мин.")
    await send_log(ctx.guild, "🔇 Мут", f"Модератор: {ctx.author}\nЦель: {member}\nВремя: {minutes}м\nПричина: {reason}")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member):
    await member.timeout(None)
    await ctx.send(f"🔊 С {member.mention} снято ограничение.")
    await send_log(ctx.guild, "🔊 Размут", f"Модератор: {ctx.author}\nЦель: {member}")

@bot.command()
@commands.has_permissions(kick_members=True)
async def warn(ctx, member: discord.Member, *, reason="Нарушение"):
    data = load_data()
    user = get_user(data, member.id)
    user["warns"] += 1
    save_data(data)
    await ctx.send(f"⚠️ {member.mention} получил варн! (Всего: {user['warns']})")
    await send_log(ctx.guild, "⚠️ Варн", f"Модератор: {ctx.author}\nЦель: {member}\nПричина: {reason}")

@bot.command()
@commands.has_permissions(kick_members=True)
async def unwarn(ctx, member: discord.Member):
    data = load_data()
    user = get_user(data, member.id)
    if user["warns"] > 0:
        user["warns"] -= 1
        save_data(data)
        await ctx.send(f"✅ У {member.mention} снят один варн.")
    else:
        await ctx.send("❌ У игрока нет варнов.")

# --- ЭКОНОМИКА ---

@bot.command()
async def balance(ctx, member: discord.Member = None):
    member = member or ctx.author
    data = load_data()
    user = get_user(data, member.id)
    embed = discord.Embed(title=f"Кошелек {member.display_name}", color=discord.Color.gold())
    embed.add_field(name="Баланс", value=f"{user['money']} 💰")
    embed.add_field(name="Предупреждения", value=f"{user['warns']} ⚠️")
    await ctx.send(embed=embed)

@bot.command()
@commands.cooldown(1, 3600, commands.BucketType.user) # Раз в час
async def work(ctx):
    reward = random.randint(100, 300)
    data = load_data()
    user = get_user(data, ctx.author.id)
    user["money"] += reward
    save_data(data)
    await ctx.send(f"👷 {ctx.author.mention}, ты отработал смену и получил **{reward}** 💰!")

@bot.command(name="set-money")
@commands.has_permissions(administrator=True)
async def set_money(ctx, member: discord.Member, amount: int):
    data = load_data()
    user = get_user(data, member.id)
    user["money"] = amount
    save_data(data)
    await ctx.send(f"💳 Баланс {member.mention} изменен на **{amount}**.")

# --- МАГАЗИН И ИНВЕНТАРЬ ---

@bot.command(name="add-item")
@commands.has_permissions(administrator=True)
async def add_item(ctx, name: str, type: str, price: int, category: str, *, desc: str):
    """Пример: !add-item Меч item 1000 Оружие Крутой меч"""
    data = load_data()
    data["shop"][name.lower()] = {
        "name": name, "type": type.lower(), "price": price, "category": category, "desc": desc
    }
    save_data(data)
    await ctx.send(f"✅ Товар **{name}** добавлен в магазин.")

@bot.command()
async def shop(ctx):
    data = load_data()
    if not data["shop"]: return await ctx.send("🛒 Магазин пуст.")
    embed = discord.Embed(title="🏪 Магазин сервера", color=discord.Color.green())
    for n, i in data["shop"].items():
        t = "🎭 Роль" if i["type"] == "role" else "📦 Предмет"
        embed.add_field(name=f"{i['name']} | {i['price']} 💰", value=f"Тип: {t} | Кат: {i['category']}\n*{i['desc']}*", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def buy(ctx, *, item_name: str):
    data = load_data()
    item_key = item_name.lower()
    if item_key not in data["shop"]: return await ctx.send("❌ Товар не найден.")
    
    item = data["shop"][item_key]
    user = get_user(data, ctx.author.id)
    
    if user["money"] < item["price"]: return await ctx.send("❌ Недостаточно денег.")
    
    user["money"] -= item["price"]
    if item["type"] == "role":
        role = ctx.guild.get_role(int(item["desc"]))
        await ctx.author.add_roles(role)
        await ctx.send(f"✅ Вы купили роль {role.name}!")
    else:
        user["inventory"].append(item["name"])
        await ctx.send(f"✅ Вы купили {item['name']}! Проверьте `!inv`.")
    save_data(data)

@bot.command()
async def inv(ctx):
    data = load_data()
    user = get_user(data, ctx.author.id)
    items = ", ".join(user["inventory"]) if user["inventory"] else "Пусто"
    await ctx.send(f"🎒 **Ваш инвентарь:** {items}")

@bot.command(name="del-item")
@commands.has_permissions(administrator=True)
async def del_item(ctx, *, name: str):
    data = load_data()
    if name.lower() in data["shop"]:
        del data["shop"][name.lower()]
        save_data(data)
        await ctx.send(f"🗑️ Удалено.")
keep_alive()  # Запускает веб-сервер в отдельном потоке
import os
# ... (весь твой код) ...
bot.run(os.getenv('')) # Бот будет брать токен из настроек хостинга