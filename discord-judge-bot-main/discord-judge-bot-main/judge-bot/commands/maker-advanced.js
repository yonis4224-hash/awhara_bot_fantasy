/**
 * @file maker-advanced.js - Advanced settings for challenge creators
 * @description Provides advanced configuration options for Maker role users
 * @version 1.1.0
 * @author gl0bal01
 * @since 2025-04-03
 */
const { SlashCommandBuilder, EmbedBuilder, PermissionFlagsBits, ModalBuilder, 
  TextInputBuilder, TextInputStyle, ActionRowBuilder, ButtonBuilder, ButtonStyle } = require('discord.js');
const fs = require('fs').promises;
const path = require('path');
const yaml = require('js-yaml');
const Validation = require('../utils/validation');

// Path to the games directory where individual game files will be stored
const GAMES_DIR = path.join(__dirname, '../config/games');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('maker-advanced')
    .setDescription('Advanced settings for challenge creators (Maker role only)')
    .setDefaultMemberPermissions(null)
    .addSubcommand(subcommand =>
      subcommand
        .setName('settings')
        .setDescription('Configure advanced settings for one of your games')
        .addStringOption(option => 
          option.setName('game_id')
            .setDescription('ID of the game to configure')
            .setRequired(true)
            .setAutocomplete(true)
        )
    )
    .addSubcommand(subcommand =>
      subcommand
        .setName('reward')
        .setDescription('Configure reward settings for one of your games')
        .addStringOption(option => 
          option.setName('game_id')
            .setDescription('ID of the game to configure')
            .setRequired(true)
            .setAutocomplete(true)
        )
        .addStringOption(option =>
          option.setName('reward_type')
            .setDescription('Type of reward to configure')
            .setRequired(true)
            .addChoices(
              { name: 'Digital Badge (Badgr)', value: 'badgr' },
              { name: 'Text Message', value: 'text' }
            )
        )
    ),

  // Set up autocomplete for game selection
  async autocomplete(interaction, { config, logger }) {
    const focusedOption = interaction.options.getFocused(true);

    if (focusedOption.name === 'game_id') {
      try {
        const userGames = await getUserOwnedGames(interaction.user.id);
        
        const filtered = userGames.filter(game => 
          game.id.includes(focusedOption.value) || 
          game.name.toLowerCase().includes(focusedOption.value.toLowerCase())
        );
        
        await interaction.respond(
          filtered.map(game => ({
            name: `${game.name} (${game.id})`,
            value: game.id
          })).slice(0, 25)
        );
      } catch (error) {
        logger.error(`Error in autocomplete: ${error.message}`);
        await interaction.respond([]);
      }
    }
  },

async execute(interaction, { client, config, logger }) {
  const userId = interaction.user.id;
  const subcommand = interaction.options.getSubcommand();

  logger.info(`${interaction.user.tag} (${userId}) used /maker-advanced ${subcommand}`);

  try {
    // Check if user has the Maker role OR is an admin
    const member = interaction.member;
    const makerRoleId = config.bot.maker_role_id;
    const hasMakerRole = makerRoleId ? member.roles.cache.has(makerRoleId) : member.roles.cache.some(role => role.name.toLowerCase() === 'maker');
    const isAdmin = Validation.isAdmin(userId, config.bot.admins);

    if (!hasMakerRole && !isAdmin) {
      await interaction.reply({
        content: '❌ You need the "Maker" role to use these commands.',
        ephemeral: true
      });
      return;
    }  

      // Ensure games directory exists
      await fs.mkdir(GAMES_DIR, { recursive: true });

      // Handle subcommands
      switch (subcommand) {
        case 'settings':
          await handleAdvancedSettings(interaction, config, logger);
          break;
        case 'reward':
          await handleRewardSettings(interaction, config, logger);
          break;
      }
    } catch (error) {
      logger.error(`Error in maker-advanced command: ${error.message}`);

      if (interaction.replied || interaction.deferred) {
        await interaction.followUp({
          content: '❌ An error occurred while processing your request. Please try again later.',
          ephemeral: true
        });
      } else {
        await interaction.reply({
          content: '❌ An error occurred while processing your request. Please try again later.',
          ephemeral: true
        });
      }
    }
  }
};

