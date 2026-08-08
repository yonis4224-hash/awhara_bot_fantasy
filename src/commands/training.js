const { getStore, saveStore } = require('../store');
const { teams } = require('../data/teams');
const { calculatePlayerValue } = require('../data/teams');

const TRAINING_COST_XP = {
  physique: 100,
  technique: 150,
  tactics: 80,
  speed: 200,
  stamina: 120,
};

function getTrainingLevels() {
  return [
    { id: 'physique', name: 'اللياقة البدنية', desc: 'يزيد القوة والتحمل', max: 5, costPer: TRAINING_COST_XP.physique },
    { id: 'technique', name: 'المهارات الفنية', desc: 'يزيد التمرير والتحكم بالكرة', max: 5, costPer: TRAINING_COST_XP.technique },
    { id: 'tactics', name: 'التكتيك', desc: 'يزيد الذكاء الخططي', max: 5, costPer: TRAINING_COST_XP.tactics },
    { id: 'speed', name: 'السرعة', desc: 'يزيد السرعة والمراوغة', max: 5, costPer: TRAINING_COST_XP.speed },
    { id: 'stamina', name: 'التحمل', desc: 'يزيد القدرة على اللعب لكامل المباراة', max: 5, costPer: TRAINING_COST_XP.stamina },
  ];
}

function showTrainingMenu(userId, playerName) {
  const store = getStore();
  const coach = store.coaches[userId];
  if (!coach || !coach.team) return { ok: false, msg: 'يجب أن تمتلك فريقاً أولاً!' };

  const player = coach.players.find(p => p.name === playerName || p.name.includes(playerName));
  if (!player) return { ok: false, msg: `لم أجد لاعباً باسم "${playerName}" في فريقك.` };

  const levels = getTrainingLevels();
  const lines = levels.map(l => {
    const current = player.trainingLevels ? (player.trainingLevels[l.id] || 0) : 0;
    const status = current >= l.max ? '🚫 مكتمل' : `${current}/${l.max} - التكلفة: ${l.costPer} XP`;
    return `**${l.name}** (${l.desc})\n▶ المستوى: ${status}`;
  });

  return {
    ok: true,
    msg: `⚽ **تطوير اللاعب: ${player.name}**\nالتقييم الحالي: ⭐ ${player.rating}\nنقاط الخبرة المتوفرة: ${coach.xp} XP\n\n${lines.join('\n\n')}\n\n📌 استخدم الأمر:\n\`!تدريب "${playerName}" المهارات الفنية\`\nلاستبدال "المهارات الفنية" بأي من المهارات أعلاه.`
  };
}

function trainPlayer(userId, playerName, skillType) {
  const store = getStore();
  const coach = store.coaches[userId];
  if (!coach || !coach.team) return { ok: false, msg: 'يجب أن تمتلك فريقاً أولاً!' };

  const player = coach.players.find(p => p.name === playerName || p.name.includes(playerName));
  if (!player) return { ok: false, msg: `لم أجد لاعباً باسم "${playerName}" في فريقك.` };

  const level = getTrainingLevels().find(l => l.name === skillType || l.id === skillType);
  if (!level) return { ok: false, msg: `نوع التدريب "${skillType}" غير موجود. استخدم الأمر \`!لاعب ${playerName}\` لمشاهدة الخيارات.` };

  if (!player.trainingLevels) player.trainingLevels = {};
  const currentLevel = player.trainingLevels[level.id] || 0;

  if (currentLevel >= level.max) return { ok: false, msg: `🚫 اللاعب ${player.name} وصل للحد الأقصى في "${level.name}".` };

  const cost = level.costPer;
  if (coach.xp < cost) return { ok: false, msg: `💰 ليس لديك نقاط خبرة كافية! تحتاج ${cost} XP ولديك ${coach.xp} XP فقط.` };

  coach.xp -= cost;
  player.trainingLevels[level.id] = currentLevel + 1;

  const ratingBoost = 1;
  player.rating += ratingBoost;
  player.baseRating += ratingBoost;

  const newValue = calculatePlayerValue(player.rating, player.potential, player.age);
  player.value = newValue;

  saveStore(store);
  return {
    ok: true,
    msg: `✅ **تدريب ناجح!**\nاللاعب ${player.name} أكمل المستوى ${currentLevel + 1} في "${level.name}"\nالتقييم ارتفع إلى ⭐ ${player.rating}\nالقيمة السوقية الجديدة: 💰 ${newValue.toLocaleString()} ريال\nنقاط الخبرة المتبقية: ${coach.xp} XP`
  };
}

function getTeamRating(players) {
  if (!players || players.length === 0) return 0;
  const sum = players.reduce((acc, p) => acc + p.rating, 0);
  return Math.round(sum / players.length * 10) / 10;
}

module.exports = { showTrainingMenu, trainPlayer, getTeamRating, getTrainingLevels, TRAINING_COST_XP };
