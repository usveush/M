import discord
from discord.ext import commands
import asyncio
import datetime
import os
import re
from collections import defaultdict
from threading import Thread
from flask import Flask

# --- خادم ويب وهمي للاستضافة على Railway ---
app = Flask('')

@app.route('/')
def home():
    return "نظام الحماية القصوى المطور يعمل بنجاح 24/7"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

Thread(target=run_web, daemon=True).start()

# --- إعدادات البوت ---
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=".", intents=intents)

# الحسابات الموثوقة (الأونرات)
TRUSTED_IDS = [1422918463034228757, 1423421691773714482]

# البوتات المستثناة والتي تملك حصانة كاملة ومطلقة في السيرفر
EXEMPTED_BOTS = [
    652505019920285707, 
    762217899355013120, 
    1526691977863626802,  # بوت الحماية من حذف الرومات
    1510521767423246486   # بوت الحماية من حذف الرولات
]

# الذاكرة المؤقتة للرتب والسبام
removed_roles_backup = {}
action_cooldown = defaultdict(list)

# الصلاحيات الخطيرة المراقبة
DANGEROUS_PERMS = ['administrator', 'manage_guild', 'ban_members', 'kick_members', 'manage_roles', 'manage_channels', 'manage_webhooks']

# نمط التحقق من روابط دعوات ديسكورد
INVITE_REGEX = re.compile(r'(discord\.gg|discord\.com/invite)/[a-zA-Z0-9]+', re.IGNORECASE)

# --- دالة إرسال الإمبيد التفصيلي للأونرات فقط ---
async def send_owner_embed(title, description, target_info=None, extra_info=None):
    embed = discord.Embed(
        title=f"🛡️ تقرير أمني | {title}",
        description=description,
        color=discord.Color.red(),
        timestamp=discord.utils.utcnow()
    )
    if target_info:
        embed.add_field(name="🔹 الهدف المتأثر:", value=target_info, inline=False)
    if extra_info:
        embed.add_field(name="🔹 تفاصيل إضافية:", value=extra_info, inline=False)
    
    embed.set_footer(text="تقرير تلقائي - نظام الحماية القصوى")
        
    for owner_id in TRUSTED_IDS:
        try:
            owner = bot.get_user(owner_id) or await bot.fetch_user(owner_id)
            if owner:
                await owner.send(embed=embed)
        except Exception:
            pass

# --- دالة قشع الرتب وإرسال رسالة بالخاص للشخص المخالف ---
async def strip_roles(member: discord.Member, reason: str, target_info=None, extra_info=None):
    if member.id in TRUSTED_IDS or member.id in EXEMPTED_BOTS:
        return
        
    if member.bot:
        try:
            await member.kick(reason=f"[الحماية] - {reason}")
            title_msg = "🚨 طرد بوت مخالف من السيرفر"
            desc_msg = f"🤖 **البوت المخالف:** {member.mention}\n🆔 **ايدي البوت:** `{member.id}`\n❓ **السبب الكامل:** {reason}"
            await send_owner_embed(title_msg, desc_msg, target_info, extra_info)
        except Exception:
            pass
        return
    
    # جلب الرتب التي يمكن للبوت إزالتها (أقل من رتبة البوت وليست رتبة @everyone)
    bot_top_role = member.guild.me.top_role
    all_removable_roles = [role for role in member.roles if not role.is_default() and role.position < bot_top_role.position]
    
    if all_removable_roles:
        removed_roles_backup[member.id] = all_removable_roles
        try:
            # إرسال رسالة تنبيه بالخاص للشخص المقشوع قبل السحب
            embed_dm = discord.Embed(
                title="⚠️ تنبيه أمني من نظام الحماية",
                description=f"مرحباً {member.mention}، تم سحب رتبك تلقائياً من سيرفر **{member.guild.name}** بسبب محاولة تخريب أو مخالفة أنظمة الحماية.\n\n❓ **السبب:** {reason}",
                color=discord.Color.orange()
            )
            try:
                await member.send(embed=embed_dm)
            except Exception:
                pass # إذا كانت خاصيته مغفلة

            await member.remove_roles(*all_removable_roles, reason=f"[الحماية] - {reason}")
            
            title_msg = "🚨 رصد مخالفة وقشع الرتب"
            desc_msg = f"👤 **الفاعل المتأثر:** {member.mention}\n🆔 **الايدي:** `{member.id}`\n❓ **السبب:** {reason}"
            await send_owner_embed(title_msg, desc_msg, target_info, extra_info)
        except discord.Forbidden:
            print(f"فشل قشع رتب {member.name} بسبب نقص الصلاحيات.")

