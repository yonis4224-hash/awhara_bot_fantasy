#!/bin/bash
# save_and_restart.sh - Automated Bot Update and Restart Script
# Description: Development utility script for quickly stopping the running bot process,
#              rebuilding the games configuration from approved challenges, and restarting
#              the bot with updated configurations. Includes backup creation and error handling.

# Stop the running bot (adjust as needed for your environment)
echo "Stopping the current bot process..."
pkill -f "node index.js" || echo "No process found, continuing..."

# Apply the updated reloadGamesConfig function 
echo "Updating maker-manage.js and maker.js..."
# Back up original files
cp commands/maker-manage.js commands/maker-manage.js.bak
cp commands/maker.js commands/maker.js.bak

# Edit the files - you can replace this with your preferred editing method
# For maker-manage.js:
# 1. Find the reloadGamesConfig function
# 2. Replace it with the updated version

# For maker.js:
# 1. Update the handleGameCreate function as needed

# Force a reload of games.yaml now
echo "Manually reloading games.yaml..."
node -e "
const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');

try {
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
      const gameData = yaml.load(content);
      
      if (gameData && gameData[gameId] && gameData[gameId].approved) {
        // Get the game data and clean it up for the config
        const game = gameData[gameId];
        
        mergedConfig.games[gameId] = {
          name: game.name,
          description: game.description,
          author: game.author,
          answer: game.answer,
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
      console.error(`Error processing ${file}: ${error.message}`);
    }
  }
  
  // Write the updated config
  fs.writeFileSync(
    path.join(__dirname, 'config/games.yaml'),
    yaml.dump(mergedConfig),
    'utf8'
  );
  
  console.log('Successfully updated games.yaml with approved games.');
  console.log('Games included:', Object.keys(mergedConfig.games));
} catch (error) {
  console.error('Error updating games.yaml:', error);
}
"

# Start the bot again
echo "Starting the bot..."
node index.js &

echo "Bot restart complete!"
