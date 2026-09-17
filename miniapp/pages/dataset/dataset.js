const { ensureLogin, request, hydrateImageFields, downloadFile, downloadAndSaveImage, normalizePagePayload } = require('../../utils/request')
const { syncTabBar } = require('../../utils/tabbar')
const { formatDisplayTime } = require('../../utils/date')

const PAGE_SIZE = 8
const FETCH_PAGE_SIZE = 20

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
const STATUS_OPTIONS = [
  { value: 'all', label: '全部状态' },
  { value: 'pending', label: '待归档' },
  { value: 'archived', label: '已归档' }
]

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

function formatRecordCode(categoryLabel, id) {
  return `${toChineseCategoryLabel(categoryLabel)}-${String(Number(id) || 0).padStart(6, '0')}`
}

function normalizeCategoryLabel(value) {
  return toChineseCategoryLabel(value)
}

function getDetectionCategoryOptions(item) {
  if (Array.isArray(item.category_options) && item.category_options.length) {
    return item.category_options.map((label) => normalizeCategoryLabel(label))
  }
  const labels = []
  const seen = new Set()
  ;(item.results || []).forEach((result) => {
    const label = normalizeCategoryLabel(result.label)
    if (!seen.has(label)) {
      seen.add(label)
      labels.push(label)
    }
  })
  return labels.length ? labels : [DEFAULT_CATEGORY]
}

function getDetectionPrimaryCategory(item) {
  return normalizeCategoryLabel(item.primary_category || getDetectionCategoryOptions(item)[0])
}

function buildCategoryOptions(detections, items) {
  const seen = new Set()
  const options = [{ value: '', label: '全部类别' }]

  detections.forEach((item) => {
    getDetectionCategoryOptions(item).forEach((label) => {
      if (!seen.has(label)) {
        seen.add(label)
        options.push({ value: label, label })
      }
    })
    const archivedLabel = normalizeCategoryLabel(item.archived_category_label)
    if (item.archived_category_label && !seen.has(archivedLabel)) {
      seen.add(archivedLabel)
      options.push({ value: archivedLabel, label: archivedLabel })
    }
  })

  items.forEach((item) => {
    const label = normalizeCategoryLabel(item.category_label)
    if (!seen.has(label)) {
      seen.add(label)
      options.push({ value: label, label })
    }
  })

  return options
}

function normalizeDatasetItems(items) {
  return items.map((item) => ({
    ...item,
    record_code: item.record_code || formatRecordCode(item.category_label, item.id),
    source_detection_code: item.source_detection_code || (item.source_detection_id ? formatRecordCode(item.category_label, item.source_detection_id) : ''),
    category_label: normalizeCategoryLabel(item.category_label),
    preview_url: item.image_url || item.source_detection_preview_url || ''
  }))
}

function mergeDetectionsWithItems(detections, items) {
  const itemMap = {}
  items.forEach((item) => {
    if (item.source_detection_id) {
      itemMap[item.source_detection_id] = item
    }
  })

  return detections.map((item) => {
    const datasetItem = itemMap[item.id] || null
    const categoryOptions = getDetectionCategoryOptions(item)
    const primaryCategory = getDetectionPrimaryCategory(item)
    return {
      ...item,
      record_code: item.record_code || formatRecordCode(primaryCategory, item.id),
      category_options: categoryOptions,
      primary_category: primaryCategory,
      is_collected: !!datasetItem,
      dataset_image_id: datasetItem ? datasetItem.id : null,
      dataset_record_code: datasetItem ? datasetItem.record_code : '',
      archived_category_label: datasetItem ? datasetItem.category_label : '',
      collect_button_class: datasetItem ? 'archive-btn--active' : '',
      collect_button_text: datasetItem ? '取消归档' : '归档',
      display_created_at: formatDisplayTime(item.created_at),
      status_class: datasetItem ? 'status-chip--active' : '',
      status_text: datasetItem ? '已归档' : '待归档'
    }
  })
}