/**
* Handle advanced settings for a game
* @param {Object} interaction - Discord interaction object
* @param {Object} config - Bot configuration 
* @param {Object} logger - Logger instance
* @returns {Promise<void>}
*/
async function handleAdvancedSettings(interaction, config, logger) {
  const gameId = interaction.options.getString('game_id');

  // Get the game data
  try {
    const gameData = await getGameById(gameId);

    if (!gameData) {
      await interaction.reply({
        content: `❌ Game with ID "${gameId}" not found.`,
        ephemeral: true
      });
      return;
    }

    // Check ownership
    if (gameData.owner_id !== interaction.user.id && !Validation.isAdmin(interaction.user.id, config.bot.admins)) {
      await interaction.reply({
        content: `❌ You don't have permission to edit this game. Only the creator (${gameData.author}) can edit it.`,
        ephemeral: true
      });
      return;
    }

    // Create a modal for advanced settings
    const modal = new ModalBuilder()
      .setCustomId(`adv-settings-modal-${gameId}`)
      .setTitle(`Advanced Settings: ${gameData.name}`);

    // Badge Class ID input (for Badgr)
    const badgeClassInput = new TextInputBuilder()
      .setCustomId('badge-class-id')
      .setLabel('Badgr Badge Class ID (for Badgr rewards)')
      .setValue(gameData.badge_class_id || '')
      .setStyle(TextInputStyle.Short)
      .setRequired(false);

    // Text Reward input
    const textRewardInput = new TextInputBuilder()
      .setCustomId('text-reward')
      .setLabel('Text Reward (for Text rewards)')
      .setValue(gameData.reward_text || '')
      .setStyle(TextInputStyle.Paragraph)
      .setRequired(false);

    // Custom Field 1
    const customField1Input = new TextInputBuilder()
      .setCustomId('custom-field-1')
      .setLabel('Custom Field 1 (optional)')
      .setValue(gameData.custom_field_1 || '')
      .setStyle(TextInputStyle.Short)
      .setRequired(false);

    // Additional Notes
    const notesInput = new TextInputBuilder()
      .setCustomId('notes')
      .setLabel('Additional Notes (only visible to you)')
      .setValue(gameData.notes || '')
      .setStyle(TextInputStyle.Paragraph)
      .setRequired(false);

    // Add inputs to the modal
    modal.addComponents(
      new ActionRowBuilder().addComponents(badgeClassInput),
      new ActionRowBuilder().addComponents(textRewardInput),
      new ActionRowBuilder().addComponents(customField1Input),
      new ActionRowBuilder().addComponents(notesInput)
    );

    // Show the modal
    await interaction.showModal(modal);

    // Wait for modal submission
    const submission = await interaction.awaitModalSubmit({
      time: 300000, // 5 minutes
      filter: i => i.customId === `adv-settings-modal-${gameId}`
    }).catch(() => null);

    if (!submission) {
      logger.info(`${interaction.user.tag} did not submit the advanced settings form`);
      return;
    }

    // Get values from form
    const badgeClassId = submission.fields.getTextInputValue('badge-class-id').trim();
    const textReward = submission.fields.getTextInputValue('text-reward').trim();
    const customField1 = submission.fields.getTextInputValue('custom-field-1').trim();
    const notes = submission.fields.getTextInputValue('notes').trim();

    // Update game object
    const updatedGame = {
      ...gameData
    };

    // Only set fields that have values
    if (badgeClassId) updatedGame.badge_class_id = badgeClassId;
    if (textReward) updatedGame.reward_text = textReward;
    if (customField1) updatedGame.custom_field_1 = customField1;
    if (notes) updatedGame.notes = notes;

    // Delete fields explicitly if they were cleared
    if (!badgeClassId && 'badge_class_id' in updatedGame) delete updatedGame.badge_class_id;
    if (!textReward && 'reward_text' in updatedGame) delete updatedGame.reward_text;
    if (!customField1 && 'custom_field_1' in updatedGame) delete updatedGame.custom_field_1;
    if (!notes && 'notes' in updatedGame) delete updatedGame.notes;

    // Set reward type based on which field was filled
    if (badgeClassId && !textReward) {
      updatedGame.reward_type = 'badgr';
    } else if (textReward && !badgeClassId) {
      updatedGame.reward_type = 'text';
    } else if (!badgeClassId && !textReward) {
      // If neither field is filled, don't change the reward type
    } else {
      // If both fields are filled, use the existing reward type or default to badgr
      if (!updatedGame.reward_type) {
        updatedGame.reward_type = 'badgr';
      }
    }

    // Write updated game to file
    const gameFilePath = Validation.resolveGamePath(gameId, GAMES_DIR);
    if (!gameFilePath) {
      await submission.reply({
        content: '❌ Invalid game ID.',
        ephemeral: true
      });
      return;
    }

    try {
      // Remove the 'id' property before saving (it's redundant with the YAML key)
      const { id, ...gameToSave } = updatedGame;

      await fs.writeFile(
        gameFilePath,
        yaml.dump({ [gameId]: gameToSave }),
        'utf8'
      );

      // Reload the games configuration
      await reloadGamesConfig(logger);

      // Send success message
      const embed = new EmbedBuilder()
        .setTitle('⚙️ Advanced Settings Updated')
        .setColor('#00BFFF')
        .setDescription(`Advanced settings for "${updatedGame.name}" have been updated!`);

      // Add reward configuration info
      let rewardInfo = '❌ No reward configuration set';
      if (badgeClassId) {
        rewardInfo = '✅ Badgr Badge Class ID set';
      } else if (textReward) {
        rewardInfo = '✅ Text Reward set';
      }
      
      embed.addFields({ 
        name: 'Reward Configuration', 
        value: rewardInfo
      });

      if (customField1) {
        embed.addFields({
          name: 'Custom Fields',
          value: '✅ Custom Field 1 set'
        });
      }

      if (notes) {
        embed.addFields({
          name: 'Private Notes',
          value: '✅ Additional notes saved'
        });
      }

      await submission.reply({
        embeds: [embed],
        ephemeral: true
      });
    } catch (error) {
      logger.error(`Error updating advanced settings: ${error.message}`);
      await submission.reply({
        content: '❌ An error occurred while updating the settings. Please try again later.',
        ephemeral: true
      });
    }
  } catch (error) {
    logger.error(`Error getting game data: ${error.message}`);
    await interaction.reply({
      content: '❌ An error occurred while retrieving the game data. Please try again later.',
      ephemeral: true
    });
  }
}