# --- دالة فحص سجلات التدقيق ---
async def get_audit_executor(guild, action_type, check_time=5):
    await asyncio.sleep(0.8)  # تأخير طفيف لضمان تسجيل العملية في ديسكورد
    try:
        async for entry in guild.audit_logs(limit=3, action=action_type):
            now = datetime.datetime.now(datetime.timezone.utc)
            if (now - entry.created_at).total_seconds() < check_time:
                return entry
    except discord.Forbidden:
        print(f"البوت يفتقر لصلاحية عرض سجلات التدقيق في سيرفر: {guild.name}")
    return None

# --- دالة مراقبة السبام ---
def check_spam_action(user_id, action_name, max_count=3, seconds=5):
    now = datetime.datetime.now(datetime.timezone.utc)
    key = f"{user_id}_{action_name}"
    user_actions = action_cooldown[key]
    
    # تنظيف العمليات القديمة المتوافقة مع الـ timezone
    user_actions = [t for t in user_actions if (now - t).total_seconds() < seconds]
    user_actions.append(now)
    action_cooldown[key] = user_actions
    
    return len(user_actions) > max_count

# ==================== أنظمة الحماية والأحداث ====================

@bot.event
async def on_guild_channel_delete(channel):
    entry = await get_audit_executor(channel.guild, discord.AuditLogAction.channel_delete)
    if entry and entry.user.id not in TRUSTED_IDS and entry.user.id not in EXEMPTED_BOTS:
        member = channel.guild.get_member(entry.user.id)
        if member:
            await strip_roles(member, "محاولة حذف قناة/فئة من السيرفر", f"اسم الروم: {channel.name} | النوع: {channel.type}")
            try:
                await channel.clone(reason="إعادة إنشاء الروم تلقائياً لحماية هيكل السيرفر")
            except Exception:
                pass

@bot.event
async def on_guild_channel_update(before, after):
    entry = await get_audit_executor(after.guild, discord.AuditLogAction.channel_update)
    if entry and entry.user.id not in TRUSTED_IDS and entry.user.id not in EXEMPTED_BOTS:
        member = after.guild.get_member(entry.user.id)
        if member:
            await strip_roles(member, "تعديل خصائص أو صلاحيات القنوات", f"الروم المتأثر: {after.mention} (`{after.id}`)", f"الاسم قبل: {before.name} | بعد: {after.name}")
            try:
                await after.edit(name=before.name, topic=before.topic, nsfw=before.nsfw, category=before.category, sync_permissions=True)
            except Exception:
                pass

@bot.event
async def on_guild_channel_create(channel):
    entry = await get_audit_executor(channel.guild, discord.AuditLogAction.channel_create)
    if entry and entry.user.id not in TRUSTED_IDS and entry.user.id not in EXEMPTED_BOTS:
        if check_spam_action(entry.user.id, "channel_create", max_count=3, seconds=10):
            member = channel.guild.get_member(entry.user.id)
            if member:
                await strip_roles(member, "سبام إنشاء قنوات مكثف", f"الروم المكتشف: {channel.name}")
            try:
                await channel.delete()
            except Exception:
                pass

@bot.event
async def on_guild_role_delete(role):
    entry = await get_audit_executor(role.guild, discord.AuditLogAction.role_delete)
    if entry and entry.user.id not in TRUSTED_IDS and entry.user.id not in EXEMPTED_BOTS:
        member = role.guild.get_member(entry.user.id)
        if member:
            await strip_roles(member, "حذف رتبة من السيرفر", f"اسم الرتبة المحذوفة: {role.name} (`{role.id}`)")
            try:
                await role.guild.create_role(name=role.name, permissions=role.permissions, color=role.color, hoist=role.hoist, mentionable=role.mentionable)
            except Exception:
                pass

