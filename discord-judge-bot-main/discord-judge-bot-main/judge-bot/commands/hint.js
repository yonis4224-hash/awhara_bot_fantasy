/**
 * @file hint.js - Challenge Hint System Command
 * @description Discord slash command for requesting hints on challenges with point cost calculation.
 *              Features confirmation dialogs, point cost preview, automatic hint progression tracking,
 *              and database integration for hint usage management. Includes comprehensive validation
 *              and user-friendly cost transparency before hint delivery.
 * @version 1.1.0
 * @author gl0bal01
 * @since 2025-04-03
 */
const { SlashCommandBuilder, EmbedBuilder, ButtonBuilder, ButtonStyle, ActionRowBuilder } = require('discord.js');
const { getUser, getProgress, updateHintUsage } = require('../services/database');
const PointsCalculator = require('../services/points');
const Validation = require('../utils/validation');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('judge-hint')
    .setDescription('Request a hint for a specific challenge (costs points)')
    .addStringOption(option => {
      const gameOption = option
        .setName('game')
        .setDescription('Game ID to get a hint for')
        .setRequired(true)
        .setAutocomplete(true); // Use autocomplete instead of choices
      
      return gameOption;
    }),
  
  async execute(interaction, { config, logger }) {
    const userId = interaction.user.id;
    const gameId = interaction.options.getString('game');
    
    logger.info(`${interaction.user.tag} (${userId}) used /judge-hint for game ${gameId}`);
    
    try {
      // Check if user is registered
      const user = await getUser(userId);
      
      if (!user) {
        await interaction.reply({
          content: '❌ You need to register first! Use `/judge-register` to get started.',
          ephemeral: true
        });
        return;
      }
      
      // Check if game exists
      if (!Validation.isValidGameId(gameId, config)) {
        await interaction.reply({
          content: `❌ Invalid game ID: ${gameId}. Use \`/judge-games\` to see available challenges.`,
          ephemeral: true
        });
        return;
      }
      
      const game = config.games[gameId];
      
      // Get user's current progress
      const progress = await getProgress(user.id, gameId);
      
      // Check if game is already completed
      if (progress && progress.completed) {
        await interaction.reply({
          content: `✅ You have already completed the "${game.name}" challenge!`,
          ephemeral: true
        });
        return;
      }
      
      // Check if we have more hints available
      const hintsUsed = progress ? progress.hints_used : 0;
      
      if (!game.hints || !Array.isArray(game.hints) || hintsUsed >= game.hints.length) {
        await interaction.reply({
          content: `❌ No more hints available for "${game.name}"!`,
          ephemeral: true
        });
        return;
      }
      
      // Calculate the cost of this hint
      const pointsCalculator = new PointsCalculator(config);
      const hintCost = pointsCalculator.calculateNextHintCost(hintsUsed);
      const maxPointsPossibleAfterHint = pointsCalculator.calculateMaxPossiblePoints(hintsUsed + 1, game);
      
      // Create confirmation buttons
      const confirmButton = new ButtonBuilder()
        .setCustomId('confirm-hint')
        .setLabel('Get Hint')
        .setStyle(ButtonStyle.Primary);
      
      const cancelButton = new ButtonBuilder()
        .setCustomId('cancel-hint')
        .setLabel('Cancel')
        .setStyle(ButtonStyle.Secondary);
      
      const row = new ActionRowBuilder()
        .addComponents(confirmButton, cancelButton);
      
      // Create embed for hint confirmation
      const embed = new EmbedBuilder()
        .setTitle(`Hint Confirmation for "${game.name}"`)
        .setColor('#FFA500')
        .setDescription(`This will be hint #${hintsUsed + 1} of ${game.hints.length}`)
        .addFields(
          { 
            name: 'Cost', 
            value: `This hint will cost you ${hintCost} points` 
          },
          { 
            name: 'Maximum Points Possible After Hint', 
            value: `${maxPointsPossibleAfterHint} points` 
          }
        )
        .setFooter({ 
          text: 'Hints cannot be undone and will permanently reduce your potential points for this challenge.' 
        });
      
      // Send confirmation message
      const response = await interaction.reply({
        embeds: [embed],
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
        
        // Handle button interactions
        if (i.customId === 'confirm-hint') {
          // Update hint usage in database
          const hintResult = await updateHintUsage(user.id, gameId);
          
          if (!hintResult.success) {
            await i.update({
              content: `❌ Error retrieving hint: ${hintResult.error}`,
              embeds: [],
              components: []
            });
            return;
          }
          
          // Get the hint text
          const updatedHintsUsed = hintResult.hintsUsed;
          const hintText = game.hints[updatedHintsUsed - 1]; // -1 because we just incremented
          
          // Calculate new max possible points
          const newMaxPoints = pointsCalculator.calculateMaxPossiblePoints(updatedHintsUsed, game);
          
          // Create hint embed
          const hintEmbed = new EmbedBuilder()
            .setTitle(`Hint for "${game.name}"`)
            .setColor('#00BFFF')
            .setDescription(`Here is your hint:`)
            .addFields(
              { 
                name: `Hint #${updatedHintsUsed}`, 
                value: hintText 
              },
              { 
                name: 'Hints Used', 
                value: `${updatedHintsUsed} of ${game.hints.length}` 
              },
              { 
                name: 'Maximum Points Possible', 
                value: `${newMaxPoints} points` 
              }
            )
            .setFooter({ 
              text: 'Use `/judge-submit ' + gameId + '` to submit your answer when ready.' 
            });
          
          await i.update({
            embeds: [hintEmbed],
            components: []
          });
        } else if (i.customId === 'cancel-hint') {
          await i.update({
            content: 'Hint request canceled.',
            embeds: [],
            components: []
          });
        }
      });
      
      collector.on('end', async collected => {
        if (collected.size === 0) {
          // Timeout - no button was pressed
          await response.edit({
            content: 'Hint request timed out.',
            embeds: [],
            components: []
          }).catch(() => {
            // Silently fail if message was deleted
          });
        }
      });
    } catch (error) {
      logger.error(`Error in hint command: ${error.message}`);
      await interaction.reply({
        content: '❌ An error occurred while retrieving the hint. Please try again later.',
        ephemeral: true
      });
    }
  },
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
};