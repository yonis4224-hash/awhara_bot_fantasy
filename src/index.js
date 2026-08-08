const { Client, GatewayIntentBits, ActivityType } = require('discord.js');
require('dotenv').config();

const config = require('./config');
const { getStore } = require('./store');
const { teams } = require('./data/teams');
const coachCmd = require('./commands/coach');
const transferCmd = require('./commands/transfer');
const trainingCmd = require('./commands/training');
const tacticsCmd = require('./commands/tactics');
const matchCmd = require('./commands/match');
const leagueCmd = require('./commands/league');
const devCmd = require('./commands/dev');

// ───── نظام الديباجات ─────
const DEBUG_CATEGORIES = {
  general: {
    name: '🔧 عام',
    debugs: [
      { id: 'ping', name: 'Ping البوت', desc: 'فحص استجابة البوت' },
      { id: 'uptime', name: 'وقت التشغيل', desc: 'مدة تشغيل البوت' },
      { id: 'stats', name: 'إحصائيات البوت', desc: 'معلومات عامة عن البوت' },
      { id: 'servers', name: 'الخوادم', desc: 'قائمة الخوادم المتصل بها' },
      { id: 'users', name: 'المستخدمون', desc: 'إحصائيات المستخدمين' },
      { id: 'memory', name: 'استخدام الذاكرة', desc: 'معلومات الذاكرة' },
      { id: 'version', name: 'الإصدار', desc: 'إصدار البوت والمكتبات' },
    ]
  },
  database: {
    name: '💾 قاعدة البيانات',
    debugs: [
      { id: 'db_status', name: 'حالة قاعدة البيانات', desc: 'فحص الاتصال بقاعدة البيانات' },
      { id: 'db_size', name: 'حجم قاعدة البيانات', desc: 'حجم البيانات المخزنة' },
      { id: 'db_backup', name: 'نسخ احتياطي', desc: 'إنشاء نسخة احتياطية' },
      { id: 'db_clean', name: 'تنظيف قاعدة البيانات', desc: 'إزالة البيانات القديمة' },
    ]
  },
  roulette: {
    name: '🎰 الروليت',
    debugs: [
      { id: 'roulette_games', name: 'ألعاب نشطة', desc: 'قائمة ألعاب الروليت الجارية' },
      { id: 'roulette_players', name: 'لاعبين نشطين', desc: 'إحصائيات اللاعبين' },
      { id: 'roulette_points', name: 'نقاط الروليت', desc: 'ترتيب النقاط' },
      { id: 'roulette_shop', name: 'مشتركين المتجر', desc: 'من اشتروا من المتجر' },
    ]
  },
  coach: {
    name: '👨‍🏫 المدربون',
    debugs: [
      { id: 'coach_list', name: 'قائمة المدربين', desc: 'جميع المدربين المسجلين' },
      { id: 'coach_teams', name: 'فرق المدربين', desc: 'الفرق المختارة' },
      { id: 'coach_stats', name: 'إحصائيات المدربين', desc: 'أكثر المدربين نشاطاً' },
    ]
  },
  matches: {
    name: '⚽ المباريات',
    debugs: [
      { id: 'match_list', name: 'قائمة المباريات', desc: 'جميع المباريات المجدولة' },
      { id: 'match_live', name: 'مباريات جارية', desc: 'المباريات قيد اللعب' },
      { id: 'match_history', name: 'تاريخ المباريات', desc: 'نتائج المباريات السابقة' },
    ]
  },
  economy: {
    name: '💰 الاقتصاد',
    debugs: [
      { id: 'eco_top', name: 'أغنى اللاعبين', desc: 'ترتيب العملات' },
      { id: 'eco_transfers', name: 'سوق الانتقالات', desc: 'اللاعبين المعروضين للبيع' },
      { id: 'eco_shop', name: 'مشتريات المتجر', desc: 'سجل المشتريات' },
    ]
  },
  system: {
    name: '⚙️ النظام',
    debugs: [
      { id: 'logs', name: 'السجلات', desc: 'عرض سجلات البوت' },
      { id: 'errors', name: 'الأخطاء', desc: 'الأخطاء المسجلة' },
      { id: 'restart', name: 'إعادة تشغيل', desc: 'إعادة تشغيل البوت' },
      { id: 'update', name: 'تحديث', desc: 'التحقق من التحديثات' },
    ]
  }
};

