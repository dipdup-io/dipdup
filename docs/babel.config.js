module.exports = {
    presets: [
      [
        '@babel/preset-env',
        {
          modules: false,
          useBuiltIns: 'entry',
          corejs: 3
          // forceAllTransforms: true
        }
      ],
      '@babel/preset-react'
    ],
    plugins: [
      '@babel/plugin-syntax-dynamic-import',
      '@babel/plugin-proposal-class-properties',
      'babel-plugin-transform-class-properties',
      'babel-plugin-syntax-async-functions',
      'babel-plugin-transform-regenerator'
    ]
  };