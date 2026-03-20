// 数字分身的知识库
const knowledgeBase = {
    // 关于她在做什么
    '做什么': '林安现在主要在搭自己的个人主页，同时正在整理自己的作品和写作方向。作为内容策划，她希望能用 AI 工具做出更棒的产品。',
    '在做什么': '林安现在主要在搭自己的个人主页，同时正在整理自己的作品和写作方向。作为内容策划，她希望能用 AI 工具做出更棒的产品。',
    '最近': '林安现在主要在搭自己的个人主页，同时正在整理自己的作品和写作方向。作为内容策划，她希望能用 AI 工具做出更棒的产品。',
    '工作': '林安是一名内容策划，正在学习用 AI 做产品。她最近在做个人主页和整理作品集。',
    '职业': '林安是一名内容策划，正在学习用 AI 做产品。她擅长内容表达和知识整理。',

    // 关于作品
    '作品': '林安正在整理作品集，目前主要涉及 AI 应用相关的内容策划和写作。如果你对某个具体项目感兴趣，可以问她更多细节！',
    '项目': '林安正在整理作品集，目前主要涉及 AI 应用相关的内容策划和写作。如果你对某个具体项目感兴趣，可以问她更多细节！',

    // 关于联系
    '联系': '你可以通过邮箱联系林安，或者在社交媒体上找到她。她很乐意和朋友、潜在合作伙伴交流！',
    '怎么联系': '你可以通过邮箱联系林安，或者在社交媒体上找到她。她很乐意和朋友、潜在合作伙伴交流！',
    '邮箱': '你可以通过邮箱联系林安，或者在社交媒体上找到她。她很乐意和朋友、潜在合作伙伴交流！',
    '微信': '林安很乐意和大家交流，具体联系方式可以通过邮箱获取。',
    'social': '林安很乐意和大家交流，具体联系方式可以通过邮箱获取。',

    // 关于兴趣
    '兴趣': '林安的兴趣包括 AI 应用、写作和旅行。她喜欢探索新技术如何帮助人们更好地表达和创作。',
    '爱好': '林安的兴趣包括 AI 应用、写作和旅行。她喜欢探索新技术如何帮助人们更好地表达和创作。',

    // 关于特点
    '特点': '林安最有记忆点的特点是：喜欢把复杂问题讲成人话。作为内容策划，她善于将深奥的概念用简单易懂的方式表达出来。',
    '擅长': '林安擅长内容表达、AI 应用和知识整理。她的特点是能把复杂问题讲成人话。',

    // 默认回答
    'default': '抱歉，这个问题暂时不在我的知识库里。不过你可以问问我：你在做什么？你有哪些作品？怎么联系你？'
};

// 分析用户问题并获取答案
function getAnswer(question) {
    question = question.toLowerCase().trim();

    // 检查关键词匹配
    for (const [key, answer] of Object.entries(knowledgeBase)) {
        if (key === 'default') continue;

        if (question.includes(key)) {
            return answer;
        }
    }

    // 返回默认回答
    return knowledgeBase['default'];
}

// 创建消息元素
function createMessageElement(type, text) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;

    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'avatar-small';

    const avatarImg = document.createElement('img');
    avatarImg.src = type === 'bot'
        ? 'https://api.dicebear.com/7.x/avataaars/svg?seed=linan&backgroundColor=b6e3f4'
        : 'https://api.dicebear.com/7.x/avataaars/svg?seed=visitor&backgroundColor=c0aede';

    avatarDiv.appendChild(avatarImg);

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    const paragraph = document.createElement('p');
    paragraph.textContent = text;

    contentDiv.appendChild(paragraph);
    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(contentDiv);

    return messageDiv;
}

// 添加消息到聊天区域
function addMessage(type, text) {
    const chatMessages = document.getElementById('chatMessages');
    const messageElement = createMessageElement(type, text);
    chatMessages.appendChild(messageElement);

    // 滚动到底部
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// 处理用户输入
function handleUserInput(input) {
    if (!input.trim()) return;

    // 添加用户消息
    addMessage('user', input);

    // 模拟思考延迟
    setTimeout(() => {
        const answer = getAnswer(input);
        addMessage('bot', answer);
    }, 500);
}

// 初始化事件监听
document.addEventListener('DOMContentLoaded', () => {
    const chatInput = document.getElementById('chatInput');
    const sendButton = document.getElementById('sendButton');
    const quickButtons = document.querySelectorAll('.quick-btn');

    // 发送按钮点击事件
    sendButton.addEventListener('click', () => {
        handleUserInput(chatInput.value);
        chatInput.value = '';
    });

    // 输入框回车事件
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            handleUserInput(chatInput.value);
            chatInput.value = '';
        }
    });

    // 快捷问题按钮点击事件
    quickButtons.forEach(button => {
        button.addEventListener('click', () => {
            const question = button.getAttribute('data-question');
            handleUserInput(question);
        });
    });

    // 页面加载完成后，让输入框获得焦点
    if (window.innerWidth > 768) {
        chatInput.focus();
    }
});