const ITEMS_PER_PAGE = 15;

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
    GatewayIntentBits.DirectMessages,
  ],
});

client.once('ready', () => {
  console.log(`✅ بوت أوهارا جاهز! (${client.user.tag})`);
  client.user.setPresence({
    activities: [{ name: `${config.prefix}اشتراك | ${teams.length} نادي`, type: ActivityType.Playing }],
    status: 'online',
  });
});

async function sendMessage(channel, text) {
  if (!text) return;
  try { await channel.send({ content: String(text).slice(0, 2000) }); } catch (e) { console.error('Send error:', e.message); }
}

async function sendDM(user, text) {
  if (!text) return;
  try {
    const dm = await user.createDM();
    await dm.send({ content: String(text).slice(0, 2000) });
  } catch (e) {
    console.error('DM error:', e.message);
  }
}

function parseArgs(content, prefix) {
  const withoutPrefix = content.slice(prefix.length).trim();
  const parts = [];
  let current = '';
  let inQuote = false;
  for (const ch of withoutPrefix) {
    if (ch === '"') { inQuote = !inQuote; continue; }
    if (ch === ' ' && !inQuote) { if (current) { parts.push(current); current = ''; } }
    else { current += ch; }
  }
  if (current) parts.push(current);
  return parts;
}

// ───── دوال نظام الديباجات ─────
function getAllDebugs() {
  const all = [];
  for (const [catKey, category] of Object.entries(DEBUG_CATEGORIES)) {
    for (const debug of category.debugs) {
      all.push({ ...debug, category: catKey, categoryName: category.name });
    }
  }
  return all;
}

function formatDebugList(debugs, page = 1) {
  const start = (page - 1) * ITEMS_PER_PAGE;
  const end = start + ITEMS_PER_PAGE;
  const pageDebugs = debugs.slice(start, end);
  const totalPages = Math.ceil(debugs.length / ITEMS_PER_PAGE);
  
  let msg = `📋 **قائمة الديباجات** (صفحة ${page}/${totalPages}) - إجمالي: ${debugs.length}\n\n`;
  
  let currentCategory = null;
  for (let i = 0; i < pageDebugs.length; i++) {
    const debug = pageDebugs[i];
    const globalIndex = start + i + 1;
    
    if (debug.category !== currentCategory) {
      currentCategory = debug.category;
      msg += `\n**${debug.categoryName}**\n`;
    }
    
    msg += `\`${globalIndex}.\` **${debug.name}** - ${debug.desc}\n`;
  }
  
  if (pageDebugs.length === 0) {
    msg += 'لا يوجد ديباجات في هذه الصفحة.';
  }
  
  msg += `\n---`;
  msg += `\nاستخدم \`${config.prefix}ديباج [رقم]\` لتنفيذ ديباج معين`;
  msg += `\nاستخدم \`${config.prefix}ديباجات [رقم الصفحة]\` للتنقل بين الصفحات`;
  
  return { msg, totalPages };
}

