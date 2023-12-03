const path = require('path');
const TsconfigPathsPlugin = require('tsconfig-paths-webpack-plugin');
const HtmlWebpackPlugin = require('html-webpack-plugin');
const ForkTsCheckerWebpackPlugin = require('fork-ts-checker-webpack-plugin');
const ReactRefreshWebpackPlugin = require('@pmmmwh/react-refresh-webpack-plugin');
const BundleAnalyzerPlugin = require('webpack-bundle-analyzer');
const CompressionPlugin = require('compression-webpack-plugin');
const BundleTrackerPlugin = require('webpack-bundle-tracker');

module.exports = (env) => {
  const isEnvDevelopment = env.development;
  const isEnvProduction = env.production;
  const exclude = /node_modules/;

  return {
    entry: {
      main: path.resolve(__dirname, 'frontend/static/frontend', 'index.tsx'),
    },
    devtool: isEnvDevelopment ? 'eval' : false,
    mode: isEnvProduction
      ? 'production'
      : isEnvDevelopment
      ? 'development'
      : 'none',
    output: {
      path: path.resolve(__dirname, 'dist'),
      publicPath: isEnvProduction
        ? 'https://secleadevstorage.blob.core.windows.net/portal-dev/'
        : '/',
      filename: 'main.[contenthash].js',
      chunkFilename: '[name].[contenthash].chunk.js',
      hashDigestLength: 8,
    },
    resolve: {
      // Enables absolute paths from tsconfig.json without add alias entries on webpack.config.js
      plugins: [new TsconfigPathsPlugin()],
      extensions: ['.ts', '.tsx', '.js', '.jsx', '.json'],
    },
    module: {
      rules: [
        {
          test: /\.(js|jsx)$/,
          loader: 'babel-loader',
          exclude,
        },
        {
          test: /\.(ts|tsx)$/,
          loader: 'ts-loader',
          exclude,
        },
        {
          test: /\.css$/i,
          use: ['style-loader', 'css-loader'],
        },
        {
          test: /\.scss$/,
          use: ['sass-loader'],
        },
        {
          test: /\.svg$/,
          use: ['@svgr/webpack', 'file-loader'],
        },
        {
          test: /\.(png|jpe?g|gif)$/i,
          use: [
            {
              loader: 'file-loader',
              options: {
                name: '[name].[ext]',
                outputPath: 'media/',
                publicPath: isEnvProduction ? '/static/media' : '',
              },
            },
          ],
        },
      ],
    },
    plugins: [
      // htmlWebpackPlugin create and run the localhost server
      new HtmlWebpackPlugin({
        template: path.join(__dirname, 'frontend/templates', 'index.html'),
      }),
      new BundleTrackerPlugin({ filename: './webpack-stats.json' }),

      //Speeds up TypeScript type checking (by moving it to a separate process)
      new ForkTsCheckerWebpackPlugin(),

      // react-refresh-webpack-plugin prevent page from reloading on changes
      // in stead it just update and render the new page immediately without
      // reload the whole page
      isEnvDevelopment ? new ReactRefreshWebpackPlugin() : false,

      // bundle analyzer create a map visualization of your packages on  http://localhost:8888/
      isEnvDevelopment
        ? new BundleAnalyzerPlugin.BundleAnalyzerPlugin({ openAnalyzer: false })
        : false,

      // Prepare compressed versions of assets to serve them with Content-Encoding
      new CompressionPlugin({ test: /\.(js|ts|tsx)(\?.*)?$/i }),
    ].filter(Boolean),
    optimization: {
      splitChunks: {
        // all node_modules will be splitted into their own vendor chunk
        chunks: 'all',
        filename: '[name].[contenthash].vendor.js',
      },
    },
    devServer: {
      historyApiFallback: true,
      open: true,
      client: {
        // overlay is responsible to show on screen when typescript
        // has an error. we have disable overlay for warnings
        overlay: {
          warnings: false,
          errors: true,
        },
      },
    },
  };
};
