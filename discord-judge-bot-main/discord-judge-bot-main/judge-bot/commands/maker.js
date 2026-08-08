/**
 * @file maker.js - Challenge Creation and Management System
 * @description Comprehensive Discord slash command system for challenge creators with maker role permissions.
 *              Provides complete CRUD operations for challenges including creation, editing, removal, and listing.
 *              Features modal-based input forms, reward configuration, admin notifications, and automatic
 *              game ID generation. Includes robust validation and role-based access control.
 * @version 1.1.0
 * @author gl0bal01
 * @since 2025-04-03
 */

const { SlashCommandBuilder, EmbedBuilder, ActionRowBuilder, ModalBuilder, TextInputBuilder, 
  TextInputStyle, ButtonBuilder, ButtonStyle } = require('discord.js');
const fs = require('fs').promises;
const path = require('path');
const yaml = require('js-yaml');
const Validation = require('../utils/validation');

// Path to the games directory where individual game files will be stored
const GAMES_DIR = path.join(__dirname, '../config/games');

module.exports = {
  data: new SlashCommandBuilder()
  .setName('maker')
  .setDescription('Create, edit, or remove games (Maker role only)') // Make sure this isn't too long
  .setDefaultMemberPermissions(null) // Make visible to everyone, we'll handle permissions in the execute function
  .addSubcommand(subcommand =>
  subcommand
    .setName('create')
    .setDescription('Create a new game challenge') // Keep this description short
  )
  .addSubcommand(subcommand =>
  subcommand
    .setName('edit')
    .setDescription('Edit one of your existing games') // Keep this description short
    .addStringOption(option => 
      option.setName('game_id')
        .setDescription('Game to edit')
        .setRequired(true)
        .setAutocomplete(true)
    )
  )
  .addSubcommand(subcommand =>
  subcommand
    .setName('remove')
    .setDescription('Remove one of your games') // Keep this description short
    .addStringOption(option => 
      option.setName('game_id')
        .setDescription('Game to remove')
        .setRequired(true)
        .setAutocomplete(true)
    )
  )
  .addSubcommand(subcommand =>
  subcommand
    .setName('list')
    .setDescription('List all games you have created') // Keep this description short
  ),

// Set up autocomplete for game selection
async autocomplete(interaction, { config, logger }) {
const focusedOption = interaction.options.getFocused(true);

if (focusedOption.name === 'game_id') {
try {
  // Get only games owned by this user (unless they're an admin)
  const userId = interaction.user.id;
  const isAdmin = Validation.isAdmin(userId, config.bot.admins);
  
  let userGames;
  if (isAdmin) {
    // Admins can see all games
    userGames = await getAllGames();
  } else {
    // Regular makers only see their own games
    userGames = await getUserOwnedGames(userId);
  }
  
  // Filter games based on input
  const filtered = userGames.filter(game => 
    game.name.toLowerCase().includes(focusedOption.value.toLowerCase()) ||
    game.id.includes(focusedOption.value.toLowerCase())
  );
  
  // Return game name as the display, but game_id as the value
  await interaction.respond(
    filtered.map(game => ({
      name: `${game.name} ${game.approved ? '✅' : '⏳'}`,
      value: game.id
    })).slice(0, 25)
  );
} catch (error) {
  logger.error(`Error in autocomplete: ${error.message}`);
  await interaction.respond([]);
}
}
},
// Fixed execute function for maker.js
async execute(interaction, { client, config, logger }) {
  const userId = interaction.user.id;
  // Get the subcommand that was used
  const subcommand = interaction.options.getSubcommand();
  
  logger.info(`${interaction.user.tag} (${userId}) used /maker ${subcommand}`);

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
      case 'create':
        logger.info('Create subcommand detected');
        await handleGameCreate(interaction, client, logger, config);
        break;
      case 'edit':
        await handleGameEdit(interaction, client, logger, config);
        break;
      case 'remove':
        await handleGameRemove(interaction, logger, config);
        break;
      case 'list':
        await handleGameList(interaction, logger);
        break;
    }
  } catch (error) {
    logger.error(`Error in maker command: ${error.message}`);
    logger.error(`Error stack: ${error.stack}`);

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
* Handle game creation with auto-generated ID and direct reward configuration
*/
// Find and modify the handleGameCreate function in maker.js
// The issue is that your modal has 6 components, but Discord only allows maximum of 5

async function handleGameCreate(interaction, client, logger, config) {
  try {
    logger.info(`Starting to create a modal for user ${interaction.user.tag}`);
    // Create a modal for game creation
    const modal = new ModalBuilder()
    .setCustomId('create-game-modal')
    .setTitle('Create a New Challenge');
  
    logger.info('Modal created, adding components');
  
    // Game Name input
    const gameNameInput = new TextInputBuilder()
    .setCustomId('game-name')
    .setLabel('Challenge Name')
    .setPlaceholder('Cryptography Challenge')
    .setStyle(TextInputStyle.Short)
    .setMaxLength(100)
    .setRequired(true);
  
    // Game Description input
    const gameDescInput = new TextInputBuilder()
    .setCustomId('game-description')
    .setLabel('Challenge Description')
    .setPlaceholder('Decrypt the hidden message to complete this challenge.')
    .setStyle(TextInputStyle.Paragraph)
    .setMaxLength(1000)
    .setRequired(true);
  
    // Game Answer input
    const gameAnswerInput = new TextInputBuilder()
    .setCustomId('game-answer')
    .setLabel('Correct Answer')
    .setPlaceholder('The exact answer players need to submit')
    .setStyle(TextInputStyle.Short)
    .setMaxLength(100)
    .setRequired(true);
  
    // Game Difficulty input (1-4)
    const gameDifficultyInput = new TextInputBuilder()
    .setCustomId('game-difficulty')
    .setLabel('Difficulty (1-4)')
    .setPlaceholder('Enter a number from 1 to 4')
    .setStyle(TextInputStyle.Short)
    .setRequired(true);
  
    // Combined field for Reward Type + Hints
    const combinedInput = new TextInputBuilder()
    .setCustomId('combined-field')
    .setLabel('Reward Type + Hints (one per line)')
    .setPlaceholder('First line: "text" or "badgr"\nFollowing lines: your hints')
    .setStyle(TextInputStyle.Paragraph)
    .setMaxLength(1500)
    .setRequired(true);
  
    // Add inputs to the modal - maximum 5 components!
    modal.addComponents(
      new ActionRowBuilder().addComponents(gameNameInput),
      new ActionRowBuilder().addComponents(gameDescInput),
      new ActionRowBuilder().addComponents(gameAnswerInput),
      new ActionRowBuilder().addComponents(gameDifficultyInput),
      new ActionRowBuilder().addComponents(combinedInput)
    );
  
    logger.info('Attempting to show modal to user');
  
    // Show the modal
    await interaction.showModal(modal);
    logger.info('Modal shown successfully');
    
    // Wait for modal submission
    const submission = await interaction.awaitModalSubmit({
    time: 300000, // 5 minutes
    filter: i => i.customId === 'create-game-modal'
    }).catch(() => null);
  
    if (!submission) {
      logger.info(`${interaction.user.tag} did not submit the game creation form`);
      return;
    }
  
    try {
      // Get values from form with better validation
      const gameName = submission.fields.getTextInputValue('game-name').trim();
      const gameDesc = submission.fields.getTextInputValue('game-description').trim();
      const gameDifficultyStr = submission.fields.getTextInputValue('game-difficulty').trim();
      const gameAnswer = submission.fields.getTextInputValue('game-answer').trim();
      const combinedText = submission.fields.getTextInputValue('combined-field').trim();
      
      // Parse the combined field
      const combinedLines = combinedText.split('\n').filter(line => line.trim());
      const gameRewardType = combinedLines[0].trim().toLowerCase();
      const gameHintsText = combinedLines.slice(1).join('\n');
      
      // Validate required fields
      if (!gameName || !gameDesc || !gameAnswer) {
        await submission.reply({
          content: '❌ Name, description, and answer are required fields.',
          ephemeral: true
        });
        return;
      }
  
      // Parse difficulty (default to 1 if invalid)
      let difficulty = 1;
      const diffValue = parseInt(gameDifficultyStr);
      if (!isNaN(diffValue) && diffValue >= 1 && diffValue <= 4) {
        difficulty = diffValue;
      }
  
      // Validate reward type (default to badgr if invalid)
      let rewardType = 'badgr';
      if (gameRewardType === 'text') {
        rewardType = 'text';
      }
  
      // Generate a game ID based on the name (slugify)
      const gameId = generateGameId(gameName, interaction.user.id);
  
      // Process hints (split by newlines)
      const hints = gameHintsText ? gameHintsText.split('\n').filter(hint => hint.trim()) : [];
  
      // Create game object
      const game = {
        name: gameName,
        description: gameDesc,
        author: interaction.user.username, // Set author
        owner_id: interaction.user.id,     // Set owner ID for access control
        answer: gameAnswer,
        difficulty: difficulty,
        reward_type: rewardType,
        creation_date: new Date().toISOString().split('T')[0], // YYYY-MM-DD format
        hints: hints
      };
  
      // Write game to file
      const gameFilePath = Validation.resolveGamePath(gameId, GAMES_DIR);
      if (!gameFilePath) {
        await submission.reply({ content: '❌ Invalid game ID.', ephemeral: true });
        return;
      }
  
      await fs.writeFile(
        gameFilePath,
        yaml.dump({ [gameId]: game }),
        'utf8'
      );
  
      // Send initial success message
      const embed = new EmbedBuilder()
      .setTitle('🎮 Challenge Created')
      .setColor('#00FF00')
      .setDescription(`Your challenge "${gameName}" has been created!`)
      .addFields(
        { name: 'Difficulty', value: '⭐'.repeat(difficulty), inline: true },
        { name: 'Reward Type', value: rewardType === 'badgr' ? 'Digital Badge' : 'Text Message', inline: true },
        { name: 'Hints', value: hints.length > 0 ? `${hints.length} hints provided` : 'No hints', inline: true },
        { name: 'Next Steps', value: 'Use the buttons below to configure your reward details.' }
      );
    
    // Create configuration buttons
    const badgrButton = new ButtonBuilder()
      .setCustomId(`config-badgr-${gameId}`)
      .setLabel('Configure Badge')
      .setStyle(ButtonStyle.Primary)
      .setDisabled(rewardType !== 'badgr');
    
    const textButton = new ButtonBuilder()
      .setCustomId(`config-text-${gameId}`)
      .setLabel('Configure Text Reward')
      .setStyle(ButtonStyle.Success)
      .setDisabled(rewardType !== 'text');
    
    const row = new ActionRowBuilder()
      .addComponents(badgrButton, textButton);
    
    // Send the message with buttons
    const response = await submission.reply({
      embeds: [embed],
      components: [row],
      ephemeral: true
    });
    
    // Create collector for button interactions
    const collector = response.createMessageComponentCollector({
      time: 300000 // 5 minutes
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
    
      if (i.customId === `config-badgr-${gameId}`) {
        // Create and show badge configuration modal
        const modal = new ModalBuilder()
          .setCustomId(`badge-config-${gameId}`)
          .setTitle(`Badge Configuration: ${gameName}`);
    
        // Badge Class ID input
        const badgeIdInput = new TextInputBuilder()
          .setCustomId('badge-class-id')
          .setLabel('Badgr Badge Class ID')
          .setPlaceholder('Enter your Badgr badge class ID')
          .setStyle(TextInputStyle.Short)
          .setRequired(true);
    
        // Badge Description input
        const badgeDescInput = new TextInputBuilder()
          .setCustomId('badge-description')
          .setLabel('Badge Description (shown to players)')
          .setPlaceholder('Complete this challenge to earn the Crypto Master badge!')
          .setStyle(TextInputStyle.Paragraph)
          .setRequired(false);
    
        // Add inputs to the modal
        modal.addComponents(
          new ActionRowBuilder().addComponents(badgeIdInput),
          new ActionRowBuilder().addComponents(badgeDescInput)
        );
    
        // Show the modal
        await i.showModal(modal);
      } 
      else if (i.customId === `config-text-${gameId}`) {
        // Create and show text reward configuration modal
        const modal = new ModalBuilder()
          .setCustomId(`text-reward-config-${gameId}`)
          .setTitle(`Text Reward: ${gameName}`);
    
        // Reward text input
        const rewardTextInput = new TextInputBuilder()
          .setCustomId('reward-text')
          .setLabel('Reward Text/Message/Link')
          .setPlaceholder('RIGHT IS THE LAW!!! Here is your reward!')
          .setStyle(TextInputStyle.Paragraph)
          .setMaxLength(1000)
          .setRequired(true);
    
        // Add inputs to the modal
        modal.addComponents(
          new ActionRowBuilder().addComponents(rewardTextInput)
        );
    
        // Show the modal
        await i.showModal(modal);
      }
    });
      // Notify admins about the new game
      await notifyAdminsAboutNewGame(client, interaction.user, game, gameId, logger, config);
  
    } catch (error) {
      logger.error(`Error processing game creation form: ${error.message}`);
      if (submission.replied) {
        await submission.followUp({
          content: '❌ An error occurred while creating the game. Please try again later.',
          ephemeral: true
        });
      } else {
        await submission.reply({
          content: '❌ An error occurred while creating the game. Please try again later.',
          ephemeral: true
        });
      }
    }
  } catch (error) {
    logger.error(`Error creating game: ${error.message}`);
    logger.error(`Error stack: ${error.stack}`);
    if (interaction.replied || interaction.deferred) {
      await interaction.followUp({
        content: '❌ An error occurred during game creation. Please try again later.',
        ephemeral: true
      });
    } else {
      await interaction.reply({
        content: '❌ An error occurred during game creation. Please try again later.',
        ephemeral: true
      });
    }
  }
  }

/**
* Handle game editing
*/
async function handleGameEdit(interaction, client, logger, config) {
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

// Create a modal for game editing
const modal = new ModalBuilder()
.setCustomId(`edit-game-modal-${gameId}`)
.setTitle(`Edit Challenge: ${gameData.name}`);

// Game Name input
const gameNameInput = new TextInputBuilder()
.setCustomId('game-name')
.setLabel('Challenge Name')
.setValue(gameData.name)
.setStyle(TextInputStyle.Short)
.setRequired(true);

// Game Description input
const gameDescInput = new TextInputBuilder()
.setCustomId('game-description')
.setLabel('Challenge Description')
.setValue(gameData.description)
.setStyle(TextInputStyle.Paragraph)
.setRequired(true);

// Game Answer input
const gameAnswerInput = new TextInputBuilder()
.setCustomId('game-answer')
.setLabel('Correct Answer')
.setValue(gameData.answer)
.setStyle(TextInputStyle.Short)
.setRequired(true);

// Game Difficulty input
const gameDifficultyInput = new TextInputBuilder()
.setCustomId('game-difficulty')
.setLabel('Difficulty (1-4)')
.setValue(gameData.difficulty?.toString() || '1')
.setStyle(TextInputStyle.Short)
.setRequired(true);

// Game Hints input
const gameHintsInput = new TextInputBuilder()
.setCustomId('game-hints')
.setLabel('Hints (one per line)')
.setValue(gameData.hints?.join('\n') || '')
.setStyle(TextInputStyle.Paragraph)
.setRequired(false);

// Add inputs to the modal
modal.addComponents(
new ActionRowBuilder().addComponents(gameNameInput),
new ActionRowBuilder().addComponents(gameDescInput),
new ActionRowBuilder().addComponents(gameAnswerInput),
new ActionRowBuilder().addComponents(gameDifficultyInput),
new ActionRowBuilder().addComponents(gameHintsInput)
);

// Show the modal
await interaction.showModal(modal);

// Wait for modal submission
const submission = await interaction.awaitModalSubmit({
time: 300000, // 5 minutes
filter: i => i.customId === `edit-game-modal-${gameId}`
}).catch(() => null);

if (!submission) {
logger.info(`${interaction.user.tag} did not submit the game edit form`);
return;
}

// Get values from form
const gameName = submission.fields.getTextInputValue('game-name').trim();
const gameDesc = submission.fields.getTextInputValue('game-description').trim();
const gameAnswer = submission.fields.getTextInputValue('game-answer').trim();
const gameDifficulty = submission.fields.getTextInputValue('game-difficulty').trim();
const gameHintsText = submission.fields.getTextInputValue('game-hints').trim();

// Add validation for string lengths
if (gameName.length > 100) {
  await submission.reply({
    content: '❌ Game name must be 100 characters or less.',
    ephemeral: true
  });
  return;
}

if (gameDesc.length > 1000) {
  await submission.reply({
    content: '❌ Game description must be 1000 characters or less.',
    ephemeral: true
  });
  return;
}

if (gameAnswer.length > 100) {
  await submission.reply({
    content: '❌ Game answer must be 100 characters or less.',
    ephemeral: true
  });
  return;
}

if (gameHintsText.length > 1500) {
  await submission.reply({
    content: '❌ Hints text must be 1500 characters or less.',
    ephemeral: true
  });
  return;
}

// Validate difficulty
const difficulty = parseInt(gameDifficulty);
if (isNaN(difficulty) || difficulty < 1 || difficulty > 4) {
await submission.reply({
  content: '❌ Difficulty must be a number between 1 and 4.',
  ephemeral: true
});
return;
}

// Process hints (split by newlines)
const hints = gameHintsText ? gameHintsText.split('\n').filter(hint => hint.trim()) : [];

// Update game object
const updatedGame = {
...gameData,
name: gameName,
description: gameDesc,
answer: gameAnswer,
difficulty: difficulty,
hints: hints,
last_modified: new Date().toISOString().split('T')[0] // YYYY-MM-DD format
};

// If game was already approved, reset it to pending if major fields changed
if (updatedGame.approved) {
const majorChange = 
  gameData.answer !== gameAnswer ||
  gameData.difficulty !== difficulty ||
  JSON.stringify(gameData.hints) !== JSON.stringify(hints);
  
if (majorChange) {
  updatedGame.approved = false;
  updatedGame.pending_review = true;
  updatedGame.edit_reason = "Major changes require admin review";
  
  // Notify the user about approval reset
  await submission.reply({
    content: '⚠️ Since you changed significant gameplay elements, your challenge will need to be approved again by an admin.',
    ephemeral: true
  });
  
  // Notify admins about the edited game
  await notifyAdminsAboutEditedGame(client, interaction.user, updatedGame, gameId, logger, config);
}
}

// Write updated game to file
const gameFilePath = Validation.resolveGamePath(gameId, GAMES_DIR);
if (!gameFilePath) {
  await submission.reply({ content: '❌ Invalid game ID.', ephemeral: true });
  return;
}

try {
// Remove the 'id' property before saving
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
  .setTitle('✏️ Challenge Updated')
  .setColor('#00BFFF')
  .setDescription(`Your challenge "${gameName}" has been updated!`)
  .addFields(
    { name: 'Game ID', value: gameId, inline: true },
    { name: 'Difficulty', value: '⭐'.repeat(difficulty), inline: true },
    { name: 'Hints', value: hints.length > 0 ? `${hints.length} hints provided` : 'No hints', inline: true }
  );

// Add status field
if (updatedGame.approved) {
  embed.addFields({ name: 'Status', value: '✅ Approved and available to players' });
} else if (updatedGame.rejected) {
  embed.addFields({ name: 'Status', value: '❌ Rejected - needs revision' });
} else if (updatedGame.pending_review) {
  embed.addFields({ name: 'Status', value: '⏳ Pending admin review' });
} else {
  embed.addFields({ name: 'Status', value: '⏳ Awaiting admin approval' });
}

// If reward is not configured, prompt to configure it
// If reward is not configured, prompt to configure it
if ((updatedGame.reward_type === 'badgr' && !updatedGame.badge_class_id) ||
    (updatedGame.reward_type === 'text' && !updatedGame.reward_text)) {
  
  embed.addFields({ 
    name: 'Reward Configuration', 
    value: '⚠️ Your reward is not fully configured. Use the button below to set it up.' 
  });
  
  // Send initial reply
  await submission.reply({
    embeds: [embed],
    components: [
      new ActionRowBuilder().addComponents(
        new ButtonBuilder()
          .setCustomId(`config-reward-${gameId}`)
          .setLabel('Configure Reward')
          .setStyle(ButtonStyle.Primary)
      )
    ],
    ephemeral: true
  });
  
  // Set up button collector
  const message = await submission.fetchReply();
  const collector = message.createMessageComponentCollector({
    filter: i => i.customId === `config-reward-${gameId}` && i.user.id === interaction.user.id,
    time: 300000, // 5 minutes
    max: 1
  });
  
  collector.on('collect', async i => {
    if (updatedGame.reward_type === 'text') {
      await showTextRewardConfigModal(interaction, gameId, gameName);
    } else {
      await showBadgeConfigModal(interaction, gameId, gameName);
    }
    
    await i.update({
      components: []
    });
  });
} else {
  await submission.reply({
    embeds: [embed],
    ephemeral: true
  });
}

} catch (error) {
logger.error(`Error updating game: ${error.message}`);
await submission.reply({
  content: '❌ An error occurred while updating the game. Please try again later.',
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
* Handle game removal
*/
async function handleGameRemove(interaction, logger, config) {
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
  content: `❌ You don't have permission to remove this game. Only the creator (${gameData.author}) can remove it.`,
  ephemeral: true
});
return;
}

// Create confirmation message
const embed = new EmbedBuilder()
.setTitle('🗑️ Remove Challenge')
.setColor('#FF0000')
.setDescription(`Are you sure you want to remove the challenge "${gameData.name}"?`)
.addFields(
  { name: 'ID', value: gameId, inline: true },
  { name: 'Created by', value: gameData.author, inline: true }
)
.setFooter({ text: 'This action cannot be undone!' });

// Create confirmation buttons
const confirmButton = new ButtonBuilder()
.setCustomId(`confirm-remove-${gameId}`)
.setLabel('Yes, Remove It')
.setStyle(ButtonStyle.Danger);

const cancelButton = new ButtonBuilder()
.setCustomId('cancel-remove')
.setLabel('Cancel')
.setStyle(ButtonStyle.Secondary);

const row = new ActionRowBuilder().addComponents(confirmButton, cancelButton);

// Send confirmation message
const response = await interaction.reply({
embeds: [embed],
components: [row],
ephemeral: true
});

// Wait for button click
const collector = response.createMessageComponentCollector({ 
time: 60000 // 1 minute
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

if (i.customId === `confirm-remove-${gameId}`) {
  // Remove the game file
  const gameFilePath = Validation.resolveGamePath(gameId, GAMES_DIR);
  if (!gameFilePath) {
    await i.update({
      content: '❌ Invalid game ID.',
      embeds: [],
      components: []
    });
    return;
  }
  
  try {
    await fs.unlink(gameFilePath);
    
    // Reload the games configuration
    await reloadGamesConfig(logger);
    
    await i.update({
      content: `✅ The challenge "${gameData.name}" has been removed.`,
      embeds: [],
      components: []
    });
  } catch (error) {
    logger.error(`Error removing game: ${error.message}`);
    await i.update({
      content: '❌ An error occurred while removing the game. Please try again later.',
      embeds: [],
      components: []
    });
  }
} else if (i.customId === 'cancel-remove') {
  await i.update({
    content: '❌ Removal operation cancelled.',
    embeds: [],
    components: []
  });
}
});

collector.on('end', async collected => {
if (collected.size === 0) {
  // Timeout
  await response.edit({
    content: '❌ Removal operation timed out.',
    embeds: [],
    components: []
  }).catch(() => {});
}
});
} catch (error) {
logger.error(`Error getting game data: ${error.message}`);
await interaction.reply({
content: '❌ An error occurred while retrieving the game data. Please try again later.',
ephemeral: true
});
}
}


/**
 * Handle listing all games created by the user - Fixed to handle Discord's field length limits
 * @param {Object} interaction - Discord interaction object
 * @param {Object} logger - Logger instance
 * @returns {Promise<void>}
 */
async function handleGameList(interaction, logger) {
  try {
    const userId = interaction.user.id;
    
    // Create embed first - we'll populate it based on what we find
    const embed = new EmbedBuilder()
      .setTitle('🎮 Your Created Challenges')
      .setColor('#0099ff');
    
    // Make sure the directory exists
    const GAMES_DIR = path.join(__dirname, '../config/games');
    logger.info(`Checking games directory: ${GAMES_DIR}`);
    
    try {
      await fs.mkdir(GAMES_DIR, { recursive: true });
    } catch (dirError) {
      logger.error(`Error creating games directory: ${dirError.message}`);
      // Continue execution to check if directory already exists
    }
    
    // Read all game files
    let files = [];
    try {
      files = await fs.readdir(GAMES_DIR);
      logger.info(`Found ${files.length} files in games directory`);
    } catch (error) {
      logger.error(`Error reading games directory: ${error.message}`);
      await interaction.reply({
        content: '❌ Error accessing games directory. Please try again later.',
        ephemeral: true
      });
      return;
    }
    
    // Filter to just YAML files
    const gameFiles = files.filter(file => file.endsWith('.yaml'));
    logger.info(`Found ${gameFiles.length} yaml files`);
    
    // Initialize arrays for different game states
    const pendingGames = [];
    const approvedGames = [];
    const rejectedGames = [];
    
    // Process each game file
    for (const file of gameFiles) {
      try {
        // Extract game ID from filename
        const gameId = path.basename(file, '.yaml');
        
        // Read and parse the file
        const filePath = Validation.resolveGamePath(gameId, GAMES_DIR);
        if (!filePath) continue;
        
        const content = await fs.readFile(filePath, 'utf8');
        
        // Try to parse YAML safely
        let gameData = null;
        try {
          gameData = yaml.load(content, { schema: yaml.DEFAULT_SCHEMA });
        } catch (yamlError) {
          logger.error(`Error parsing YAML in ${file}: ${yamlError.message}`);
          continue;
        }
        
        // Skip if no data or wrong format
        if (!gameData || !gameData[gameId]) {
          logger.warn(`Invalid game data in ${file}, skipping`);
          continue;
        }
        
        // Skip if not owned by this user
        if (gameData[gameId].owner_id !== userId) {
          continue;
        }
        
        // Create a game object with sanitized data
        const game = {
          id: gameId,
          name: gameData[gameId].name || 'Unnamed Game',
          description: gameData[gameId].description || 'No description',
          difficulty: parseInt(gameData[gameId].difficulty) || 1,
          approved: Boolean(gameData[gameId].approved),
          rejected: Boolean(gameData[gameId].rejected),
          creation_date: gameData[gameId].creation_date || 'Unknown',
          approval_date: gameData[gameId].approval_date || 'Unknown',
          rejection_date: gameData[gameId].rejection_date || 'Unknown',
          rejection_reason: gameData[gameId].rejection_reason || 'No reason provided',
          reward_type: gameData[gameId].reward_type || 'none'
        };
        
        // Categorize the game
        if (game.rejected) {
          rejectedGames.push(game);
        } else if (game.approved) {
          approvedGames.push(game);
        } else {
          pendingGames.push(game);
        }
      } catch (error) {
        logger.error(`Error parsing game file ${file}: ${error.message}`);
        // Continue to next file
      }
    }
    
    // Update description with count
    const totalCount = pendingGames.length + approvedGames.length + rejectedGames.length;
    embed.setDescription(`Your created challenges (${totalCount} total)`);
    
    // If no games found at all
    if (totalCount === 0) {
      await interaction.reply({
        content: "You haven't created any challenges yet. Use `/maker create` to make your first challenge!",
        ephemeral: true
      });
      return;
    }

    // Function to split text to chunks within Discord's field value limit (1024 chars)
    function splitToChunks(text, maxLength = 1024) {
      if (!text || text.length <= maxLength) return [text];
      
      const chunks = [];
      let currentChunk = "";
      
      // Split by lines to avoid breaking in the middle of a line
      const lines = text.split('\n');
      
      for (const line of lines) {
        // If adding this line would exceed the limit, start a new chunk
        if (currentChunk.length + line.length + 1 > maxLength) {
          chunks.push(currentChunk);
          currentChunk = line;
        } else {
          // Otherwise, add to current chunk
          if (currentChunk) {
            currentChunk += '\n' + line;
          } else {
            currentChunk = line;
          }
        }
      }
      
      // Add the last chunk if there's anything left
      if (currentChunk) {
        chunks.push(currentChunk);
      }
      
      return chunks;
    }
    
    // Add approved games section - FIXED FOR DISCORD'S FIELD VALUE LIMIT
    if (approvedGames.length > 0) {
      // Sort by approval date (newest first)
      approvedGames.sort((a, b) => {
        return new Date(b.approval_date || 0) - new Date(a.approval_date || 0);
      });
      
      let approvedText = '';
      for (const game of approvedGames) {
        // Make sure difficulty is a valid number for the repeat
        const difficultyStars = '⭐'.repeat(Math.min(Math.max(game.difficulty, 1), 5));
        
        // Format reward type nicely
        let rewardType = 'No reward';
        if (game.reward_type === 'badgr') {
          rewardType = '🏅 Digital Badge';
        } else if (game.reward_type === 'text') {
          rewardType = '📝 Text Reward';
        }
        
        const gameEntry = `• **${game.name}** - ${difficultyStars}\n  Status: Live ✅ | Reward: ${rewardType}\n\n`;
        approvedText += gameEntry;
      }
      
      // Split into chunks if the text is too long
      const approvedChunks = splitToChunks(approvedText);
      
      // Add each chunk as a separate field
      for (let i = 0; i < approvedChunks.length; i++) {
        const fieldName = (i === 0) 
          ? `✅ Live Challenges (${approvedGames.length})` 
          : `✅ Live Challenges (continued ${i+1}/${approvedChunks.length})`;
        
        embed.addFields({ name: fieldName, value: approvedChunks[i] || 'None' });
      }
    }
    
    // Add pending games section - FIXED FOR DISCORD'S FIELD VALUE LIMIT
    if (pendingGames.length > 0) {
      // Sort by creation date (newest first)
      pendingGames.sort((a, b) => {
        return new Date(b.creation_date || 0) - new Date(a.creation_date || 0);
      });
      
      let pendingText = '';
      for (const game of pendingGames) {
        // Make sure difficulty is a valid number for the repeat
        const difficultyStars = '⭐'.repeat(Math.min(Math.max(game.difficulty, 1), 5));
        
        // Format reward type nicely
        let rewardType = 'Not configured';
        if (game.reward_type === 'badgr') {
          rewardType = '🏅 Digital Badge';
        } else if (game.reward_type === 'text') {
          rewardType = '📝 Text Reward';
        }
        
        const gameEntry = `• **${game.name}** (${game.id}) - ${difficultyStars}\n  Status: Pending Review ⏳ | Reward: ${rewardType}\n\n`;
        pendingText += gameEntry;
      }
      
      // Split into chunks if the text is too long
      const pendingChunks = splitToChunks(pendingText);
      
      // Add each chunk as a separate field
      for (let i = 0; i < pendingChunks.length; i++) {
        const fieldName = (i === 0) 
          ? `⏳ Pending Review (${pendingGames.length})` 
          : `⏳ Pending Review (continued ${i+1}/${pendingChunks.length})`;
        
        embed.addFields({ name: fieldName, value: pendingChunks[i] || 'None' });
      }
    }
    
    // Add rejected games section - FIXED FOR DISCORD'S FIELD VALUE LIMIT
    if (rejectedGames.length > 0) {
      let rejectedText = '';
      for (const game of rejectedGames) {
        const gameEntry = `• **${game.name}** (${game.id})\n  Feedback: ${game.rejection_reason}\n`;
        rejectedText += gameEntry;
      }
      
      // Split into chunks if the text is too long
      const rejectedChunks = splitToChunks(rejectedText);
      
      // Add each chunk as a separate field
      for (let i = 0; i < rejectedChunks.length; i++) {
        const fieldName = (i === 0) 
          ? `❌ Needs Revision (${rejectedGames.length})` 
          : `❌ Needs Revision (continued ${i+1}/${rejectedChunks.length})`;
        
        embed.addFields({ name: fieldName, value: rejectedChunks[i] || 'None' });
      }
    }
    
    // Add footer with help
    embed.setFooter({
      text: "Use /maker edit <game_id> to update existing challenges"
    });
    
    // Send the embed
    await interaction.reply({
      embeds: [embed],
      ephemeral: true
    });
    
    logger.info(`Successfully displayed ${totalCount} games to ${interaction.user.tag}`);
  } catch (error) {
    logger.error(`Error listing games: ${error.message}`);
    logger.error(`Error stack: ${error.stack}`);
    await interaction.reply({
      content: '❌ An error occurred while retrieving your games. Please try again later.',
      ephemeral: true
    });
  }
}

/**
 * Helper function to chunk an array into smaller arrays
 * @param {Array} array - The array to chunk
 * @param {number} size - The maximum size of each chunk
 * @returns {Array} Array of chunked arrays
 */
function chunkArray(array, size) {
  const chunked = [];
  for (let i = 0; i < array.length; i += size) {
    chunked.push(array.slice(i, i + size));
  }
  return chunked;
}
/**
* Generate a unique game ID from the name
*/
/**
 * Generate a unique game ID from the name
 * @param {string} name - The game name
 * @param {string} userId - The creator's Discord ID
 * @returns {string} A unique game ID
 */
function generateGameId(name, userId) {
// Convert name to lowercase and replace spaces with underscores
const baseId = name.toLowerCase()
.replace(/[^a-z0-9]+/g, '_')  // Replace non-alphanumeric chars with underscore
.replace(/^_+|_+$/g, '')      // Remove leading/trailing underscores
.substring(0, 15);            // Limit length

// Add a timestamp to ensure uniqueness
const timestamp = Date.now().toString(36).substring(0, 4);

// Add user identifier (last 4 characters of user ID)
const userSuffix = userId.substring(userId.length - 4);

return `${baseId}_${timestamp}_${userSuffix}`;
}

/**
* Show badge configuration modal
* @param {Object} interaction - The Discord interaction object
* @param {string} gameId - The game ID
* @param {string} gameName - The game name
* @returns {Promise<void>}
*/
async function showBadgeConfigModal(interaction, gameId, gameName) {
// Create modal for Badgr configuration
const modal = new ModalBuilder()
.setCustomId(`badge-config-${gameId}`)
.setTitle(`Badge Configuration: ${gameName}`);

// Badge Class ID input
const badgeIdInput = new TextInputBuilder()
.setCustomId('badge-class-id')
.setLabel('Badgr Badge Class ID')
.setPlaceholder('Enter your Badgr badge class ID')
.setStyle(TextInputStyle.Short)
.setRequired(true);

// Badge Description input
const badgeDescInput = new TextInputBuilder()
.setCustomId('badge-description')
.setLabel('Badge Description (shown to players)')
.setPlaceholder('Complete this challenge to earn the Crypto Master badge!')
.setStyle(TextInputStyle.Paragraph)
.setRequired(false);

// Add inputs to the modal
modal.addComponents(
new ActionRowBuilder().addComponents(badgeIdInput),
new ActionRowBuilder().addComponents(badgeDescInput)
);

// Show the modal
await interaction.followUp({
  content: 'Please configure your badge reward details:',
  components: [
  new ActionRowBuilder().addComponents(
    new ButtonBuilder()
      .setCustomId(`show-badge-config-${gameId}`)
      .setLabel('Configure Badge')
      .setStyle(ButtonStyle.Primary)
  )
  ],
  ephemeral: true
  });
  
  // Set up collector for the button
  const message = await interaction.fetchReply();
  const collector = message.createMessageComponentCollector({
  filter: i => i.customId === `show-badge-config-${gameId}` && i.user.id === interaction.user.id,
  time: 300000, // 5 minutes
  max: 1
  });
  
  collector.on('collect', async i => {
  await i.showModal(modal);
  });
  }
  /**
* Show text reward configuration modal
* @param {Object} interaction - The Discord interaction object
* @param {string} gameId - The game ID
* @param {string} gameName - The game name
* @returns {Promise<void>}
*/
async function showTextRewardConfigModal(interaction, gameId, gameName) {
  // Create modal for text reward configuration
  const modal = new ModalBuilder()
    .setCustomId(`text-reward-config-${gameId}`)
    .setTitle(`Text Reward: ${gameName}`);

  // Reward text input
  const rewardTextInput = new TextInputBuilder()
    .setCustomId('reward-text')
    .setLabel('Reward Text/Message/Link')
    .setPlaceholder('RIGHT IS THE LAW!!! Here is your reward!')
    .setStyle(TextInputStyle.Paragraph)
    .setMaxLength(1000)
    .setRequired(true);

  // Add inputs to the modal
  modal.addComponents(
    new ActionRowBuilder().addComponents(rewardTextInput)
  );

  // Show the modal
  await interaction.followUp({
    content: 'Please configure your text reward:',
    components: [
      new ActionRowBuilder().addComponents(
        new ButtonBuilder()
          .setCustomId(`show-text-reward-${gameId}`)
          .setLabel('Configure Text Reward')
          .setStyle(ButtonStyle.Primary)
      )
    ],
    ephemeral: true
  });

  // Set up collector for the button
  const message = await interaction.fetchReply();
  const collector = message.createMessageComponentCollector({
    filter: i => i.customId === `show-text-reward-${gameId}` && i.user.id === interaction.user.id,
    time: 300000, // 5 minutes
    max: 1
  });

  collector.on('collect', async i => {
    await i.showModal(modal);
  });
}
 
  
  /**
  * Notify admins about a new game ready for approval
  * @param {Object} client - Discord client
  * @param {Object} creator - The game creator user object
  * @param {Object} game - The game object
  * @param {string} gameId - The game ID
  * @param {Object} logger - Logger instance
  * @param {Object} config - Configuration object
  * @returns {Promise<void>}
  */
  async function notifyAdminsAboutNewGame(client, creator, game, gameId, logger, config) {
  try {
  // Get admin IDs from config
  const adminIds = config.bot.admins || [];
  
  if (adminIds.length === 0) {
  logger.warn('No admins configured to notify about new game');
  return;
  }
  
  // Create notification embed
  const embed = new EmbedBuilder()
  .setTitle('🆕 New Challenge Ready for Review')
  .setColor('#00BFFF')
  .setDescription(`${creator.tag} has created a new challenge that needs approval.`)
  .addFields(
    { name: 'Challenge Name', value: game.name, inline: true },
    { name: 'Difficulty', value: '⭐'.repeat(game.difficulty || 1), inline: true },
    { name: 'Reward Type', value: game.reward_type === 'badgr' ? 'Digital Badge' : 'Text Message', inline: true },
    { name: 'Description', value: game.description },
    { name: 'Action Required', value: `Use \`/maker-manage approve game_id:${gameId}\` to approve this challenge.` }
  )
  .setTimestamp()
  .setFooter({ text: `Game ID: ${gameId}` });
  
  // Try to notify each admin
  for (const adminId of adminIds) {
  try {
    const admin = await client.users.fetch(adminId);
    if (admin) {
      await admin.send({ embeds: [embed] });
      logger.info(`Notified admin ${admin.tag} about new game ${gameId}`);
    }
  } catch (error) {
    logger.warn(`Failed to notify admin ${adminId}: ${error.message}`);
  }
  }
  } catch (error) {
  logger.error(`Error notifying admins about new game: ${error.message}`);
  }
  }
  
  /**
  * Notify admins about edited game
  * @param {Object} client - Discord client
  * @param {Object} creator - The game creator user object
  * @param {Object} game - The game object
  * @param {string} gameId - The game ID
  * @param {Object} logger - Logger instance
  * @param {Object} config - Configuration object
  * @returns {Promise<void>}
  */
  async function notifyAdminsAboutEditedGame(client, creator, game, gameId, logger, config) {
  try {
  // Get admin IDs from config
  const adminIds = config.bot.admins || [];
  
  if (adminIds.length === 0) {
  logger.warn('No admins configured to notify about edited game');
  return;
  }
  
  // Create notification embed
  const embed = new EmbedBuilder()
  .setTitle('📝 Challenge Updated - Needs Review')
  .setColor('#FFA500')
  .setDescription(`${creator.tag} has made significant changes to "${game.name}" that require approval.`)
  .addFields(
    { name: 'Challenge Name', value: game.name, inline: true },
    { name: 'Difficulty', value: '⭐'.repeat(game.difficulty || 1), inline: true },
    { name: 'Last Modified', value: game.last_modified || 'Unknown', inline: true },
    { name: 'Description', value: game.description },
    { name: 'Action Required', value: `Use \`/maker-manage approve game_id:${gameId}\` to approve the changes.` }
  )
  .setTimestamp()
  .setFooter({ text: `Game ID: ${gameId}` });
  
  // Try to notify each admin
  for (const adminId of adminIds) {
  try {
    const admin = await client.users.fetch(adminId);
    if (admin) {
      await admin.send({ embeds: [embed] });
      logger.info(`Notified admin ${admin.tag} about edited game ${gameId}`);
    }
  } catch (error) {
    logger.warn(`Failed to notify admin ${adminId}: ${error.message}`);
  }
  }
  } catch (error) {
  logger.error(`Error notifying admins about edited game: ${error.message}`);
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
      const gamePath = Validation.resolveGamePath(gameId, GAMES_DIR);
      if (!gamePath) continue;
      const content = await fs.readFile(gamePath, 'utf8');
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
      // This is okay - may be first time creating the file
      logger.info('No existing games.yaml found or error reading it: ' + error.message);
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
    
    // Log the games being added to verify
    logger.info(`Adding the following games to config: ${JSON.stringify(Object.keys(mergedConfig.games))}`);
    
    // Write the merged config to the main games.yaml file with absolute path
    const gamesConfigPath = path.join(__dirname, '../config/games.yaml');
    logger.info(`Writing games config to: ${gamesConfigPath}`);
    
    await fs.writeFile(
      gamesConfigPath,
      yaml.dump(mergedConfig),
      'utf8'
    );
    
    // Log the number of games available
    logger.info(`Reloaded games config: ${Object.keys(mergedConfig.games).length} games available`);
    
    // Here is the important part: reload the global config with the new games
    // This ensures the current process sees the changes immediately
    if (global.config) {
      // Merge the updated games into the global config
      global.config.games = mergedConfig.games;
      logger.info(`Updated global config with ${Object.keys(global.config.games).length} games`);
    }
    
    return true;
  } catch (error) {
    logger.error(`Error reloading games config: ${error.message}`);
    return false;
  }
}
