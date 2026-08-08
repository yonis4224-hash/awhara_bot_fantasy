/**
 * @file submit.js - Challenge Answer Submission Command
 * @description Discord slash command that handles user answer submissions for challenges. Implements
 *              modal-based answer input, validates submissions against stored answers, calculates points
 *              based on hints used and difficulty, manages game completion status, and coordinates
 *              reward distribution and success announcements. Includes comprehensive error handling
 *              and administrative notifications.
 * @version 1.1.0
 * @author gl0bal01
 * @since 2025-04-03
 */
const { SlashCommandBuilder, EmbedBuilder, ModalBuilder, TextInputBuilder, TextInputStyle, ActionRowBuilder } = require('discord.js');
const { getUser, getProgress, recordAttempt, completeGameAtomic, getUserStats } = require('../services/database');
const PointsCalculator = require('../services/points');
const RewardService = require('../services/reward');
const Validation = require('../utils/validation');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('judge-submit')
    .setDescription('Submit your answer to a challenge')
    .addStringOption(option => {
      const gameOption = option
        .setName('game')
        .setDescription('Game ID to submit an answer for')
        .setRequired(true)
        .setAutocomplete(true);
      
      // We'll add choices in the deploy-commands.js file
      return gameOption;
    }),
  
  async execute(interaction, { client, config, logger, successAnnouncer }) {
    const userId = interaction.user.id;
    const gameId = interaction.options.getString('game');
    
    logger.info(`${interaction.user.tag} (${userId}) used /judge-submit for game ${gameId}`);
    
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
      
      // Create a modal for answer submission
      const modal = new ModalBuilder()
        .setCustomId(`submit-answer-${gameId}`)
        .setTitle(`Submit Your Answer`);
        //.setTitle(`Submit Answer for ${game.name.substring(0, 45)}`);
      
      // Add answer input field
      const answerInput = new TextInputBuilder()
        .setCustomId('answer-input')
        .setLabel('Your Answer')
        .setPlaceholder('Enter your answer here')
        .setStyle(TextInputStyle.Paragraph)
        .setRequired(true);
      
      // Create action row with the input field
      const actionRow = new ActionRowBuilder().addComponents(answerInput);
      modal.addComponents(actionRow);
      
      // Show the modal
      await interaction.showModal(modal);
      
      // Wait for modal submission
      const submission = await interaction.awaitModalSubmit({
        time: 300000, // Wait for 5 minutes
        filter: i => i.customId === `submit-answer-${gameId}`
      }).catch(() => null);
      
      if (!submission) {
        logger.info(`${interaction.user.tag} did not submit an answer for game ${gameId}`);
        return;
      }
      
      // Get the answer from submission
      const userAnswer = submission.fields.getTextInputValue('answer-input');
      
      // Record the attempt
      await recordAttempt(user.id, gameId);
      
      // Check if answer is correct
      const isCorrect = Validation.isCorrectAnswer(userAnswer, game.answer);
      
      if (isCorrect) {
        // Calculate points
        const hintsUsed = progress ? progress.hints_used : 0;
        const pointsCalculator = new PointsCalculator(config);
        const pointsEarned = pointsCalculator.calculatePoints(hintsUsed, game);
        const formattedPoints = pointsCalculator.formatPointsDisplay(pointsEarned, game);
        
        // Update database to mark game as completed
        const completionResult = await completeGameAtomic(user.id, gameId, pointsEarned);
        if (!completionResult.success) {
          if (completionResult.alreadyCompleted) {
            await submission.reply({
              content: `✅ You have already completed the "${game.name}" challenge!`,
              ephemeral: true
            });
            return;
          }
          throw new Error(completionResult.error || 'Failed to complete game');
        }
        
        // Issue reward
        const rewardService = new RewardService(config);
        let rewardInfo;
        
        try {
          // Ensure game object has id property
          const gameWithId = {
            ...game,
            id: gameId  // Explicitly add the gameId
          };
          
          rewardInfo = await rewardService.issueReward(user, gameWithId);
        } catch (error) {
          logger.error(`Error issuing reward for ${gameId} to user ${userId}: ${error.message}`);
          rewardInfo = {
            message: 'There was an error issuing your reward. An administrator will be notified.',
            type: 'error'
          };
        }
        
        // Create success embed
        const successEmbed = new EmbedBuilder()
          .setTitle(`🎉 Challenge Completed!`)
          .setColor('#00FF00')
          .setDescription(`Congratulations! You have successfully completed the "${game.name}" challenge.`)
          .addFields(
            { 
              name: 'Points Earned', 
              value: formattedPoints 
            }
          );

        // Add reward information
        if (rewardInfo) {
          if (rewardInfo.type === 'badgr') {
            successEmbed.addFields({
              name: 'Reward',
              value: '🏆 Digital Badge awarded! Check the email you registered with for badge delivery details.'
            });
          } else if (rewardInfo.type === 'text') {
            // Display the text reward directly
            successEmbed.addFields({
              name: 'Reward',
              value: rewardInfo.data.text
            });
          } else {
            successEmbed.addFields({
              name: 'Reward',
              value: rewardInfo.message
            });
          }
}
        
        // Add footer with next steps
        successEmbed.setFooter({
          text: 'Use `/judge-progress` to view your overall progress or `/judge-games` to find your next challenge!'
        });
        
        await submission.reply({
          embeds: [successEmbed],
          ephemeral: true
        });
        
        // NEW CODE: Announce the success in the designated channel
        if (successAnnouncer) {
          try {
            // Pass the database user object to the success announcer
            await successAnnouncer.announceSuccess(
              interaction.user,
              {...game, id: gameId},  // Add the game ID to the game object
              pointsEarned,
              user  // Database user object
            );
          } catch (error) {
            logger.error(`Error announcing success: ${error.message}`);
            // Continue even if announcement fails - don't impact user experience
          }
        }
        
        // Notify admins about the completion (optional)
        if (config.bot.admins && config.bot.admins.length > 0) {
          // Find a DM channel with each admin
          for (const adminId of config.bot.admins) {
            try {
              const admin = await client.users.fetch(adminId);
              if (admin) {
                const adminEmbed = new EmbedBuilder()
                  .setTitle(`Challenge Completion`)
                  .setColor('#00FF00')
                  .setDescription(`User ${interaction.user.tag} has completed "${game.name}"`)
                  .addFields(
                    { name: 'Game ID', value: gameId },
                    { name: 'Points Earned', value: formattedPoints },
                    { name: 'Hints Used', value: hintsUsed.toString() }
                  );
                
                await admin.send({ embeds: [adminEmbed] }).catch(() => {
                  // Silently fail if unable to DM the admin
                });
              }
            } catch (error) {
              logger.error(`Error notifying admin ${adminId}: ${error.message}`);
            }
          }
        }
      } else {
        // Create incorrect answer embed
        const incorrectEmbed = new EmbedBuilder()
          .setTitle(`❌ Incorrect Answer`)
          .setColor('#FF0000')
          .setDescription(`Your answer for "${game.name}" is incorrect. Please try again!`)
          .addFields(
            { 
              name: 'Need Help?', 
              value: `Use \`/judge-hint ${gameId}\` to get a hint!` 
            }
          );
        
        await submission.reply({
          embeds: [incorrectEmbed],
          ephemeral: true
        });
      }
    } catch (error) {
      logger.error(`Error in submit command: ${error.message}`);
      
      if (interaction.replied || interaction.deferred) {
        await interaction.followUp({
          content: '❌ An error occurred while processing your submission. Please try again later.',
          ephemeral: true
        });
      } else {
        await interaction.reply({
          content: '❌ An error occurred while processing your submission. Please try again later.',
          ephemeral: true
        });
      }
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
