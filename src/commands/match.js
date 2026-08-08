const { getStore, saveStore, getMatchesStore, saveMatchesStore } = require('../store');
const { getFormationModifier, getPlanModifier } = require('./tactics');
const { getTeamRating } = require('./training');
const config = require('../config');

function scheduleMatch(userId, opponentId, isFriendly) {
  const store = getStore();
  const coach = store.coaches[userId];
  const opponent = store.coaches[opponentId];

  if (!coach || !coach.team) return { ok: false, msg: 'أنت لا تملك فريقاً!' };
  if (!opponent || !opponent.team) return { ok: false, msg: 'الخصم لا يملك فريقاً!' };
  if (userId === opponentId) return { ok: false, msg: 'لا يمكنك لعب مباراة مع نفسك!' };

  const matchesStore = getMatchesStore();
  const match = {
    id: `m_${Date.now()}`,
    homeId: userId,
    awayId: opponentId,
    isFriendly: !!isFriendly,
    status: 'pending_setup',
    homeSetup: null,
    awaySetup: null,
    homeTactics: null,
    awayTactics: null,
    createdAt: Date.now(),
  };
  matchesStore.matches.push(match);
  saveMatchesStore(matchesStore);

  const oppName = opponent.name || `<@${opponentId}>`;
  return {
    ok: true,
    msg: `⚔️ **مباراة جديدة!**\n🆚 <@${userId}> vs ${oppName}\n\nالمرحلة 1: تجهيز التشكيلة\nكلا المدربين يستخدم الأمر:\n\`!تجهيز ${match.id}\`\nلإرسال تشكيلته للتقييم.\n📌 كل مدرب يرى فقط تشكيلته (السرية مضمونة).\n\nبعد تجهيز الطرفين، سيتم إعلامكما لاختيار الخطط.`
  };
}

function prepareMatch(userId, matchId, lineup, formation) {
  const matchesStore = getMatchesStore();
  const match = matchesStore.matches.find(m => m.id === matchId);
  if (!match) return { ok: false, msg: 'المباراة غير موجودة.' };
  if (match.status !== 'pending_setup') return { ok: false, msg: 'هذه المباراة ليس في مرحلة التجهيز.' };

  const isHome = match.homeId === userId;
  const isAway = match.awayId === userId;
  if (!isHome && !isAway) return { ok: false, msg: 'هذه المباراة ليست لك.' };

  const key = isHome ? 'homeSetup' : 'awaySetup';
  match[key] = { lineup, formation };

  const bothReady = match.homeSetup && match.awaySetup;
  if (bothReady) {
    match.status = 'pending_tactics';

    const homeCoach = `<@${match.homeId}>`;
    const awayCoach = `<@${match.awayId}>`;

    saveMatchesStore(matchesStore);
    return {
      ok: true,
      msg: `✅ **تم تجهيز التشكيلتين!**\n\nالمرحلة 2: اختيار الخطط\n${homeCoach} استخدم:\n\`!خطة مباراة ${match.id} هجومي A2\`\n${awayCoach} استخدم:\n\`!خطة مباراة ${match.id} دفاعي B1\`\n\n🔒 ملاحظة: كل مدخل خطة يتم إرساله بشكل خاص (DM) للبوت.\n🔄 بعد إرسال الخطة، يمكنك تغييرها بنفس الأمر حتى انتهاء الوقت.`,
      bothReady: true
    };
  }

  saveMatchesStore(matchesStore);
  return { ok: true, msg: '✅ تم استلام تشكيلتك. في انتظار المدرب الآخر.' };
}

function setMatchTactics(userId, matchId, gamePlan, planKey, trainingBoost) {
  const matchesStore = getMatchesStore();
  const match = matchesStore.matches.find(m => m.id === matchId);
  if (!match) return { ok: false, msg: 'المباراة غير موجودة.' };
  if (match.status !== 'pending_tactics') return { ok: false, msg: 'هذه المباراة ليست في مرحلة اختيار الخطط.' };

  const isHome = match.homeId === userId;
  const isAway = match.awayId === userId;
  if (!isHome && !isAway) return { ok: false, msg: 'هذه المباراة ليست لك.' };

  const key = isHome ? 'homeTactics' : 'awayTactics';
  match[key] = { gamePlan, planKey, trainingBoost: trainingBoost || 0 };

  const ready = match.homeTactics && match.awayTactics;
  if (ready) {
    match.status = 'ready';
    saveMatchesStore(matchesStore);
    return { ok: true, msg: '✅ تم استلام خطط الطرفين! المباراة جاهزة للمحاكاة.', bothReady: true, matchId };
  }

  saveMatchesStore(matchesStore);
  return { ok: true, msg: '✅ تم استلام خطتك. في انتظار المدرب الآخر.' };
}

