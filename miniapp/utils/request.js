const { DEFAULT_BASE_URL, getBaseUrl, CLOUD_ENV, CLOUD_SERVICE } = require('./config')

const DATA_URL_RE = /^data:([^;]+);base64,(.+)$/i
const LOCAL_FILE_RE = /^(wxfile:\/\/|file:\/\/|[A-Za-z]:[\\/])/i
const INVALID_FILE_CHARS_RE = /[<>:"/\\|?*\u0000-\u001F]/g

function buildUrl(url) {
  if (/^https?:\/\//.test(url)) {
    return url
  }
  return `${getBaseUrl()}${url}`
}

function extractObjectMessage(error) {
  if (!error || typeof error !== 'object') {
    return ''
  }
  const priorityKeys = ['detail', 'non_field_errors', 'username', 'password', 'nickname', 'old_password', 'new_password', 'confirm_password']
  const keys = [...priorityKeys, ...Object.keys(error)]
  const visited = new Set()

  for (const key of keys) {
    if (visited.has(key) || !(key in error)) {
      continue
    }
    visited.add(key)
    const value = error[key]
    if (Array.isArray(value) && value.length) {
      return String(value[0])
    }
    if (value && typeof value === 'object') {
      const nested = extractObjectMessage(value)
      if (nested) {
        return nested
      }
    }
    if (typeof value === 'string' && value.trim()) {
      return value.trim()
    }
  }
  return ''
}

function normalizeError(error, fallbackDetail = '请求失败') {
  if (!error) {
    return { detail: fallbackDetail }
  }
  if (error.detail) {
    const detail = String(error.detail)
    if (/<\/?[a-z][\s\S]*>/i.test(detail) || /<!DOCTYPE html>/i.test(detail) || detail.length > 200) {
      return { ...error, detail: fallbackDetail }
    }
    return error
  }
  if (typeof error === 'string') {
    if (/<\/?[a-z][\s\S]*>/i.test(error) || /<!DOCTYPE html>/i.test(error) || error.length > 200) {
      return { detail: fallbackDetail }
    }
    return { detail: error }
  }
  if (error.errMsg) {
    return { ...error, detail: error.errMsg }
  }
  if (error.message) {
    return { ...error, detail: error.message }
  }
  const objectMessage = extractObjectMessage(error)
  return { ...error, detail: objectMessage || fallbackDetail }
}

function normalizePagePayload(payload) {
  if (Array.isArray(payload)) {
    return {
      results: payload,
      count: payload.length,
      hasNext: false,
      hasPrevious: false
    }
  }
  return {
    results: Array.isArray(payload && payload.results) ? payload.results : [],
    count: Number(payload && payload.count) || 0,
    hasNext: !!(payload && payload.next),
    hasPrevious: !!(payload && payload.previous)
  }
}

function getToken() {
  return wx.getStorageSync('token') || ''
}

function getAuthHeader() {
  const token = getToken()
  return token ? { Authorization: `Token ${token}` } : {}
}

function getStoredUser() {
  return wx.getStorageSync('user') || null
}

function setSession(payload) {
  wx.setStorageSync('token', payload.token)
  wx.setStorageSync('user', payload.user)
  const app = getApp()
  app.globalData.token = payload.token
  app.globalData.user = payload.user
}

function isDataUrl(value) {
  return typeof value === 'string' && DATA_URL_RE.test(value.trim())
}

function parseDataUrl(value) {
  const match = String(value || '').trim().match(DATA_URL_RE)
  if (!match) {
    return null
  }
  return {
    mimeType: match[1] || 'image/jpeg',
    base64: match[2] || ''
  }
}

function isLocalFilePath(value) {
  return typeof value === 'string' && LOCAL_FILE_RE.test(value.trim())
}

function getFileExtension(filePath) {
  const normalized = String(filePath || '').split('?')[0]
  const parts = normalized.split('.')
  return parts.length > 1 ? parts.pop().toLowerCase() : 'jpg'
}

function sanitizeFilename(name, fallback = 'image.jpg') {
  const raw = String(name || '').trim().replace(/\\/g, '/')
  const base = raw.split('/').pop() || fallback
  const cleaned = base.replace(INVALID_FILE_CHARS_RE, '').replace(/^\.+|\.+$/g, '') || fallback
  if (cleaned.includes('.')) {
    return cleaned
  }
  const ext = getFileExtension(fallback)
  return `${cleaned}.${ext || 'jpg'}`
}

function extensionFromMimeType(mimeType = 'image/jpeg') {
  const subtype = String(mimeType || '').split('/')[1] || 'jpg'
  return subtype === 'jpeg' ? 'jpg' : subtype
}

function buildNamedTempFilePath(fileName, mimeType = 'image/jpeg') {
  const extension = getFileExtension(fileName) || extensionFromMimeType(mimeType) || 'jpg'
  const uniqueName = `temp-${Date.now()}-${Math.random().toString(36).slice(2, 8)}.${extension}`
  return `${wx.env.USER_DATA_PATH}/${uniqueName}`
}

function buildHydratedImageFileName(item, targetField) {
  const prefix = sanitizeFilename(
    item && (item.record_code || item.id || item.pk || 'image'),
    'image'
  ).replace(/\.[^.]+$/, '')
  return `${prefix}-${targetField}.jpg`
}

function uploadToCloud(filePath) {
  return new Promise((resolve, reject) => {
    const extension = getFileExtension(filePath)
    const cloudPath = `detections/${Date.now()}-${Math.random().toString(36).slice(2, 8)}.${extension}`
    wx.cloud.uploadFile({
      cloudPath,
      filePath,
      config: { env: CLOUD_ENV || undefined },
      success: (res) => resolve(res.fileID),
      fail: (error) => reject(error)
    })
  })
}

function getTempFileUrl(fileID) {
  return new Promise((resolve, reject) => {
    wx.cloud.getTempFileURL({
      fileList: [fileID],
      success: (res) => {
        const item = res.fileList && res.fileList[0]
        if (item && item.tempFileURL) {
          resolve(item.tempFileURL)
          return
        }
        reject({ detail: '获取图片临时链接失败' })
      },
      fail: (error) => reject(error)
    })
  })
}

function writeBase64ToTempFile(base64, mimeType = 'image/jpeg', fileName = '') {
  return new Promise((resolve, reject) => {
    const fs = wx.getFileSystemManager()
    const tempFilePath = buildNamedTempFilePath(fileName, mimeType)
    const normalizedBase64 = String(base64 || '').replace(/\s/g, '')
    const arrayBuffer = typeof wx.base64ToArrayBuffer === 'function'
      ? wx.base64ToArrayBuffer(normalizedBase64)
      : null
    fs.writeFile({
      filePath: tempFilePath,
      data: arrayBuffer || normalizedBase64,
      ...(arrayBuffer ? {} : { encoding: 'base64' }),
      success: () => resolve(tempFilePath),
      fail: (error) => reject(error)
    })
  })
}

function request({ url, method = 'GET', data = null, header = {} }) {
  return new Promise((resolve, reject) => {
    wx.cloud.callContainer({
      config: { env: CLOUD_ENV || undefined },
      path: url,
      method,
      data,
      header: {
        'X-WX-SERVICE': CLOUD_SERVICE,
        ...getAuthHeader(),
        ...header
      },
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
          return
        }
        const payload = res.data && typeof res.data === 'object'
          ? { ...res.data, statusCode: res.statusCode }
          : { detail: typeof res.data === 'string' ? res.data : `请求失败(${res.statusCode})`, statusCode: res.statusCode }
        reject(normalizeError(payload, `请求失败(${res.statusCode})`))
      },
      fail: (error) => reject(normalizeError(error, '网络请求失败'))
    })
  })
}

