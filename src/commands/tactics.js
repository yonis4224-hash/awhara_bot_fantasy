const { getStore, saveStore } = require('../store');
const config = require('../config');

function showTactics(userId) {
  const store = getStore();
  const coach = store.coaches[userId];
  if (!coach || !coach.team) return { ok: false, msg: 'يجب أن تمتلك فريقاً أولاً!' };

  const tactics = coach.tactics || { formation: '4-4-2', gamePlan: 'استحواذ', planKey: 'A1' };

  const formations = Object.entries(config.formations).map(([key, val]) =>
    `\`${key}\` - ${val.desc}`
  ).join('\n');

  const plans = Object.entries(config.gamePlans).map(([key, val]) =>
    `\`${key}\` - ${val.desc}`
  ).join('\n');

  return {
    ok: true,
    msg: `📋 **التشكيلة والتكتيكات الحالية**\n\n**التشكيلة:** ${tactics.formation}\n**الخطة:** ${tactics.gamePlan}\n**المفتاح الخططي:** ${tactics.planKey} (🔒 مخفي عن الخصم)\n\n━━━━━━━━━━━━━━━━\n**التشكيلات المتاحة**\n${formations}\n━━━━━━━━━━━━━━━━\n**خطط اللعب**\n${plans}\n━━━━━━━━━━━━━━━━\n**لتغيير:**\n\`!تشكيلة 4-3-3\`\n\`!خطة دفاعي\`\n\`!مفتاح A1\``
  };
}

function setFormation(userId, formationId) {
  const store = getStore();
  const coach = store.coaches[userId];
  if (!coach || !coach.team) return { ok: false, msg: 'يجب أن تمتلك فريقاً أولاً!' };

  if (!config.formations[formationId]) return { ok: false, msg: `تشكيلة غير معروفة. التشكيلات المتاحة: ${Object.keys(config.formations).join(', ')}` };

  if (!coach.tactics) coach.tactics = { formation: '4-4-2', gamePlan: 'استحواذ', planKey: 'A1' };
  coach.tactics.formation = formationId;
  saveStore(store);
  return { ok: true, msg: `✅ تم تعيين التشكيلة إلى **${formationId}** - ${config.formations[formationId].desc}` };
}

function setGamePlan(userId, planId) {
  const store = getStore();
  const coach = store.coaches[userId];
  if (!coach || !coach.team) return { ok: false, msg: 'يجب أن تمتلك فريقاً أولاً!' };

  const planKey = Object.keys(config.gamePlans).find(k => k === planId || k.includes(planId));
  if (!planKey) return { ok: false, msg: `خطة غير معروفة. الخطط المتاحة: ${Object.keys(config.gamePlans).join(', ')}` };

  if (!coach.tactics) coach.tactics = { formation: '4-4-2', gamePlan: 'استحواذ', planKey: 'A1' };
  coach.tactics.gamePlan = planKey;
  saveStore(store);
  return { ok: true, msg: `✅ تم تعيين خطة اللعب إلى **${planKey}** - ${config.gamePlans[planKey].desc}` };
}

function setPlanKey(userId, keyId) {
  const store = getStore();
  const coach = store.coaches[userId];
  if (!coach || !coach.team) return { ok: false, msg: 'يجب أن تمتلك فريقاً أولاً!' };

  const upper = keyId.toUpperCase();
  if (!config.planKeys[upper]) return { ok: false, msg: `مفتاح غير معروف. المفاتيح المتاحة: ${Object.keys(config.planKeys).join(', ')}` };

  if (!coach.tactics) coach.tactics = { formation: '4-4-2', gamePlan: 'استحواذ', planKey: 'A1' };
  coach.tactics.planKey = upper;
  saveStore(store);
  return { ok: true, msg: `✅ تم تعيين المفتاح الخططي إلى **${upper}** (${config.planKeys[upper].name})\n🔒 هذا المفتاح سيكون مخفياً عن الخصم حتى المباراة.` };
}

function getFormationModifier(formationId, opponentFormation) {
  const f = config.formations[formationId];
  const of = config.formations[opponentFormation];
  if (!f || !of) return 0;

  let mod = 0;
  if (f.def > of.atk + 1) mod += 0.05;
  if (f.atk > of.def + 1) mod += 0.05;
  if (f.mid > of.mid + 1) mod += 0.03;
  if (f.mid < of.mid - 2) mod -= 0.05;
  return mod;
}

function getPlanModifier(gamePlan, opponentPlan, planKey, opponentKey) {
  const gp = config.gamePlans[gamePlan];
  const op = config.gamePlans[opponentPlan];
  if (!gp || !op) return { atk: 0, def: 0 };

  let atkMod = gp.atkBonus || 0;
  let defMod = gp.defBonus || 0;

  if (gp.style === 'attack' && op.style === 'defend') {
    atkMod -= 0.05;
  }
  if (gp.style === 'defend' && op.style === 'attack') {
    defMod += 0.05;
  }
  if (gp.style === 'counter' && op.style === 'possession') {
    atkMod += 0.05;
  }
  if (gp.style === 'possession' && op.style === 'counter') {
    defMod -= 0.05;
  }

  const pk = config.planKeys[planKey];
  const ok = config.planKeys[opponentKey];
  if (pk && ok) {
    if (pk.counters && pk.counters.includes(opponentKey)) {
      atkMod += 0.10;
    }
    if (pk.weakTo && pk.weakTo.includes(opponentKey)) {
      defMod -= 0.08;
    }
    if (ok.counters && ok.counters.includes(planKey)) {
      defMod -= 0.08;
    }
    if (ok.weakTo && ok.weakTo.includes(planKey)) {
      atkMod += 0.10;
    }
  }

  return { atk: atkMod, def: defMod };
}

module.exports = { showTactics, setFormation, setGamePlan, setPlanKey, getFormationModifier, getPlanModifier };
