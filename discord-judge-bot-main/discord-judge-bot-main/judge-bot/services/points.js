/**
 * @file points.js - Points Calculation Service
 * @description Sophisticated scoring system for challenge completion that factors in difficulty levels,
 *              hint usage penalties, and dynamic bonus calculations. Implements progressive hint costs,
 *              minimum score thresholds, and difficulty-based bonus multipliers to create engaging
 *              competitive gameplay with balanced risk-reward mechanics.
 * @version 1.1.0
 * @author gl0bal01
 * @since 2025-04-03
 */

class PointsCalculator {
  constructor(config) {
    this.config = config;
    this.startingPoints = config.bot.points.starting_points || 100;
    this.hintBasePenalty = config.bot.points.hint_base_penalty || 10;
    this.hintPenaltyIncrease = config.bot.points.hint_penalty_increase || 5;
  }

  /**
   * Calculate points earned for completing a game
   * @param {number} hintsUsed - Number of hints used
   * @param {Object} game - Game configuration
   * @returns {number} - Points earned
   */
  calculatePoints(hintsUsed, game) {
    // Start with base points
    let points = this.startingPoints;
    
    // Apply difficulty multiplier if present
    const difficulty = game.difficulty || 1;
    
    // Calculate points deduction for hints
    let hintDeduction = 0;
    
    for (let i = 0; i < hintsUsed; i++) {
      // Each hint costs more than the previous one
      const thisHintPenalty = this.hintBasePenalty + (i * this.hintPenaltyIncrease);
      hintDeduction += thisHintPenalty;
    }
    
    // Apply hint deduction
    points -= hintDeduction;
    
    // Ensure points don't go below minimum threshold (10% of starting points)
    const minPoints = Math.ceil(this.startingPoints * 0.1);
    points = Math.max(points, minPoints);
    
    // Apply difficulty bonus (higher difficulty yields significantly more points)
    if (difficulty > 1) {
      // More substantial bonus: 20% for level 2, 50% for level 3, 100% for level 4
      const difficultyBonusFactors = {
        2: 0.2,  // 20% bonus
        3: 0.5,  // 50% bonus
        4: 1.0   // 100% bonus (double points)
      };
      
      const bonusFactor = difficultyBonusFactors[difficulty] || (difficulty - 1) * 0.1;
      points = Math.ceil(points * (1 + bonusFactor));
    }
    
    return points;
  }

  /**
   * Calculate cost of next hint
   * @param {number} hintsUsed - Number of hints already used
   * @returns {number} - Cost of the next hint
   */
  calculateNextHintCost(hintsUsed) {
    return this.hintBasePenalty + (hintsUsed * this.hintPenaltyIncrease);
  }

  /**
   * Calculate maximum possible points remaining
   * @param {number} hintsUsed - Number of hints already used
   * @param {Object} game - Game configuration
   * @returns {number} - Maximum points possible
   */
  calculateMaxPossiblePoints(hintsUsed, game) {
    return this.calculatePoints(hintsUsed, game);
  }

  /**
   * Format points display string with difficulty bonus
   * @param {number} points - Points earned
   * @param {Object} game - Game configuration
   * @returns {string} - Formatted points string
   */
  formatPointsDisplay(points, game) {
    const difficulty = game.difficulty || 1;
    
    if (difficulty === 1) {
      return `${points} points`;
    }
    
    const difficultyBonus = (difficulty - 1) * 10; // 10% per level as percentage
    return `${points} points (includes ${difficultyBonus}% difficulty bonus)`;
  }
}

module.exports = PointsCalculator;
