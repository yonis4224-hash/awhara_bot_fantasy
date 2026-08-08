const fs = require('fs');
const path = require('path');

const DATA_FILE = path.join(__dirname, '..', 'data.json');
const LEAGUES_FILE = path.join(__dirname, '..', 'leagues.json');
const MATCHES_FILE = path.join(__dirname, '..', 'matches.json');

function readJSON(filePath, fallback) {
  try {
    if (fs.existsSync(filePath)) {
      return JSON.parse(fs.readFileSync(filePath, 'utf8'));
    }
  } catch (e) { /* ignore */ }
  return fallback;
}

function writeJSON(filePath, data) {
  fs.writeFileSync(filePath, JSON.stringify(data, null, 2), 'utf8');
}

function getStore() {
  return readJSON(DATA_FILE, { coaches: {}, marketListings: [] });
}

function saveStore(store) {
  writeJSON(DATA_FILE, store);
}

function getLeagues() {
  return readJSON(LEAGUES_FILE, { leagues: [] });
}

function saveLeagues(data) {
  writeJSON(LEAGUES_FILE, data);
}

function getMatchesStore() {
  return readJSON(MATCHES_FILE, { matches: [] });
}

function saveMatchesStore(data) {
  writeJSON(MATCHES_FILE, data);
}

module.exports = { getStore, saveStore, getLeagues, saveLeagues, getMatchesStore, saveMatchesStore };
