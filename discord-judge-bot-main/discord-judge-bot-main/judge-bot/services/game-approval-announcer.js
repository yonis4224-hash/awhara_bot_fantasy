/**
 * @file game-approval-announcer.js - Game Approval Announcement Service
 * @description Automated notification system for newly approved challenges, broadcasting availability
 *              to community channels. Features customizable announcements with creator recognition,
 *              difficulty indicators, reward information, and interactive elements to encourage
 *              participation in fresh content. Supports role pinging and celebration reactions.
 * @version 1.1.0
 * @author gl0bal01
 * @since 2025-04-03
 */
const { EmbedBuilder } = require('discord.js');

/**
 * Game Approval Announcer service for ScoreBot
 * Announces newly approved games in a designated channel
 */
class GameApprovalAnnouncer {
  /**
   * Initialize the GameApprovalAnnouncer
   * @param {Object} client - Discord.js client
   * @param {Object} config - Configuration object containing game announcement settings
   * @param {Object} logger - Logger instance
   */
  constructor(client, config, logger) {
    this.client = client;
    this.logger = logger;
    
    // Extract configuration - default structure similar to success_announcements
    this.config = config.bot.game_announcements || {};
    this.enabled = this.config.enabled || false;
    this.channelId = this.config.channel_id;
    this.pingMakers = this.config.ping_makers || false;
    this.pingRoleId = this.config.ping_role_id;
    
    logger.info(`Game approval announcer initialized. Enabled: ${this.enabled}`);
  }

  /**
   * Announce a newly approved game
   * @param {Object} game - Game configuration
   * @param {string} approverTag - Tag of the admin who approved the game
   * @param {string} ownerId - Discord ID of the game creator
   * @returns {Promise<Object|null>} - The sent message or null if failed
   */
  async announceApproval(game, approverTag, ownerId) {
    if (!this.enabled || !this.channelId) {
      this.logger.debug('Game approval announcer is disabled or no channel configured. Skipping announcement.');
      return null;
    }
    
    try {
      // Get the target channel
      const channel = await this.client.channels.fetch(this.channelId);
      if (!channel) {
        this.logger.error(`Could not find game announcement channel with ID ${this.channelId}`);
        return null;
      }
      
      // Try to fetch the game owner if available
      let creatorMention = "a creative Maker";
      try {
        if (ownerId) {
          const owner = await this.client.users.fetch(ownerId);
          if (owner) {
            creatorMention = owner.toString();
          }
        }
      } catch (error) {
        this.logger.warn(`Could not fetch game creator with ID ${ownerId}: ${error.message}`);
      }
      
      // Determine message content
      let content = '';
      if (this.pingMakers) {
        content += `${creatorMention} `;
      } else if (this.pingRoleId) {
        content += `<@&${this.pingRoleId}> `;
      }
      
      content += `A new challenge has been approved and is now available to play!`;
      
      // Create the announcement embed
      const embed = this._createApprovalEmbed(game, approverTag, creatorMention);
      
      // Send the announcement
      const message = await channel.send({ content, embeds: [embed] });
      
      // Add celebration reactions
      await this._addCelebrationReactions(message);
      
      this.logger.info(`Game approval announcement sent for "${game.name}"`);
      return message;
      
    } catch (error) {
      this.logger.error(`Error sending game approval announcement: ${error.message}`);
      return null;
    }
  }
  
  /**
   * Create an embed for the approval announcement
   * @private
   * @param {Object} game - Game configuration
   * @param {string} approverTag - Tag of the admin who approved
   * @param {string} creatorMention - Mention of the game creator
   * @returns {EmbedBuilder} The created embed
   */
  _createApprovalEmbed(game, approverTag, creatorMention) {
    // Get difficulty level
    const difficulty = game.difficulty || 1;
    const difficultyStars = '⭐'.repeat(difficulty);
    
    // Create the embed
    const embed = new EmbedBuilder()
      .setTitle('🎮 New Challenge Available!')
      .setDescription(`"${game.name}" by ${creatorMention} is now available to play!`)
      .setColor(this._getDifficultyColor(difficulty))
      .setTimestamp()
      .addFields(
        { name: 'Challenge Name', value: game.name, inline: true },
        { name: 'Author', value: game.author || 'Anonymous', inline: true },
        { name: 'Difficulty', value: difficultyStars, inline: true },
        { name: 'Description', value: game.description || 'No description provided' }
      );
    
    // Add reward type information
    if (game.reward_type) {
      embed.addFields({
        name: 'Reward Type',
        value: this._formatRewardType(game.reward_type),
        inline: true
      });
    }
    
    // Add approved by information
    if (approverTag) {
      embed.addFields({
        name: 'Approved By',
        value: approverTag,
        inline: true
      });
    }
    
    // Add how to play info
    embed.addFields({
      name: 'How to Play',
      value: 'Use `/judge-submit ' + game.id + '` to submit your answer or `/judge-hint ' + game.id + '` if you need help!'
    });
    
    // Add footer
    embed.setFooter({ 
      text: 'ScoreBot • New challenges are regularly added!' 
    });
    
    return embed;
  }
  
  /**
   * Add celebration emoji reactions to the message
   * @private
   * @param {Object} message - Discord message object
   */
  async _addCelebrationReactions(message) {
    const celebrationEmojis = ['🎮', '🎯', '🎲', '🧩', '🏆'];
    
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
   * @param {Array} array - Array to select from
   * @param {number} count - Number of items to select
   * @returns {Array} Selected items
   */
  _getRandomItems(array, count) {
    const shuffled = [...array].sort(() => 0.5 - Math.random());
    return shuffled.slice(0, Math.min(count, array.length));
  }
  
  /**
   * Get a color based on difficulty level
   * @private
   * @param {number} difficulty - Game difficulty level
   * @returns {number} Color hex code as number
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
   * @param {string} rewardType - Reward type string
   * @returns {string} Formatted reward type
   */
  _formatRewardType(rewardType) {
    if (!rewardType) return 'Unknown';
    
    switch (rewardType.toLowerCase()) {
      case 'badgr':
        return '🏅 Digital Badge';
      case 'text':
        return '📝 Text Message';
      default:
        return rewardType.charAt(0).toUpperCase() + rewardType.slice(1);
    }
  }
}

module.exports = GameApprovalAnnouncer;
