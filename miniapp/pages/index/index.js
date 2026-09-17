const { ensureLogin, uploadFile, hydrateImageFields, downloadAndSaveImage } = require('../../utils/request')
const { syncTabBar } = require('../../utils/tabbar')

const CATEGORY_LABELS = {
  healthy: '健康叶片',
  brown_spot: '褐斑病',
  leaf_scald: '叶枯病',
  leaf_blast: '稻瘟病',
  bacterial_leaf_blight: '白叶枯病',
  leaf_smut: '叶黑粉病',
  narrow_brown_spot: '窄褐斑病',
  not_leaf: '非叶片'
}

function getImageType(name, path, fallback = 'jpg') {
  for (const value of [name, path]) {
    const source = String(value || '').split('?')[0]
    const match = source.match(/\.([a-z0-9]+)$/i)
    if (match) {
      const type = match[1].toLowerCase()
      return type === 'jpeg' ? 'jpg' : type
    }
  }
  return fallback
}

function formatResultForView(result) {
  if (!result) return result
  const formatted = { ...result }
  if (Array.isArray(formatted.results)) {
    formatted.results = formatted.results.map((item) => ({
      ...item,
      label_display: CATEGORY_LABELS[item.label] || '未知类别',
      confidenceText: `${(item.confidence * 100).toFixed(1)}%`
    }))
  }
  return formatted
}

Page({
  data: {
    imagePath: '',
    imageInfo: null,
    loading: false,
    result: null
  },

  onShow() {
    syncTabBar(this, 'pages/index/index')
    ensureLogin().catch((error) => {
      wx.reLaunch({ url: '/pages/login/login' })
    })
  },

  chooseImage() {
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      success: (res) => {
        const file = res.tempFiles[0]
        const tempPath = file.tempFilePath
        const displayName = file.name || file.fileName || tempPath.split('/').pop()
        this.setData({ imagePath: tempPath })
        wx.getImageInfo({
          src: tempPath,
          success: (info) => {
            this.setData({
              imageInfo: {
                name: displayName,
                fileType: getImageType(displayName, tempPath),
                path: tempPath,
                size: file.size || 0,
                sizeKb: ((file.size || 0) / 1024).toFixed(1),
                width: info.width,
                height: info.height
              }
            })
          },
          fail: () => {
            this.setData({
              imageInfo: {
                name: displayName,
                fileType: getImageType(displayName, tempPath),
                path: tempPath,
                size: file.size || 0,
                sizeKb: ((file.size || 0) / 1024).toFixed(1),
                width: 0,
                height: 0
              }
            })
          }
        })
      }
    })
  },

  async submitDetection() {
    if (!this.data.imagePath) {
      wx.showToast({ title: '请先选择图片', icon: 'none' })
      return
    }
    this.setData({ loading: true })
    wx.showLoading({ title: '检测中...', mask: true })
    try {
      await ensureLogin()
      const result = await uploadFile({
        url: '/api/detections/',
        filePath: this.data.imagePath,
        formData: {
          image_name: this.data.imageInfo && this.data.imageInfo.name ? this.data.imageInfo.name : ''
        }
      })
      const hydrated = await hydrateImageFields(result, [
        { sourceField: 'original_image_url', targetField: 'original_image_local_path' },
        { sourceField: 'visualized_image_url', targetField: 'visualized_image_local_path' },
        { sourceField: 'preview_image_url', targetField: 'preview_image_local_path' }
      ])
      const viewResult = formatResultForView(hydrated)
      getApp().globalData.detectionDetail = viewResult
      this.setData({ result: viewResult })
    } catch (error) {
      wx.showToast({ title: error.detail || error.error_message || '检测失败', icon: 'none' })
    } finally {
      wx.hideLoading()
      this.setData({ loading: false })
    }
  },

  async saveImage(event) {
    const kind = event.currentTarget.dataset.kind
    const isOriginal = kind === 'original'
    const url = isOriginal
      ? (this.data.imagePath || (this.data.result && (this.data.result.original_image_local_path || this.data.result.original_image_url)))
      : (this.data.result && (this.data.result.visualized_image_local_path || this.data.result.visualized_image_url))
    const filename = isOriginal
      ? ((this.data.imageInfo && this.data.imageInfo.name) || (this.data.result && this.data.result.original_image_name) || '')
      : ((this.data.result && (this.data.result.visualized_image_name || this.data.result.preview_image_name)) || '')
    if (!url) {
      wx.showToast({ title: '图片不可用', icon: 'none' })
      return
    }
    wx.showLoading({ title: '保存中...', mask: true })
    try {
      await downloadAndSaveImage(url, filename)
      wx.showToast({ title: '已保存到相册', icon: 'success' })
    } catch (error) {
      wx.showToast({ title: error.detail || '保存失败', icon: 'none' })
    } finally {
      wx.hideLoading()
    }
  }
})
