const TABS = [
  {
    pagePath: 'pages/index/index',
    text: '检测',
    iconPath: '/images/tabbar/tab-detect.png',
    selectedIconPath: '/images/tabbar/tab-detect-active.png'
  },
  {
    pagePath: 'pages/history/history',
    text: '历史',
    iconPath: '/images/tabbar/tab-history.png',
    selectedIconPath: '/images/tabbar/tab-history-active.png'
  },
  {
    pagePath: 'pages/dataset/dataset',
    text: '采集',
    iconPath: '/images/tabbar/tab-dataset.png',
    selectedIconPath: '/images/tabbar/tab-dataset-active.png'
  },
  {
    pagePath: 'pages/statistics/statistics',
    text: '统计',
    iconPath: '/images/tabbar/tab-stats.png',
    selectedIconPath: '/images/tabbar/tab-stats-active.png'
  },
  {
    pagePath: 'pages/profile/profile',
    text: '我的',
    iconPath: '/images/tabbar/tab-profile.png',
    selectedIconPath: '/images/tabbar/tab-profile-active.png'
  }
]

function getCurrentRoute() {
  const pages = getCurrentPages()
  if (!pages.length) {
    return ''
  }
  return pages[pages.length - 1].route || ''
}

Component({
  data: {
    tabs: TABS,
    selectedPath: ''
  },

  lifetimes: {
    attached() {
      this.syncSelected()
    }
  },

  pageLifetimes: {
    show() {
      this.syncSelected()
    }
  },

  methods: {
    syncSelected() {
      this.setData({
        selectedPath: getCurrentRoute()
      })
    },

    onTabTap(event) {
      const { path } = event.currentTarget.dataset
      if (!path) {
        return
      }
      if (path === this.data.selectedPath) {
        return
      }
      this.setData({
        selectedPath: path
      })
      wx.switchTab({
        url: `/${path}`
      })
    }
  }
})
