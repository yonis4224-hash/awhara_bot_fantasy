/**
 * @file pagination.js - Interactive Pagination Utility
 * @description Comprehensive pagination system for Discord select menus and button navigation.
 *              Handles large datasets by splitting them into manageable pages with automatic navigation
 *              controls. Features customizable item formatting, page indicators, and event handling
 *              for seamless user interactions across multiple pages of content.
 * @version 1.1.0
 * @author gl0bal01
 * @since 2025-04-03
 */
const { StringSelectMenuBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle } = require('discord.js');

/**
 * Creates paginated dropdown menus for Discord interactions
 * Use this when you have more than 25 options to display in a dropdown
 */
class PaginatedMenu {
  /**
   * Create a new paginated menu
   * @param {Object} options - Configuration options
   * @param {Array} options.items - Array of items to paginate 
   * @param {number} options.itemsPerPage - Number of items per page (max 25, default 24)
   * @param {Function} options.formatItem - Function to format each item for the dropdown
   * @param {string} options.placeholder - Placeholder text for the dropdown
   * @param {string} options.customId - Custom ID for the dropdown component
   */
  constructor(options) {
    this.items = options.items || [];
    this.itemsPerPage = Math.min(options.itemsPerPage || 24, 24); // Max 24 to leave room for pagination
    this.formatItem = options.formatItem || this.defaultFormatItem;
    this.placeholder = options.placeholder || 'Select an option';
    this.customId = options.customId || 'paginated-dropdown';
    
    // Calculate total pages immediately to ensure it's set properly
    this.totalPages = Math.max(1, Math.ceil(this.items.length / this.itemsPerPage));
    this.currentPage = 1;
  }
  
  /**
   * Default item formatter if none provided
   * @param {*} item - The item to format
   * @returns {Object} Formatted item for the dropdown
   */
  defaultFormatItem(item) {
    if (typeof item === 'string') {
      return {
        label: item.substring(0, 100),
        value: item,
        description: ''
      };
    }
    
    if (typeof item === 'object') {
      return {
        label: (item.label || item.name || 'Item').substring(0, 100),
        value: item.value || item.id || 'value',
        description: (item.description || '').substring(0, 100),
        emoji: item.emoji
      };
    }
    
    return {
      label: 'Item',
      value: 'value',
      description: ''
    };
  }
  
  /**
   * Set current page
   * @param {number} page - Page number
   */
  setPage(page) {
    try {
      // Ensure page is a valid number
      const pageNum = Number(page);
      if (Number.isNaN(pageNum) || !Number.isInteger(pageNum)) {
        this.currentPage = 1;
        return this;
      }
      
      // Apply bounds
      if (pageNum < 1) this.currentPage = 1;
      else if (pageNum > this.totalPages) this.currentPage = this.totalPages;
      else this.currentPage = pageNum;
      
      return this;
    } catch (error) {
      // Default to first page on error
      this.currentPage = 1;
      return this;
    }
  }
  
