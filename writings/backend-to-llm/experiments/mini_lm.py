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
