/**
 * @file deploy-commands.js - Discord Slash Command Deployment Utility
 * @description Automated script for registering and deploying Discord slash commands to the Discord API.
 *              Loads all command definitions from the commands directory, validates their structure,
 *              and handles both guild-specific (instant) and global (up to 1 hour) deployment modes.
 *              Includes error handling, timeout management, and progress logging for reliable deployment.
 * @version 1.1.0
 * @author gl0bal01
 * @since 2025-04-03
 */

const fs = require('fs');
const path = require('path');
const { REST } = require('@discordjs/rest');
const { Routes } = require('discord-api-types/v10');
const yaml = require('js-yaml');
require('dotenv').config();

// Load environment variables
const token = process.env.DISCORD_TOKEN;
const clientId = process.env.CLIENT_ID;
const guildId = process.env.GUILD_ID; // Optional: for guild-specific deployment

if (!token || !clientId) {
  console.error('Missing required environment variables. Please check your .env file.');
  process.exit(1);
}

// Load commands
const commands = [];
const commandsPath = path.join(__dirname, 'commands');
const commandFiles = fs.readdirSync(commandsPath).filter(file => file.endsWith('.js'));

// Load games from config for choices
const config = yaml.load(fs.readFileSync('./config/games.yaml', 'utf8'));
const gameChoices = [];

// Create choices array from games in config
if (config && config.games) {
  for (const [gameId, game] of Object.entries(config.games)) {
    gameChoices.push({
      name: `${game.name} (${gameId})`,
      value: gameId
    });
  }
}

// Load all command files
for (const file of commandFiles) {
  const filePath = path.join(commandsPath, file);
  const command = require(filePath);
  
  if ('data' in command) {
    // Add game choices to specific commands
    commands.push(command.data.toJSON());
    
    console.log(`Loaded command: ${command.data.name}`);
  } else {
    console.warn(`The command at ${filePath} is missing required "data" property.`);
  }
}

// Initialize REST client
const rest = new REST({ version: '10' }).setToken(token);
// Deploy commands
(async () => {
  try {
    console.log(`Started refreshing ${commands.length} application (/) commands.`);
    console.log(`Command names: ${commands.map(cmd => cmd.name).join(', ')}`); // Log just the names
    
    // Set a timeout for the request
    const timeoutMs = 60000; // 1 minute timeout
    let timeoutId;
    
    const timeoutPromise = new Promise((_, reject) => {
      timeoutId = setTimeout(() => {
        reject(new Error('Request timed out after ' + timeoutMs/1000 + ' seconds'));
      }, timeoutMs);
    });
    
    let data;
    if (guildId) {
      console.log(`Attempting guild deployment to guild ${guildId}...`);
      
      // Guild specific deployment with timeout
      const requestPromise = rest.put(
        Routes.applicationGuildCommands(clientId, guildId),
        { 
		body: commands,
    		headers: {
      			'User-Agent': 'ScoreBot/1.0'
    		}
 	}
      );
      
      data = await Promise.race([requestPromise, timeoutPromise]);
      clearTimeout(timeoutId);
      
      console.log(`Successfully registered commands in guild ${guildId}.`);
    } else {
      console.log('Attempting global deployment (this can take up to an hour)...');
      
      // Global deployment with longer timeout (10 minutes)
      const globalTimeoutMs = 600000; // 10 minutes
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => {
        console.error('Global deployment taking longer than expected. The process may continue in the background.');
        process.exit(0); // Exit gracefully
      }, globalTimeoutMs);
      
      data = await rest.put(
        Routes.applicationCommands(clientId),
        { body: commands }
      );
      
      clearTimeout(timeoutId);
      console.log('Successfully registered commands globally.');
    }
    
    console.log(`Registered ${data ? data.length : 'unknown number of'} commands.`);
  } catch (error) {
    console.error('Error registering commands:', error);
    // Exit with error code
    process.exit(1);
  }
})();
