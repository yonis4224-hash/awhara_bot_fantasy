/**
 * @file index.js - Main Discord Bot Entry Point
 * @description Core application file that initializes the Discord Judge Bot, manages command loading,
 *              handles user interactions, and coordinates between various services including database,
 *              success announcements, and game approval workflows. This file serves as the central
 *              orchestrator for all bot functionality including slash commands, modal submissions,
 *              and administrative notifications.
 * @version 1.1.0
 * @author gl0bal01
 * @since 2025-04-03
 */

const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');
const { Client, Collection, GatewayIntentBits, EmbedBuilder } = require('discord.js');
const Logger = require('./utils/logger');
const Validation = require('./utils/validation');
const { initializeDatabase } = require('./services/database');
const SuccessAnnouncer = require('./services/success-announcer');
const GameApprovalAnnouncer = require('./services/game-approval-announcer');
require('dotenv').config();

// Initialize configuration
const loadConfig = () => {
  try {
    const botConfig = yaml.load(fs.readFileSync('./config/bot.yaml', 'utf8'), { schema: yaml.DEFAULT_SCHEMA });
    const gamesConfig = yaml.load(fs.readFileSync('./config/games.yaml', 'utf8'), { schema: yaml.DEFAULT_SCHEMA });
    const apiConfig = yaml.load(fs.readFileSync('./config/api.yaml', 'utf8'), { schema: yaml.DEFAULT_SCHEMA });
    return { ...botConfig, ...gamesConfig, ...apiConfig };
  } catch (error) {
    console.error('Error loading configuration:', error);
    process.exit(1);
  }
};

// Initialize the client
const client = new Client({ 
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages
  ] 
});

// Load the configuration
const config = loadConfig();

// Initialize logger
const logger = new Logger(config.logging.level, config.logging.file);
global.logger = logger;
global.config = config;

// Initialize the success announcer
let successAnnouncer = null;
let gameApprovalAnnouncer = null;

// Set up commands collection
client.commands = new Collection();
const commandsPath = path.join(__dirname, 'commands');
const commandFiles = fs.readdirSync(commandsPath).filter(file => file.endsWith('.js'));

// Load all command modules
for (const file of commandFiles) {
  const filePath = path.join(commandsPath, file);
  const command = require(filePath);
  
  if ('data' in command && 'execute' in command) {
    client.commands.set(command.data.name, command);
    logger.info(`Loaded command: ${command.data.name}`);
  } else {
    logger.warn(`The command at ${filePath} is missing required "data" or "execute" property.`);
  }
}

// When the client is ready
client.once('ready', async () => {
  logger.info(`Logged in as ${client.user.tag}`);
  
  // Initialize the database
  await initializeDatabase();
  logger.info('Database initialized');

  // Initialize the success announcer after client is ready
  successAnnouncer = new SuccessAnnouncer(client, config, logger);
  logger.info('Success announcer initialized');

  gameApprovalAnnouncer = new GameApprovalAnnouncer(client, config, logger);
  logger.info('Game Approval Announcer service initialized');

  // Define the reloadGamesConfig function
  global.reloadGamesConfig = async function() {
    try {
      const logger = global.logger;
      logger.info('Manually reloading games config...');

      // Get all games from the games directory
      const GAMES_DIR = path.join(__dirname, 'config/games');
      const files = fs.readdirSync(GAMES_DIR).filter(file => file.endsWith('.yaml'));

      // Create the merged config
      const mergedConfig = { games: {} };

      // Process each game file
      for (const file of files) {
        try {
          const gameId = path.basename(file, '.yaml');
          const content = fs.readFileSync(path.join(GAMES_DIR, file), 'utf8');
          const gameData = yaml.load(content, { schema: yaml.DEFAULT_SCHEMA });

          if (gameData && gameData[gameId] && gameData[gameId].approved) {
            // Get the game data
            const game = gameData[gameId];

            // Create a clean version for the config (without answer)
            mergedConfig.games[gameId] = {
              name: game.name,
              description: game.description,
              author: game.author,
              difficulty: game.difficulty || 1,
              reward_type: game.reward_type || 'badgr',
              hints: game.hints || []
            };

            // Add reward-specific properties
            if (game.reward_type === 'badgr' && game.badge_class_id) {
              mergedConfig.games[gameId].badge_class_id = game.badge_class_id;
            } else if (game.reward_type === 'text' && game.reward_text) {
              mergedConfig.games[gameId].reward_text = game.reward_text;
            }

            // Add reward description if available
            if (game.reward_description) {
              mergedConfig.games[gameId].reward_description = game.reward_description;
            }
          }
        } catch (error) {
          if (logger) logger.error(`Error processing ${file}: ${error.message}`);
          else console.error(`Error processing ${file}: ${error.message}`);
        }
      }

      // Write the updated config file
      fs.writeFileSync(
        path.join(__dirname, 'config/games.yaml'),
        yaml.dump(mergedConfig),
        'utf8'
      );

      // Update the global config directly
      if (global.config) {
        global.config.games = mergedConfig.games;
        if (logger) logger.info(`Updated global.config.games with ${Object.keys(global.config.games).length} games`);
        else console.log(`Updated global.config.games with ${Object.keys(global.config.games).length} games`);
      }

      return true;
    } catch (error) {
      if (global.logger) global.logger.error(`Error reloading games config: ${error.message}`);
      else console.error(`Error reloading games config: ${error.message}`);
      return false;
    }
  };

  // Reload games on startup
  global.reloadGamesConfig().then(success => {
    if (success) logger.info('Games config loaded successfully on startup');
    else logger.warn('Failed to load games config on startup');
  });
});

