/**
 * @file logger.js - Application Logging Service
 * @description Centralized logging system using Winston for comprehensive application monitoring.
 *              Provides configurable log levels, file and console output, timestamp formatting,
 *              and color-coded console messages. Ensures proper log directory creation and supports
 *              both development and production logging requirements.
 * @version 1.1.0
 * @author gl0bal01
 * @since 2025-04-03
 */
const fs = require('fs');
const path = require('path');
const { createLogger, format, transports } = require('winston');
const { combine, timestamp, printf, colorize } = format;

class Logger {
  constructor(level = 'info', logFile = 'scorebot.log') {
    // Ensure the logs directory exists
    const logDir = path.join(__dirname, '../logs');
    if (!fs.existsSync(logDir)) {
      fs.mkdirSync(logDir, { recursive: true });
    }

    const logFilePath = path.join(logDir, logFile);

    // Custom format
    const customFormat = printf(({ level, message, timestamp }) => {
      return `[${timestamp}] ${level}: ${message}`;
    });

    // Initialize Winston logger
    this.logger = createLogger({
      level: level.toLowerCase(),
      format: combine(
        timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
        customFormat
      ),
      transports: [
        // Console output with colors
        new transports.Console({
          format: combine(
            colorize(),
            timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
            customFormat
          )
        }),
        // File output with rotation
        new transports.File({
          filename: logFilePath,
          maxsize: 5242880, // 5MB per file
          maxFiles: 5,      // Keep 5 rotated files
          tailable: true
        })
      ]
    });

    this.info(`Logger initialized with level ${level}`);
  }

  info(message) {
    this.logger.info(message);
  }

  warn(message) {
    this.logger.warn(message);
  }

  error(message) {
    this.logger.error(message);
  }

  debug(message) {
    this.logger.debug(message);
  }
}

module.exports = Logger;
