require('dotenv').config();

module.exports = {
  token: process.env.DISCORD_TOKEN,
  clientId: process.env.CLIENT_ID,
  prefix: process.env.PREFIX || '!',

  startingBudget: 100000000,
  maxSquadSize: 25,
  trainingCostPerPoint: 500000,
  maxTrainingPerPlayer: 10,

  formations: {
    '4-4-2': { def: 3, mid: 3, atk: 4, desc: 'متوازن - خط وسط قوي' },
    '4-3-3': { def: 3, mid: 3, atk: 5, desc: 'هجومي - أجنحة سريعة' },
    '3-5-2': { def: 3, mid: 4, atk: 4, desc: 'سيطرة وسط - هجوم ثنائي' },
    '4-2-3-1': { def: 3, mid: 4, atk: 4, desc: 'وسط هجومي - صانع ألعاب' },
    '5-3-2': { def: 5, mid: 3, atk: 3, desc: 'دفاعي - مرتدات سريعة' },
  },

  gamePlans: {
    هجومي: { style: 'attack', defReduction: -0.1, atkBonus: 0.15, desc: 'ضغط عالي - هجوم مكثف' },
    دفاعي: { style: 'defend', defBonus: 0.15, atkReduction: -0.1, desc: 'تماسك دفاعي - غلق مساحات' },
    مرتد: { style: 'counter', defBonus: 0.05, atkBonus: 0.1, desc: 'دفاع ثم هجوم مرتد سريع' },
    استحواذ: { style: 'possession', midBonus: 0.1, atkReduction: -0.05, desc: 'التحكم بالكرة - صبر هجومي' },
  },

  planKeys: {
    A1: { name: 'أجنحة - حذر', counters: [], weakTo: ['C2', 'B3'], bonus: { atk: 0.02, def: 0.04 } },
    A2: { name: 'أجنحة - متوازن', counters: ['B1', 'D3'], weakTo: ['C1', 'A3'], bonus: { atk: 0.04, def: 0.02 } },
    A3: { name: 'أجنحة - هجومي', counters: ['A2', 'C1'], weakTo: ['B2', 'D1'], bonus: { atk: 0.07, def: -0.02 } },
    B1: { name: 'اختراق وسط - حذر', counters: ['C3', 'D2'], weakTo: ['A2', 'B3'], bonus: { atk: 0.02, def: 0.04 } },
    B2: { name: 'اختراق وسط - متوازن', counters: ['A3', 'D1'], weakTo: ['C3', 'B1'], bonus: { atk: 0.04, def: 0.02 } },
    B3: { name: 'اختراق وسط - هجومي', counters: ['A1', 'B1'], weakTo: ['C2', 'D2'], bonus: { atk: 0.07, def: -0.02 } },
    C1: { name: 'كرات طويلة - حذر', counters: ['A2', 'D3'], weakTo: ['A3', 'C2'], bonus: { atk: 0.03, def: 0.03 } },
    C2: { name: 'كرات طويلة - متوازن', counters: ['A1', 'B3'], weakTo: ['C1', 'D3'], bonus: { atk: 0.05, def: 0.01 } },
    C3: { name: 'كرات طويلة - هجومي', counters: ['B2', 'D1'], weakTo: ['B1', 'A2'], bonus: { atk: 0.08, def: -0.03 } },
    D1: { name: 'تمرير سريع - حذر', counters: ['A3', 'B2'], weakTo: ['B2', 'D2'], bonus: { atk: 0.03, def: 0.03 } },
    D2: { name: 'تمرير سريع - متوازن', counters: ['B3', 'D1'], weakTo: ['B1', 'A1'], bonus: { atk: 0.05, def: 0.01 } },
    D3: { name: 'تمرير سريع - هجومي', counters: ['A2', 'C2'], weakTo: ['A1', 'C1'], bonus: { atk: 0.08, def: -0.03 } },
  },

  goalkeeperRatings: {
    excellent: { min: 85, max: 92, label: 'ممتاز' },
    good: { min: 78, max: 84, label: 'جيد جداً' },
    average: { min: 70, max: 77, label: 'جيد' },
    poor: { min: 60, max: 69, label: 'متوسط' },
  },

  league: {
    minCoaches: 4,
    maxCoaches: 20,
    pointsWin: 3,
    pointsDraw: 1,
    pointsLose: 0,
  },
};
