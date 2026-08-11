import discord
from discord.ext import commands
import os
from threading import Thread
from flask import Flask

# --- خادم ويب وهمي للاستضافة على Railway ---
app = Flask('')

@app.route('/')
def home():
    return "سكربت سحب الرتبة يعمل بنجاح 24/7"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

Thread(target=run_web, daemon=True).start()

# --- إعدادات البوت ---
intents = discord.Intents.default()
intents.members = True  # ضروري لتفعيل جلب الاعضاء

bot = commands.Bot(command_prefix=".", intents=intents)

# --- البيانات الخاصة بالعملية ---
GUILD_ID = 000000000000000000  # <--- حط آيدي السيرفر حقك هنا بدال الأصفار
USER_ID = 1155991299195945030   # آيدي الشخص
ROLE_ID = 1527939953881911468   # آيدي الرتبة

@bot.event
async def on_ready():
    print(f'✅ تم تسجيل الدخول باسم البوت: {bot.user}')
    
    try:
        # جلب السيرفر
        guild = bot.get_guild(GUILD_ID) or await bot.fetch_guild(GUILD_ID)
        
        if guild:
            # جلب العضو والرتبة
            member = guild.get_member(USER_ID) or await guild.fetch_member(USER_ID)
            role = guild.get_role(ROLE_ID)
            
            if member and role:
                # التأكد من ترتيب الصلاحيات
                if role.position < guild.me.top_role.position and not role.managed:
                    await member.remove_roles(role, reason="إزالة تلقائية عبر السكربت المباشر")
                    print(f"🎉 تم إزالة الرتبة ({role.name}) من العضو ({member.display_name}) بنجاح!")
                else:
                    print("⚠️ خطأ صلاحيات: رتبة البوت أقل من الرتبة المراد إزالتها، أو أنها رتبة نظام تلقائية.")
            else:
                print("❌ لم يتم العثور على العضو أو الرتبة داخل هذا السيرفر.")
        else:
            print("❌ لم يتم العثور على السيرفر، تأكد من صحة GUILD_ID وأن البوت داخل السيرفر.")

    except Exception as e:
        print(f"❌ حدث خطأ أثناء التنفيذ: {e}")

# --- تشغيل البوت ---
BOT_TOKEN = os.environ.get("DISCORD_TOKEN")
if BOT_TOKEN:
    bot.run(BOT_TOKEN)
else:
    print("خطأ: لم يتم العثور على متغير البيئة DISCORD_TOKEN")
