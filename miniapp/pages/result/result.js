const { ensureLogin, hydrateImageFields, downloadAndSaveImage } = require('../../utils/request')

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

function formatDetailForView(detail) {
  if (!detail) return detail
  const formatted = { ...detail }
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
    detail: null,
    saving: false
  },

  async onShow() {
    try {
      await ensureLogin()
      const detail = getApp().globalData.detectionDetail
      if (!detail) {
        this.setData({ detail: null })
        return
      }
      const hydrated = await hydrateImageFields(detail, [
        { sourceField: 'original_image_url', targetField: 'original_image_local_path' },
        { sourceField: 'visualized_image_url', targetField: 'visualized_image_local_path' }
      ])
      this.setData({ detail: formatDetailForView(hydrated) })
    } catch (error) {
      wx.reLaunch({ url: '/pages/login/login' })
    }
  },

  async saveImage(event) {
    const url = event.currentTarget.dataset.url
    const filename = event.currentTarget.dataset.filename || ''
    if (!url) {
      wx.showToast({ title: '图片不可用', icon: 'none' })
      return
    }
    this.setData({ saving: true })
    wx.showLoading({ title: '保存中...', mask: true })
    try {
      await downloadAndSaveImage(url, filename)
      wx.showToast({ title: '已保存到相册', icon: 'success' })
    } catch (error) {
      wx.showToast({ title: error.detail || '保存失败', icon: 'none' })
    } finally {
      wx.hideLoading()
      this.setData({ saving: false })
    }
  }
})
