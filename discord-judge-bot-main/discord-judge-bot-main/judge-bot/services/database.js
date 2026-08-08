/**
 * @file database.js - Core Database Service Layer
 * @description Comprehensive SQLite database service providing secure user management, progress tracking,
 *              and statistics collection for the Discord Judge Bot. Features parameterized queries,
 *              transaction support, input validation, and comprehensive error handling. Manages user
 *              registration, game progress, hint tracking, rewards, and leaderboard functionality.
 * @version 1.1.0
 * @author gl0bal01
 * @since 2025-04-03
 */

const sqlite3 = require('sqlite3');
const { open } = require('sqlite');
const path = require('path');

let db;

/**
 * Initialize the database and create tables if they don't exist
 * @returns {Promise<boolean>} Success status
 */
async function initializeDatabase() {
  try {
    // Ensure we use path.join for cross-platform compatibility
    const dbPath = path.join(__dirname, '../data/scorebot.db');
    
    // Open database with specific options
    db = await open({
      filename: dbPath,
      driver: sqlite3.Database,
      // Add SQLite pragmas for better security and performance
      mode: sqlite3.OPEN_READWRITE | sqlite3.OPEN_CREATE
    });
    
    // Enable foreign keys
    await db.exec('PRAGMA foreign_keys = ON;');
    
    // Create tables if they don't exist
    await db.exec(`
      CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        discord_id TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE,
        username TEXT NOT NULL,
        registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      );
      
      CREATE TABLE IF NOT EXISTS progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        game_id TEXT NOT NULL,
        completed BOOLEAN DEFAULT 0,
        hints_used INTEGER DEFAULT 0,
        points_earned INTEGER,
        attempts INTEGER DEFAULT 0,
        completion_date TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        UNIQUE (user_id, game_id)
      );
      
      CREATE TABLE IF NOT EXISTS rewards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        game_id TEXT NOT NULL,
        reward_type TEXT NOT NULL,
        reward_data TEXT,
        issue_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        UNIQUE (user_id, game_id)
      );
      
      /* Table for success announcements */
      CREATE TABLE IF NOT EXISTS success_announcements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        game_id TEXT NOT NULL,
        points_earned INTEGER NOT NULL,
        announcement_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        channel_id TEXT NOT NULL,
        message_id TEXT,
        FOREIGN KEY (user_id, game_id) REFERENCES progress (user_id, game_id)
      );
      
      /* Create an index for faster lookups */
      CREATE INDEX IF NOT EXISTS idx_success_announcements_user_game 
      ON success_announcements(user_id, game_id);
    `);
    
    // Check if we need to alter the progress table to add completion_time
    const progressColumns = await db.all("PRAGMA table_info(progress)");
    const hasCompletionDate = progressColumns.some(col => col.name === 'completion_date');
    
    if (!hasCompletionDate) {
      await db.exec(`
        ALTER TABLE progress ADD COLUMN completion_date TIMESTAMP;
      `);
      global.logger.info('Added completion_date column to progress table');
    }
    
    global.logger.info('Database tables created or verified');
    return true;
  } catch (error) {
    global.logger.error(`Database initialization error: ${error.message}`);
    throw error;
  }
}

/**
 * Register a new user or update existing user
 * @param {string} discordId - Discord user ID
 * @param {string} username - Discord username 
 * @param {string} email - User email (optional)
 * @returns {Promise<Object>} Operation result
 */
async function registerUser(discordId, username, email = null) {
  try {
    // Input validation
    if (!discordId || typeof discordId !== 'string') {
      return { success: false, error: 'Invalid Discord ID' };
    }
    
    if (!username || typeof username !== 'string') {
      return { success: false, error: 'Invalid username' };
    }
    
    if (email && typeof email !== 'string') {
      return { success: false, error: 'Invalid email format' };
    }
    
    // Check if user already exists (using parameterized query)
    const user = await db.get('SELECT * FROM users WHERE discord_id = ?', discordId);
    
    if (user) {
      // Update email if provided and user exists
      if (email && user.email !== email) {
        await db.run('UPDATE users SET email = ? WHERE discord_id = ?', [email, discordId]);
        return { success: true, updated: true, userId: user.id };
      }
      return { success: true, exists: true, userId: user.id };
    }
    
    // Insert new user with parameterized query
    const result = await db.run(
      'INSERT INTO users (discord_id, username, email) VALUES (?, ?, ?)',
      [discordId, username, email]
    );
    
    return { success: true, userId: result.lastID };
  } catch (error) {
    global.logger.error(`Error registering user: ${error.message}`);
    // Return a safe error message that doesn't expose internals
    return { success: false, error: 'Database error while registering user' };
  }
}

