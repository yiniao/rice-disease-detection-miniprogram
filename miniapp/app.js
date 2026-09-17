const { CLOUD_ENV } = require('./utils/config')

App({
  globalData: {
    user: null,
    token: wx.getStorageSync('token') || '',
    detectionDetail: null
  },

  onLaunch() {
    wx.cloud.init({ env: CLOUD_ENV || undefined })
    this.globalData.user = wx.getStorageSync('user') || null
  }
})
