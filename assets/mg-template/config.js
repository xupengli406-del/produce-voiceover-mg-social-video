window.MG_CONFIG = {
  title: "示例主题",
  series: "信息型 MG",
  duration: 60,
  theme: {
    paper: "#FBF4E8",
    ink: "#111522",
    blue: "#2167F5",
    navy: "#14245B",
    yellow: "#FFD84D",
    yellow2: "#FFF1A3",
    green: "#19B77A",
    mint: "#DDF6E9",
    coral: "#FF6B57",
    gray: "#707681",
    white: "#FFFFFF"
  },
  scenes: [
    {
      type: "hook",
      duration: 8,
      tag: "先用一句人话理解",
      title: "一个信息或概念",
      accent: "到底意味着什么？",
      subtitle: "先说结论，再给例子"
    },
    {
      type: "list",
      duration: 12,
      tag: "把复杂词换成动作",
      title: "观众真正关心的",
      accent: "是能解决哪几件事",
      items: ["约时间", "找资料", "改数据", "走流程"]
    },
    {
      type: "workflow",
      duration: 18,
      tag: "用一个例子讲清楚",
      title: "一句需求",
      accent: "被拆成连续动作",
      request: "帮我把这件事继续推进",
      steps: ["读取信息", "创建内容", "更新状态", "通知结果"]
    },
    {
      type: "compare",
      duration: 12,
      tag: "边界与选择",
      title: "不是谁更强",
      accent: "而是谁更适合当前场景",
      left: {label: "方案 A", points: ["适合日常协作", "上手更直接"]},
      right: {label: "方案 B", points: ["适合多个模块", "扩展更灵活"]}
    },
    {
      type: "cta",
      duration: 10,
      tag: "最后一句",
      title: "记住这个结论",
      accent: "把信息变成能执行的动作",
      cta: "收藏并关注下一期"
    }
  ]
};
