import math
import os
import re
import time
from collections import Counter
from functools import lru_cache

from wiki import search_titles, download_article, safe_name

PAGES_DIR = os.path.join("data", "pages")

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by", "for",
    "from", "had", "has", "have", "he", "her", "his", "in", "is", "it",
    "its", "of", "on", "or", "she", "that", "the", "their", "they", "this",
    "to", "was", "were", "which", "who", "will", "with", "would",
}


def tokenize(text):
    """Turn raw text into a list of lowercase words, without stop words."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w for w in words if w not in STOP_WORDS]


@lru_cache(maxsize=None)
def load_text(doc):
    with open(os.path.join(PAGES_DIR, doc + ".txt"), encoding="utf-8") as f:
        return f.read()


def add_document(doc, index, doc_lengths):
    """Add one saved article to the inverted index."""
    if doc in doc_lengths:
        return
    tokens = tokenize(load_text(doc))
    if not tokens:
        return
    doc_lengths[doc] = len(tokens)
    for word, count in Counter(tokens).items():
        index.setdefault(word, {})[doc] = count


def build_index(folder=PAGES_DIR):
    """Inverted index: word -> {document: count}, plus each document's length."""
    index, doc_lengths = {}, {}
    for filename in os.listdir(folder):
        if filename.endswith(".txt"):
            add_document(filename[:-4], index, doc_lengths)
    return index, doc_lengths


def grow_index(query, index, doc_lengths, limit=3):
    """Fetch Wikipedia's top articles for a query and add any new ones.
    Returns (all matching documents, newly added documents)."""
    hits, added = [], []
    for title in search_titles(query, limit):
        if "(disambiguation)" in title:
            continue
        doc = safe_name(title)
        if doc not in doc_lengths:
            download_article(title)
            if os.path.exists(os.path.join(PAGES_DIR, doc + ".txt")):
                add_document(doc, index, doc_lengths)
                added.append(doc)
            time.sleep(0.5)
        if doc in doc_lengths:
            hits.append(doc)
    return hits, added


def search(query, index, doc_lengths, top_k=10, boost_docs=None):
    """Rank documents with TF-IDF, then boost title, exact-phrase and Wikipedia matches."""
    words = list(set(tokenize(query)))
    if not words:
        return []
    boost_docs = boost_docs or set()
    n_docs = len(doc_lengths)
    postings = [set(index.get(w, {})) for w in words]

    # Documents containing ALL the query words; fall back to ANY if none do
    candidates = set.intersection(*postings)
    if not candidates:
        candidates = set.union(*postings)
    candidates = candidates | (boost_docs & set(doc_lengths))

    query_clean = " ".join(re.findall(r"[a-z0-9]+", query.lower()))
    scores = {}
    for doc in candidates:
        # Base score: TF-IDF
        score = 0.0
        for w in words:
            count = index.get(w, {}).get(doc)
            if count:
                idf = math.log(n_docs / len(index[w])) + 1
                score += (count / doc_lengths[doc]) * idf

        # Boost if query words appear in the title
        title_words = set(tokenize(doc))
        title_hits = sum(1 for w in words if w in title_words)
        score *= 1 + 3 * title_hits / len(words)

        # Big boost if the title is exactly the query
        if " ".join(re.findall(r"[a-z0-9]+", doc.lower())) == query_clean:
            score *= 5

        # Boost if the exact phrase appears in the text
        text_clean = " ".join(re.findall(r"[a-z0-9]+", load_text(doc).lower()))
        if len(words) > 1 and query_clean in text_clean:
            score *= 2

        # Boost articles that Wikipedia's own search also picked for this query
        if doc in boost_docs:
            score *= 3

        scores[doc] = score

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    if not ranked:
        return []

    # Drop weak matches: keep only results scoring at least 25% of the best
    best = ranked[0][1]
    ranked = [(doc, s) for doc, s in ranked if s >= 0.25 * best]
    return ranked[:top_k]


def split_sentences(text):
    """Split an article into clean sentences, skipping headings."""
    sentences = []
    for line in text.split("\n"):
        line = line.strip()
        if not line or line.startswith("="):
            continue
        for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", line):
            if 40 <= len(s) <= 400:
                sentences.append(s)
    return sentences


def make_overview(query, results, max_docs=3, max_chars=1300):
    """Extractive overview: the most relevant sentences from the top articles.
    Returns [(document, [sentences in their original order]), ...]."""
    words = set(tokenize(query))
    groups, used = [], 0
    for rank, (doc, _score) in enumerate(results[:max_docs]):
        scored = []
        for pos, s in enumerate(split_sentences(load_text(doc))):
            hits = len(words & set(tokenize(s)))
            if hits == 0 and pos >= 2:
                continue
            # more query words = better; the opening sentences define the topic
            scored.append((hits + (1.5 if pos < 2 else 0) - 0.02 * pos, pos, s))
        scored.sort(reverse=True)
        take = 4 if rank == 0 else 2
        chosen = sorted(scored[:take], key=lambda item: item[1])
        sentences = []
        for _, _, s in chosen:
            if used + len(s) > max_chars:
                break
            sentences.append(s)
            used += len(s)
        if sentences:
            groups.append((doc, sentences))
    return groups


def get_snippet(doc, query_words, length=300):
    """Show the sentence containing the most query words."""
    text = load_text(doc)
    best, best_hits = "", 0
    for s in split_sentences(text):
        hits = sum(1 for w in query_words if w in set(tokenize(s)))
        if hits > best_hits:
            best, best_hits = s, hits
    snippet = best if best else text[:length]
    return snippet[:length] + ("..." if len(snippet) > length else "")


if __name__ == "__main__":
    index, doc_lengths = build_index()
    print(len(doc_lengths), "documents,", len(index), "unique words")
    results = search("first person on the moon", index, doc_lengths, 5)
    for doc, score in results:
        print(f"{score:.4f}  {doc}")
    for doc, sentences in make_overview("first person on the moon", results):
        print(doc, "->", " ".join(sentences)[:200])