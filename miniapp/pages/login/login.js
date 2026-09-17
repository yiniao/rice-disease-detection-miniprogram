const { getBaseUrl, login, register } = require('../../utils/request')

Page({
  data: {
    mode: 'login',
    username: '',
    nickname: '',
    password: '',
    confirmPassword: '',
    loading: false
  },

  onLoad() {
    const token = wx.getStorageSync('token')
    if (token) {
      wx.reLaunch({ url: '/pages/index/index' })
      return
    }
    const baseUrl = getBaseUrl()
    if (/127\.0\.0\.1|localhost/.test(baseUrl)) {
      wx.showToast({
        title: '请先配置后端地址',
        icon: 'none',
        duration: 2500
      })
    }
  },

  onUsernameInput(event) {
    this.setData({ username: event.detail.value })
  },

  onNicknameInput(event) {
    this.setData({ nickname: event.detail.value })
  },

  onPasswordInput(event) {
    this.setData({ password: event.detail.value })
  },

  onConfirmPasswordInput(event) {
    this.setData({ confirmPassword: event.detail.value })
  },

  switchMode(event) {
    const mode = event.currentTarget.dataset.mode || 'login'
    this.setData({
      mode,
      password: '',
      confirmPassword: ''
    })
  },

  async submitAuth() {
    if (!this.data.username || !this.data.password) {
      wx.showToast({ title: '请输入用户名和密码', icon: 'none' })
      return
    }
    if (this.data.mode === 'register') {
      if (this.data.password.length < 8) {
        wx.showToast({ title: '密码至少 8 位', icon: 'none' })
        return
      }
      if (this.data.password !== this.data.confirmPassword) {
        wx.showToast({ title: '两次输入的密码不一致', icon: 'none' })
        return
      }
    }
    this.setData({ loading: true })
    try {
      if (this.data.mode === 'register') {
        await register({
          username: this.data.username.trim(),
          password: this.data.password,
          nickname: this.data.nickname.trim()
        })
      } else {
        await login(this.data.username.trim(), this.data.password)
      }
      wx.reLaunch({ url: '/pages/index/index' })
    } catch (error) {
      wx.showToast({
        title: error.detail || error.errMsg || (this.data.mode === 'register' ? '注册失败' : '登录失败'),
        icon: 'none'
      })
    } finally {
      this.setData({ loading: false })
    }
  }
})
