---
id: backend-to-llm-lab
work_id: backend-to-llm
title: 第6章 · 在CPU上训练自己的字符语言模型
status: 草稿
version: 1
updated: 2026-11-01
---

# 第6章 · 在CPU上训练自己的字符语言模型

> 材料说明：基于2026-11-01用户问题与所贴AI回答重新编写；技术事实就近链接原始资料，时间与路线属于编写建议。

<!-- block: experiment-question -->
## 01 · 这次实验只验证三件事

我们要验证：参数能否通过训练改善预测？引入上下文能否优于只看前一个字符？保存再加载后，模型是否保持同样的计算结果？

数据由脚本现场生成：240条形如`service api reads key k003 result hit.`的合成事件记录。它们是教学样本，不是真实日志；重复的语法故意降低任务难度。每条记录不同，先打乱整条记录，再按192/48分成训练和验证，之后才采窗口。

本实验没有最终测试集，验证集还参与观察训练，所以只能作为教学比较，不能作为正式泛化报告。训练和验证共享同一种生成语法，有些键值也会在不同记录中出现，不能据此宣称模型学会真实语言或学会处理未知业务。

<!-- block: run-it -->
## 02 · 运行方法与环境

完整脚本在本章末尾，也保存于项目的`writings/backend-to-llm/experiments/mini_lm.py`。你可以复制末尾代码为`mini_lm.py`。它只有PyTorch这一项直接第三方依赖，默认CPU、2线程，不下载数据或模型权重。

在有Python 3.12和uv的环境中：

```sh
uv run --python 3.12 --with torch mini_lm.py --model gpt --steps 400 --out runs/gpt
uv run --python 3.12 --with torch mini_lm.py --model bigram --steps 400 --out runs/bigram
```