/**
 * Get user by Discord ID
 * @param {string} discordId - Discord user ID
 * @returns {Promise<Object|null>} User object or null
 */
async function getUser(discordId) {
  try {
    // Input validation
    if (!discordId || typeof discordId !== 'string') {
      return null;
    }
    
    return await db.get('SELECT * FROM users WHERE discord_id = ?', discordId);
  } catch (error) {
    global.logger.error(`Error getting user: ${error.message}`);
    return null;
  }
}

/**
 * Get or initialize game progress for a user
 * @param {number} userId - User ID in database
 * @param {string} gameId - Game ID
 * @returns {Promise<Object|null>} Progress object or null
 */
async function getProgress(userId, gameId) {
  try {
    // Input validation
    if (!userId || !gameId || typeof gameId !== 'string') {
      return null;
    }
    
    const progress = await db.get(
      'SELECT * FROM progress WHERE user_id = ? AND game_id = ?',
      [userId, gameId]
    );
    
    if (!progress) {
      // Initialize progress if it doesn't exist
      await db.run(
        'INSERT INTO progress (user_id, game_id, hints_used, attempts) VALUES (?, ?, 0, 0)',
        [userId, gameId]
      );
      return { hints_used: 0, completed: 0, attempts: 0 };
    }
    
    return progress;
  } catch (error) {
    global.logger.error(`Error getting progress: ${error.message}`);
    return null;
  }
}

/**
 * Update hint usage for a user when they request a hint
 * @param {number} userId - User ID in database
 * @param {string} gameId - Game ID
 * @returns {Promise<Object>} - Result of the operation
 */
async function updateHintUsage(userId, gameId) {
  try {
    // Input validation
    if (!userId || !gameId || typeof gameId !== 'string') {
      return { success: false, error: 'Invalid user or game ID' };
    }
    
    const progress = await getProgress(userId, gameId);
    
    if (!progress) {
      return { success: false, error: 'Progress not found' };
    }
    
    if (progress.completed) {
      return { success: false, error: 'Game already completed' };
    }
    
    await db.run(
      'UPDATE progress SET hints_used = hints_used + 1 WHERE user_id = ? AND game_id = ?',
      [userId, gameId]
    );
    
    return { success: true, hintsUsed: progress.hints_used + 1 };
  } catch (error) {
    global.logger.error(`Error updating hint usage: ${error.message}`);
    return { success: false, error: 'Database error while updating hints' };
  }
}

/**
 * Admin function to manage hint count for a user
 * @param {number} userId - User ID in database
 * @param {string} gameId - Game ID
 * @param {number} action - Action to perform: 1 = add hint, -1 = remove hint, 0 = reset hints
 * @returns {Promise<Object>} - Result of the operation
 */
async function adminManageHints(userId, gameId, action) {
  try {
    // Input validation
    if (!userId || !gameId || typeof gameId !== 'string') {
      return { success: false, error: 'Invalid user or game ID' };
    }
    
    if (action !== 0 && action !== -1 && action !== 1) {
      return { success: false, error: 'Invalid action' };
    }
    
    const progress = await getProgress(userId, gameId);
    
    if (!progress) {
      return { success: false, error: 'Progress not found' };
    }
    
    let newHintCount;
    
    if (action === 0) {
      // Reset hints to zero
      newHintCount = 0;
    } else if (action === -1) {
      // Remove one hint (but not below zero)
      newHintCount = Math.max(0, progress.hints_used - 1);
    } else if (action === 1) {
      // Add one hint
      newHintCount = progress.hints_used + 1;
    } else {
      return { success: false, error: 'Invalid action' };
    }
    
    // Update the hint count
    await db.run(
      'UPDATE progress SET hints_used = ? WHERE user_id = ? AND game_id = ?',
      [newHintCount, userId, gameId]
    );
    
    return { 
      success: true, 
      previousHints: progress.hints_used,
      newHints: newHintCount
    };
  } catch (error) {
    global.logger.error(`Error managing hints: ${error.message}`);
    return { success: false, error: 'Database error while managing hints' };
  }
}

/**
 * Record a submission attempt
 * @param {number} userId - User ID in database
 * @param {string} gameId - Game ID
 * @returns {Promise<Object>} Operation result
 */
async function recordAttempt(userId, gameId) {
  try {
    // Input validation
    if (!userId || !gameId || typeof gameId !== 'string') {
      return { success: false, error: 'Invalid user or game ID' };
    }
    
    await db.run(
      'UPDATE progress SET attempts = attempts + 1 WHERE user_id = ? AND game_id = ?',
      [userId, gameId]
    );
    return { success: true };
  } catch (error) {
    global.logger.error(`Error recording attempt: ${error.message}`);
    return { success: false, error: 'Database error while recording attempt' };
  }
}

