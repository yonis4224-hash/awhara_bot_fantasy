import { Database } from 'st.db';
import { Database as ReplitDB } from "quick.replit";
import inquirer from "inquirer";
import startBot from "./bot.js";
import { Interval } from 'quickinterval';
import { createRouletteGifImage, shuffleArray, getRandomDarkHexCode, createRouletteImage, getRandomNumber } from "roulette-image";
import { InteractionCollector } from 'eris-collects';
const is_replit = process.env.REPL_ID && process.env.REPL_SLUG && process.env.REPL_OWNER;
const shuruhatik = `█▀ █░█ █░█ █▀█ █░█ █░█ ▄▀█ ▀█▀ █ █▄▀\n▄█ █▀█ █▄█ █▀▄ █▄█ █▀█ █▀█ ░█░ █ █░█`
const config = is_replit ? new ReplitDB() : new Database("./config.yml");
const settings = is_replit ? new Database("./config.yml") : config;
const pointsDB = is_replit ? new ReplitDB("./points.json") : new Database("./points.json");

function disabledMultipleButtons(mm, specific_custom_id, username, is_leave = false) {
  mm.components.forEach(async (a, i) => {
    a.components.forEach(async (b, e) => {
      if (specific_custom_id && mm.components[i].components[e].custom_id.includes(specific_custom_id)) {
        mm.components[i].components[e].disabled = is_leave ? false : true
        if (username) mm.components[i].components[e].label = is_leave ? `${+mm.components[i].components[e].custom_id.split("_")[1] + 1}` : username;
      } else if (!specific_custom_id) {
        mm.components[i].components[e].disabled = true
      }
      if (e + 1 == a.components.length && mm.components.length == i + 1) {
        return mm.components
      }
    })
  })
}

function getMultipleButtons(all_buttons) {
  let components = [];
  for (let i = 0; i < all_buttons.length; i += 5) {
    let component = { components: [], type: 1 }
    for (let btn of all_buttons.slice(i, i + 5)) {
      component.components.push(btn);
    }
    components.push(component);
  }
  return components;
}