function deleteCloudFile(fileID) {
  if (!fileID) {
    return Promise.resolve()
  }
  return new Promise((resolve) => {
    wx.cloud.deleteFile({
      fileList: [fileID],
      success: () => resolve(),
      fail: () => resolve()
    })
  })
}

function uploadFile({ url, filePath, name = 'image', formData = {} }) {
  let uploadedFileID = ''
  return uploadToCloud(filePath)
    .then((fileID) => {
      uploadedFileID = fileID
      return getTempFileUrl(fileID)
    })
    .then((tempFileURL) => request({
      url,
      method: 'POST',
      data: {
        ...formData,
        [name]: tempFileURL
      }
    }))
    .catch((error) => Promise.reject(normalizeError(error, '上传失败')))
    .finally(() => deleteCloudFile(uploadedFileID))
}

function copyLocalFileToTemp(filePath, fileName = '') {
  if (!fileName) {
    return Promise.resolve(filePath)
  }
  const targetPath = buildNamedTempFilePath(fileName)
  if (String(filePath) === targetPath) {
    return Promise.resolve(filePath)
  }
  return new Promise((resolve, reject) => {
    wx.getFileSystemManager().copyFile({
      srcPath: filePath,
      destPath: targetPath,
      success: () => resolve(targetPath),
      fail: (error) => reject(error)
    })
  })
}

function isContainerImagePath(url) {
  return /^\/api\/detections\/\d+\/(?:original-image|visualized-image)\/?(?:\?.*)?$/i.test(String(url || '').trim())
}

async function downloadContainerImage(url, fileName = '') {
  const separator = String(url).includes('?') ? '&' : '?'
  const payload = await request({
    url: `${url}${separator}image_response=data`
  })
  const dataUrl = payload && payload.data_url
  const parsed = parseDataUrl(dataUrl)
  if (!parsed) {
    throw { detail: '图片下载失败' }
  }
  return writeBase64ToTempFile(parsed.base64, parsed.mimeType, fileName)
}