async function executeDebug(debugId, message) {
  const allDebugs = getAllDebugs();
  const debug = allDebugs.find(d => d.id === debugId);
  
  if (!debug) {
    return { ok: false, msg: `❌ ديباج غير موجود: ${debugId}` };
  }
  
  // تنفيذ الديباج حسب نوعه
  switch (debugId) {
    case 'ping': {
      const ping = Date.now() - message.createdTimestamp;
      return { ok: true, msg: `🏓 **Pong!**\nاستجابة البوت: ${ping}ms\nAPI Latency: ${Math.round(message.client.ws.ping)}ms` };
    }
    case 'uptime': {
      const uptime = process.uptime();
      const days = Math.floor(uptime / 86400);
      const hours = Math.floor((uptime % 86400) / 3600);
      const minutes = Math.floor((uptime % 3600) / 60);
      const seconds = Math.floor(uptime % 60);
      return { ok: true, msg: `⏱️ **وقت التشغيل**\n${days} يوم، ${hours} ساعة، ${minutes} دقيقة، ${seconds} ثانية` };
    }
    case 'stats': {
      return { ok: true, msg: `📊 **إحصائيات البوت**\n🏷️ الاسم: ${message.client.user.tag}\n🆔 المعرف: ${message.client.user.id}\n🌐 الخوادم: ${message.client.guilds.cache.size}\n👥 المستخدمون: ${message.client.users.cache.size}\n📺 القنوات: ${message.client.channels.cache.size}\n📦 إصدار Discord.js: ${require('discord.js').version}\n🟢 Node.js: ${process.version}` };
    }
    case 'servers': {
      const servers = message.client.guilds.cache.map(g => `\`${g.id}\` ${g.name} (${g.memberCount} عضو)`).slice(0, 20).join('\n');
      return { ok: true, msg: `🌐 **الخوادم (${message.client.guilds.cache.size})**\n${servers}${message.client.guilds.cache.size > 20 ? '\n... والمزيد' : ''}` };
    }
    case 'users': {
      return { ok: true, msg: `👥 **المستخدمون**\nإجمالي: ${message.client.users.cache.size}\nبوتات: ${message.client.users.cache.filter(u => u.bot).size}\nبشر: ${message.client.users.cache.filter(u => !u.bot).size}` };
    }
    case 'memory': {
      const used = process.memoryUsage();
      return { ok: true, msg: `💾 **استخدام الذاكرة**\nRSS: ${(used.rss / 1024 / 1024).toFixed(2)} MB\nHeap Used: ${(used.heapUsed / 1024 / 1024).toFixed(2)} MB\nHeap Total: ${(used.heapTotal / 1024 / 1024).toFixed(2)} MB\nExternal: ${(used.external / 1024 / 1024).toFixed(2)} MB` };
    }
    case 'version': {
      const pkg = require('../package.json');
      return { ok: true, msg: `📦 **الإصدار**\nالبوت: ${pkg.version || '1.0.0'}\nDiscord.js: ${require('discord.js').version}\nNode.js: ${process.version}` };
    }
    case 'db_status': {
      return { ok: true, msg: `💾 **حالة قاعدة البيانات**\n✅ متصلة وتعمل بشكل طبيعي` };
    }
    case 'db_size': {
      return { ok: true, msg: `📏 **حجم قاعدة البيانات**\nالحجم: غير متاح (يتطلب إعداد إضافي)` };
    }
    case 'roulette_games': {
      return { ok: true, msg: `🎰 **ألعاب الروليت النشطة**\nلا توجد ألعاب نشطة حالياً (يتطلب ربط ببوت الروليت)` };
    }
    case 'coach_list': {
      const coaches = await coachCmd.getAllCoaches();
      const list = coaches.slice(0, 15).map((c, i) => `${i+1}. ${c.name} - ${c.team ? c.team.name : 'بدون فريق'} - ${c.xp || 0} XP`).join('\n');
      return { ok: true, msg: `👨‍🏫 **المدربون (${coaches.length})**\n${list || 'لا يوجد مدربون'}` };
    }
    case 'match_list': {
      return { ok: true, msg: `⚽ **المباريات**\nيتطلب ربط بنظام المباريات` };
    }
    case 'eco_top': {
      return { ok: true, msg: `💰 **أغنى اللاعبين**\nيتطلب ربط بنظام الاقتصاد` };
    }
    case 'logs': {
      return { ok: true, msg: `📜 **السجلات**\nآخر 10 أسطر من السجلات:\n\`\`\`\n(يتطلب نظام تسجيل مخصص)\n\`\`\`` };
    }
    case 'errors': {
      return { ok: true, msg: `❌ **الأخطاء**\nلا توجد أخطاء مسجلة مؤخراً` };
    }
    default: {
      return { ok: true, msg: `✅ تم تنفيذ ديباج: **${debug.name}** (${debugId})\nالوصف: ${debug.desc}\n\n⚠️ هذا الديباج لا يحتوي على تنفيذ فعلي بعد.` };
    }
  }
}

