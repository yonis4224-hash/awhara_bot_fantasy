const { getStore, saveStore } = require('../store');
const { teams } = require('../data/teams');
const { calculatePlayerValue } = require('../data/teams');

const MARKET_FEE = 0.05;

function listMarket(userId) {
  const store = getStore();
  const coach = store.coaches[userId];
  if (!coach || !coach.team) return { ok: false, msg: 'يجب أن تمتلك فريقاً أولاً!' };

  const listings = store.marketListings || [];
  if (listings.length === 0) return { ok: false, msg: '📭 سوق الانتقالات فارغ حالياً. استخدم الأمر `!بيع` لعرض لاعب للبيع.' };

  const lines = listings.map((l, i) =>
    `**${i + 1}.** ${l.playerName} - ⭐${l.rating} - 💰 ${l.price.toLocaleString()} ريال\n   🏢 البائع: <@${l.sellerId}>`
  );
  return { ok: true, msg: `🏪 **سوق الانتقالات**\n\n${lines.join('\n')}\n\nللشراء استخدم: \`!شراء رقم_اللاعب\`` };
}

function sellPlayer(userId, playerName, price) {
  const store = getStore();
  const coach = store.coaches[userId];
  if (!coach || !coach.team) return { ok: false, msg: 'يجب أن تمتلك فريقاً أولاً!' };

  const playerIndex = coach.players.findIndex(p => p.name === playerName || p.name.includes(playerName));
  if (playerIndex === -1) return { ok: false, msg: `لم أجد لاعباً باسم "${playerName}" في فريقك.` };

  const player = coach.players[playerIndex];
  if (!player.value || player.value < 100000) return { ok: false, msg: 'هذا اللاعب لا يمكن بيعه.' };

  const listing = {
    playerIndex,
    playerName: player.name,
    rating: player.rating,
    pos: player.pos,
    price: Math.max(price || player.value, 100000),
    sellerId: userId,
    playerData: player,
  };

  store.marketListings = store.marketListings || [];
  store.marketListings.push(listing);
  saveStore(store);

  return { ok: true, msg: `📢 تم عرض **${player.name}** للبيع بسعر 💰 ${listing.price.toLocaleString()} ريال!` };
}

function buyPlayer(userId, marketIndex) {
  const store = getStore();
  const coach = store.coaches[userId];
  if (!coach || !coach.team) return { ok: false, msg: 'يجب أن تمتلك فريقاً أولاً!' };

  const listings = store.marketListings || [];
  if (marketIndex < 0 || marketIndex >= listings.length) return { ok: false, msg: 'رقم اللاعب غير صحيح.' };

  const listing = listings[marketIndex];
  if (listing.sellerId === userId) return { ok: false, msg: 'لا يمكنك شراء لاعبك الخاص!' };

  const seller = store.coaches[listing.sellerId];
  if (!seller) return { ok: false, msg: 'البائع غير موجود.' };

  const totalPrice = Math.round(listing.price * (1 + MARKET_FEE));
  if (coach.budget < totalPrice) return { ok: false, msg: `💰 ميزانيتك غير كافية! تحتاج ${totalPrice.toLocaleString()} ريال ولديك ${coach.budget.toLocaleString()} ريال.` };

  if (coach.players.length >= 25) return { ok: false, msg: '🚫 فريقك مكتمل (25 لاعباً). يجب بيع لاعب أولاً.' };

  const boughtPlayer = { ...listing.playerData };
  coach.budget -= totalPrice;
  coach.players.push(boughtPlayer);
  seller.budget += listing.price;
  seller.players = seller.players || [];
  const sellIdx = seller.players.findIndex(p => p.name === listing.playerName);
  if (sellIdx !== -1) seller.players.splice(sellIdx, 1);

  listings.splice(marketIndex, 1);
  saveStore(store);

  return {
    ok: true,
    msg: `✅ **تمت الصفقة!**\n📥 اشتريت **${boughtPlayer.name}** (⭐${boughtPlayer.rating}) من <@${listing.sellerId}>\n💰 المبلغ المدفوع: ${totalPrice.toLocaleString()} ريال (شامل الرسوم)\n💵 البائع حصل على: ${listing.price.toLocaleString()} ريال`
  };
}

function cancelListing(userId, marketIndex) {
  const store = getStore();
  const listings = store.marketListings || [];
  if (marketIndex < 0 || marketIndex >= listings.length) return { ok: false, msg: 'رقم غير صحيح.' };

  if (listings[marketIndex].sellerId !== userId) return { ok: false, msg: 'هذا العرض ليس لك.' };

  const playerName = listings[marketIndex].playerName;
  listings.splice(marketIndex, 1);
  saveStore(store);
  return { ok: true, msg: `✅ تم إلغاء عرض بيع **${playerName}**.` };
}

module.exports = { listMarket, sellPlayer, buyPlayer, cancelListing };
