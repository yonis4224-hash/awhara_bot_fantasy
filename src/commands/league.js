const { getStore, saveStore, getLeagues, saveLeagues } = require('../store');
const config = require('../config');

function createLeague(userId, name, maxCoaches) {
  const store = getStore();
  const coach = store.coaches[userId];
  if (!coach || !coach.team) return { ok: false, msg: 'يجب أن تمتلك فريقاً لإنشاء دوري.' };

  const leagues = getLeagues();
  if (leagues.leagues.some(l => l.name === name)) return { ok: false, msg: `دوري باسم "${name}" موجود بالفعل.` };

  const league = {
    id: `l_${Date.now()}`,
    name,
    ownerId: userId,
    maxCoaches: Math.min(Math.max(maxCoaches || 8, 4), 20),
    coaches: [{ id: userId, team: coach.team, joinedAt: Date.now() }],
    matches: [],
    status: 'open',
    createdAt: Date.now(),
    currentMatchday: 0,
  };
  leagues.leagues.push(league);
  saveLeagues(leagues);

  return { ok: true, msg: `🏆 **تم إنشاء الدوري "${name}"!**\nالحد الأقصى: ${league.maxCoaches} مدرب\nللدعوة: \`!انضمام ${league.id}\`` };
}

function joinLeague(userId, leagueId) {
  const store = getStore();
  const coach = store.coaches[userId];
  if (!coach || !coach.team) return { ok: false, msg: 'يجب أن تمتلك فريقاً للانضمام.' };

  const leagues = getLeagues();
  const league = leagues.leagues.find(l => l.id === leagueId);
  if (!league) return { ok: false, msg: 'الدوري غير موجود.' };
  if (league.status !== 'open') return { ok: false, msg: 'الدوري مغلق أو انتهى.' };
  if (league.coaches.some(c => c.id === userId)) return { ok: false, msg: 'أنت مسجل في هذا الدوري بالفعل.' };

  const teamTaken = league.coaches.some(c => c.team === coach.team);
  if (teamTaken) return { ok: false, msg: 'هذا الفريق موجود بالفعل في الدوري.' };

  if (league.coaches.length >= league.maxCoaches) return { ok: false, msg: 'الدوري مكتمل العدد.' };

  league.coaches.push({ id: userId, team: coach.team, joinedAt: Date.now() });
  saveLeagues(leagues);
  return { ok: true, msg: `✅ انضممت إلى الدوري **${league.name}**! (${league.coaches.length}/${league.maxCoaches} مدرب)` };
}

function listLeagues() {
  const leagues = getLeagues();
  if (leagues.leagues.length === 0) return { ok: false, msg: 'لا توجد دوريات حالياً. استخدم `!إنشاء دوري`.' };

  const lines = leagues.leagues.map(l =>
    `**${l.name}** - ${l.coaches.length}/${l.maxCoaches} مدرب - ${l.status === 'open' ? '🟢 مفتوح' : '🔴 مغلق'}\n🆔 \`${l.id}\``
  );
  return { ok: true, msg: `🏆 **الدوريات المتاحة**\n\n${lines.join('\n\n')}` };
}

function showLeague(leagueId) {
  const leagues = getLeagues();
  const league = leagues.leagues.find(l => l.id === leagueId || l.name.includes(leagueId));
  if (!league) return { ok: false, msg: 'الدوري غير موجود.' };

  const store = getStore();
  const standings = league.coaches.map(c => {
    const coach = store.coaches[c.id];
    return {
      id: c.id,
      team: c.team,
      name: coach ? coach.name : 'غير معروف',
      wins: coach?.wins || 0,
      draws: coach?.draws || 0,
      losses: coach?.losses || 0,
      goals: coach?.totalGoals || 0,
      conceded: coach?.goalsConceded || 0,
    };
  });

  standings.sort((a, b) => {
    const ptsA = a.wins * 3 + a.draws;
    const ptsB = b.wins * 3 + b.draws;
    if (ptsB !== ptsA) return ptsB - ptsA;
    const gdA = a.goals - a.conceded;
    const gdB = b.goals - b.conceded;
    return gdB - gdA;
  });

  const table = standings.map((s, i) => {
    const pts = s.wins * 3 + s.draws;
    const gd = s.goals - s.conceded;
    return `${i + 1}. **${s.team}** (${s.name}) | ${s.wins}ف ${s.draws}ت ${s.losses}خ | نقاط: ${pts} | +/-: ${gd > 0 ? '+' : ''}${gd}`;
  }).join('\n');

  return {
    ok: true,
    msg: `🏆 **${league.name}** - ترتيب الدوري\n\n${table}\n\n📅 الجولة: ${league.currentMatchday || 0}\n${league.status === 'open' ? '🔓 مفتوح للتسجيل' : '🔒 مغلق'}`,
    league
  };
}

