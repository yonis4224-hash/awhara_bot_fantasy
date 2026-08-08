/**
 * @file progress.js - User Progress Tracking Command
 * @description Discord slash command for displaying personalized user progress statistics including
 *              completion percentages, points earned, hints used, and visual progress indicators.
 *              Features color-coded progress bars, comprehensive statistics display, and encouragement
 *              messaging to promote continued engagement with challenges.
 * @version 1.1.0
 * @author gl0bal01
 * @since 2025-04-03
 */
const { SlashCommandBuilder, EmbedBuilder } = require('discord.js');
const { getUser, getUserStats } = require('../services/database');
const Validation = require('../utils/validation');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('judge-progress')
    .setDescription('View your current progress and points'),
  
  async execute(interaction, { config, logger }) {
    const userId = interaction.user.id;
    logger.info(`${interaction.user.tag} (${userId}) used /judge-progress`);
    
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
      
      // Get user stats
      const stats = await getUserStats(user.id);
      
      if (!stats) {
        await interaction.reply({
          content: '❌ Failed to retrieve your progress. Please try again later.',
          ephemeral: true
        });
        return;
      }
      
      // Calculate completion percentage
      const completionPercentage = stats.total_games > 0 
        ? Math.round((stats.completed_games / stats.total_games) * 100) 
        : 0;
      
      // Create a visual progress bar with color
      const progressBarLength = 20;
      const filledBars = Math.round((completionPercentage / 100) * progressBarLength);
      
      // Get color based on completion percentage
      const getColorForPercentage = (pct) => {
        if (pct < 30) return '🟥'; // Red
        if (pct < 70) return '🟨'; // Yellow
        return '🟩'; // Green
      };
      
      const progressColor = getColorForPercentage(completionPercentage);
      const progressBar = progressColor.repeat(filledBars) + '⬜'.repeat(progressBarLength - filledBars);
      
      // Create embed
      const embed = new EmbedBuilder()
        .setTitle(`${interaction.user.username}'s Progress`)
        .setColor(completionPercentage < 30 ? '#ff4444' : completionPercentage < 70 ? '#ffaa00' : '#44bb44')
        .setDescription(`Overall progress: ${progressBar} ${completionPercentage}%`)
        .addFields(
          { 
            name: 'Completed Challenges', 
            value: `${stats.completed_games || 0}/${stats.total_games || 0}`, 
            inline: true 
          },
          { 
            name: 'Total Points', 
            value: `${stats.total_points || 0}`, 
            inline: true 
          },
          { 
            name: 'Hints Used', 
            value: `${stats.total_hints || 0}`, 
            inline: true 
          },
          { 
            name: 'Total Attempts', 
            value: `${stats.total_attempts || 0}`, 
            inline: true 
          }
        );
      
      // Add email info if registered
      if (user.email) {
        embed.addFields({
          name: 'Registered Email',
          value: Validation.maskEmail(user.email)
        });
      }
      
      // Add game details if there are any
      if (stats.total_games > 0) {
        // Get games from config
        const games = config.games || {};
        
        // Add a field for completed games
        const completedGames = Object.entries(games)
          .filter(([gameId, game]) => {
            // Here we would need to check if the user completed this specific game
            // But we don't have that information in the stats, so we'll skip this for now
            // In a real implementation, you would query the database for completed games
            return false;
          })
          .map(([gameId, game]) => {
            return `✅ ${game.name}`;
          })
          .join('\n');
        
        if (completedGames) {
          embed.addFields({
            name: 'Completed Challenges',
            value: completedGames || 'None yet'
          });
        }
      }
      
      // Add footer with next steps
      embed.setFooter({
        text: 'Use `/judge-games` to view available challenges or `/judge-leaderboard` to see how you rank!'
      });
      
      await interaction.reply({
        embeds: [embed],
        ephemeral: true
      });
    } catch (error) {
      logger.error(`Error in progress command: ${error.message}`);
      await interaction.reply({
        content: '❌ An error occurred while retrieving your progress. Please try again later.',
        ephemeral: true
      });
    }
  },
};