async function startRoundRoulette(bot, interaction, roulette_games, id, round = 1) {
  if (!roulette_games.has(interaction.guildID)) return await interaction.channel.createMessage(":x: | تم إيقاف الجولة بواسطة المسؤولين");
  let roulette_data = roulette_games.get(interaction.guildID)
  let players = shuffleArray(roulette_data.players.sort((a, b) => a.number - b.number, 0));
  let winner = players[players.length - 1];
  let bufferRouletteImage = await createRouletteGifImage(players)
  await interaction.channel.createMessage(`**${winner.number + 1}** - <@${winner.id}>${players.length <= 2 ? `\n:crown: **هذه الجولة الأخيرة ! اللاعب المختار هو اللاعب الفائز في اللعبة.**` : ""}`, {
    file: bufferRouletteImage,
    name: 'roulette.gif'
  });
  
  // Give participation points to all players (1 point per round)
  for (const player of roulette_data.players) {
    await addPoints(player.id, interaction.guildID, 1);
  }
  
  if (players.length <= 2) {
    // Winner gets 3 points and 10 coins
    await addPoints(winner.id, interaction.guildID, 3);
    await addCoins(winner.id, interaction.guildID, 10);
    await interaction.channel.createMessage(`:crown: - فاز <@!${winner.id}> في اللعبة وحصل على **3 نقاط** و **10 عملات**!`);
    roulette_games.delete(interaction.guildID);
  } else {
    // Check if winner has items
    const hasDoubleKick = await hasItem(winner.id, interaction.guildID, 'double_kick');
    const hasShield = await hasItem(winner.id, interaction.guildID, 'shield');
    const hasReverseKick = await hasItem(winner.id, interaction.guildID, 'reverse_kick');
    
    const kickButtons = players.slice(0, -1).slice(0, 24).map((player) => ({
      type: 2,
      style: 2,
      label: `${player.number + 1}. ${player.username}`,
      custom_id: `kick_${player.number}_groulette_${interaction.guildID}_${id}`
    }));
    
    // Add special buttons based on items
    if (hasDoubleKick) {
      kickButtons.push({
        type: 2,
        style: 1,
        label: "👥 طرد ثنائي",
        custom_id: `doublekick_groulette_${interaction.guildID}_${id}`
      });
    }
    if (hasShield) {
      kickButtons.push({
        type: 2,
        style: 3,
        label: "🛡️ تفعيل الدرع",
        custom_id: `shield_groulette_${interaction.guildID}_${id}`
      });
    }
    if (hasReverseKick) {
      kickButtons.push({
        type: 2,
        style: 1,
        label: "🔄 طرد عكسي",
        custom_id: `reversekick_groulette_${interaction.guildID}_${id}`
      });
    }
    
    // Random kick button
    kickButtons.push({
      type: 2,
      style: 3,
      label: "🎲 طرد عشوائي",
      custom_id: `randomkick_groulette_${interaction.guildID}_${id}`
    });
    
    kickButtons.push({
      type: 2,
      style: 4,
      label: "انسحاب",
      custom_id: `withdraw_groulette_${interaction.guildID}_${id}`
    });
    
    const game_msg = await interaction.channel.createMessage({
      content: `<@${winner.id}> لديك **30 ثانية** لإختيار لاعب لطرده`, components: getMultipleButtons(kickButtons)
    });
    const collecter_buttons = new InteractionCollector(bot, { channel: interaction.channel, time: 30000, filter: i => i.data && i.data.custom_id && i.data.custom_id.endsWith(`groulette_${interaction.guildID}_${id}`) && i.type != 2 })
    collecter_buttons.on('collect', async i => {
      if (winner.id !== i.member.id) return await i.createMessage({ flags: 64, content: `:x: | فقط الشخص الذي لديه الدور يمكنه الاختيار` })
      await i.deferUpdate();
      if (!roulette_games.has(interaction.guildID)) return collecter_buttons.stop("stop");
      collecter_buttons.stop(i.data.custom_id);
    })
    collecter_buttons.on("end", async (interactions, r) => {
      if (!roulette_games.has(interaction.guildID)) {
        await interaction.channel.createMessage(":x: | تم إيقاف الجولة بواسطة المسؤولين");
        interaction.channel.getMessage(game_msg.id).then(async mm => {
          if (mm.components[0] && !mm.components[0].components[0].disabled) {
            await disabledMultipleButtons(mm)
            await mm.edit({ components: mm.components }).catch(() => { });
          }
        }).catch(console.error);
      } else {
        let data = r.split("_")
        if (r.startsWith("kick")) {
          let number = +data[1];
          let player = roulette_data.players.find(player => player.number == number);
          
          // Check if target has shield
          const targetHasShield = await hasItem(player.id, interaction.guildID, 'shield');
          if (targetHasShield) {
            await removeFromInventory(player.id, interaction.guildID, 'shield');
            interaction.channel.getMessage(game_msg.id).then(async mm => {
              if (mm.components[0] && !mm.components[0].components[0].disabled) {
                await disabledMultipleButtons(mm)
                await mm.edit({ components: mm.components }).catch(() => { });
                interaction.channel.createMessage(`🛡️ | <@${player.id}> استخدم **الدرع** ونجا من الطرد! تم استهلاك الدرع.`);
                // Winner still gets 1 point for attempting kick
                await addPoints(winner.id, interaction.guildID, 1);
                await startRoundRoulette(bot, interaction, roulette_games, id, round + 1);
              }
            })
            return;
          }
          
          // Check if target has reverse kick
          const targetHasReverse = await hasItem(player.id, interaction.guildID, 'reverse_kick');
          if (targetHasReverse) {
            await removeFromInventory(player.id, interaction.guildID, 'reverse_kick');
            interaction.channel.getMessage(game_msg.id).then(async mm => {
              if (mm.components[0] && !mm.components[0].components[0].disabled) {
                await disabledMultipleButtons(mm)
                await mm.edit({ components: mm.components }).catch(() => { });
                interaction.channel.createMessage(`🔄 | <@${player.id}> استخدم **الطرد العكسي**! تم طرد <@${winner.id}> بدلاً منه!`);
                // Target gets 1 point for reverse kick
                await addPoints(player.id, interaction.guildID, 1);
                roulette_data.players = roulette_data.players.filter(x => x.id != winner.id);
                roulette_games.set(interaction.guildID, roulette_data);
                await startRoundRoulette(bot, interaction, roulette_games, id, round + 1);
              }
            })
            return;
          }
          
          // Normal kick
          interaction.channel.getMessage(game_msg.id).then(async mm => {
            if (mm.components[0] && !mm.components[0].components[0].disabled) {
              await disabledMultipleButtons(mm)
              await mm.edit({ components: mm.components }).catch(() => { });
              interaction.channel.createMessage(`💣 | تم طرد <@${player.id}> من اللعبة ، سيتم بدء الجولة القادمة في بضع ثواني...`);
              // Winner gets 1 point for successful kick
              await addPoints(winner.id, interaction.guildID, 1);
              await addCoins(winner.id, interaction.guildID, 2);
              roulette_data.players = roulette_data.players.filter(x => x.number != number);
              roulette_games.set(interaction.guildID, roulette_data);
              await startRoundRoulette(bot, interaction, roulette_games, id, round + 1);
            }
          })
        } else if (r.startsWith("doublekick")) {
          // Double kick - winner picks 2 players
          interaction.channel.getMessage(game_msg.id).then(async mm => {
            if (mm.components[0] && !mm.components[0].components[0].disabled) {
              await disabledMultipleButtons(mm)
              await mm.edit({ components: mm.components }).catch(() => { });
              await removeFromInventory(winner.id, interaction.guildID, 'double_kick');
              
              // Show selection for 2 players
              const pick_msg = await interaction.channel.createMessage({
                content: `<@${winner.id}> اختر **لاعبين** للطرد (اختر الأول)`, components: getMultipleButtons([
                  ...players.slice(0, -1).slice(0, 24).map((player) => ({
                    type: 2,
                    style: 2,
                    label: `${player.number + 1}. ${player.username}`,
                    custom_id: `doublekick1_${player.number}_groulette_${interaction.guildID}_${id}`
                  })),
                  {
                    type: 2,
                    style: 4,
                    label: "إلغاء",
                    custom_id: `cancel_doublekick_groulette_${interaction.guildID}_${id}`
                  }
                ])
              });
              
              const pick_collector = new InteractionCollector(bot, { channel: interaction.channel, time: 30000, filter: i => i.data && i.data.custom_id && i.data.custom_id.endsWith(`groulette_${interaction.guildID}_${id}`) && i.type != 2 })
              pick_collector.on('collect', async i => {
                if (winner.id !== i.member.id) return await i.createMessage({ flags: 64, content: `:x: | فقط الشخص الذي لديه الدور يمكنه الاختيار` })
                await i.deferUpdate();
                pick_collector.stop(i.data.custom_id);
              })
              pick_collector.on("end", async (interactions, r) => {
                let data = r.split("_")
                if (r.startsWith("doublekick1")) {
                  let number1 = +data[1];
                  let player1 = roulette_data.players.find(player => player.number == number1);
                  
                  // Second pick
                  const remainingPlayers = players.slice(0, -1).filter(p => p.number != number1);
                  const pick_msg2 = await interaction.channel.createMessage({
                    content: `<@${winner.id}> اختر **اللاعب الثاني** للطرد`, components: getMultipleButtons([
                      ...remainingPlayers.slice(0, 24).map((player) => ({
                        type: 2,
                        style: 2,
                        label: `${player.number + 1}. ${player.username}`,
                        custom_id: `doublekick2_${number1}_${player.number}_groulette_${interaction.guildID}_${id}`
                      })),
                      {
                        type: 2,
                        style: 4,
                        label: "إلغاء",
                        custom_id: `cancel_doublekick_groulette_${interaction.guildID}_${id}`
                      }
                    ])
                  });
                  
                  const pick_collector2 = new InteractionCollector(bot, { channel: interaction.channel, time: 30000, filter: i => i.data && i.data.custom_id && i.data.custom_id.endsWith(`groulette_${interaction.guildID}_${id}`) && i.type != 2 })
                  pick_collector2.on('collect', async i => {
                    if (winner.id !== i.member.id) return await i.createMessage({ flags: 64, content: `:x: | فقط الشخص الذي لديه الدور يمكنه الاختيار` })
                    await i.deferUpdate();
                    pick_collector2.stop(i.data.custom_id);
                  })
                  pick_collector2.on("end", async (interactions, r) => {
                    let data = r.split("_")
                    if (r.startsWith("doublekick2")) {
                      let number1 = +data[1];
                      let number2 = +data[2];
                      let player1 = roulette_data.players.find(player => player.number == number1);
                      let player2 = roulette_data.players.find(player => player.number == number2);
                      
                      interaction.channel.getMessage(pick_msg2.id).then(async mm => {
                        if (mm.components[0] && !mm.components[0].components[0].disabled) {
                          await disabledMultipleButtons(mm)
                          await mm.edit({ components: mm.components }).catch(() => { });
                        }
                      })
                      interaction.channel.getMessage(pick_msg.id).then(async mm => {
                        if (mm.components[0] && !mm.components[0].components[0].disabled) {
                          await disabledMultipleButtons(mm)
                          await mm.edit({ components: mm.components }).catch(() => { });
                        }
                      })
                      
                      interaction.channel.createMessage(`💣💣 | تم طرد <@${player1.id}> و <@${player2.id}> من اللعبة (طرد ثنائي)!`);
                      await addPoints(winner.id, interaction.guildID, 2); // 2 points for double kick
                      await addCoins(winner.id, interaction.guildID, 5);
                      roulette_data.players = roulette_data.players.filter(x => x.number != number1 && x.number != number2);
                      roulette_games.set(interaction.guildID, roulette_data);
                      await startRoundRoulette(bot, interaction, roulette_games, id, round + 1);
                    } else {
                      interaction.channel.getMessage(pick_msg.id).then(async mm => {
                        if (mm.components[0] && !mm.components[0].components[0].disabled) {
                          await disabledMultipleButtons(mm)
                          await mm.edit({ components: mm.components }).catch(() => { });
                        }
                      })
                      interaction.channel.createMessage(`❌ | تم إلغاء الطرد الثنائي`);
                      await startRoundRoulette(bot, interaction, roulette_games, id, round + 1);
                    }
                  })
                } else {
                  interaction.channel.getMessage(pick_msg.id).then(async mm => {
                    if (mm.components[0] && !mm.components[0].components[0].disabled) {
                      await disabledMultipleButtons(mm)
                      await mm.edit({ components: mm.components }).catch(() => { });
                    }
                  })
                  interaction.channel.createMessage(`❌ | تم إلغاء الطرد الثنائي`);
                  await startRoundRoulette(bot, interaction, roulette_games, id, round + 1);
                }
              })
            }
          })
        } else if (r.startsWith("shield")) {
          // Shield activation - protects from next kick
          await removeFromInventory(winner.id, interaction.guildID, 'shield');
          // Add shield protection flag to player data
          winner.shieldActive = true;
          roulette_games.set(interaction.guildID, roulette_data);
          interaction.channel.getMessage(game_msg.id).then(async mm => {
            if (mm.components[0] && !mm.components[0].components[0].disabled) {
              await disabledMultipleButtons(mm)
              await mm.edit({ components: mm.components }).catch(() => { });
            }
          })
          interaction.channel.createMessage(`🛡️ | <@${winner.id}> فعل **الدرع**! أنت محمي من الطرد القادم.`);
          await startRoundRoulette(bot, interaction, roulette_games, id, round + 1);
        } else if (r.startsWith("reversekick")) {
          // Reverse kick - next kick against you will reverse
          await removeFromInventory(winner.id, interaction.guildID, 'reverse_kick');
          winner.reverseKickActive = true;
          roulette_games.set(interaction.guildID, roulette_data);
          interaction.channel.getMessage(game_msg.id).then(async mm => {
            if (mm.components[0] && !mm.components[0].components[0].disabled) {
              await disabledMultipleButtons(mm)
              await mm.edit({ components: mm.components }).catch(() => { });
            }
          })
          interaction.channel.createMessage(`🔄 | <@${winner.id}> فعل **الطرد العكسي**! من سيطردك سيطرد بدلاً منك.`);
          await startRoundRoulette(bot, interaction, roulette_games, id, round + 1);
        } else if (r.startsWith("randomkick")) {
          // Random kick
          const victims = players.slice(0, -1);
          const randomVictim = victims[Math.floor(Math.random() * victims.length)];
          interaction.channel.getMessage(game_msg.id).then(async mm => {
            if (mm.components[0] && !mm.components[0].components[0].disabled) {
              await disabledMultipleButtons(mm)
              await mm.edit({ components: mm.components }).catch(() => { });
              interaction.channel.createMessage(`🎲 | **طرد عشوائي**! تم طرد <@${randomVictim.id}> من اللعبة!`);
              await addPoints(winner.id, interaction.guildID, 1);
              roulette_data.players = roulette_data.players.filter(x => x.number != randomVictim.number);
              roulette_games.set(interaction.guildID, roulette_data);
              await startRoundRoulette(bot, interaction, roulette_games, id, round + 1);
            }
          })
        } else if (r.startsWith("withdraw")) {
          interaction.channel.getMessage(game_msg.id).then(async mm => {
            if (mm.components[0] && !mm.components[0].components[0].disabled) {
              await disabledMultipleButtons(mm)
              await mm.edit({ components: mm.components }).catch(() => { });
              interaction.channel.createMessage(`💣 | لقد انسحب <@${winner.id}> من اللعبة ، سيتم بدء الجولة القادمة في بضع ثواني...`);
              roulette_data.players = roulette_data.players.filter(x => x.id != winner.id);
              roulette_games.set(interaction.guildID, roulette_data);
              await startRoundRoulette(bot, interaction, roulette_games, id, round + 1);
            }
          })
        } else if (r == "time") {
          interaction.channel.getMessage(game_msg.id).then(async mm => {
            if (mm.components[0] && !mm.components[0].components[0].disabled) {
              await disabledMultipleButtons(mm)
              await mm.edit({ components: mm.components }).catch(() => { });
              interaction.channel.createMessage(`💣 | تم طرد <@${winner.id}> من اللعبة لعدم تفاعله ، سيتم بدء الجولة القادمة في بضع ثواني...`);
              roulette_data.players = roulette_data.players.filter(x => x.id != winner.id);
              roulette_games.set(interaction.guildID, roulette_data);
              await startRoundRoulette(bot, interaction, roulette_games, id, round + 1);
            }
          }).catch(console.error);
        }
      }
    })
  }
};

