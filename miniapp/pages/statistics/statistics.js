const { getBaseUrl, ensureLogin, request } = require('../../utils/request')
const { syncTabBar } = require('../../utils/tabbar')

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

function toChineseCategoryLabel(value) {
  const label = String(value || '').trim()
  if (!label) {
    return '未标注'
  }
  const normalized = label.toLowerCase().replace(/-/g, '_').replace(/\s+/g, '_')
  return ENGLISH_TO_CHINESE_CATEGORY[normalized] || label
}

function asOptionList(items, valueKey = 'value', labelKey = 'label') {
  return (items || []).map((item) => {
    if (typeof item === 'string') {
      return { value: item, label: toChineseCategoryLabel(item) }
    }
    return {
      value: item[valueKey],
      label: labelKey === 'label'
        ? toChineseCategoryLabel(item[labelKey])
        : item[labelKey]
    }
  })
}

function pickIndex(options, value) {
  const target = value === undefined || value === null ? '' : String(value)
  const index = options.findIndex((item) => String(item.value) === target)
  return index >= 0 ? index : 0
}

function buildQuery(filters) {
  const parts = []
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== '' && value !== null && value !== undefined) {
      parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
    }
  })
  return parts.join('&')
}

function formatLocalDate(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function calcBarWidth(total, max) {
  const value = Number(total) || 0
  const peak = Number(max) || 0
  if (value <= 0 || peak <= 0) {
    return '0%'
  }
  return `${Math.max(1, Math.round((value / peak) * 100))}%`
}

function calcTimelineHeight(total, max) {
  const value = Number(total) || 0
  const peak = Number(max) || 0
  if (value <= 0 || peak <= 0) {
    return 0
  }
  return Math.max(28, Math.round((value / peak) * 220) + 20)
}

Page({
  data: {
    loading: false,
    error: '',
    isAdmin: false,
    user: {},
    start_date: '',
    end_date: '',
    category: '',
    status: '',
    model: '',
    user_id: '',
    granularity: 'auto',
    categoryOptions: [],
    statusOptions: [],
    modelOptions: [],
    userOptions: [],
    granularityOptions: [
      { value: 'auto', label: '自动' },
      { value: 'day', label: '按天' },
      { value: 'week', label: '按周' },
      { value: 'month', label: '按月' }
    ],
    selectedCategoryIndex: 0,
    selectedStatusIndex: 0,
    selectedModelIndex: 0,
    selectedUserIndex: 0,
    selectedGranularityIndex: 0,
    selectedCategoryLabel: '全部类别',
    selectedStatusLabel: '全部状态',
    selectedModelLabel: '全部模型',
    selectedUserLabel: '全部用户',
    selectedGranularityLabel: '自动',
    summaryCards: [],
    timelineRows: [],
    categoryRows: [],
    statusRows: [],
    modelRows: [],
    userRows: [],
    confidenceRows: [],
    hasUserFilter: false
  },

  onShow() {
    syncTabBar(this, 'pages/statistics/statistics')
    this.loadStatistics()
  },

  getFilters() {
    return {
      start_date: this.data.start_date,
      end_date: this.data.end_date,
      category: this.data.category,
      status: this.data.status,
      model: this.data.model,
      user_id: this.data.isAdmin ? this.data.user_id : '',
      granularity: this.data.granularity
    }
  },

  applyPayload(payload) {
    const { filters, summary, charts } = payload
    const categoryOptions = [{ value: '', label: '全部类别' }, ...asOptionList(filters.options.categories, 'value', 'label')]
    const statusOptions = [{ value: '', label: '全部状态' }, ...asOptionList(filters.options.statuses, 'value', 'label')]
    const modelOptions = [{ value: '', label: '全部模型' }, ...asOptionList(filters.options.models)]
    const userOptions = [{ value: '', label: '全部用户' }, ...asOptionList(filters.options.users, 'id', 'username')]
    const granularityOptions = [{ value: 'auto', label: '自动' }, ...asOptionList(filters.options.granularities, 'value', 'label')]

    const currentFilters = filters.selected || {}
    const categoryIndex = pickIndex(categoryOptions, currentFilters.category)
    const statusIndex = pickIndex(statusOptions, currentFilters.status)
    const modelIndex = pickIndex(modelOptions, currentFilters.model)
    const userIndex = pickIndex(userOptions, currentFilters.user_id)
    const granularityIndex = pickIndex(granularityOptions, currentFilters.granularity || 'auto')

    const maxTimeline = Math.max(...charts.timeline.map((item) => item.total), 0)
    const maxCategory = Math.max(...charts.categories.map((item) => item.total), 0)
    const maxModel = Math.max(...charts.model_distribution.map((item) => item.total), 0)
    const maxUser = Math.max(...charts.user_distribution.map((item) => item.total), 0)
    const maxConfidence = Math.max(...charts.confidence_distribution.map((item) => item.total), 0)

    this.setData({
      user: getApp().globalData.user || {},
      isAdmin: !!filters.options.can_select_user,
      hasUserFilter: !!filters.options.can_select_user,
      start_date: currentFilters.start_date || '',
      end_date: currentFilters.end_date || '',
      category: currentFilters.category || '',
      status: currentFilters.status || '',
      model: currentFilters.model || '',
      user_id: currentFilters.user_id || '',
      granularity: currentFilters.granularity || 'auto',
      categoryOptions,
      statusOptions,
      modelOptions,
      userOptions,
      granularityOptions,
      selectedCategoryIndex: categoryIndex,
      selectedStatusIndex: statusIndex,
      selectedModelIndex: modelIndex,
      selectedUserIndex: userIndex,
      selectedGranularityIndex: granularityIndex,
      selectedCategoryLabel: categoryOptions[categoryIndex].label,
      selectedStatusLabel: statusOptions[statusIndex].label,
      selectedModelLabel: modelOptions[modelIndex].label,
      selectedUserLabel: userOptions[userIndex].label,
      selectedGranularityLabel: granularityOptions[granularityIndex].label,
      summaryCards: [
        { label: '检测记录总数', value: summary.total_records, note: '当前筛选范围内' },
        { label: '成功率', value: `${summary.success_rate}%`, note: `失败 ${summary.failed_records} 条` },
        { label: '检测框总数', value: summary.total_results, note: '所有目标框' },
        { label: '平均耗时', value: `${summary.avg_duration_ms} ms`, note: '单次检测平均值' },
        { label: '平均置信度', value: `${summary.avg_confidence}%`, note: '越高越稳定' },
        { label: '单图均框数', value: summary.avg_results_per_image, note: '每张图平均框数' },
        { label: '涉及用户数', value: summary.unique_users, note: '查询范围内账号' },
        { label: '涉及类别数', value: summary.unique_categories, note: '病虫害标签' }
      ],
      timelineRows: charts.timeline.map((item) => ({
        ...item,
        barHeight: calcTimelineHeight(item.total, maxTimeline)
      })),
      categoryRows: charts.categories.map((item) => ({
        ...item,
        label: toChineseCategoryLabel(item.label),
        barWidth: calcBarWidth(item.total, maxCategory)
      })),
      statusRows: charts.status_distribution.map((item) => ({
        ...item,
        barWidth: calcBarWidth(item.total, summary.total_records)
      })),
      modelRows: charts.model_distribution.map((item) => ({
        ...item,
        barWidth: calcBarWidth(item.total, maxModel)
      })),
      userRows: charts.user_distribution.map((item) => ({
        ...item,
        barWidth: calcBarWidth(item.total, maxUser)
      })),
      confidenceRows: charts.confidence_distribution.map((item) => ({
        ...item,
        barWidth: calcBarWidth(item.total, maxConfidence)
      }))
    })
  },

  async loadStatistics() {
    const filters = this.getFilters()
    this.setData({ loading: true, error: '' })
    wx.showLoading({ title: '加载统计中...', mask: true })
    try {
      await ensureLogin()
      const query = buildQuery({ ...filters, include_recent: 0 })
      const payload = await request({
        url: `/api/statistics/?${query}`
      })
      this.applyPayload(payload)
    } catch (error) {
      if (error.detail === '请先登录') {
        wx.reLaunch({ url: '/pages/login/login' })
        return
      }
      this.setData({ error: error.detail || '统计数据加载失败' })
    } finally {
      wx.hideLoading()
      this.setData({ loading: false })
    }
  },

  onStartDateChange(event) {
    this.setData({ start_date: event.detail.value })
  },

  onEndDateChange(event) {
    this.setData({ end_date: event.detail.value })
  },

  onCategoryChange(event) {
    const index = Number(event.detail.value)
    const option = this.data.categoryOptions[index]
    this.setData({
      selectedCategoryIndex: index,
      category: option ? option.value : '',
      selectedCategoryLabel: option ? option.label : '全部类别'
    })
  },

  onStatusChange(event) {
    const index = Number(event.detail.value)
    const option = this.data.statusOptions[index]
    this.setData({
      selectedStatusIndex: index,
      status: option ? option.value : '',
      selectedStatusLabel: option ? option.label : '全部状态'
    })
  },

  onModelChange(event) {
    const index = Number(event.detail.value)
    const option = this.data.modelOptions[index]
    this.setData({
      selectedModelIndex: index,
      model: option ? option.value : '',
      selectedModelLabel: option ? option.label : '全部模型'
    })
  },

  onUserChange(event) {
    const index = Number(event.detail.value)
    const option = this.data.userOptions[index]
    this.setData({
      selectedUserIndex: index,
      user_id: option ? option.value : '',
      selectedUserLabel: option ? option.label : '全部用户'
    })
  },

  onGranularityChange(event) {
    const index = Number(event.detail.value)
    const option = this.data.granularityOptions[index]
    this.setData({
      selectedGranularityIndex: index,
      granularity: option ? option.value : 'auto',
      selectedGranularityLabel: option ? option.label : '自动'
    })
  },

  setQuickRange(event) {
    const days = Number(event.currentTarget.dataset.days)
    const end = new Date()
    const start = new Date()
    start.setDate(end.getDate() - days + 1)
    const start_date = formatLocalDate(start)
    const end_date = formatLocalDate(end)
    this.setData({ start_date, end_date })
  },

  resetFilters() {
    this.setData({
      start_date: '',
      end_date: '',
      category: '',
      status: '',
      model: '',
      user_id: this.data.isAdmin ? '' : this.data.user_id,
      granularity: 'auto',
      selectedCategoryIndex: 0,
      selectedStatusIndex: 0,
      selectedModelIndex: 0,
      selectedUserIndex: 0,
      selectedGranularityIndex: 0,
      selectedCategoryLabel: '全部类别',
      selectedStatusLabel: '全部状态',
      selectedModelLabel: '全部模型',
      selectedUserLabel: '全部用户',
      selectedGranularityLabel: '自动'
    })
    this.loadStatistics()
  },

  applyFilters() {
    this.loadStatistics()
  },

  exportReport() {
    const query = buildQuery(this.getFilters())
    const token = wx.getStorageSync('token') || ''
    wx.showLoading({ title: '导出中...', mask: true })
    wx.downloadFile({
      url: `${getBaseUrl()}/api/statistics/export/${query ? `?${query}` : ''}`,
      header: token ? { Authorization: `Token ${token}` } : {},
      success: (res) => {
        wx.hideLoading()
        if (res.statusCode !== 200) {
          wx.showToast({ title: '导出失败', icon: 'none' })
          return
        }
        wx.openDocument({
          filePath: res.tempFilePath,
          fileType: 'xlsx',
          showMenu: true,
          success: () => wx.showToast({ title: '已打开报表', icon: 'success' }),
          fail: () => wx.showToast({ title: '文件已下载', icon: 'none' })
        })
      },
      fail: () => {
        wx.hideLoading()
        wx.showToast({ title: '导出失败', icon: 'none' })
      }
    })
  }
})