/**
 * Mark a game as completed
 * @param {number} userId - User ID in database
 * @param {string} gameId - Game ID
 * @param {number} pointsEarned - Points earned for completion
 * @returns {Promise<Object>} Operation result
 */
async function completeGame(userId, gameId, pointsEarned) {
  try {
    // Input validation
    if (!userId || !gameId || typeof gameId !== 'string') {
      return { success: false, error: 'Invalid user or game ID' };
    }
    
    if (!Number.isInteger(pointsEarned) || pointsEarned < 0) {
      return { success: false, error: 'Invalid points value' };
    }
    
    await db.run(
      `UPDATE progress 
       SET completed = 1, points_earned = ?, completion_date = CURRENT_TIMESTAMP 
       WHERE user_id = ? AND game_id = ?`,
      [pointsEarned, userId, gameId]
    );
    return { success: true };
  } catch (error) {
    global.logger.error(`Error completing game: ${error.message}`);
    return { success: false, error: 'Database error while completing game' };
  }
}

/**
 * Record reward issuance
 * @param {number} userId - User ID in database
 * @param {string} gameId - Game ID
 * @param {string} rewardType - Type of reward (badgr, text)
 * @param {string} rewardData - JSON string of reward data
 * @returns {Promise<Object>} Operation result
 */
async function recordReward(userId, gameId, rewardType, rewardData) {
  try {
    // Input validation
    if (!userId || !gameId || !rewardType) {
      return { success: false, error: 'Missing required parameters' };
    }
    await db.run(
      'INSERT INTO rewards (user_id, game_id, reward_type, reward_data) VALUES (?, ?, ?, ?)',
      [userId, gameId, rewardType, rewardData]
    );
    return { success: true };
  } catch (error) {
    global.logger.error(`Error recording reward: ${error.message}`);
    return { success: false, error: 'Database error while recording reward' };
  }
}

/**
 * Record a success announcement
 * @param {number} userId - User ID in database
 * @param {string} gameId - Game ID
 * @param {number} pointsEarned - Points earned
 * @param {string} channelId - Discord channel ID where announced
 * @param {string} messageId - Discord message ID of announcement
 * @returns {Promise<Object>} Operation result
 */
async function recordSuccessAnnouncement(userId, gameId, pointsEarned, channelId, messageId) {
  try {
    // Input validation
    if (!userId || !gameId || !channelId) {
      return { success: false, error: 'Missing required parameters' };
    }
    
    await db.run(
      'INSERT INTO success_announcements (user_id, game_id, points_earned, channel_id, message_id) VALUES (?, ?, ?, ?, ?)',
      [userId, gameId, pointsEarned, channelId, messageId]
    );
    return { success: true };
  } catch (error) {
    global.logger.error(`Error recording success announcement: ${error.message}`);
    return { success: false, error: 'Database error while recording announcement' };
  }
}

/**
 * Check if user has completed any games
 * @param {number} userId - User ID in database
 * @returns {Promise<boolean>} True if any games completed
 */
async function hasCompletedAnyGames(userId) {
  try {
    if (!userId) return false;
    
    const result = await db.get(
      'SELECT COUNT(*) as count FROM progress WHERE user_id = ? AND completed = 1',
      userId
    );
    return result && result.count > 0;
  } catch (error) {
    global.logger.error(`Error checking if user has completed any games: ${error.message}`);
    return false;
  }
}

/**
 * Check if user has completed all available games
 * @param {number} userId - User ID in database
 * @param {number} totalGamesCount - Total number of available games
 * @returns {Promise<boolean>} True if all games completed
 */
async function hasCompletedAllGames(userId, totalGamesCount) {
  try {
    if (!userId || !Number.isInteger(totalGamesCount)) return false;
    
    const result = await db.get(
      'SELECT COUNT(*) as count FROM progress WHERE user_id = ? AND completed = 1',
      userId
    );
    return result && result.count === totalGamesCount;
  } catch (error) {
    global.logger.error(`Error checking if user has completed all games: ${error.message}`);
    return false;
  }
}

/**
 * Get user statistics summary
 * @param {number} userId - User ID in database
 * @returns {Promise<Object|null>} User stats or null
 */
