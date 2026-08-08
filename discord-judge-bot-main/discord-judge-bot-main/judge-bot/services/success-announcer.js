/**
 * @file success-announcer.js - Challenge Success Announcement Service
 * @description Automated celebration system that announces player achievements in designated Discord channels.
 *              Features milestone detection, role pinging, celebration reactions, and customizable embed formatting.
 *              Tracks completion milestones, handles difficulty-based styling, and provides comprehensive
 *              success broadcasting to encourage community engagement and recognition.
 * @version 1.1.0
 * @author gl0bal01
 * @since 2025-04-03
 */
const { EmbedBuilder } = require('discord.js');
const { recordSuccessAnnouncement, hasCompletedAnyGames, hasCompletedAllGames } = require('./database');

/**
 * Success Announcer service for ScoreBot
 * Announces player successes in a designated channel
 */
class SuccessAnnouncer {
  /**
   * Initialize the SuccessAnnouncer
   * @param {Object} client - Discord.js client
   * @param {Object} config - Configuration object containing success announcement settings
   * @param {Object} logger - Logger instance
   */
  constructor(client, config, logger) {
    this.client = client;
    this.logger = logger;
    
    // Extract configuration
    this.config = config.bot.success_announcements || {};
    this.enabled = this.config.enabled || false;
    this.channelId = this.config.channel_id;
    this.showRewardDetails = this.config.show_reward_details || false;
    this.pingEveryone = this.config.ping_everyone || false;
    this.pingRoleId = this.config.ping_role_id;
    this.milestoneMessages = this.config.milestone_messages || {};
    
    logger.info(`Success announcer initialized. Enabled: ${this.enabled}`);
  }

  /**
   * Announce a player's successful completion of a game
   * @param {Object} user - Discord user who completed the game
   * @param {Object} game - Game configuration
   * @param {number} pointsEarned - Points earned for this completion
   * @param {Object} dbUser - Database user object containing the user ID
   * @returns {Promise<Object|null>} - The sent message or null if failed
   */
  async announceSuccess(user, game, pointsEarned, dbUser) {
    if (!this.enabled || !this.channelId) {
      this.logger.debug('Success announcer is disabled or no channel configured. Skipping announcement.');
      return null;
    }
    
    try {
      // Get the target channel
      const channel = await this.client.channels.fetch(this.channelId);
      if (!channel) {
        this.logger.error(`Could not find success channel with ID ${this.channelId}`);
        return null;
      }
      
      // Check milestone completions using database functions
      const isFirstCompletion = !(await hasCompletedAnyGames(dbUser.id));
      const totalGames = Object.keys(this.config.games || {}).length;
      const hasCompletedAll = await hasCompletedAllGames(dbUser.id, totalGames);
      
      // Determine message content
      let content = '';
      if (this.pingEveryone) {
        content += '@everyone ';
      } else if (this.pingRoleId) {
        content += `<@&${this.pingRoleId}> `;
      }
      
      // Add milestone messages if applicable
      if (isFirstCompletion && this.milestoneMessages.first_completion) {
        content += this.milestoneMessages.first_completion.replace('{{user}}', user.toString());
      } else if (hasCompletedAll && this.milestoneMessages.all_completed) {
        content += this.milestoneMessages.all_completed.replace('{{user}}', user.toString());
      }
      
      // Create the success embed
      const embed = this._createSuccessEmbed(user, game, pointsEarned);
      
      // Send the announcement
      const message = await channel.send({ content, embeds: [embed] });
      
      // Add celebration reactions
      await this._addCelebrationReactions(message);
      
      // Record the announcement in the database
      await recordSuccessAnnouncement(
        dbUser.id,
        game.id,
        pointsEarned,
        channel.id,
        message.id
      );
      
      this.logger.info(`Success announcement sent for ${user.tag} completing "${game.name}"`);
      return message;
      
    } catch (error) {
      this.logger.error(`Error sending success announcement: ${error.message}`);
      return null;
    }
  }
  
  /**
   * Create an embed for the success announcement
   * @private
   */
  _createSuccessEmbed(user, game, pointsEarned) {
    // Get difficulty level
    const difficulty = game.difficulty || 1;
    const difficultyStars = '⭐'.repeat(difficulty);
    
    // Format points with any difficulty bonus
    const formattedPoints = difficulty > 1 
      ? `${pointsEarned} (includes ${(difficulty - 1) * 10}% bonus)`
      : `${pointsEarned}`;
    
    // Create the embed
    const embed = new EmbedBuilder()
      .setTitle('🎉 Challenge Completed!')
      .setDescription(`${user.toString()} has completed the "${game.name}" challenge!`)
      .setColor(this._getDifficultyColor(difficulty))
      .setTimestamp()
      .addFields(
        { name: 'Challenge', value: game.name, inline: true },
        { name: 'Author', value: game.author || 'Anonymous', inline: true },
        { name: 'Difficulty', value: difficultyStars, inline: true },
        { name: 'Points Earned', value: formattedPoints, inline: true }
      );
    
    // Add reward type if configured to show it
    if (this.showRewardDetails) {
      embed.addFields({
        name: 'Reward Type',
        value: this._formatRewardType(game.reward_type),
        inline: true
      });
    }
    
    // Set author with user's avatar
    if (user.avatar) {
      embed.setAuthor({ 
        name: user.username, 
        iconURL: user.displayAvatarURL() 
      });
    } else {
      embed.setAuthor({ name: user.username });
    }
    
    // Add footer
    embed.setFooter({ 
      text: 'ScoreBot • Complete challenges to see your name here!' 
    });
    
    return embed;
  }
  
  /**
   * Add celebration emoji reactions to the message
   * @private
   */
  async _addCelebrationReactions(message) {
    const celebrationEmojis = ['🎉', '🎊', '🏆', '👏'];
    
    try {
      // Add 2 random celebration emojis
      const selectedEmojis = this._getRandomItems(celebrationEmojis, 2);
      
      for (const emoji of selectedEmojis) {
        await message.react(emoji);
        // Small delay to avoid rate limits
        await new Promise(resolve => setTimeout(resolve, 500));
      }
    } catch (error) {
      this.logger.warn(`Failed to add reaction: ${error.message}`);
    }
  }
  
  /**
   * Get random items from an array
   * @private
   */
  _getRandomItems(array, count) {
    const shuffled = [...array].sort(() => 0.5 - Math.random());
    return shuffled.slice(0, Math.min(count, array.length));
  }
  
  /**
   * Get a color based on difficulty level
   * @private
   */
  _getDifficultyColor(difficulty) {
    // Discord color values
    const colors = {
      1: 0x4CAF50, // Green
      2: 0x2196F3, // Blue
      3: 0xFFC107, // Amber/Yellow
      4: 0xF44336  // Red
    };
    
    return colors[difficulty] || 0x9E9E9E; // Default to gray
  }
  
  /**
   * Format a reward type for display
   * @private
   */
  _formatRewardType(rewardType) {
    if (!rewardType) return 'Unknown';
    
    switch (rewardType.toLowerCase()) {
      case 'badgr':
        return '🏅 Digital Badge';
      case 'text':
        return '📁 Text Message';
      default:
        return rewardType.charAt(0).toUpperCase() + rewardType.slice(1);
    }
  }
}

module.exports = SuccessAnnouncer;