/**
* Get all games from the games directory
* @returns {Promise<Array>} Array of game objects
*/
async function getAllGames() {
  try {
    // Ensure games directory exists
    await fs.mkdir(GAMES_DIR, { recursive: true });

    const files = await fs.readdir(GAMES_DIR);
    const gameFiles = files.filter(file => file.endsWith('.yaml'));

    const games = [];

    for (const file of gameFiles) {
      try {
        const gameId = path.basename(file, '.yaml');
        const content = await fs.readFile(path.join(GAMES_DIR, file), 'utf8');
        const gameData = yaml.load(content, { schema: yaml.DEFAULT_SCHEMA });
        
        if (gameData && gameData[gameId]) {
          games.push({
            id: gameId,
            ...gameData[gameId]
          });
        }
      } catch (error) {
        console.error(`Error parsing game file ${file}:`, error);
      }
    }

    return games;
  } catch (error) {
    console.error('Error getting all games:', error);
    return [];
  }
}

/**
* Get games owned by a specific user
* @param {string} userId - Discord user ID
* @returns {Promise<Array>} Array of game objects
*/
async function getUserOwnedGames(userId) {
  const allGames = await getAllGames();
  return allGames.filter(game => game.owner_id === userId);
}

/**
* Get a specific game by ID
* @param {string} gameId - Game ID
* @returns {Promise<Object|null>} Game object or null
*/
async function getGameById(gameId) {
  try {
    const gameFilePath = Validation.resolveGamePath(gameId, GAMES_DIR);
    if (!gameFilePath) return null;
    const content = await fs.readFile(gameFilePath, 'utf8');
    const gameData = yaml.load(content, { schema: yaml.DEFAULT_SCHEMA });

    if (gameData && gameData[gameId]) {
      return {
        id: gameId,
        ...gameData[gameId]
      };
    }

    return null;
  } catch (error) {
    console.error(`Error getting game ${gameId}:`, error);
    return null;
  }
}