async function getUserStats(userId) {
  try {
    if (!userId) return null;
    
    const stats = await db.get(
      `SELECT 
        COUNT(CASE WHEN completed = 1 THEN 1 END) as completed_games,
        SUM(points_earned) as total_points,
        COUNT(*) as total_games,
        SUM(hints_used) as total_hints,
        SUM(attempts) as total_attempts
      FROM progress
      WHERE user_id = ?`,
      userId
    );
    
    return stats;
  } catch (error) {
    global.logger.error(`Error getting user stats: ${error.message}`);
    return null;
  }
}

/**
 * Get detailed stats for a specific user, including per-game performance
 * @param {string} discordId - Discord ID of the user
 * @returns {Promise<Object|null>} Detailed user statistics
 */
async function getDetailedUserStats(discordId) {
  try {
    if (!discordId || typeof discordId !== 'string') {
      return null;
    }
    
    // Get user information
    const user = await getUser(discordId);
    if (!user) {
      return null;
    }
    
    // Get overall stats
    const overallStats = await getUserStats(user.id);
    
    // Get per-game progress
    const gameProgress = await db.all(
      `SELECT 
        p.game_id,
        p.completed,
        p.hints_used,
        p.points_earned,
        p.attempts,
        p.completion_date
      FROM progress p
      WHERE p.user_id = ?
      ORDER BY CASE WHEN p.completion_date IS NULL THEN 1 ELSE 0 END, p.completion_date DESC`,
      user.id
    );
    
    // Get last active time
    const lastActive = await db.get(
      `SELECT MAX(completion_date) as last_active_time
       FROM progress
       WHERE user_id = ? AND (attempts > 0 OR hints_used > 0)`,
      user.id
    );
    
    return {
      user,
      overallStats,
      gameProgress,
      lastActive: lastActive ? lastActive.last_active_time : null
    };
  } catch (error) {
    global.logger.error(`Error getting detailed user stats: ${error.message}`);
    return null;
  }
}

/**
 * Get leaderboard data
 * @param {number} limit - Maximum number of entries
 * @returns {Promise<Array>} Leaderboard entries
 */
async function getLeaderboard(limit = 10) {
  try {
    // Input validation
    if (!Number.isInteger(limit) || limit <= 0) {
      limit = 10;
    }
    
    // Sanitize limit parameter to prevent SQL injection
    const sanitizedLimit = Math.min(Math.max(1, limit), 100); // Between 1 and 100
    
    return await db.all(
      `SELECT 
        u.username,
        COUNT(CASE WHEN p.completed = 1 THEN 1 END) as completed_games,
        SUM(p.points_earned) as total_points
      FROM users u
      JOIN progress p ON u.id = p.user_id
      GROUP BY u.id
      ORDER BY total_points DESC, completed_games DESC
      LIMIT ?`,
      sanitizedLimit
    );
  } catch (error) {
    global.logger.error(`Error getting leaderboard: ${error.message}`);
    return [];
  }
}

/**
 * Get detailed leaderboard with individual game completions
 * @param {number} limit - Number of entries to return (defaults to all)
 * @returns {Promise<Array>} - Detailed completion history
 */
async function getDetailedLeaderboard(limit = null) {
  try {
    let query = `
      SELECT 
        u.username,
        p.game_id,
        p.completed,
        p.points_earned,
        p.completion_date
      FROM progress p
      JOIN users u ON p.user_id = u.id
      WHERE p.completed = 1
      ORDER BY p.completion_date DESC
    `;
    
    const params = [];
    
    // Add limit if specified
    if (limit !== null && Number.isInteger(Number(limit)) && Number(limit) > 0) {
      query += ` LIMIT ?`;
      params.push(Math.min(Number(limit), 1000)); // Cap at 1000 for safety
    }
    
    return await db.all(query, params);
  } catch (error) {
    global.logger.error(`Error getting detailed leaderboard: ${error.message}`);
    return [];
  }
}

/**
 * Get statistics for a specific game
 * @param {string} gameId - Game ID
 * @returns {Promise<Object|null>} Game statistics
 */
async function getGameStats(gameId) {
  try {
    if (!gameId || typeof gameId !== 'string') {
      return null;
    }
    
    return await db.get(
      `SELECT 
        COUNT(CASE WHEN completed = 1 THEN 1 END) as completions,
        COUNT(DISTINCT user_id) as players,
        AVG(CASE WHEN completed = 1 THEN hints_used END) as avg_hints,
        AVG(CASE WHEN completed = 1 THEN attempts END) as avg_attempts
      FROM progress
      WHERE game_id = ?`,
      gameId
    );
  } catch (error) {
    global.logger.error(`Error getting game stats: ${error.message}`);
    return null;
  }
}

