/**
 * @file help.js - Help Documentation Command
 * @description Simple Discord slash command that displays comprehensive help information for all
 *              available bot commands. Provides users with command descriptions, usage instructions,
 *              and getting started guidance in a clean, organized embed format. Essential for user
 *              onboarding and command discovery.
 * @version 1.1.0
 * @author gl0bal01
 * @since 2025-04-03
 */
const { SlashCommandBuilder, EmbedBuilder } = require('discord.js');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('judge-help')
    .setDescription('Display help information for ScoreBot commands'),
  
  async execute(interaction, { config, logger }) {
    logger.info(`${interaction.user.tag} (${interaction.user.id}) used /judge-help`);
    
    const embed = new EmbedBuilder()
      .setTitle('ScoreBot Help')
      .setColor('#0099ff')
      .setDescription('Complete challenges to earn badges and rewards!')
      .addFields(
        { 
          name: '/judge-register', 
          value: 'Register your email to receive badges' 
        },
        { 
          name: '/judge-games', 
          value: 'View available challenges and their descriptions' 
        },
        { 
          name: '/judge-hint', 
          value: 'Request a hint for a specific challenge (costs points)' 
        },
        { 
          name: '/judge-submit', 
          value: 'Submit your answer to a challenge' 
        },
        { 
          name: '/judge-progress', 
          value: 'View your current progress and points' 
        },
        { 
          name: '/judge-leaderboard', 
          value: 'View the global leaderboard' 
        },
        { 
          name: '/judge-health', 
          value: 'Check the bot status' 
        }
      )
      .setFooter({ 
        text: 'Start by registering and viewing available games!' 
      });
    
    // Send as an ephemeral message (only visible to the user)
    await interaction.reply({ 
      embeds: [embed], 
      ephemeral: true 
    });
  },
};