async function runAction(auto_run) {
  console.clear()
  if (await settings.has("reset") && await config.has("token")) {
    if (auto_run) return await startBot(await settings.get("debug") || false, config);
    const { action } = await inquirer.prompt({
      name: "action",
      type: 'list',
      message: `What is the action you want to do?`,
      choices: [
        { name: "Run the bot", value: 0 }, { name: "Run the bot with debug mode", value: 1 }, { name: "Re-setup to put a new token and information", value: 2 }
      ]
    })

    if (action == 0) {
      await settings.set("debug", action);
      return await startBot(false, config);
    } else if (action == 1) {
      await settings.set("debug", action);
      return await startBot(true, config);
    };
  } else {
    console.log(`\nDeveloped By \u001b[32;1mShuruhatik#2443\u001b[0m `)
    await config.delete(`token`);
    const { waiting_time, token_bot, status_type, status_bot } = await inquirer.prompt([
      {
        name: "token_bot",
        mask: "#",
        type: 'password',
        prefix: "\u001b[32;1m1-\u001b[0m",
        message: `Put your Bot token :`,
        mask: "*"
      }, {
        name: "status_bot",
        type: 'input',
        prefix: "\u001b[32;1m2-\u001b[0m",
        message: `Type in the status of the bot you want :`
      }, {
        name: "status_type",
        type: 'rawlist',
        prefix: "\u001b[32;1m3-\u001b[0m",
        message: `Choose the type of bot status :`,
        choices: [
          { name: "Playing", value: 0 }, { name: "Listening", value: 2 }, { name: "Watching", value: 3 }, { name: "Competing", value: 5 }
        ]
      }, {
        name: "waiting_time",
        type: 'number',
        prefix: "\u001b[32;1m4-\u001b[0m",
        default: 40,
        message: `Wait time until the round starts (in seconds) :`
      }
    ]);
    await config.set(`token`, clearTextPrompt(token_bot));
    await settings.set("status_bot", clearTextPrompt(status_bot, true));
    await settings.set("status_type", status_type);
    await settings.set("waiting_time", waiting_time);
    await settings.set("prefix", "-");
    await settings.set("roulette_command_names", ["roulette", "روليت"]);
    await settings.set("stop_command_names", ["stop", "توقف"]);
    await settings.set("reset", "احذف هذا السطر إذا كنت تريد تحط توكن جديد");
    return await runAction();
  };
};

