import { InteractionCollector } from 'eris-collects';
import { getRandomDarkHexCode, getRandomNumber } from "roulette-image";
import { startRoundRoulette, disabledMultipleButtons, getMultipleButtons, getCoins, addCoins, spendCoins, spendPoints, getPlayerInventory, addToInventory, removeFromInventory, hasItem, getPoints, addPoints, pointsDB } from "./functions.js"
const roulette_games = new Map();
const SHOP_ITEMS = {
  double_kick: { id: 'double_kick', name: 'طرد ثنائي', price: 20, currency: 'coins', description: 'يمكنك طرد لاعبين في نفس الجولة', emoji: '👥' },
  shield: { id: 'shield', name: 'درع ضد الطرد', price: 18, currency: 'coins', description: 'يحميك من الطرد مرة واحدة', emoji: '🛡️' },
  reverse_kick: { id: 'reverse_kick', name: 'طرد عكسي', price: 25, currency: 'points', description: 'يعكس الطرد ويطرد من حاول طردك', emoji: '🔄' }
};

export default async function (bot, interaction, type = "slash", settings) {
  let roulette_command_names = await settings.has("roulette_command_names") ? await settings.get("roulette_command_names") : ["roulette", "روليت"]
  let stop_command_names = await settings.has("stop_command_names") ? await settings.get("stop_command_names") : ["stop", "توقف"]
  let points_command_names = ["points", "نقاط", "رصيد", "coins", "عملات"];
  let leaderboard_command_names = ["leaderboard", "ترتيب", "القادة", "top"];

  if (interaction.type == 2 && stop_command_names.map(e => e.toLowerCase()).includes(interaction.data.name.toLowerCase())) {
    if (!interaction.member.permissions.has("manageEvents")) return await interaction.createMessage({
      "flags": 64,
      "content": ":x: | فقط Manga Events يمكنهم قيام بهذا الامر ",
    })
    if (!roulette_games.has(interaction.guildID)) return await interaction.createMessage({
      "content": "❌ لا توجد لعبة قيد التشغيل في الوقت الحالي"
    })
    roulette_games.delete(interaction.guildID);
    await interaction.createMessage({
      "content": `:x: | تم طلب أيقاف لعبة روليت من قبل <@!${interaction.member.id}>`
    })
  }
  if (interaction.type == 2 && roulette_command_names.map(e => e.toLowerCase()).includes(interaction.data.name.toLowerCase())) {
      if (!interaction.member.permissions.has("manageEvents")) return await interaction.createMessage({
        "flags": 64,
        "content": ":x: | فقط Manga Events يمكنهم قيام بهذا الامر ",
      })
      if (roulette_games.has(interaction.guildID)) return await interaction.createMessage({
        "flags": 64,
        "content": ":x: | يوجد جولة تعمل الان بالفعل"
      })
      const waiting_time = await settings.has("waiting_time") ? await settings.get("waiting_time") : 60
      const id = Date.now();
      await interaction.createMessage({
        components: getMultipleButtons([
          ...Array(25).fill().map((x, i) => ({
            type: 2,
            style: 2,
            label: `${i + 1}`,
            custom_id: `join_${i}_roulette_${interaction.guildID}_${id}`
          })),
          {
            type: 2,
            style: 3,
            label: "🛒 المتجر",
            custom_id: `shop_roulette_${interaction.guildID}_${id}`
          }
        ]),
        embeds: [{
          title: "روليت",
          color: 0xe4f000,
          description: `__**اللاعبين:**__\nلا يوجد لاعبين مشاركين باللعبة`,
          fields: [{
            name: "__طريقة اللاعب:__",
            value: `**1-** انضم في اللعبة
              **2-** ستبدأ الجولة الأولى وسيتم تدوير العجلة واختيار لاعب عشوائي
              **3-** إذا كنت اللاعب المختار ، فستختار لاعبًا من اختيارك ليتم طرده من اللعبة
              **4-** يُطرد اللاعب وتبدأ جولة جديدة ، عندما يُطرد جميع اللاعبين ويتبقى لاعبان فقط ، ستدور العجلة ويكون اللاعب المختار هو الفائز باللعبة`
          }, {
            name: `__ستبدأ اللعبة خلال__:`,
            value: `**<t:${Math.floor((Date.now() + (waiting_time * 1000)) / 1000)}:R>**`
          }]
        }]
      });
    let mm_2 = await interaction.channel.createMessage({
      components: getMultipleButtons([
        ...Array(15).fill().map((x, i) => ({
          type: 2,
          style: 2,
          label: `${i + 26}`,
          custom_id: `join_${i + 25}_roulette_${interaction.guildID}_${id}`
        })),
        {
          type: 2,
          style: 3,
          label: "دخول عشوائي",
          custom_id: `join_random_roulette_${interaction.guildID}_${id}`
        }, {
          type: 2,
          style: 4,
          label: "اخرج من اللعبة",
          custom_id: `leave_roulette_${interaction.guildID}_${id}`
        }, {
          type: 2,
          style: 3,
          label: "🛒 المتجر",
          custom_id: `shop_roulette_${interaction.guildID}_${id}`
        }
      ])
    })
    roulette_games.set(interaction.guildID, { id, players: [] })
    const m = await interaction.getOriginalMessage();
    
    // Start shop collector for join phase
    startShopCollector(bot, interaction.channel, interaction.guildID, id);
    
    const collecter_buttons = new InteractionCollector(bot, { channel: interaction.channel, time: waiting_time * 1000, filter: i => i.type != 2 && i.data && i.data.custom_id && i.data.custom_id.endsWith(`roulette_${interaction.guildID}_${id}`) })
    collecter_buttons.on('collect', async i => {
      let data = i.data.custom_id.split("_")
      if (!i.data.custom_id.endsWith(`roulette_${interaction.guildID}_${id}`)) return;
      if (!roulette_games.has(interaction.guildID)) return collecter_buttons.stop("time");
      
      // Handle shop button
      if (data[0] == "shop") {
        await i.deferUpdate();
        await showShop(i, interaction.guildID, id, bot);
        return;
      }
      
      if (data[0] == "leave") {
        await i.deferUpdate();
        let roulette_data = roulette_games.get(i.guildID)
        if (!roulette_data.players[0]) return await i.createMessage({ flags: 64, content: `:x: | انت غير مشارك بالفعل` });
        let player = roulette_data.players.find(player => player.id == i.member.id)
        if (roulette_data.players[0] && !player) return await i.createMessage({ flags: 64, content: `:x: | انت غير مشارك بالفعل` });

        roulette_data.players = roulette_data.players.filter(x => x.id != i.member.id);
        roulette_games.set(i.guildID, roulette_data)
        await i.createMessage({ flags: 64, content: `✅ | تم إزالتك من اللعبة` });
        data[0] = "join_" + player.number
        await disabledMultipleButtons(i.message, `${data.join("_")}`, `${i.member.username}`, true);
        m.embeds[0].description = `__**اللاعبين:**__\n${roulette_data.players[0] ? `${roulette_data.players.sort((a, b) => a.number - b.number, 0).map(player => `\`${`${player.number + 1}`.length == 1 ? "0" : ""}${player.number + 1}\`: <@!${player.id}>`).join("\n")}` : "لا يوجد لاعبين مشاركين باللعبة"}`
        await disabledMultipleButtons(m, `${data.join("_")}`, `${i.member.username}`, true);
        await disabledMultipleButtons(mm_2, `${data.join("_")}`, `${i.member.username}`, true);
        await m.edit({ embeds: m.embeds, components: m.components }).catch(() => { });
        await mm_2.edit({ components: mm_2.components }).catch(() => { });
      } else if (data[0] == "join") {
        let roulette_data = roulette_games.get(i.guildID)
        if (roulette_data.players.length >= 40) return await i.createMessage({ flags: 64, content: "عدد المشاركين مكتمل" })
        if (roulette_data.players[0] && roulette_data.players.some(player => player.id == i.member.id)) return await i.createMessage({ flags: 64, content: "انت مشارك بالفعل لكي تغير مكانك يجب عليك الخروج من الروليت ثم الدخول مرة اخري" });
        await i.deferUpdate();
        if (data[1] == "random") {
          let number = await getRandomNumber(40, roulette_data.players.map(e => e.number));
          roulette_data.players.push({
            username: i.member.username,
            id: i.member.id,
            avatarURL: i.member.staticAvatarURL.replace("size=128", "size=512") || i.member.defaultAvatarURL,
            number,
            color: getRandomDarkHexCode()
          })
          roulette_games.set(i.guildID, roulette_data)
          data[1] = number;
          m.embeds[0].description = `__**اللاعبين:**__\n${roulette_data.players[0] ? `${roulette_data.players.sort((a, b) => a.number - b.number, 0).map(player => `\`${`${player.number + 1}`.length == 1 ? "0" : ""}${player.number + 1}\`: <@!${player.id}>`).join("\n")}` : "لا يوجد لاعبين مشاركين باللعبة"}`
          await i.message.edit({ components: i.message.components }).catch(() => { });
          await disabledMultipleButtons(m, `${data.join("_")}`, `${number + 1}. ${i.member.username}`);
          await disabledMultipleButtons(mm_2, `${data.join("_")}`, `${number + 1}. ${i.member.username}`);

          await m.edit({ embeds: m.embeds, components: m.components }).catch(() => { });
          await mm_2.edit({ components: mm_2.components }).catch(() => { });
        } else {
          let number = +data[1];
          roulette_data.players.push({
            username: i.member.username,
            id: i.member.id,
            avatarURL: i.member.staticAvatarURL.replace("size=128", "size=512") || i.member.defaultAvatarURL,
            number,
            color: getRandomDarkHexCode()
          })
          roulette_games.set(i.guildID, roulette_data)
          m.embeds[0].description = `__**اللاعبين:**__\n${roulette_data.players[0] ? `${roulette_data.players.sort((a, b) => a.number - b.number, 0).map(player => `\`${`${player.number + 1}`.length == 1 ? "0" : ""}${player.number + 1}\`: <@!${player.id}>`).join("\n")}` : "لا يوجد لاعبين مشاركين باللعبة"}`
          await i.message.edit({ components: i.message.components }).catch(() => { });
          await disabledMultipleButtons(m, i.data.custom_id, `${number + 1}. ${i.member.username}`);
          await disabledMultipleButtons(mm_2, i.data.custom_id, `${number + 1}. ${i.member.username}`);

          await m.edit({ embeds: m.embeds, components: m.components }).catch(() => { });
          await mm_2.edit({ components: mm_2.components }).catch(() => { });
        }
        // Give participation points when joining
        await addPoints(i.member.id, i.guildID, 5);
      }
    });
    collecter_buttons.on("end", async (interactions, r) => {
      interaction.channel.getMessage(m.id).then(async mm => {
        if (mm.components[0] && mm.components[0].components[0]) {
          await disabledMultipleButtons(mm)
          mm.embeds[0].color = 0x0ff000
          mm.embeds[0].fields = [mm.embeds[0].fields[0]]
          await mm.edit({ embeds: mm.embeds, components: mm.components }).catch(() => { });
          await disabledMultipleButtons(mm_2)
          await mm_2.edit({ components: mm_2.components }).catch(() => { });
        }
      }).catch(() => { });
      if (roulette_games.has(interaction.guildID) && !roulette_games.get(interaction.guildID).players[2]) {
        interaction.channel.createMessage("🚫 | تم إلغاء اللعبة لعدم وجود 3 لاعبين على الأقل");
        roulette_games.delete(interaction.guildID)
      } else if (roulette_games.has(interaction.guildID)) {
        await interaction.channel.createMessage("✅ | تم توزيع الأرقام على كل لاعب. ستبدأ الجولة الأولى في بضع ثواني...");
        await startRoundRoulette(bot, interaction, roulette_games, id)
      } else if (!roulette_games.has(interaction.guildID)) {
        await interaction.channel.createMessage(":x: | تم إيقاف الجولة بواسطة المسؤولين");
      }
    })
  }

  // Points command
  if (interaction.type == 2 && points_command_names.map(e => e.toLowerCase()).includes(interaction.data.name.toLowerCase())) {
    const targetUser = interaction.data.options?.[0]?.value ? interaction.data.options[0].value : interaction.member.id;
    const points = await getPoints(targetUser, interaction.guildID);
    const coins = await getCoins(targetUser, interaction.guildID);
    const inventory = await getPlayerInventory(targetUser, interaction.guildID);
    
    let inventoryText = "لا يوجد عناصر";
    if (inventory.length > 0) {
      inventoryText = inventory.map(item => {
        const shopItem = SHOP_ITEMS[item.id];
        return shopItem ? `${shopItem.emoji} ${shopItem.name}` : item.id;
      }).join(", ");
    }
    
    await interaction.createMessage({
      embeds: [{
        title: "📊 رصيد اللاعب",
        color: 0x00ff00,
        description: `<@${targetUser}>`,
        fields: [
          { name: "⭐ النقاط", value: `${points}`, inline: true },
          { name: "💰 العملات", value: `${coins}`, inline: true },
          { name: "🎒 المخزون", value: inventoryText, inline: false }
        ]
      }]
    });
  }

  // Leaderboard command
  if (interaction.type == 2 && leaderboard_command_names.map(e => e.toLowerCase()).includes(interaction.data.name.toLowerCase())) {
    // Get all points from database
    const allData = await pointsDB.all();
    const pointsData = allData
      .filter(item => item.id.startsWith(`points_${interaction.guildID}_`))
      .map(item => ({
        userId: item.id.replace(`points_${interaction.guildID}_`, ''),
        points: item.value
      }))
      .sort((a, b) => b.points - a.points)
      .slice(0, 10);
    
    if (pointsData.length === 0) {
      return await interaction.createMessage({ content: "لا يوجد لاعبين في الترتيب بعد!" });
    }
    
    const leaderboardText = pointsData.map((entry, index) => {
      const medal = index === 0 ? "🥇" : index === 1 ? "🥈" : index === 2 ? "🥉" : `${index + 1}.`;
      return `${medal} <@${entry.userId}> - **${entry.points}** نقطة`;
    }).join("\n");
    
    await interaction.createMessage({
      embeds: [{
        title: "🏆 لوحة المتصدرين - روليت",
        color: 0xffd700,
        description: leaderboardText
      }]
    });
  }
}

