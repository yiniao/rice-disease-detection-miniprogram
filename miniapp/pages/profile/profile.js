const { ensureLogin, logout, updateMe } = require('../../utils/request')
const { syncTabBar } = require('../../utils/tabbar')

function isAuthError(error) {
  const detail = String(error && error.detail ? error.detail : '')
  const statusCode = Number(error && error.statusCode ? error.statusCode : 0)
  return statusCode === 401 || /请先登录|token|认证|unauthorized|unauthor/i.test(detail)
}

Page({
  data: {
    user: {},
    avatarText: 'U',
    username: '',
    nickname: '',
    oldPassword: '',
    newPassword: '',
    confirmPassword: '',
    saving: false
  },

  async onShow() {
    syncTabBar(this, 'pages/profile/profile')
    const cachedUser = getApp().globalData.user || wx.getStorageSync('user') || {}
    if (cachedUser && (cachedUser.username || cachedUser.nickname)) {
      this.syncUser(cachedUser)
    }
    try {
      await ensureLogin()
    } catch (error) {
      if (isAuthError(error) || String(error && error.detail ? error.detail : '') === '请先登录') {
        logout()
        wx.reLaunch({ url: '/pages/login/login' })
        return
      }
      if (!(cachedUser && (cachedUser.username || cachedUser.nickname))) {
        wx.showToast({ title: '个人信息加载失败', icon: 'none' })
      }
    }
  },

  syncUser(user) {
    const avatarText = ((user.nickname || user.username || 'U').trim().charAt(0) || 'U').toUpperCase()
    this.setData({
      user,
      avatarText,
      username: user.username || '',
      nickname: user.nickname || '',
      oldPassword: '',
      newPassword: '',
      confirmPassword: ''
    })
  },

  onUsernameInput(event) {
    this.setData({ username: event.detail.value })
  },

  onNicknameInput(event) {
    this.setData({ nickname: event.detail.value })
  },

  onOldPasswordInput(event) {
    this.setData({ oldPassword: event.detail.value })
  },

  onNewPasswordInput(event) {
    this.setData({ newPassword: event.detail.value })
  },

  onConfirmPasswordInput(event) {
    this.setData({ confirmPassword: event.detail.value })
  },

  async saveProfile() {
    const { username, nickname, oldPassword, newPassword, confirmPassword } = this.data
    if (!username.trim()) {
      wx.showToast({ title: '请输入用户名', icon: 'none' })
      return
    }
    if ((newPassword || confirmPassword || oldPassword) && (!oldPassword || !newPassword || !confirmPassword)) {
      wx.showToast({ title: '修改密码需填写完整', icon: 'none' })
      return
    }
    this.setData({ saving: true })
    wx.showLoading({ title: '保存中...', mask: true })
    try {
      const user = await updateMe({
        username: username.trim(),
        nickname: nickname.trim(),
        old_password: oldPassword,
        new_password: newPassword,
        confirm_password: confirmPassword
      })
      this.syncUser(user)
      wx.showToast({ title: '已保存', icon: 'success' })
    } catch (error) {
      if (Number(error && error.statusCode) === 404) {
        wx.showToast({ title: '资料接口未部署，请先发布后端', icon: 'none' })
      } else {
        wx.showToast({ title: error.detail || '保存失败', icon: 'none' })
      }
    } finally {
      wx.hideLoading()
      this.setData({ saving: false })
    }
  },

  doLogout() {
    logout()
    wx.reLaunch({ url: '/pages/login/login' })
  }
})