function sendDM(member, content, file) {
  return new Promise((resolve, reject) => {
    (member.user || member).getDMChannel().then(channel => {
      channel.createMessage(content, file).then(resolve).catch(reject);
    }).catch(reject);
  });
};

function clearTextPrompt(str, status_bot = false) {
  return !status_bot ? str.trim().replaceAll("\\", "").replaceAll(" ", "").replaceAll("~", "") : str.trim().replaceAll("\\", "").replaceAll("~", "")
}

async function startProject() {
  let timeEnd = await settings.has("reset") && await config.has("token") ? 1000 : 5000
  new Interval(async (int) => {
    process.stdout.write('\x1Bc');
    process.stdout.write(`\r\u001b[38;5;${getRandomNumber(230)}m${shuruhatik}\u001b[0m\n\n\u001b[1mﻲﺒﻨﻟﺍ ﻰﻠﻋ ةﻼﺻﻭ رﺎﻔﻐﺘﺳﻻﺍ ﺮﺜﻛﻭ ،ﻪﻠﻟﺍ ﺮﻛﺫ َﺲﻨﺗ ﻻ\u001b[0m`);
    if (int.elapsedTime >= timeEnd) {
      int.pause();
      await runAction(true);
    }
  }, 100).start();
}

async function getPoints(userId, guildId) {
  const key = `points_${guildId}_${userId}`;
  if (!await pointsDB.has(key)) return 0;
  return await pointsDB.get(key);
}

