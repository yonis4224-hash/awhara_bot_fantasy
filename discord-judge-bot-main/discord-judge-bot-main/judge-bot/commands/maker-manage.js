/**
 * @file maker-manage.js - Admin commands to manage Maker-created games
 * @description Commands for admins to approve, reject, and manage games created by Makers
 * @version 1.1.0
 * @author gl0bal01
 * @since 2025-04-03
 */
const GameApprovalAnnouncer = require('../services/game-approval-announcer');
const { SlashCommandBuilder, EmbedBuilder, PermissionFlagsBits, 
  ActionRowBuilder, ButtonBuilder, ButtonStyle, ModalBuilder, 
  TextInputBuilder, TextInputStyle } = require('discord.js');
const fs = require('fs').promises;
const path = require('path');
const yaml = require('js-yaml');
const Validation = require('../utils/validation');

// Path to the games directory where individual game files will be stored
const GAMES_DIR = path.join(__dirname, '../config/games');

module.exports = {
data: new SlashCommandBuilder()
.setName('maker-manage')
.setDescription('Admin commands to manage Maker-created games')
.setDefaultMemberPermissions(PermissionFlagsBits.Administrator) // Restricts to admin permissions
.addSubcommand(subcommand =>
subcommand
  .setName('list')
  .setDescription('List all Maker-created games')
  .addUserOption(option => 
    option.setName('user')
      .setDescription('Filter games by creator (optional)')
      .setRequired(false)
  )
)
.addSubcommand(subcommand =>
subcommand
  .setName('approve')
  .setDescription('Approve a game for production use')
  .addStringOption(option => 
    option.setName('game_id')
      .setDescription('ID of the game to approve')
      .setRequired(true)
      .setAutocomplete(true)
  )
)
.addSubcommand(subcommand =>
subcommand
  .setName('reject')
  .setDescription('Reject a game (with feedback)')
  .addStringOption(option => 
    option.setName('game_id')
      .setDescription('ID of the game to reject')
      .setRequired(true)
      .setAutocomplete(true)
  )
  .addStringOption(option => 
    option.setName('reason')
      .setDescription('Reason for rejection')
      .setRequired(true)
  )
)
.addSubcommand(subcommand =>
subcommand
  .setName('disable')
  .setDescription('Temporarily disable a game')
  .addStringOption(option => 
    option.setName('game_id')
      .setDescription('ID of the game to disable')
      .setRequired(true)
      .setAutocomplete(true)
  )
),

// Set up autocomplete for game selection
async autocomplete(interaction, { config, logger }) {
const focusedOption = interaction.options.getFocused(true);

if (focusedOption.name === 'game_id') {
try {
  const allGames = await getAllGames();
  
  const filtered = allGames.filter(game => 
    game.id.includes(focusedOption.value) || 
    game.name.toLowerCase().includes(focusedOption.value.toLowerCase())
  );
  
  await interaction.respond(
    filtered.map(game => ({
      name: `${game.name} (by ${game.author}) - ${game.id}`,
      value: game.id
    })).slice(0, 25)
  );
} catch (error) {
  logger.error(`Error in autocomplete: ${error.message}`);
  await interaction.respond([]);
}
}
},

async execute(interaction, { client, config, logger, gameApprovalAnnouncer }) {
const userId = interaction.user.id;
const subcommand = interaction.options.getSubcommand();

logger.info(`${interaction.user.tag} (${userId}) used /maker-manage ${subcommand}`);

try {
// Check if user is an admin
if (!Validation.isAdmin(userId, config.bot.admins)) {
  await interaction.reply({
    content: '❌ You do not have permission to use these commands.',
    ephemeral: true
  });
  return;
}

// Ensure games directory exists
await fs.mkdir(GAMES_DIR, { recursive: true });

// Handle subcommands
switch (subcommand) {
  case 'list':
    await handleListGames(interaction, logger);
    break;
  case 'approve':
    await handleApproveGame(interaction, client, logger, config);
    break;
  case 'reject':
    await handleRejectGame(interaction, client, logger, config);
    break;
  case 'disable':
    await handleDisableGame(interaction, client, logger, config);
    break;
}
} catch (error) {
logger.error(`Error in maker-manage command: ${error.message}`);

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
 * Handle listing all Maker-created games - Fixed to handle Discord's field length limits
 * @param {Object} interaction - Discord interaction object
 * @param {Object} logger - Logger instance
 * @returns {Promise<void>}
 */
async function handleListGames(interaction, logger) {
  try {
    // Get filter user if provided
    const filterUser = interaction.options.getUser('user');
    
    // Create embed first - we'll populate it based on what we find
    const embed = new EmbedBuilder()
      .setTitle('🎮 Maker-Created Games')
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
    const disabledGames = [];
    const rejectedGames = [];
    
    // Process each game file
    for (const file of gameFiles) {
      try {
        // Extract game ID from filename
        const gameId = path.basename(file, '.yaml');
        
        // Read and parse the file
        const filePath = path.join(GAMES_DIR, file);
        
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
        
        // Create a game object with sanitized data
        const game = {
          id: gameId,
          name: gameData[gameId].name || 'Unnamed Game',
          author: gameData[gameId].author || 'Unknown Author',
          owner_id: gameData[gameId].owner_id || '',
          description: gameData[gameId].description || 'No description',
          difficulty: parseInt(gameData[gameId].difficulty) || 1,
          approved: Boolean(gameData[gameId].approved),
          disabled: Boolean(gameData[gameId].disabled),
          rejected: Boolean(gameData[gameId].rejected),
          creation_date: gameData[gameId].creation_date || 'Unknown',
          approval_date: gameData[gameId].approval_date || 'Unknown',
          disable_reason: gameData[gameId].disable_reason || '',
          rejection_reason: gameData[gameId].rejection_reason || ''
        };
        
        // Filter by user if needed
        if (filterUser && game.owner_id !== filterUser.id) {
          continue;
        }
        
        // Categorize the game
        if (game.disabled) {
          disabledGames.push(game);
        } else if (game.rejected) {
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
    
    // Update description with count
    const totalCount = pendingGames.length + approvedGames.length + disabledGames.length + rejectedGames.length;
    if (filterUser) {
      embed.setDescription(`Games created by ${filterUser.tag} (${totalCount} total)`);
    } else {
      embed.setDescription(`All games created by Makers (${totalCount} total)`);
    }
    
    // If no games found at all
    if (totalCount === 0) {
      if (filterUser) {
        await interaction.reply({
          content: `No games found created by ${filterUser.tag}.`,
          ephemeral: true
        });
      } else {
        embed.setDescription('No games found in the system.');
        await interaction.reply({
          embeds: [embed],
          ephemeral: true
        });
      }
      return;
    }
    
    // Add pending games section
    if (pendingGames.length > 0) {
      // Sort by creation date (newest first)
      pendingGames.sort((a, b) => {
        return new Date(b.creation_date || 0) - new Date(a.creation_date || 0);
      });
      
      let pendingText = '';
      for (const game of pendingGames) {
        // Make sure difficulty is a valid number for the repeat
        const difficultyStars = '⭐'.repeat(Math.min(Math.max(game.difficulty, 1), 5));
        
        const gameEntry = `• **${game.name}** by ${game.author}\n  Difficulty: ${difficultyStars} | Created: ${game.creation_date}\n\n`;
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
    
    // Add approved games section
    if (approvedGames.length > 0) {
      // Sort by approval date (newest first)
      approvedGames.sort((a, b) => {
        return new Date(b.approval_date || 0) - new Date(a.approval_date || 0);
      });
      
      let approvedText = '';
      for (const game of approvedGames) {
        // Make sure difficulty is a valid number for the repeat
        const difficultyStars = '⭐'.repeat(Math.min(Math.max(game.difficulty, 1), 5));
        
        const gameEntry = `• **${game.name}** (${game.id}) by ${game.author}\n  Difficulty: ${difficultyStars} | Approved: ${game.approval_date}\n\n`;
        approvedText += gameEntry;
      }
      
      // Split into chunks if the text is too long
      const approvedChunks = splitToChunks(approvedText);
      
      // Add each chunk as a separate field
      for (let i = 0; i < approvedChunks.length; i++) {
        const fieldName = (i === 0) 
          ? `\n✅ Approved (${approvedGames.length})` 
          : `\n✅ Approved (continued ${i+1}/${approvedChunks.length})`;
        
        embed.addFields({ name: fieldName, value: approvedChunks[i] || 'None' });
      }
    }
    
    // Add rejected games section
    if (rejectedGames.length > 0) {
      let rejectedText = '';
      for (const game of rejectedGames) {
        const gameEntry = `• **${game.name}** (${game.id}) by ${game.author}\n  Reason: ${game.rejection_reason}\n\n`;
        rejectedText += gameEntry;
      }
      
      // Split into chunks if the text is too long
      const rejectedChunks = splitToChunks(rejectedText);
      
      // Add each chunk as a separate field
      for (let i = 0; i < rejectedChunks.length; i++) {
        const fieldName = (i === 0) 
          ? `❌ Rejected (${rejectedGames.length})` 
          : `❌ Rejected (continued ${i+1}/${rejectedChunks.length})`;
        
        embed.addFields({ name: fieldName, value: rejectedChunks[i] || 'None' });
      }
    }
    
    // Add disabled games section
    if (disabledGames.length > 0) {
      let disabledText = '';
      for (const game of disabledGames) {
        const gameEntry = `• **${game.name}** by ${game.author}\n  Reason: ${game.disable_reason}\n\n`;
        disabledText += gameEntry;
      }
      
      // Split into chunks if the text is too long
      const disabledChunks = splitToChunks(disabledText);
      
      // Add each chunk as a separate field
      for (let i = 0; i < disabledChunks.length; i++) {
        const fieldName = (i === 0) 
          ? `🚫 Disabled (${disabledGames.length})` 
          : `🚫 Disabled (continued ${i+1}/${disabledChunks.length})`;
        
        embed.addFields({ name: fieldName, value: disabledChunks[i] || 'None' });
      }
    }
    
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
      content: '❌ An error occurred while retrieving the games list. Please try again later.',
      ephemeral: true
    });
  }
}

/**
* Handle approving a game
* @param {Object} interaction - Discord interaction object
* @param {Object} client - Discord client
* @param {Object} logger - Logger instance
* @param {Object} config - Bot configuration
* @returns {Promise<void>}
*/
async function handleApproveGame(interaction, client, logger, config) {
const gameId = interaction.options.getString('game_id');

try {
// Get the game data
const gameData = await getGameById(gameId);

if (!gameData) {
await interaction.reply({
  content: `❌ Game with ID "${gameId}" not found.`,
  ephemeral: true
});
return;
}

// Check if game is already approved
if (gameData.approved) {
await interaction.reply({
  content: `⚠️ The game "${gameData.name}" is already approved.`,
  ephemeral: true
});
return;
}

// Check if game is disabled
if (gameData.disabled) {
await interaction.reply({
  content: `⚠️ The game "${gameData.name}" is currently disabled. Please enable it first.`,
  ephemeral: true
});
return;
}

// Create confirmation message
const embed = new EmbedBuilder()
.setTitle('✅ Approve Game')
.setColor('#00FF00')
.setDescription(`Review details for "${gameData.name}" before approving:`)
.addFields(
  { name: 'ID', value: gameId, inline: true },
  { name: 'Creator', value: gameData.author, inline: true },
  { name: 'Difficulty', value: '⭐'.repeat(gameData.difficulty || 1), inline: true },
  { name: 'Description', value: gameData.description || 'No description provided' },
  { name: 'Reward Type', value: gameData.reward_type || 'Not specified' }
);

// Add reward details if present
if (gameData.reward_type === 'badgr' && gameData.badge_class_id) {
  embed.addFields({ name: 'Badge Class ID', value: gameData.badge_class_id });
} else if (gameData.reward_type === 'text' && gameData.reward_text) {
  embed.addFields({ name: 'Text Reward', value: `Configured (${gameData.reward_text.length} characters)` });
} else {
  embed.addFields({ name: 'Reward Warning', value: 'No reward configuration found!' });
}

// Create confirmation buttons
const confirmButton = new ButtonBuilder()
.setCustomId(`approve-game-${gameId}`)
.setLabel('Approve Game')
.setStyle(ButtonStyle.Success);

const cancelButton = new ButtonBuilder()
.setCustomId('cancel-approval')
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

if (i.customId === `approve-game-${gameId}`) {
  // Update game with approval info
  const updatedGame = {
    ...gameData,
    approved: true,
    approval_date: new Date().toISOString().split('T')[0], // YYYY-MM-DD format
    approver_id: interaction.user.id,
    approver_name: interaction.user.tag
  };
  
  if (updatedGame.disabled) {
    delete updatedGame.disabled;
    delete updatedGame.disable_reason;
  }
  
  if (updatedGame.rejected) {
    delete updatedGame.rejected;
    delete updatedGame.rejection_reason;
  }
  
  if (updatedGame.pending_review) {
    delete updatedGame.pending_review;
    delete updatedGame.edit_reason;
  }
  
  // Save updated game
  const gameFilePath = Validation.resolveGamePath(gameId, GAMES_DIR);
  if (!gameFilePath) {
    await i.update({
      content: '❌ Invalid game ID.',
      embeds: [],
      components: []
    });
    return;
  }

  // Remove the 'id' property before saving
  const { id, ...gameToSave } = updatedGame;

  await fs.writeFile(
    gameFilePath,
    yaml.dump({ [gameId]: gameToSave }),
    'utf8'
  );

  // Reload the games configuration
  await reloadGamesConfig(logger);

  // Announce the game approval if announcer exists
  if (interaction.client.gameApprovalAnnouncer) {
    try {
      // Announce the approved game
      await interaction.client.gameApprovalAnnouncer.announceApproval(
        {...updatedGame, id: gameId},  // Add the game ID to the game object
        interaction.user.tag,          // Admin who approved
        gameData.owner_id              // Game creator's Discord ID
      );
    } catch (error) {
      logger.error(`Error announcing game approval: ${error.message}`);
      // Continue even if announcement fails
    }
  }

  // Try to notify the game creator
  try {
    const creator = await client.users.fetch(gameData.owner_id);
    if (creator) {
      const notificationEmbed = new EmbedBuilder()
        .setTitle('🎉 Your Challenge Has Been Approved!')
        .setColor('#00FF00')
        .setDescription(`Your challenge "${gameData.name}" has been approved and is now available to all players!`)
        .setFooter({ text: `Approved by ${interaction.user.tag}` });
      
      await creator.send({ embeds: [notificationEmbed] }).catch(() => {
        // Silently fail if unable to DM the creator
        logger.warn(`Unable to send DM to ${creator.tag}`);
      });
    }
  } catch (error) {
    logger.warn(`Unable to notify game creator: ${error.message}`);
  }
  
  await i.update({
    content: `✅ The game "${gameData.name}" has been approved and is now available to all players!`,
    embeds: [],
    components: []
  });

} else if (i.customId === 'cancel-approval') {
  await i.update({
    content: '✅ Game approval cancelled.',
    embeds: [],
    components: []
  });
}
});

collector.on('end', async collected => {
if (collected.size === 0) {
  // Timeout
  await response.edit({
    content: '⏱️ Approval request timed out.',
    embeds: [],
    components: []
  }).catch(() => {});
}
});
} catch (error) {
logger.error(`Error approving game: ${error.message}`);

if (interaction.replied) {
await interaction.followUp({
  content: '❌ An error occurred while approving the game. Please try again later.',
  ephemeral: true
});
} else {
await interaction.reply({
  content: '❌ An error occurred while approving the game. Please try again later.',
  ephemeral: true
});
}
}
}

/**
* Handle rejecting a game with feedback
* @param {Object} interaction - Discord interaction object
* @param {Object} client - Discord client
* @param {Object} logger - Logger instance
* @param {Object} config - Bot configuration
* @returns {Promise<void>}
*/
async function handleRejectGame(interaction, client, logger, config) {
const gameId = interaction.options.getString('game_id');
const reason = interaction.options.getString('reason');

try {
// Get the game data
const gameData = await getGameById(gameId);

if (!gameData) {
await interaction.reply({
  content: `❌ Game with ID "${gameId}" not found.`,
  ephemeral: true
});
return;
}

// Create confirmation message
const embed = new EmbedBuilder()
.setTitle('❌ Reject Game')
.setColor('#FF0000')
.setDescription(`Are you sure you want to reject "${gameData.name}"?`)
.addFields(
  { name: 'Creator', value: gameData.author, inline: true },
  { name: 'Rejection Reason', value: reason }
);

// Create confirmation buttons
const confirmButton = new ButtonBuilder()
.setCustomId(`reject-game-${gameId}`)
.setLabel('Confirm Rejection')
.setStyle(ButtonStyle.Danger);

const cancelButton = new ButtonBuilder()
.setCustomId('cancel-rejection')
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

if (i.customId === `reject-game-${gameId}`) {
  // Update game with rejection info
  const updatedGame = {
    ...gameData,
    rejected: true,
    rejection_date: new Date().toISOString().split('T')[0], // YYYY-MM-DD format
    rejection_reason: reason,
    rejector_id: interaction.user.id,
    rejector_name: interaction.user.tag
  };
  
  // Clear other states
  if (updatedGame.approved) {
    delete updatedGame.approved;
    delete updatedGame.approval_date;
  }
  
  if (updatedGame.pending_review) {
    delete updatedGame.pending_review;
  }
  
  // Save updated game
  const gameFilePath = Validation.resolveGamePath(gameId, GAMES_DIR);
  if (!gameFilePath) {
    await i.update({
      content: '❌ Invalid game ID.',
      embeds: [],
      components: []
    });
    return;
  }

  // Remove the 'id' property before saving
  const { id, ...gameToSave } = updatedGame;

  await fs.writeFile(
    gameFilePath,
    yaml.dump({ [gameId]: gameToSave }),
    'utf8'
  );

  // Reload the games configuration
  await reloadGamesConfig(logger);

  // Try to notify the game creator
  try {
    const creator = await client.users.fetch(gameData.owner_id);
    if (creator) {
      const notificationEmbed = new EmbedBuilder()
        .setTitle('Your Challenge Needs Revisions')
        .setColor('#FF9900')
        .setDescription(`Your challenge "${gameData.name}" requires revisions before it can be approved.`)
        .addFields(
          { name: 'Feedback', value: reason },
          { name: 'Next Steps', value: 'Please revise your challenge using the `/maker edit` command, addressing the feedback provided.' }
        )
        .setFooter({ text: `Feedback provided by ${interaction.user.tag}` });
      
      await creator.send({ embeds: [notificationEmbed] }).catch(() => {
        // Silently fail if unable to DM the creator
        logger.warn(`Unable to send DM to ${creator.tag}`);
      });
    }
  } catch (error) {
    logger.warn(`Unable to notify game creator: ${error.message}`);
  }
  
  await i.update({
    content: `✅ Feedback has been sent to the creator of "${gameData.name}".`,
    embeds: [],
    components: []
  });
} else if (i.customId === 'cancel-rejection') {
  await i.update({
    content: '✅ Game rejection cancelled.',
    embeds: [],
    components: []
  });
}
});

collector.on('end', async collected => {
if (collected.size === 0) {
  // Timeout
  await response.edit({
    content: '⏱️ Rejection request timed out.',
    embeds: [],
    components: []
  }).catch(() => {});
}
});
} catch (error) {
logger.error(`Error rejecting game: ${error.message}`);

if (interaction.replied) {
await interaction.followUp({
  content: '❌ An error occurred while rejecting the game. Please try again later.',
  ephemeral: true
});
} else {
await interaction.reply({
  content: '❌ An error occurred while rejecting the game. Please try again later.',
  ephemeral: true
});
}
}
}

/**
* Handle disabling a game
* @param {Object} interaction - Discord interaction object
* @param {Object} client - Discord client
* @param {Object} logger - Logger instance
* @param {Object} config - Bot configuration
* @returns {Promise<void>}
*/
async function handleDisableGame(interaction, client, logger, config) {
const gameId = interaction.options.getString('game_id');

try {
// Get the game data
const gameData = await getGameById(gameId);

if (!gameData) {
await interaction.reply({
  content: `❌ Game with ID "${gameId}" not found.`,
  ephemeral: true
});
return;
}

// Check if game is already disabled
if (gameData.disabled) {
// Create re-enable buttons
const enableButton = new ButtonBuilder()
  .setCustomId(`enable-game-${gameId}`)
  .setLabel('Re-enable Game')
  .setStyle(ButtonStyle.Success);

const cancelButton = new ButtonBuilder()
  .setCustomId('cancel-enable')
  .setLabel('Cancel')
  .setStyle(ButtonStyle.Secondary);

const row = new ActionRowBuilder().addComponents(enableButton, cancelButton);

// Send message
const response = await interaction.reply({
  content: `⚠️ The game "${gameData.name}" is already disabled. Would you like to re-enable it?`,
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
  
  if (i.customId === `enable-game-${gameId}`) {
    // Re-enable the game
    const updatedGame = {
      ...gameData
    };
    
    delete updatedGame.disabled;
    delete updatedGame.disable_reason;
    delete updatedGame.disable_date;
    
    // Save updated game
    const gameFilePath = Validation.resolveGamePath(gameId, GAMES_DIR);
    if (!gameFilePath) {
      await i.update({
        content: '❌ Invalid game ID.',
        components: []
      });
      return;
    }

    // Remove the 'id' property before saving
    const { id, ...gameToSave } = updatedGame;

    await fs.writeFile(
      gameFilePath,
      yaml.dump({ [gameId]: gameToSave }),
      'utf8'
    );

    // Reload the games configuration
    await reloadGamesConfig(logger);

    await i.update({
      content: `✅ The game "${gameData.name}" has been re-enabled.`,
      components: []
    });
  } else if (i.customId === 'cancel-enable') {
    await i.update({
      content: '✅ Operation cancelled.',
      components: []
    });
  }
});

collector.on('end', async collected => {
  if (collected.size === 0) {
    // Timeout
    await response.edit({
      content: '⏱️ Request timed out.',
      components: []
    }).catch(() => {});
  }
});

return;
}

// Create a modal for disable reason
const modal = new ModalBuilder()
.setCustomId(`disable-game-modal-${gameId}`)
.setTitle(`Disable Game: ${gameData.name}`);

// Reason input
const reasonInput = new TextInputBuilder()
.setCustomId('disable-reason')
.setLabel('Reason for disabling')
.setPlaceholder('Enter the reason why this game is being disabled')
.setStyle(TextInputStyle.Paragraph)
.setRequired(true);

// Add inputs to the modal
modal.addComponents(
new ActionRowBuilder().addComponents(reasonInput)
);

// Show the modal
await interaction.showModal(modal);

// Wait for modal submission
const filter = i => i.customId === `disable-game-modal-${gameId}` && i.user.id === interaction.user.id;
const submission = await interaction.awaitModalSubmit({
filter,
time: 300000 // 5 minutes
}).catch(() => null);

if (!submission) {
logger.info(`${interaction.user.tag} did not submit the disable reason`);
return;
}

// Get values from form
const disableReason = submission.fields.getTextInputValue('disable-reason').trim();

// Update game
const updatedGame = {
...gameData,
disabled: true,
disable_reason: disableReason,
disable_date: new Date().toISOString().split('T')[0], // YYYY-MM-DD format
disabled_by: interaction.user.tag
};

// Save updated game
const gameFilePath = Validation.resolveGamePath(gameId, GAMES_DIR);
if (!gameFilePath) {
await submission.reply({ content: '❌ Invalid game ID.', ephemeral: true });
return;
}

// Remove the 'id' property before saving
const { id, ...gameToSave } = updatedGame;

await fs.writeFile(
gameFilePath,
yaml.dump({ [gameId]: gameToSave }),
'utf8'
);

// Reload the games configuration
await reloadGamesConfig(logger);

// Try to notify the game creator
try {
const creator = await client.users.fetch(gameData.owner_id);
if (creator) {
  const notificationEmbed = new EmbedBuilder()
    .setTitle('⚠️ Your Challenge Has Been Temporarily Disabled')
    .setColor('#FF9900')
    .setDescription(`Your challenge "${gameData.name}" has been temporarily disabled.`)
    .addFields({ name: 'Reason', value: disableReason })
    .setFooter({ text: `Disabled by ${interaction.user.tag}` });
  
  await creator.send({ embeds: [notificationEmbed] }).catch(() => {
    // Silently fail if unable to DM the creator
    logger.warn(`Unable to send DM to ${creator.tag}`);
  });
}
} catch (error) {
logger.warn(`Unable to notify game creator: ${error.message}`);
}

await submission.reply({
content: `✅ The game "${gameData.name}" has been disabled.`,
ephemeral: true
});
} catch (error) {
logger.error(`Error disabling game: ${error.message}`);

if (interaction.replied) {
await interaction.followUp({
  content: '❌ An error occurred while disabling the game. Please try again later.',
  ephemeral: true
});
} else {
await interaction.reply({
  content: '❌ An error occurred while disabling the game. Please try again later.',
  ephemeral: true
});
}
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
          // Sanitize numeric values to avoid "Invalid number value" errors
          const sanitizedData = sanitizeGameData(gameData[gameId]);
          
          games.push({
            id: gameId,
            ...sanitizedData
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
 * Sanitize game data by ensuring all numeric values are properly formatted
 * @param {Object} gameData - Raw game data from YAML file
 * @returns {Object} Sanitized game data
 */
function sanitizeGameData(gameData) {
  if (!gameData) return {};
  
  // Create a deep copy to avoid modifying the original
  const sanitized = JSON.parse(JSON.stringify(gameData));
  
  // Handle common numeric fields
  if (sanitized.difficulty !== undefined && sanitized.difficulty !== null) {
    sanitized.difficulty = Number(sanitized.difficulty) || 1;
  }
  
  if (sanitized.points !== undefined && sanitized.points !== null) {
    sanitized.points = Number(sanitized.points) || 0;
  }
  
  // Ensure hints array is valid
  if (sanitized.hints && !Array.isArray(sanitized.hints)) {
    sanitized.hints = [];
  }
  
  return sanitized;
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
      // Sanitize numeric values to avoid "Invalid number value" errors
      const sanitizedData = sanitizeGameData(gameData[gameId]);

      return {
        id: gameId,
        ...sanitizedData
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