// Handle interactions
client.on('interactionCreate', async interaction => {
  // Handle autocomplete interactions
  if (interaction.isAutocomplete()) {
    const command = client.commands.get(interaction.commandName);
    if (!command || !command.autocomplete) return;

    try {
      await command.autocomplete(interaction, {
        client,
        config,
        logger
      });
    } catch (error) {
      logger.error(`Error handling autocomplete for ${interaction.commandName}: ${error.stack}`);
    }
    return;
  }

  if (!interaction.isCommand()) return;

  const command = client.commands.get(interaction.commandName);
  if (!command) return;

  try {
    // Check rate limits
    const rateLimits = config.bot.rate_limits;
    // Extract base command name without the "judge-" or "maker-" prefix for rate limiting
    const baseCommandName = interaction.commandName.replace(/^(judge-|maker-)/, '');
    
    const makerRateLimits = config.bot.maker_rate_limits || {};
    const rateLimit = rateLimits[baseCommandName] || makerRateLimits[interaction.commandName];
    if (rateLimit) {
      // Implement rate limiting here
      // This is a simplified version - you might want to use a proper rate limiting library
      const now = Date.now();
      const cooldownKey = `${interaction.user.id}-${interaction.commandName}`;
      const cooldowns = client.cooldowns || new Collection();
      client.cooldowns = cooldowns;

      if (cooldowns.has(cooldownKey)) {
        const expirationTime = cooldowns.get(cooldownKey) + (rateLimit * 1000);
        if (now < expirationTime) {
          const timeLeft = (expirationTime - now) / 1000;
          return interaction.reply({
            content: `Please wait ${timeLeft.toFixed(1)} more seconds before using \`/${interaction.commandName}\` again.`,
            ephemeral: true
          });
        }
      }

      cooldowns.set(cooldownKey, now);
      setTimeout(() => cooldowns.delete(cooldownKey), rateLimit * 1000);
    }

    // Execute the command
    await command.execute(interaction, { 
      client, 
      config, 
      logger,
      successAnnouncer,
      gameApprovalAnnouncer
    });
  } catch (error) {
    logger.error(`Error executing ${interaction.commandName}: ${error.stack}`);
    const errorMessage = 'There was an error executing this command.';
    
    if (interaction.replied || interaction.deferred) {
      await interaction.followUp({ content: errorMessage, ephemeral: true });
    } else {
      await interaction.reply({ content: errorMessage, ephemeral: true });
    }
  }
});

// Notify admins about game configuration updates
async function notifyAdminsAboutGameUpdate(client, creator, game, gameId, logger, config) {
  try {
    // Get admin IDs from config
    const adminIds = config.bot.admins || [];

    if (adminIds.length === 0) {
      logger.warn('No admins configured to notify about game update');
      return;
    }

    // Create notification embed
    const embed = new EmbedBuilder()
      .setTitle('🔄 Challenge Configuration Updated')
      .setColor('#00BFFF')
      .setDescription(`${creator.tag} has configured rewards for "${game.name}"`)
      .addFields(
        { name: 'Reward Type', value: game.reward_type === 'badgr' ? 'Digital Badge' : 'Text Message', inline: true },
        { name: 'Configuration Status', value: 'Complete ✅', inline: true },
        { name: 'Action Required', value: `Use \`/maker-manage approve game_id:${gameId}\` to review and approve this challenge.` }
      )
      .setTimestamp()
      .setFooter({ text: `Game ID: ${gameId}` });

    // Try to notify each admin
    for (const adminId of adminIds) {
      try {
        const admin = await client.users.fetch(adminId);
        if (admin) {
          await admin.send({ embeds: [embed] });
          logger.info(`Notified admin ${admin.tag} about game update for ${gameId}`);
        }
      } catch (error) {
        logger.warn(`Failed to notify admin ${adminId}: ${error.message}`);
      }
    }
  } catch (error) {
    logger.error(`Error notifying admins about game update: ${error.message}`);
  }
}