  /**
   * Get the components for the current page
   * @returns {Array} Array of ActionRowBuilder components
   */
  getComponents() {
    const components = [];
    
    // Recalculate total pages to handle dynamic changes in items array
    this.totalPages = Math.max(1, Math.ceil(this.items.length / this.itemsPerPage));
    
    // Ensure current page is valid
    if (this.currentPage > this.totalPages) {
      this.currentPage = this.totalPages;
    }
    
    // Calculate current page items
    const startIndex = (this.currentPage - 1) * this.itemsPerPage;
    const endIndex = Math.min(startIndex + this.itemsPerPage, this.items.length);
    const currentItems = this.items.slice(startIndex, endIndex);
    
    // Create dropdown menu
    const selectMenu = new StringSelectMenuBuilder()
      .setCustomId(this.customId)
      .setPlaceholder(`${this.placeholder} (Page ${this.currentPage}/${this.totalPages})`)
      .setMinValues(1)
      .setMaxValues(1);
    
    // Add options to dropdown
    if (currentItems.length > 0) {
      currentItems.forEach(item => {
        try {
          const formattedItem = this.formatItem(item);
          selectMenu.addOptions(formattedItem);
        } catch (error) {
          console.error('Error formatting item:', error);
          // Continue with other items if one fails
        }
      });
    } else {
      // Add a placeholder option if no items are available for this page
      selectMenu.addOptions({
        label: 'No options available',
        value: 'no-options',
        description: 'There are no items to display on this page'
      });
      selectMenu.setDisabled(true);
    }
    
    components.push(new ActionRowBuilder().addComponents(selectMenu));
    
    // Add pagination buttons if needed
    if (this.totalPages > 1) {
      const paginationRow = new ActionRowBuilder();
      
      // Previous page button
      const prevButton = new ButtonBuilder()
        .setCustomId('prev-page')
        .setLabel('◀️ Previous')
        .setStyle(ButtonStyle.Secondary)
        .setDisabled(this.currentPage === 1);
      
      // Next page button
      const nextButton = new ButtonBuilder()
        .setCustomId('next-page')
        .setLabel('Next ▶️')
        .setStyle(ButtonStyle.Secondary)
        .setDisabled(this.currentPage === this.totalPages);
      
      // Page indicator
      const pageIndicator = new ButtonBuilder()
        .setCustomId('page-indicator')
        .setLabel(`Page ${this.currentPage} of ${this.totalPages}`)
        .setStyle(ButtonStyle.Primary)
        .setDisabled(true);
      
      paginationRow.addComponents(prevButton, pageIndicator, nextButton);
      components.push(paginationRow);
    }
    
    return components;
  }
  
  /**
   * Create a collector for the pagination menu
   * @param {Object} interaction - Discord interaction
   * @param {Object} options - Collector options
   * @param {Function} options.onSelect - Function called when item selected
   * @param {Function} options.onPageChange - Function called when page changes
   * @param {Function} options.filter - Filter function for the collector
   * @param {number} options.time - Collector timeout in ms
   * @returns {InteractionCollector} The created collector
   */
  createCollector(interaction, options = {}) {
    const response = options.message || interaction;
    const filter = options.filter || (i => i.user.id === interaction.user.id);
    const time = options.time || 300000; // 5 minutes
    
    const collector = response.createMessageComponentCollector({ filter, time });
    
    collector.on('collect', async i => {
      try {
        // Handle pagination buttons
        if (i.customId === 'prev-page') {
          this.setPage(this.currentPage - 1);
          
          if (options.onPageChange) {
            await options.onPageChange(i, this.currentPage);
          } else {
            await i.update({ components: this.getComponents() });
          }
          return;
        } 
        
        if (i.customId === 'next-page') {
          this.setPage(this.currentPage + 1);
          
          if (options.onPageChange) {
            await options.onPageChange(i, this.currentPage);
          } else {
            await i.update({ components: this.getComponents() });
          }
          return;
        }
        
        // Handle select menu
        if (i.customId === this.customId && options.onSelect) {
          await options.onSelect(i, i.values[0]);
        }
      } catch (error) {
        console.error('Error in collector:', error);
        await i.reply({
          content: 'There was an error processing your selection. Please try again.',
          ephemeral: true
        }).catch(() => {});
      }
    });
    
    return collector;
  }
  
  /**
   * Helper function to handle the initial response
   * @param {Object} interaction - Discord interaction
   * @param {Object} options - Response options
   * @param {Object} options.embed - Embed to send
   * @param {boolean} options.ephemeral - Whether the response should be ephemeral
   * @param {Function} options.onSelect - Function called when item selected
   * @param {Function} options.onPageChange - Function called when page changes
   * @returns {Promise<Message>} The sent message
   */
  async respond(interaction, options = {}) {
    const responseOptions = {
      embeds: options.embed ? [options.embed] : [],
      components: this.getComponents(),
      ephemeral: options.ephemeral !== undefined ? options.ephemeral : true
    };
    
    const response = await interaction.reply(responseOptions);
    
    this.createCollector(interaction, {
      message: response,
      onSelect: options.onSelect,
      onPageChange: options.onPageChange,
      time: options.time
    });
    
    return response;
  }
}

module.exports = PaginatedMenu;