Page({
  data: {
    allDetections: [],
    allItems: [],
    detections: [],
    items: [],
    detectionCount: 0,
    itemCount: 0,
    loading: false,
    statusOptions: STATUS_OPTIONS,
    selectedStatusIndex: 0,
    selectedStatusLabel: STATUS_OPTIONS[0].label,
    statusFilter: 'all',
    categoryOptions: [{ value: '', label: '全部类别' }],
    selectedCategoryIndex: 0,
    selectedCategoryLabel: '全部类别',
    categoryFilter: '',
    page: 1,
    totalPages: 1,
    hasNextPage: false,
    hasPreviousPage: false,
    loading: false
  },

  onShow() {
    syncTabBar(this, 'pages/dataset/dataset')
    this.loadData()
  },

  onPullDownRefresh() {
    this.loadData().finally(() => {
      wx.stopPullDownRefresh()
    })
  },

  applyLocalFilters(page = this.data.page) {
    const { allDetections, allItems, statusFilter, categoryFilter } = this.data

    const filteredDetections = allDetections.filter((item) => {
      const matchesStatus = statusFilter === 'all'
        ? true
        : statusFilter === 'archived'
          ? item.is_collected
          : !item.is_collected

      const matchesCategory = !categoryFilter
        || item.primary_category === categoryFilter
        || (item.category_options || []).includes(categoryFilter)
        || item.archived_category_label === categoryFilter

      return matchesStatus && matchesCategory
    })

    const items = (statusFilter === 'pending' ? [] : allItems).filter((item) => {
      return !categoryFilter || item.category_label === categoryFilter
    })

    const totalPages = Math.max(1, Math.ceil(filteredDetections.length / PAGE_SIZE))
    const currentPage = Math.min(Math.max(1, Number(page) || 1), totalPages)
    const start = (currentPage - 1) * PAGE_SIZE

    this.setData({
      detections: filteredDetections.slice(start, start + PAGE_SIZE),
      items,
      page: currentPage,
      totalPages,
      hasNextPage: currentPage < totalPages,
      hasPreviousPage: currentPage > 1
    })
  },

  async loadData(page = this.data.page) {
    let targetPage = Math.max(1, Number(page) || 1)
    this.setData({ loading: true })
    try {
      await ensureLogin()
      const [allDetectionResults, itemCountPayload] = await Promise.all([
        this.loadAllDetections(),
        request({ url: '/api/dataset-images/?page=1&page_size=1' })
      ])
      const itemPage = normalizePagePayload(itemCountPayload)
      const hydratedDetections = allDetectionResults.map((item) => ({
        ...item,
        record_code: item.record_code || formatRecordCode(getDetectionPrimaryCategory(item), item.id),
        primary_category: getDetectionPrimaryCategory(item),
        category_options: getDetectionCategoryOptions(item),
        display_created_at: formatDisplayTime(item.created_at),
        status_class: item.is_collected ? 'status-chip--active' : '',
        status_text: item.is_collected ? '已归档' : '待归档',
        collect_button_text: item.is_collected ? '取消归档' : '归档',
        collect_button_class: item.is_collected ? 'record-action-btn--warning' : 'record-action-btn--primary'
      }))

      const categoryOptions = buildCategoryOptions(hydratedDetections, [])
      const selectedCategoryIndex = categoryOptions.findIndex((option) => option.value === this.data.categoryFilter)
      const safeCategoryIndex = selectedCategoryIndex >= 0 ? selectedCategoryIndex : 0

      this.setData({
        allDetections: hydratedDetections,
        allItems: [],
        detectionCount: hydratedDetections.length,
        itemCount: itemPage.count,
        categoryOptions,
        selectedCategoryIndex: safeCategoryIndex,
        selectedCategoryLabel: categoryOptions[safeCategoryIndex].label,
        categoryFilter: categoryOptions[safeCategoryIndex].value
      }, () => {
        this.applyLocalFilters(targetPage)
      })
    } catch (error) {
      if (isAuthError(error)) {
        wx.reLaunch({ url: '/pages/login/login' })
        return
      }
      wx.showToast({ title: error.detail || '采集数据加载失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  async loadAllDetections() {
    const results = []
    let page = 1

    while (true) {
      const payload = normalizePagePayload(await request({
        url: `/api/detections/?page=${page}&page_size=${FETCH_PAGE_SIZE}`
      }))
      results.push(...payload.results)
      if (!payload.hasNext || !payload.results.length) {
        return results
      }
      page += 1
    }
  },

  previousPage() {
    if (this.data.hasPreviousPage) {
      this.applyLocalFilters(this.data.page - 1)
    }
  },

  nextPage() {
    if (this.data.hasNextPage) {
      this.applyLocalFilters(this.data.page + 1)
    }
  },

  onStatusChange(event) {
    const index = Number(event.detail.value)
    const option = this.data.statusOptions[index] || this.data.statusOptions[0]
    this.setData({
      selectedStatusIndex: index,
      selectedStatusLabel: option.label,
      statusFilter: option.value
    }, () => {
      this.applyLocalFilters(1)
    })
  },

  onCategoryChange(event) {
    const index = Number(event.detail.value)
    const option = this.data.categoryOptions[index] || this.data.categoryOptions[0]
    this.setData({
      selectedCategoryIndex: index,
      selectedCategoryLabel: option.label,
      categoryFilter: option.value
    }, () => {
      this.applyLocalFilters(1)
    })
  },

  async pickCategoryLabel(detection) {
    const options = getDetectionCategoryOptions(detection)
    if (options.length <= 1) {
      return options[0]
    }
    return new Promise((resolve) => {
      wx.showActionSheet({
        itemList: options,
        success: (res) => resolve(options[res.tapIndex] || ''),
        fail: () => resolve('')
      })
    })
  },

  async openDetectionDetailById(id) {
    try {
      const detail = await request({ url: `/api/detections/${id}/` })
      const hydrated = await hydrateImageFields(detail, [
        { sourceField: 'original_image_url', targetField: 'original_image_local_path' },
        { sourceField: 'visualized_image_url', targetField: 'visualized_image_local_path' }
      ])
      getApp().globalData.detectionDetail = hydrated
      wx.navigateTo({ url: '/pages/result/result' })
    } catch (error) {
      wx.showToast({ title: error.detail || '读取失败', icon: 'none' })
    }
  },

  async openDetectionDetail(event) {
    const detectionId = Number(event.currentTarget.dataset.id)
    if (!detectionId) {
      wx.showToast({ title: '记录不可用', icon: 'none' })
      return
    }
    await this.openDetectionDetailById(detectionId)
  },

  async toggleDetectionCollection(event) {
    const detectionId = Number(event.currentTarget.dataset.id)
    const detection = this.data.allDetections.find((item) => item.id === detectionId)
    if (!detection) {
      wx.showToast({ title: '记录不存在', icon: 'none' })
      return
    }

    let categoryLabel = ''
    if (!detection.is_collected) {
      categoryLabel = await this.pickCategoryLabel(detection)
      if (!categoryLabel) {
        return
      }
    }

    this.setData({ loading: true })
    wx.showLoading({ title: detection.is_collected ? '取消归档中...' : '归档中...', mask: true })
    try {
      await ensureLogin()
      const payload = await request({
        url: `/api/dataset-toggle/${detectionId}/`,
        method: 'POST',
        data: categoryLabel ? { category_label: categoryLabel } : {}
      })
      await this.loadData()
      wx.showToast({ title: payload.collected ? '已归档到数据集' : '已取消归档', icon: 'success' })
    } catch (error) {
      wx.showToast({ title: error.detail || '操作失败', icon: 'none' })
    } finally {
      wx.hideLoading()
      this.setData({ loading: false })
    }
  },

  async previewImage(event) {
    const url = event.currentTarget.dataset.url
    if (!url) return
    wx.showLoading({ title: '打开图片...', mask: true })
    try {
      const localPath = await downloadFile({
        url,
        fileName: event.currentTarget.dataset.filename || 'dataset-preview.jpg'
      })
      wx.previewImage({
        urls: [localPath],
        current: localPath
      })
    } catch (error) {
      wx.showToast({ title: error.detail || '图片预览失败', icon: 'none' })
    } finally {
      wx.hideLoading()
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
  }
})