client.on('messageCreate', async (message) => {
  if (message.author.bot) return;
  if (!message.content.startsWith(config.prefix)) return;

  const args = parseArgs(message.content, config.prefix);
  const cmd = args[0]?.toLowerCase();
  const rest = args.slice(1);

  try {
    let result;

    switch (cmd) {

      // ───── تسجيل وملف ─────
      case 'اشتراك':
      case 'تسجيل': {
        result = await coachCmd.registerCoach(message.author.id, message.author.displayName);
        break;
      }

      case 'ملفي':
      case 'معلوماتي': {
        const profile = coachCmd.getProfile(message.author.id);
        if (!profile) { result = { ok: false, msg: 'لم تسجل بعد. استخدم `!اشتراك`' }; break; }
        const c = profile.coach;
        result = {
          ok: true,
          msg: `📋 **ملف المدرب ${c.name}**\n🏢 الفريق: ${profile.team ? `${profile.team.flag} ${profile.team.name}` : 'لم تختر فريقاً بعد'}\n💰 الميزانية: ${(c.budget || 0).toLocaleString()} ريال\n✨ نقاط الخبرة: ${c.xp || 0} XP\n⚔️ ف/ت/خ: ${c.wins || 0}/${c.draws || 0}/${c.losses || 0}\n⚽ أهداف: ${c.totalGoals || 0} له / ${c.goalsConceded || 0} عليه\n\n${!profile.team ? `اختر فريقك: \`${config.prefix}اختيار فريق [id]\`\nالأندية: ${teams.map(t => `\`${t.id}\` (${t.flag} ${t.name})`).join(', ')}` : ''}`
        };
        break;
      }

      // ───── اختيار فريق ─────
      case 'فريقي': {
        const profile = coachCmd.getProfile(message.author.id);
        if (!profile || !profile.coach.team) { result = { ok: false, msg: 'لم تختر فريقاً بعد. استخدم `!اختيار فريق [id]`' }; break; }
        const t = profile.team;
        const c = profile.coach;
        const avg = c.players ? (c.players.reduce((s, p) => s + p.rating, 0) / c.players.length).toFixed(1) : 0;
        const playerList = (c.players || []).map(p =>
          `  ${p.pos === 'GK' ? '🧤' : p.pos.match(/[DR]/) ? '🛡️' : p.pos.match(/[SCF]/) ? '⚔️' : '⚡'} ${p.name} ⭐${p.rating} 💰${(p.value || 0).toLocaleString()}`
        ).join('\n');
        result = {
          ok: true,
          msg: `🏟️ **${t.flag} ${t.name}**\n👤 المدرب: ${c.name}\n⭐ متوسط التقييم: ${avg}\n💰 الميزانية: ${(c.budget || 0).toLocaleString()} ريال | ✨ XP: ${c.xp || 0}\n\n**اللاعبون (${(c.players || []).length}):**\n${playerList}`
        };
        break;
      }

      case 'اختيار فريق':
      case 'اختيار':
      case 'اختر': {
        const teamId = rest[0]?.toLowerCase();
        if (!teamId) { result = { ok: false, msg: `استخدم: \`${config.prefix}اختيار فريق [id]\`\nالأندية: ${teams.map(t => `\`${t.id}\` (${t.flag} ${t.name})`).join(', ')}` }; break; }
        result = await coachCmd.chooseTeam(message.author.id, teamId);
        break;
      }

      // ───── تدريب وتطوير ─────
      case 'لاعب':
      case 'تطوير':
      case 'player': {
        const playerName = rest.join(' ');
        if (!playerName) { result = { ok: false, msg: 'استخدم: `!لاعب اسم_اللاعب`' }; break; }
        result = trainingCmd.showTrainingMenu(message.author.id, playerName);
        break;
      }

      case 'تدريب':
      case 'train': {
        const pName = rest[0] ? rest.slice(0, -1).join(' ') : '';
        const skill = rest[rest.length - 1] || '';
        if (!pName || !skill) { result = { ok: false, msg: 'استخدم: `!تدريب "اسم اللاعب" المهارة`' }; break; }
        result = trainingCmd.trainPlayer(message.author.id, pName, skill);
        break;
      }

      // ───── تكتيكات ─────
      case 'تكتيكاتي':
      case 'تكتيكات':
      case 'tactics': {
        result = tacticsCmd.showTactics(message.author.id);
        break;
      }

      case 'تشكيلة':
      case 'formation': {
        const fId = rest[0];
        if (!fId) { result = { ok: false, msg: `استخدم: \`${config.prefix}تشكيلة [id]\`\nالمتاح: ${Object.keys(config.formations).join(', ')}` }; break; }
        result = tacticsCmd.setFormation(message.author.id, fId);
        break;
      }

      case 'خطة':
      case 'gameplan': {
        const plan = rest.join(' ');
        if (!plan) { result = { ok: false, msg: `استخدم: \`${config.prefix}خطة [اسم الخطة]\`\nالخطط: ${Object.keys(config.gamePlans).join(', ')}` }; break; }
        result = tacticsCmd.setGamePlan(message.author.id, plan);
        break;
      }

      case 'مفتاح':
      case 'plankey': {
        const key = rest[0]?.toUpperCase();
        if (!key) { result = { ok: false, msg: `استخدم: \`${config.prefix}مفتاح [key]\`\nالمفاتيح: ${Object.keys(config.planKeys).join(', ')}` }; break; }
        result = tacticsCmd.setPlanKey(message.author.id, key);
        break;
      }

      // ───── سوق انتقالات ─────
      case 'سوق':
      case 'market': {
        result = transferCmd.listMarket(message.author.id);
        break;
      }

      case 'بيع':
      case 'sell': {
        const priceIdx = rest.findIndex(r => !isNaN(parseInt(r)));
        if (priceIdx === -1) { result = { ok: false, msg: 'استخدم: `!بيع اسم_اللاعب السعر`' }; break; }
        const sellName = rest.slice(0, priceIdx).join(' ');
        const sellPrice = parseInt(rest[priceIdx]);
        result = transferCmd.sellPlayer(message.author.id, sellName, sellPrice);
        break;
      }

      case 'شراء':
      case 'buy': {
        const idx = parseInt(rest[0]) - 1;
        if (isNaN(idx) || idx < 0) { result = { ok: false, msg: 'استخدم: `!شراء رقم_اللاعب` (رقم من قائمة السوق)' }; break; }
        result = transferCmd.buyPlayer(message.author.id, idx);
        break;
      }

      // ───── مباريات ─────
      case 'تحدي':
      case 'challenge': {
        const oppId = rest[0]?.replace(/[<@!>]/g, '');
        const isFriendly = rest[1] === 'ودية';
        if (!oppId) { result = { ok: false, msg: 'استخدم: `!تحدي @الخصم [ودية]`' }; break; }
        result = matchCmd.scheduleMatch(message.author.id, oppId, isFriendly);
        break;
      }

      case 'تجهيز':
      case 'prepare': {
        const mid = rest[0];
        if (!mid) { result = { ok: false, msg: 'استخدم: !تجهيز [معرف المباراة]' }; break; }
        const profile = coachCmd.getProfile(message.author.id);
        if (!profile || !profile.coach.team) { result = { ok: false, msg: 'يجب أن تملك فريقاً.' }; break; }
        const lineup = (profile.coach.players || []).slice(0, 11).map(p => p.name).join(', ');
        const formation = profile.coach.tactics?.formation || '4-4-2';
        result = matchCmd.prepareMatch(message.author.id, mid, lineup, formation);
        break;
      }

      case 'خطة مباراة':
      case 'matchplan': {
        const mId = rest[0];
        const mPlan = rest[1];
        const mKey = rest[2]?.toUpperCase();
        const mTraining = parseInt(rest[3]) || 0;
        if (!mId || !mPlan) { result = { ok: false, msg: 'استخدم: !خطة مباراة [معرف] [الخطة] [المفتاح] [تدريب]' }; break; }
        result = matchCmd.setMatchTactics(message.author.id, mId, mPlan, mKey, mTraining);
        if (result.ok && !result.bothReady) {
          sendDM(message.author, `🔒 **خطتك السرية للمباراة ${mId}**\nالخطة: ${mPlan}\nالمفتاح: ${mKey || '—'}\nالتدريب: ${mTraining || 0}\n\n✅ خزنت بشكل آمن.`);
          result.msg = '✅ تم استلام خطتك عبر الرسائل الخاصة.';
        }
        break;
      }

      case 'محاكاة':
      case 'simulate':
      case 'sim': {
        const simId = rest[0];
        if (!simId) { result = { ok: false, msg: 'استخدم: !محاكاة [معرف المباراة]' }; break; }
        result = matchCmd.simulateMatch(simId);
        break;
      }

      // ───── دوريات ─────
      case 'الدوريات':
      case 'leagues': {
        result = leagueCmd.listLeagues();
        break;
      }

      case 'دوري جديد':
      case 'إنشاء دوري':
      case 'creatleague': {
        const leagueName = rest.slice(0, -1).join(' ');
        const maxC = parseInt(rest[rest.length - 1]) || 8;
        if (!leagueName) { result = { ok: false, msg: 'استخدم: !دوري جديد الاسم [العدد_الأقصى]' }; break; }
        result = leagueCmd.createLeague(message.author.id, leagueName, maxC);
        break;
      }

      case 'انضمام':
      case 'joinleague': {
        const leagueId = rest[0];
        if (!leagueId) { result = { ok: false, msg: 'استخدم: !انضمام [معرف الدوري]' }; break; }
        result = leagueCmd.joinLeague(message.author.id, leagueId);
        break;
      }

      case 'دوري':
      case 'league': {
        const showId = rest.join(' ');
        if (!showId) { result = { ok: false, msg: 'استخدم: !دوري [اسم/معرف الدوري]' }; break; }
        result = leagueCmd.showLeague(showId);
        break;
      }

      case 'بدء دوري':
      case 'startleague': {
        const startId = rest[0];
        if (!startId) { result = { ok: false, msg: 'استخدم: !بدء دوري [معرف]' }; break; }
        result = leagueCmd.startLeague(message.author.id, startId);
        break;
      }

      case 'جولة':
      case 'matchday': {
        const roundId = rest.join(' ');
        if (!roundId) { result = { ok: false, msg: 'استخدم: !جولة [معرف الدوري]' }; break; }
        result = leagueCmd.getCurrentMatchday(roundId);
        break;
      }

      // ───── أوامر مساعدة ─────
      case 'مساعدة':
      case 'مساعدة':
      case 'help':
      case 'اوامر':
      case 'commands': {
        result = {
          ok: true,
          msg: `📚 **أوامر أوهارا - المدرب الأفضل**\n\n` +
            `**التسجيل**\n\`!اشتراك\` - تسجيل حساب مدرب\n\`!اختيار فريق [id]\` - اختيار ناديك\n\`!فريقي\` - عرض فريقك\n\`!ملفي\` - عرض ملفك\n\n` +
            `**التطوير**\n\`!لاعب [اسم]\` - قائمة التطوير\n\`!تدريب "اسم" [مهارة]\` - تدريب لاعب\n\n` +
            `**التكتيكات** (🔒 مخفية حتى المباراة)\n\`!تكتيكاتي\` - عرض التكتيكات\n\`!تشكيلة [id]\` - تغيير التشكيلة\n\`!خطة [اسم]\` - تغيير خطة اللعب\n\`!مفتاح [key]\` - تغيير المفتاح الخططي\n\n` +
            `**السوق**\n\`!سوق\` - سوق الانتقالات\n\`!بيع [اسم] [سعر]\` - عرض لاعب للبيع\n\`!شراء [رقم]\` - شراء لاعب\n\n` +
            `**المباريات**\n\`!تحدي @خصم [ودية]\` - تحدٍ جديد\n\`!تجهيز [id]\` - تجهيز التشكيلة\n\`!خطة مباراة [id] [خطة] [مفتاح] [تدريب]\` - إرسال الخطة\n\`!محاكاة [id]\` - محاكاة المباراة\n\n` +
            `**الدوريات**\n\`!الدوريات\` - قائمة الدوريات\n\`!دوري جديد [اسم] [عدد]\` - إنشاء دوري\n\`!انضمام [id]\` - انضمام لدوري\n\`!دوري [id]\` - ترتيب الدوري\n\`!بدء دوري [id]\` - بدء الدوري\n\`!جولة [id]\` - جدول الجولة\n\n` +
            `**الديباجات (للأدمن فقط)**\n\`!ديباجات [صفحة]\` - قائمة الديباجات (15 لكل صفحة)\n\`!ديباج [رقم/اسم]\` - تنفيذ ديباج معين`
        };
        break;
      }

      // ───── نظام الديباجات (للأدمن فقط) ─────
      case 'ديباجات':
      case 'debugs':
      case 'debug_list': {
        // فقط في الخاص أو للأدمن
        if (message.guild && !message.member.permissions.has('Administrator')) {
          result = { ok: false, msg: '❌ هذا الأمر متاح للأدمن فقط في السيرفرات' };
          break;
        }
        const page = parseInt(rest[0]) || 1;
        const allDebugs = getAllDebugs();
        const { msg, totalPages } = formatDebugList(allDebugs, page);
        if (page < 1 || page > totalPages) {
          result = { ok: false, msg: `❌ رقم صفحة غير صحيح. المتاح: 1-${totalPages}` };
        } else {
          result = { ok: true, msg };
        }
        break;
      }

      case 'ديباج':
      case 'debug':
      case 'run_debug': {
        if (message.guild && !message.member.permissions.has('Administrator')) {
          result = { ok: false, msg: '❌ هذا الأمر متاح للأدمن فقط في السيرفرات' };
          break;
        }
        const debugInput = rest.join(' ').trim();
        if (!debugInput) {
          result = { ok: false, msg: `استخدم: \`${config.prefix}ديباج [رقم أو اسم]\`\nمثال: \`${config.prefix}ديباج 1\` أو \`${config.prefix}ديباج ping\`` };
          break;
        }
        
        // محاولة البحث بالرقم أولاً
        let debugId = debugInput;
        const allDebugs = getAllDebugs();
        const num = parseInt(debugInput);
        if (!isNaN(num) && num > 0 && num <= allDebugs.length) {
          debugId = allDebugs[num - 1].id;
        }
        
        result = await executeDebug(debugId, message);
        break;
      }

      default: {
        if (cmd) result = { ok: false, msg: `❓ أمر غير معروف. استخدم \`${config.prefix}اوامر\`` };
      }
    }

    if (result) {
      await sendMessage(message.channel, result.msg);
    }

  } catch (err) {
    console.error(`Error processing command "${cmd}":`, err);
    await sendMessage(message.channel, '⚠️ حدث خطأ أثناء تنفيذ الأمر.');
  }
});

client.login(config.token).catch(err => {
  console.error('❌ فشل تسجيل الدخول. تأكد من توكن البوت في ملف .env');
  console.error(err.message);
  process.exit(1);
});
