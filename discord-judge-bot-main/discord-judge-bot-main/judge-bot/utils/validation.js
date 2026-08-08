/**
 * @file validation.js - Input Validation and Security Service
 * @description Comprehensive validation utilities providing input sanitization, format verification,
 *              and security controls for user-submitted data. Includes email validation, admin access
 *              control, answer comparison logic, and protection against injection attacks. Essential
 *              for maintaining application security and data integrity.
 * @version 1.1.0
 * @author gl0bal01
 * @since 2025-04-03
 */

/**
 * Validation utility functions with enhanced security features
 */
class Validation {
  /**
   * Validate an email address
   * @param {string} email - Email to validate
   * @returns {boolean} - True if email is valid
   */
  static isValidEmail(email) {
    if (!email) return false;
    
    // More comprehensive email validation regex
    const emailRegex = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/;
    return emailRegex.test(email) && email.length <= 254; // RFC 5321 length limit
  }

  /**
   * Check if user is an admin
   * @param {string} userId - Discord user ID
   * @param {Array} adminList - List of admin user IDs
   * @returns {boolean} - True if user is an admin
   */
  static isAdmin(userId, adminList = []) {
    if (!userId || typeof userId !== 'string') return false;
    return Array.isArray(adminList) && adminList.includes(userId);
  }

  /**
   * Validate game ID exists in configuration
   * @param {string} gameId - Game ID to validate
   * @param {Object} gamesConfig - Games configuration
   * @returns {boolean} - True if game ID exists
   */
  static isValidGameId(gameId, gamesConfig) {
    if (!gameId || typeof gameId !== 'string') return false;
    return gamesConfig && 
           gamesConfig.games && 
           typeof gamesConfig.games === 'object' && 
           gamesConfig.games[gameId] !== undefined;
  }

  /**
   * Sanitize user input for display or logging
   * @param {string} input - Input to sanitize
   * @returns {string} - Sanitized input
   */
  static sanitizeInput(input) {
    if (!input) return '';
    
    // Convert to string if not already
    const str = String(input);
    
    // Enhanced sanitization to remove potentially harmful characters
    return str
      .replace(/[<>]/g, '') // Remove angle brackets
      .replace(/javascript:/gi, '') // Remove javascript: protocol
      .replace(/on\w+=/gi, '') // Remove event handlers
      .replace(/data:/gi, 'data&#58;') // Neutralize data: URIs
      .replace(/&/g, '&amp;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#x27;')
      .replace(/\//g, '&#x2F;')
      .trim();
  }

  /**
   * Check if an answer is correct for a given game
   * @param {string} userAnswer - User's submitted answer
   * @param {string} correctAnswer - Correct answer from game config
   * @returns {boolean} - True if answer is correct
   */
  static isCorrectAnswer(userAnswer, correctAnswer) {
    if (!userAnswer || !correctAnswer) return false;
    
    // Normalize both strings for case-insensitive comparison
    // Remove extra whitespace and trim
    const normalizedUserAnswer = userAnswer.toLowerCase().replace(/\s+/g, ' ').trim();
    const normalizedCorrectAnswer = correctAnswer.toLowerCase().replace(/\s+/g, ' ').trim();
    
    return normalizedUserAnswer === normalizedCorrectAnswer;
  }

  /**
   * Validate a hint index is available for a game
   * @param {number} hintIndex - Hint index (0-based)
   * @param {Object} game - Game configuration
   * @returns {boolean} - True if hint is available
   */
  static isValidHintIndex(hintIndex, game) {
    return game && 
           game.hints && 
           Array.isArray(game.hints) && 
           Number.isInteger(hintIndex) &&
           hintIndex >= 0 && 
           hintIndex < game.hints.length;
  }
  
  /**
   * Validate Discord user ID format
   * @param {string} userId - Discord user ID to validate
   * @returns {boolean} - True if user ID format is valid
   */
  static isValidUserId(userId) {
    if (!userId || typeof userId !== 'string') return false;
    // Discord IDs are numeric and typically 17-20 characters
    return /^\d{17,20}$/.test(userId);
  }
  
  /**
   * Validate that a value is a safe integer
   * @param {any} value - Value to check
   * @param {number} min - Minimum allowed value
   * @param {number} max - Maximum allowed value
   * @returns {boolean} - True if value is a safe integer within range
   */
  static isSafeInteger(value, min = Number.MIN_SAFE_INTEGER, max = Number.MAX_SAFE_INTEGER) {
    const num = Number(value);
    return Number.isSafeInteger(num) && num >= min && num <= max;
  }
  
  /**
   * Sanitize a filename to prevent directory traversal
   * @param {string} filename - Filename to sanitize
   * @returns {string} - Sanitized filename
   */
  static sanitizeFilename(filename) {
    if (!filename || typeof filename !== 'string') return '';

    // Remove path traversal characters and limit to safe characters
    return filename
      .replace(/\.\./g, '')
      .replace(/[\/\\]/g, '')
      .replace(/[^a-zA-Z0-9_.-]/g, '')
      .substring(0, 255); // Limit length
  }

  /**
   * Resolve a game file path safely, preventing path traversal.
   * Returns the resolved path or null if the gameId is invalid.
   * @param {string} gameId - Game ID (user-supplied)
   * @param {string} gamesDir - Absolute path to the games directory
   * @returns {string|null} Safe resolved path or null
   */
  static resolveGamePath(gameId, gamesDir) {
    if (!gameId || typeof gameId !== 'string') return null;
    const sanitized = Validation.sanitizeFilename(gameId);
    if (!sanitized) return null;
    const resolved = require('path').resolve(gamesDir, `${sanitized}.yaml`);
    if (!resolved.startsWith(require('path').resolve(gamesDir))) return null;
    return resolved;
  }

  /**
   * Mask an email address for safe display (e.g., "j***@example.com")
   * @param {string} email - Email to mask
   * @returns {string} Masked email
   */
  static maskEmail(email) {
    if (!email || typeof email !== 'string') return 'No email registered';
    const parts = email.split('@');
    if (parts.length !== 2) return '***';
    const local = parts[0];
    const masked = local.charAt(0) + '***';
    return `${masked}@${parts[1]}`;
  }

  /**
   * Validate YAML content structure for games
   * @param {Object} content - Parsed YAML content
   * @returns {boolean} - True if structure is valid
   */
  static isValidGameStructure(content) {
    if (!content || typeof content !== 'object') return false;
    
    // Check basic structure (has games object)
    if (!content.games || typeof content.games !== 'object') return false;
    
    // Validate each game has required fields
    for (const [gameId, game] of Object.entries(content.games)) {
      if (!game.name || !game.description || !game.answer) {
        return false;
      }
    }
    
    return true;
  }
}

module.exports = Validation;