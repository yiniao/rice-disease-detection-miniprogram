// 部署私有配置：云托管地址、微信云开发环境 ID、云托管服务名。
//
// 这些值因人而异，属于个人部署信息，**不要提交到公开仓库**。
// 本地开发时把真实值写进同目录的 config.local.js（已在 .gitignore 中排除），例如：
//
//   // miniapp/utils/config.local.js
//   module.exports = {
//     DEFAULT_BASE_URL: 'https://<你的云托管服务地址>',
//     CLOUD_ENV: '<你的微信云开发环境ID>',
//     CLOUD_SERVICE: '<你的云托管服务名>'
//   }
//
// config.local.js 不存在时下面的占位值生效，小程序仍可编译，只是请求会失败。
let localConfig = {}
try {
  localConfig = require('./config.local') || {}
} catch (error) {
  localConfig = {}
}

const DEFAULT_BASE_URL = localConfig.DEFAULT_BASE_URL || 'https://your-cloud-run-service.example.com'
const API_BASE_URL_STORAGE_KEY = 'apiBaseUrl'

// 微信云开发环境 ID，在微信开发者工具 / 小程序后台 → 云开发控制台查看
const CLOUD_ENV = localConfig.CLOUD_ENV || ''

// 云托管服务名（wx.cloud.callContainer 的 X-WX-SERVICE 头）
const CLOUD_SERVICE = localConfig.CLOUD_SERVICE || 'your-cloud-service-name'

function normalizeBaseUrl(url) {
  const value = String(url || '').trim().replace(/\/+$/, '')
  return value.replace(/^http:\/\//i, 'https://')
}

function getBaseUrl() {
  if (typeof wx === 'undefined') {
    return DEFAULT_BASE_URL
  }
  const stored = wx.getStorageSync(API_BASE_URL_STORAGE_KEY)
  return normalizeBaseUrl(stored) || DEFAULT_BASE_URL
}

module.exports = {
  DEFAULT_BASE_URL,
  API_BASE_URL_STORAGE_KEY,
  CLOUD_ENV,
  CLOUD_SERVICE,
  getBaseUrl
}
