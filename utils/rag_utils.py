import os
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Tuple

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer, CrossEncoder
_EMBEDDER_CACHE: Dict[str, SentenceTransformer] = {}


def _get_cached_embedder(model_name: str) -> SentenceTransformer:
    if model_name not in _EMBEDDER_CACHE:
        _EMBEDDER_CACHE[model_name] = SentenceTransformer(model_name)
    return _EMBEDDER_CACHE[model_name]


from config.settings import get_config


def _hash_text(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _ensure_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


@dataclass
class Chunk:
    text: str
    meta: Dict[str, Any]


class RAGIndexer:
    """负责切分、嵌入、建索引与持久化（FAISS + 本地元数据）。"""

    def __init__(self):
        rag_cfg = get_config("rag")
        self.chunk_size = rag_cfg.get("chunk_size", 800)
        self.chunk_overlap = rag_cfg.get("chunk_overlap", 100)
        self.index_dir = Path(rag_cfg.get("index_dir", "outputs/index"))
        self.embedding_model_name = rag_cfg.get("embedding_model", "BAAI/bge-m3")
        self._ensure_models()

        _ensure_dir(str(self.index_dir))

    def _ensure_models(self):
        # BAAI/bge-m3 建议开启归一化，以使用内积近似余弦
        self.embedder = _get_cached_embedder(self.embedding_model_name)

    def split_text(self, text: str, file_id: str) -> List[Chunk]:
        chunks: List[Chunk] = []
        clean = text.replace("\r\n", "\n").replace("\r", "\n")
        length = len(clean)
        stride = max(1, self.chunk_size - self.chunk_overlap)
        start = 0
        while start < length:
            end = min(length, start + self.chunk_size)
            chunk_text = clean[start:end]
            meta = {
                "file_id": file_id,
                "start": start,
                "end": end,
            }
            chunks.append(Chunk(text=chunk_text, meta=meta))
            start += stride
        return chunks

    def _index_paths(self, file_id: str) -> Tuple[Path, Path]:
        base = self.index_dir / file_id
        return base.with_suffix(".faiss"), base.with_suffix(".meta.npy")

    def build_or_load_index(self, file_id: str, text: str) -> Tuple[Any, List[Chunk]]:
        faiss_path, meta_path = self._index_paths(file_id)

        if faiss_path.exists() and meta_path.exists():
            index = faiss.read_index(str(faiss_path))
            metas = np.load(str(meta_path), allow_pickle=True).tolist()
            chunks = [Chunk(text=m["text"], meta={k: v for k, v in m.items() if k != "text"}) for m in metas]
            return index, chunks

        chunks = self.split_text(text, file_id)
        texts = [c.text for c in chunks]
        embeds = self.embedder.encode(texts, normalize_embeddings=True, batch_size=32, show_progress_bar=False)
        embeds = np.array(embeds, dtype=np.float32)

        # 使用内积（与归一化向量等价于 cosine）。当片段较多时切换为 HNSW 以加速检索
        dim = embeds.shape[1]
        if len(chunks) > 1500:
            index = faiss.IndexHNSWFlat(dim, 32)
            index.hnsw.efConstruction = 200
        else:
            index = faiss.IndexFlatIP(dim)
        index.add(embeds)

        # 持久化索引与元数据
        faiss.write_index(index, str(faiss_path))
        metas = []
        for c in chunks:
            m = {**c.meta, "text": c.text}
            metas.append(m)
        np.save(str(meta_path), np.array(metas, dtype=object))
        return index, chunks


_RERANKER_CACHE: Dict[str, CrossEncoder] = {}


def _get_cached_reranker(model_name: str) -> CrossEncoder:
    if model_name not in _RERANKER_CACHE:
        _RERANKER_CACHE[model_name] = CrossEncoder(model_name)
    return _RERANKER_CACHE[model_name]


class RAGRetriever:
    """负责向量检索与重排。"""

    def __init__(self):
        rag_cfg = get_config("rag")
        self.top_k = rag_cfg.get("top_k", 8)
        self.candidate_k = rag_cfg.get("candidate_k", 20)
        self.embedding_model_name = rag_cfg.get("embedding_model", "BAAI/bge-m3")
        self.reranker_model_name = rag_cfg.get("reranker_model", "BAAI/bge-reranker-base")

        # 延迟注入，避免重复加载
        self.embedder = None  # type: ignore
        self.reranker = None  # type: ignore

    def search(self, index: Any, chunks: List[Chunk], question: str) -> List[Chunk]:
        # 先取候选
        q_vec = self.embedder.encode([question], normalize_embeddings=True)
        q_vec = np.array(q_vec, dtype=np.float32)
        scores, idxs = index.search(q_vec, k=min(self.candidate_k, len(chunks)))
        idxs = idxs[0]

        candidates: List[Tuple[int, Chunk]] = []
        for i in idxs:
            if i == -1:
                continue
            candidates.append((i, chunks[i]))

        # 重排：pair (question, passage)
        pairs = [(question, c.text) for _, c in candidates]
        if not pairs:
            return []
        if self.reranker is None:
            self.reranker = _get_cached_reranker(self.reranker_model_name)
        rerank_scores = self.reranker.predict(pairs)
        # 组合并排序
        scored = list(zip(rerank_scores, candidates))
        scored.sort(key=lambda x: float(x[0]), reverse=True)
        top = [c for _, (_, c) in scored[: self.top_k]]
        return top


def build_context(chunks: List[Chunk]) -> Tuple[str, List[Dict[str, Any]]]:
    """将检索片段拼接为上下文，并产出可用于展示的引用元数据。"""
    parts: List[str] = []
    cites: List[Dict[str, Any]] = []
    for idx, c in enumerate(chunks, 1):
        parts.append(f"[片段 {idx}]:\n{c.text}")
        cites.append({
            "index": idx,
            "start": c.meta.get("start"),
            "end": c.meta.get("end"),
            "file_id": c.meta.get("file_id"),
        })
    return "\n\n".join(parts), cites


# ---------- Simple Facade APIs for app.py ----------

def compute_file_id(file_path: str) -> str:
    """根据文件路径的名称、大小与修改时间生成稳定的 file_id。"""
    p = Path(file_path)
    try:
        stat = p.stat()
        basis = f"{p.name}:{stat.st_size}:{int(stat.st_mtime)}"
    except Exception:
        basis = f"{p.name}:{p.exists()}"
    return _hash_text(basis)


def build_or_load_index(file_id: str, text: str):
    """构建或加载索引，返回 store(dict) 与共享的 embedder、占位 reranker(兼容接口)。"""
    indexer = RAGIndexer()
    index, chunks = indexer.build_or_load_index(file_id=file_id, text=text)
    store = {"index": index, "chunks": chunks}
    return store, indexer.embedder, None


def retrieve_with_optional_rerank(
    query: str,
    store: Dict[str, Any],
    embedder: Any,
    top_k: int = 12,
    rerank_top_n: int = 6,
    use_reranker: bool = True,
) -> List[Chunk]:
    retriever = RAGRetriever()
    # 复用已加载的 embedder，避免重复加载
    retriever.embedder = embedder
    # 检索候选并重排
    retriever.top_k = top_k
    retriever.candidate_k = max(top_k, rerank_top_n * 2)
    chunks = retriever.search(store["index"], store["chunks"], query)
    if not use_reranker:
        # 如果关闭重排，则直接返回 top_k（search 已按重排排序，这里兼容开关，直接截断）
        return chunks[:top_k]
    # search 内部已重排，最终裁剪为 rerank_top_n
    return chunks[:rerank_top_n]


def build_context_from_chunks(chunks: List[Chunk]) -> str:
    context, _ = build_context(chunks)
    return context


