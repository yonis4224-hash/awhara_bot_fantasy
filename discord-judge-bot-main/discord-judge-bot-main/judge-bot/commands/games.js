/**
 * @file games.js - Challenge Browser and Selection Command
 * @description Interactive Discord slash command for browsing and selecting available challenges.
 *              Features paginated display, sorting options (difficulty/name), progress tracking indicators,
 *              detailed challenge information, and intuitive navigation with selection dropdowns and back buttons.
 *              Provides comprehensive challenge overview with status indicators and difficulty ratings.
 * @version 1.1.0
 * @author gl0bal01
 * @since 2025-04-03
 */
const { SlashCommandBuilder, EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle } = require('discord.js');
const { getUser, getProgress } = require('../services/database');
const PaginatedMenu = require('../utils/pagination');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('judge-games')
    .setDescription('View available challenges and their descriptions')
    .addIntegerOption(option => 
      option.setName('page')
        .setDescription('Page number to view (for servers with many games)')
        .setRequired(false)
        .setMinValue(1)
    )
    .addStringOption(option =>
      option.setName('sort')
        .setDescription('Sort challenges by a specific criteria')
        .setRequired(false)
        .addChoices(
          { name: 'Difficulty (Ascending)', value: 'difficulty_asc' },
          { name: 'Difficulty (Descending)', value: 'difficulty_desc' },
          { name: 'Name (A-Z)', value: 'name_asc' },
          { name: 'Name (Z-A)', value: 'name_desc' }
        )
    ),
  
  async execute(interaction, { config, logger }) {
    const userId = interaction.user.id;
    logger.info(`${interaction.user.tag} (${userId}) used /judge-games`);
    
    try {
      // Get user data
      const user = await getUser(userId);
      
      if (!user) {
        await interaction.reply({
          content: '❌ You need to register first! Use `/judge-register` to get started.',
          ephemeral: true
        });
        return;
      }
      
      // Get games from config
      const games = config.games || {};
      let gameEntries = Object.entries(games);
      
      if (!games || gameEntries.length === 0) {
        await interaction.reply({
          content: '❌ No challenges are currently available. Please try again later.',
          ephemeral: true
        });
        return;
      }
      
      // Get sort option
      const sortOption = interaction.options.getString('sort') || 'difficulty_asc'; // Default to difficulty ascending
      
      // Sort game entries based on sort option
      gameEntries = await this.sortGames(gameEntries, sortOption, user);
      
      // Get page from options - ensure it's a valid number
      let requestedPage = 1;
      try {
        const pageOption = interaction.options.getInteger('page');
        if (pageOption !== null && Number.isInteger(pageOption) && pageOption > 0) {
          requestedPage = pageOption;
        }
      } catch (error) {
        logger.warn(`Invalid page parameter: ${error.message}`);
        // Default to page 1 if there's an error
        requestedPage = 1;
      }
      
      // Adjust items per page to display in a cleaner format
      const itemsPerPage = 9; // Show 9 items per page for better readability
      
      // Format items for the dropdown with progress indicators
      const formattedItems = await Promise.all(gameEntries.map(async ([gameId, game]) => {
        // Get game progress
        const progress = await getProgress(user.id, gameId);
        
        // Create status emoji
        let statusEmoji = '🔷'; // Not started
        if (progress && progress.completed) {
          statusEmoji = '✅'; // Completed
        } else if (progress && (progress.hints_used > 0 || progress.attempts > 0)) {
          statusEmoji = '🔶'; // In progress
        }
        
        // Add difficulty stars
        const difficulty = game.difficulty || 1;
        const difficultyStars = '⭐'.repeat(difficulty);
        
        return {
          label: game.name.substring(0, 100),
          description: `Difficulty: ${difficultyStars}`.substring(0, 100),
          value: gameId,
          emoji: statusEmoji
        };
      }));
      
      // Calculate total pages
      const totalPages = Math.max(1, Math.ceil(formattedItems.length / itemsPerPage));
      
      // Ensure requested page is valid
      if (requestedPage > totalPages) {
        requestedPage = totalPages;
      }
      
      // Create the paginated menu with the adjusted items per page
      const menu = new PaginatedMenu({
        items: formattedItems,
        itemsPerPage: itemsPerPage,
        placeholder: 'Select a challenge',
        customId: 'game-select'
      });
      
      // Set the page
      menu.setPage(requestedPage);
      
      // Calculate current page items for the embed
      const startIndex = (requestedPage - 1) * itemsPerPage;
      const endIndex = Math.min(startIndex + itemsPerPage, gameEntries.length);
      const currentGames = gameEntries.slice(startIndex, endIndex);
      
      // Create embed with improved formatting
      const embed = new EmbedBuilder()
        .setTitle('Available Challenges')
        .setColor('#0099ff')
        .setDescription(`Viewing page ${requestedPage} of ${totalPages}. Select a challenge to view details.\nSorted by: ${this.getSortName(sortOption)}`);
      
      // Add games with better formatting - one game per field, not inline
      for (const [gameId, game] of currentGames) {
        const progress = await getProgress(user.id, gameId);
        
        let statusEmoji = '🔷'; // Not started
        if (progress && progress.completed) {
          statusEmoji = '✅'; // Completed
        } else if (progress && (progress.hints_used > 0 || progress.attempts > 0)) {
          statusEmoji = '🔶'; // In progress
        }
        
        const difficulty = game.difficulty || 1;
        const difficultyStars = '⭐'.repeat(difficulty);
        
        // Create a properly formatted field for each game
        embed.addFields({
          name: `${statusEmoji} ${game.name}`,
          value: `Difficulty: ${difficultyStars}\n${game.description ? game.description.substring(0, 100) + (game.description.length > 100 ? '...' : '') : 'No description provided'}`,
          inline: false // Set to false for cleaner formatting
        });
      }
      
      // Add footer with total count
      embed.setFooter({ text: `${formattedItems.length} total challenges` });
      
      // Send the response with the paginated menu
      const response = await interaction.reply({
        embeds: [embed],
        components: menu.getComponents(),
        ephemeral: true
      });
      
      // Create collector
      menu.createCollector(interaction, {
        message: response,
        onSelect: async (i, gameId) => {
          // Handle game selection
          const game = games[gameId];
          
          if (!game) {
            await i.reply({
              content: '❌ Invalid game selection.',
              ephemeral: true
            });
            return;
          }
          
          // Get game progress
          const progress = await getProgress(user.id, gameId);
          
          // Create detailed embed for selected game with improved formatting
          const detailEmbed = new EmbedBuilder()
            .setTitle(`${game.name}`)
            .setColor('#0099ff')
            .setDescription(game.description || "No description available");
          
          // Add game details section
          detailEmbed.addFields(
            { 
              name: 'Challenge Details',
              value: `**Author:** ${game.author || 'Anonymous'}\n**Difficulty:** ${'⭐'.repeat(game.difficulty || 1)}\n**Reward Type:** ${game.reward_type === 'badgr' ? 'Digital Badge' : 'Text Reward'}`
            }
          );
          
          // Add progress information if any
          if (progress) {
            let statusText = 'Not started';
            
            if (progress.completed) {
              statusText = `✅ Completed with ${progress.points_earned} points`;
            } else if (progress.hints_used > 0 || progress.attempts > 0) {
              statusText = `🔶 In Progress\n• Hints used: ${progress.hints_used}\n• Attempts made: ${progress.attempts}`;
            }
            
            detailEmbed.addFields({
              name: 'Your Progress',
              value: statusText
            });
          }
          
          // Add help for next steps
          if (!progress || !progress.completed) {
            detailEmbed.addFields({
              name: 'How to Proceed',
              value: `• Use \`/judge-hint ${gameId}\` to get a hint\n• Use \`/judge-submit ${gameId}\` to submit your answer`
            });
          }
          
          // Create a back button as a proper button component
          const backButton = new ActionRowBuilder()
            .addComponents(
              new ButtonBuilder()
                .setCustomId(`back-to-list-${gameId}`)
                .setLabel('Back to Game List')
                .setStyle(ButtonStyle.Secondary)
            );
          
          // Update with game details and the fixed back button
          await i.update({
            embeds: [detailEmbed],
            components: [backButton]
          });
        },
        // Handle page changes
        onPageChange: async (i, page) => {
          // Update the embed with the current page games
          const newEmbed = new EmbedBuilder()
            .setTitle('Available Challenges')
            .setColor('#0099ff')
            .setDescription(`Viewing page ${page} of ${menu.totalPages}. Select a challenge to view details.\nSorted by: ${this.getSortName(sortOption)}`);
          
          // Re-fetch the current page items to reflect in the embed
          const startIndex = (page - 1) * menu.itemsPerPage;
          const endIndex = Math.min(startIndex + menu.itemsPerPage, gameEntries.length);
          const currentGames = gameEntries.slice(startIndex, endIndex);
          
          // Add fields for the current page - one game per field, not inline
          for (const [gameId, game] of currentGames) {
            const progress = await getProgress(user.id, gameId);
            
            let statusEmoji = '🔷'; // Not started
            if (progress && progress.completed) {
              statusEmoji = '✅'; // Completed
            } else if (progress && (progress.hints_used > 0 || progress.attempts > 0)) {
              statusEmoji = '🔶'; // In progress
            }
            
            const difficulty = game.difficulty || 1;
            const difficultyStars = '⭐'.repeat(difficulty);
            
            // Create a properly formatted field for each game
            newEmbed.addFields({
              name: `${statusEmoji} ${game.name}`,
              value: `Difficulty: ${difficultyStars}\n${game.description ? game.description.substring(0, 100) + (game.description.length > 100 ? '...' : '') : 'No description provided'}`,
              inline: false // Set to false for cleaner formatting
            });
          }
          
          // Add footer with total count
          newEmbed.setFooter({ text: `${formattedItems.length} total challenges` });
          
          // Update the message with the new embed and components
          await i.update({
            embeds: [newEmbed],
            components: menu.getComponents()
          });
        }
      });
      
      // Add a collector for all button interactions
      const buttonCollector = response.createMessageComponentCollector({
        filter: i => i.isButton() && i.user.id === interaction.user.id,
        time: 300000
      });
      
      buttonCollector.on('collect', async i => {
        // Check if it's a back button
        if (i.customId.startsWith('back-to-list')) {
          try {
            // Create a new reply with the games list
            const responseOptions = {
              embeds: [embed],
              components: menu.getComponents(),
              ephemeral: true
            };
            
            // Update with the game list
            await i.update(responseOptions);
          } catch (error) {
            logger.error(`Error handling back button: ${error.message}`);
            await i.deferUpdate().catch(() => {});
          }
        }
      });
      
    } catch (error) {
      logger.error(`Error in games command: ${error.message}`);
      await interaction.reply({
        content: '❌ An error occurred while retrieving games. Please try again later.',
        ephemeral: true
      });
    }
  },
  
  // Helper method to sort games based on sort option
  async sortGames(gameEntries, sortOption, user) {
    // Add progress info for sorting by completion status
    const gameEntriesWithProgress = await Promise.all(gameEntries.map(async ([gameId, game]) => {
      const progress = await getProgress(user.id, gameId);
      return {
        id: gameId,
        game: game,
        progress: progress,
        difficulty: game.difficulty || 1
      };
    }));
    
    // Sort based on option
    switch (sortOption) {
      case 'difficulty_asc':
        gameEntriesWithProgress.sort((a, b) => a.difficulty - b.difficulty);
        break;
      case 'difficulty_desc':
        gameEntriesWithProgress.sort((a, b) => b.difficulty - a.difficulty);
        break;
      case 'name_asc':
        gameEntriesWithProgress.sort((a, b) => a.game.name.localeCompare(b.game.name));
        break;
      case 'name_desc':
        gameEntriesWithProgress.sort((a, b) => b.game.name.localeCompare(a.game.name));
        break;
      default:
        // Default sort by difficulty ascending
        gameEntriesWithProgress.sort((a, b) => a.difficulty - b.difficulty);
    }
    
    // Convert back to [gameId, game] format
    return gameEntriesWithProgress.map(entry => [entry.id, entry.game]);
  },
  
  // Helper method to get readable sort option name
  getSortName(sortOption) {
    const sortNames = {
      'difficulty_asc': 'Difficulty (Easiest First)',
      'difficulty_desc': 'Difficulty (Hardest First)',
      'name_asc': 'Name (A-Z)',
      'name_desc': 'Name (Z-A)'
    };
    
    return sortNames[sortOption] || 'Default';
  }
};