/**
 * Get statistics for all games
 * @returns {Promise<Array>} Array of game statistics
 */
async function getAllGamesStats() {
  try {
    return await db.all(
      `SELECT 
        game_id,
        COUNT(CASE WHEN completed = 1 THEN 1 END) as completions,
        COUNT(DISTINCT user_id) as players,
        AVG(CASE WHEN completed = 1 THEN hints_used END) as avg_hints,
        AVG(CASE WHEN completed = 1 THEN attempts END) as avg_attempts
      FROM progress
      GROUP BY game_id`
    );
  } catch (error) {
    global.logger.error(`Error getting all games stats: ${error.message}`);
    return [];
  }
}

/**
 * Reset user progress for a game or all games
 * @param {number} userId - User ID in database
 * @param {string} gameId - Game ID (optional, if null reset all games)
 * @returns {Promise<Object>} Operation result
 */
async function resetUserProgress(userId, gameId = null) {
  try {
    // Input validation
    if (!userId) {
      return { success: false, error: 'Invalid user ID' };
    }
    
    // Use a transaction to ensure all operations complete or none do
    await db.run('BEGIN TRANSACTION');
    
    try {
      // First, delete related records from success_announcements
      if (gameId) {
        await db.run(
          'DELETE FROM success_announcements WHERE user_id = ? AND game_id = ?',
          [userId, gameId]
        );
      } else {
        await db.run(
          'DELETE FROM success_announcements WHERE user_id = ?',
          [userId]
        );
      }
      
      // Then, delete related records from rewards
      if (gameId) {
        await db.run(
          'DELETE FROM rewards WHERE user_id = ? AND game_id = ?',
          [userId, gameId]
        );
      } else {
        await db.run(
          'DELETE FROM rewards WHERE user_id = ?',
          [userId]
        );
      }
      
      // Finally, delete progress records
      if (gameId) {
        await db.run(
          'DELETE FROM progress WHERE user_id = ? AND game_id = ?',
          [userId, gameId]
        );
      } else {
        await db.run(
          'DELETE FROM progress WHERE user_id = ?',
          [userId]
        );
      }
      
      // Commit transaction
      await db.run('COMMIT');
      return { success: true };
    } catch (error) {
      // Rollback if any operation fails
      await db.run('ROLLBACK');
      throw error; // Re-throw to be caught by outer try/catch
    }
  } catch (error) {
    global.logger.error(`Error resetting progress: ${error.message}`);
    return { success: false, error: `Database error while resetting progress: ${error.message}` };
  }
}

/**
 * Atomically check that a game is not yet completed and mark it complete.
 * Returns { success: false, alreadyCompleted: true } if the game was already done.
 * This prevents race conditions from double-submissions.
 * @param {number} userId - User ID in database
 * @param {string} gameId - Game ID
 * @param {number} pointsEarned - Points earned for completion
 * @returns {Promise<Object>} Operation result
 */
async function completeGameAtomic(userId, gameId, pointsEarned) {
  try {
    if (!userId || !gameId || typeof gameId !== 'string') {
      return { success: false, error: 'Invalid user or game ID' };
    }
    if (!Number.isInteger(pointsEarned) || pointsEarned < 0) {
      return { success: false, error: 'Invalid points value' };
    }

    await db.run('BEGIN IMMEDIATE');
    try {
      const progress = await db.get(
        'SELECT completed FROM progress WHERE user_id = ? AND game_id = ?',
        [userId, gameId]
      );

      if (progress && progress.completed) {
        await db.run('ROLLBACK');
        return { success: false, alreadyCompleted: true };
      }

      await db.run(
        `UPDATE progress
         SET completed = 1, points_earned = ?, completion_date = CURRENT_TIMESTAMP
         WHERE user_id = ? AND game_id = ?`,
        [pointsEarned, userId, gameId]
      );
      await db.run('COMMIT');
      return { success: true };
    } catch (err) {
      await db.run('ROLLBACK');
      throw err;
    }
  } catch (error) {
    global.logger.error(`Error in completeGameAtomic: ${error.message}`);
    return { success: false, error: 'Database error while completing game' };
  }
}

module.exports = {
  initializeDatabase,
  registerUser,
  getUser,
  getProgress,
  updateHintUsage,
  adminManageHints,
  recordAttempt,
  completeGame,
  completeGameAtomic,
  recordReward,
  recordSuccessAnnouncement,
  hasCompletedAnyGames,
  hasCompletedAllGames,
  getUserStats,
  getDetailedUserStats,
  getLeaderboard,
  getDetailedLeaderboard,
  getGameStats,
  getAllGamesStats,
  resetUserProgress
};