也可以在自己的虚拟环境安装PyTorch后用`python mini_lm.py`运行；安装方式随系统和设备选择，以[PyTorch官方安装入口](https://pytorch.org/get-started/locally/)为准。首次安装可能花时间或遇到网络问题，它与训练本身的耗时不同。不要因为环境问题就推断模型规模过大。

脚本会输出训练与验证loss、参数量、生成样本，并把权重和JSON结果放到指定目录。默认输出目录是当前目录下的`mini-lm-output`；用于本项目时请将输出放入已忽略的`tmp/`，避免提交二进制权重。

<!-- block: what-to-observe -->
## 03 · 先预测结果，再看屏幕

bigram只根据当前字符预测下一个字符。例如看到空格后，无法区分自己位于`service `还是`result `之后，因为它记不住更前面的词。Transformer可以利用窗口里的多个位置，但窗口长度只有24，也没有无限记忆。

运行前写下三项预测：初始loss大致会不会接近`ln(词表大小)`？Transformer的验证loss是否会低于bigram？哪一种输出更像完整事件记录？预测不需要先答对，它帮助你在观察后明确更新了什么认识。

成功标准不是“生成像聊天的句子”，而是：在相同数据和留出窗口上观察loss变化；解释两种模型使用的信息差别；两项程序断言通过。bigram与Transformer参数量不同，这不是严格控制计算预算的算法比较。

<!-- block: observed-result -->
## 04 · 本次实际观测

本书编写时已在本机实际执行两种模型，各训练400步。环境为Python 3.12、PyTorch 2.15.0、Darwin arm64、CPU、2线程，固定随机种子42，窗口24，batch size为16，词表为31个字符。验证集使用12批固定窗口，按token平均交叉熵。

| 模型 | 参数量 | 训练前验证loss | 400步后验证loss |
| --- | --- | --- | --- |
| bigram | 961 | 4.0092 | 2.3417 |
| 两层微型Transformer | 60,799 | 3.5426 | 0.1999 |

在这份非常简单的留出数据上，Transformer的验证损失更低，生成样本更接近事件语法。这支持“它能利用超出单字符的信息”这一有限判断，不支持真实中文、问答或推理能力的结论。单次运行不是统计显著性研究，不同版本和设备也可能产生不同数值。

本次Transformer的真实输出片段：

```text
service api reads key k033 result hit.
service worker reads key k038 result hit.
service api reads key k010 result miss.
```

两种模型均通过因果性检查与保存重载检查。模型权重和完整结果留在本地`tmp/coauthor-check/`，不加入网站或仓库。运行时PyTorch提示未安装NumPy，但本实验没有调用NumPy接口，训练与断言正常完成；若你的环境有此提示，可区分它与真正的执行异常。


<!-- block: checks-and-limits -->
## 05 · 两个检查，比漂亮样本更重要

**因果检查**：改掉窗口后半段，前半段logits应保持不变。若改变了，模型可能偷看未来；即便loss很好，也不是符合本任务定义的因果预测器。

**重载检查**：保存权重，重新构造同类模型并加载，比较同一输入的logits是否完全相同。只看到文件存在不能证明保存正确。实际部署还需要tokenizer、配置、版本和输入预处理一起管理，本例已保存词表和窗口配置，但没有构建服务。

这个小模型没有指令训练、知识库或工具系统。生成的`hit`也不是对真实缓存的检测结果。它只是学到训练分布中的字符规律。若让它回答“生产事故原因是什么”，输出没有可信依据。

<!-- block: experiments-to-change -->
## 06 · 接下来改哪个变量

先只改一个变量：将窗口从24缩到8，或将训练步数从400改为100、800。记录验证loss和三段固定提示的输出。观察长窗口是否真的被利用，而不是预先认定更大一定更好。

若要做正式验证，可再切出从未用于选择参数的测试记录；若想验证组合泛化，可按键值或模板分组切分，而不是只随机拆记录。若使用真实语料，必须重新考虑数据许可、清洗、重复和隐私边界。

完整代码如下。注意`loss.backward()`与`optimizer.step()`分别承担什么；先追踪`[B,T]`到`[B,T,V]`，再读生成循环。代码中的`view`、`transpose`与`contiguous`可以拿到聊天里逐行讲。

<!-- block: complete-code -->
## 07 · 完整教学代码

```python
"""A CPU teaching experiment: bigram baseline and causal Transformer.
Self-authored synthetic event records; no downloads, no pretrained weights.
Python 3.12, PyTorch 2.x. Run --steps 400 --model gpt, or --model bigram.
"""
import argparse
import json
import random
from pathlib import Path

import torch
from torch import nn
from torch.nn import functional as F


def documents():
    # A shared grammar with distinct keys. Split whole records before windowing.
    return [f"service {s} reads key k{i:03d} result {r}.\n"
            for i in range(60) for s in ("api", "worker")
            for r in ("hit", "miss")]


class Bigram(nn.Module):
    def __init__(self, vocab, context):
        super().__init__()
        self.table = nn.Embedding(vocab, vocab)

    def forward(self, ids):
        return self.table(ids)


class Attention(nn.Module):
    def __init__(self, width, heads, context):
        super().__init__()
        self.heads = heads
        self.qkv = nn.Linear(width, 3 * width)
        self.out = nn.Linear(width, width)
        self.register_buffer("mask", torch.tril(torch.ones(context, context)).bool())

    def forward(self, x):
        b, t, c = x.shape
        q, k, v = self.qkv(x).chunk(3, dim=-1)
        q, k, v = [z.view(b, t, self.heads, c // self.heads).transpose(1, 2)
                   for z in (q, k, v)]
        scores = q @ k.transpose(-2, -1) / (k.size(-1) ** 0.5)
        weights = scores.masked_fill(~self.mask[:t, :t], float("-inf")).softmax(-1)
        out = (weights @ v).transpose(1, 2).contiguous().view(b, t, c)
        return self.out(out)


class Block(nn.Module):
    def __init__(self, width, heads, context):
        super().__init__()
        self.norm1, self.norm2 = nn.LayerNorm(width), nn.LayerNorm(width)
        self.attn = Attention(width, heads, context)
        self.ffn = nn.Sequential(nn.Linear(width, 4 * width), nn.GELU(),
                                 nn.Linear(4 * width, width))

    def forward(self, x):
        x = x + self.attn(self.norm1(x))
        return x + self.ffn(self.norm2(x))


class TinyGPT(nn.Module):
    def __init__(self, vocab, context):
        super().__init__()
        width = 48
        self.tokens = nn.Embedding(vocab, width)
        self.positions = nn.Embedding(context, width)
        self.blocks = nn.Sequential(*[Block(width, 3, context) for _ in range(2)])
        self.norm = nn.LayerNorm(width)
        self.head = nn.Linear(width, vocab)

    def forward(self, ids):
        x = self.tokens(ids) + self.positions(torch.arange(ids.size(1)))
        return self.head(self.norm(self.blocks(x)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=("bigram", "gpt"), default="gpt")
    parser.add_argument("--steps", type=int, default=400)
    parser.add_argument("--out", type=Path, default=Path("mini-lm-output"))
    args = parser.parse_args()
    if args.steps < 1:
        parser.error("steps must be positive")
    torch.set_num_threads(2)
    torch.manual_seed(42)
    docs = documents()
    random.Random(42).shuffle(docs)
    chars = sorted(set("".join(docs)))  # Alphabet only; not learned from held-out text.
    stoi = {c: i for i, c in enumerate(chars)}
    context, batch_size = 24, 16
    encode = lambda text: torch.tensor([stoi[c] for c in text], dtype=torch.long)
    train, valid = [encode("".join(part)) for part in (docs[:192], docs[192:])]
    assert not set(docs[:192]) & set(docs[192:])
    # Frozen validation windows, separate RNG: evaluations don't alter training batches.
    eval_rng = torch.Generator().manual_seed(123)

    def batch(data, rng=None):
        starts = torch.randint(len(data) - context, (batch_size,), generator=rng)
        return (torch.stack([data[i:i + context] for i in starts]),
                torch.stack([data[i + 1:i + context + 1] for i in starts]))

    validation = [batch(valid, eval_rng) for _ in range(12)]
    model = (TinyGPT if args.model == "gpt" else Bigram)(len(chars), context)
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.003)

    def loss_for(x, y):
        logits = model(x)  # [B, T, V], targets [B, T]
        return F.cross_entropy(logits.reshape(-1, len(chars)), y.reshape(-1))

    @torch.no_grad()
    def evaluate():
        model.eval()
        value = torch.stack([loss_for(x, y) for x, y in validation]).mean().item()
        model.train()
        return value

    initial = evaluate()
    for step in range(1, args.steps + 1):
        loss = loss_for(*batch(train))
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        optimizer.step()
        if step == 1 or step % 100 == 0 or step == args.steps:
            print(f"step={step} train={loss.item():.4f} valid={evaluate():.4f}")
    final = evaluate()
    model.eval()
    with torch.no_grad():
        x, _ = validation[0]
        altered = x.clone()
        altered[:, 12:] = (altered[:, 12:] + 1) % len(chars)
        assert torch.allclose(model(x)[:, :12], model(altered)[:, :12], atol=1e-6)
        expected = model(x).clone()
        args.out.mkdir(parents=True, exist_ok=True)
        torch.save({"state_dict": model.state_dict(), "chars": chars,
                    "context": context, "model": args.model}, args.out / "model.pt")
        checkpoint = torch.load(args.out / "model.pt", weights_only=True)
        reloaded = (TinyGPT if checkpoint["model"] == "gpt" else Bigram)(len(checkpoint["chars"]), checkpoint["context"])
        reloaded.load_state_dict(checkpoint["state_dict"])
        reloaded.eval()
        assert torch.equal(expected, reloaded(x))
        ids = torch.tensor([[stoi[c] for c in "service "]])
        for _ in range(160):
            logits = reloaded(ids[:, -context:])[:, -1]
            next_id = torch.multinomial(logits.softmax(-1), 1)
            ids = torch.cat([ids, next_id], dim=1)
        sample = "".join(chars[i] for i in ids[0].tolist())
    result = {"torch": torch.__version__, "device": "cpu", "model": args.model,
              "parameters": sum(p.numel() for p in model.parameters()),
              "vocab": len(chars), "context": context, "steps": args.steps,
              "initial_valid_loss": initial, "final_valid_loss": final,
              "causal_check": True, "reload_check": True, "sample": sample}
    (args.out / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
```
