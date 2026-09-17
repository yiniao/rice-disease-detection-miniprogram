function syncTabBar(page, selectedPath) {
  if (!page || typeof page.getTabBar !== 'function') {
    return
  }
  const tabBar = page.getTabBar()
  if (!tabBar || typeof tabBar.setData !== 'function') {
    return
  }
  tabBar.setData({
    selectedPath
  })
}

module.exports = {
  syncTabBar
}
