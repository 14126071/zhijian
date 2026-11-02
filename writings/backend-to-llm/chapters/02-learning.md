---
id: backend-to-llm-learning
work_id: backend-to-llm
title: 第2章 · 一个模型究竟怎样学会预测
status: 草稿
version: 1
updated: 2026-11-01
---

# 第2章 · 一个模型究竟怎样学会预测

> 材料说明：基于2026-11-01用户问题与所贴AI回答重新编写；技术事实就近链接原始资料，时间与路线属于编写建议。

<!-- block: function-and-state -->
## 01 · 从后端函数走向可学习函数

可以先把模型写成 `logits = model(input_ids, parameters)`。其中输入是整数ID，参数是大量可调整的数字，输出是未经归一化的分数。固定参数和确定性执行条件下，它仍是一次数值计算。训练的特殊之处，在于参数不完全由程序员手写，而由数据和目标函数来更新。

整数ID本身没有语义：17不会因为比8大，就表示更重要的词。Embedding是按ID查出可学习向量的表；向量之间的关系取决于学习任务。推荐系统中的物品ID也可以查类似的向量表，但不意味着两个系统的向量可以直接互换。

<!-- block: hand-computation -->
## 02 · 一个可以亲手计算的预测

为方便手算，假设词表只有“好”“坏”“了”三个token。模型对某位置输出的logits是 `[2, 1, 0]`。softmax把它们变成概率，公式为：

```text
p(i) = exp(z_i) / sum_j exp(z_j)
     ≈ [0.665, 0.245, 0.090]
```

正确下一个token若是“好”，交叉熵损失约为 `-ln(0.665)=0.408`；若实际是“了”，损失约为 `-ln(0.090)=2.408`。更自信地猜错，会受到更大惩罚。这里用自然对数，损失单位可称为nats。

把真实标签写成one-hot向量y，交叉熵对logit的梯度是 `p-y`。真值为“好”时约为 `[-0.335, 0.245, 0.090]`。梯度下降使参数朝降低损失的方向变化。注意：训练更新的是产生这些logits的参数，不是把本次输出数组直接永久写回。

PyTorch的交叉熵接口直接接收logits；训练前不应再手动softmax一次。[CrossEntropyLoss官方定义](https://docs.pytorch.org/docs/stable/generated/torch.nn.CrossEntropyLoss.html)

<!-- block: the-training-loop -->
## 03 · 六行循环里的因果关系

```python
logits = model(x)
loss = cross_entropy(logits, target)
optimizer.zero_grad()
loss.backward()
optimizer.step()
```

前向计算产生预测，损失衡量预测与目标的偏差，反向传播按链式法则计算每个参数对损失的影响，优化器据此修改参数。清梯度是因为PyTorch默认会累加梯度；把多批梯度累加也可以是有意设计，但初学时先掌握每批清零的版本。

`backward()`通常不负责更新权重，`step()`才更新。`eval()`改变某些层的行为，不能代替关闭梯度；推理时常结合`no_grad()`或推理模式使用。[PyTorch自动微分教程](https://docs.pytorch.org/tutorials/beginner/basics/autogradqs_tutorial.html)

<!-- block: self-supervision -->
## 04 · 自监督也有标签

文本“服务 正常 启动”可以自动变成训练对：

```text
输入：服务 正常
目标：正常 启动
```

目标由原始文本右移产生，因而不必逐条人工标注；但模型训练仍有明确目标。把它说成“预训练不需要标签”容易误导，准确说法是“目标通常可由数据本身构造”。[Hugging Face因果语言模型课程](https://huggingface.co/learn/llm-course/chapter7/6)

token也不总是一个汉字或一个英语单词。教学字符模型把每个字符当一个token，是为了让编码透明，不能据此估算真实模型的token费用和上下文容量。

<!-- block: generalization -->
## 05 · 损失下降只回答了一个局部问题

模型可能背下训练样本，也可能学到可迁移规律。验证集用来辅助选择方案；测试集应留到最后，避免反复调参污染最终评估。业务资料若被切成高度重复的片段后随机拆分，训练和验证可能共享相同答案，分数就会虚高。

推荐系统常按时间评估，避免用未来行为预测过去；文档任务可以先按文档或版本切分，再做片段化。数据边界先于模型复杂度。

若损失使用自然对数，困惑度可写成 `exp(平均交叉熵)`。只在tokenizer、数据和评估口径可比时比较；不同切词方法下的两个困惑度，不应直接排名。

练习：词表均匀随机猜测时，每项概率为1/V，损失是多少？答案是`ln(V)`。第6章会把这个量作为初始直觉，但随机初始化的网络不保证恰好输出均匀分布。