// Handle modal submissions for reward configuration
client.on('interactionCreate', async (interaction) => {
  // Only proceed with modal submissions
  if (!interaction.isModalSubmit()) return;
  
  // Get the custom ID
  const customId = interaction.customId;
  
  // Get path to games directory
  const GAMES_DIR = path.join(__dirname, './config/games');
  
  // Check if this is a badge config submission
  if (customId.startsWith('badge-config-')) {
    const gameId = customId.replace('badge-config-', '');
    const gameFilePath = Validation.resolveGamePath(gameId, GAMES_DIR);
    if (!gameFilePath) {
      await interaction.reply({ content: '❌ Invalid game ID.', ephemeral: true });
      return;
    }

    try {
      // Get the badge class ID and description
      const badgeClassId = interaction.fields.getTextInputValue('badge-class-id').trim();
      const badgeDescription = interaction.fields.getTextInputValue('badge-description').trim();

      // Input length validation
      if (badgeClassId.length > 200) {
        await interaction.reply({ content: '❌ Badge class ID is too long (max 200 characters).', ephemeral: true });
        return;
      }
      if (badgeDescription.length > 1000) {
        await interaction.reply({ content: '❌ Badge description is too long (max 1000 characters).', ephemeral: true });
        return;
      }

      // Get the game data
      const content = await fs.promises.readFile(gameFilePath, 'utf8');
      const gameData = yaml.load(content, { schema: yaml.DEFAULT_SCHEMA });

      if (!gameData || !gameData[gameId]) {
        await interaction.reply({
          content: '❌ Game not found.',
          ephemeral: true
        });
        return;
      }

      // Authorization check
      if (gameData[gameId].owner_id !== interaction.user.id && !Validation.isAdmin(interaction.user.id, (global.config.bot.admins || []))) {
        await interaction.reply({ content: '❌ You do not have permission to configure this game.', ephemeral: true });
        return;
      }

      // Update the game with badge details
      gameData[gameId].badge_class_id = badgeClassId;
      if (badgeDescription) {
        gameData[gameId].reward_description = badgeDescription;
      }

      // Save the updated game
      await fs.promises.writeFile(
        gameFilePath,
        yaml.dump(gameData),
        'utf8'
      );

      await interaction.reply({
        content: '✅ Badge configuration saved! Your challenge is now ready for admin approval.',
        ephemeral: true
      });

      // Notify admins about the updated game configuration
      await notifyAdminsAboutGameUpdate(client, interaction.user, gameData[gameId], gameId, global.logger, global.config);
    } catch (error) {
      global.logger.error(`Error saving badge config: ${error.message}`);
      await interaction.reply({
        content: '❌ An error occurred while saving badge configuration.',
        ephemeral: true
      });
    }
  }
  // Check if this is a text reward config submission
else if (customId.startsWith('text-reward-config-')) {
    const gameId = customId.replace('text-reward-config-', '');
    const gameFilePath = Validation.resolveGamePath(gameId, GAMES_DIR);
    if (!gameFilePath) {
      await interaction.reply({ content: '❌ Invalid game ID.', ephemeral: true });
      return;
    }

    try {
      // Get the reward text
      const rewardText = interaction.fields.getTextInputValue('reward-text').trim();

      // Input length validation
      if (rewardText.length > 2000) {
        await interaction.reply({ content: '❌ Reward text is too long (max 2000 characters).', ephemeral: true });
        return;
      }

      // Get the game data
      const content = await fs.promises.readFile(gameFilePath, 'utf8');
      const gameData = yaml.load(content, { schema: yaml.DEFAULT_SCHEMA });

      if (!gameData || !gameData[gameId]) {
        await interaction.reply({
          content: '❌ Game not found.',
          ephemeral: true
        });
        return;
      }

      // Authorization check
      if (gameData[gameId].owner_id !== interaction.user.id && !Validation.isAdmin(interaction.user.id, (global.config.bot.admins || []))) {
        await interaction.reply({ content: '❌ You do not have permission to configure this game.', ephemeral: true });
        return;
      }

      // Update the game with reward details
      gameData[gameId].reward_type = 'text';
      gameData[gameId].reward_text = rewardText;

      // Save the updated game
      await fs.promises.writeFile(
        gameFilePath,
        yaml.dump(gameData),
        'utf8'
      );

      await interaction.reply({
        content: '✅ Text reward configured! Your challenge is now ready for admin approval.',
        ephemeral: true
      });

      // Notify admins about the updated game configuration
      await notifyAdminsAboutGameUpdate(client, interaction.user, gameData[gameId], gameId, global.logger, global.config);
    } catch (error) {
      global.logger.error(`Error saving text reward: ${error.message}`);
      await interaction.reply({
        content: '❌ An error occurred while saving the text reward.',
        ephemeral: true
      });
    }
  }
});

// Login to Discord
client.login(process.env.DISCORD_TOKEN);

// Handle unhandled promise rejections
process.on('unhandledRejection', error => {
  logger.error(`Unhandled rejection: ${error.stack}`);
});

// Handle uncaught exceptions
process.on('uncaughtException', error => {
  logger.error(`Uncaught exception: ${error.stack}`);
  // Don't exit immediately to allow for graceful shutdown if possible
  setTimeout(() => {
    process.exit(1);
  }, 3000);
});