@bot.event
async def on_guild_role_create(role):
    entry = await get_audit_executor(role.guild, discord.AuditLogAction.role_create)
    if entry and entry.user.id not in TRUSTED_IDS and entry.user.id not in EXEMPTED_BOTS:
        if check_spam_action(entry.user.id, "role_create", max_count=3, seconds=10):
            member = role.guild.get_member(entry.user.id)
            if member:
                await strip_roles(member, "سبام إنشاء رتب مكثف", f"الرتبة المكتشفة: {role.name}")
            try:
                await role.delete()
            except Exception:
                pass

@bot.event
async def on_guild_role_update(before, after):
    entry = await get_audit_executor(after.guild, discord.AuditLogAction.role_update)
    if entry and entry.user.id not in TRUSTED_IDS and entry.user.id not in EXEMPTED_BOTS:
        member = after.guild.get_member(entry.user.id)
        if member:
            for perm in DANGEROUS_PERMS:
                has_before = getattr(before.permissions, perm)
                has_after = getattr(after.permissions, perm)
                
                if has_after and not has_before:
                    await strip_roles(member, f"محاولة تفعيل صلاحية خطيرة جديدة للرتبة ({perm})", f"الرتبة المعدلة: {after.name} (`{after.id}`)")
                    try:
                        await after.edit(permissions=before.permissions)
                    except Exception:
                        pass
                    return

@bot.event
async def on_member_update(before, after):
    if len(before.roles) != len(after.roles):
        entry = await get_audit_executor(after.guild, discord.AuditLogAction.member_role_update)
        if entry and entry.user.id not in TRUSTED_IDS and entry.user.id not in EXEMPTED_BOTS:
            added_roles = [r for r in after.roles if r not in before.roles]
            for role in added_roles:
                if any(getattr(role.permissions, perm) for perm in DANGEROUS_PERMS):
                    admin_member = after.guild.get_member(entry.user.id)
                    
                    # قشع المشرف أولاً
                    if admin_member:
                        await strip_roles(admin_member, f"إعطاء رتبة خطيرة ({role.name}) لعضو آخر بدون تصريح رسمي", 
                                          f"الرتبة الموزعة: {role.name} (`{role.id}`)", 
                                          f"👤 **الشخص المستهدف:** {after.mention} (`{after.id}`)")
                    
                    # قشع الشخص الذي استلم الصلاحية لحماية الخادم
                    if after.id not in TRUSTED_IDS and after.id not in EXEMPTED_BOTS:
                        await strip_roles(after, f"استلام رتبة خطيرة ({role.name}) تحتوي على صلاحيات إدارية",
                                          f"الرتبة المستلمة: {role.name}",
                                          f"👤 **المشرف الفاعل:** {admin_member.mention if admin_member else 'غير معروف'}")
                    return

@bot.event
async def on_webhooks_update(channel):
    await asyncio.sleep(0.5)
    try:
        async for entry in channel.guild.audit_logs(limit=1):
            if entry.action in [discord.AuditLogAction.webhook_create, discord.AuditLogAction.webhook_update, discord.AuditLogAction.webhook_delete]:
                if entry.user.id not in TRUSTED_IDS and entry.user.id not in EXEMPTED_BOTS:
                    member = channel.guild.get_member(entry.user.id)
                    if member:
                        action_name = "إنشاء" if entry.action == discord.AuditLogAction.webhook_create else "تعديل" if entry.action == discord.AuditLogAction.webhook_update else "حذف"
                        await strip_roles(member, f"التلاعب بالويب هوك ({action_name})", f"الروم المتأثر: {channel.mention}", f"اسم الويب هوك: {entry.target.name if entry.target else 'غير معروف'}")
                        if entry.action == discord.AuditLogAction.webhook_create and entry.target:
                            try:
                                wh = await bot.fetch_webhook(entry.target.id)
                                await wh.delete()
                            except Exception:
                                pass
    except Exception:
        pass

