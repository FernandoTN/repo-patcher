/**
 * Utility functions for data processing
 */
const _ = require('lodash');

// This function uses lodash but doesn't import it - causing ReferenceError
function getUniqueValues(array) {
    return _.uniq(array);
}

function processData(data) {
    return data.map(item => item.value);
}

module.exports = {
    getUniqueValues,
    processData
};