function simulateMatch(matchId) {
  const matchesStore = getMatchesStore();
  const match = matchesStore.matches.find(m => m.id === matchId);
  if (!match) return { ok: false, msg: 'المباراة غير موجودة.' };
  if (match.status !== 'ready') return { ok: false, msg: 'المباراة ليست جاهزة.' };

  const store = getStore();
  const homeCoach = store.coaches[match.homeId];
  const awayCoach = store.coaches[match.awayId];
  if (!homeCoach || !awayCoach) return { ok: false, msg: 'أحد المدربين غير موجود.' };

  const homePlayers = homeCoach.players || [];
  const awayPlayers = awayCoach.players || [];

  const homeAvg = getTeamRating(homePlayers);
  const awayAvg = getTeamRating(awayPlayers);

  const homeTac = match.homeTactics || { gamePlan: 'استحواذ', planKey: 'A1', trainingBoost: 0 };
  const awayTac = match.awayTactics || { gamePlan: 'استحواذ', planKey: 'A1', trainingBoost: 0 };
  const homeForm = match.homeSetup?.formation || '4-4-2';
  const awayForm = match.awaySetup?.formation || '4-4-2';

  let homeStrength = homeAvg;
  let awayStrength = awayAvg;

  homeStrength += homeTac.trainingBoost || 0;
  awayStrength += awayTac.trainingBoost || 0;

  const formMod = getFormationModifier(homeForm, awayForm);
  homeStrength += formMod * 5;
  awayStrength -= formMod * 3;

  const planMod = getPlanModifier(homeTac.gamePlan, awayTac.gamePlan, homeTac.planKey, awayTac.planKey);
  homeStrength += (planMod.atk || 0) * 5;
  homeStrength -= (planMod.def || 0) * 3;
  awayStrength += (planMod.def || 0) * 3;
  awayStrength -= (planMod.atk || 0) * 5;

  const homeDefPlayers = homePlayers.filter(p => ['GK', 'CB', 'RB', 'LB', 'CDM'].includes(p.pos));
  const awayDefPlayers = awayPlayers.filter(p => ['GK', 'CB', 'RB', 'LB', 'CDM'].includes(p.pos));
  const homeMidPlayers = homePlayers.filter(p => ['CM', 'CDM', 'AM'].includes(p.pos));
  const awayMidPlayers = awayPlayers.filter(p => ['CM', 'CDM', 'AM'].includes(p.pos));
  const homeAtkPlayers = homePlayers.filter(p => ['ST', 'LW', 'RW', 'CF'].includes(p.pos));
  const awayAtkPlayers = awayPlayers.filter(p => ['ST', 'LW', 'RW', 'CF'].includes(p.pos));

  const defHome = homeDefPlayers.reduce((s, p) => s + p.rating, 0) / Math.max(homeDefPlayers.length, 1);
  const defAway = awayDefPlayers.reduce((s, p) => s + p.rating, 0) / Math.max(awayDefPlayers.length, 1);
  const midHome = homeMidPlayers.reduce((s, p) => s + p.rating, 0) / Math.max(homeMidPlayers.length, 1);
  const midAway = awayMidPlayers.reduce((s, p) => s + p.rating, 0) / Math.max(awayMidPlayers.length, 1);
  const atkHome = homeAtkPlayers.reduce((s, p) => s + p.rating, 0) / Math.max(homeAtkPlayers.length, 1);
  const atkAway = awayAtkPlayers.reduce((s, p) => s + p.rating, 0) / Math.max(awayAtkPlayers.length, 1);

  const gpHomeConfig = match.homeTactics?.gamePlan;
  const gpAwayConfig = match.awayTactics?.gamePlan;

  let attackBonus = 0, defendBonus = 0;
  if (gpHomeConfig === 'هجومي') { attackBonus = 0.15; defendBonus = -0.10; }
  else if (gpHomeConfig === 'دفاعي') { defendBonus = 0.15; attackBonus = -0.08; }
  else if (gpHomeConfig === 'مرتد') { attackBonus = 0.05; defendBonus = 0.05; }

  if (gpAwayConfig === 'هجومي') { attackBonus -= 0.10; }
  else if (gpAwayConfig === 'دفاعي') { attackBonus += 0.05; }
  else if (gpAwayConfig === 'مرتد') { attackBonus -= 0.03; }

  let homeScoreChance = (atkHome + attackBonus * 8) / (defAway + 10) + (homeStrength - awayStrength) / 20;
  let awayScoreChance = (atkAway - attackBonus * 6) / (defHome + 10) + (awayStrength - homeStrength) / 20;

  const homeKey = config.planKeys[match.homeTactics?.planKey];
  const awayKey = config.planKeys[match.awayTactics?.planKey];
  if (homeKey) {
    if (homeKey.counters?.includes(match.awayTactics?.planKey)) homeScoreChance += 0.2;
    if (homeKey.weakTo?.includes(match.awayTactics?.planKey)) homeScoreChance -= 0.15;
  }
  if (awayKey) {
    if (awayKey.counters?.includes(match.homeTactics?.planKey)) awayScoreChance += 0.2;
    if (awayKey.weakTo?.includes(match.homeTactics?.planKey)) awayScoreChance -= 0.15;
  }

  const homeTrained = (match.homeTactics?.trainingBoost || 0) > 3;
  const awayTrained = (match.awayTactics?.trainingBoost || 0) > 3;
  if (homeTrained && !awayTrained) homeScoreChance += 0.15;
  if (awayTrained && !homeTrained) awayScoreChance += 0.15;

  if (gpHomeConfig === 'هجومي' && defHome < 78) homeScoreChance -= 0.25;
  if (gpHomeConfig === 'دفاعي' && atkHome > 83) homeScoreChance -= 0.1;
  if (gpAwayConfig === 'هجومي' && defAway < 78) awayScoreChance -= 0.25;
  if (gpAwayConfig === 'دفاعي' && atkAway > 83) awayScoreChance -= 0.1;

  const upsetFactor = (Math.random() * 0.3) - 0.15;
  homeScoreChance += upsetFactor;
  awayScoreChance -= upsetFactor;

  const total = Math.abs(homeScoreChance) + Math.abs(awayScoreChance);
  const homeProb = total > 0 ? Math.abs(homeScoreChance) / total : 0.5;
  const awayProb = total > 0 ? Math.abs(awayScoreChance) / total : 0.5;

  const avgGoals = 2.5;
  const lambdaHome = avgGoals * homeProb;
  const lambdaAway = avgGoals * awayProb;

  function poisson(lambda) {
    if (lambda <= 0) return 0;
    const L = Math.exp(-lambda);
    let k = 0;
    let p = 1;
    do { k++; p *= Math.random(); } while (p > L);
    return Math.min(k - 1, 8);
  }

  let homeGoals = poisson(lambdaHome);
  let awayGoals = poisson(lambdaAway);

  const homePlayersArr = homeCoach.players || [];
  const awayPlayersArr = awayCoach.players || [];

  const homeScorers = homeGoals > 0 ? generateScorers(homePlayersArr, homeGoals) : [];
  const awayScorers = awayGoals > 0 ? generateScorers(awayPlayersArr, awayGoals) : [];

  const teamShortHome = homeCoach.team ? (homeCoach.team.length > 12 ? homeCoach.team.slice(0, 12) + '...' : homeCoach.team) : '???';
  const teamShortAway = awayCoach.team ? (awayCoach.team.length > 12 ? awayCoach.team.slice(0, 12) + '...' : awayCoach.team) : '???';

  const homeName = `<@${match.homeId}> (${teamShortHome})`;
  const awayName = `<@${match.awayId}> (${teamShortAway})`;

  let result;
  if (homeGoals > awayGoals) {
    result = 'home';
    homeCoach.wins = (homeCoach.wins || 0) + 1;
    awayCoach.losses = (awayCoach.losses || 0) + 1;
  } else if (awayGoals > homeGoals) {
    result = 'away';
    awayCoach.wins = (awayCoach.wins || 0) + 1;
    homeCoach.losses = (homeCoach.losses || 0) + 1;
  } else {
    result = 'draw';
    homeCoach.draws = (homeCoach.draws || 0) + 1;
    awayCoach.draws = (awayCoach.draws || 0) + 1;
  }

  homeCoach.totalGoals = (homeCoach.totalGoals || 0) + homeGoals;
  homeCoach.goalsConceded = (homeCoach.goalsConceded || 0) + awayGoals;
  awayCoach.totalGoals = (awayCoach.totalGoals || 0) + awayGoals;
  awayCoach.goalsConceded = (awayCoach.goalsConceded || 0) + homeGoals;

  const xpEarned = Math.round(10 + homeGoals * 2 + (homeGoals === awayGoals ? 5 : homeGoals > awayGoals ? 10 : 0));
  const oppXpEarned = Math.round(10 + awayGoals * 2 + (homeGoals === awayGoals ? 5 : awayGoals > homeGoals ? 10 : 0));
  homeCoach.xp = (homeCoach.xp || 0) + xpEarned;
  awayCoach.xp = (awayCoach.xp || 0) + oppXpEarned;

  if (!match.isFriendly) {
    homeCoach.budget = (homeCoach.budget || 0) + (homeGoals > awayGoals ? 5000000 : homeGoals === awayGoals ? 2000000 : 1000000);
    awayCoach.budget = (awayCoach.budget || 0) + (awayGoals > homeGoals ? 5000000 : homeGoals === awayGoals ? 2000000 : 1000000);
  }

  const commentary = generateCommentary(homeGoals, awayGoals, homeScorers, awayScorers, homePlayersArr, awayPlayersArr);

  match.status = 'completed';
  match.result = { homeGoals, awayGoals, homeScorers, awayScorers, commentary };
  saveStore(store);
  saveMatchesStore(matchesStore);

  return {
    ok: true,
    msg: `⚽ **نتيجة المباراة**\n\n${homeName} ${homeGoals} - ${awayGoals} ${awayName}\n\n━━━━━━━━━━━━━━━━\n\n${commentary}\n\n━━━━━━━━━━━━━━━━\n🎯 **الأهداف**\n${homeGoals > 0 ? `🏠 **${homeName}**: ${homeScorers.join(', ') || '—'}` : ''}\n${awayGoals > 0 ? `✈️ **${awayName}**: ${awayScorers.join(', ') || '—'}` : ''}\n\n━━━━━━━━━━━━━━━━\n📊 **الإحصائيات**\nمتوسط تقييم المنزل: ⭐${homeAvg.toFixed(1)}\nمتوسط تقييم الضيف: ⭐${awayAvg.toFixed(1)}\nالتكتيك المنزلي: ${match.homeTactics?.gamePlan || '—'} | مفتاح: ${match.homeTactics?.planKey || '—'}\nالتكتيك الضيف: ${match.awayTactics?.gamePlan || '—'} | مفتاح: ${match.awayTactics?.planKey || '—'}\n\n💰 الجائزة: ${match.isFriendly ? 'مباراة ودية (لا جوائز مالية)' : `${homeGoals > awayGoals ? '<@' + match.homeId + '> يحصل على 5,000,000 ريال' : homeGoals === awayGoals ? 'كل مدرب يحصل على 2,000,000 ريال' : '<@' + match.awayId + '> يحصل على 5,000,000 ريال'}`}\n✨ XP: +${xpEarned} للمنزل | +${oppXpEarned} للضيف`
  };
}

