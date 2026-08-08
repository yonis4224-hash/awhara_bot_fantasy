/**
 * @file register.js - User Registration Command
 * @description Discord slash command for user registration that collects email addresses for badge
 *              delivery and progress tracking. Features modal-based email input with validation,
 *              secure database storage, and user-friendly response handling. Ensures proper email
 *              format validation and provides clear registration status feedback to users.
 * @version 1.1.0
 * @author gl0bal01
 * @since 2025-04-03
 */
const { SlashCommandBuilder, EmbedBuilder, ActionRowBuilder, ModalBuilder, TextInputBuilder, TextInputStyle } = require('discord.js');
const { registerUser, getUser } = require('../services/database');
const Validation = require('../utils/validation');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('judge-register')
    .setDescription('Register your email to track progress and receive badges'),
  
  async execute(interaction, { config, logger }) {
    const userId = interaction.user.id;
    logger.info(`${interaction.user.tag} (${userId}) used /judge-register`);
    
    // Create a modal for email input
    const modal = new ModalBuilder()
      .setCustomId('register-modal')
      .setTitle('Register for ScoreBot');
    
    // Add email input field
    const emailInput = new TextInputBuilder()
      .setCustomId('email-input')
      .setLabel('Enter your email for badge delivery')
      .setPlaceholder('example@domain.com')
      .setStyle(TextInputStyle.Short)
      .setRequired(true);
    
    // Create action row with the input field
    const actionRow = new ActionRowBuilder().addComponents(emailInput);
    modal.addComponents(actionRow);
    
    // Show the modal
    await interaction.showModal(modal);
    
    try {
      // Wait for modal submission
      const submission = await interaction.awaitModalSubmit({
        time: 60000, // Wait for 1 minute
        filter: i => i.customId === 'register-modal'
      }).catch(() => null);
      
      if (!submission) {
        logger.info(`${interaction.user.tag} did not submit the registration form`);
        return;
      }
      
      // Get the email from submission
      const email = submission.fields.getTextInputValue('email-input');
      
      // Validate email
      if (!Validation.isValidEmail(email)) {
        await submission.reply({
          content: '❌ Please provide a valid email address.',
          ephemeral: true
        });
        return;
      }
      
      // Register user in database
      const result = await registerUser(
        userId, 
        interaction.user.username, 
        email
      );
      
      if (result.success) {
        const embed = new EmbedBuilder()
          .setTitle('Registration Successful')
          .setColor('#00ff00')
          .setDescription(`You have been registered with email: ${email}`)
          .addFields(
            { 
              name: 'Next Steps', 
              value: 'Use `/judge-games` to see available challenges!' 
            }
          )
          .setFooter({ 
            text: 'Your progress and earned badges will be tracked with this email.' 
          });
        
        await submission.reply({ 
          embeds: [embed], 
          ephemeral: true 
        });
      } else {
        logger.error(`Error registering user ${userId}: ${result.error}`);
        await submission.reply({
          content: '❌ There was an error processing your registration. Please try again later.',
          ephemeral: true
        });
      }
    } catch (error) {
      logger.error(`Error in register command: ${error.message}`);
      // If we reach here, something went wrong with the modal or submission
      if (interaction.replied || interaction.deferred) {
        await interaction.followUp({
          content: '❌ There was an error processing your registration. Please try again later.',
          ephemeral: true
        });
      }
    }
  },
};
