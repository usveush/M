import discord
from discord.ext import commands
import os
from threading import Thread
from flask import Flask

# --- خادم ويب وهمي للاستضافة على Railway ---
app = Flask('')

@app.route('/')
def home():
    return "سكربت سحب الرتبة التلقائي يعمل 24/7"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

Thread(target=run_web, daemon=True).start()

# --- إعدادات البوت ---
intents = discord.Intents.default()
intents.members = True  # ضروري لتشغيل جلب الأعضاء

bot = commands.Bot(command_prefix=".", intents=intents)

# --- البيانات الخاصة بالعملية ---
USER_ID = 1155991299195945030   # آيدي الشخص
ROLE_ID = 1527939953881911468   # آيدي الرتبة

@bot.event
async def on_ready():
    print(f'✅ تم تسجيل الدخول باسم البوت: {bot.user}')
    print("🔍 جاري البحث في كافة السيرفرات المتواجد فيها البوت...")

    found = False

    # البحث في كل السيرفرات التي يدخلها البوت
    for guild in bot.guilds:
        try:
            # البحث عن الرتبة والعضو داخل السيرفر الحالي
            role = guild.get_role(ROLE_ID)
            member = guild.get_member(USER_ID)

            # إذا لم يجد العضو كـ Cache يحاول يجيبه من الديسكورد
            if not member:
                try:
                    member = await guild.fetch_member(USER_ID)
                except Exception:
                    member = None

            # إذا وجد الاثنين في نفس السيرفر ينفذ العملية
            if member and role:
                found = True
                print(f"🎯 تم العثور على المطلوب في سيرفر: {guild.name} (`{guild.id}`)")

                if role.position < guild.me.top_role.position and not role.managed:
                    await member.remove_roles(role, reason="إزالة تلقائية عبر البحث الشامل")
                    print(f"🎉 تم إزالة الرتبة ({role.name}) من العضو ({member.display_name}) بنجاح!")
                else:
                    print(f"⚠️ خطأ صلاحيات في سيرفر ({guild.name}): رتبة البوت أقل من الرتبة المراد إزالتها أو أنها رتبة نظام.")
                break  # العثور والتنفيذ وتوقف البحث

        except Exception as e:
            print(f"❌ حدث خطأ أثناء الفحص في سيرفر {guild.name}: {e}")

    if not found:
        print("❌ لم يتم العثور على العضو والرتبة معاً في أي سيرفر يوجد فيه البوت حالياً.")

# --- تشغيل البوت ---
BOT_TOKEN = os.environ.get("DISCORD_TOKEN")
if BOT_TOKEN:
    bot.run(BOT_TOKEN)
else:
    print("خطأ: لم يتم العثور على متغير البيئة DISCORD_TOKEN")
