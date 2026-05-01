const path = require('path');

module.exports = {
    entry: './src/js/portfolio.js',
    output: {
        filename: 'bundle.js',
        path: path.resolve(__dirname, 'static/dist'),
    },
    mode: 'production',
};
