// 扩展安装时执行
chrome.runtime.onInstalled.addListener(() => {
    console.log('Extension installed');
    // 设置侧边栏行为
    chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true })
        .catch(error => console.error('Error setting side panel behavior:', error));
});

// 点击扩展图标时打开侧边栏
chrome.action.onClicked.addListener((tab) => {
    chrome.sidePanel.open({ windowId: tab.windowId });
});