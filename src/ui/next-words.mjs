// Short everyday utterances, with explicit Mandarin word boundaries.
// Count continuations for the last one or two words. Ties keep source order.
const english = `thank you for your help
thank you so much
thank you very much
thanks for the update
thanks for your help
thanks again for everything
i am going to school
i am happy to help
i am on my way
i want to go home
i want a coffee
i need to check
i need some help
i think so too
i think it works
i will be there soon
i will let you know
i can help you
i can see it
i would like to try
i have a question
i have to go
i don't know yet
i'm on my way home
can you help me
can you send me the link
can you check this
could you please send it
do you want to go
do you have time today
are you free tomorrow
are you ready to go
what time is it
what do you think
how are you doing
how about tomorrow morning
how was your day
see you later today
see you tomorrow morning
see you soon
talk to you later
let me know when
let me check first
let's meet at school
we can meet tomorrow
we are almost there
where are you now
would you like some more
sounds good to me
good morning everyone
good night everyone
good luck today
no problem at all
no worries at all
happy birthday to you
on the way home
at the same time
looking forward to it
please let me know
please send the link
hello there everyone
hello how are you
take care of yourself
that sounds great
it is ready now
it's time to go
work on the project
finish the homework today
after school today
the next step
the best way
this is my first time`;
const chinese = `我 想 要 吃飯
我 想 去 學校
我 想 問 一下
我 要 吃飯 了
我 要 回家 了
我 要 去 上課
我 是 你 的 朋友
我 是 學生
我 今天 有空
我 已經 到 了
我 在 家裡
我 在 路上
我 可以 幫忙
我 不 知道
我 知道 了
我 覺得 很 好
你 好 嗎
你 在 哪裡
你 在 做 什麼
你 想 吃 什麼
你 要 不要 一起 去
你 可以 幫 我 嗎
你 今天 有空 嗎
你 的 朋友
你 的 作業
你 的 名字
我們 一起 去 吃飯
我們 明天 見
我們 可以 一起 去
今天 天氣 很 好
今天 晚上 有空 嗎
今天 要 上課
明天 早上 見
明天 一起 吃飯
下午 幾點 見面
晚上 一起 吃飯
等 一下 再 說
等 我 一下
等一下 就 到 了
謝謝 你 的 幫忙
謝謝 大家 的 支持
謝謝 老師
不好意思 請問 一下
請問 現在 幾點
請 幫 我 看 一下
可以 幫忙 嗎
可以 一起 去 嗎
好 的 謝謝
好 啊 明天 見
沒有 問題
沒 關係
沒問題 謝謝 你
辛苦 了
早安 今天 好嗎
晚安 明天 見
吃飯 了 嗎
吃完飯 再 去
回家 以後 再 說
到家 了 嗎
下課 了 嗎
放學 後 一起 回家
作業 寫 完 了
這個 怎麼 用
這 是 什麼
這樣 就 可以 了
世界 和平
有 時間 嗎
有空 再 聊
晚點 再 聯絡`;

function indexLines(lines, separator) {
    const counts = new Map();
    for (const line of lines.split('\n')) {
        const words = line.split(' ');
        for (let i = 1; i < words.length; i++) {
            for (let n = 1; n <= Math.min(i, 2); n++) {
                const key = words.slice(i - n, i).join(separator);
                const choices = counts.get(key) || new Map();
                choices.set(words[i], (choices.get(words[i]) || 0) + 1);
                counts.set(key, choices);
            }
        }
    }
    const index = new Map();
    for (const [key, choices] of counts)
        index.set(key, Array.from(choices).sort((a,b) => b[1]-a[1]).map(pair => pair[0]));
    return index;
}
const en = indexLines(english, ' ');
const zh = indexLines(chinese, '');
const maxChinese = Math.max(...Array.from(zh.keys()).map(key => key.length));

export function nextWords(context, mandarin) {
    const keys = [];
    if (mandarin) {
        for (let n = Math.min(context.length,maxChinese); n > 0; n--)
            keys.push(context.slice(-n));
    } else {
        const match = context.toLowerCase().replace(/’/g,"'").match(/(?:^|[^a-z'])((?:[a-z']+ +)?[a-z']+) +$/);
        if (!match) return [];
        const words = match[1].split(/ +/);
        keys.push(words.join(' '), words[words.length-1]);
    }
    const index = mandarin ? zh : en;
    const result = [];
    for (const key of keys) {
        for (const word of index.get(key) || [])
            if (!result.includes(word)) result.push(word);
    }
    return result.slice(0,3);
}
