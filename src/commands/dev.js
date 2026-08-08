const { getStore, saveStore } = require('../store');
const { teams } = require('../data/teams');

function resetUser(userId) {
  const store = getStore();
  if (store.coaches[userId]) {
    delete store.coaches[userId];
    saveStore(store);
    return { ok: true, msg: '✅ تم حذف حسابك التجريبي.' };
  }
  return { ok: false, msg: 'لا يوجد حساب.' };
}

function addXP(userId, amount) {
  const store = getStore();
  const coach = store.coaches[userId];
  if (!coach) return { ok: false, msg: 'لا يوجد مدرب.' };
  coach.xp = (coach.xp || 0) + amount;
  saveStore(store);
  return { ok: true, msg: `✅ تمت إضافة ${amount} XP. الرصيد الحالي: ${coach.xp} XP` };
}

function addBudget(userId, amount) {
  const store = getStore();
  const coach = store.coaches[userId];
  if (!coach) return { ok: false, msg: 'لا يوجد مدرب.' };
  coach.budget = (coach.budget || 0) + amount;
  saveStore(store);
  return { ok: true, msg: `✅ تمت إضافة ${amount.toLocaleString()} ريال. الميزانية: ${coach.budget.toLocaleString()} ريال` };
}

module.exports = { resetUser, addXP, addBudget };
