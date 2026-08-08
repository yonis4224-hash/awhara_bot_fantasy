/**
 * @file clear-commands.js - Discord Command Cleanup Utility
 * @description Administrative script for removing all registered Discord slash commands from both
 *              guild-specific and global scopes. Useful for development cleanup, command structure
 *              changes, or complete bot resets. Provides separate cleanup operations for guild
 *              and global commands with proper error handling and status reporting.
 * @version 1.1.0
 * @author gl0bal01
 * @since 2025-04-03
 */
const { REST } = require('@discordjs/rest');
const { Routes } = require('discord-api-types/v10');
require('dotenv').config();

// Load environment variables
const token = process.env.DISCORD_TOKEN;
const clientId = process.env.CLIENT_ID;
const guildId = process.env.GUILD_ID; // Optional: for guild-specific commands

const rest = new REST({ version: '10' }).setToken(token);

// For clearing guild commands
if (guildId) {
  (async () => {
    try {
      console.log('Started clearing guild application commands.');
      
      await rest.put(
        Routes.applicationGuildCommands(clientId, guildId),
        { body: [] }
      );
      
      console.log('Successfully cleared guild application commands.');
    } catch (error) {
      console.error(error);
    }
  })();
}

// For clearing global commands
(async () => {
  try {
    console.log('Started clearing global application commands.');
    
    await rest.put(
      Routes.applicationCommands(clientId),
      { body: [] }
    );
    
    console.log('Successfully cleared global application commands.');
  } catch (error) {
    console.error(error);
  }
})();