@bot.event
async def on_guild_update(before, after):
    entry = await get_audit_executor(after, discord.AuditLogAction.guild_update)
    if entry and entry.user.id not in TRUSTED_IDS and entry.user.id not in EXEMPTED_BOTS:
        member = after.get_member(entry.user.id)
        if member:
            await strip_roles(member, "تعديل وتخريب إعدادات وهوية السيرفر", f"اسم السيرفر: {after.name}")
            try:
                await after.edit(name=before.name, icon=before.icon, banner=before.banner, description=before.description, verification_level=before.verification_level)
            except Exception:
                pass

@bot.event
async def on_guild_emojis_update(guild, before, after):
    if len(before) > len(after):
        entry = await get_audit_executor(guild, discord.AuditLogAction.emoji_delete)
        if entry and entry.user.id not in TRUSTED_IDS and entry.user.id not in EXEMPTED_BOTS:
            member = guild.get_member(entry.user.id)
            if member:
                await strip_roles(member, "حذف إيموجيات السيرفر")

@bot.event
async def on_guild_stickers_update(guild, before, after):
    if len(before) > len(after):
        entry = await get_audit_executor(guild, discord.AuditLogAction.sticker_delete)
        if entry and entry.user.id not in TRUSTED_IDS and entry.user.id not in EXEMPTED_BOTS:
            member = guild.get_member(entry.user.id)
            if member:
                await strip_roles(member, "حذف ستيكرات السيرفر")

@bot.event
async def on_invite_create(invite):
    executor = invite.inviter
    if executor and executor.id not in TRUSTED_IDS and executor.id not in EXEMPTED_BOTS:
        if check_spam_action(executor.id, "invite_create", max_count=4, seconds=10):
            member = invite.guild.get_member(executor.id)
            if member:
                await strip_roles(member, "سبام إنشاء روابط دعوات مكثف")
            try:
                await invite.delete()
            except Exception:
                pass

@bot.event
async def on_member_ban(guild, user):
    entry = await get_audit_executor(guild, discord.AuditLogAction.ban)
    if entry and entry.user.id not in TRUSTED_IDS and entry.user.id not in EXEMPTED_BOTS:
        if check_spam_action(entry.user.id, "mass_ban", max_count=3, seconds=300):
            member = guild.get_member(entry.user.id)
            if member:
                await strip_roles(member, "سبام حظر مكثف (Mass Ban)")

@bot.event
async def on_member_remove(member):
    entry = await get_audit_executor(member.guild, discord.AuditLogAction.kick)
    if entry and entry.user.id not in TRUSTED_IDS and entry.user.id not in EXEMPTED_BOTS:
        if check_spam_action(entry.user.id, "mass_kick", max_count=3, seconds=300):
            admin_member = member.guild.get_member(entry.user.id)
            if admin_member:
                await strip_roles(admin_member, "سبام طرد للأعضاء (Kick Spam)")

@bot.event
async def on_member_join(member):
    if member.bot:
        entry = await get_audit_executor(member.guild, discord.AuditLogAction.bot_add)
        if entry and entry.user.id not in TRUSTED_IDS and entry.user.id not in EXEMPTED_BOTS:
            try:
                await member.ban(reason="دخول بوت غير مصرح به")
                inviter = member.guild.get_member(entry.user.id)
                if inviter: 
                    await strip_roles(inviter, "إدخال بوت غريب ومخرب للسيرفر", f"🤖 **البوت الدخيل:** {member.mention}")
            except Exception:
                pass