/**
* Reload the games configuration
* @param {Object} logger - Logger instance
* @returns {Promise<boolean>} Success status
*/
async function reloadGamesConfig(logger) {
  try {
    // Get all games
    const games = await getAllGames();

    // Only include approved games in the main config
    const approvedGames = games.filter(game => 
      game.approved && !game.disabled && !game.rejected
    );

    // Create a merged config object
    const mergedConfig = {
      games: {}
    };

    // First load the existing games.yaml if it exists to preserve any manually added games
    try {
      const existingConfigPath = path.join(__dirname, '../config/games.yaml');
      const existingContent = await fs.readFile(existingConfigPath, 'utf8');
      const existingConfig = yaml.load(existingContent, { schema: yaml.DEFAULT_SCHEMA });
      
      if (existingConfig && existingConfig.games) {
        // Copy existing games that aren't from the maker system
        for (const [gameId, gameData] of Object.entries(existingConfig.games)) {
          // Check if this is not a maker-created game (no owner_id)
          if (!gameData.owner_id) {
            mergedConfig.games[gameId] = gameData;
          }
        }
      }
    } catch (error) {
      console.log('No existing games.yaml found or error reading it:', error.message);
    }

    // Add each approved maker game to the config
    for (const game of approvedGames) {
      const { id, ...gameData } = game;
      
      // Create a clean version of the game data for the config
      // This removes internal maker properties that shouldn't be exposed
      const cleanGameData = {
        name: gameData.name,
        description: gameData.description,
        author: gameData.author,
        difficulty: gameData.difficulty || 1,
        reward_type: gameData.reward_type || 'badgr',
        hints: gameData.hints || []
      };
      
      // Add reward-specific properties
      if (gameData.reward_type === 'badgr' && gameData.badge_class_id) {
        cleanGameData.badge_class_id = gameData.badge_class_id;
      } else if (gameData.reward_type === 'text' && gameData.reward_text) {
        cleanGameData.reward_text = gameData.reward_text;
      }
      
      // Add reward description if available
      if (gameData.reward_description) {
        cleanGameData.reward_description = gameData.reward_description;
      }
      
      // Add to the merged config
      mergedConfig.games[id] = cleanGameData;
    }

    // Write the merged config to the main games.yaml file
    await fs.writeFile(
      path.join(__dirname, '../config/games.yaml'),
      yaml.dump(mergedConfig),
      'utf8'
    );

    if (logger) {
      logger.info(`Reloaded games config: ${Object.keys(mergedConfig.games).length} games available`);
    } else {
      console.log(`Reloaded games config: ${Object.keys(mergedConfig.games).length} games available`);
    }

    return true;
  } catch (error) {
    if (logger) {
      logger.error(`Error reloading games config: ${error.message}`);
    } else {
      console.error('Error reloading games config:', error.message);
    }
    return false;
  }
}

