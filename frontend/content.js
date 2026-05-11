chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
    if (request.action === "doAction") {
        // 在这里添加你想要执行的操作
        console.log("Performing action on the page");
        // 示例：改变页面背景颜色
        document.body.style.backgroundColor = "#f0f0f0";
        sendResponse({status: "Action performed"});
    }
    return true; // 保持消息通道打开，以便异步发送响应
});
    