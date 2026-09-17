const { ensureLogin, request, hydrateImageFields, downloadAndSaveImage, normalizePagePayload } = require('../../utils/request')
const { syncTabBar } = require('../../utils/tabbar')
const { formatDisplayTime } = require('../../utils/date')

const PAGE_SIZE = 8

const DEFAULT_CATEGORY = '未标注'
const ENGLISH_TO_CHINESE_CATEGORY = {
  healthy: '健康叶片',
  brown_spot: '褐斑病',
  leaf_scald: '叶枯病',
  leaf_blast: '稻瘟病',
  bacterial_leaf_blight: '白叶枯病',
  leaf_smut: '叶黑粉病',
  narrow_brown_spot: '窄褐斑病',
  not_leaf: '非叶片'
}

function isAuthError(error) {
  const detail = String(error && error.detail ? error.detail : '')
  const statusCode = Number(error && error.statusCode ? error.statusCode : 0)
  return statusCode === 401 || /请先登录|token|认证|unauthorized|unauthor/i.test(detail)
}

function toChineseCategoryLabel(value) {
  const label = String(value || '').trim()
  if (!label) {
    return DEFAULT_CATEGORY
  }
  const normalized = label.toLowerCase().replace(/-/g, '_').replace(/\s+/g, '_')
  return ENGLISH_TO_CHINESE_CATEGORY[normalized] || label
}

function getPrimaryCategory(record) {
  if (record.primary_category) {
    return toChineseCategoryLabel(record.primary_category)
  }
  const firstResult = Array.isArray(record.results) && record.results.length ? record.results[0] : null
  return toChineseCategoryLabel(firstResult && firstResult.label)
}

function decorateRecord(record) {
  const primaryCategory = getPrimaryCategory(record)
  return {
    ...record,
    primary_category_label: primaryCategory,
    record_title: record.record_code || `${primaryCategory}-${String(Number(record.id) || 0).padStart(6, '0')}`,
    display_created_at: formatDisplayTime(record.created_at)
  }
}

Page({
  data: {
    records: [],
    page: 1,
    totalPages: 1,
    hasNextPage: false,
    hasPreviousPage: false,
    loading: false
  },

  onShow() {
    syncTabBar(this, 'pages/history/history')
    this.loadData()
  },

  onPullDownRefresh() {
    this.loadData().finally(() => {
      wx.stopPullDownRefresh()
    })
  },

  async loadData(page = this.data.page) {
    let targetPage = Math.max(1, Number(page) || 1)
    this.setData({ loading: true })
    try {
      await ensureLogin()
      while (true) {
        const payload = normalizePagePayload(await request({
          url: `/api/detections/?page=${targetPage}&page_size=${PAGE_SIZE}`
        }))
        const totalPages = Math.max(1, Math.ceil(payload.count / PAGE_SIZE))
        if (payload.count > 0 && targetPage > totalPages) {
          targetPage = totalPages
          continue
        }
        this.setData({
          records: payload.results.map(decorateRecord),
          page: targetPage,
          totalPages,
          hasNextPage: payload.hasNext,
          hasPreviousPage: payload.hasPrevious
        })
        break
      }
    } catch (error) {
      if (isAuthError(error)) {
        wx.reLaunch({ url: '/pages/login/login' })
        return
      }
      wx.showToast({ title: error.detail || '历史记录加载失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  previousPage() {
    if (this.data.hasPreviousPage) {
      this.loadData(this.data.page - 1)
    }
  },

  nextPage() {
    if (this.data.hasNextPage) {
      this.loadData(this.data.page + 1)
    }
  },

  async openDetail(event) {
    const { id } = event.currentTarget.dataset
    try {
      const detail = await request({ url: `/api/detections/${id}/` })
      const hydrated = await hydrateImageFields(decorateRecord(detail), [
        { sourceField: 'original_image_url', targetField: 'original_image_local_path' },
        { sourceField: 'visualized_image_url', targetField: 'visualized_image_local_path' }
      ])
      getApp().globalData.detectionDetail = hydrated
      wx.navigateTo({ url: '/pages/result/result' })
    } catch (error) {
      wx.showToast({ title: error.detail || '读取失败', icon: 'none' })
    }
  },

  async saveImage(event) {
    const url = event.currentTarget.dataset.url
    const filename = event.currentTarget.dataset.filename || ''
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
  },

  async deleteRecord(event) {
    const id = Number(event.currentTarget.dataset.id)
    if (!id) {
      wx.showToast({ title: '记录不可用', icon: 'none' })
      return
    }
    const confirmed = await new Promise((resolve) => {
      wx.showModal({
        title: '删除记录',
        content: '确定删除这条检测记录吗？',
        success: (res) => resolve(!!res.confirm),
        fail: () => resolve(false)
      })
    })
    if (!confirmed) {
      return
    }
    wx.showLoading({ title: '删除中...', mask: true })
    try {
      await request({ url: `/api/detections/${id}/`, method: 'DELETE' })
      await this.loadData()
      wx.showToast({ title: '已删除', icon: 'success' })
    } catch (error) {
      wx.showToast({ title: error.detail || '删除失败', icon: 'none' })
    } finally {
      wx.hideLoading()
    }
  }
})