function downloadFile({ url, header = {}, filePath = '', fileName = '' }) {
  if (isDataUrl(url)) {
    const parsed = parseDataUrl(url)
    if (!parsed) {
      return Promise.reject({ detail: '图片下载失败' })
    }
    return writeBase64ToTempFile(parsed.base64, parsed.mimeType, fileName)
  }
  if (isLocalFilePath(url)) {
    return copyLocalFileToTemp(url, fileName)
  }
  if (isContainerImagePath(url)) {
    return downloadContainerImage(url, fileName)
  }
  return new Promise((resolve, reject) => {
    wx.downloadFile({
      url: buildUrl(url),
      timeout: 15000,
      header: {
        'X-WX-SERVICE': CLOUD_SERVICE,
        ...getAuthHeader(),
        ...header
      },
      filePath: filePath || (fileName ? buildNamedTempFilePath(fileName) : ''),
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.tempFilePath)
          return
        }
        reject({ detail: '图片下载失败', statusCode: res.statusCode })
      },
      fail: (error) => reject(normalizeError(error, '图片下载失败'))
    })
  })
}

function saveImageToAlbum(filePath) {
  return new Promise((resolve, reject) => {
    const ensurePermission = () => {
      wx.getSetting({
        success: (setting) => {
          if (setting.authSetting['scope.writePhotosAlbum']) {
            wx.saveImageToPhotosAlbum({
              filePath,
              success: resolve,
              fail: reject
            })
            return
          }
          wx.authorize({
            scope: 'scope.writePhotosAlbum',
            success: () => {
              wx.saveImageToPhotosAlbum({
                filePath,
                success: resolve,
                fail: reject
              })
            },
            fail: reject
          })
        },
        fail: reject
      })
    }
    ensurePermission()
  })
}

async function downloadAndSaveImage(url, fileName = '') {
  if (isLocalFilePath(url)) {
    try {
      await saveImageToAlbum(url)
      return url
    } catch (directSaveError) {
      const tempFilePath = await copyLocalFileToTemp(url, fileName)
      await saveImageToAlbum(tempFilePath)
      return tempFilePath
    }
  }
  const tempFilePath = await downloadFile({ url, fileName })
  await saveImageToAlbum(tempFilePath)
  return tempFilePath
}

async function hydrateImageField(item, sourceField, targetField) {
  if (!item || !item[sourceField]) {
    return item
  }
  if (isLocalFilePath(item[targetField])) {
    return item
  }
  try {
    item[targetField] = await downloadFile({
      url: item[sourceField],
      fileName: buildHydratedImageFileName(item, targetField)
    })
  } catch (error) {
    item[targetField] = ''
  }
  return item
}

async function hydrateImageFields(item, mappings) {
  if (!item) {
    return item
  }
  for (const mapping of mappings) {
    await hydrateImageField(item, mapping.sourceField, mapping.targetField)
  }
  return item
}

function ensureLogin() {
  const app = getApp()
  if (app.globalData.token) {
    return Promise.resolve(app.globalData.token)
  }
  const token = getToken()
  if (token) {
    app.globalData.token = token
    app.globalData.user = getStoredUser()
    return Promise.resolve(token)
  }
  return Promise.reject({ detail: '请先登录' })
}

async function login(username, password) {
  const payload = await request({
    url: '/api/auth/login/',
    method: 'POST',
    data: { username, password }
  })
  if (!payload || !payload.token || !payload.user) {
    throw { detail: '登录接口返回异常，请检查云端是否已部署 Django 后端' }
  }
  setSession(payload)
  return payload
}

async function register({ username, password, nickname = '', avatar_url = '' }) {
  const payload = await request({
    url: '/api/auth/register/',
    method: 'POST',
    data: { username, password, nickname, avatar_url }
  })
  if (!payload || !payload.token || !payload.user) {
    throw { detail: '注册接口返回异常，请检查云端是否已部署 Django 后端' }
  }
  setSession(payload)
  return payload
}

async function getMe() {
  return request({
    url: '/api/auth/me/'
  })
}

async function updateMe(payload) {
  const user = await request({
    url: '/api/auth/me/',
    method: 'PATCH',
    data: payload
  })
  wx.setStorageSync('user', user)
  const app = getApp()
  app.globalData.user = user
  return user
}

function logout() {
  wx.removeStorageSync('token')
  wx.removeStorageSync('user')
  const app = getApp()
  app.globalData.token = ''
  app.globalData.user = null
}

module.exports = {
  BASE_URL: DEFAULT_BASE_URL,
  getBaseUrl,
  buildUrl,
  normalizeError,
  normalizePagePayload,
  request,
  uploadFile,
  downloadFile,
  saveImageToAlbum,
  downloadAndSaveImage,
  hydrateImageField,
  hydrateImageFields,
  ensureLogin,
  login,
  register,
  getMe,
  updateMe,
  logout
}