async function showShop(interaction, guildId, gameId, bot) {
  const userId = interaction.member.id;
  const coins = await getCoins(userId, guildId);
  const inventory = await getPlayerInventory(userId, guildId);
  
  const embed = {
    title: "🛒 متجر الروليت",
    color: 0x0099ff,
    description: `**رصيدك:** ${coins} عملة | ${await getPoints(userId, guildId)} نقطة\n\nاختر عنصراً للشراء:`,
    fields: Object.values(SHOP_ITEMS).map(item => ({
      name: `${item.emoji} ${item.name} - ${item.price} ${item.currency === 'points' ? 'نقطة' : 'عملة'}`,
      value: `${item.description}${inventory.some(inv => inv.id === item.id) ? '\n✅ **ممتلك**' : ''}`,
      inline: true
    })),
    footer: { text: "العناصر المشتراة تظهر في جولة الطرد" }
  };
  
  const components = getMultipleButtons([
    ...Object.values(SHOP_ITEMS).map(item => ({
      type: 2,
      style: inventory.some(inv => inv.id === item.id) ? 2 : 1,
      label: `${item.emoji} ${item.name} (${item.price})`,
      custom_id: `buy_${item.id}_${guildId}_${gameId}`,
      disabled: inventory.some(inv => inv.id === item.id)
    })),
    {
      type: 2,
      style: 4,
      label: "إغلاق",
      custom_id: `close_shop_${guildId}_${gameId}`
    }
  ]);
  
  const shopMsg = await interaction.channel.createMessage({
    content: `<@${userId}>`,
    embeds: [embed],
    components: components,
    flags: 64
  });
  
  // Start collector for this shop message
  const shopCollector = new InteractionCollector(bot, { 
    channel: interaction.channel, 
    time: 60000,
    filter: i => i.data && i.data.custom_id && i.data.custom_id.includes(`_${guildId}_${gameId}`) && (i.data.custom_id.startsWith("buy_") || i.data.custom_id.startsWith("close_shop")) && i.type != 2 
  });
  
  shopCollector.on('collect', async i => {
    const data = i.data.custom_id.split("_");
    if (data[0] === "buy" && data[1]) {
      const itemId = data[1];
      await i.deferUpdate();
      await handleShopPurchase(i, guildId, gameId, itemId);
      // Update the shop message to reflect purchase
      const newCoins = await getCoins(userId, guildId);
      const newInventory = await getPlayerInventory(userId, guildId);
      const newEmbed = {
        title: "🛒 متجر الروليت",
        color: 0x0099ff,
        description: `**رصيدك:** ${newCoins} عملة | ${await getPoints(userId, guildId)} نقطة\n\nاختر عنصراً للشراء:`,
        fields: Object.values(SHOP_ITEMS).map(item => ({
          name: `${item.emoji} ${item.name} - ${item.price} ${item.currency === 'points' ? 'نقطة' : 'عملة'}`,
          value: `${item.description}${newInventory.some(inv => inv.id === item.id) ? '\n✅ **ممتلك**' : ''}`,
          inline: true
        })),
        footer: { text: "العناصر المشتراة تظهر في جولة الطرد" }
      };
      const newComponents = getMultipleButtons([
        ...Object.values(SHOP_ITEMS).map(item => ({
          type: 2,
          style: newInventory.some(inv => inv.id === item.id) ? 2 : 1,
          label: `${item.emoji} ${item.name} (${item.price})`,
          custom_id: `buy_${item.id}_${guildId}_${gameId}`,
          disabled: newInventory.some(inv => inv.id === item.id)
        })),
        {
          type: 2,
          style: 4,
          label: "إغلاق",
          custom_id: `close_shop_${guildId}_${gameId}`
        }
      ]);
      await shopMsg.edit({ embeds: [newEmbed], components: newComponents }).catch(() => {});
    } else if (data[0] === "close" && data[1] === "shop") {
      await i.deferUpdate();
      await shopMsg.delete().catch(() => {});
      shopCollector.stop("closed");
    }
  });
  
  shopCollector.on("end", () => {});
}

