const { getStore, saveStore } = require('../store');
const { teams } = require('../data/teams');
const config = require('../config');

async function registerCoach(userId, username) {
  const store = getStore();
  if (store.coaches[userId]) {
    return { ok: false, msg: 'أنت مسجل بالفعل كمدرب! استخدم الأمر !ملفي' };
  }

  store.coaches[userId] = {
    id: userId,
    name: username,
    team: null,
    budget: config.startingBudget,
    xp: 0,
    wins: 0,
    draws: 0,
    losses: 0,
    totalGoals: 0,
    goalsConceded: 0,
    joinDate: Date.now(),
  };
  saveStore(store);
  return { ok: true, msg: `🎉 مرحباً أيها المدرب **${username}**! تم تسجيلك بنجاح.\nاستخدم الأمر \`${config.prefix}اختيار فريق\` لاختيار ناديك المفضل.` };
}

async function chooseTeam(userId, teamId) {
  const store = getStore();
  const coach = store.coaches[userId];
  if (!coach) return { ok: false, msg: 'يجب تسجيلك أولاً. استخدم الأمر !اشتراك' };
  if (coach.team) return { ok: false, msg: `لديك فريق بالفعل: **${coach.team}**!` };

  const team = teams.find(t => t.id === teamId);
  if (!team) return { ok: false, msg: 'هذا الفريق غير موجود. الفرق المتاحة: ' + teams.map(t => `\`${t.id}\` (${t.name})`).join(', ') };

  const taken = Object.values(store.coaches).some(c => c.team === teamId);
  if (taken) return { ok: false, msg: `فريق **${team.name}** تم اختياره بالفعل بواسطة مدرب آخر!` };

  coach.team = teamId;
  coach.players = team.players.map(p => ({
    ...p,
    baseRating: p.rating,
    trainingPoints: 0,
    form: 7.0,
  }));
  saveStore(store);
  return { ok: true, msg: `✅ اخترت فريق **${team.flag} ${team.name}**!\nالميزانية: 💰 ${coach.budget.toLocaleString()} ريال\nعدد اللاعبين: ${coach.players.length}\nاستخدم \`${config.prefix}فريقي\` لعرض التفاصيل.` };
}

function getProfile(userId) {
  const store = getStore();
  const coach = store.coaches[userId];
  if (!coach) return null;

  const team = coach.team ? teams.find(t => t.id === coach.team) : null;
  return { coach, team };
}

function getAvatar(userId) {
  const store = getStore();
  const coach = store.coaches[userId];
  if (!coach) return null;
  return coach;
}

function getAllCoaches() {
  const store = getStore();
  return Object.values(store.coaches);
}

module.exports = { registerCoach, chooseTeam, getProfile, getAllCoaches };