function generateScorers(players, goals) {
  const forwards = players.filter(p => ['ST', 'LW', 'RW', 'CF', 'AM'].includes(p.pos));
  const mids = players.filter(p => ['CM', 'CDM'].includes(p.pos));
  const defs = players.filter(p => ['CB', 'RB', 'LB'].includes(p.pos));

  const scorers = [];
  for (let i = 0; i < goals; i++) {
    const pool = Math.random() < 0.7 ? forwards : Math.random() < 0.5 ? mids : defs;
    if (pool.length > 0) {
      const scorer = pool[Math.floor(Math.random() * pool.length)];
      const min = Math.floor(Math.random() * 90) + 1;
      scorers.push(`${scorer.name} ⚽ (${min}')`);
    }
  }
  return scorers;
}

function generateCommentary(hG, aG, hS, aS, hP, aP) {
  const events = [];
  for (let m = 0; m < 90; m += 5) {
    if (Math.random() < 0.2) {
      const team = Math.random() < 0.5 ? 'home' : 'away';
      const players = team === 'home' ? hP : aP;
      const p = players[Math.floor(Math.random() * players.length)];
      const actions = [
        `🔴 ${p.name} يحصل على بطاقة صفراء`,
        `⚡ ${p.name} يمرر كرة طويلة رائعة`,
        `🛑 ${p.name} يقطع هجمة خطيرة`,
        `🎯 تسديدة من ${p.name} لكنها تمر فوق المرمى`,
        `🏃 ${p.name} يركض خلف الدفاع لكن الحارس يخرج`,
        `🔄 تمريرة بينية من ${p.name}`,
        `💪 التحام قوي من ${p.name}`,
        `👟 كرة عرضية من ${p.name}`,
      ];
      events.push(`${m}' - ${actions[Math.floor(Math.random() * actions.length)]}`);
    }
  }
  return events.slice(0, 8).join('\n') || '⚽ مباراة هادئة بدون أحداث تذكر.';
}

module.exports = { scheduleMatch, prepareMatch, setMatchTactics, simulateMatch };