// Handle shop purchases - this will be called from the kick phase collector
export async function handleShopPurchase(interaction, guildId, gameId, itemId) {
  const userId = interaction.member.id;
  const item = SHOP_ITEMS[itemId];
  
  if (!item) return await interaction.createMessage({ flags: 64, content: ":x: | عنصر غير موجود" });
  
  const inventory = await getPlayerInventory(userId, guildId);
  if (inventory.some(inv => inv.id === itemId)) {
    return await interaction.createMessage({ flags: 64, content: ":x: | تمتلك هذا العنصر بالفعل" });
  }
  
  let success = false;
  if (item.currency === 'points') {
    success = await spendPoints(userId, guildId, item.price);
  } else {
    success = await spendCoins(userId, guildId, item.price);
  }
  
  if (!success) {
    const currencyName = item.currency === 'points' ? 'نقطة' : 'عملة';
    return await interaction.createMessage({ flags: 64, content: `:x: | رصيدك غير كافٍ (تحتاج ${item.price} ${currencyName})` });
  }
  
  await addToInventory(userId, guildId, { id: itemId, purchasedAt: Date.now() });
  await interaction.createMessage({ flags: 64, content: `✅ | تم شراء **${item.name}** بنجاح!` });
}

// Collector for shop purchases during join phase
export async function startShopCollector(bot, channel, guildId, gameId) {
  const shopCollector = new InteractionCollector(bot, { 
    channel: channel, 
    time: 60000, // 1 minute timeout for shop
    filter: i => i.data && i.data.custom_id && i.data.custom_id.includes(`_${guildId}_${gameId}`) && i.data.custom_id.startsWith("buy_") && i.type != 2 
  });
  
  shopCollector.on('collect', async i => {
    const data = i.data.custom_id.split("_");
    if (data[0] === "buy" && data[1]) {
      const itemId = data[1];
      await i.deferUpdate();
      await handleShopPurchase(i, guildId, gameId, itemId);
    } else if (data[0] === "close" && data[1] === "shop") {
      await i.deferUpdate();
      // Message will be deleted or disabled
      await i.message.delete().catch(() => {});
      shopCollector.stop("closed");
    }
  });
  
  shopCollector.on("end", () => {});
}