@bot.event
async def on_message(message):
    if not message.guild or message.author.bot or message.author.id in TRUSTED_IDS or message.author.id in EXEMPTED_BOTS:
        await bot.process_commands(message)
        return

    if INVITE_REGEX.search(message.content):
        try:
            await message.delete()
            await strip_roles(message.author, "نشر روابط دعوات لسيرفرات أخرى")
            return
        except Exception:
            pass

    if message.role_mentions:
        for role in message.role_mentions:
            if len(role.members) >= 10:
                cooldown_seconds = 120 if message.author.bot else 300
                if check_spam_action(message.author.id, f"role_mention_{role.id}", max_count=4, seconds=cooldown_seconds):
                    time_frame = "دقيقتين" if message.author.bot else "5 دقائق"
                    await strip_roles(message.author, f"تكرار منشن رتبة كبيرة ({role.name}) 4 مرات خلال {time_frame}")
                    try:
                        await message.delete()
                    except Exception:
                        pass
                    return

    if message.mention_everyone or len(message.mentions) >= 10:
        if check_spam_action(message.author.id, "mass_mention", max_count=3, seconds=300):
            await strip_roles(message.author, "سبام منشن جماعي أو عشوائي للأعضاء (Mass Mention)")
            try:
                await message.delete()
            except Exception:
                pass
            return

    if len(message.mentions) > 0:
        if check_spam_action(message.author.id, "mention_spam", max_count=3, seconds=10):
            await strip_roles(message.author, "سبام وتكرار المنشن المزعج للأعضاء")
            try:
                await message.delete()
            except Exception:
                pass
            return

    await bot.process_commands(message)

@bot.event
async def on_message_delete(message):
    if not message.guild or message.author.bot:
        return
    entry = await get_audit_executor(message.guild, discord.AuditLogAction.message_delete)
    if entry and entry.user.id not in TRUSTED_IDS and entry.user.id not in EXEMPTED_BOTS:
        if check_spam_action(entry.user.id, "message_delete_spam", max_count=15, seconds=10):
            member = message.guild.get_member(entry.user.id)
            if member:
                await strip_roles(member, "سبام حذف رسائل الأعضاء بكثرة")

# ==================== أوامر التحكم والفك ====================

@bot.command(name="انطم")
async def mute_all(ctx):
    if ctx.author.id not in TRUSTED_IDS: 
        return
    if ctx.author.voice and ctx.author.voice.channel:
        for member in ctx.author.voice.channel.members:
            if member.id not in TRUSTED_IDS and not member.bot:
                try:
                    await member.edit(mute=True)
                except Exception:
                    pass
        await ctx.send("🤫 تم كتم الجميع في الروم الصوتي.")
    else: 
        await ctx.send("يجب أن تكون داخل روم صوتي أولاً")

@bot.command(name="تكلم")
async def unmute_all(ctx):
    if ctx.author.id not in TRUSTED_IDS: 
        return
    if ctx.author.voice and ctx.author.voice.channel:
        for member in ctx.author.voice.channel.members:
            try:
                await member.edit(mute=False)
            except Exception:
                pass
        await ctx.send("🔊 تم فتح المايك عن الجميع.")
    else: 
        await ctx.send("يجب أن تكون داخل روم صوتي أولاً")

@bot.command(name="فك")
async def restore_roles(ctx, member: discord.Member):
    if ctx.author.id not in TRUSTED_IDS: 
        return
    if member.id in removed_roles_backup:
        bot_top_role = ctx.guild.me.top_role
        roles_to_add = [r for r in removed_roles_backup[member.id] if r in ctx.guild.roles and r.position < bot_top_role.position]
        if roles_to_add:
            try:
                await member.add_roles(*roles_to_add, reason="إعادة الرتب بواسطة الأونر")
                del removed_roles_backup[member.id]
                await ctx.send(f"✅ تم إعادة الرتب بنجاح للعضو: {member.mention}")
            except Exception:
                await ctx.send("حدث خطأ، تأكد من صلاحيات وترتيب رتبة البوت.")
        else: 
            await ctx.send("لم يتم العثور على رتب صالحة لإعادتها.")
    else: 
        await ctx.send("لا توجد رتب محفوظة ومقشوعة لهذا الشخص في الرام.")

# --- تشغيل البوت ---
BOT_TOKEN = os.environ.get("DISCORD_TOKEN")
if BOT_TOKEN:
    bot.run(BOT_TOKEN)
else:
    print("خطأ: لم يتم العثور على متغير البيئة DISCORD_TOKEN")
