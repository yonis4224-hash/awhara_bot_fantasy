/**
 * @file admin.js - Administrative Management Command
 * @description Comprehensive Discord slash command providing administrative functionality for bot management.
 *              Includes user progress reset capabilities, hint management, detailed statistics reporting,
 *              and game analytics. Features confirmation dialogs for destructive operations, role-based
 *              access control, and comprehensive logging. Restricted to users with administrator permissions.
 * @version 1.1.0
 * @author gl0bal01
 * @since 2025-04-03
 */
const { SlashCommandBuilder, EmbedBuilder, PermissionFlagsBits, ButtonBuilder, ButtonStyle, ActionRowBuilder } = require('discord.js');
const { getUser, resetUserProgress, getGameStats, getAllGamesStats, getProgress, adminManageHints, getDetailedUserStats } = require('../services/database');
const Validation = require('../utils/validation');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('judge-admin')
    .setDescription('Admin commands for ScoreBot')
    .setDefaultMemberPermissions(PermissionFlagsBits.Administrator) // Restricts to users with Administrator permission
    .addSubcommand(subcommand =>
      subcommand
        .setName('reset')
        .setDescription('Reset a user\'s progress for a game or all games')
        .addUserOption(option => 
          option.setName('user')
            .setDescription('The user to reset')
            .setRequired(true)
        )
        .addStringOption(option => {
          const gameOption = option
            .setName('game')
            .setDescription('Game ID to reset (leave empty to reset all games)')
            .setRequired(false)
            .setAutocomplete(true);
          // We'll add choices in the deploy-commands.js file
          return gameOption;
        })
    )
    .addSubcommand(subcommand =>
      subcommand
        .setName('stats')
        .setDescription('View statistics for a specific game or all games')
        .addStringOption(option => {
          const gameOption = option
            .setName('game')
            .setDescription('Game ID to get stats for (leave empty for all games)')
            .setRequired(false)
            .setAutocomplete(true); // not sure
          
          // We'll add choices in the deploy-commands.js file
          return gameOption;
        })
    )
    .addSubcommand(subcommand =>
      subcommand
        .setName('manage-hints')
        .setDescription('Add or remove hints for a user')
        .addUserOption(option => 
          option.setName('user')
            .setDescription('The user to manage hints for')
            .setRequired(true)
        )
        .addStringOption(option => {
          const gameOption = option
            .setName('game')
            .setDescription('Game ID to manage hints for')
            .setRequired(true)
            .setAutocomplete(true); //not sure
          
          // We'll add choices in the deploy-commands.js file
          return gameOption;
        })
        .addIntegerOption(option =>
          option.setName('action')
            .setDescription('Action to perform with hints')
            .setRequired(true)
            .addChoices(
              { name: 'Add one hint', value: 1 },
              { name: 'Remove one hint', value: -1 },
              { name: 'Reset hints to zero', value: 0 }
            )
        )
    )
    .addSubcommand(subcommand =>
      subcommand
        .setName('user-stats')
        .setDescription('View detailed statistics for a specific user')
        .addUserOption(option => 
          option.setName('user')
            .setDescription('The user to view statistics for')
            .setRequired(true)
        )
    ),

  async autocomplete(interaction, { config, logger }) {
    const focusedOption = interaction.options.getFocused(true);
    
    if (focusedOption.name === 'game') {
      try {
        // Get all games from config
        const games = config.games || {};
        
        // Filter based on user input
        const filtered = Object.entries(games)
          .filter(([gameId, game]) => 
            game.name.toLowerCase().includes(focusedOption.value.toLowerCase()) ||
            gameId.includes(focusedOption.value.toLowerCase())
          )
          .slice(0, 25) // Discord limits autocomplete to 25 options
          .map(([gameId, game]) => ({
            name: `${game.name} (${gameId})`,
            value: gameId
          }));
        
        await interaction.respond(filtered);
      } catch (error) {
        logger.error(`Error in autocomplete: ${error.message}`);
        await interaction.respond([]);
      }
    }
  },
  
  async execute(interaction, { config, logger }) {
    const userId = interaction.user.id;
    logger.info(`${interaction.user.tag} (${userId}) used /judge-admin`);
    
    try {
      // Check if user is an admin
      if (!Validation.isAdmin(userId, config.bot.admins)) {
        await interaction.reply({
          content: '❌ You do not have permission to use admin commands.',
          ephemeral: true
        });
        return;
      }
      
      // Handle subcommands
      const subcommand = interaction.options.getSubcommand();
      
      if (subcommand === 'reset') {
        // Get target user
        const targetUser = interaction.options.getUser('user');
        const gameId = interaction.options.getString('game');
        
        // Validate game ID if provided
        if (gameId && !Validation.isValidGameId(gameId, config)) {
          await interaction.reply({
            content: `❌ Invalid game ID: ${gameId}`,
            ephemeral: true
          });
          return;
        }
        
        // Get user from database
        const user = await getUser(targetUser.id);
        
        if (!user) {
          await interaction.reply({
            content: `❌ User ${targetUser.tag} is not registered in the system.`,
            ephemeral: true
          });
          return;
        }
        
        // Create confirmation message
        const confirmMessage = gameId 
          ? `Are you sure you want to reset progress for ${targetUser.tag} for game "${config.games[gameId].name}"?`
          : `Are you sure you want to reset ALL progress for ${targetUser.tag}? This cannot be undone.`;
        
        // Create confirmation buttons
        const confirmButton = new ButtonBuilder()
          .setCustomId('confirm-reset')
          .setLabel('Confirm Reset')
          .setStyle(ButtonStyle.Danger);
        
        const cancelButton = new ButtonBuilder()
          .setCustomId('cancel-reset')
          .setLabel('Cancel')
          .setStyle(ButtonStyle.Secondary);
        
        const row = new ActionRowBuilder()
          .addComponents(confirmButton, cancelButton);
        
        // Send confirmation message
        const response = await interaction.reply({
          content: confirmMessage,
          components: [row],
          ephemeral: true
        });
        
        // Create collector for button interactions
        const collector = response.createMessageComponentCollector({ 
          time: 30000 // 30 second timeout
        });
        
        collector.on('collect', async i => {
          // Only respond to the original user
          if (i.user.id !== interaction.user.id) {
            await i.reply({
              content: 'These buttons are not for you!',
              ephemeral: true
            });
            return;
          }
          
          if (i.customId === 'confirm-reset') {
            // Reset progress
            const result = await resetUserProgress(user.id, gameId);
            
            if (result.success) {
              await i.update({
                content: `✅ Successfully reset progress for ${targetUser.tag} ${gameId ? `for game "${config.games[gameId].name}"` : 'for all games'}.`,
                components: []
              });
            } else {
              await i.update({
                content: `❌ Error resetting progress: ${result.error}`,
                components: []
              });
            }
          } else if (i.customId === 'cancel-reset') {
            await i.update({
              content: '❌ Reset operation cancelled.',
              components: []
            });
          }
        });
        
        collector.on('end', async collected => {
          if (collected.size === 0) {
            // Timeout
            await response.edit({
              content: '❌ Reset operation timed out.',
              components: []
            }).catch(() => {});
          }
        });
      } else if (subcommand === 'manage-hints') {
        // Get parameters
        const targetUser = interaction.options.getUser('user');
        const gameId = interaction.options.getString('game');
        const action = interaction.options.getInteger('action');
        
        // Validate game ID
        if (!Validation.isValidGameId(gameId, config)) {
          await interaction.reply({
            content: `❌ Invalid game ID: ${gameId}`,
            ephemeral: true
          });
          return;
        }
        
        // Get user from database
        const user = await getUser(targetUser.id);
        
        if (!user) {
          await interaction.reply({
            content: `❌ User ${targetUser.tag} is not registered in the system.`,
            ephemeral: true
          });
          return;
        }
        
        // Get current progress to check if game is completed
        const progress = await getProgress(user.id, gameId);
        
        if (progress && progress.completed) {
          await interaction.reply({
            content: `❌ Cannot modify hints for ${targetUser.tag} as they have already completed the "${config.games[gameId].name}" challenge.`,
            ephemeral: true
          });
          return;
        }
        
        // Get action description
        let actionDescription;
        if (action === 1) actionDescription = "add one hint";
        else if (action === -1) actionDescription = "remove one hint";
        else actionDescription = "reset hints to zero";
        
        // Create confirmation message
        const confirmMessage = `Are you sure you want to ${actionDescription} for ${targetUser.tag} on "${config.games[gameId].name}"?`;
        
        // Create confirmation buttons
        const confirmButton = new ButtonBuilder()
          .setCustomId('confirm-hint-manage')
          .setLabel('Confirm')
          .setStyle(ButtonStyle.Primary);
        
        const cancelButton = new ButtonBuilder()
          .setCustomId('cancel-hint-manage')
          .setLabel('Cancel')
          .setStyle(ButtonStyle.Secondary);
        
        const row = new ActionRowBuilder()
          .addComponents(confirmButton, cancelButton);
        
        // Send confirmation message
        const response = await interaction.reply({
          content: confirmMessage,
          components: [row],
          ephemeral: true
        });
        
        // Create collector for button interactions
        const collector = response.createMessageComponentCollector({ 
          time: 30000 // 30 second timeout
        });
        
        collector.on('collect', async i => {
          // Only respond to the original user
          if (i.user.id !== interaction.user.id) {
            await i.reply({
              content: 'These buttons are not for you!',
              ephemeral: true
            });
            return;
          }
          
          if (i.customId === 'confirm-hint-manage') {
            // Manage hints
            const result = await adminManageHints(user.id, gameId, action);
            
            if (result.success) {
              let responseMessage;
              
              if (action === 0) {
                responseMessage = `✅ Successfully reset hint count to 0 for ${targetUser.tag} on "${config.games[gameId].name}". (Previous: ${result.previousHints})`;
              } else if (action === -1) {
                responseMessage = `✅ Successfully removed a hint for ${targetUser.tag} on "${config.games[gameId].name}". (${result.previousHints} → ${result.newHints})`;
              } else {
                responseMessage = `✅ Successfully added a hint for ${targetUser.tag} on "${config.games[gameId].name}". (${result.previousHints} → ${result.newHints})`;
              }
              
              await i.update({
                content: responseMessage,
                components: []
              });
            } else {
              await i.update({
                content: `❌ Error managing hints: ${result.error}`,
                components: []
              });
            }
          } else if (i.customId === 'cancel-hint-manage') {
            await i.update({
              content: '❌ Hint management operation cancelled.',
              components: []
            });
          }
        });
        
        collector.on('end', async collected => {
          if (collected.size === 0) {
            // Timeout
            await response.edit({
              content: '❌ Hint management operation timed out.',
              components: []
            }).catch(() => {});
          }
        });
      } else if (subcommand === 'user-stats') {
  // Get target user
  const targetUser = interaction.options.getUser('user');
  
  try {
    // Get detailed user stats
    const userStats = await getDetailedUserStats(targetUser.id);
    
    if (!userStats) {
      await interaction.reply({
        content: `❌ User ${targetUser.tag} has no stats available or is not registered.`,
        ephemeral: true
      });
      return;
    }
    
    // Create embed
    const embed = new EmbedBuilder()
      .setTitle(`Stats for ${targetUser.username}`)
      .setColor('#0099ff')
      .setThumbnail(targetUser.displayAvatarURL());
    
    // Add overall stats
    if (userStats.overallStats) {
      // Convert all values to numbers with fallback to 0
      const completedGames = Number(userStats.overallStats.completed_games || 0);
      const totalGames = Number(userStats.overallStats.total_games || 0);
      const totalPoints = Number(userStats.overallStats.total_points || 0);
      const totalHints = Number(userStats.overallStats.total_hints || 0);
      const totalAttempts = Number(userStats.overallStats.total_attempts || 0);
      
      embed.addFields(
        { 
          name: 'Completed Challenges', 
          value: `${completedGames}/${totalGames}`, 
          inline: true 
        },
        { 
          name: 'Total Points', 
          value: `${totalPoints}`, 
          inline: true 
        },
        { 
          name: 'Hints Used', 
          value: `${totalHints}`, 
          inline: true 
        },
        { 
          name: 'Total Attempts', 
          value: `${totalAttempts}`, 
          inline: true 
        }
      );
    }
    
    // Add registration info
    if (userStats.user) {
      let registrationDateStr = 'Unknown';
      try {
        if (userStats.user.registration_date) {
          const registrationDate = new Date(userStats.user.registration_date);
          registrationDateStr = registrationDate.toISOString().split('T')[0];
        }
      } catch (err) {
        logger.warn(`Error formatting registration date: ${err.message}`);
      }
      
      embed.addFields(
        {
          name: 'Registered Email',
          value: Validation.maskEmail(userStats.user.email),
          inline: true
        },
        { 
          name: 'Registration Date', 
          value: registrationDateStr, 
          inline: true 
        }
      );
    }
    
    // Add last active time
    if (userStats.lastActive) {
      let lastActiveStr = 'Unknown';
      try {
        const lastActiveDate = new Date(userStats.lastActive);
        lastActiveStr = lastActiveDate.toLocaleString();
      } catch (err) {
        logger.warn(`Error formatting last active date: ${err.message}`);
      }
      
      embed.addFields({
        name: 'Last Active',
        value: lastActiveStr
      });
    }
    
    // Add per-game progress
    if (userStats.gameProgress && userStats.gameProgress.length > 0) {
      embed.addFields({ name: '\u200B', value: '**Game Progress**' });
      
      for (const progress of userStats.gameProgress) {
        try {
          // Get game info from config
          const gameId = progress.game_id || 'unknown';
          const game = config.games[gameId];
          const gameName = game ? game.name : gameId;
          
          // Convert to numbers with fallback to 0
          const hintsUsed = Number(progress.hints_used || 0);
          const attempts = Number(progress.attempts || 0);
          const pointsEarned = Number(progress.points_earned || 0);
          
          let status = '🔷 Not Started';
          let details = '';
          
          if (progress.completed) {
            let completionDateStr = 'unknown date';
            try {
              if (progress.completion_date) {
                const completionDate = new Date(progress.completion_date);
                completionDateStr = completionDate.toISOString().split('T')[0];
              }
            } catch (err) {
              logger.warn(`Error formatting completion date: ${err.message}`);
            }
            
            status = `✅ Completed (${completionDateStr})`;
            details = `Points: ${pointsEarned}`;
          } else if (hintsUsed > 0 || attempts > 0) {
            status = '🔶 In Progress';
            details = `Hints: ${hintsUsed}, Attempts: ${attempts}`;
          }
          
          embed.addFields({
            name: gameName,
            value: `${status}\n${details}`
          });
        } catch (err) {
          logger.warn(`Error processing game progress: ${err.message}`);
        }
      }
    } else {
      embed.addFields({
        name: 'Game Progress',
        value: 'No game progress found.'
      });
    }
    
    await interaction.reply({
      embeds: [embed],
      ephemeral: true
    });
  } catch (error) {
    logger.error(`Error in user-stats command: ${error.message}`);
    await interaction.reply({
      content: '❌ An error occurred while retrieving user stats. Please try again later.',
      ephemeral: true
    });
  }
      } else if (subcommand === 'stats') {
        // Get game ID (optional)
        const gameId = interaction.options.getString('game');
        
        // If a specific game is requested
        if (gameId) {
          // Validate game ID
          if (!Validation.isValidGameId(gameId, config)) {
            await interaction.reply({
              content: `❌ Invalid game ID: ${gameId}`,
              ephemeral: true
            });
            return;
          }
          
          const game = config.games[gameId];
          
          // Get game stats
          const stats = await getGameStats(gameId);
          
          if (!stats) {
            await interaction.reply({
              content: `❌ Failed to retrieve stats for game ${gameId}.`,
              ephemeral: true
            });
            return;
          }
          
          // Create stats embed for single game
          const embed = new EmbedBuilder()
            .setTitle(`Stats for "${game.name}"`)
            .setColor('#0099ff')
            .addFields(
              { 
                name: 'Completions', 
                value: `${stats.completions || 0}`, 
                inline: true 
              },
              { 
                name: 'Players Attempted', 
                value: `${stats.players || 0}`, 
                inline: true 
              },
              { 
                name: 'Completion Rate', 
                value: `${stats.players > 0 ? Math.round((stats.completions / stats.players) * 100) : 0}%`, 
                inline: true 
              },
              { 
                name: 'Average Hints Used', 
                value: `${stats.avg_hints ? stats.avg_hints.toFixed(1) : 0}`, 
                inline: true 
              },
              { 
                name: 'Average Attempts', 
                value: `${stats.avg_attempts ? stats.avg_attempts.toFixed(1) : 0}`, 
                inline: true 
              }
            )
            .setFooter({
              text: `Game ID: ${gameId} | Difficulty: ${'⭐'.repeat(game.difficulty || 1)}`
            });
          
          await interaction.reply({
            embeds: [embed],
            ephemeral: true
          });
        } else {
          // Show stats for all games
          const embed = new EmbedBuilder()
            .setTitle('Stats for All Games')
            .setColor('#0099ff')
            .setDescription('Overview of all game statistics');
          
          // Get all game IDs from config
          const gameIds = Object.keys(config.games || {});
          
          if (gameIds.length === 0) {
            await interaction.reply({
              content: '❌ No games found in configuration.',
              ephemeral: true
            });
            return;
          }
          
          // Get stats for all games at once
          const allGamesStats = await getAllGamesStats();
          
          // Match stats with game configuration
          const allStats = [];
          for (const id of gameIds) {
            const game = config.games[id];
            // Find stats for this game ID
            const stats = allGamesStats.find(s => s.game_id === id) || {
              completions: 0,
              players: 0,
              avg_hints: 0,
              avg_attempts: 0
            };
            
            allStats.push({
              id,
              name: game.name,
              difficulty: game.difficulty || 1,
              stats
            });
          }
          
          // Sort by completion rate (highest first)
          allStats.sort((a, b) => {
            const rateA = a.stats.players > 0 ? (a.stats.completions / a.stats.players) : 0;
            const rateB = b.stats.players > 0 ? (b.stats.completions / b.stats.players) : 0;
            return rateB - rateA;
          });
          
          // Add total statistics
          const totalCompletions = allStats.reduce((sum, game) => sum + (game.stats.completions || 0), 0);
          const totalPlayers = allStats.reduce((sum, game) => sum + (game.stats.players || 0), 0);
          const avgCompletionRate = totalPlayers > 0 ? Math.round((totalCompletions / totalPlayers) * 100) : 0;
          
          embed.addFields(
            { 
              name: 'Total Games', 
              value: `${gameIds.length}`, 
              inline: true 
            },
            { 
              name: 'Total Completions', 
              value: `${totalCompletions}`, 
              inline: true 
            },
            { 
              name: 'Overall Completion Rate', 
              value: `${avgCompletionRate}%`, 
              inline: true 
            }
          );
          
          // Add individual game stats
          embed.addFields({ name: '\u200B', value: '**Individual Game Stats**' });
          
          for (const game of allStats) {
            const completionRate = game.stats.players > 0 
              ? Math.round((game.stats.completions / game.stats.players) * 100) 
              : 0;
            
            embed.addFields({
              name: `${game.name} ${'⭐'.repeat(game.difficulty)}`,
              value: `Completions: ${game.stats.completions || 0} / ${game.stats.players || 0} (${completionRate}%)\n` +
                    `Avg Hints: ${game.stats.avg_hints ? game.stats.avg_hints.toFixed(1) : 0} | ` +
                    `Avg Attempts: ${game.stats.avg_attempts ? game.stats.avg_attempts.toFixed(1) : 0}`
            });
          }
          
          await interaction.reply({
            embeds: [embed],
            ephemeral: true
          });
        }
      }
    } catch (error) {
      logger.error(`Error in admin command: ${error.message}`);
      await interaction.reply({
        content: '❌ An error occurred while executing the admin command.',
        ephemeral: true
      });
    }
  },
};