function startLeague(userId, leagueId) {
  const leagues = getLeagues();
  const league = leagues.leagues.find(l => l.id === leagueId);
  if (!league) return { ok: false, msg: 'الدوري غير موجود.' };
  if (league.ownerId !== userId) return { ok: false, msg: 'فقط منشئ الدوري يمكنه بدء الدوري.' };
  if (league.status !== 'open') return { ok: false, msg: 'الدوري بدأ بالفعل.' };
  if (league.coaches.length < 4) return { ok: false, msg: 'يحتاج الدوري 4 مدربين على الأقل.' };

  league.status = 'active';
  const coachIds = league.coaches.map(c => c.id);
  const matchdays = [];
  const rounds = league.coaches.length - 1;
  const half = Math.floor(league.coaches.length / 2);

  for (let r = 0; r < rounds; r++) {
    const day = [];
    for (let i = 0; i < half; i++) {
      const home = coachIds[i];
      const away = coachIds[coachIds.length - 1 - i];
      day.push({ home, away, matchday: r + 1, played: false, homeGoals: null, awayGoals: null });
    }
    matchdays.push(...day);
    coachIds.splice(1, 0, coachIds.pop());
  }

  const returnLegs = matchdays.map(m => ({
    home: m.away,
    away: m.home,
    matchday: m.matchday + rounds,
    played: false,
    homeGoals: null,
    awayGoals: null,
  }));
  matchdays.push(...returnLegs);

  league.matches = matchdays;
  league.currentMatchday = 1;
  saveLeagues(leagues);

  return { ok: true, msg: `🏆 **بدأ الدوري "${league.name}"!**\nعدد المباريات: ${matchdays.length}\nعدد الجولات: ${rounds * 2}` };
}

function getCurrentMatchday(leagueId) {
  const leagues = getLeagues();
  const league = leagues.leagues.find(l => l.id === leagueId);
  if (!league || league.status !== 'active') return { ok: false, msg: 'الدوري غير نشط.' };

  const upcoming = league.matches.filter(m => m.matchday === league.currentMatchday && !m.played);
  const store = getStore();

  const lines = upcoming.map(m => {
    const homeCoach = store.coaches[m.home];
    const awayCoach = store.coaches[m.away];
    return `🆚 ${homeCoach?.team || '???'} (${m.home}) vs ${awayCoach?.team || '???'} (${m.away})`;
  });

  return {
    ok: true,
    msg: `📅 **${league.name}** - الجولة ${league.currentMatchday}\n\n${lines.join('\n') || 'لا توجد مباريات في هذه الجولة.'}`,
    matches: upcoming
  };
}

function recordLeagueMatch(leagueId, matchday, matchIdx, homeGoals, awayGoals) {
  const leagues = getLeagues();
  const league = leagues.leagues.find(l => l.id === leagueId);
  if (!league) return { ok: false, msg: 'الدوري غير موجود.' };

  const match = league.matches.find(m => m.matchday === matchday && !m.played);
  if (!match) return { ok: false, msg: 'لا توجد مباراة غير مُلعبة في هذه الجولة.' };

  match.played = true;
  match.homeGoals = homeGoals;
  match.awayGoals = awayGoals;

  const allPlayed = league.matches.filter(m => m.matchday === matchday).every(m => m.played);
  if (allPlayed) league.currentMatchday++;

  saveLeagues(leagues);
  return { ok: true, msg: '✅ تم تسجيل نتيجة المباراة.' };
}

module.exports = { createLeague, joinLeague, listLeagues, showLeague, startLeague, getCurrentMatchday, recordLeagueMatch };