/**
* Handle reward settings for a game
* @param {Object} interaction - Discord interaction object
* @param {Object} config - Bot configuration 
* @param {Object} logger - Logger instance
* @returns {Promise<void>}
*/
async function handleRewardSettings(interaction, config, logger) {
  const gameId = interaction.options.getString('game_id');
  const rewardType = interaction.options.getString('reward_type');

  // Get the game data
  try {
    const gameData = await getGameById(gameId);

    if (!gameData) {
      await interaction.reply({
        content: `❌ Game with ID "${gameId}" not found.`,
        ephemeral: true
      });
      return;
    }

    // Check ownership
    if (gameData.owner_id !== interaction.user.id && !Validation.isAdmin(interaction.user.id, config.bot.admins)) {
      await interaction.reply({
        content: `❌ You don't have permission to edit this game. Only the creator (${gameData.author}) can edit it.`,
        ephemeral: true
      });
      return;
    }

    // Modal title and fields depend on reward type
    let modalTitle, primaryFieldLabel, primaryFieldValue;

    if (rewardType === 'badgr') {
      modalTitle = 'Badgr Badge Reward';
      primaryFieldLabel = 'Badge Class ID';
      primaryFieldValue = gameData.badge_class_id || '';
    } else if (rewardType === 'text') {
      modalTitle = 'Text Reward';
      primaryFieldLabel = 'Reward Text';
      primaryFieldValue = gameData.reward_text || '';
    } else {
      await interaction.reply({
        content: '❌ Invalid reward type. Please select either "badgr" or "text".',
        ephemeral: true
      });
      return;
    }

    // Create a modal for reward settings
    const modal = new ModalBuilder()
      .setCustomId(`reward-modal-${gameId}-${rewardType}`)
      .setTitle(`${modalTitle}: ${gameData.name}`);

    // Primary field (Badge ID or Text reward)
    const primaryInput = new TextInputBuilder()
      .setCustomId('primary-field')
      .setLabel(primaryFieldLabel)
      .setValue(primaryFieldValue)
      .setStyle(rewardType === 'text' ? TextInputStyle.Paragraph : TextInputStyle.Short)
      .setRequired(true);

    // Description field
    const descriptionInput = new TextInputBuilder()
      .setCustomId('description')
      .setLabel('Reward Description (shown to players)')
      .setValue(gameData.reward_description || '')
      .setStyle(TextInputStyle.Paragraph)
      .setRequired(false);

    // Add inputs to the modal
    modal.addComponents(
      new ActionRowBuilder().addComponents(primaryInput),
      new ActionRowBuilder().addComponents(descriptionInput)
    );

    // Show the modal
    await interaction.showModal(modal);

    // Wait for modal submission
    const submission = await interaction.awaitModalSubmit({
      time: 300000, // 5 minutes
      filter: i => i.customId === `reward-modal-${gameId}-${rewardType}`
    }).catch(() => null);

    if (!submission) {
      logger.info(`${interaction.user.tag} did not submit the reward settings form`);
      return;
    }

    // Get values from form
    const primaryField = submission.fields.getTextInputValue('primary-field').trim();
    const description = submission.fields.getTextInputValue('description').trim();

    if (!primaryField) {
      await submission.reply({
        content: `❌ ${primaryFieldLabel} is required.`,
        ephemeral: true
      });
      return;
    }

    // Update game object
    const updatedGame = {
      ...gameData,
      reward_type: rewardType
    };

    // Set type-specific fields
    if (rewardType === 'badgr') {
      updatedGame.badge_class_id = primaryField;
      if ('reward_text' in updatedGame) delete updatedGame.reward_text;
    } else if (rewardType === 'text') {
      updatedGame.reward_text = primaryField;
      if ('badge_class_id' in updatedGame) delete updatedGame.badge_class_id;
    }

    // Set description if provided
    if (description) {
      updatedGame.reward_description = description;
    } else if ('reward_description' in updatedGame) {
      delete updatedGame.reward_description;
    }

    // Write updated game to file
    const gameFilePath = Validation.resolveGamePath(gameId, GAMES_DIR);
    if (!gameFilePath) {
      await submission.reply({
        content: '❌ Invalid game ID.',
        ephemeral: true
      });
      return;
    }

    try {
      // Remove the 'id' property before saving (it's redundant with the YAML key)
      const { id, ...gameToSave } = updatedGame;

      await fs.writeFile(
        gameFilePath,
        yaml.dump({ [gameId]: gameToSave }),
        'utf8'
      );

      // Reload the games configuration
      await reloadGamesConfig(logger);

      // Send success message
      const embed = new EmbedBuilder()
        .setTitle('🏆 Reward Settings Updated')
        .setColor('#FFD700')
        .setDescription(`Reward settings for "${updatedGame.name}" have been updated!`)
        .addFields(
          { 
            name: 'Reward Type', 
            value: rewardType === 'badgr' ? 'Digital Badge (Badgr)' : 'Text Message', 
            inline: true 
          },
          { 
            name: primaryFieldLabel, 
            value: '✅ Configured', 
            inline: true 
          }
        );

      if (description) {
        embed.addFields({
          name: 'Reward Description',
          value: description
        });
      }

      await submission.reply({
        embeds: [embed],
        ephemeral: true
      });
    } catch (error) {
      logger.error(`Error updating reward settings: ${error.message}`);
      await submission.reply({
        content: '❌ An error occurred while updating the reward settings. Please try again later.',
        ephemeral: true
      });
    }
  } catch (error) {
    logger.error(`Error getting game data: ${error.message}`);
    await interaction.reply({
      content: '❌ An error occurred while retrieving the game data. Please try again later.',
      ephemeral: true
    });
  }
}