async function addPoints(userId, guildId, amount) {
  const key = `points_${guildId}_${userId}`;
  const current = await getPoints(userId, guildId);
  await pointsDB.set(key, current + amount);
  return current + amount;
}

async function getCoins(userId, guildId) {
  const key = `coins_${guildId}_${userId}`;
  if (!await pointsDB.has(key)) return 0;
  return await pointsDB.get(key);
}

async function addCoins(userId, guildId, amount) {
  const key = `coins_${guildId}_${userId}`;
  const current = await getCoins(userId, guildId);
  await pointsDB.set(key, current + amount);
  return current + amount;
}

async function spendCoins(userId, guildId, amount) {
  const key = `coins_${guildId}_${userId}`;
  const current = await getCoins(userId, guildId);
  if (current < amount) return false;
  await pointsDB.set(key, current - amount);
  return true;
}

async function spendPoints(userId, guildId, amount) {
  const key = `points_${guildId}_${userId}`;
  const current = await getPoints(userId, guildId);
  if (current < amount) return false;
  await pointsDB.set(key, current - amount);
  return true;
}

async function getPlayerInventory(userId, guildId) {
  const key = `inventory_${guildId}_${userId}`;
  if (!await pointsDB.has(key)) return [];
  return await pointsDB.get(key);
}

async function addToInventory(userId, guildId, item) {
  const key = `inventory_${guildId}_${userId}`;
  const inventory = await getPlayerInventory(userId, guildId);
  inventory.push(item);
  await pointsDB.set(key, inventory);
}

async function removeFromInventory(userId, guildId, itemId) {
  const key = `inventory_${guildId}_${userId}`;
  const inventory = await getPlayerInventory(userId, guildId);
  const index = inventory.findIndex(item => item.id === itemId);
  if (index !== -1) {
    inventory.splice(index, 1);
    await pointsDB.set(key, inventory);
    return true;
  }
  return false;
}

async function hasItem(userId, guildId, itemId) {
  const inventory = await getPlayerInventory(userId, guildId);
  return inventory.some(item => item.id === itemId);
}

export { startProject, shuruhatik, sendDM, startRoundRoulette, disabledMultipleButtons, createRouletteImage, getMultipleButtons, pointsDB, getPoints, addPoints, getCoins, addCoins, spendCoins, spendPoints, getPlayerInventory, addToInventory, removeFromInventory, hasItem }