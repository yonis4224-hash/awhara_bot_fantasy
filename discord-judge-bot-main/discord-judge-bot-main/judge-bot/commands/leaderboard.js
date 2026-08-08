/**
 * @file leaderboard.js - Global Leaderboard Display Command
 * @description Interactive Discord slash command for displaying user rankings and challenge completion
 *              statistics. Features pagination, detailed completion history mode, user highlighting,
 *              and real-time navigation controls. Supports both compact ranking view and comprehensive
 *              completion timeline for competitive tracking and community engagement.
 * @version 1.1.0
 * @author gl0bal01
 * @since 2025-04-03
 */
const { SlashCommandBuilder, EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle } = require('discord.js');
const { getUser, getLeaderboard, getDetailedLeaderboard } = require('../services/database');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('judge-leaderboard')
    .setDescription('View the global leaderboard')
    .addIntegerOption(option => 
      option.setName('page')
        .setDescription('Page number to view (default: 1)')
        .setRequired(false)
        .setMinValue(1)
    )
    .addIntegerOption(option => 
      option.setName('entries')
        .setDescription('Number of entries per page (default: 10, max: 25)')
        .setRequired(false)
        .setMinValue(1)
        .setMaxValue(25)
    )
    .addBooleanOption(option =>
      option.setName('detailed')
        .setDescription('Show detailed completion history (default: false)')
        .setRequired(false)
    ),
  
  async execute(interaction, { config, logger }) {
    const userId = interaction.user.id;
    logger.info(`${interaction.user.tag} (${userId}) used /judge-leaderboard`);
    
    try {
      // Get options
      const pageNumber = interaction.options.getInteger('page') || 1;
      const entriesPerPage = interaction.options.getInteger('entries') || 10;
      const showDetailed = interaction.options.getBoolean('detailed') || false;
      
      // Check if user is registered
      const user = await getUser(userId);
      
      if (!user) {
        await interaction.reply({
          content: '❌ You need to register first! Use `/judge-register` to get started.',
          ephemeral: true
        });
        return;
      }
      
      // Show detailed leaderboard if requested
      if (showDetailed) {
        await interaction.deferReply({ ephemeral: true });
        
        // Get detailed leaderboard data - get more entries for pagination
        const limit = entriesPerPage * 10; // Get enough for 10 pages
        const detailedData = await getDetailedLeaderboard(limit);
        
        if (!detailedData || detailedData.length === 0) {
          await interaction.editReply({
            content: 'No challenge completions available yet. Be the first to complete a challenge!',
          });
          return;
        }
        
        // Calculate total pages and current page data
        const totalItems = detailedData.length;
        const totalPages = Math.ceil(totalItems / entriesPerPage);
        const validPage = Math.min(Math.max(1, pageNumber), totalPages);
        
        const startIndex = (validPage - 1) * entriesPerPage;
        const endIndex = Math.min(startIndex + entriesPerPage, totalItems);
        const currentPageData = detailedData.slice(startIndex, endIndex);
        
        // Create detailed leaderboard embed
        const embed = new EmbedBuilder()
          .setTitle('🏆 Challenge Completion History')
          .setColor('#FFD700')
          .setDescription(`Recent game completions by all players (Page ${validPage}/${totalPages})`);
        
        let descriptionText = '';
        
        // Add completion entries
        for (const entry of currentPageData) {
          const game = config.games[entry.game_id];
          const gameName = game ? game.name : entry.game_id;
          const completionDate = entry.completion_date ? 
            new Date(entry.completion_date).toISOString().replace('T', ' at ').substring(0, 19) : 
            'unknown date';
          
          descriptionText += `**${entry.username}** - ${gameName}: ✅ Completed (on ${completionDate})\n`;
        }
        
        embed.setDescription(`Recent game completions by all players (Page ${validPage}/${totalPages})\n\n${descriptionText}`);
        
        // Add footer with encourage message
        embed.setFooter({
          text: `Showing ${startIndex + 1}-${endIndex} of ${totalItems} completions`
        });
        
        // Add pagination buttons if needed
        const components = [];
        if (totalPages > 1) {
          const row = new ActionRowBuilder()
            .addComponents(
              new ButtonBuilder()
                .setCustomId('first_page')
                .setLabel('⏮️ First')
                .setStyle(ButtonStyle.Secondary)
                .setDisabled(validPage === 1),
              new ButtonBuilder()
                .setCustomId('prev_page')
                .setLabel('◀️ Previous')
                .setStyle(ButtonStyle.Primary)
                .setDisabled(validPage === 1),
              new ButtonBuilder()
                .setCustomId('next_page')
                .setLabel('Next ▶️')
                .setStyle(ButtonStyle.Primary)
                .setDisabled(validPage === totalPages),
              new ButtonBuilder()
                .setCustomId('last_page')
                .setLabel('Last ⏭️')
                .setStyle(ButtonStyle.Secondary)
                .setDisabled(validPage === totalPages)
            );
          components.push(row);
        }
        
        const message = await interaction.editReply({ 
          embeds: [embed],
          components
        });
        
        // Only set up collector if we have pagination
        if (components.length > 0) {
          const collector = message.createMessageComponentCollector({ 
            filter: i => i.user.id === interaction.user.id,
            time: 300000 // 5 minutes
          });
          
          collector.on('collect', async i => {
            let newPage = validPage;
            
            if (i.customId === 'first_page') newPage = 1;
            else if (i.customId === 'prev_page') newPage = validPage - 1;
            else if (i.customId === 'next_page') newPage = validPage + 1;
            else if (i.customId === 'last_page') newPage = totalPages;
            
            if (newPage !== validPage) {
              // Calculate new page data
              const startIndex = (newPage - 1) * entriesPerPage;
              const endIndex = Math.min(startIndex + entriesPerPage, totalItems);
              const newPageData = detailedData.slice(startIndex, endIndex);
              
              // Rebuild description text for new page
              let newDescriptionText = '';
              
              // Add completion entries
              for (const entry of newPageData) {
                const game = config.games[entry.game_id];
                const gameName = game ? game.name : entry.game_id;
                const completionDate = entry.completion_date ? 
                  new Date(entry.completion_date).toISOString().replace('T', ' at ').substring(0, 19) : 
                  'unknown date';
                
                newDescriptionText += `**${entry.username}** - ${gameName}: ✅ Completed (on ${completionDate})\n`;
              }
              
              // Update embed
              embed.setDescription(`Recent game completions by all players (Page ${newPage}/${totalPages})\n\n${newDescriptionText}`);
              embed.setFooter({
                text: `Showing ${startIndex + 1}-${endIndex} of ${totalItems} completions`
              });
              
              // Update buttons
              const updatedRow = new ActionRowBuilder()
                .addComponents(
                  new ButtonBuilder()
                    .setCustomId('first_page')
                    .setLabel('⏮️ First')
                    .setStyle(ButtonStyle.Secondary)
                    .setDisabled(newPage === 1),
                  new ButtonBuilder()
                    .setCustomId('prev_page')
                    .setLabel('◀️ Previous')
                    .setStyle(ButtonStyle.Primary)
                    .setDisabled(newPage === 1),
                  new ButtonBuilder()
                    .setCustomId('next_page')
                    .setLabel('Next ▶️')
                    .setStyle(ButtonStyle.Primary)
                    .setDisabled(newPage === totalPages),
                  new ButtonBuilder()
                    .setCustomId('last_page')
                    .setLabel('Last ⏭️')
                    .setStyle(ButtonStyle.Secondary)
                    .setDisabled(newPage === totalPages)
                );
              
              // Update the message
              await i.update({ 
                embeds: [embed],
                components: [updatedRow]
              });
            } else {
              await i.deferUpdate();
            }
          });
        }
        
        return;
      }
      
      // Show regular leaderboard with pagination
      await interaction.deferReply({
        ephemeral: false
      });
      
      // Get more entries for pagination (up to 250)
      const maxEntries = 250;
      const leaderboardData = await getLeaderboard(maxEntries);
      
      if (!leaderboardData || leaderboardData.length === 0) {
        await interaction.editReply({
          content: 'No leaderboard data available yet. Be the first to complete a challenge!',
        });
        return;
      }
      
      // Calculate total pages and current page data
      const totalItems = leaderboardData.length;
      const totalPages = Math.ceil(totalItems / entriesPerPage);
      const validPage = Math.min(Math.max(1, pageNumber), totalPages);
      
      const startIndex = (validPage - 1) * entriesPerPage;
      const endIndex = Math.min(startIndex + entriesPerPage, totalItems);
      const currentPageData = leaderboardData.slice(startIndex, endIndex);
      
      // Create leaderboard embed
      const embed = new EmbedBuilder()
        .setTitle('🏆 Challenge Leaderboard')
        .setColor('#FFD700')
        .setDescription(`Top scorers based on points earned (Page ${validPage}/${totalPages})`);
      
      // Add leaderboard entries
      let leaderboardText = '';
      
      currentPageData.forEach((entry, index) => {
        // Calculate the actual position in the leaderboard
        const position = startIndex + index + 1;
        
        // Create medal emoji for top 3
        let medal = '';
        if (position === 1) medal = '🥇';
        else if (position === 2) medal = '🥈';
        else if (position === 3) medal = '🥉';
        else medal = `${position}.`;
        
        // Highlight the current user
        const isCurrentUser = entry.username === interaction.user.username;
        const username = isCurrentUser ? `**${entry.username}**` : entry.username;
        
        // Add to leaderboard text
        leaderboardText += `${medal} ${username} - ${entry.total_points || 0} points (${entry.completed_games || 0} challenges)\n`;
      });
      
      embed.setDescription(`Top scorers based on points earned (Page ${validPage}/${totalPages})\n\n${leaderboardText}`);
      
      // Add footer with encourage message
      embed.setFooter({
        text: `Showing ranks ${startIndex + 1}-${endIndex} of ${totalItems} • Try "/judge-leaderboard detailed:true" for completion history`
      });
      
      // Add pagination buttons if needed
      const components = [];
      if (totalPages > 1) {
        const row = new ActionRowBuilder()
          .addComponents(
            new ButtonBuilder()
              .setCustomId('first_page')
              .setLabel('⏮️ First')
              .setStyle(ButtonStyle.Secondary)
              .setDisabled(validPage === 1),
            new ButtonBuilder()
              .setCustomId('prev_page')
              .setLabel('◀️ Previous')
              .setStyle(ButtonStyle.Primary)
              .setDisabled(validPage === 1),
            new ButtonBuilder()
              .setCustomId('next_page')
              .setLabel('Next ▶️')
              .setStyle(ButtonStyle.Primary)
              .setDisabled(validPage === totalPages),
            new ButtonBuilder()
              .setCustomId('last_page')
              .setLabel('Last ⏭️')
              .setStyle(ButtonStyle.Secondary)
              .setDisabled(validPage === totalPages)
          );
        components.push(row);
      }
      
      const message = await interaction.editReply({ 
        embeds: [embed],
        components
      });
      
      // Only set up collector if we have pagination
      if (components.length > 0) {
        const collector = message.createMessageComponentCollector({ 
          filter: i => i.user.id === interaction.user.id,
          time: 300000 // 5 minutes
        });
        
        collector.on('collect', async i => {
          let newPage = validPage;
          
          if (i.customId === 'first_page') newPage = 1;
          else if (i.customId === 'prev_page') newPage = validPage - 1;
          else if (i.customId === 'next_page') newPage = validPage + 1;
          else if (i.customId === 'last_page') newPage = totalPages;
          
          if (newPage !== validPage) {
            // Calculate new page data
            const startIndex = (newPage - 1) * entriesPerPage;
            const endIndex = Math.min(startIndex + entriesPerPage, totalItems);
            const newPageData = leaderboardData.slice(startIndex, endIndex);
            
            // Rebuild leaderboard text for new page
            let newLeaderboardText = '';
            
            newPageData.forEach((entry, index) => {
              // Calculate the actual position in the leaderboard
              const position = startIndex + index + 1;
              
              // Create medal emoji for top 3
              let medal = '';
              if (position === 1) medal = '🥇';
              else if (position === 2) medal = '🥈';
              else if (position === 3) medal = '🥉';
              else medal = `${position}.`;
              
              // Highlight the current user
              const isCurrentUser = entry.username === interaction.user.username;
              const username = isCurrentUser ? `**${entry.username}**` : entry.username;
              
              // Add to leaderboard text
              newLeaderboardText += `${medal} ${username} - ${entry.total_points || 0} points (${entry.completed_games || 0} challenges)\n`;
            });
            
            // Update embed
            embed.setDescription(`Top scorers based on points earned (Page ${newPage}/${totalPages})\n\n${newLeaderboardText}`);
            embed.setFooter({
              text: `Showing ranks ${startIndex + 1}-${endIndex} of ${totalItems} • Try "/judge-leaderboard detailed:true" for completion history`
            });
            
            // Update buttons
            const updatedRow = new ActionRowBuilder()
              .addComponents(
                new ButtonBuilder()
                  .setCustomId('first_page')
                  .setLabel('⏮️ First')
                  .setStyle(ButtonStyle.Secondary)
                  .setDisabled(newPage === 1),
                new ButtonBuilder()
                  .setCustomId('prev_page')
                  .setLabel('◀️ Previous')
                  .setStyle(ButtonStyle.Primary)
                  .setDisabled(newPage === 1),
                new ButtonBuilder()
                  .setCustomId('next_page')
                  .setLabel('Next ▶️')
                  .setStyle(ButtonStyle.Primary)
                  .setDisabled(newPage === totalPages),
                new ButtonBuilder()
                  .setCustomId('last_page')
                  .setLabel('Last ⏭️')
                  .setStyle(ButtonStyle.Secondary)
                  .setDisabled(newPage === totalPages)
              );
            
            // Update the message
            await i.update({ 
              embeds: [embed],
              components: [updatedRow]
            });
          } else {
            await i.deferUpdate();
          }
        });
      }
    } catch (error) {
      logger.error(`Error in leaderboard command: ${error.message}`);
      if (interaction.deferred) {
        await interaction.editReply({
          content: '❌ An error occurred while retrieving the leaderboard. Please try again later.',
        });
      } else {
        await interaction.reply({
          content: '❌ An error occurred while retrieving the leaderboard. Please try again later.',
          ephemeral: true
        });
      }
    }
  },
};
